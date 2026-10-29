"""TruthLens AI Part 5: Evidence Extraction and Source Comparison Package."""

from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem,
    SourceComparisonItem,
)
from app.verification.evidence.base import EvidenceAnalyzer
from app.verification.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.verification.evidence.llm import LLMEvidenceAnalyzer
from app.verification.evidence.hybrid import HybridEvidenceAnalyzer
from app.verification.evidence.comparator import SourceComparator
from app.verification.evidence.service import EvidenceAnalysisService

__all__ = [
    "EvidenceType",
    "EvidenceRelevance",
    "SourceRelationship",
    "EvidenceConsistency",
    "ExtractedEvidenceItem",
    "SourceComparisonItem",
    "EvidenceAnalyzer",
    "RuleBasedEvidenceAnalyzer",
    "LLMEvidenceAnalyzer",
    "HybridEvidenceAnalyzer",
    "SourceComparator",
    "EvidenceAnalysisService",
]
