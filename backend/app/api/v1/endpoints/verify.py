import logging
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

logger = logging.getLogger(__name__)

from app.verification.history.service import compute_content_hash, record_verification_event
from app.database.session import get_db
from app.models.verification_request import VerificationRequest
from app.models.claim import Claim
from app.core.exceptions import SecurityRiskException
from app.schemas.verify import (
    NotImplementedResponse,
    TextVerificationRequest,
    UrlVerificationRequest,
    UrlVerificationResponse,
    TextVerificationResponse,
    ExtractedClaimSchema
)
from app.verification.preprocessing import clean_text, segment_sentences
from app.verification.extractors.hybrid import HybridClaimExtractor
from app.utils.security_helpers import validate_url_for_ssrf

from app.verification.search.discovery_service import SourceDiscoveryService
from app.schemas.search import DiscoveredSourceSchema, SearchQueryAuditSchema
from app.verification.evidence.service import EvidenceAnalysisService
from app.schemas.evidence import EvidenceItemSchema, SourceComparisonSchema
from app.verification.verdict.service import VerdictService
from app.schemas.verdict import ClaimVerdictResponse, RequestVerdictResponse
from app.verification.article.service import ArticleVerificationService
from app.schemas.image import ImageVerificationResponse
from app.verification.image.service import ImageVerificationService
from app.schemas.media import MediaVerificationResponse
from app.verification.media.service import MediaVerificationService

router = APIRouter()

hybrid_extractor = HybridClaimExtractor()
discovery_service = SourceDiscoveryService()
evidence_service = EvidenceAnalysisService()
verdict_service = VerdictService()
article_service = ArticleVerificationService()
image_service = ImageVerificationService()
media_service = MediaVerificationService()





@router.post(
    "/verify/text",
    response_model=TextVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Claims & Discover Web Sources",
    description=(
        "Preprocesses input text, decomposes it into atomic verifiable claims, executes real web search "
        "across reputable sources, classifies discovered domains, and persists claims, queries, and sources "
        "to the TruthLens database."
    )
)
def verify_text(
    payload: TextVerificationRequest,
    db: Session = Depends(get_db)
):
    # 1. Clean and normalize input text
    original_text, normalized_text = clean_text(payload.text)
    sentences = segment_sentences(normalized_text)

    # 2. Extract atomic claims with hybrid engine
    extracted_items = hybrid_extractor.extract_claims(normalized_text, context=payload.context)

    # 3. Persist verification request to database
    content_hash_val = compute_content_hash(normalized_text)
    v_request = VerificationRequest(
        request_type="text",
        content=normalized_text,
        content_hash=content_hash_val,
        status="processing",
        priority=0
    )
    db.add(v_request)
    db.flush()  # Populates v_request.id

    record_verification_event(
        db=db,
        request_id=v_request.id,
        stage_name="initialization",
        event_type="REQUEST_CREATED",
        status="success",
        details={"content_length": len(normalized_text), "sentences_count": len(sentences)}
    )

    # 4. Persist each extracted claim
    response_claims: List[ExtractedClaimSchema] = []
    saved_db_claims: List[Claim] = []
    extraction_method_used = "hybrid"

    for item in extracted_items:
        db_claim = Claim(
            request_id=v_request.id,
            claim_text=item.text,
            normalized_text=item.normalized_text,
            claim_type=item.claim_type.value,
            verifiability=item.verifiability.value,
            importance=item.importance.value,
            entities=item.entities,
            dates=item.dates,
            locations=item.locations,
            numbers=item.numbers,
            source_attributions=item.source_attributions,
            original_sentence=item.original_sentence,
            extraction_method=item.extraction_method,
            status="extracted"
        )
        db.add(db_claim)
        db.flush()
        saved_db_claims.append(db_claim)

        extraction_method_used = item.extraction_method

        response_claims.append(ExtractedClaimSchema(
            id=item.id,
            db_id=db_claim.id,
            text=item.text,
            normalized_text=item.normalized_text,
            claim_type=item.claim_type,
            verifiability=item.verifiability,
            importance=item.importance,
            entities=item.entities,
            dates=item.dates,
            locations=item.locations,
            numbers=item.numbers,
            source_attributions=item.source_attributions,
            original_sentence=item.original_sentence,
            extraction_method=item.extraction_method
        ))

    db.commit()

    # 5. Execute real web search & source discovery if requested
    discovered_sources_schemas: List[DiscoveredSourceSchema] = []
    search_queries_schemas: List[SearchQueryAuditSchema] = []
    active_search_provider: Optional[str] = None

    if payload.perform_search and saved_db_claims:
        # Search up to top 3 claims to keep response performant
        claims_to_search = saved_db_claims[:3]
        seen_urls = set()

        for c_rec in claims_to_search:
            try:
                audits, results = discovery_service.discover_sources_for_claim(
                    claim_id=c_rec.id,
                    db=db,
                    max_queries=2,
                    max_results_per_query=4
                )
                for a in audits:
                    search_queries_schemas.append(SearchQueryAuditSchema(
                        query_text=a.query_text,
                        strategy_level=a.strategy_level,
                        search_engine=a.search_engine,
                        results_count=a.results_count,
                        status=a.status,
                        error_message=a.error_message
                    ))
                    if not active_search_provider:
                        active_search_provider = a.search_engine

                for r in results:
                    if r.canonical_url not in seen_urls:
                        seen_urls.add(r.canonical_url)
                        discovered_sources_schemas.append(DiscoveredSourceSchema(
                            title=r.title,
                            url=r.url,
                            canonical_url=r.canonical_url,
                            domain=r.domain,
                            snippet=r.snippet,
                            published_at=r.published_at,
                            publisher=r.publisher,
                            author=r.author,
                            country=r.country,
                            source_type=r.source_type.value,
                            query=r.query,
                            retrieved_at=r.retrieved_at,
                            provider=r.provider,
                            syndication_source=r.syndication_source
                        ))
            except Exception as search_err:
                # Never fail the whole extraction if search provider is offline or misconfigured
                search_queries_schemas.append(SearchQueryAuditSchema(
                    query_text=f"Search failed for claim {c_rec.id}",
                    strategy_level="ERROR",
                    search_engine="unknown",
                    results_count=0,
                    status="failed",
                    error_message=str(search_err)
                ))

    # 6. Extract evidence passages and compute source comparisons if requested
    evidence_schemas: List[EvidenceItemSchema] = []
    comparison_schemas: List[SourceComparisonSchema] = []

    if payload.extract_evidence and discovered_sources_schemas and saved_db_claims:
        for c_rec in saved_db_claims[:3]:
            try:
                ev_items, comp_items = evidence_service.analyze_evidence_for_claim(
                    claim_id=c_rec.id,
                    db=db
                )
                for e in ev_items:
                    evidence_schemas.append(EvidenceItemSchema(
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
                    ))
                for cmp_item in comp_items:
                    comparison_schemas.append(SourceComparisonSchema(
                        id=cmp_item.id,
                        claim_id=cmp_item.claim_id,
                        source_a_id=cmp_item.source_a_id,
                        source_b_id=cmp_item.source_b_id,
                        source_a_title=cmp_item.source_a_title,
                        source_b_title=cmp_item.source_b_title,
                        source_a_domain=cmp_item.source_a_domain,
                        source_b_domain=cmp_item.source_b_domain,
                        comparison_type=cmp_item.comparison_type,
                        source_relationship=cmp_item.source_relationship.value,
                        evidence_consistency=cmp_item.evidence_consistency.value,
                        details=cmp_item.details,
                        supporting_sources_count=cmp_item.supporting_sources_count,
                        contradicting_sources_count=cmp_item.contradicting_sources_count,
                        neutral_sources_count=cmp_item.neutral_sources_count,
                        consensus_verdict=cmp_item.consensus_verdict,
                        analysis_summary=cmp_item.analysis_summary
                    ))
            except Exception as ev_err:
                logger.warning(f"Evidence extraction error for claim {c_rec.id}: {ev_err}")

    # 7. Finalize claim verdicts & overall dossier if requested
    request_verdict_schema: Optional[RequestVerdictResponse] = None
    claim_verdict_schemas: List[ClaimVerdictResponse] = []

    if payload.finalize_verdicts and saved_db_claims:
        try:
            req_verdict_res = verdict_service.finalize_request(
                request_id=v_request.id,
                db=db,
                reevaluate_claims=False
            )
            for c in req_verdict_res.claims:
                claim_verdict_schemas.append(ClaimVerdictResponse(
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
                ))
            request_verdict_schema = RequestVerdictResponse(
                id=req_verdict_res.id,
                request_id=req_verdict_res.request_id,
                overall_verdict=req_verdict_res.overall_verdict.value,
                overall_confidence=req_verdict_res.overall_confidence,
                summary=req_verdict_res.summary,
                claims=claim_verdict_schemas,
                claims_count=req_verdict_res.claims_count,
                supported_count=req_verdict_res.supported_count,
                contradicted_count=req_verdict_res.contradicted_count,
                misleading_count=req_verdict_res.misleading_count,
                unverified_count=req_verdict_res.unverified_count,
                insufficient_count=req_verdict_res.insufficient_count,
                limitations=req_verdict_res.limitations,
                methodology_notes=req_verdict_res.methodology_notes,
                generated_at=req_verdict_res.generated_at
            )
        except Exception as v_err:
            logger.warning(f"Verdict synthesis error for request {v_request.id}: {v_err}")

    if request_verdict_schema:
        msg = f"Verification complete. Overall verdict: {request_verdict_schema.overall_verdict} (Confidence: {request_verdict_schema.overall_confidence:.1%})."
        res_status = "completed"
    elif evidence_schemas:
        msg = (
            f"Extracted {len(response_claims)} claims, discovered {len(discovered_sources_schemas)} sources, "
            f"and analyzed {len(evidence_schemas)} evidence items."
        )
        res_status = "extracted"
    elif discovered_sources_schemas:
        msg = f"Extracted {len(response_claims)} claims and discovered {len(discovered_sources_schemas)} web sources."
        res_status = "extracted"
    else:
        msg = "Claims extracted successfully. No relevant web sources were retrieved."
        res_status = "extracted"

    v_request.status = res_status
    v_request.completed_at = datetime.now(timezone.utc)
    record_verification_event(
        db=db,
        request_id=v_request.id,
        stage_name="pipeline",
        event_type="PROCESSING_COMPLETED",
        status="success",
        details={"status": res_status, "claims_count": len(response_claims)}
    )
    db.commit()

    return TextVerificationResponse(
        status=res_status,
        request_id=v_request.id,
        input_text=normalized_text,
        sentence_count=len(sentences),
        claims_count=len(response_claims),
        claims=response_claims,
        extraction_method=extraction_method_used,
        sources_count=len(discovered_sources_schemas),
        sources=discovered_sources_schemas,
        queries=search_queries_schemas,
        search_provider=active_search_provider or "duckduckgo",
        evidence_count=len(evidence_schemas),
        evidence=evidence_schemas,
        comparisons_count=len(comparison_schemas),
        source_comparisons=comparison_schemas,
        verdict=request_verdict_schema,
        claim_verdicts=claim_verdict_schemas,
        message=msg
    )



@router.post(
    "/verify/url",
    response_model=UrlVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify News URL & Article Content",
    description=(
        "Safely fetches news article content from a public URL, extracts clean metadata and body text, "
        "identifies verifiable claims, performs independent multi-source web discovery, extracts traceable evidence, "
        "and produces a comprehensive verification verdict dossier."
    )
)
def verify_url(
    payload: UrlVerificationRequest,
    db: Session = Depends(get_db)
):
    try:
        result = article_service.verify_url(
            url=str(payload.url),
            db=db,
            perform_search=payload.perform_search,
            extract_evidence=payload.extract_evidence,
            finalize_verdicts=payload.finalize_verdicts
        )
        return UrlVerificationResponse(**result)
    except SecurityRiskException as sre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security rejection: {str(sre)}"
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        logger.error(f"Unexpected error in verify_url: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while verifying the URL: {str(exc)}"
        )


@router.post(
    "/verify/image",
    response_model=ImageVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Image, Screenshot & OCR Claims (Part 8)",
    description=(
        "Uploads and verifies news screenshots, social media posts, quote cards, and infographics. "
        "Performs security checks, de-skewing/preprocessing, multi-engine OCR extraction, "
        "detects visible URLs and social handles, extracts claims, conducts multi-source search, "
        "and produces evidence verdicts with strictly distinct OCR vs Evidence confidence scores."
    )
)
async def verify_image(
    file: UploadFile = File(..., description="Image or screenshot to verify"),
    perform_search: bool = Form(default=True, description="Execute web search to discover corroborating sources"),
    extract_evidence: bool = Form(default=True, description="Extract and analyze evidence stances from sources"),
    finalize_verdicts: bool = Form(default=True, description="Compute mathematical verdicts and confidence scores"),
    max_claims: int = Form(default=5, description="Maximum number of claims to verify from OCR text"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        filename = file.filename or "uploaded_image.png"

        result = image_service.verify_image(
            file_bytes=content,
            original_filename=filename,
            db=db,
            perform_search=perform_search,
            extract_evidence=extract_evidence,
            finalize_verdicts=finalize_verdicts,
            max_claims=max_claims
        )
        return ImageVerificationResponse(**result)
    except SecurityRiskException as sre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security rejection: {str(sre)}"
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        logger.error(f"Unexpected error in verify_image: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while verifying the image: {str(exc)}"
        )


@router.post(
    "/verify/media",
    response_model=MediaVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Audio or Video Media Claim (Part 9)",
    description=(
        "Inspects audio or video container for format and duration safety, extracts metadata, "
        "transcribes spoken speech with timestamped segments, discovers web sources, extracts evidence, "
        "and computes final verdicts with strictly separated acoustic transcription vs journalistic evidence confidence."
    )
)
async def verify_media(
    file: UploadFile = File(..., description="Audio or video file to verify"),
    perform_search: bool = Form(default=True, description="Execute web search to discover corroborating sources"),
    extract_evidence: bool = Form(default=True, description="Extract and analyze evidence stances from sources"),
    finalize_verdicts: bool = Form(default=True, description="Compute mathematical verdicts and confidence scores"),
    max_claims: int = Form(default=5, description="Maximum number of claims to verify from spoken transcript"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        filename = file.filename or "uploaded_media.mp4"

        result = media_service.verify_media(
            file_bytes=content,
            original_filename=filename,
            db=db,
            perform_search=perform_search,
            extract_evidence=extract_evidence,
            finalize_verdicts=finalize_verdicts,
            max_claims=max_claims
        )
        return MediaVerificationResponse(**result)
    except SecurityRiskException as sre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security rejection: {str(sre)}"
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        logger.error(f"Unexpected error in verify_media: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while verifying the media: {str(exc)}"
        )


@router.post(
    "/verify/audio",
    response_model=MediaVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Audio / Speech Claim (Part 9)",
    description="Transcribes spoken audio, identifies claims, cross-references sources, and delivers factual verdict."
)
async def verify_audio(
    file: UploadFile = File(..., description="Audio file to analyze"),
    perform_search: bool = Form(default=True),
    extract_evidence: bool = Form(default=True),
    finalize_verdicts: bool = Form(default=True),
    max_claims: int = Form(default=5),
    db: Session = Depends(get_db)
):
    return await verify_media(
        file=file,
        perform_search=perform_search,
        extract_evidence=extract_evidence,
        finalize_verdicts=finalize_verdicts,
        max_claims=max_claims,
        db=db
    )


@router.post(
    "/verify/video",
    response_model=MediaVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Video Clip (Part 9)",
    description="Extracts audio stream, transcribes spoken statements, and corroborates claims against verified web sources."
)
async def verify_video(
    file: UploadFile = File(..., description="Video file to analyze"),
    perform_search: bool = Form(default=True),
    extract_evidence: bool = Form(default=True),
    finalize_verdicts: bool = Form(default=True),
    max_claims: int = Form(default=5),
    db: Session = Depends(get_db)
):
    return await verify_media(
        file=file,
        perform_search=perform_search,
        extract_evidence=extract_evidence,
        finalize_verdicts=finalize_verdicts,
        max_claims=max_claims,
        db=db
    )

