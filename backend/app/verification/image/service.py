import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.verification_request import VerificationRequest
from app.models.media_file import MediaFile
from app.models.image_verification import ImageVerification
from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.verification.domain_models import ExtractedClaimItem, ClaimType, Verifiability, Importance
from app.verification.image.security import (
    validate_image_security,
    extract_and_sanitize_exif,
    save_image_file,
)
from app.verification.image.preprocessor import ImagePreprocessor
from app.verification.image.ocr.engine import UnifiedOCREngine
from app.verification.image.ocr.base import OCRResult
from app.verification.extractors.hybrid import HybridClaimExtractor
from app.verification.search.discovery_service import SourceDiscoveryService
from app.verification.evidence.service import EvidenceAnalysisService
from app.verification.verdict.service import VerdictService
from app.verification.history.service import record_verification_event

logger = logging.getLogger(__name__)


class ImageVerificationService:
    """
    End-to-end orchestration service for Image, Screenshot & OCR Verification.
    Coordinates:
    1. Secure byte inspection (magic bytes, size check, decompression bomb defense)
    2. Privacy-preserving EXIF sanitization (GPS and PII stripped)
    3. Image preprocessing (orientation, contrast enhancement, grayscale)
    4. Multi-engine OCR extraction with word-level bounding blocks and clarity confidence
    5. Contextual entity detection (URLs, social handles, engagement metrics, timestamps)
    6. Claim extraction from recognized OCR text (Part 3)
    7. Multi-source web search & source discovery (Part 4)
    8. Evidence extraction and cross-source comparisons (Part 5)
    9. Final verdict determination and mathematical evidence confidence scoring (Part 6)
    10. Dual-confidence image verification dossier assembly
    """

    def __init__(
        self,
        preprocessor: Optional[ImagePreprocessor] = None,
        ocr_engine: Optional[UnifiedOCREngine] = None,
        claim_extractor: Optional[HybridClaimExtractor] = None,
        discovery_service: Optional[SourceDiscoveryService] = None,
        evidence_service: Optional[EvidenceAnalysisService] = None,
        verdict_service: Optional[VerdictService] = None,
    ):
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.ocr_engine = ocr_engine or UnifiedOCREngine()
        self.claim_extractor = claim_extractor or HybridClaimExtractor()
        self.discovery_service = discovery_service or SourceDiscoveryService()
        self.evidence_service = evidence_service or EvidenceAnalysisService()
        self.verdict_service = verdict_service or VerdictService()

    def verify_image(
        self,
        file_bytes: bytes,
        original_filename: str,
        db: Session,
        user_id: Optional[int] = None,
        perform_search: bool = True,
        extract_evidence: bool = True,
        finalize_verdicts: bool = True,
        max_claims: int = 5,
    ) -> Dict[str, Any]:
        """
        Executes complete verification pipeline for an uploaded image or screenshot.
        """
        # 1. Validate security and integrity (decompression bomb protection & magic bytes)
        mime_type, ext, width, height = validate_image_security(file_bytes, original_filename)

        # 2. Extract and sanitize EXIF metadata (GPS/PII strictly stripped)
        sanitized_exif = extract_and_sanitize_exif(file_bytes)

        # 3. Secure disk storage with collision-resistant UUID filename
        file_meta = save_image_file(file_bytes, original_filename, mime_type, ext)

        # 4. Save MediaFile record
        db_media = MediaFile(
            original_filename=file_meta["original_filename"],
            stored_filename=file_meta["stored_filename"],
            file_path=file_meta["file_path"],
            file_size_bytes=file_meta["file_size_bytes"],
            mime_type=file_meta["mime_type"],
            file_hash_sha256=file_meta["file_hash_sha256"],
            storage_provider=file_meta["storage_provider"],
        )
        db.add(db_media)
        db.flush()

        # 5. Image Preprocessing for OCR
        preprocessed_img, prep_ops = self.preprocessor.process(file_bytes)

        # 6. OCR Extraction (bounding boxes + recognition confidence)
        ocr_result: OCRResult = self.ocr_engine.extract(preprocessed_img)

        # 7. Create VerificationRequest
        v_request = VerificationRequest(
            user_id=user_id,
            request_type="image",
            content=ocr_result.normalized_text or f"Image: {original_filename}",
            content_hash=file_meta["file_hash_sha256"],
            media_file_id=db_media.id,
            status="processing",
            priority=0,
        )
        db.add(v_request)
        db.flush()

        record_verification_event(
            db=db,
            request_id=v_request.id,
            stage_name="initialization",
            event_type="REQUEST_CREATED",
            status="success",
            details={"original_filename": original_filename, "hash": file_meta["file_hash_sha256"]},
        )

        # 8. Save ImageVerification entity
        detected_entities_dict = {
            "handles": ocr_result.detected_handles,
            "metrics": ocr_result.detected_metrics,
            "dates": ocr_result.detected_dates,
        }

        db_image_verif = ImageVerification(
            request_id=v_request.id,
            media_file_id=db_media.id,
            image_width=width,
            image_height=height,
            image_format=ext.upper(),
            raw_ocr_text=ocr_result.raw_text,
            normalized_ocr_text=ocr_result.normalized_text,
            ocr_confidence=ocr_result.overall_confidence,
            ocr_blocks=[b.to_dict() for b in ocr_result.blocks],
            detected_urls=ocr_result.detected_urls,
            detected_entities=detected_entities_dict,
            exif_metadata=sanitized_exif,
            ocr_engine=ocr_result.engine_used,
        )
        db.add(db_image_verif)
        db.flush()

        # 9. Claim Extraction (Part 3)
        saved_db_claims: List[Claim] = []
        text_for_claims = ocr_result.normalized_text[:18000].strip()

        if text_for_claims and len(text_for_claims) > 10:
            extracted_claim_items = self.claim_extractor.extract_claims(
                text_for_claims,
                context=f"Image text extracted from screenshot {original_filename}"
            )
        else:
            extracted_claim_items = []

        # Fallback if no atomic claims extracted but text has substance
        if not extracted_claim_items and len(text_for_claims.split()) >= 4:
            first_sentence = text_for_claims.split(".")[0].strip()
            if len(first_sentence) > 10:
                extracted_claim_items = [
                    ExtractedClaimItem(
                        text=first_sentence,
                        normalized_text=first_sentence.lower(),
                        claim_type=ClaimType.FACTUAL,
                        verifiability=Verifiability.VERIFIABLE,
                        importance=Importance.HIGH,
                        entities=ocr_result.detected_handles,
                        dates=ocr_result.detected_dates,
                        locations=[],
                        numbers=[],
                        source_attributions=[],
                        original_sentence=first_sentence,
                        extraction_method="ocr_text_fallback",
                    )
                ]

        target_claim_items = extracted_claim_items[:max_claims]

        for item in target_claim_items:
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
                status="extracted",
            )
            db.add(db_claim)
            db.flush()
            saved_db_claims.append(db_claim)

        db.commit()

        # 10. Multi-Source Web Search & Discovery (Part 4)
        queries_schemas: List[Dict[str, Any]] = []
        discovered_sources_map: Dict[str, Dict[str, Any]] = {}
        active_provider: Optional[str] = None

        if perform_search and saved_db_claims:
            for c_rec in saved_db_claims:
                try:
                    audits, results = self.discovery_service.discover_sources_for_claim(
                        claim_id=c_rec.id,
                        db=db,
                        max_queries=2,
                        max_results_per_query=4,
                    )
                    for a in audits:
                        queries_schemas.append({
                            "query_text": a.query_text,
                            "strategy_level": a.strategy_level,
                            "search_engine": a.search_engine,
                            "results_count": a.results_count,
                            "status": a.status,
                            "error_message": a.error_message,
                        })
                        if not active_provider:
                            active_provider = a.search_engine

                    for r in results:
                        if r.canonical_url not in discovered_sources_map:
                            discovered_sources_map[r.canonical_url] = {
                                "title": r.title,
                                "url": r.url,
                                "canonical_url": r.canonical_url,
                                "domain": r.domain,
                                "snippet": r.snippet,
                                "published_at": r.published_at,
                                "publisher": r.publisher,
                                "author": r.author,
                                "country": r.country,
                                "source_type": r.source_type.value,
                                "source_role": "INDEPENDENT_SOURCE",
                                "query": r.query,
                                "retrieved_at": r.retrieved_at,
                                "provider": r.provider,
                                "syndication_source": r.syndication_source,
                            }
                except Exception as s_err:
                    logger.warning(f"Search error for claim {c_rec.id}: {s_err}")
                    queries_schemas.append({
                        "query_text": f"Search failed for claim {c_rec.id}",
                        "strategy_level": "ERROR",
                        "search_engine": "unknown",
                        "results_count": 0,
                        "status": "failed",
                        "error_message": str(s_err),
                    })

        # 11. Evidence Extraction & Comparison (Part 5)
        evidence_schemas: List[Dict[str, Any]] = []
        comparison_schemas: List[Dict[str, Any]] = []

        if extract_evidence and saved_db_claims:
            for c_rec in saved_db_claims:
                try:
                    ev_items, comp_items = self.evidence_service.analyze_evidence_for_claim(
                        claim_id=c_rec.id,
                        db=db,
                    )
                    for e in ev_items:
                        evidence_schemas.append({
                            "id": e.id,
                            "claim_id": e.claim_id,
                            "source_id": e.source_id,
                            "evidence_text": e.evidence_text,
                            "snippet": e.snippet,
                            "evidence_type": e.evidence_type.value if hasattr(e.evidence_type, "value") else str(e.evidence_type),
                            "direction": e.direction,
                            "relevance": e.relevance.value if hasattr(e.relevance, "value") else str(e.relevance),
                            "relevance_score": e.relevance_score,
                            "confidence_in_extraction": e.confidence_in_extraction,
                            "stance_confidence": e.stance_confidence,
                            "source_location": e.source_location,
                            "extraction_method": e.extraction_method,
                            "extracted_at": e.extracted_at,
                            "url": e.url,
                            "article_title": e.article_title,
                            "publisher": e.publisher,
                            "domain": e.domain,
                            "publish_date": e.publish_date,
                            "explanation": e.explanation
                        })
                    for cmp in comp_items:
                        comparison_schemas.append({
                            "id": cmp.id,
                            "claim_id": cmp.claim_id,
                            "source_a_id": cmp.source_a_id,
                            "source_b_id": cmp.source_b_id,
                            "source_a_title": cmp.source_a_title,
                            "source_b_title": cmp.source_b_title,
                            "source_a_domain": cmp.source_a_domain,
                            "source_b_domain": cmp.source_b_domain,
                            "comparison_type": cmp.comparison_type,
                            "source_relationship": cmp.source_relationship.value if hasattr(cmp.source_relationship, "value") else str(cmp.source_relationship),
                            "evidence_consistency": cmp.evidence_consistency.value if hasattr(cmp.evidence_consistency, "value") else str(cmp.evidence_consistency),
                            "details": cmp.details,
                            "supporting_sources_count": cmp.supporting_sources_count,
                            "contradicting_sources_count": cmp.contradicting_sources_count,
                            "neutral_sources_count": cmp.neutral_sources_count,
                            "consensus_verdict": cmp.consensus_verdict,
                            "analysis_summary": cmp.analysis_summary
                        })
                except Exception as ev_err:
                    logger.warning(f"Evidence error for claim {c_rec.id}: {ev_err}")

        # 12. Final Verdict & Evidence Confidence (Part 6)
        verdicts_response = None
        if finalize_verdicts and saved_db_claims:
            try:
                res_verdict = self.verdict_service.finalize_request(
                    request_id=v_request.id,
                    db=db,
                    reevaluate_claims=False
                )
                claim_verdict_dicts = []
                for cv in res_verdict.claims:
                    claim_verdict_dicts.append({
                        "id": cv.id,
                        "claim_id": cv.claim_id,
                        "claim_text": cv.claim_text,
                        "verdict": cv.verdict.value if hasattr(cv.verdict, "value") else str(cv.verdict),
                        "confidence": cv.confidence,
                        "confidence_level": cv.confidence_level.value if hasattr(cv.confidence_level, "value") else str(cv.confidence_level),
                        "evidence_strength": cv.evidence_strength.value if hasattr(cv.evidence_strength, "value") else str(cv.evidence_strength),
                        "explanation": cv.explanation,
                        "supporting_evidence_ids": cv.supporting_evidence_ids or [],
                        "contradicting_evidence_ids": cv.contradicting_evidence_ids or [],
                        "contextual_evidence_ids": cv.contextual_evidence_ids or [],
                        "limitations": cv.limitations or [],
                        "methodology_version": cv.methodology_version,
                        "generated_at": cv.generated_at
                    })
                verdicts_response = {
                    "id": res_verdict.id,
                    "request_id": res_verdict.request_id,
                    "overall_verdict": res_verdict.overall_verdict.value if hasattr(res_verdict.overall_verdict, "value") else str(res_verdict.overall_verdict),
                    "overall_confidence": res_verdict.overall_confidence,
                    "summary": res_verdict.summary,
                    "claims": claim_verdict_dicts,
                    "claims_count": res_verdict.claims_count,
                    "supported_count": res_verdict.supported_count,
                    "contradicted_count": res_verdict.contradicted_count,
                    "misleading_count": res_verdict.misleading_count,
                    "unverified_count": res_verdict.unverified_count,
                    "insufficient_count": res_verdict.insufficient_count,
                    "limitations": res_verdict.limitations or [],
                    "methodology_notes": res_verdict.methodology_notes,
                    "generated_at": res_verdict.generated_at
                }
            except Exception as v_err:
                logger.warning(f"Verdict evaluation error: {v_err}")

        # 13. Update request status
        v_request.status = "completed"
        v_request.completed_at = datetime.now(timezone.utc)
        record_verification_event(
            db=db,
            request_id=v_request.id,
            stage_name="pipeline",
            event_type="PROCESSING_COMPLETED",
            status="success",
            details={"status": "completed", "claims_count": len(saved_db_claims)},
        )
        db.commit()

        # Build claim response schemas
        claims_response = []
        for c in saved_db_claims:
            claims_response.append({
                "id": f"claim_{c.id}",
                "db_id": c.id,
                "text": c.claim_text,
                "normalized_text": c.normalized_text,
                "claim_type": c.claim_type,
                "verifiability": c.verifiability,
                "importance": c.importance,
                "entities": c.entities or [],
                "dates": c.dates or [],
                "locations": c.locations or [],
                "numbers": c.numbers or [],
                "source_attributions": c.source_attributions or [],
                "original_sentence": c.original_sentence or c.claim_text,
                "extraction_method": c.extraction_method or "hybrid",
                "status": c.status,
            })

        return {
            "request_id": v_request.id,
            "media_file_id": db_media.id,
            "image_verification_id": db_image_verif.id,
            "status": "completed",
            "forensics": {
                "image_width": width,
                "image_height": height,
                "image_format": ext.upper(),
                "file_size_bytes": file_meta["file_size_bytes"],
                "file_hash_sha256": file_meta["file_hash_sha256"],
                "original_filename": file_meta["original_filename"],
                "sanitized_exif": sanitized_exif,
                "ocr_engine": ocr_result.engine_used,
                "preprocessing_applied": prep_ops,
            },
            "ocr": {
                "raw_text": ocr_result.raw_text,
                "normalized_text": ocr_result.normalized_text,
                "ocr_confidence": ocr_result.overall_confidence,
                "word_count": ocr_result.word_count,
                "low_confidence_warning": ocr_result.low_confidence_warning,
                "detected_urls": ocr_result.detected_urls,
                "detected_handles": ocr_result.detected_handles,
                "detected_metrics": ocr_result.detected_metrics,
                "detected_dates": ocr_result.detected_dates,
                "blocks": [b.to_dict() for b in ocr_result.blocks],
            },
            "claims": claims_response,
            "sources": list(discovered_sources_map.values()),
            "evidence": evidence_schemas,
            "comparisons": comparison_schemas,
            "verdicts": verdicts_response,
            "claims_count": len(claims_response),
            "sources_count": len(discovered_sources_map),
            "evidence_count": len(evidence_schemas),
            "authenticity_disclaimer": (
                "TruthLens AI verifies the factual claims stated in text found within images against authoritative "
                "web sources. High evidence credibility indicates verified factual reporting, but does not certify "
                "that the image file itself is digitally authentic or free from visual manipulation."
            ),
        }
