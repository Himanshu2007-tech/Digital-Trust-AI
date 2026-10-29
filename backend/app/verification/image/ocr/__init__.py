from app.verification.image.ocr.base import OCRResult, OCRBlockItem
from app.verification.image.ocr.engine import (
    UnifiedOCREngine,
    TesseractOCREngine,
    FallbackOCREngine,
    normalize_ocr_text
)
from app.verification.image.ocr.patterns import (
    extract_detected_urls,
    extract_social_handles,
    extract_metrics,
    extract_dates
)

__all__ = [
    "OCRResult",
    "OCRBlockItem",
    "UnifiedOCREngine",
    "TesseractOCREngine",
    "FallbackOCREngine",
    "normalize_ocr_text",
    "extract_detected_urls",
    "extract_social_handles",
    "extract_metrics",
    "extract_dates"
]
