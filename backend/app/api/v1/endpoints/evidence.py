import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.schemas.evidence import (
    ClaimEvidenceRequest,
    ClaimEvidenceResponse,
    RequestEvidenceAnalysisResponse,
    EvidenceItemSchema,
    SourceComparisonSchema
)
from app.verification.evidence.service import EvidenceAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()
evidence_service = EvidenceAnalysisService()


@router.post(
    "/verify/claims/evidence",
    response_model=ClaimEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Evidence for a Claim",
    description=(
        "Extracts traceable factual passages from discovered web sources linked to a claim, "
        "classifies the evidence stance (SUPPORTING, CONTRADICTING, CONTEXTUAL, INSUFFICIENT), "
        "and evaluates source-to-source agreement and independence without issuing final truth verdicts."
    )
)
def analyze_claim_evidence(
    payload: ClaimEvidenceRequest,
    db: Session = Depends(get_db)
):
    claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID {payload.claim_id} not found."
        )

    try:
        evidence_items, comparisons = evidence_service.analyze_evidence_for_claim(
            claim_id=claim.id,
            db=db,
            force_refresh=payload.force_refresh
        )
    except Exception as exc:
        logger.error(f"Evidence analysis failed for claim {claim.id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evidence analysis failed: {str(exc)}"
        )

    evidence_schemas = [
        EvidenceItemSchema(
            id=e.id,
            claim_id=e.claim_id,
            source_id=e.source_id,
            evidence_text=e.evidence_text,
            snippet=e.snippet,
            evidence_type=e.evidence_type.value,
            direction=e.direction,
            relevance=e.relevance.value,
            relevance_score=e.relevance_score,
            confidence_in_extraction=e.confidence_in_extraction,
            stance_confidence=e.stance_confidence,
            source_location=e.source_location,
            extraction_method=e.extraction_method,
            extracted_at=e.extracted_at,
            url=e.url,
            article_title=e.article_title,
            publisher=e.publisher,
            domain=e.domain,
            publish_date=e.publish_date,
            explanation=e.explanation
        )
        for e in evidence_items
    ]

    comparison_schemas = [
        SourceComparisonSchema(
            id=c.id,
            claim_id=c.claim_id,
            source_a_id=c.source_a_id,
            source_b_id=c.source_b_id,
            source_a_title=c.source_a_title,
            source_b_title=c.source_b_title,
            source_a_domain=c.source_a_domain,
            source_b_domain=c.source_b_domain,
            comparison_type=c.comparison_type,
            source_relationship=c.source_relationship.value,
            evidence_consistency=c.evidence_consistency.value,
            details=c.details,
            supporting_sources_count=c.supporting_sources_count,
            contradicting_sources_count=c.contradicting_sources_count,
            neutral_sources_count=c.neutral_sources_count,
            consensus_verdict=c.consensus_verdict,
            analysis_summary=c.analysis_summary
        )
        for c in comparisons
    ]

    return ClaimEvidenceResponse(
        status="success",
        claim_id=claim.id,
        claim_text=claim.claim_text,
        evidence_count=len(evidence_schemas),
        evidence=evidence_schemas,
        comparisons_count=len(comparison_schemas),
        source_comparisons=comparison_schemas,
        message=(
            f"Extracted {len(evidence_schemas)} evidence items and generated {len(comparison_schemas)} source comparisons. "
            "Final truth verdicts and credibility weighting will be determined in Part 6."
        ) if evidence_schemas else "No sources are associated with this claim to extract evidence from."
    )


@router.post(
    "/verify/requests/{request_id}/evidence",
    response_model=RequestEvidenceAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk Analyze Evidence for a Verification Request",
    description="Extracts evidence and computes source comparisons across all claims in a verification request."
)
def analyze_request_evidence(
    request_id: int,
    db: Session = Depends(get_db)
):
    try:
        res = evidence_service.analyze_evidence_for_request(request_id=request_id, db=db)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )
    except Exception as exc:
        logger.error(f"Bulk evidence analysis failed for request {request_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk evidence analysis failed: {str(exc)}"
        )

    return RequestEvidenceAnalysisResponse(
        status="success",
        request_id=res["request_id"],
        claims_analyzed=res["claims_analyzed"],
        total_evidence=res["total_evidence"],
        total_comparisons=res["total_comparisons"],
        claims=res["claims"],
        message=f"Analyzed {res['total_evidence']} evidence items across {res['claims_analyzed']} claims."
    )


@router.get(
    "/verify/claims/{claim_id}/evidence",
    response_model=ClaimEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Existing Evidence and Source Comparisons for a Claim"
)
def get_claim_evidence(
    claim_id: int,
    db: Session = Depends(get_db)
):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID {claim_id} not found."
        )

    db_evidence = db.query(Evidence).filter(Evidence.claim_id == claim_id).all()
    db_comparisons = db.query(SourceComparison).filter(SourceComparison.claim_id == claim_id).all()

    evidence_schemas = [
        EvidenceItemSchema(
            id=e.id,
            claim_id=e.claim_id,
            source_id=e.source_id,
            evidence_text=e.evidence_text or e.snippet,
            snippet=e.snippet,
            evidence_type=e.evidence_type,
            direction=e.direction,
            relevance=e.relevance,
            relevance_score=e.relevance_score,
            confidence_in_extraction=e.confidence_in_extraction,
            stance_confidence=e.stance_confidence,
            source_location=e.source_location,
            extraction_method=e.extraction_method,
            extracted_at=e.extracted_at,
            url=e.url,
            article_title=e.article_title,
            publisher=e.source.publisher if e.source else None,
            domain=e.source.domain if e.source else None,
            publish_date=e.publish_date,
            explanation=f"Stored evidence ({e.evidence_type}) with {e.relevance} relevance."
        )
        for e in db_evidence
    ]

    comparison_schemas = [
        SourceComparisonSchema(
            id=c.id,
            claim_id=c.claim_id,
            source_a_id=c.source_a_id,
            source_b_id=c.source_b_id,
            source_a_title=c.source_a.title if c.source_a else None,
            source_b_title=c.source_b.title if c.source_b else None,
            source_a_domain=c.source_a.domain if c.source_a else None,
            source_b_domain=c.source_b.domain if c.source_b else None,
            comparison_type=c.comparison_type,
            source_relationship=c.source_relationship,
            evidence_consistency=c.evidence_consistency,
            details=c.details,
            supporting_sources_count=c.supporting_sources_count,
            contradicting_sources_count=c.contradicting_sources_count,
            neutral_sources_count=c.neutral_sources_count,
            consensus_verdict=c.consensus_verdict,
            analysis_summary=c.analysis_summary
        )
        for c in db_comparisons
    ]

    return ClaimEvidenceResponse(
        status="success",
        claim_id=claim.id,
        claim_text=claim.claim_text,
        evidence_count=len(evidence_schemas),
        evidence=evidence_schemas,
        comparisons_count=len(comparison_schemas),
        source_comparisons=comparison_schemas,
        message=f"Retrieved {len(evidence_schemas)} stored evidence items."
    )
