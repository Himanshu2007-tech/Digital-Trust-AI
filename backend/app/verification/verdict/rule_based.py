from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem,
    SourceComparisonItem
)
from app.verification.verdict.base import VerdictEngine
from app.verification.verdict.models import (
    VerdictType,
    EvidenceStrength,
    ConfidenceLevel,
    ClaimVerdictItem
)
from app.verification.verdict.evaluator import EvidenceEvaluator


class RuleBasedVerdictEngine(VerdictEngine):
    """
    Deterministic, transparent verdict engine.
    Applies multi-source evidence synthesis, anti-syndication checks,
    and non-majority-voting principles to reach an explainable verdict.
    """

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
        supp_items = [e for e in evidence if e.evidence_type == EvidenceType.SUPPORTING]
        contra_items = [e for e in evidence if e.evidence_type == EvidenceType.CONTRADICTING]
        ctx_items = [e for e in evidence if e.evidence_type == EvidenceType.CONTEXTUAL]
        insuff_items = [e for e in evidence if e.evidence_type == EvidenceType.INSUFFICIENT]

        supp_ids = [e.id for e in supp_items if e.id is not None]
        contra_ids = [e.id for e in contra_items if e.id is not None]
        ctx_ids = [e.id for e in ctx_items if e.id is not None]

        evidence_strength = EvidenceEvaluator.evaluate_evidence_strength(evidence, comparisons)
        limitations = EvidenceEvaluator.identify_limitations(evidence, comparisons)

        # ==========================================
        # 1. No Meaningful Evidence Case
        # ==========================================
        if not evidence or len(insuff_items) == len(evidence):
            verdict = VerdictType.INSUFFICIENT_EVIDENCE
            confidence = 0.15
            conf_level = ConfidenceLevel.LOW
            explanation = (
                "No sufficiently relevant or conclusive evidence was discovered across indexed web sources "
                "to verify or refute this claim."
            )
            return ClaimVerdictItem(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=verdict,
                confidence=confidence,
                confidence_level=conf_level,
                evidence_strength=EvidenceStrength.INSUFFICIENT,
                explanation=explanation,
                supporting_evidence_ids=supp_ids,
                contradicting_evidence_ids=contra_ids,
                contextual_evidence_ids=ctx_ids,
                limitations=limitations,
                methodology_version="truthlens-v1.0",
                generated_at=datetime.now(timezone.utc)
            )

        # ==========================================
        # 2. Contextual / Misleading Detection
        # ==========================================
        # If evidence indicates a real event/topic but with misleading omission or spin
        is_misleading = False
        misleading_reason = ""

        for ctx in ctx_items:
            exp_lower = (ctx.explanation or "").lower()
            text_lower = (ctx.evidence_text or "").lower()
            if any(k in exp_lower or k in text_lower for k in [
                "discussion, proposal, or review rather than a confirmed outcome",
                "under review",
                "considered",
                "draft proposal",
                "internal discussion draft",
                "discussion draft",
                "not been introduced or passed",
                "only proposed",
                "no law has been enacted"
            ]):
                is_misleading = True
                misleading_reason = (
                    "The claim presents an ongoing proposal or discussion as an approved/implemented reality. "
                    "Available evidence indicates the matter was considered or drafted, not finalized."
                )
                break

        # Check numerical distortion: small discrepancy that is partially based on real facts
        if contra_items and not is_misleading:
            for contra in contra_items:
                c_exp = (contra.explanation or "").lower()
                if "numerical conflict" in c_exp and supp_items:
                    # Some sources support the general event, but numbers conflict
                    is_misleading = True
                    misleading_reason = (
                        "The claim correctly identifies the event but misrepresents the precise numbers or statistics "
                        "reported by official/primary documentation."
                    )
                    break

        if is_misleading:
            verdict = VerdictType.MISLEADING
            confidence, conf_level, _ = EvidenceEvaluator.calculate_confidence_score(
                evidence, comparisons, verdict
            )
            return ClaimVerdictItem(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=verdict,
                confidence=confidence,
                confidence_level=conf_level,
                evidence_strength=evidence_strength,
                explanation=misleading_reason,
                supporting_evidence_ids=supp_ids,
                contradicting_evidence_ids=contra_ids,
                contextual_evidence_ids=ctx_ids,
                limitations=limitations,
                methodology_version="truthlens-v1.0",
                generated_at=datetime.now(timezone.utc)
            )

        # ==========================================
        # 3. Direct Contradiction Case
        # ==========================================
        if contra_items and not supp_items:
            verdict = VerdictType.CONTRADICTED
            confidence, conf_level, _ = EvidenceEvaluator.calculate_confidence_score(
                evidence, comparisons, verdict
            )
            top_contra = contra_items[0]
            explanation = (
                f"Reliable evidence directly contradicts the claim: {top_contra.explanation or 'Conflicting assertions identified.'} "
                f"Source ({top_contra.domain or top_contra.publisher or 'publisher'}) explicitly reports contrary facts."
            )
            return ClaimVerdictItem(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=verdict,
                confidence=confidence,
                confidence_level=conf_level,
                evidence_strength=evidence_strength,
                explanation=explanation,
                supporting_evidence_ids=supp_ids,
                contradicting_evidence_ids=contra_ids,
                contextual_evidence_ids=ctx_ids,
                limitations=limitations,
                methodology_version="truthlens-v1.0",
                generated_at=datetime.now(timezone.utc)
            )

        # ==========================================
        # 4. Conflicting Sources (Both Support and Contradiction)
        # ==========================================
        if supp_items and contra_items:
            # Check if resolved by primary vs secondary authority
            max_supp_q = max(EvidenceEvaluator.get_item_source_quality(e) for e in supp_items)
            max_contra_q = max(EvidenceEvaluator.get_item_source_quality(e) for e in contra_items)

            if max_contra_q >= 0.90 and max_supp_q <= 0.60:
                verdict = VerdictType.CONTRADICTED
                explanation = (
                    "Direct contradiction: High-authority official or primary documentation refutes the claim, "
                    "superseding secondary, speculative, or uncorroborated reports."
                )
            elif max_supp_q >= 0.90 and max_contra_q <= 0.60:
                verdict = VerdictType.SUPPORTED
                explanation = (
                    "Supported by official or primary documentation, which decisively outweighs conflicting uncorroborated reports."
                )
            else:
                # Genuine conflict across credible sources -> MIXED
                verdict = VerdictType.MIXED
                explanation = (
                    "Conflicting reporting detected across multiple sources: Substantial corroborating and contradictory "
                    "evidence exists without decisive authoritative consensus."
                )

            confidence, conf_level, _ = EvidenceEvaluator.calculate_confidence_score(
                evidence, comparisons, verdict
            )
            return ClaimVerdictItem(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=verdict,
                confidence=confidence,
                confidence_level=conf_level,
                evidence_strength=evidence_strength,
                explanation=explanation,
                supporting_evidence_ids=supp_ids,
                contradicting_evidence_ids=contra_ids,
                contextual_evidence_ids=ctx_ids,
                limitations=limitations,
                methodology_version="truthlens-v1.0",
                generated_at=datetime.now(timezone.utc)
            )

        # ==========================================
        # 5. Direct Supporting Case
        # ==========================================
        if supp_items and not contra_items:
            official_primary_supp = [
                e for e in supp_items
                if EvidenceEvaluator.get_item_source_quality(e) >= 0.90
            ]
            credible_news_supp = [
                e for e in supp_items
                if EvidenceEvaluator.get_item_source_quality(e) >= 0.70
            ]
            def _get_dom(e) -> str:
                if e.domain:
                    return e.domain.lower()
                if e.url:
                    from urllib.parse import urlparse
                    return (urlparse(e.url).netloc or "").lower()
                return ""

            unique_domains = {_get_dom(e) for e in credible_news_supp if _get_dom(e)}

            # Check if any pairwise comparisons indicate syndication/wire copy
            pairwise = [c for c in comparisons if c.comparison_type == "PAIRWISE"]
            syndicated = any(
                p.source_relationship in (SourceRelationship.POSSIBLY_SYNDICATED, SourceRelationship.DUPLICATE)
                for p in pairwise
            )
            has_independent_corroboration = any(
                p.source_relationship == SourceRelationship.INDEPENDENT for p in pairwise
            ) or (len(unique_domains) >= 2 and not syndicated)

            # Strict Conservative Standards for SUPPORTED:
            # 1. At least 1 primary/official source (e.g. .gov, ISRO, RBI, WHO, PIB) with High/Medium relevance, OR
            # 2. Independent cross-corroboration across at least 2 distinct reputable news outlets with High/Medium relevance, OR
            # 3. A single top-tier primary wire or international news agency (Reuters, AP) with HIGH relevance and >= 0.90 confidence.
            is_supported = False
            if official_primary_supp and any(e.relevance in (EvidenceRelevance.HIGH, EvidenceRelevance.MEDIUM) for e in official_primary_supp):
                is_supported = True
            elif (has_independent_corroboration or len(unique_domains) >= 2) and any(e.relevance in (EvidenceRelevance.HIGH, EvidenceRelevance.MEDIUM) for e in credible_news_supp):
                is_supported = True
            elif len(credible_news_supp) >= 1 and any(
                e.relevance == EvidenceRelevance.HIGH
                and (e.confidence_in_extraction or 0) >= 0.90
                and any(wire in (_get_dom(e) + " " + (e.publisher or "").lower()) for wire in ["reuters", "apnews", "afp", "bloomberg"])
                for e in credible_news_supp
            ):
                is_supported = True

            domains = list({e.domain or e.publisher or "web source" for e in supp_items})
            domain_str = ", ".join(domains[:3])

            if is_supported:
                verdict = VerdictType.SUPPORTED
                explanation = (
                    f"Available evidence directly supports the factual claim. Corroborating reporting identified from "
                    f"{domain_str} with no contradictory findings identified."
                )
            else:
                verdict = VerdictType.UNVERIFIED
                explanation = (
                    f"Although supporting reporting was referenced ({domain_str}), the claim lacks sufficient independent cross-corroboration "
                    f"from primary official documentation or multiple established news outlets to be definitively affirmed."
                )

            confidence, conf_level, _ = EvidenceEvaluator.calculate_confidence_score(
                evidence, comparisons, verdict
            )
            return ClaimVerdictItem(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=verdict,
                confidence=confidence,
                confidence_level=conf_level,
                evidence_strength=evidence_strength,
                explanation=explanation,
                supporting_evidence_ids=supp_ids,
                contradicting_evidence_ids=contra_ids,
                contextual_evidence_ids=ctx_ids,
                limitations=limitations,
                methodology_version="truthlens-v1.0",
                generated_at=datetime.now(timezone.utc)
            )

        # ==========================================
        # 6. Fallback: Contextual Only
        # ==========================================
        verdict = VerdictType.UNVERIFIED
        confidence, conf_level, _ = EvidenceEvaluator.calculate_confidence_score(
            evidence, comparisons, verdict
        )
        explanation = (
            "Retrieved sources provide general background or context but lack direct evidence "
            "to substantiate or refute the specific assertion."
        )
        return ClaimVerdictItem(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=verdict,
            confidence=confidence,
            confidence_level=conf_level,
            evidence_strength=evidence_strength,
            explanation=explanation,
            supporting_evidence_ids=supp_ids,
            contradicting_evidence_ids=contra_ids,
            contextual_evidence_ids=ctx_ids,
            limitations=limitations,
            methodology_version="truthlens-v1.0",
            generated_at=datetime.now(timezone.utc)
        )
