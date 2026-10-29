import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import settings
from app.verification.evidence.base import EvidenceAnalyzer
from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    ExtractedEvidenceItem
)

logger = logging.getLogger(__name__)

EVIDENCE_SYSTEM_PROMPT = """You are the Evidence Extraction & Stance Analysis Engine for TruthLens AI.
Your role is to extract factual evidence from a given source and determine how it relates to an atomic claim.

CRITICAL NON-HALLUCINATION RULES:
1. ONLY analyze the provided CLAIM and SOURCE TEXT (Title + Snippet/Content).
2. DO NOT browse the internet or use outside knowledge.
3. NEVER fabricate, alter, or synthesize quotations. The "evidence_text" field MUST be an EXACT verbatim passage/substring present in the source text.
4. DO NOT issue a final truth verdict (TRUE / FALSE / FAKE). Verdicts belong to a future phase.
5. Classify the relationship into exactly one of these categories:
   - "SUPPORTING": Source directly corroborates or confirms the claim.
   - "CONTRADICTING": Source directly refutes, contradicts, states opposite facts, numbers, or dates.
   - "CONTEXTUAL": Source discusses the same background, topic, or entity, but does not directly confirm or refute the claim.
   - "INSUFFICIENT": Source lacks enough information or relevance to determine a relationship.
6. Relevance must be "HIGH", "MEDIUM", or "LOW".
7. Confidence ("confidence_in_extraction") is a float 0.0 to 1.0 reflecting how confident the extraction and stance interpretation is. It is NOT a claim truth score.

Return a JSON object with this exact structure:
{
  "evidence_text": "Verbatim quote directly from the source snippet",
  "evidence_type": "SUPPORTING | CONTRADICTING | CONTEXTUAL | INSUFFICIENT",
  "relevance": "HIGH | MEDIUM | LOW",
  "confidence_in_extraction": 0.95,
  "explanation": "Concise factual reason for the classified relationship"
}
"""


class LLMEvidenceAnalyzer(EvidenceAnalyzer):
    """
    LLM-powered evidence analyzer adhering strictly to non-hallucinatory extraction constraints.
    Supports OpenAI, Gemini, Ollama, and compatible endpoints.
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

    def analyze_evidence(
        self,
        claim_id: int,
        claim_text: str,
        source_id: Optional[int],
        source_title: Optional[str],
        source_snippet: Optional[str],
        source_url: str,
        source_domain: Optional[str] = None,
        source_publisher: Optional[str] = None,
        publish_date: Optional[str] = None,
        claim_entities: Optional[List[str]] = None,
        claim_numbers: Optional[List[str]] = None,
        claim_dates: Optional[List[str]] = None,
    ) -> ExtractedEvidenceItem:
        if not self.is_configured():
            raise ValueError(f"LLM provider '{self.provider}' is not configured.")

        combined_source = ""
        if source_title:
            combined_source += f"Title: {source_title}\n"
        if source_publisher:
            combined_source += f"Publisher: {source_publisher}\n"
        if publish_date:
            combined_source += f"Date: {publish_date}\n"
        if source_snippet:
            combined_source += f"Snippet/Content: {source_snippet}\n"

        prompt = f"""CLAIM TO EVALUATE:
\"\"\"{claim_text}\"\"\"

SOURCE INFORMATION:
\"\"\"{combined_source.strip()}\"\"\"
"""
        raw_json_str = self._call_llm(prompt)
        return self._parse_evidence_json(
            raw_json_str=raw_json_str,
            claim_id=claim_id,
            source_id=source_id,
            source_url=source_url,
            source_title=source_title,
            source_snippet=source_snippet or "",
            source_domain=source_domain,
            source_publisher=source_publisher,
            publish_date=publish_date
        )

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
                {"role": "system", "content": EVIDENCE_SYSTEM_PROMPT},
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
                "parts": [{"text": EVIDENCE_SYSTEM_PROMPT}]
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
            "system": EVIDENCE_SYSTEM_PROMPT,
            "prompt": user_prompt,
            "format": "json",
            "stream": False
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["response"]

    def _parse_evidence_json(
        self,
        raw_json_str: str,
        claim_id: int,
        source_id: Optional[int],
        source_url: str,
        source_title: Optional[str],
        source_snippet: str,
        source_domain: Optional[str],
        source_publisher: Optional[str],
        publish_date: Optional[str]
    ) -> ExtractedEvidenceItem:
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

        evidence_text = (parsed.get("evidence_text") or source_snippet or "").strip()
        raw_type = (parsed.get("evidence_type") or "CONTEXTUAL").upper()
        try:
            evidence_type = EvidenceType(raw_type)
        except ValueError:
            evidence_type = EvidenceType.CONTEXTUAL

        raw_rel = (parsed.get("relevance") or "MEDIUM").upper()
        try:
            relevance = EvidenceRelevance(raw_rel)
        except ValueError:
            relevance = EvidenceRelevance.MEDIUM

        confidence = float(parsed.get("confidence_in_extraction") or 0.85)
        confidence = max(0.0, min(1.0, confidence))

        explanation = parsed.get("explanation") or "Evaluated via structured LLM stance analysis."

        return ExtractedEvidenceItem(
            claim_id=claim_id,
            source_id=source_id,
            evidence_text=evidence_text,
            snippet=evidence_text,
            evidence_type=evidence_type,
            direction=evidence_type.value,
            relevance=relevance,
            relevance_score=0.9 if relevance == EvidenceRelevance.HIGH else (0.6 if relevance == EvidenceRelevance.MEDIUM else 0.3),
            confidence_in_extraction=confidence,
            stance_confidence=0.9,
            source_location="snippet",
            extraction_method="llm",
            extracted_at=datetime.now(timezone.utc),
            url=source_url,
            article_title=source_title,
            publisher=source_publisher,
            domain=source_domain,
            publish_date=publish_date,
            explanation=explanation
        )
