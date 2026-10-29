"""
TruthLens AI - Text Input & Claim Extraction Engine (Part 3)
Provides:
- Preprocessing and sentence segmentation
- Domain models and enums for claims
- Deterministic Rule-Based Claim Extractor
- Non-hallucinatory LLM Claim Extractor
- Resilient Hybrid Claim Extractor
"""

from app.verification.domain_models import (
    ClaimType,
    Verifiability,
    Importance,
    ExtractedClaimItem
)
from app.verification.preprocessing import (
    clean_text,
    segment_sentences
)
from app.verification.extractors.base import ClaimExtractor
from app.verification.extractors.rule_based import RuleBasedClaimExtractor
from app.verification.extractors.llm import LLMClaimExtractor
from app.verification.extractors.hybrid import HybridClaimExtractor

__all__ = [
    "ClaimType",
    "Verifiability",
    "Importance",
    "ExtractedClaimItem",
    "clean_text",
    "segment_sentences",
    "ClaimExtractor",
    "RuleBasedClaimExtractor",
    "LLMClaimExtractor",
    "HybridClaimExtractor",
]
