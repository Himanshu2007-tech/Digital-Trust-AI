import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.claim import Claim
from app.models.verification_request import VerificationRequest
from app.models.verification_result import VerificationResult
from app.schemas.verdict import (
    ClaimVerdictResponse,
    RequestVerdictResponse,
    FinalizeRequestOptions
)
from app.verification.verdict.service import VerdictService
from app.verification.verdict.models import VerdictType, ConfidenceLevel, EvidenceStrength

logger = logging.getLogger(__name__)

router = APIRouter()
verdict_service = VerdictService()


@router.post(
    "/verify/claims/{claim_id}",
    response_model=ClaimVerdictResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Verdict for Claim",
    description="Synthesizes extracted evidence and source comparisons to generate a claim verdict with transparent evidence confidence."
)
def verify_claim(
    claim_id: int,
    db: Session = Depends(get_db)
):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID {claim_id} not found."
        )

    try:
        verdict_item = verdict_service.verify_claim(claim_id=claim.id, db=db)
    except Exception as exc:
        logger.error(f"Verdict synthesis failed for claim {claim.id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verdict determination failed: {str(exc)}"
        )

    return ClaimVerdictResponse(
        id=verdict_item.id,
        claim_id=verdict_item.claim_id,
        claim_text=verdict_item.claim_text,
        verdict=verdict_item.verdict.value,
        confidence=verdict_item.confidence,
        confidence_level=verdict_item.confidence_level.value,
        evidence_strength=verdict_item.evidence_strength.value,
        explanation=verdict_item.explanation,
        supporting_evidence_ids=verdict_item.supporting_evidence_ids,
        contradicting_evidence_ids=verdict_item.contradicting_evidence_ids,
        contextual_evidence_ids=verdict_item.contextual_evidence_ids,
        limitations=verdict_item.limitations,
        methodology_version=verdict_item.methodology_version,
        generated_at=verdict_item.generated_at
    )


@router.get(
    "/verify/claims/{claim_id}/verdict",
    response_model=ClaimVerdictResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Claim Verdict Dossier",
    description="Retrieves the persisted verdict dossier and traceable citations for a previously evaluated claim."
)
def get_claim_verdict(
    claim_id: int,
    db: Session = Depends(get_db)
):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID {claim_id} not found."
        )

    vr = db.query(VerificationResult).filter(VerificationResult.claim_id == claim.id).first()
    if not vr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verification verdict found for claim {claim_id}. Run evaluation first."
        )

    conf = vr.confidence
    if conf >= 0.75:
        clevel = ConfidenceLevel.HIGH.value
        cstrength = EvidenceStrength.STRONG.value
    elif conf >= 0.50:
        clevel = ConfidenceLevel.MODERATE.value
        cstrength = EvidenceStrength.MODERATE.value
    else:
        clevel = ConfidenceLevel.LOW.value
        cstrength = EvidenceStrength.WEAK.value

    return ClaimVerdictResponse(
        id=vr.id,
        claim_id=claim.id,
        claim_text=claim.claim_text,
        verdict=vr.verdict,
        confidence=vr.confidence,
        confidence_level=clevel,
        evidence_strength=cstrength,
        explanation=vr.explanation,
        supporting_evidence_ids=vr.supporting_evidence_ids or [],
        contradicting_evidence_ids=vr.contradicting_evidence_ids or [],
        contextual_evidence_ids=vr.contextual_evidence_ids or [],
        limitations=vr.limitations or [],
        methodology_version=vr.methodology_version or "truthlens-v1.0",
        generated_at=vr.generated_at
    )


@router.post(
    "/verify/requests/{request_id}/finalize",
    response_model=RequestVerdictResponse,
    status_code=status.HTTP_200_OK,
    summary="Finalize Request Verdict Dossier",
    description="Synthesizes verdicts across all claims in the request, computes multi-claim synthesis, and persists overall dossier."
)
def finalize_request_verdicts(
    request_id: int,
    options: Optional[FinalizeRequestOptions] = None,
    db: Session = Depends(get_db)
):
    req = db.query(VerificationRequest).filter(VerificationRequest.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VerificationRequest with ID {request_id} not found."
        )

    reevaluate = options.reevaluate_claims if options else False
    try:
        final_res = verdict_service.finalize_request(
            request_id=req.id,
            db=db,
            reevaluate_claims=reevaluate
        )
    except Exception as exc:
        logger.error(f"Request finalization failed for request {req.id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Request finalization failed: {str(exc)}"
        )

    claim_schemas = [
        ClaimVerdictResponse(
            id=c.id,
            claim_id=c.claim_id,
            claim_text=c.claim_text,
            verdict=c.verdict.value,
            confidence=c.confidence,
            confidence_level=c.confidence_level.value,
            evidence_strength=c.evidence_strength.value,
            explanation=c.explanation,
            supporting_evidence_ids=c.supporting_evidence_ids,
            contradicting_evidence_ids=c.contradicting_evidence_ids,
            contextual_evidence_ids=c.contextual_evidence_ids,
            limitations=c.limitations,
            methodology_version=c.methodology_version,
            generated_at=c.generated_at
        )
        for c in final_res.claims
    ]

    return RequestVerdictResponse(
        id=final_res.id,
        request_id=final_res.request_id,
        overall_verdict=final_res.overall_verdict.value,
        overall_confidence=final_res.overall_confidence,
        summary=final_res.summary,
        claims=claim_schemas,
        claims_count=final_res.claims_count,
        supported_count=final_res.supported_count,
        contradicted_count=final_res.contradicted_count,
        misleading_count=final_res.misleading_count,
        unverified_count=final_res.unverified_count,
        insufficient_count=final_res.insufficient_count,
        limitations=final_res.limitations,
        methodology_notes=final_res.methodology_notes,
        generated_at=final_res.generated_at
    )


@router.get(
    "/verify/requests/{request_id}/verdict",
    response_model=RequestVerdictResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Request Verdict Dossier",
    description="Retrieves the overall request verdict dossier and all constituent claim verdicts."
)
def get_request_verdict(
    request_id: int,
    db: Session = Depends(get_db)
):
    req = db.query(VerificationRequest).filter(VerificationRequest.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VerificationRequest with ID {request_id} not found."
        )

    # Find request-level result
    vr = db.query(VerificationResult).filter(
        VerificationResult.request_id == req.id,
        VerificationResult.claim_id.is_(None)
    ).first()

    if not vr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No overall verdict dossier found for request {request_id}. Run finalization first."
        )

    # Collect claim results
    claim_schemas: List[ClaimVerdictResponse] = []
    for c in req.claims:
        c_vr = c.verification_result
        if c_vr:
            conf = c_vr.confidence
            if conf >= 0.75:
                clevel = ConfidenceLevel.HIGH.value
                cstrength = EvidenceStrength.STRONG.value
            elif conf >= 0.50:
                clevel = ConfidenceLevel.MODERATE.value
                cstrength = EvidenceStrength.MODERATE.value
            else:
                clevel = ConfidenceLevel.LOW.value
                cstrength = EvidenceStrength.WEAK.value

            claim_schemas.append(
                ClaimVerdictResponse(
                    id=c_vr.id,
                    claim_id=c.id,
                    claim_text=c.claim_text,
                    verdict=c_vr.verdict,
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

    findings = vr.key_findings_json or {}
    return RequestVerdictResponse(
        id=vr.id,
        request_id=req.id,
        overall_verdict=vr.overall_verdict or vr.verdict,
        overall_confidence=vr.confidence,
        summary=vr.summary or vr.explanation,
        claims=claim_schemas,
        claims_count=findings.get("claims_count", len(claim_schemas)),
        supported_count=findings.get("supported_count", 0),
        contradicted_count=findings.get("contradicted_count", 0),
        misleading_count=findings.get("misleading_count", 0),
        unverified_count=findings.get("unverified_count", 0),
        insufficient_count=findings.get("insufficient_count", 0),
        limitations=vr.limitations or [],
        methodology_notes=vr.methodology_notes or "Evaluated via TruthLens Part 6 multi-dimensional evidence synthesis protocol.",
        generated_at=vr.generated_at
    )
