from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsTimelineResponse,
    AnalyticsVerificationTypesResponse,
    AnalyticsVerdictDistributionResponse,
    AnalyticsSourceCoverageResponse,
)
from app.verification.analytics.service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Intelligence"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get Verification Overview Metrics",
    description=(
        "Returns macro-level operational metrics including request volume, status breakdown, "
        "completion rate, claim and source totals, eligible average confidence, and generated report counts."
    )
)
def get_analytics_overview(
    time_range: Optional[str] = Query(None, description="Time window: 7d, 30d, 90d, all, custom"),
    date_range: Optional[str] = Query(None, description="Alias for time_range"),
    from_date: Optional[datetime] = Query(None, description="Custom start date (ISO 8601)"),
    start_date: Optional[datetime] = Query(None, description="Alias for from_date"),
    to_date: Optional[datetime] = Query(None, description="Custom end date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Alias for to_date"),
    db: Session = Depends(get_db)
):
    resolved_range = date_range if date_range is not None else (time_range or "30d")
    resolved_from = start_date or from_date
    resolved_to = end_date or to_date
    return analytics_service.get_overview(
        db=db,
        user_id=None,
        time_range=resolved_range,
        from_date=resolved_from,
        to_date=resolved_to
    )


@router.get(
    "/timeline",
    response_model=AnalyticsTimelineResponse,
    summary="Get Verification Timeline",
    description="Returns contiguous daily time-series distribution of verification volume, status, and modality breakdown."
)
def get_analytics_timeline(
    time_range: Optional[str] = Query(None, description="Time window: 7d, 30d, 90d, all, custom"),
    date_range: Optional[str] = Query(None, description="Alias for time_range"),
    from_date: Optional[datetime] = Query(None, description="Custom start date (ISO 8601)"),
    start_date: Optional[datetime] = Query(None, description="Alias for from_date"),
    to_date: Optional[datetime] = Query(None, description="Custom end date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Alias for to_date"),
    interval: str = Query("day", description="Time bucket interval: day, week, month"),
    db: Session = Depends(get_db)
):
    resolved_range = date_range if date_range is not None else (time_range or "30d")
    resolved_from = start_date or from_date
    resolved_to = end_date or to_date
    return analytics_service.get_timeline(
        db=db,
        user_id=None,
        time_range=resolved_range,
        from_date=resolved_from,
        to_date=resolved_to,
        interval=interval
    )


@router.get(
    "/verification-types",
    response_model=AnalyticsVerificationTypesResponse,
    summary="Get Modality Distribution",
    description="Returns breakdown of requests across text, news URLs, images, audio, and video modalities."
)
def get_analytics_verification_types(
    time_range: Optional[str] = Query(None, description="Time window: 7d, 30d, 90d, all, custom"),
    date_range: Optional[str] = Query(None, description="Alias for time_range"),
    from_date: Optional[datetime] = Query(None, description="Custom start date (ISO 8601)"),
    start_date: Optional[datetime] = Query(None, description="Alias for from_date"),
    to_date: Optional[datetime] = Query(None, description="Custom end date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Alias for to_date"),
    db: Session = Depends(get_db)
):
    resolved_range = date_range if date_range is not None else (time_range or "30d")
    resolved_from = start_date or from_date
    resolved_to = end_date or to_date
    return analytics_service.get_verification_types(
        db=db,
        user_id=None,
        time_range=resolved_range,
        from_date=resolved_from,
        to_date=resolved_to
    )


@router.get(
    "/verdict-distribution",
    response_model=AnalyticsVerdictDistributionResponse,
    summary="Get Categorical Verdict Distribution",
    description="Returns categorical breakdown of findings, strictly separating request-level verdicts from claim-level verdicts."
)
def get_analytics_verdict_distribution(
    time_range: Optional[str] = Query(None, description="Time window: 7d, 30d, 90d, all, custom"),
    date_range: Optional[str] = Query(None, description="Alias for time_range"),
    from_date: Optional[datetime] = Query(None, description="Custom start date (ISO 8601)"),
    start_date: Optional[datetime] = Query(None, description="Alias for from_date"),
    to_date: Optional[datetime] = Query(None, description="Custom end date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Alias for to_date"),
    db: Session = Depends(get_db)
):
    resolved_range = date_range if date_range is not None else (time_range or "30d")
    resolved_from = start_date or from_date
    resolved_to = end_date or to_date
    return analytics_service.get_verdict_distribution(
        db=db,
        user_id=None,
        time_range=resolved_range,
        from_date=resolved_from,
        to_date=resolved_to
    )


@router.get(
    "/source-coverage",
    response_model=AnalyticsSourceCoverageResponse,
    summary="Get Source & Evidence Coverage Transparency",
    description="Returns metrics on discovered external sources, unique domains, primary source ratio, and stance distribution."
)
def get_analytics_source_coverage(
    time_range: Optional[str] = Query(None, description="Time window: 7d, 30d, 90d, all, custom"),
    date_range: Optional[str] = Query(None, description="Alias for time_range"),
    from_date: Optional[datetime] = Query(None, description="Custom start date (ISO 8601)"),
    start_date: Optional[datetime] = Query(None, description="Alias for from_date"),
    to_date: Optional[datetime] = Query(None, description="Custom end date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Alias for to_date"),
    db: Session = Depends(get_db)
):
    resolved_range = date_range if date_range is not None else (time_range or "30d")
    resolved_from = start_date or from_date
    resolved_to = end_date or to_date
    return analytics_service.get_source_coverage(
        db=db,
        user_id=None,
        time_range=resolved_range,
        from_date=resolved_from,
        to_date=resolved_to
    )


@router.get(
    "/export/csv",
    summary="Export Filtered Investigations to CSV",
    description="Downloads a formula-injection-safe CSV file containing filtered investigation records."
)
def export_analytics_csv(
    query: Optional[str] = Query(None, description="Search keyword in claim or content"),
    request_type: Optional[str] = Query(None, description="Filter by type (text, url, image, audio, video)"),
    status: Optional[str] = Query(None, description="Filter by status (completed, failed, etc.)"),
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    date_range: Optional[str] = Query(None, description="Time window preset"),
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
    resolved_range = date_range or time_range
    resolved_from = start_date or from_date
    resolved_to = end_date or to_date
    csv_content = analytics_service.export_verifications_csv(
        db=db,
        user_id=None,
        query=query,
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
    filename = f"truthlens_analytics_export_{timestamp_str}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )
