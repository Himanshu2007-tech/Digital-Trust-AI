from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.verification.evidence.models import ExtractedEvidenceItem


class EvidenceAnalyzer(ABC):
    """
    Abstract interface for evidence extraction and stance analysis engines.
    Converts a claim and a retrieved web source into structured, non-hallucinatory evidence.
    """

    @abstractmethod
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
        """
        Extracts relevant factual passages from the source and determines the evidence stance
        relative to the claim (SUPPORTING, CONTRADICTING, CONTEXTUAL, INSUFFICIENT).
        """
        pass
