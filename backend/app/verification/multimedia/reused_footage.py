import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.video_frame import VideoFrame

logger = logging.getLogger(__name__)


def check_reused_footage_in_database(
    frame_hashes: List[str],
    current_media_verification_id: Optional[int],
    db: Session,
) -> Dict[str, Any]:
    """
    Compares frame cryptographic SHA-256 fingerprints against past analyses
    stored internally in the TruthLens database.
    Strictly follows non-hallucination rules:
    - Discloses that external reverse image search is not available.
    - Does NOT claim to identify original uploader or first recording.
    """
    if not frame_hashes:
        return {
            "reused_footage_detected": False,
            "matching_frames_count": 0,
            "matched_prior_requests": [],
            "source_origin_note": "Source origin could not be established.",
            "reverse_image_search_status": "External reverse image search is not available in this analysis.",
            "disclaimer": "Internal database matches indicate duplicate frame re-analysis within TruthLens only."
        }

    # Query existing frames with matching hash belonging to DIFFERENT media verifications
    query = db.query(VideoFrame).filter(VideoFrame.image_hash.in_(frame_hashes))
    if current_media_verification_id:
        query = query.filter(VideoFrame.media_verification_id != current_media_verification_id)

    matches = query.limit(10).all()

    matched_records: List[Dict[str, Any]] = []
    seen_hashes = set()

    for m in matches:
        if m.image_hash not in seen_hashes:
            seen_hashes.add(m.image_hash)
            matched_records.append({
                "frame_id": m.id,
                "media_verification_id": m.media_verification_id,
                "image_hash": m.image_hash,
                "prior_timestamp": m.timestamp,
                "selection_method": m.selection_method,
                "match_label": "MATCHING FRAME FOUND IN PREVIOUS ANALYSIS",
                "analysis_note": "Identical frame cryptographic fingerprint was previously verified in TruthLens DB.",
            })

    reused_detected = len(matched_records) > 0

    return {
        "reused_footage_detected": reused_detected,
        "matching_frames_count": len(matched_records),
        "matched_prior_requests": matched_records,
        "source_origin_note": "Source origin could not be established.",
        "reverse_image_search_status": "External reverse image search is not available in this analysis.",
        "disclaimer": (
            "Internal database matches reflect previous file uploads within the TruthLens platform. "
            "They do not establish original authorship or external internet provenance."
        ),
    }
