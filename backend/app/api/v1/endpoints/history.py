import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.history import (
    HistoryListResponse,
    HistoryFiltersResponse,
    HistoryDetailResponse,
    DuplicateCheckResponse,
    ReverifyResponse,
    ArchiveToggleRequest,
)
from app.verification.history.service import HistoryService
from app.verification.analytics.service import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter()
history_service = HistoryService()



@router.get(
    "/history",
    response_model=HistoryListResponse,
    summary="List Verification History",
    description=(
        "Returns paginated, searchable, and filtered verification history backed by real database records. "
        "Supports filtering by format, status, verdict, date range, and confidence range."
    ),
)
def list_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    query: Optional[str] = Query(None, description="Search keyword for claim text, URL, or Request ID"),
    search: Optional[str] = Query(None, description="Alias for query parameter"),
    request_type: Optional[str] = Query(None, description="Filter by type: text, url, image, audio, video"),
    status: Optional[str] = Query(None, description="Filter by lifecycle status: completed, processing, partial, failed"),
    verdict: Optional[str] = Query(None, description="Filter by overall verdict: SUPPORTED, CONTRADICTED, MISLEADING, etc."),
    from_date: Optional[datetime] = Query(None, description="Earliest creation date (ISO 8601)"),
    to_date: Optional[datetime] = Query(None, description="Latest creation date (ISO 8601)"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum evidence confidence"),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum evidence confidence"),
    source_domain: Optional[str] = Query(None, description="Filter by discovered source domain"),
    is_archived: bool = Query(False, description="Whether to include soft-archived investigations (default: False)"),
    sort_by: str = Query("created_at", description="Sort field: created_at, confidence, status, request_type, id"),
    sort_order: str = Query("desc", description="Sort order: desc or asc"),
    db: Session = Depends(get_db),
):
    try:
        search_query = query if query is not None else search
        return history_service.get_history(
            db=db,
            user_id=None,  # Expandable when user authentication is active
            page=page,
            page_size=page_size,
            query=search_query,
            request_type=request_type,
            status=status,
            verdict=verdict,
            from_date=from_date,
            to_date=to_date,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            source_domain=source_domain,
            is_archived=is_archived,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        logger.error(f"Error querying verification history: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve verification history from database.",
        )


@router.get(
    "/history/export",
    summary="Export Filtered Investigations as CSV",
    description="Securely exports filtered verification investigations as a formula-injection-safe CSV document."
)
def export_history_csv(
    query: Optional[str] = Query(None, description="Search keyword in claim or content"),
    search: Optional[str] = Query(None, description="Alias for query parameter"),
    request_type: Optional[str] = Query(None, description="Filter by type (text, url, image, audio, video)"),
    status: Optional[str] = Query(None, description="Filter by status (completed, failed, etc.)"),
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    date_range: Optional[str] = Query(None, description="Preset date range (7d, 30d, 90d, all)"),
    time_range: Optional[str] = Query(None, description="Alias for date_range"),
    from_date: Optional[datetime] = Query(None, description="Earliest date (ISO 8601)"),
    start_date: Optional[datetime] = Query(None, description="Alias for from_date"),
    to_date: Optional[datetime] = Query(None, description="Latest date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Alias for to_date"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum confidence"),
    source_domain: Optional[str] = Query(None, description="Filter by discovered source domain"),
    limit: int = Query(1000, ge=1, le=2000, description="Maximum rows to export"),
    db: Session = Depends(get_db)
):
    search_query = query if query is not None else search
    resolved_range = date_range or time_range
    resolved_from = start_date or from_date
    resolved_to = end_date or to_date
    csv_content = analytics_service.export_verifications_csv(
        db=db,
        user_id=None,
        query=search_query,
        request_type=request_type,
        status=status,
        verdict=verdict,
        time_range=resolved_range,
        from_date=resolved_from,
        to_date=resolved_to,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        source_domain=source_domain,
        limit=limit
    )

    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"truthlens_history_export_{timestamp_str}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )



@router.get(
    "/history/filters",
    response_model=HistoryFiltersResponse,
    summary="Get Available History Filters",
    description="Returns distinct formats, statuses, verdicts, and sort options available in the database.",
)
def get_history_filters(db: Session = Depends(get_db)):
    try:
        return history_service.get_filter_options(db=db)
    except Exception as exc:
        logger.error(f"Error getting history filter options: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve history filter options.",
        )


@router.get(
    "/history/check-duplicate",
    response_model=DuplicateCheckResponse,
    summary="Check for Existing Duplicate Investigation",
    description="Checks if an identical claim, article URL, or media fingerprint was previously verified.",
)
def check_duplicate(
    content_hash: Optional[str] = Query(None, description="SHA-256 fingerprint of input content"),
    text: Optional[str] = Query(None, description="Raw claim text to check"),
    content: Optional[str] = Query(None, description="Alias for text parameter"),
    url: Optional[str] = Query(None, description="Article URL to check"),
    exclude_request_id: Optional[int] = Query(None, description="Exclude current request ID from duplicate check"),
    db: Session = Depends(get_db),
):
    try:
        target_text = text if text is not None else content
        return history_service.check_duplicates(
            db=db,
            content_hash=content_hash,
            text=target_text,
            url=url,
            exclude_request_id=exclude_request_id,
        )
    except Exception as exc:
        logger.error(f"Error checking duplicate: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check duplicate verification.",
        )


@router.get(
    "/history/{request_id}",
    response_model=HistoryDetailResponse,
    summary="Get Verification Detail Dossier",
    description="Retrieves the complete authentic historical record, claim breakdowns, retrieved sources, evidence, verdicts, and lifecycle events.",
)
def get_history_detail(
    request_id: int,
    db: Session = Depends(get_db),
):
    try:
        record = history_service.get_history_detail(request_id=request_id, db=db)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification request #{request_id} not found in database.",
            )
        return record
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching verification detail for #{request_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve verification details for request #{request_id}.",
        )


@router.post(
    "/history/{request_id}/reverify",
    response_model=ReverifyResponse,
    summary="Re-Verify an Existing Investigation",
    description="Re-runs the appropriate verification engine on the original input, creates a linked child request, and saves new evidence and verdicts without modifying the original.",
)
def reverify_investigation(
    request_id: int,
    db: Session = Depends(get_db),
):
    try:
        result = history_service.reverify_request(request_id=request_id, db=db)
        if result.status == "failed" and result.new_request_id == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message,
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error reverifying request #{request_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-verify request #{request_id}: {str(exc)}",
        )


@router.post(
    "/history/{request_id}/archive",
    summary="Archive or Unarchive Investigation",
    description="Toggles the soft-archived state of a verification record. Archived records remain accessible through explicit filtering.",
)
def archive_investigation(
    request_id: int,
    payload: Optional[ArchiveToggleRequest] = None,
    archive: Optional[bool] = Query(None, description="True to archive, False to unarchive"),
    db: Session = Depends(get_db),
):
    try:
        target_archive = True
        if payload is not None:
            target_archive = payload.archive
        elif archive is not None:
            target_archive = archive

        record = history_service.archive_request(request_id=request_id, db=db, archive=target_archive)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification request #{request_id} not found in database.",
            )
        return {
            "status": "success",
            "request_id": record.id,
            "is_archived": record.is_archived,
            "message": f"Verification #{record.id} {'archived' if record.is_archived else 'unarchived'} successfully.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error archiving request #{request_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update archive status for request #{request_id}.",
        )
