import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
import httpx

from app.core.config import settings
from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    ExtractedEvidenceItem,
    SourceComparisonItem
)
from app.verification.verdict.base import VerdictEngine
from app.verification.verdict.models import (
    VerdictType,
    EvidenceStrength,
    ConfidenceLevel,
    ClaimVerdictItem
)
from app.verification.verdict.evaluator import EvidenceEvaluator

logger = logging.getLogger(__name__)

VERDICT_SYSTEM_PROMPT = """You are the Final Verdict & Confidence Synthesis Engine for TruthLens AI.
Your role is to impartially synthesize extracted evidence items and source comparisons into a rigorous fact-checking verdict for a specific claim.

CRITICAL NON-HALLUCINATION & INTEGRITY RULES:
1. STRICT BOUNDARY: Base your evaluation ONLY and EXCLUSIVELY on the provided CLAIM, EXTRACTED EVIDENCE, and SOURCE COMPARISONS.
2. DO NOT browse the internet, use external knowledge, or extrapolate beyond what is stated in the provided evidence.
3. NEVER fabricate quotations, facts, dates, sources, or evidence IDs.
4. STRICT PROHIBITION: Never output binary "TRUE" or "FALSE".
5. VERDICT CLASSIFICATIONS (Choose EXACTLY ONE):
   - "SUPPORTED": Direct, corroborating evidence from reliable sources confirms the claim facts.
   - "CONTRADICTED": Direct, verifiable evidence refutes the claim or proves contrary facts/numbers/dates.
   - "MISLEADING": The claim contains an element of truth (e.g. discussions, draft proposals, partial facts) but distorts key context, presents an unapproved proposal as enacted policy, exaggerates figures, or cherry-picks information.
   - "UNVERIFIED": Sources provide background or tangential discussion, but do not conclusively confirm or refute the specific claim.
   - "INSUFFICIENT_EVIDENCE": Little or no relevant evidence was retrieved to substantiate or dispute the claim.
6. TRACEABLE CITATIONS:
   - "supporting_evidence_ids": Array of integer IDs of evidence items that directly support the claim.
   - "contradicting_evidence_ids": Array of integer IDs of evidence items that contradict the claim.
   - "contextual_evidence_ids": Array of integer IDs of evidence items providing background context.
   All IDs MUST strictly be members of the provided evidence list. Do NOT invent IDs.
7. LIMITATIONS:
   - Provide a list of concise empirical limitations in the evidence (e.g., "No primary official documentation available", "Sources are secondary news reports", "Only one source examined").

Return a valid JSON object matching this exact schema:
{
  "verdict": "SUPPORTED | CONTRADICTED | MISLEADING | UNVERIFIED | INSUFFICIENT_EVIDENCE",
  "explanation": "Clear, objective, factual justification referencing the specific evidence without speculation...",
  "supporting_evidence_ids": [1, 2],
  "contradicting_evidence_ids": [],
  "contextual_evidence_ids": [3],
  "limitations": ["Limitation 1", "Limitation 2"]
}
"""


class LLMVerdictEngine(VerdictEngine):
    """
    LLM-powered verdict synthesis engine adhering strictly to non-hallucinatory evaluation constraints.
    Supports OpenAI, Gemini, Ollama, and compatible endpoints with fallback to rule-based evaluation.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower() if settings.LLM_PROVIDER else "none"
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        if self.provider in ("none", ""):
            return False
        if self.provider == "ollama":
            return True
        return bool(self.api_key)

    def determine_verdict(
        self,
        claim_id: int,
        claim_text: str,
        evidence: List[ExtractedEvidenceItem],
        comparisons: List[SourceComparisonItem],
        claim_entities: Optional[List[str]] = None,
        claim_numbers: Optional[List[str]] = None,
        claim_dates: Optional[List[str]] = None,
    ) -> ClaimVerdictItem:
        if not self.is_configured():
            raise ValueError(f"LLM provider '{self.provider}' is not configured.")

        # If zero evidence provided, handle immediately without calling LLM
        if not evidence:
            return ClaimVerdictItem(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=VerdictType.INSUFFICIENT_EVIDENCE,
                confidence=0.15,
                confidence_level=ConfidenceLevel.LOW,
                evidence_strength=EvidenceStrength.INSUFFICIENT,
                explanation="No verifiable sources or empirical evidence were retrieved for this claim.",
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
                contextual_evidence_ids=[],
                limitations=["No sources or evidence retrieved for evaluation."],
                methodology_version="truthlens-v1.0",
                generated_at=datetime.now(timezone.utc)
            )

        # Build prompt
        prompt = self._build_verdict_prompt(
            claim_text=claim_text,
            evidence=evidence,
            comparisons=comparisons,
            claim_entities=claim_entities,
            claim_numbers=claim_numbers,
            claim_dates=claim_dates
        )

        raw_json_str = self._call_llm(prompt)
        return self._parse_verdict_json(
            raw_json_str=raw_json_str,
            claim_id=claim_id,
            claim_text=claim_text,
            evidence=evidence,
            comparisons=comparisons
        )

    def _build_verdict_prompt(
        self,
        claim_text: str,
        evidence: List[ExtractedEvidenceItem],
        comparisons: List[SourceComparisonItem],
        claim_entities: Optional[List[str]] = None,
        claim_numbers: Optional[List[str]] = None,
        claim_dates: Optional[List[str]] = None,
    ) -> str:
        lines = [
            f"ATOMIC CLAIM TO VERIFY (ID: {claim_text}):",
            f'"{claim_text}"',
            ""
        ]
        if claim_entities:
            lines.append(f"Identified Entities: {', '.join(claim_entities)}")
        if claim_numbers:
            lines.append(f"Identified Quantities/Numbers: {', '.join(claim_numbers)}")
        if claim_dates:
            lines.append(f"Identified Dates/Times: {', '.join(claim_dates)}")

        lines.append("\nAVAILABLE EXTRACTED EVIDENCE ITEMS:")
        for idx, ev in enumerate(evidence, 1):
            e_id = ev.id if ev.id is not None else idx
            lines.append(
                f"[Evidence ID: {e_id}] Type: {ev.evidence_type.value} | Relevance: {ev.relevance.value} | Confidence: {ev.confidence_in_extraction:.2f}\n"
                f"Source: {ev.publisher or 'Unknown Publisher'} ({ev.url})\n"
                f"Date: {ev.publish_date or 'Unknown Date'}\n"
                f'Verbatim Passage: "{ev.evidence_text or ev.snippet}"\n'
                f"Stance Rationale: {ev.explanation or 'None'}\n"
            )

        if comparisons:
            lines.append("SOURCE COMPARISONS & CROSS-VERIFICATION:")
            for comp in comparisons:
                lines.append(
                    f"- Source {comp.source_id_a} vs Source {comp.source_id_b}: "
                    f"Relationship: {comp.source_relationship.value}, Consistency: {comp.consistency_type.value}. "
                    f"Notes: {comp.comparison_notes or 'None'}"
                )

        return "\n".join(lines)

    def _call_llm(self, user_prompt: str) -> str:
        if self.provider == "openai":
            return self._call_openai(user_prompt)
        elif self.provider == "gemini":
            return self._call_gemini(user_prompt)
        elif self.provider == "ollama":
            return self._call_ollama(user_prompt)
        else:
            return self._call_openai(user_prompt)

    def _call_openai(self, user_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": VERDICT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _call_gemini(self, user_prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model or 'gemini-1.5-flash'}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "system_instruction": {
                "parts": [{"text": VERDICT_SYSTEM_PROMPT}]
            },
            "contents": [
                {"parts": [{"text": user_prompt}]}
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_ollama(self, user_prompt: str) -> str:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model or "llama3",
            "system": VERDICT_SYSTEM_PROMPT,
            "prompt": user_prompt,
            "format": "json",
            "stream": False
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["response"]

    def _parse_verdict_json(
        self,
        raw_json_str: str,
        claim_id: int,
        claim_text: str,
        evidence: List[ExtractedEvidenceItem],
        comparisons: List[SourceComparisonItem]
    ) -> ClaimVerdictItem:
        try:
            parsed = json.loads(raw_json_str)
        except json.JSONDecodeError:
            if "```" in raw_json_str:
                clean_str = raw_json_str.split("```")[1]
                if clean_str.startswith("json"):
                    clean_str = clean_str[4:]
                parsed = json.loads(clean_str.strip())
            else:
                raise

        # 1. Parse verdict type
        raw_verdict = (parsed.get("verdict") or "UNVERIFIED").upper()
        try:
            verdict = VerdictType(raw_verdict)
            if verdict == VerdictType.MIXED:
                verdict = VerdictType.MISLEADING
        except ValueError:
            verdict = VerdictType.UNVERIFIED

        # 2. Strict ID verification (enforce valid IDs from input evidence only)
        valid_ids: Set[int] = {e.id for e in evidence if e.id is not None}
        
        supporting_ids = [i for i in parsed.get("supporting_evidence_ids", []) if isinstance(i, int) and i in valid_ids]
        contradicting_ids = [i for i in parsed.get("contradicting_evidence_ids", []) if isinstance(i, int) and i in valid_ids]
        contextual_ids = [i for i in parsed.get("contextual_evidence_ids", []) if isinstance(i, int) and i in valid_ids]

        # If LLM failed to populate IDs, fallback to evidence types from items
        if not supporting_ids and not contradicting_ids and not contextual_ids:
            for ev in evidence:
                if ev.id is not None:
                    if ev.evidence_type == EvidenceType.SUPPORTING:
                        supporting_ids.append(ev.id)
                    elif ev.evidence_type == EvidenceType.CONTRADICTING:
                        contradicting_ids.append(ev.id)
                    elif ev.evidence_type == EvidenceType.CONTEXTUAL:
                        contextual_ids.append(ev.id)

        # 3. Transparent mathematical evidence confidence score
        confidence_score, confidence_level, _ = EvidenceEvaluator.calculate_confidence_score(
            evidence=evidence,
            comparisons=comparisons,
            verdict=verdict
        )
        evidence_strength = EvidenceEvaluator.evaluate_evidence_strength(evidence, comparisons)

        # 4. Limitations
        llm_limitations = parsed.get("limitations") or []
        if isinstance(llm_limitations, str):
            llm_limitations = [llm_limitations]
        system_limitations = EvidenceEvaluator.detect_limitations(evidence, comparisons)
        all_limitations = list(dict.fromkeys(llm_limitations + system_limitations))

        explanation = (parsed.get("explanation") or "").strip()
        if not explanation:
            explanation = f"Evaluated based on {len(evidence)} retrieved evidence item(s)."

        return ClaimVerdictItem(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=verdict,
            confidence=confidence_score,
            confidence_level=confidence_level,
            evidence_strength=evidence_strength,
            explanation=explanation,
            supporting_evidence_ids=supporting_ids,
            contradicting_evidence_ids=contradicting_ids,
            contextual_evidence_ids=contextual_ids,
            limitations=all_limitations,
            methodology_version="truthlens-v1.0",
            generated_at=datetime.now(timezone.utc)
        )
