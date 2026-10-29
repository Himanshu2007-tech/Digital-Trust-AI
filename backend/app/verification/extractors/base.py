from abc import ABC, abstractmethod
from typing import List, Optional
from app.verification.domain_models import ExtractedClaimItem


class ClaimExtractor(ABC):
    """
    Abstract interface for claim extraction engines.
    Allows swappable implementations (rule-based, LLM, or hybrid).
    """

    @abstractmethod
    def extract_claims(self, text: str, context: Optional[str] = None) -> List[ExtractedClaimItem]:
        """
        Decomposes input text into structured, atomic, verifiable claims.

        Args:
            text (str): Input paragraph, article, or statement.
            context (Optional[str]): Optional metadata, origin, or speaker context.

        Returns:
            List[ExtractedClaimItem]: List of structured atomic claims.
        """
        pass
