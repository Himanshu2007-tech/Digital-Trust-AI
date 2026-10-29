from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.verify import ExtractedClaimSchema
from app.schemas.search import DiscoveredSourceSchema
from app.schemas.evidence import EvidenceItemSchema, SourceComparisonSchema
from app.schemas.verdict import RequestVerdictResponse


class OCRBlockSchema(BaseModel):
    """Spatial bounding box and word-level confidence."""
    text: str = Field(..., description="Recognized word or phrase")
    confidence: float = Field(..., description="Word OCR confidence (0-100)")
    bbox: List[int] = Field(..., description="Bounding box [x, y, width, height]")
    block_num: int = Field(default=0)
    par_num: int = Field(default=0)
    line_num: int = Field(default=0)
    word_num: int = Field(default=0)


class ImageForensicDetailsSchema(BaseModel):
    """Technical metadata and privacy-sanitized image properties."""
    image_width: int = Field(..., description="Width in pixels")
    image_height: int = Field(..., description="Height in pixels")
    image_format: str = Field(..., description="Image container format (PNG, JPEG, etc.)")
    file_size_bytes: int = Field(..., description="Size in bytes")
    file_hash_sha256: str = Field(..., description="Cryptographic SHA-256 fingerprint")
    original_filename: str = Field(..., description="Client upload filename")
    sanitized_exif: Dict[str, Any] = Field(default_factory=dict, description="Sanitized EXIF metadata (GPS/PII removed)")
    ocr_engine: str = Field(default="tesseract", description="OCR engine utilized")
    preprocessing_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied image enhancement stages")


class ImageOCRSummarySchema(BaseModel):
    """Complete OCR extraction output with dual confidence metrics."""
    raw_text: str = Field(..., description="Raw text exactly as recognized by OCR")
    normalized_text: str = Field(..., description="Cleaned, normalized text used for claim extraction")
    ocr_confidence: float = Field(..., description="OCR text recognition clarity score (0.0 - 100.0)")
    word_count: int = Field(default=0, description="Total recognized words")
    low_confidence_warning: bool = Field(default=False, description="Flagged if OCR confidence is beneath quality threshold")
    detected_urls: List[str] = Field(default_factory=list, description="URLs visible within image text")
    detected_handles: List[str] = Field(default_factory=list, description="Social media handles recognized")
    detected_metrics: Dict[str, str] = Field(default_factory=dict, description="Engagement statistics recognized")
    detected_dates: List[str] = Field(default_factory=list, description="Dates or timestamps recognized")
    blocks: List[OCRBlockSchema] = Field(default_factory=list, description="Bounding boxes for recognized text elements")


class ImageVerificationResponse(BaseModel):
    """Comprehensive image forensic and factual verification dossier."""
    request_id: int = Field(..., description="Verification request ID")
    media_file_id: Optional[int] = Field(default=None, description="MediaFile record ID")
    image_verification_id: Optional[int] = Field(default=None, description="ImageVerification record ID")
    status: str = Field(..., description="Pipeline execution status: completed, partial, or failed")

    # Forensics & OCR
    forensics: ImageForensicDetailsSchema = Field(..., description="Technical file forensics")
    ocr: ImageOCRSummarySchema = Field(..., description="OCR text and spatial layout")

    # Verification Layers (Parts 3 - 6)
    claims: List[ExtractedClaimSchema] = Field(default_factory=list, description="Verifiable claims extracted from image text")
    sources: List[DiscoveredSourceSchema] = Field(default_factory=list, description="Web sources discovered for corroboration")
    evidence: List[EvidenceItemSchema] = Field(default_factory=list, description="Traceable evidence items extracted from sources")
    comparisons: List[SourceComparisonSchema] = Field(default_factory=list, description="Cross-source consistency comparisons")
    verdicts: Optional[RequestVerdictResponse] = Field(default=None, description="Overall dossier and per-claim verdicts")

    claims_count: int = Field(default=0)
    sources_count: int = Field(default=0)
    evidence_count: int = Field(default=0)

    # Core journalistic disclosure
    authenticity_disclaimer: str = Field(
        default=(
            "TruthLens AI verifies the factual claims stated in text found within images against authoritative "
            "web sources. High evidence credibility indicates verified factual reporting, but does not certify "
            "that the image file itself is digitally authentic or free from visual manipulation."
        ),
        description="Clear boundary distinguishing claim factual truth from image pixel tampering"
    )
