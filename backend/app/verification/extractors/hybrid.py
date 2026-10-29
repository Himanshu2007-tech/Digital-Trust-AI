import logging
from typing import List, Optional

from app.verification.domain_models import ExtractedClaimItem
from app.verification.extractors.base import ClaimExtractor
from app.verification.extractors.rule_based import RuleBasedClaimExtractor
from app.verification.extractors.llm import LLMClaimExtractor

logger = logging.getLogger(__name__)


class HybridClaimExtractor(ClaimExtractor):
    """
    Orchestrates claim extraction using a hybrid approach:
    1. If LLM provider and API credentials are configured, attempts structured LLM extraction.
    2. If LLM is not configured, times out, or raises an error, gracefully falls back
       to the deterministic RuleBasedClaimExtractor.
    3. Guarantees deterministic, production-grade reliability without downtime.
    """

    def __init__(self, rule_extractor: Optional[RuleBasedClaimExtractor] = None,
                 llm_extractor: Optional[LLMClaimExtractor] = None):
        self.rule_extractor = rule_extractor or RuleBasedClaimExtractor()
        self.llm_extractor = llm_extractor or LLMClaimExtractor()

    def extract_claims(self, text: str, context: Optional[str] = None) -> List[ExtractedClaimItem]:
        """
        Extracts atomic claims using LLM if available, falling back cleanly to rule-based analysis.
        """
        if self.llm_extractor.is_configured():
            try:
                logger.info("Attempting claim extraction via LLM extractor...")
                llm_claims = self.llm_extractor.extract_claims(text, context)
                if llm_claims:
                    logger.info(f"LLM extraction succeeded: {len(llm_claims)} claims extracted.")
                    return llm_claims
                else:
                    logger.warning("LLM extractor returned empty list, falling back to rule-based.")
            except Exception as exc:
                logger.warning(
                    f"LLM extraction encountered an error ({type(exc).__name__}: {exc}). "
                    f"Falling back safely to RuleBasedClaimExtractor."
                )

        # Fallback to rule-based extractor
        logger.info("Executing RuleBasedClaimExtractor fallback.")
        return self.rule_extractor.extract_claims(text, context)
