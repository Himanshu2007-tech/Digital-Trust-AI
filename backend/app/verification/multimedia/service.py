import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.media_verification import MediaVerification
from app.models.video_frame import VideoFrame
from app.models.claim_occurrence import ClaimOccurrence
from app.models.claim import Claim
from app.verification.extractors.hybrid import HybridClaimExtractor
from app.verification.domain_models import ExtractedClaimItem, ClaimType, Verifiability, Importance
from app.verification.multimedia.sampling import VideoFrameSampler, ExtractedFrameItem
from app.verification.multimedia.visual_extractor import FrameVisualExtractor
from app.verification.multimedia.deduplication import MultimodalClaimDeduplicator
from app.verification.multimedia.alignment import TimelineAndAlignmentAnalyzer
from app.verification.multimedia.reused_footage import check_reused_footage_in_database

logger = logging.getLogger(__name__)


class MultimediaAnalysisService:
    """
    Advanced Video & Multimedia Analysis Engine (Part 10).
    Orchestrates:
    1. Keyframe sampling (fixed interval + scene change detection)
    2. Frame OCR & on-screen visual information extraction (reusing Part 8)
    3. Multimodal claim fusion & deduplication (linking audio + visual occurrences)
    4. Unified chronological media timeline generation
    5. Audio-visual thematic alignment & context mismatch assessment
    6. Internal database reused footage fingerprint search
    7. Strict forensic boundaries: no fabricated deepfake or AI detection scores.
    """

    def __init__(
        self,
        frame_sampler: Optional[VideoFrameSampler] = None,
        visual_extractor: Optional[FrameVisualExtractor] = None,
        claim_extractor: Optional[HybridClaimExtractor] = None,
        claim_deduplicator: Optional[MultimodalClaimDeduplicator] = None,
        timeline_analyzer: Optional[TimelineAndAlignmentAnalyzer] = None,
    ):
        self.frame_sampler = frame_sampler or VideoFrameSampler()
        self.visual_extractor = visual_extractor or FrameVisualExtractor()
        self.claim_extractor = claim_extractor or HybridClaimExtractor()
        self.claim_deduplicator = claim_deduplicator or MultimodalClaimDeduplicator()
        self.timeline_analyzer = timeline_analyzer or TimelineAndAlignmentAnalyzer()

    def analyze_video_multimedia(
        self,
        video_path: str,
        media_verification_id: int,
        duration_seconds: float,
        transcript_segments: List[Any],
        raw_audio_claims: List[Dict[str, Any]],
        db: Session,
        raw_bytes: Optional[bytes] = None,
        injected_frames: Optional[List[ExtractedFrameItem]] = None,
        injected_ocr_map: Optional[Dict[int, str]] = None,
        max_claims: int = 5,
    ) -> Dict[str, Any]:
        """
        Executes complete multimedia analysis for video files.
        """
        # 1. Video Frame Sampling & Scene Change Detection
        sampled_frames = self.frame_sampler.sample_frames(
            video_path=video_path,
            duration_seconds=duration_seconds,
            raw_bytes=raw_bytes,
            injected_frames=injected_frames,
        )

        # 2. Frame OCR & Visual Context Extraction
        analyzed_frames: List[Dict[str, Any]] = []
        visual_claims_raw: List[Dict[str, Any]] = []
        saved_db_frames: List[VideoFrame] = []
        frame_hashes: List[str] = []

        for frame_item in sampled_frames:
            injected_text = injected_ocr_map.get(frame_item.frame_number) if injected_ocr_map else None
            frame_data = self.visual_extractor.analyze_frame(frame_item, injected_ocr_text=injected_text)
            analyzed_frames.append(frame_data)
            frame_hashes.append(frame_item.image_hash)

            # Save VideoFrame entity in database
            db_frame = VideoFrame(
                media_verification_id=media_verification_id,
                timestamp=frame_data["timestamp"],
                frame_number=frame_data["frame_number"],
                width=frame_data["width"],
                height=frame_data["height"],
                selection_method=frame_data["selection_method"],
                image_hash=frame_data["image_hash"],
                stored_path=frame_data["stored_path"],
                ocr_text=frame_data["ocr_text"],
                ocr_confidence=frame_data["ocr_confidence"],
                ocr_blocks=frame_data["ocr_blocks"],
                visual_context=frame_data["visual_context"],
            )
            db.add(db_frame)
            db.flush()
            saved_db_frames.append(db_frame)
            frame_data["id"] = db_frame.id

            # If frame has informative text, extract potential visual claims
            ocr_text = frame_data["ocr_text"] or ""
            if ocr_text and len(ocr_text) > 12:
                try:
                    c_items = self.claim_extractor.extract_claims(
                        ocr_text,
                        context=f"Visual on-screen graphic at timestamp {frame_data['formatted_timestamp']}"
                    )
                    for ci in c_items:
                        visual_claims_raw.append({
                            "text": ci.text,
                            "claim_type": ci.claim_type,
                            "verifiability": ci.verifiability,
                            "importance": ci.importance,
                            "entities": ci.entities,
                            "dates": ci.dates,
                            "numbers": ci.numbers,
                            "timestamp": frame_data["timestamp"],
                            "formatted_timestamp": frame_data["formatted_timestamp"],
                            "frame_id": db_frame.id,
                            "frame_number": db_frame.frame_number,
                            "ocr_confidence": frame_data["ocr_confidence"],
                        })
                except Exception as c_err:
                    logger.debug(f"Claim extraction note from frame {db_frame.frame_number}: {c_err}")

        # 3. Multimodal Claim Fusion & Deduplication
        fused_claims = self.claim_deduplicator.fuse_and_deduplicate(
            audio_claims=raw_audio_claims,
            visual_claims=visual_claims_raw,
            max_claims=max_claims,
        )

        # 4. Timeline Construction
        timeline_events = self.timeline_analyzer.build_timeline(
            duration_seconds=duration_seconds,
            segments=transcript_segments,
            frames=analyzed_frames,
            claims=fused_claims,
        )

        # 5. Audio-Visual Alignment & Mismatch Assessment
        alignment_assessment = self.timeline_analyzer.evaluate_audio_visual_alignment(
            segments=transcript_segments,
            frames=analyzed_frames,
        )

        # 6. Reused Footage Internal Fingerprint Search
        reused_footage_result = check_reused_footage_in_database(
            frame_hashes=frame_hashes,
            current_media_verification_id=media_verification_id,
            db=db,
        )

        # 7. Media Forensics & AI/Deepfake Non-Hallucination Disclosures
        forensic_observations = {
            "ai_generation_assessment": "NOT ASSESSED (No dedicated AI generation detector integrated)",
            "deepfake_assessment": "NOT ASSESSED (No dedicated deepfake detector integrated)",
            "external_reverse_image_search": "NOT AVAILABLE",
            "frame_sampling_method": "HYBRID (Interval + Scene Change Detection)",
            "frames_analyzed_count": len(analyzed_frames),
            "reused_footage": reused_footage_result,
            "alignment": alignment_assessment,
            "disclaimer": (
                "TruthLens AI performs factual verification of claims against independent news sources. "
                "Technical observations (codecs, container, audio-visual alignment, frame hashing) are technical indicators only "
                "and do not constitute proof of synthetic generation or pixel tampering."
            ),
        }

        db.commit()

        return {
            "frames": analyzed_frames,
            "fused_claims": fused_claims,
            "timeline": timeline_events,
            "alignment": alignment_assessment,
            "reused_footage": reused_footage_result,
            "forensic_observations": forensic_observations,
            "frames_count": len(analyzed_frames),
        }
