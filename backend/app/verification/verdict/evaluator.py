from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import re

from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem,
    SourceComparisonItem
)
from app.verification.verdict.models import (
    VerdictType,
    EvidenceStrength,
    ConfidenceLevel
)

# Source Authority Mapping (Empirical evidentiary value, NOT arbitrary truth percentage)
SOURCE_QUALITY_WEIGHTS = {
    "PRIMARY": 1.00,
    "OFFICIAL": 1.00,
    "FACT_CHECK": 0.95,
    "RELIABLE_NEWS": 0.85,
    "SECONDARY": 0.65,
    "UNKNOWN": 0.40,
    "BLOG": 0.35,
    "SOCIAL_MEDIA": 0.30,
}


class EvidenceEvaluator:
    """
    Multi-dimensional evidence evaluator.
    Computes evidence directness, source quality, reporting independence,
    and the transparent mathematical evidence confidence score.
    """

    @classmethod
    def evaluate_source_quality(cls, source_type: Optional[str]) -> float:
        st = (source_type or "UNKNOWN").upper()
        return SOURCE_QUALITY_WEIGHTS.get(st, 0.40)

    @classmethod
    def get_item_source_quality(cls, item: ExtractedEvidenceItem) -> float:
        domain = (item.domain or "").lower()
        if not domain and item.url:
            from urllib.parse import urlparse
            domain = (urlparse(item.url).netloc or "").lower()
        if (
            domain.endswith(".gov")
            or ".gov." in domain
            or domain.endswith(".nic.in")
            or ".nic." in domain
            or "rbi.org" in domain
            or "who.int" in domain
            or "isro.gov" in domain
            or "pib.gov" in domain
            or "un.org" in domain
            or "nasa.gov" in domain
            or "cdc.gov" in domain
        ):
            return 1.0
        if any(fc in domain for fc in ["factcheck", "altnews", "boomlive", "snopes", "politifact", "vishvasnews", "fullfact"]):
            return 0.95
        if any(nw in domain for nw in [
            "reuters", "apnews", "bloomberg", "thehindu", "indianexpress", "bbc",
            "timesofindia", "indiatimes", "ptinews", "afp", "nytimes", "wsj", "theguardian", "hindustantimes", "ndtv"
        ]):
            return 0.85
        if any(bl in domain for bl in ["wordpress", "blogspot", "medium", "substack", "tumblr", "weebly", "blogger", "blog"]):
            return 0.35
        if any(sm in domain for sm in ["twitter", "x.com", "facebook", "tiktok", "instagram", "reddit", "telegram", "threads"]):
            return 0.30
        return 0.50

    @classmethod
    def evaluate_evidence_strength(
        cls,
        evidence: List[ExtractedEvidenceItem],
        comparisons: List[SourceComparisonItem]
    ) -> EvidenceStrength:
        if not evidence:
            return EvidenceStrength.INSUFFICIENT

        has_high_rel = any(e.relevance == EvidenceRelevance.HIGH for e in evidence)
        has_direct_stance = any(e.evidence_type in (EvidenceType.SUPPORTING, EvidenceType.CONTRADICTING) for e in evidence)
        independent_sources = any(c.source_relationship == SourceRelationship.INDEPENDENT for c in comparisons)

        if has_high_rel and has_direct_stance and (independent_sources or len(evidence) >= 2):
            return EvidenceStrength.STRONG
        elif has_direct_stance or (has_high_rel and len(evidence) >= 1):
            return EvidenceStrength.MODERATE
        elif any(e.evidence_type == EvidenceType.CONTEXTUAL for e in evidence):
            return EvidenceStrength.WEAK
        return EvidenceStrength.INSUFFICIENT

    @classmethod
    def calculate_confidence_score(
        cls,
        evidence: List[ExtractedEvidenceItem],
        comparisons: List[SourceComparisonItem],
        verdict: VerdictType
    ) -> Tuple[float, ConfidenceLevel, Dict[str, float]]:
        """
        Calculates the transparent mathematical evidence confidence score:
        C = 0.25 * S_direct + 0.25 * S_quality + 0.20 * S_indep + 0.20 * S_consist + 0.10 * S_temporal

        Note: Represents strength of available evidence underpinning classification,
        NOT statistical probability that the claim is true.
        """
        if not evidence or verdict in (VerdictType.INSUFFICIENT_EVIDENCE, VerdictType.UNVERIFIED):
            # For unverified/insufficient claims, confidence in having proved truth/falsity is low
            if not evidence:
                score = 0.15
            else:
                score = 0.35
            return score, ConfidenceLevel.LOW, {
                "directness": 0.1,
                "source_quality": 0.2,
                "independence": 0.2,
                "consistency": 0.2,
                "temporal": 0.2
            }

        # 1. Directness & Specificity (0.0 to 1.0)
        direct_items = [e for e in evidence if e.evidence_type in (EvidenceType.SUPPORTING, EvidenceType.CONTRADICTING)]
        if any(e.relevance == EvidenceRelevance.HIGH and e.confidence_in_extraction >= 0.90 for e in direct_items):
            s_direct = 1.0
        elif direct_items:
            s_direct = 0.80
        elif any(e.evidence_type == EvidenceType.CONTEXTUAL for e in evidence):
            s_direct = 0.50
        else:
            s_direct = 0.25

        # 2. Source Authority & Quality (0.0 to 1.0)
        qualities = [e.relevance_score for e in direct_items] if direct_items else [e.relevance_score for e in evidence]
        s_quality = sum(qualities) / max(len(qualities), 1)

        # 3. Source Independence (0.0 to 1.0)
        # Anti-syndication discount: multiple wire copies should not inflate confidence
        pairwise = [c for c in comparisons if c.comparison_type == "PAIRWISE"]
        if any(p.source_relationship == SourceRelationship.INDEPENDENT for p in pairwise):
            s_indep = 1.0
        elif len(evidence) == 1:
            s_indep = 0.70  # Single reliable source
        elif any(p.source_relationship in (SourceRelationship.POSSIBLY_SYNDICATED, SourceRelationship.DUPLICATE) for p in pairwise):
            s_indep = 0.60  # Syndication discount
        else:
            s_indep = 0.50

        # 4. Evidence Consistency (0.0 to 1.0)
        supp_count = sum(1 for e in evidence if e.evidence_type == EvidenceType.SUPPORTING)
        contra_count = sum(1 for e in evidence if e.evidence_type == EvidenceType.CONTRADICTING)

        if supp_count > 0 and contra_count > 0:
            # Unresolved contradiction penalty
            s_consist = 0.35
        elif supp_count > 0 or contra_count > 0:
            s_consist = 1.0
        else:
            s_consist = 0.50

        # 5. Temporal Relevance (0.0 to 1.0)
        dated_evidence = [e for e in evidence if e.publish_date]
        if len(dated_evidence) >= len(evidence) * 0.5:
            s_temporal = 0.90
        elif dated_evidence:
            s_temporal = 0.75
        else:
            s_temporal = 0.60

        # Formula synthesis
        raw_score = (
            0.25 * s_direct +
            0.25 * s_quality +
            0.20 * s_indep +
            0.20 * s_consist +
            0.10 * s_temporal
        )
        score = max(0.10, min(0.98, round(raw_score, 2)))

        if score >= 0.75:
            level = ConfidenceLevel.HIGH
        elif score >= 0.50:
            level = ConfidenceLevel.MODERATE
        else:
            level = ConfidenceLevel.LOW

        breakdown = {
            "directness": round(s_direct, 2),
            "source_quality": round(s_quality, 2),
            "independence": round(s_indep, 2),
            "consistency": round(s_consist, 2),
            "temporal": round(s_temporal, 2)
        }
        return score, level, breakdown

    @classmethod
    def identify_limitations(
        cls,
        evidence: List[ExtractedEvidenceItem],
        comparisons: List[SourceComparisonItem]
    ) -> List[str]:
        limitations = []
        if not evidence:
            limitations.append("No publicly discoverable web sources were indexed for this specific claim.")
            return limitations

        # Check for missing publication dates
        missing_dates = sum(1 for e in evidence if not e.publish_date)
        if missing_dates > 0:
            limitations.append(f"{missing_dates} of {len(evidence)} source(s) did not report verifiable publication dates.")

        # Check for syndicated sources
        syndicated = [c for c in comparisons if c.source_relationship in (SourceRelationship.POSSIBLY_SYNDICATED, SourceRelationship.DUPLICATE)]
        if syndicated:
            limitations.append("Multiple retrieved articles exhibit wire syndication or text reproduction and were not counted as separate investigations.")

        # Check for single source
        if len(evidence) == 1:
            limitations.append("Only a single source was identified; independent cross-corroboration was not possible.")

        # Check for snippet vs full text
        limitations.append("Evidence was evaluated from live search passages and metadata; full paywalled or archival content was not inspected.")

        # Check for conflicting evidence
        supp = sum(1 for e in evidence if e.evidence_type == EvidenceType.SUPPORTING)
        contra = sum(1 for e in evidence if e.evidence_type == EvidenceType.CONTRADICTING)
        if supp > 0 and contra > 0:
            limitations.append("Directly contradictory reporting was discovered across retrieved publishers.")

        return limitations

    detect_limitations = identify_limitations

