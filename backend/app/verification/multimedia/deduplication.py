import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from app.verification.domain_models import ExtractedClaimItem, ClaimType, Verifiability, Importance

logger = logging.getLogger(__name__)


def calculate_claim_similarity(text_a: str, text_b: str) -> float:
    """
    Computes word-level Jaccard similarity between two claim statements.
    """
    words_a = set(w for w in re.findall(r"\w+", text_a.lower()) if len(w) > 2)
    words_b = set(w for w in re.findall(r"\w+", text_b.lower()) if len(w) > 2)

    if not words_a or not words_b:
        return 0.0

    intersection = len(words_a.intersection(words_b))
    union = len(words_a.union(words_b))
    return intersection / float(union) if union > 0 else 0.0


class MultimodalClaimDeduplicator:
    """
    Fuses and deduplicates claims extracted from speech audio transcripts and on-screen frame OCR.
    Maintains multiple granular occurrences for identical or closely corroborating statements.
    """

    def __init__(self, similarity_threshold: float = 0.45):
        self.similarity_threshold = similarity_threshold

    def fuse_and_deduplicate(
        self,
        audio_claims: List[Dict[str, Any]],
        visual_claims: List[Dict[str, Any]],
        max_claims: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fuses audio and visual claims, deduplicating repetitive instances while
        preserving every appearance as a ClaimOccurrence.

        Parameters:
            audio_claims: Extracted claims from audio transcript with segment references.
            visual_claims: Extracted claims from on-screen keyframes with frame references.
            max_claims: Maximum unique claims to retain for downstream search & verification.

        Returns:
            List of unified claim dicts, each with an 'occurrences' list.
        """
        fused_claims: List[Dict[str, Any]] = []

        # 1. Seed with Audio Claims
        for ac in audio_claims:
            claim_text = ac.get("text", "").strip()
            if not claim_text:
                continue

            occurrences = [{
                "source_type": "AUDIO_TRANSCRIPT",
                "timestamp_start": ac.get("start_time", 0.0) or 0.0,
                "timestamp_end": ac.get("end_time", 0.0) or 0.0,
                "frame_id": None,
                "transcript_segment_id": ac.get("segment_id"),
                "ocr_block_id": None,
                "text": claim_text,
                "confidence": ac.get("confidence", 0.90),
                "formatted_timestamp": ac.get("formatted_timestamp") or "00:00",
            }]

            fused_claims.append({
                "text": claim_text,
                "normalized_text": ac.get("normalized_text", claim_text.lower()),
                "claim_type": ac.get("claim_type", ClaimType.FACTUAL),
                "verifiability": ac.get("verifiability", Verifiability.VERIFIABLE),
                "importance": ac.get("importance", Importance.HIGH),
                "entities": ac.get("entities", []),
                "dates": ac.get("dates", []),
                "locations": ac.get("locations", []),
                "numbers": ac.get("numbers", []),
                "source_attributions": ac.get("source_attributions", []),
                "original_sentence": ac.get("original_sentence", claim_text),
                "extraction_method": ac.get("extraction_method", "audio_transcript"),
                "primary_origin": "AUDIO_TRANSCRIPT",
                "occurrences": occurrences,
            })

        # 2. Match and Merge Visual Claims
        for vc in visual_claims:
            v_text = vc.get("text", "").strip()
            if not v_text or len(v_text) < 10:
                continue

            v_timestamp = vc.get("timestamp", 0.0)
            v_frame_id = vc.get("frame_id")
            v_frame_num = vc.get("frame_number", 0)
            v_fmt_ts = vc.get("formatted_timestamp") or f"{int(v_timestamp)}s"

            v_occurrence = {
                "source_type": "VISUAL_OCR",
                "timestamp_start": v_timestamp,
                "timestamp_end": v_timestamp,
                "frame_id": v_frame_id,
                "frame_number": v_frame_num,
                "transcript_segment_id": None,
                "ocr_block_id": None,
                "text": v_text,
                "confidence": vc.get("ocr_confidence", 85.0),
                "formatted_timestamp": v_fmt_ts,
            }

            # Check if this visual claim matches an already extracted audio or visual claim
            matched_claim = None
            best_sim = 0.0

            for fc in fused_claims:
                sim = calculate_claim_similarity(v_text, fc["text"])
                if sim > best_sim:
                    best_sim = sim
                    matched_claim = fc

            if matched_claim is not None and best_sim >= self.similarity_threshold:
                # Merge occurrence into existing claim
                matched_claim["occurrences"].append(v_occurrence)
                # Enhance entities if visual text has numbers or dates
                if vc.get("numbers") and not matched_claim.get("numbers"):
                    matched_claim["numbers"] = vc["numbers"]
                if vc.get("dates") and not matched_claim.get("dates"):
                    matched_claim["dates"] = vc["dates"]
                # If claim appeared in both audio and video, mark as multimodal
                matched_claim["primary_origin"] = "MULTIMODAL (AUDIO + VISUAL)"
            else:
                # Novel visual on-screen claim
                fused_claims.append({
                    "text": v_text,
                    "normalized_text": v_text.lower(),
                    "claim_type": vc.get("claim_type", ClaimType.FACTUAL),
                    "verifiability": vc.get("verifiability", Verifiability.VERIFIABLE),
                    "importance": vc.get("importance", Importance.HIGH),
                    "entities": vc.get("entities", []),
                    "dates": vc.get("dates", []),
                    "locations": vc.get("locations", []),
                    "numbers": vc.get("numbers", []),
                    "source_attributions": vc.get("source_attributions", ["On-Screen Graphic"]),
                    "original_sentence": v_text,
                    "extraction_method": "frame_ocr",
                    "primary_origin": "VISUAL_OCR",
                    "occurrences": [v_occurrence],
                })

        return fused_claims[:max_claims]
