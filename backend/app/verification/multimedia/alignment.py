import re
import logging
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def extract_content_keywords(text: str) -> set:
    """Extracts informative content words (>3 chars, non-stopwords)."""
    stopwords = {
        "this", "that", "with", "from", "have", "were", "what", "when", "where",
        "their", "there", "about", "which", "will", "would", "could", "should"
    }
    words = set(w for w in re.findall(r"\b[a-zA-Z]{4,}\b", text.lower()))
    return words - stopwords


class TimelineAndAlignmentAnalyzer:
    """
    Constructs unified chronological multimedia timeline and analyzes
    thematic alignment or mismatch between speech audio and visible on-screen text.
    """

    def build_timeline(
        self,
        duration_seconds: float,
        segments: List[Any],
        frames: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Creates unified chronological timeline combining speech events,
        scene changes, on-screen text appearances, and extracted verifiable claims.
        """
        timeline_events: List[Dict[str, Any]] = []

        # 1. Add Speech Events
        for seg in segments:
            timeline_events.append({
                "timestamp": round(seg.start_time, 2),
                "timestamp_end": round(seg.end_time, 2),
                "formatted_timestamp": f"{int(seg.start_time // 60):02d}:{int(seg.start_time % 60):02d}",
                "event_type": "AUDIO_SPEECH",
                "label": "Spoken Statement",
                "description": seg.text,
                "confidence": seg.confidence,
                "badge_color": "cyan",
            })

        # 2. Add Keyframe / Scene Change Events
        for frm in frames:
            ts = frm.get("timestamp", 0.0)
            sel_method = frm.get("selection_method", "FIXED_INTERVAL")
            ocr_text = frm.get("ocr_text", "").strip()

            label = (
                "Scene Change" if sel_method == "SCENE_CHANGE"
                else "High Text Density" if sel_method == "HIGH_TEXT_DENSITY"
                else "Sampled Keyframe"
            )

            timeline_events.append({
                "timestamp": round(ts, 2),
                "timestamp_end": round(ts, 2),
                "formatted_timestamp": f"{int(ts // 60):02d}:{int(ts % 60):02d}",
                "event_type": "KEYFRAME_SCENE",
                "label": label,
                "description": f"Keyframe #{frm.get('frame_number', 0)} ({sel_method})",
                "frame_id": frm.get("id"),
                "badge_color": "slate",
            })

            # If frame has substantial on-screen text, add as visual text event
            if ocr_text and len(ocr_text) > 8:
                timeline_events.append({
                    "timestamp": round(ts, 2),
                    "timestamp_end": round(ts, 2),
                    "formatted_timestamp": f"{int(ts // 60):02d}:{int(ts % 60):02d}",
                    "event_type": "VISUAL_TEXT",
                    "label": "On-Screen Graphic / Ticker",
                    "description": ocr_text,
                    "confidence": frm.get("ocr_confidence"),
                    "frame_id": frm.get("id"),
                    "badge_color": "indigo",
                })

        # 3. Add Verifiable Claim Events
        for idx, clm in enumerate(claims):
            for occ in clm.get("occurrences", []):
                ts = occ.get("timestamp_start", 0.0)
                timeline_events.append({
                    "timestamp": round(ts, 2),
                    "timestamp_end": round(occ.get("timestamp_end", ts), 2),
                    "formatted_timestamp": f"{int(ts // 60):02d}:{int(ts % 60):02d}",
                    "event_type": "VERIFIABLE_CLAIM",
                    "label": f"Claim #{idx + 1} ({occ.get('source_type')})",
                    "description": clm.get("text", ""),
                    "claim_id": clm.get("id"),
                    "badge_color": "emerald",
                })

        # Sort all timeline events chronologically
        timeline_events.sort(key=lambda x: (x["timestamp"], 0 if x["event_type"] == "KEYFRAME_SCENE" else 1))
        return timeline_events

    def evaluate_audio_visual_alignment(
        self,
        segments: List[Any],
        frames: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluates thematic consistency or divergence between audio track speech
        and visible on-screen graphics in overlapping timestamp windows.
        """
        alignments: List[Dict[str, Any]] = []
        mismatches: List[Dict[str, Any]] = []

        for frm in frames:
            frm_text = frm.get("ocr_text", "").strip()
            if not frm_text or len(frm_text) < 12:
                continue

            frm_ts = frm.get("timestamp", 0.0)
            frm_words = extract_content_keywords(frm_text)
            if not frm_words:
                continue

            # Find speech segments occurring within +/- 6 seconds of this frame
            overlapping_segs = [
                s for s in segments
                if (s.start_time <= frm_ts + 6.0 and s.end_time >= frm_ts - 6.0)
            ]

            for seg in overlapping_segs:
                seg_words = extract_content_keywords(seg.text)
                if not seg_words:
                    continue

                common_words = frm_words.intersection(seg_words)
                overlap_ratio = len(common_words) / float(min(len(frm_words), len(seg_words)))

                fmt_ts = f"{int(frm_ts // 60):02d}:{int(frm_ts % 60):02d}"

                if overlap_ratio >= 0.25:
                    alignments.append({
                        "status": "AUDIO_VISUAL_CONTENT_ALIGNMENT",
                        "timestamp": round(frm_ts, 2),
                        "formatted_timestamp": fmt_ts,
                        "frame_number": frm.get("frame_number"),
                        "audio_snippet": seg.text,
                        "visual_snippet": frm_text,
                        "common_entities": list(common_words),
                        "observation": f"Audio statement and on-screen graphic at [{fmt_ts}] corroborate the same topic.",
                    })
                elif overlap_ratio == 0.0 and len(frm_words) >= 4 and len(seg_words) >= 4:
                    mismatches.append({
                        "status": "POSSIBLE_AUDIO_VISUAL_CONTEXT_MISMATCH",
                        "timestamp": round(frm_ts, 2),
                        "formatted_timestamp": fmt_ts,
                        "frame_number": frm.get("frame_number"),
                        "audio_snippet": seg.text,
                        "visual_snippet": frm_text,
                        "observation": f"Audio discusses one subject while on-screen text displays unrelated content at [{fmt_ts}].",
                    })

        # Overall alignment assessment
        if alignments and not mismatches:
            summary_status = "CONSISTENT_ALIGNMENT"
            summary_note = "Spoken audio track and on-screen typography align consistently across keyframes."
        elif mismatches and not alignments:
            summary_status = "CONTEXT_DIVERGENCE_OBSERVED"
            summary_note = "Discrepancy detected between spoken statements and visible on-screen titles."
        elif alignments and mismatches:
            summary_status = "MIXED_ALIGNMENT"
            summary_note = "Certain keyframes exhibit thematic alignment, while other segments diverge in context."
        else:
            summary_status = "INSUFFICIENT_ONSCREEN_TEXT"
            summary_note = "On-screen text was minimal or absent; alignment evaluation inconclusive."

        return {
            "summary_status": summary_status,
            "summary_note": summary_note,
            "alignments_count": len(alignments),
            "mismatches_count": len(mismatches),
            "alignments": alignments[:5],
            "mismatches": mismatches[:5],
            "disclaimer": (
                "Audio-visual alignment reflects thematic similarity between speech and visible graphics. "
                "Alignment or mismatch does NOT certify digital manipulation or prove factual truth."
            ),
        }
