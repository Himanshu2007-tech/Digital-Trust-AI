import logging
from typing import Optional, List

from app.verification.evidence.models import ExtractedEvidenceItem, SourceComparisonItem
from app.verification.verdict.base import VerdictEngine
from app.verification.verdict.models import ClaimVerdictItem
from app.verification.verdict.rule_based import RuleBasedVerdictEngine
from app.verification.verdict.llm import LLMVerdictEngine

logger = logging.getLogger(__name__)


class HybridVerdictEngine(VerdictEngine):
    """
    Hybrid Verdict Engine:
    Attempts structured LLM verdict synthesis when configured;
    seamlessly falls back to deterministic RuleBasedVerdictEngine on failure,
    missing API credentials, or network errors.
    """

    def __init__(
        self,
        rule_engine: Optional[RuleBasedVerdictEngine] = None,
        llm_engine: Optional[LLMVerdictEngine] = None
    ):
        self.rule_engine = rule_engine or RuleBasedVerdictEngine()
        self.llm_engine = llm_engine or LLMVerdictEngine()

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
        if self.llm_engine.is_configured():
            try:
                logger.info(f"Executing LLM verdict synthesis for claim {claim_id}...")
                result = self.llm_engine.determine_verdict(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    evidence=evidence,
                    comparisons=comparisons,
                    claim_entities=claim_entities,
                    claim_numbers=claim_numbers,
                    claim_dates=claim_dates,
                )
                return result
            except Exception as e:
                logger.warning(
                    f"LLM verdict synthesis failed for claim {claim_id} ({e}). "
                    f"Falling back gracefully to RuleBasedVerdictEngine."
                )

        logger.info(f"Using RuleBasedVerdictEngine for claim {claim_id}.")
        return self.rule_engine.determine_verdict(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence=evidence,
            comparisons=comparisons,
            claim_entities=claim_entities,
            claim_numbers=claim_numbers,
            claim_dates=claim_dates,
        )
