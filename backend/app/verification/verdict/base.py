from abc import ABC, abstractmethod
from typing import List, Optional
from app.verification.evidence.models import ExtractedEvidenceItem, SourceComparisonItem
from app.verification.verdict.models import ClaimVerdictItem


class VerdictEngine(ABC):
    """
    Abstract interface for claim verification and verdict synthesis engines.
    Synthesizes extracted evidence, source comparisons, and empirical metadata
    into an explainable, non-hallucinatory verdict classification.
    """

    @abstractmethod
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
        """
        Determines the final verification verdict (SUPPORTED, CONTRADICTED, MISLEADING,
        UNVERIFIED, INSUFFICIENT_EVIDENCE) and calculates evidence confidence and explanation.
        """
        pass
