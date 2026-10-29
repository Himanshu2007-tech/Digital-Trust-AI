from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional


@dataclass
class OCRBlockItem:
    """Represents an atomic recognized text block or line with spatial coordinates."""
    text: str
    confidence: float  # 0.0 to 100.0
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    block_num: int = 0
    par_num: int = 0
    line_num: int = 0
    word_num: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 1),
            "bbox": list(self.bbox),
            "block_num": self.block_num,
            "par_num": self.par_num,
            "line_num": self.line_num,
            "word_num": self.word_num
        }


@dataclass
class OCRResult:
    """Complete extracted OCR analysis from an image."""
    raw_text: str
    normalized_text: str
    overall_confidence: float  # 0.0 to 100.0
    blocks: List[OCRBlockItem] = field(default_factory=list)
    detected_urls: List[str] = field(default_factory=list)
    detected_handles: List[str] = field(default_factory=list)
    detected_metrics: Dict[str, str] = field(default_factory=dict)
    detected_dates: List[str] = field(default_factory=list)
    engine_used: str = "tesseract"
    low_confidence_warning: bool = False
    word_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "overall_confidence": round(self.overall_confidence, 2),
            "word_count": self.word_count,
            "engine_used": self.engine_used,
            "low_confidence_warning": self.low_confidence_warning,
            "detected_urls": self.detected_urls,
            "detected_handles": self.detected_handles,
            "detected_metrics": self.detected_metrics,
            "detected_dates": self.detected_dates,
            "blocks": [b.to_dict() for b in self.blocks]
        }
