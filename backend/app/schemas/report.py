from typing import Optional, List
from pydantic import BaseModel, Field


class GenerateReportRequest(BaseModel):
    """Payload to trigger report generation for a saved verification request."""
    request_id: int = Field(..., description="ID of the saved verification request")
    title: Optional[str] = Field(None, description="Optional custom title for the dossier")


class ReportSchema(BaseModel):
    """Complete serialized representation of an investigation report."""
    id: int
    report_uuid: str
    request_id: int
    user_id: Optional[int] = None
    title: str
    format: str = "pdf"
    download_url: str
    file_size_bytes: Optional[int] = None
    mime_type: str = "application/pdf"
    sha256_hash: Optional[str] = None
    status: str
    version: str = "1.0"
    generated_at: Optional[str] = None
    generation_time_ms: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None


class ReportListResponse(BaseModel):
    """Paginated response containing reports."""
    items: List[ReportSchema]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ReportDeleteResponse(BaseModel):
    """Response confirming report removal."""
    status: str = "success"
    message: str
    report_id: int
