import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image
import io

from app.verification.image.ocr.engine import UnifiedOCREngine
from app.verification.image.preprocessor import ImagePreprocessor
from app.verification.image.ocr.base import OCRResult
from app.verification.image.ocr.patterns import (
    extract_ocr_urls,
    extract_ocr_handles,
    extract_ocr_metrics,
    extract_ocr_dates,
)
from app.verification.multimedia.sampling import ExtractedFrameItem

logger = logging.getLogger(__name__)


# Keywords indicating formal news or document graphics
DOCUMENT_KEYWORDS = {
    "circular", "gazette", "notification", "ministry", "official", "department",
    "order", "directive", "act", "section", "govt", "government", "press release"
}

CHART_KEYWORDS = {
    "graph", "chart", "inflation", "gdp", "growth", "percent", "%", "index", "rate", "statistics"
}


def detect_visual_context_observations(
    ocr_text: str,
    frame_width: int,
    frame_height: int,
    ocr_blocks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Formulates non-hallucinatory, strictly observational visual context indicators.
    Follows journalistic principle:
    - Never fabricates specific identities (e.g. 'Person visible in frame', NOT 'Person X')
    - Notes possible document or news graphic formats as observations, NOT certified proof.
    """
    text_lower = ocr_text.lower()
    words = set(re.findall(r"\b\w+\b", text_lower))

    observations: List[str] = []
    has_document_indicator = bool(words.intersection(DOCUMENT_KEYWORDS))
    has_chart_indicator = bool(words.intersection(CHART_KEYWORDS))

    # Check for broadcast lower-third / ticker text (blocks in bottom 30% of frame height)
    ticker_text_present = False
    if ocr_blocks and frame_height > 0:
        bottom_threshold = frame_height * 0.70
        for block in ocr_blocks:
            bbox = block.get("bbox", [0, 0, 0, 0])
            if len(bbox) == 4 and bbox[1] >= bottom_threshold:
                ticker_text_present = True
                break

    if has_document_indicator:
        observations.append("POSSIBLE DOCUMENT/SCREENSHOT: Official terminology or formal gazette format observed.")
    if has_chart_indicator:
        observations.append("POSSIBLE CHART/STATISTICAL GRAPHIC: Statistical metrics or economic indicators detected on-screen.")
    if ticker_text_present:
        observations.append("ON-SCREEN LOWER-THIRD/TICKER: Headline or caption typography observed in lower frame region.")

    # General non-accusatory visual context
    if not observations:
        observations.append("Standard multimedia video frame.")

    return {
        "is_possible_document": has_document_indicator,
        "is_possible_chart": has_chart_indicator,
        "is_broadcast_ticker": ticker_text_present,
        "observations": observations,
        "disclaimer": (
            "Visual context indicators represent automated typographical and spatial layout observations. "
            "They do not certify whether the on-screen graphics are authentic, unedited, or officially sanctioned."
        ),
    }


class FrameVisualExtractor:
    """
    Extracts text, statistics, headlines, and visual context from video keyframes
    by reusing the Part 8 OCR engine and preprocessor.
    """

    def __init__(
        self,
        ocr_engine: Optional[UnifiedOCREngine] = None,
        preprocessor: Optional[ImagePreprocessor] = None,
    ):
        self.ocr_engine = ocr_engine or UnifiedOCREngine()
        self.preprocessor = preprocessor or ImagePreprocessor()

    def analyze_frame(
        self,
        frame: ExtractedFrameItem,
        injected_ocr_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs OCR and visual information extraction on a single keyframe.
        """
        # Allow pre-injected OCR text (for testing / deterministic simulation)
        if injected_ocr_text is not None:
            normalized = injected_ocr_text.strip()
            raw = injected_ocr_text
            conf = 95.0
            blocks: List[Dict[str, Any]] = [
                {"text": normalized, "confidence": 95.0, "bbox": [50, 280, 540, 50]}
            ]
        else:
            try:
                preprocessed_img, _ = self.preprocessor.process(frame.image_bytes)
                ocr_res: OCRResult = self.ocr_engine.extract(preprocessed_img)
                raw = ocr_res.raw_text
                normalized = ocr_res.normalized_text
                conf = ocr_res.overall_confidence
                blocks = [b.to_dict() for b in ocr_res.blocks]
            except Exception as exc:
                logger.warning(f"Frame OCR error on frame {frame.frame_number}: {exc}")
                raw = ""
                normalized = ""
                conf = 0.0
                blocks = []

        # Extract structured entities from on-screen text
        detected_urls = extract_ocr_urls(normalized)
        detected_handles = extract_ocr_handles(normalized)
        detected_metrics = extract_ocr_metrics(normalized)
        detected_dates = extract_ocr_dates(normalized)

        # Detect visual context & non-accusatory observations
        context_data = detect_visual_context_observations(
            ocr_text=normalized,
            frame_width=frame.width,
            frame_height=frame.height,
            ocr_blocks=blocks,
        )

        return {
            "frame_number": frame.frame_number,
            "timestamp": frame.timestamp,
            "formatted_timestamp": frame.formatted_timestamp,
            "selection_method": frame.selection_method,
            "image_hash": frame.image_hash,
            "stored_path": frame.stored_path,
            "width": frame.width,
            "height": frame.height,
            "ocr_text": normalized,
            "raw_ocr_text": raw,
            "ocr_confidence": conf,
            "ocr_blocks": blocks,
            "detected_urls": detected_urls,
            "detected_handles": detected_handles,
            "detected_metrics": detected_metrics,
            "detected_dates": detected_dates,
            "visual_context": context_data,
        }
