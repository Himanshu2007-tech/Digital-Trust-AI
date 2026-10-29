from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


def format_seconds_to_timestamp(seconds: float) -> str:
    """Formats seconds into MM:SS format (e.g., 65.5 -> '01:05')."""
    total_sec = int(seconds)
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}"


@dataclass
class TranscriptSegmentItem:
    """Timestamped atomic speech segment for claim traceability."""
    start_time: float
    end_time: float
    text: str
    confidence: Optional[float] = None
    sequence: int = 0

    @property
    def formatted_timestamp(self) -> str:
        return f"{format_seconds_to_timestamp(self.start_time)} - {format_seconds_to_timestamp(self.end_time)}"

    @property
    def timestamp_label(self) -> str:
        return self.formatted_timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "formatted_timestamp": self.formatted_timestamp,
            "timestamp_label": self.timestamp_label,
            "text": self.text,
            "confidence": round(self.confidence, 2) if self.confidence is not None else None,
        }


@dataclass
class TranscriptionResult:
    """Complete speech-to-text output."""
    raw_text: str
    normalized_text: str
    language: str = "en"
    is_code_switched: bool = False
    overall_confidence: Optional[float] = None  # Speech recognition clarity
    low_confidence_warning: bool = False
    segments: List[TranscriptSegmentItem] = field(default_factory=list)
    detected_urls: List[str] = field(default_factory=list)
    detected_quotes: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = "whisper"
    has_speech: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "language": self.language,
            "is_code_switched": self.is_code_switched,
            "overall_confidence": round(self.overall_confidence, 2) if self.overall_confidence is not None else None,
            "low_confidence_warning": self.low_confidence_warning,
            "segments": [s.to_dict() for s in self.segments],
            "detected_urls": self.detected_urls,
            "detected_quotes": self.detected_quotes,
            "provider": self.provider,
            "has_speech": self.has_speech,
        }
