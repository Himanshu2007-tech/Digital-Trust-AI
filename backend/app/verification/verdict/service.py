import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.models.verification_request import VerificationRequest
from app.models.verification_result import VerificationResult
from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem,
    SourceComparisonItem
)
from app.verification.verdict.base import VerdictEngine
from app.verification.verdict.hybrid import HybridVerdictEngine
from app.verification.verdict.models import (
    VerdictType,
    EvidenceStrength,
    ConfidenceLevel,
    ClaimVerdictItem,
    RequestVerdictResult
)

logger = logging.getLogger(__name__)


class VerdictService:
    """
    Orchestration service for Claim Verification, Evidence-to-Verdict Synthesis,
    and Overall Request Dossier Finalization.
    """

    def __init__(self, engine: Optional[VerdictEngine] = None):
        self.engine = engine or HybridVerdictEngine()

    def verify_claim(self, claim_id: int, db: Session) -> ClaimVerdictItem:
        """
        Verifies a single atomic claim using its extracted evidence and source comparisons.
        Persists the ClaimVerdictItem into the verification_results table.
        """
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim with id {claim_id} does not exist.")

        # 1. Transform Evidence DB models to domain items
        evidence_items: List[ExtractedEvidenceItem] = []
        for ev in claim.evidence:
            try:
                ev_type = EvidenceType(ev.evidence_type.upper())
            except ValueError:
                ev_type = EvidenceType.CONTEXTUAL

            try:
                ev_rel = EvidenceRelevance(ev.relevance.upper())
            except ValueError:
                ev_rel = EvidenceRelevance.MEDIUM

            evidence_items.append(
                ExtractedEvidenceItem(
                    id=ev.id,
                    claim_id=ev.claim_id,
                    source_id=ev.source_id,
                    evidence_text=ev.evidence_text or ev.snippet,
                    snippet=ev.snippet,
                    evidence_type=ev_type,
                    direction=ev.direction or ev_type.value,
                    relevance=ev_rel,
                    relevance_score=ev.relevance_score,
                    confidence_in_extraction=ev.confidence_in_extraction,
                    stance_confidence=ev.stance_confidence,
                    source_location=ev.source_location or "snippet",
                    extraction_method=ev.extraction_method or "rule_based",
                    extracted_at=ev.extracted_at,
                    url=ev.url,
                    article_title=ev.article_title,
                    publisher=ev.source.publisher if ev.source and ev.source.publisher else None,
                    domain=(ev.source.domain if ev.source and ev.source.domain else (urlparse(ev.url).netloc.lower() if ev.url else None)),
                    publish_date=ev.publish_date,
                    explanation=f"Extracted from {ev.url}"
                )
            )

        # 2. Transform SourceComparison DB models to domain items
        comparison_items: List[SourceComparisonItem] = []
        for comp in claim.source_comparisons:
            try:
                rel = SourceRelationship(comp.source_relationship.upper())
            except ValueError:
                rel = SourceRelationship.UNKNOWN

            try:
                cons = EvidenceConsistency(comp.evidence_consistency.upper())
            except ValueError:
                cons = EvidenceConsistency.CONSISTENT_EVIDENCE

            comparison_items.append(
                SourceComparisonItem(
                    id=comp.id,
                    claim_id=comp.claim_id,
                    source_id_a=comp.source_a_id,
                    source_id_b=comp.source_b_id,
                    source_relationship=rel,
                    consistency_type=cons,
                    comparison_notes=comp.analysis_summary or comp.details,
                    cross_corroboration_score=0.85
                )
            )

        # 3. Determine verdict via engine
        verdict_item = self.engine.determine_verdict(
            claim_id=claim.id,
            claim_text=claim.claim_text,
            evidence=evidence_items,
            comparisons=comparison_items,
            claim_entities=claim.entities,
            claim_numbers=claim.numbers,
            claim_dates=claim.dates,
        )

        # 4. Upsert into database
        vr = db.query(VerificationResult).filter(VerificationResult.claim_id == claim.id).first()
        if not vr:
            vr = VerificationResult(
                claim_id=claim.id,
                request_id=claim.request_id,
            )
            db.add(vr)

        vr.verdict = verdict_item.verdict.value
        vr.overall_verdict = verdict_item.verdict.value
        vr.confidence = verdict_item.confidence
        vr.confidence_score = verdict_item.confidence
        vr.truth_score = verdict_item.confidence
        vr.explanation = verdict_item.explanation
        vr.summary = verdict_item.explanation[:500]
        vr.supporting_evidence_ids = verdict_item.supporting_evidence_ids
        vr.contradicting_evidence_ids = verdict_item.contradicting_evidence_ids
        vr.contextual_evidence_ids = verdict_item.contextual_evidence_ids
        vr.limitations = verdict_item.limitations
        vr.methodology_version = verdict_item.methodology_version
        vr.generated_at = verdict_item.generated_at or datetime.now(timezone.utc)
        vr.verified_at = datetime.now(timezone.utc)

        claim.status = "verified"
        db.commit()
        db.refresh(vr)

        verdict_item.id = vr.id
        return verdict_item

    def finalize_request(
        self,
        request_id: int,
        db: Session,
        reevaluate_claims: bool = False
    ) -> RequestVerdictResult:
        """
        Synthesizes the overall verification dossier for all claims within a VerificationRequest.
        Persists the request-level VerificationResult (with claim_id=None).
        """
        request = db.query(VerificationRequest).filter(VerificationRequest.id == request_id).first()
        if not request:
            raise ValueError(f"VerificationRequest with id {request_id} does not exist.")

        # 1. Verify all atomic claims
        claim_verdicts: List[ClaimVerdictItem] = []
        for claim in request.claims:
            if not reevaluate_claims and claim.verification_result:
                c_vr = claim.verification_result
                try:
                    c_verdict = VerdictType(c_vr.verdict.upper())
                except ValueError:
                    c_verdict = VerdictType.UNVERIFIED

                # Determine confidence level & strength from confidence score
                conf = c_vr.confidence
                if conf >= 0.75:
                    clevel = ConfidenceLevel.HIGH
                    cstrength = EvidenceStrength.STRONG
                elif conf >= 0.50:
                    clevel = ConfidenceLevel.MODERATE
                    cstrength = EvidenceStrength.MODERATE
                else:
                    clevel = ConfidenceLevel.LOW
                    cstrength = EvidenceStrength.WEAK

                claim_verdicts.append(
                    ClaimVerdictItem(
                        id=c_vr.id,
                        claim_id=claim.id,
                        claim_text=claim.claim_text,
                        verdict=c_verdict,
                        confidence=c_vr.confidence,
                        confidence_level=clevel,
                        evidence_strength=cstrength,
                        explanation=c_vr.explanation,
                        supporting_evidence_ids=c_vr.supporting_evidence_ids or [],
                        contradicting_evidence_ids=c_vr.contradicting_evidence_ids or [],
                        contextual_evidence_ids=c_vr.contextual_evidence_ids or [],
                        limitations=c_vr.limitations or [],
                        methodology_version=c_vr.methodology_version or "truthlens-v1.0",
                        generated_at=c_vr.generated_at
                    )
                )
            else:
                item = self.verify_claim(claim.id, db)
                claim_verdicts.append(item)

        # 2. Synthesize multi-claim overall verdict
        claims_count = len(claim_verdicts)
        supported_count = sum(1 for c in claim_verdicts if c.verdict == VerdictType.SUPPORTED)
        contradicted_count = sum(1 for c in claim_verdicts if c.verdict == VerdictType.CONTRADICTED)
        misleading_count = sum(1 for c in claim_verdicts if c.verdict == VerdictType.MISLEADING)
        unverified_count = sum(1 for c in claim_verdicts if c.verdict == VerdictType.UNVERIFIED)
        insufficient_count = sum(1 for c in claim_verdicts if c.verdict == VerdictType.INSUFFICIENT_EVIDENCE)

        if claims_count == 0:
            overall_verdict = VerdictType.INSUFFICIENT_EVIDENCE
            overall_confidence = 0.15
            summary = "No verifiable claims were extracted from the input text."
        elif claims_count == 1:
            overall_verdict = claim_verdicts[0].verdict
            overall_confidence = claim_verdicts[0].confidence
            summary = (
                f"Evaluated 1 atomic claim: '{claim_verdicts[0].claim_text}'. "
                f"Verdict: {overall_verdict.value} (Evidence Confidence: {overall_confidence:.1%}). "
                f"{claim_verdicts[0].explanation}"
            )
        else:
            # Multi-claim assessment
            # If any contradiction exists alongside supported claims -> MIXED
            if supported_count > 0 and (contradicted_count > 0 or misleading_count > 0):
                overall_verdict = VerdictType.MIXED
            elif contradicted_count > 0 and (supported_count > 0 or misleading_count > 0):
                overall_verdict = VerdictType.MIXED
            elif supported_count == claims_count:
                overall_verdict = VerdictType.SUPPORTED
            elif contradicted_count == claims_count:
                overall_verdict = VerdictType.CONTRADICTED
            elif misleading_count == claims_count:
                overall_verdict = VerdictType.MISLEADING
            elif (supported_count > 0 or contradicted_count > 0 or misleading_count > 0) and (unverified_count > 0 or insufficient_count > 0):
                # Partial verification of composite submission
                overall_verdict = VerdictType.MIXED
            elif unverified_count > 0 and insufficient_count == 0:
                overall_verdict = VerdictType.UNVERIFIED
            else:
                overall_verdict = VerdictType.INSUFFICIENT_EVIDENCE

            overall_confidence = round(sum(c.confidence for c in claim_verdicts) / claims_count, 4)

            verdict_breakdown = []
            if supported_count:
                verdict_breakdown.append(f"{supported_count} Supported")
            if contradicted_count:
                verdict_breakdown.append(f"{contradicted_count} Contradicted")
            if misleading_count:
                verdict_breakdown.append(f"{misleading_count} Misleading")
            if unverified_count:
                verdict_breakdown.append(f"{unverified_count} Unverified")
            if insufficient_count:
                verdict_breakdown.append(f"{insufficient_count} Insufficient Evidence")

            summary = (
                f"Multi-claim analysis of {claims_count} distinct assertions resulted in an overall "
                f"{overall_verdict.value} assessment ({', '.join(verdict_breakdown)}). "
                f"Mean evidence confidence is {overall_confidence:.1%} across all findings."
            )

        # 3. Aggregate all limitations across claims
        aggregated_limitations: List[str] = []
        for c in claim_verdicts:
            for lim in c.limitations:
                if lim not in aggregated_limitations:
                    aggregated_limitations.append(lim)

        # 4. Upsert Request-Level VerificationResult (claim_id is None)
        r_vr = db.query(VerificationResult).filter(
            and_(
                VerificationResult.request_id == request_id,
                VerificationResult.claim_id.is_(None)
            )
        ).first()

        now_utc = datetime.now(timezone.utc)
        if not r_vr:
            r_vr = VerificationResult(
                request_id=request_id,
                claim_id=None
            )
            db.add(r_vr)

        r_vr.verdict = overall_verdict.value
        r_vr.overall_verdict = overall_verdict.value
        r_vr.confidence = overall_confidence
        r_vr.confidence_score = overall_confidence
        r_vr.truth_score = overall_confidence
        r_vr.explanation = summary
        r_vr.summary = summary
        r_vr.limitations = aggregated_limitations
        r_vr.key_findings_json = {
            "claims_count": claims_count,
            "supported_count": supported_count,
            "contradicted_count": contradicted_count,
            "misleading_count": misleading_count,
            "unverified_count": unverified_count,
            "insufficient_count": insufficient_count,
        }
        r_vr.methodology_version = "truthlens-v1.0"
        r_vr.generated_at = now_utc
        r_vr.verified_at = now_utc

        request.status = "completed"
        db.commit()
        db.refresh(r_vr)

        return RequestVerdictResult(
            id=r_vr.id,
            request_id=request.id,
            overall_verdict=overall_verdict,
            overall_confidence=overall_confidence,
            summary=summary,
            claims=claim_verdicts,
            claims_count=claims_count,
            supported_count=supported_count,
            contradicted_count=contradicted_count,
            misleading_count=misleading_count,
            unverified_count=unverified_count,
            insufficient_count=insufficient_count,
            limitations=aggregated_limitations,
            methodology_notes="Evaluated via TruthLens Part 6 multi-dimensional evidence synthesis protocol.",
            generated_at=r_vr.generated_at
        )
