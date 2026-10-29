import json
import logging
import uuid
from typing import List, Optional
import httpx

from app.core.config import settings
from app.verification.domain_models import ExtractedClaimItem, ClaimType, Verifiability, Importance
from app.verification.extractors.base import ClaimExtractor

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are the text claim extraction engine for TruthLens AI, a professional fake-news and multimedia verification platform.

Your task is to analyze the input text and extract individual, atomic, verifiable claims.

CRITICAL NON-HALLUCINATION RULES:
1. ONLY extract claims directly stated in or explicitly implied by the input text.
2. NEVER invent, fabricate, assume, or extrapolate facts, sources, numbers, or dates not present in the input.
3. DO NOT attempt to verify or judge whether the claim is true or false. Verification happens in a later phase.
4. Decompose compound sentences into separate, standalone atomic claims (e.g., "India launched satellite in 2024 and it entered orbit" -> 2 atomic claims).
5. For each claim, extract associated entities, numbers/currencies/percentages, dates, locations, and source attributions.
6. Classify each claim:
   - claim_type: FACTUAL, NUMERICAL, TEMPORAL, LOCATION, EVENT, PERSON/ORGANIZATION, POLICY, CAUSAL, COMPARATIVE, QUOTE/ATTRIBUTION, OPINION, NON_VERIFIABLE
   - verifiability: VERIFIABLE, UNVERIFIABLE, SUBJECTIVE
   - importance: HIGH, MEDIUM, LOW

Output MUST be a valid JSON object strictly matching this schema:
{
  "claims": [
    {
      "text": "Clear standalone statement of the atomic claim",
      "normalized_text": "Normalized sentence case representation",
      "claim_type": "FACTUAL",
      "verifiability": "VERIFIABLE",
      "importance": "HIGH",
      "entities": ["entity1", "entity2"],
      "dates": ["date1"],
      "locations": ["location1"],
      "numbers": ["10%", "500 million"],
      "source_attributions": ["official source"],
      "original_sentence": "Sentence from input text containing this claim"
    }
  ]
}
"""


class LLMClaimExtractor(ClaimExtractor):
    """
    Provider-agnostic LLM Claim Extractor.
    Supports OpenAI, Gemini, Ollama, or OpenAI-compatible completion endpoints.
    Strictly constrained to non-hallucinatory atomic claim decomposition.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower() if settings.LLM_PROVIDER else "none"
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        """Returns True if an LLM provider and API key are configured."""
        if self.provider in ("none", ""):
            return False
        if self.provider == "ollama":
            return True  # Ollama may not require an API key locally
        return bool(self.api_key)

    def extract_claims(self, text: str, context: Optional[str] = None) -> List[ExtractedClaimItem]:
        """
        Calls the configured LLM provider to extract atomic claims in structured JSON format.
        """
        if not self.is_configured():
            raise ValueError(f"LLM provider '{self.provider}' is not configured or missing API key.")

        user_content = f"INPUT TEXT:\n\"\"\"\n{text}\n\"\"\""
        if context:
            user_content += f"\n\nCONTEXT / SOURCE:\n{context}"

        raw_json_str = self._call_llm(user_content)
        return self._parse_claims_json(raw_json_str, fallback_sentence=text)

    def _call_llm(self, user_prompt: str) -> str:
        """Dispatches to the appropriate provider client."""
        if self.provider == "openai":
            return self._call_openai(user_prompt)
        elif self.provider == "gemini":
            return self._call_gemini(user_prompt)
        elif self.provider == "ollama":
            return self._call_ollama(user_prompt)
        else:
            # Default to generic OpenAI-compatible endpoint
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
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
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
                "parts": [{"text": EXTRACTION_SYSTEM_PROMPT}]
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
            "system": EXTRACTION_SYSTEM_PROMPT,
            "prompt": user_prompt,
            "format": "json",
            "stream": False
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["response"]

    def _parse_claims_json(self, raw_json: str, fallback_sentence: str) -> List[ExtractedClaimItem]:
        """Parses LLM JSON response and normalizes to ExtractedClaimItem domain models."""
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as err:
            logger.warning(f"Failed to parse LLM JSON response: {err}")
            # Try to locate JSON substring if surrounded by markdown code fences
            if "```" in raw_json:
                clean_str = raw_json.split("```")[1]
                if clean_str.startswith("json"):
                    clean_str = clean_str[4:]
                parsed = json.loads(clean_str.strip())
            else:
                raise

        claims_list = parsed.get("claims", [])
        results: List[ExtractedClaimItem] = []

        for item in claims_list:
            text = (item.get("text") or "").strip()
            if not text:
                continue

            # Safe enum parsing
            raw_type = (item.get("claim_type") or "FACTUAL").upper()
            try:
                claim_type = ClaimType(raw_type)
            except ValueError:
                claim_type = ClaimType.FACTUAL

            raw_verif = (item.get("verifiability") or "VERIFIABLE").upper()
            try:
                verifiability = Verifiability(raw_verif)
            except ValueError:
                verifiability = Verifiability.VERIFIABLE

            raw_imp = (item.get("importance") or "MEDIUM").upper()
            try:
                importance = Importance(raw_imp)
            except ValueError:
                importance = Importance.MEDIUM

            results.append(ExtractedClaimItem(
                id=str(uuid.uuid4()),
                text=text,
                normalized_text=item.get("normalized_text") or text,
                claim_type=claim_type,
                verifiability=verifiability,
                importance=importance,
                entities=item.get("entities") or [],
                dates=item.get("dates") or [],
                locations=item.get("locations") or [],
                numbers=item.get("numbers") or [],
                source_attributions=item.get("source_attributions") or [],
                original_sentence=item.get("original_sentence") or fallback_sentence,
                extraction_method="llm"
            ))

        return results
