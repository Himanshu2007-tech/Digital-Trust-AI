import logging
from typing import Optional, List

from app.verification.evidence.base import EvidenceAnalyzer
from app.verification.evidence.models import ExtractedEvidenceItem
from app.verification.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.verification.evidence.llm import LLMEvidenceAnalyzer

logger = logging.getLogger(__name__)


class HybridEvidenceAnalyzer(EvidenceAnalyzer):
    """
    Hybrid Evidence Analyzer:
    Attempts structured LLM analysis if configured and available;
    seamlessly falls back to deterministic RuleBasedEvidenceAnalyzer on error,
    timeout, or missing credentials.
    """

    def __init__(
        self,
        rule_analyzer: Optional[RuleBasedEvidenceAnalyzer] = None,
        llm_analyzer: Optional[LLMEvidenceAnalyzer] = None
    ):
        self.rule_analyzer = rule_analyzer or RuleBasedEvidenceAnalyzer()
        self.llm_analyzer = llm_analyzer or LLMEvidenceAnalyzer()

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
        if self.llm_analyzer.is_configured():
            try:
                logger.info(f"Executing LLM evidence analysis for claim {claim_id}...")
                item = self.llm_analyzer.analyze_evidence(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    source_id=source_id,
                    source_title=source_title,
                    source_snippet=source_snippet,
                    source_url=source_url,
                    source_domain=source_domain,
                    source_publisher=source_publisher,
                    publish_date=publish_date,
                    claim_entities=claim_entities,
                    claim_numbers=claim_numbers,
                    claim_dates=claim_dates,
                )
                item.extraction_method = "llm"
                return item
            except Exception as exc:
                logger.warning(
                    f"LLM evidence analysis encountered an error ({type(exc).__name__}: {exc}). "
                    f"Falling back safely to RuleBasedEvidenceAnalyzer."
                )

        # Fallback to rule-based analyzer
        item = self.rule_analyzer.analyze_evidence(
            claim_id=claim_id,
            claim_text=claim_text,
            source_id=source_id,
            source_title=source_title,
            source_snippet=source_snippet,
            source_url=source_url,
            source_domain=source_domain,
            source_publisher=source_publisher,
            publish_date=publish_date,
            claim_entities=claim_entities,
            claim_numbers=claim_numbers,
            claim_dates=claim_dates,
        )
        item.extraction_method = "rule_based"
        return item
