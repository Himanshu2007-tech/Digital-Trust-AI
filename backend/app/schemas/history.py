from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VerificationEventSchema(BaseModel):
    """Audit trail lifecycle event."""
    id: int
    request_id: int
    stage_name: str
    event_type: str
    status: str
    details: Optional[Dict[str, Any]] = None
    created_at: str

    class Config:
        from_attributes = True


class HistoryItemSchema(BaseModel):
    """Summary item for verification history list."""
    id: int
    request_type: str
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    content_preview: Optional[str] = None
    content_hash: Optional[str] = None
    parent_request_id: Optional[int] = None
    is_archived: bool = False
    claims_count: int = 0
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    confidence_percentage: Optional[float] = None
    error_message: Optional[str] = None


class HistoryListResponse(BaseModel):
    """Paginated list of verification history records."""
    items: List[HistoryItemSchema]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class HistoryFiltersResponse(BaseModel):
    """Available filter options for verification history."""
    request_types: List[str]
    statuses: List[str]
    verdicts: List[str]
    sort_options: List[str]


class DuplicateCheckResponse(BaseModel):
    """Duplicate-input detection match report."""
    has_duplicate: bool
    match_type: Optional[str] = None  # "exact" | "potential"
    matched_request: Optional[HistoryItemSchema] = None
    matches_count: int = 0
    message: str


class HistoryDetailResponse(BaseModel):
    """Complete, authentic verification dossier stored in the database."""
    id: int
    request_type: str
    status: str
    content: Optional[str] = None
    content_hash: Optional[str] = None
    media_file_id: Optional[int] = None
    parent_request_id: Optional[int] = None
    is_archived: bool = False
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    # Verdict summary
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    confidence_percentage: Optional[float] = None
    summary: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)
    methodology_notes: Optional[str] = None
    supported_count: int = 0
    contradicted_count: int = 0
    misleading_count: int = 0
    unverified_count: int = 0
    insufficient_count: int = 0

    # Verification layers
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    comparisons: List[Dict[str, Any]] = Field(default_factory=list)
    queries: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[VerificationEventSchema] = Field(default_factory=list)

    # Sub-entity records
    article: Optional[Dict[str, Any]] = None
    image_verification: Optional[Dict[str, Any]] = None
    media_verification: Optional[Dict[str, Any]] = None


class ReverifyResponse(BaseModel):
    """Outcome of genuine re-verification execution."""
    status: str
    message: str
    original_request_id: int
    new_request_id: int
    new_status: str
    verdict: Optional[str] = None
    confidence: Optional[float] = None


class ArchiveToggleRequest(BaseModel):
    """Request payload to archive or unarchive an investigation."""
    archive: bool = True

