import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.report import Report
from app.schemas.report import (
    ReportSchema,
    ReportListResponse,
    GenerateReportRequest,
    ReportDeleteResponse,
)
from app.verification.reports.service import report_service

router = APIRouter()


def serialize_report(r: Report) -> ReportSchema:
    """Helper to convert Report ORM instance to ReportSchema."""
    return ReportSchema(
        id=r.id,
        report_uuid=r.report_uuid,
        request_id=r.request_id,
        user_id=r.user_id,
        title=r.title,
        format=r.format,
        download_url=f"/api/reports/{r.id}/download",
        file_size_bytes=r.file_size_bytes,
        mime_type=r.mime_type or "application/pdf",
        sha256_hash=r.sha256_hash,
        status=r.status,
        version=r.version or "1.0",
        generated_at=r.generated_at.isoformat() if r.generated_at else None,
        generation_time_ms=r.generation_time_ms,
        created_at=r.created_at.isoformat() if r.created_at else None,
        updated_at=r.updated_at.isoformat() if r.updated_at else None,
        error_message=r.error_message,
    )


@router.post(
    "/reports",
    response_model=ReportSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Professional PDF Dossier",
    description="Compiles an authentic, multi-page vector PDF report for a saved verification request."
)
async def generate_report_endpoint(
    payload: GenerateReportRequest,
    db: Session = Depends(get_db)
):
    report = report_service.generate_report(
        db=db,
        request_id=payload.request_id,
        title=payload.title
    )
    return serialize_report(report)


@router.get(
    "/reports",
    response_model=ReportListResponse,
    summary="List Generated Verification Reports",
    description="Returns real generated investigation reports from the database with pagination and filtering."
)
async def list_reports(
    request_id: Optional[int] = Query(None, description="Filter by verification request ID"),
    status: Optional[str] = Query(None, description="Filter by report status (generated, pending, failed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    reports, total_count = report_service.get_reports(
        db=db,
        request_id=request_id,
        status=status,
        page=page,
        page_size=page_size
    )
    total_pages = max(1, (total_count + page_size - 1) // page_size) if total_count > 0 else 1

    return ReportListResponse(
        items=[serialize_report(r) for r in reports],
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ReportSchema,
    summary="Get Report Metadata",
    description="Retrieves metadata and status for a specific generated verification report."
)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    report = report_service.get_report_by_id(db=db, report_id=report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} not found."
        )
    return serialize_report(report)


@router.get(
    "/reports/{report_id}/download",
    summary="Securely Download PDF Dossier",
    description="Downloads the physical PDF verification report file with strict path-traversal prevention."
)
async def download_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    report = report_service.get_report_by_id(db=db, report_id=report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} not found."
        )

    file_path = report_service.get_report_file_path(report)
    clean_filename = f"TruthLens_Report_{report.request_id}_{report.report_uuid[:8]}.pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=clean_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "X-Report-UUID": report.report_uuid,
            "X-SHA256-Hash": report.sha256_hash or "",
        }
    )


@router.delete(
    "/reports/{report_id}",
    response_model=ReportDeleteResponse,
    summary="Delete Generated Report",
    description="Safely deletes the report database record and cleans up the associated PDF file on disk."
)
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    success = report_service.delete_report(db=db, report_id=report_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} not found."
        )
    return ReportDeleteResponse(
        status="success",
        message=f"Report #{report_id} and its stored file were successfully deleted.",
        report_id=report_id
    )
