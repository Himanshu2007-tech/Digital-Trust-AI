import re
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.verification_request import VerificationRequest
from app.models.media_file import MediaFile
from app.models.media_verification import MediaVerification
from app.models.transcript_segment import TranscriptSegment
from app.models.video_frame import VideoFrame
from app.models.claim_occurrence import ClaimOccurrence
from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.verification.domain_models import ExtractedClaimItem, ClaimType, Verifiability, Importance
from app.verification.media.security import validate_media_security, save_media_file
from app.verification.media.metadata import extract_media_metadata
from app.verification.media.transcription.base import TranscriptSegmentItem, TranscriptionResult
from app.verification.media.transcription.engine import (
    UnifiedTranscriptionEngine,
    detect_language_and_codeswitching,
)
from app.verification.media.transcription.patterns import extract_spoken_urls, extract_direct_quotes
from app.verification.extractors.hybrid import HybridClaimExtractor
from app.verification.search.discovery_service import SourceDiscoveryService
from app.verification.evidence.service import EvidenceAnalysisService
from app.verification.verdict.service import VerdictService
from app.verification.multimedia.service import MultimediaAnalysisService
from app.verification.multimedia.sampling import ExtractedFrameItem
from app.verification.history.service import record_verification_event

logger = logging.getLogger(__name__)


def correlate_claim_with_segment(
    claim_text: str,
    segments: List[TranscriptSegmentItem]
) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[int]]:
    """
    Correlates an extracted claim with the most relevant transcript segment
    to establish origin timestamp traceability (e.g. 00:15 - 00:28).
    """
    if not segments:
        return (None, None, None, None)

    clean_claim = claim_text.lower()
    claim_words = set(w for w in re.findall(r"\w+", clean_claim) if len(w) > 3)

    best_segment: Optional[TranscriptSegmentItem] = None
    best_score = 0

    for seg in segments:
        seg_lower = seg.text.lower()
        # Direct substring containment
        if clean_claim in seg_lower or seg_lower in clean_claim:
            return (seg.start_time, seg.end_time, seg.formatted_timestamp, seg.sequence)

        # Word overlap
        seg_words = set(w for w in re.findall(r"\w+", seg_lower) if len(w) > 3)
        if seg_words and claim_words:
            overlap = len(claim_words.intersection(seg_words))
            if overlap > best_score:
                best_score = overlap
                best_segment = seg

    if best_segment and best_score >= 1:
        return (best_segment.start_time, best_segment.end_time, best_segment.formatted_timestamp, best_segment.sequence)

    # Fallback to the first segment
    first = segments[0]
    return (first.start_time, first.end_time, first.formatted_timestamp, first.sequence)


class MediaVerificationService:
    """
    End-to-end orchestration service for Audio and Video Claim Verification (Parts 9 & 10).
    Coordinates:
    1. Secure byte inspection (magic bytes, size check, container verification)
    2. Technical metadata & stream extraction (duration, codecs, silent track detection)
    3. Maximum duration limits enforcement (MEDIA_TOO_LONG)
    4. Speech-to-Text transcription with atomic timestamped segments and confidence scoring
    5. Contextual entity detection (spoken URLs, direct quotes, multilingual/Hinglish detection)
    6. Advanced Video Multimedia Analysis (Part 10): keyframe sampling, scene change detection,
       on-screen OCR, visual context extraction, and multimodal claim deduplication
    7. Multi-source web search & source discovery (Part 4)
    8. Evidence extraction and cross-source comparisons (Part 5)
    9. Final verdict determination and mathematical evidence confidence scoring (Part 6)
    10. Dual-confidence multimedia verification dossier assembly
    """

    def __init__(
        self,
        transcription_engine: Optional[UnifiedTranscriptionEngine] = None,
        claim_extractor: Optional[HybridClaimExtractor] = None,
        discovery_service: Optional[SourceDiscoveryService] = None,
        evidence_service: Optional[EvidenceAnalysisService] = None,
        verdict_service: Optional[VerdictService] = None,
        multimedia_service: Optional[MultimediaAnalysisService] = None,
    ):
        self.transcription_engine = transcription_engine or UnifiedTranscriptionEngine()
        self.claim_extractor = claim_extractor or HybridClaimExtractor()
        self.discovery_service = discovery_service or SourceDiscoveryService()
        self.evidence_service = evidence_service or EvidenceAnalysisService()
        self.verdict_service = verdict_service or VerdictService()
        self.multimedia_service = multimedia_service or MultimediaAnalysisService()

    def verify_media(
        self,
        file_bytes: bytes,
        original_filename: str,
        db: Session,
        user_id: Optional[int] = None,
        perform_search: bool = True,
        extract_evidence: bool = True,
        finalize_verdicts: bool = True,
        max_claims: int = 5,
        injected_frames: Optional[List[ExtractedFrameItem]] = None,
        injected_ocr_map: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes complete verification pipeline for an uploaded audio or video file.
        """
        # 1. Validate security and integrity (magic bytes, container headers, size limits)
        mime_type, ext, media_type = validate_media_security(file_bytes, original_filename)

        # 2. Secure disk storage with collision-resistant UUID filename
        file_meta = save_media_file(file_bytes, original_filename, mime_type, ext)

        # 3. Save MediaFile record
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

        # 4. Technical metadata and stream inspection (duration, channels, codecs, silent track)
        metadata = extract_media_metadata(
            file_path=file_meta["file_path"],
            media_type=media_type,
            raw_bytes=file_bytes
        )

        has_audio = metadata.get("has_audio_track", True)

        # 5. Speech-to-Text Transcription
        if not has_audio:
            # Silent video handling
            transcription_result = TranscriptionResult(
                raw_text="[SILENT VIDEO: No audio track detected in media container]",
                normalized_text="",
                language="none",
                is_code_switched=False,
                overall_confidence=100.0,
                segments=[],
                duration_seconds=metadata.get("duration_seconds", 0.0),
                engine_used="container_inspector"
            )
            spoken_urls = []
            direct_quotes = []
        else:
            transcription_result = self.transcription_engine.transcribe(
                file_path=file_meta["file_path"],
                media_type=media_type,
                raw_bytes=file_bytes
            )
            spoken_urls = extract_spoken_urls(transcription_result.raw_text)
            direct_quotes = extract_direct_quotes(transcription_result.raw_text)

        # 6. Create VerificationRequest
        v_request = VerificationRequest(
            user_id=user_id,
            request_type=media_type,
            content=transcription_result.normalized_text or f"{media_type.capitalize()}: {original_filename}",
            media_file_id=db_media.id,
            content_hash=file_meta["file_hash_sha256"],
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
            details={"original_filename": original_filename, "hash": file_meta["file_hash_sha256"], "media_type": media_type},
        )

        # 7. Save MediaVerification entity
        db_media_verif = MediaVerification(
            request_id=v_request.id,
            media_file_id=db_media.id,
            media_type=media_type,
            duration_seconds=metadata.get("duration_seconds", 0.0),
            width=metadata.get("width"),
            height=metadata.get("height"),
            video_codec=metadata.get("video_codec"),
            audio_codec=metadata.get("audio_codec"),
            sample_rate=metadata.get("sample_rate"),
            channels=metadata.get("channels"),
            bitrate=metadata.get("bitrate"),
            has_audio_track=has_audio,
            media_hash=file_meta["file_hash_sha256"],
            language=transcription_result.language,
            raw_transcript=transcription_result.raw_text,
            normalized_transcript=transcription_result.normalized_text,
            transcription_confidence=transcription_result.overall_confidence,
            detected_urls=spoken_urls,
            detected_quotes=direct_quotes,
            technical_indicators=metadata.get("technical_indicators", {}),
            metadata_json=metadata,
        )
        db.add(db_media_verif)
        db.flush()

        # 8. Save TranscriptSegment records
        saved_db_segments: List[TranscriptSegment] = []
        for seg in transcription_result.segments:
            db_seg = TranscriptSegment(
                media_verification_id=db_media_verif.id,
                sequence=seg.sequence,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
                confidence=seg.confidence,
            )
            db.add(db_seg)
            db.flush()
            saved_db_segments.append(db_seg)

        # 9. Extract Raw Audio Claims
        raw_audio_claims: List[Dict[str, Any]] = []
        text_for_claims = transcription_result.normalized_text[:18000].strip()

        if text_for_claims and len(text_for_claims) > 10:
            extracted_claim_items = self.claim_extractor.extract_claims(
                text_for_claims,
                context=f"Speech transcript from {media_type} file {original_filename}"
            )
        else:
            extracted_claim_items = []

        # Fallback if no atomic claims extracted but speech text has substance
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
                        entities=[],
                        dates=[],
                        locations=[],
                        numbers=[],
                        source_attributions=[],
                        original_sentence=first_sentence,
                        extraction_method="speech_transcript_fallback",
                    )
                ]

        for item in extracted_claim_items[:max_claims]:
            start_t, end_t, fmt_ts, seg_seq = correlate_claim_with_segment(
                item.text, transcription_result.segments
            )
            raw_audio_claims.append({
                "text": item.text,
                "normalized_text": item.normalized_text,
                "claim_type": item.claim_type,
                "verifiability": item.verifiability,
                "importance": item.importance,
                "entities": item.entities,
                "dates": item.dates,
                "locations": item.locations,
                "numbers": item.numbers,
                "source_attributions": item.source_attributions,
                "original_sentence": item.original_sentence,
                "extraction_method": item.extraction_method,
                "start_time": start_t,
                "end_time": end_t,
                "formatted_timestamp": fmt_ts,
                "segment_sequence": seg_seq,
            })

        # 10. Advanced Multimedia Analysis (Part 10)
        multimedia_data: Dict[str, Any] = {}
        if media_type == "video":
            multimedia_data = self.multimedia_service.analyze_video_multimedia(
                video_path=file_meta["file_path"],
                media_verification_id=db_media_verif.id,
                duration_seconds=metadata.get("duration_seconds", 0.0),
                transcript_segments=transcription_result.segments,
                raw_audio_claims=raw_audio_claims,
                db=db,
                raw_bytes=file_bytes,
                injected_frames=injected_frames,
                injected_ocr_map=injected_ocr_map,
                max_claims=max_claims,
            )
            target_claims_to_persist = multimedia_data["fused_claims"]
        else:
            # Audio-only: build speech-only timeline & occurrences
            target_claims_to_persist = []
            for ac in raw_audio_claims:
                ac_copy = dict(ac)
                ac_copy["primary_origin"] = "AUDIO_TRANSCRIPT"
                ac_copy["occurrences"] = [{
                    "source_type": "AUDIO_TRANSCRIPT",
                    "timestamp_start": ac.get("start_time", 0.0) or 0.0,
                    "timestamp_end": ac.get("end_time", 0.0) or 0.0,
                    "frame_id": None,
                    "transcript_segment_id": None,
                    "ocr_block_id": None,
                    "text": ac["text"],
                    "confidence": 0.90,
                    "formatted_timestamp": ac.get("formatted_timestamp") or "00:00",
                }]
                target_claims_to_persist.append(ac_copy)

            # Build audio timeline
            timeline_events = self.multimedia_service.timeline_analyzer.build_timeline(
                duration_seconds=metadata.get("duration_seconds", 0.0),
                segments=transcription_result.segments,
                frames=[],
                claims=target_claims_to_persist,
            )
            multimedia_data = {
                "frames": [],
                "fused_claims": target_claims_to_persist,
                "timeline": timeline_events,
                "alignment": {
                    "summary_status": "AUDIO_ONLY",
                    "summary_note": "Audio file analysis; visual track alignment not applicable.",
                    "alignments_count": 0,
                    "mismatches_count": 0,
                    "alignments": [],
                    "mismatches": [],
                    "disclaimer": "Audio-only verification.",
                },
                "reused_footage": {
                    "reused_footage_detected": False,
                    "matching_frames_count": 0,
                    "matched_prior_requests": [],
                    "source_origin_note": "Source origin could not be established.",
                    "reverse_image_search_status": "External reverse image search is not available in this analysis.",
                    "disclaimer": "Audio-only verification.",
                },
                "forensic_observations": {
                    "ai_generation_assessment": "NOT ASSESSED (No dedicated AI generation detector integrated)",
                    "deepfake_assessment": "NOT ASSESSED (No dedicated deepfake detector integrated)",
                    "external_reverse_image_search": "NOT AVAILABLE",
                    "disclaimer": "Technical indicators do not establish digital tampering.",
                },
                "frames_count": 0,
            }

        # 11. Persist Claim and ClaimOccurrence records
        saved_db_claims: List[Claim] = []
        claim_occurrences_map: Dict[str, List[Dict[str, Any]]] = {}

        for item in target_claims_to_persist:
            claim_type_val = item.get("claim_type")
            if hasattr(claim_type_val, "value"):
                claim_type_val = claim_type_val.value
            verifiability_val = item.get("verifiability")
            if hasattr(verifiability_val, "value"):
                verifiability_val = verifiability_val.value
            importance_val = item.get("importance")
            if hasattr(importance_val, "value"):
                importance_val = importance_val.value

            db_claim = Claim(
                request_id=v_request.id,
                claim_text=item["text"],
                normalized_text=item.get("normalized_text", item["text"].lower()),
                claim_type=claim_type_val or "FACTUAL",
                verifiability=verifiability_val or "VERIFIABLE",
                importance=importance_val or "HIGH",
                entities=item.get("entities", []),
                dates=item.get("dates", []),
                locations=item.get("locations", []),
                numbers=item.get("numbers", []),
                source_attributions=item.get("source_attributions", []),
                original_sentence=item.get("original_sentence", item["text"]),
                extraction_method=item.get("extraction_method", "multimodal"),
                status="extracted",
            )
            db.add(db_claim)
            db.flush()
            saved_db_claims.append(db_claim)

            # Persist ClaimOccurrence records
            occ_list_for_claim = []
            for occ in item.get("occurrences", []):
                db_occ = ClaimOccurrence(
                    claim_id=db_claim.id,
                    media_verification_id=db_media_verif.id,
                    source_type=occ.get("source_type", "AUDIO_TRANSCRIPT"),
                    timestamp_start=occ.get("timestamp_start", 0.0),
                    timestamp_end=occ.get("timestamp_end", 0.0),
                    frame_id=occ.get("frame_id"),
                    transcript_segment_id=occ.get("transcript_segment_id"),
                    ocr_block_id=occ.get("ocr_block_id"),
                    text=occ.get("text", item["text"]),
                    confidence=occ.get("confidence"),
                )
                db.add(db_occ)
                db.flush()

                occ_list_for_claim.append({
                    "id": db_occ.id,
                    "claim_id": db_claim.id,
                    "source_type": db_occ.source_type,
                    "timestamp_start": db_occ.timestamp_start,
                    "timestamp_end": db_occ.timestamp_end,
                    "formatted_timestamp": occ.get("formatted_timestamp") or f"{int(db_occ.timestamp_start)}s",
                    "frame_id": db_occ.frame_id,
                    "frame_number": occ.get("frame_number"),
                    "transcript_segment_id": db_occ.transcript_segment_id,
                    "text": db_occ.text,
                    "confidence": db_occ.confidence,
                })

            claim_occurrences_map[f"claim_{db_claim.id}"] = {
                "occurrences": occ_list_for_claim,
                "primary_origin": item.get("primary_origin", "AUDIO_TRANSCRIPT"),
                "start_time": item.get("start_time") or (occ_list_for_claim[0]["timestamp_start"] if occ_list_for_claim else 0.0),
                "end_time": item.get("end_time") or (occ_list_for_claim[0]["timestamp_end"] if occ_list_for_claim else 0.0),
                "formatted_timestamp": item.get("formatted_timestamp") or (occ_list_for_claim[0]["formatted_timestamp"] if occ_list_for_claim else "00:00"),
            }

        db.commit()

        # 12. Multi-Source Web Search & Discovery (Part 4)
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

        # 13. Evidence Extraction & Comparison (Part 5)
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

        # 14. Final Verdict & Evidence Confidence (Part 6)
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

        # 15. Update request status
        v_request.status = "completed"
        v_request.completed_at = datetime.now(timezone.utc)
        record_verification_event(
            db=db,
            request_id=v_request.id,
            stage_name="pipeline",
            event_type="PROCESSING_COMPLETED",
            status="success",
            details={"status": "completed", "claims_count": len(saved_db_claims), "media_type": media_type},
        )
        db.commit()

        # Build claim response schemas with occurrences
        claims_response = []
        for c in saved_db_claims:
            c_meta = claim_occurrences_map.get(f"claim_{c.id}", {})
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
                "extraction_method": c.extraction_method or "multimodal",
                "status": c.status,
                "start_time": c_meta.get("start_time"),
                "end_time": c_meta.get("end_time"),
                "formatted_timestamp": c_meta.get("formatted_timestamp"),
                "primary_origin": c_meta.get("primary_origin", "AUDIO_TRANSCRIPT"),
                "occurrences": c_meta.get("occurrences", []),
            })

        # Format transcript segments for response
        segments_response = []
        for seg in transcription_result.segments:
            segments_response.append({
                "id": None,
                "sequence": seg.sequence,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "formatted_timestamp": seg.formatted_timestamp,
                "text": seg.text,
                "confidence": seg.confidence,
            })

        return {
            "request_id": v_request.id,
            "media_file_id": db_media.id,
            "media_verification_id": db_media_verif.id,
            "status": "completed",
            "forensics": {
                "media_type": media_type,
                "duration_seconds": metadata.get("duration_seconds", 0.0),
                "file_size_bytes": file_meta["file_size_bytes"],
                "file_hash_sha256": file_meta["file_hash_sha256"],
                "original_filename": file_meta["original_filename"],
                "stored_filename": file_meta["stored_filename"],
                "mime_type": file_meta["mime_type"],
                "width": metadata.get("width"),
                "height": metadata.get("height"),
                "video_codec": metadata.get("video_codec"),
                "audio_codec": metadata.get("audio_codec"),
                "sample_rate": metadata.get("sample_rate"),
                "channels": metadata.get("channels"),
                "bitrate": metadata.get("bitrate"),
                "has_audio_track": has_audio,
                "technical_indicators": metadata.get("technical_indicators", {}),
            },
            "transcription": {
                "raw_transcript": transcription_result.raw_text,
                "normalized_transcript": transcription_result.normalized_text,
                "language": transcription_result.language,
                "is_code_switched": transcription_result.is_code_switched,
                "transcription_confidence": transcription_result.overall_confidence,
                "confidence_category": (
                    "High" if transcription_result.overall_confidence >= 80
                    else "Moderate" if transcription_result.overall_confidence >= 60
                    else "Low"
                ),
                "low_confidence_warning": transcription_result.low_confidence_warning,
                "word_count": len(transcription_result.normalized_text.split()),
                "duration_seconds": metadata.get("duration_seconds", 0.0),
                "segments": segments_response,
                "detected_urls": spoken_urls,
                "detected_quotes": direct_quotes,
            },
            # Part 10 Multimedia additions
            "frames": multimedia_data.get("frames", []),
            "timeline": multimedia_data.get("timeline", []),
            "alignment": multimedia_data.get("alignment"),
            "reused_footage": multimedia_data.get("reused_footage"),
            "forensic_observations": multimedia_data.get("forensic_observations"),
            "frames_count": len(multimedia_data.get("frames", [])),
            "claims": claims_response,
            "queries": queries_schemas,
            "sources": list(discovered_sources_map.values()),
            "evidence": evidence_schemas,
            "comparisons": comparison_schemas,
            "verdicts": verdicts_response,
            "claims_count": len(claims_response),
            "sources_count": len(discovered_sources_map),
            "evidence_count": len(evidence_schemas),
            "authenticity_disclaimer": (
                "TruthLens AI verifies the factual claims spoken or shown within audio and video recordings against authoritative "
                "web sources. High evidence credibility indicates verified factual reporting, but does not certify "
                "that the audio or video file itself is digitally authentic, unedited, or free from synthetic generation."
            ),
        }
