"""
TruthLens AI — Analytics & Macro Intelligence Service (Part 13)
Performs authentic database aggregations across verification lifecycles,
temporal volumes, modality distributions, verdict consensus, evidence coverage,
and formula-injection-safe CSV exports. Zero fabricated statistics.
"""

import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import func, or_, and_, desc, asc, select, distinct
from sqlalchemy.orm import Session

from fastapi import HTTPException
from app.core.exceptions import ValidationException
from app.models.verification_request import VerificationRequest
from app.models.verification_result import VerificationResult
from app.models.claim import Claim
from app.models.source import Source, claim_sources
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.models.report import Report
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsActivityItem,
    AnalyticsTimelineResponse,
    TimelinePoint,
    AnalyticsVerificationTypesResponse,
    TypeBreakdownItem,
    AnalyticsVerdictDistributionResponse,
    VerdictCountItem,
    AnalyticsSourceCoverageResponse,
    DomainCoverageItem,
)

logger = logging.getLogger(__name__)


def sanitize_csv_cell(val: Any) -> str:
    """
    Prevent Spreadsheet Formula Injection (CSV Injection).
    If a cell value starts with dangerous characters (=, +, -, @, tab, cr),
    prefix with an apostrophe to force spreadsheet applications to treat it as literal text.
    """
    if val is None:
        return ""
    text = str(val)
    # Check first non-whitespace character
    stripped = text.lstrip()
    if stripped and stripped[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


class AnalyticsService:
    """Enterprise analytics engine computing authentic aggregate verification metrics."""

    def parse_date_range(
        self,
        time_range: Optional[str] = "30d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Tuple[datetime, datetime, str]:
        """
        Validate and resolve date range boundaries into canonical UTC datetimes.
        Raises HTTPException(400) if preset is invalid or from_date > to_date.
        """
        now = datetime.now(timezone.utc)
        resolved_time_range = (time_range or "30d").lower().strip()

        if from_date or to_date or resolved_time_range == "custom":
            resolved_from = from_date or (now - timedelta(days=30))
            resolved_to = to_date or now
            if resolved_from.tzinfo is None:
                resolved_from = resolved_from.replace(tzinfo=timezone.utc)
            if resolved_to.tzinfo is None:
                resolved_to = resolved_to.replace(tzinfo=timezone.utc)

            if resolved_from > resolved_to:
                raise HTTPException(status_code=400, detail="Invalid date range: start_date cannot be after end_date.")
            return resolved_from, resolved_to, "custom"

        if resolved_time_range == "7d":
            return now - timedelta(days=7), now, "7d"
        elif resolved_time_range == "30d":
            return now - timedelta(days=30), now, "30d"
        elif resolved_time_range == "90d":
            return now - timedelta(days=90), now, "90d"
        elif resolved_time_range == "all":
            # Earliest historical boundary
            return datetime(2020, 1, 1, tzinfo=timezone.utc), now, "all"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date_range: '{time_range}'. Allowed values are '7d', '30d', '90d', 'all', or 'custom'."
            )

    def get_overview(
        self,
        db: Session,
        user_id: Optional[int] = None,
        time_range: Optional[str] = "30d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> AnalyticsOverviewResponse:
        """Calculate macro-level metrics from real database rows within the resolved date range."""
        from_dt, to_dt, active_range = self.parse_date_range(time_range, from_date, to_date)

        # Base request filter
        q_vr = db.query(VerificationRequest).filter(
            VerificationRequest.created_at >= from_dt,
            VerificationRequest.created_at <= to_dt
        )
        if user_id is not None:
            q_vr = q_vr.filter(VerificationRequest.user_id == user_id)

        # Request status aggregation
        status_rows = (
            db.query(
                VerificationRequest.status,
                func.count(VerificationRequest.id)
            )
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            status_rows = status_rows.filter(VerificationRequest.user_id == user_id)
        status_counts = dict(status_rows.group_by(VerificationRequest.status).all())

        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        processing = status_counts.get("processing", 0) + status_counts.get("pending", 0)
        partial = status_counts.get("partial", 0)
        total_requests = sum(status_counts.values())

        completion_rate = round((completed / total_requests) * 100.0, 1) if total_requests > 0 else 0.0

        # Total atomic claims in period
        q_claims = (
            db.query(func.count(Claim.id))
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q_claims = q_claims.filter(VerificationRequest.user_id == user_id)
        total_claims = q_claims.scalar() or 0

        # Average Evidence Confidence (Request-level results, excluding nulls and missing values)
        q_conf = (
            db.query(func.avg(VerificationResult.confidence))
            .join(VerificationRequest, VerificationResult.request_id == VerificationRequest.id)
            .filter(
                VerificationResult.claim_id.is_(None),
                VerificationResult.confidence.is_not(None),
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt,
                VerificationRequest.status == "completed"
            )
        )
        if user_id is not None:
            q_conf = q_conf.filter(VerificationRequest.user_id == user_id)
        raw_avg_conf = q_conf.scalar()
        avg_conf = round(float(raw_avg_conf), 3) if raw_avg_conf is not None else None
        avg_conf_pct = round(avg_conf * 100.0, 1) if avg_conf is not None else None

        # Distinct sources discovered in period
        q_sources = (
            db.query(func.count(distinct(Source.id)))
            .join(claim_sources, Source.id == claim_sources.c.source_id)
            .join(Claim, claim_sources.c.claim_id == Claim.id)
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q_sources = q_sources.filter(VerificationRequest.user_id == user_id)
        total_sources = q_sources.scalar() or 0

        # Distinct evidence passages extracted in period
        q_evidence = (
            db.query(func.count(Evidence.id))
            .join(Claim, Evidence.claim_id == Claim.id)
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q_evidence = q_evidence.filter(VerificationRequest.user_id == user_id)
        total_evidence = q_evidence.scalar() or 0

        # Reports generated vs failed in period
        q_rep = db.query(
            Report.status,
            func.count(Report.id)
        ).filter(
            Report.created_at >= from_dt,
            Report.created_at <= to_dt
        )
        if user_id is not None:
            q_rep = q_rep.filter(Report.user_id == user_id)
        rep_counts = dict(q_rep.group_by(Report.status).all())
        reports_generated = rep_counts.get("generated", 0) + rep_counts.get("completed", 0)
        reports_failed = rep_counts.get("failed", 0)

        # Recent Activity (Latest 5 verifications)
        recent_query = (
            db.query(VerificationRequest)
            .outerjoin(
                VerificationResult,
                and_(
                    VerificationRequest.id == VerificationResult.request_id,
                    VerificationResult.claim_id.is_(None)
                )
            )
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            recent_query = recent_query.filter(VerificationRequest.user_id == user_id)
        recent_records = (
            recent_query
            .order_by(desc(VerificationRequest.created_at))
            .limit(6)
            .all()
        )

        recent_items = []
        for r in recent_records:
            vr_res = r.verification_result
            conf_val = vr_res.confidence if vr_res else None
            recent_items.append(
                AnalyticsActivityItem(
                    id=r.id,
                    request_type=r.request_type,
                    status=r.status,
                    verdict=vr_res.overall_verdict if vr_res else None,
                    confidence=conf_val,
                    confidence_percentage=round(conf_val * 100.0, 1) if conf_val is not None else None,
                    created_at=r.created_at.isoformat() if r.created_at else None,
                    claims_count=len(r.claims) if r.claims else 0
                )
            )

        return AnalyticsOverviewResponse(
            total_requests=total_requests,
            completed_count=completed,
            failed_count=failed,
            processing_count=processing,
            partial_count=partial,
            completion_rate=completion_rate,
            total_claims=total_claims,
            average_confidence=avg_conf,
            average_confidence_percentage=avg_conf_pct,
            total_sources=total_sources,
            total_evidence_items=total_evidence,
            reports_generated=reports_generated,
            reports_failed=reports_failed,
            time_range=active_range,
            from_date=from_dt.isoformat(),
            to_date=to_dt.isoformat(),
            recent_activity=recent_items
        )

    def get_timeline(
        self,
        db: Session,
        user_id: Optional[int] = None,
        time_range: Optional[str] = "30d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        interval: str = "day"
    ) -> AnalyticsTimelineResponse:
        """
        Produce a contiguous time-series distribution of verification volume.
        Ensures dates with zero activity are included so line and bar charts render cleanly.
        """
        from_dt, to_dt, _ = self.parse_date_range(time_range, from_date, to_date)

        # Query all verification requests in the time window (lightweight projection)
        q = (
            db.query(
                VerificationRequest.created_at,
                VerificationRequest.request_type,
                VerificationRequest.status,
                VerificationResult.confidence
            )
            .outerjoin(
                VerificationResult,
                and_(
                    VerificationRequest.id == VerificationResult.request_id,
                    VerificationResult.claim_id.is_(None)
                )
            )
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q = q.filter(VerificationRequest.user_id == user_id)
        records = q.all()

        # Build contiguous date buckets
        start_date = from_dt.date()
        end_date = to_dt.date()
        day_count = (end_date - start_date).days + 1

        # Key map for bucket storage
        buckets: Dict[str, Dict[str, Any]] = {}
        curr = start_date
        while curr <= end_date:
            date_str = curr.strftime("%Y-%m-%d")
            buckets[date_str] = {
                "date": date_str,
                "total": 0,
                "completed": 0,
                "failed": 0,
                "text": 0,
                "url": 0,
                "image": 0,
                "audio": 0,
                "video": 0,
                "conf_sum": 0.0,
                "conf_count": 0,
            }
            curr += timedelta(days=1)

        total_requests = len(records)

        # Aggregate rows into date buckets
        for created_at, req_type, status_val, conf_val in records:
            if not created_at:
                continue
            date_key = created_at.strftime("%Y-%m-%d")
            if date_key in buckets:
                b = buckets[date_key]
                b["total"] += 1
                if status_val == "completed":
                    b["completed"] += 1
                elif status_val == "failed":
                    b["failed"] += 1

                t_clean = (req_type or "text").lower()
                if t_clean in b:
                    b[t_clean] += 1

                if conf_val is not None and conf_val > 0.0 and status_val == "completed":
                    b["conf_sum"] += conf_val
                    b["conf_count"] += 1

        # Format timeline points
        data_points = []
        for date_key in sorted(buckets.keys()):
            b = buckets[date_key]
            avg_c = round(b["conf_sum"] / b["conf_count"], 3) if b["conf_count"] > 0 else None
            data_points.append(
                TimelinePoint(
                    date=b["date"],
                    total=b["total"],
                    completed=b["completed"],
                    failed=b["failed"],
                    text=b["text"],
                    url=b["url"],
                    image=b["image"],
                    audio=b["audio"],
                    video=b["video"],
                    avg_confidence=avg_c
                )
            )

        return AnalyticsTimelineResponse(
            interval=interval,
            total_requests=total_requests,
            data_points=data_points,
            from_date=from_dt.isoformat(),
            to_date=to_dt.isoformat()
        )

    def get_verification_types(
        self,
        db: Session,
        user_id: Optional[int] = None,
        time_range: Optional[str] = "30d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> AnalyticsVerificationTypesResponse:
        """Calculate distribution across modalities (text, url, image, audio, video)."""
        from_dt, to_dt, _ = self.parse_date_range(time_range, from_date, to_date)

        rows = (
            db.query(
                VerificationRequest.request_type,
                VerificationRequest.status,
                VerificationResult.confidence
            )
            .outerjoin(
                VerificationResult,
                and_(
                    VerificationRequest.id == VerificationResult.request_id,
                    VerificationResult.claim_id.is_(None)
                )
            )
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            rows = rows.filter(VerificationRequest.user_id == user_id)
        records = rows.all()

        total_count = len(records)

        # Group by standard 5 types
        supported_types = ["text", "url", "image", "audio", "video"]
        counts: Dict[str, Dict[str, Any]] = {
            t: {"count": 0, "completed": 0, "conf_sum": 0.0, "conf_count": 0}
            for t in supported_types
        }

        for req_type, status_val, conf_val in records:
            t = (req_type or "text").lower()
            if t not in counts:
                counts[t] = {"count": 0, "completed": 0, "conf_sum": 0.0, "conf_count": 0}
            counts[t]["count"] += 1
            if status_val == "completed":
                counts[t]["completed"] += 1
            if conf_val is not None and conf_val > 0.0 and status_val == "completed":
                counts[t]["conf_sum"] += conf_val
                counts[t]["conf_count"] += 1

        breakdown = []
        for t in supported_types:
            c_data = counts[t]
            c = c_data["count"]
            pct = round((c / total_count) * 100.0, 1) if total_count > 0 else 0.0
            avg_c = round(c_data["conf_sum"] / c_data["conf_count"], 3) if c_data["conf_count"] > 0 else None
            breakdown.append(
                TypeBreakdownItem(
                    type=t,
                    count=c,
                    percentage=pct,
                    completed_count=c_data["completed"],
                    avg_confidence=avg_c
                )
            )

        return AnalyticsVerificationTypesResponse(
            total_requests=total_count,
            breakdown=breakdown,
            from_date=from_dt.isoformat(),
            to_date=to_dt.isoformat()
        )

    def get_verdict_distribution(
        self,
        db: Session,
        user_id: Optional[int] = None,
        time_range: Optional[str] = "30d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> AnalyticsVerdictDistributionResponse:
        """
        Calculate verdict breakdown. Strictly distinguishes request-level overall verdicts
        from claim-level atomic verdicts to prevent multi-claim counting distortion.
        """
        from_dt, to_dt, _ = self.parse_date_range(time_range, from_date, to_date)

        # 1. Request-level verdicts (overall_verdict where claim_id is null)
        q_req = (
            db.query(
                VerificationResult.overall_verdict,
                func.count(VerificationResult.id)
            )
            .join(VerificationRequest, VerificationResult.request_id == VerificationRequest.id)
            .filter(
                VerificationResult.claim_id.is_(None),
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q_req = q_req.filter(VerificationRequest.user_id == user_id)
        req_verdict_rows = dict(q_req.group_by(VerificationResult.overall_verdict).all())

        # Total completed/evaluated requests
        total_eval_req = sum(req_verdict_rows.values())

        # Total total requests in period to find pending
        q_tot_req = db.query(func.count(VerificationRequest.id)).filter(
            VerificationRequest.created_at >= from_dt,
            VerificationRequest.created_at <= to_dt
        )
        if user_id is not None:
            q_tot_req = q_tot_req.filter(VerificationRequest.user_id == user_id)
        all_req_count = q_tot_req.scalar() or 0
        pending_req = max(0, all_req_count - total_eval_req)

        # Format request verdicts
        canonical_verdicts = ["SUPPORTED", "CONTRADICTED", "MISLEADING", "UNVERIFIED", "INSUFFICIENT_INFORMATION"]
        req_items = []
        for v in canonical_verdicts:
            c = req_verdict_rows.get(v, 0)
            pct = round((c / total_eval_req) * 100.0, 1) if total_eval_req > 0 else 0.0
            req_items.append(VerdictCountItem(verdict=v, count=c, percentage=pct))

        # Check any non-standard verdicts
        for v, c in req_verdict_rows.items():
            if v and v.upper() not in canonical_verdicts:
                pct = round((c / total_eval_req) * 100.0, 1) if total_eval_req > 0 else 0.0
                req_items.append(VerdictCountItem(verdict=v.upper(), count=c, percentage=pct))

        # 2. Claim-level verdicts (verdict where claim_id is NOT null)
        q_claims = (
            db.query(
                VerificationResult.verdict,
                func.count(VerificationResult.id)
            )
            .join(Claim, VerificationResult.claim_id == Claim.id)
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationResult.claim_id.is_not(None),
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q_claims = q_claims.filter(VerificationRequest.user_id == user_id)
        claim_verdict_rows = dict(q_claims.group_by(VerificationResult.verdict).all())

        total_eval_claims = sum(claim_verdict_rows.values())

        claim_canonical = ["SUPPORTED", "CONTRADICTED", "MISLEADING", "UNVERIFIED", "INSUFFICIENT_EVIDENCE"]
        claim_items = []
        for v in claim_canonical:
            c = claim_verdict_rows.get(v, 0)
            pct = round((c / total_eval_claims) * 100.0, 1) if total_eval_claims > 0 else 0.0
            claim_items.append(VerdictCountItem(verdict=v, count=c, percentage=pct))

        for v, c in claim_verdict_rows.items():
            if v and v.upper() not in claim_canonical:
                pct = round((c / total_eval_claims) * 100.0, 1) if total_eval_claims > 0 else 0.0
                claim_items.append(VerdictCountItem(verdict=v.upper(), count=c, percentage=pct))

        return AnalyticsVerdictDistributionResponse(
            total_evaluated_requests=total_eval_req,
            pending_evaluation_requests=pending_req,
            request_verdicts=req_items,
            total_evaluated_claims=total_eval_claims,
            claim_verdicts=claim_items,
            from_date=from_dt.isoformat(),
            to_date=to_dt.isoformat()
        )

    def get_source_coverage(
        self,
        db: Session,
        user_id: Optional[int] = None,
        time_range: Optional[str] = "30d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> AnalyticsSourceCoverageResponse:
        """
        Produce transparent external evidence and source coverage metrics.
        Keeps coverage volume separate from verdict confidence.
        """
        from_dt, to_dt, _ = self.parse_date_range(time_range, from_date, to_date)

        # 1. Total claims in period
        q_claims = (
            db.query(func.count(Claim.id))
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q_claims = q_claims.filter(VerificationRequest.user_id == user_id)
        total_claims = q_claims.scalar() or 0

        # 2. Unique sources and unique domains
        q_sources = (
            db.query(
                Source.id,
                Source.domain,
                Source.publisher,
                Source.source_type
            )
            .join(claim_sources, Source.id == claim_sources.c.source_id)
            .join(Claim, claim_sources.c.claim_id == Claim.id)
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
            .distinct()
        )
        if user_id is not None:
            q_sources = q_sources.filter(VerificationRequest.user_id == user_id)
        source_rows = q_sources.all()

        unique_sources_count = len(source_rows)
        domains_set = set(r.domain for r in source_rows if r.domain)
        unique_domains_count = len(domains_set)

        # Primary sources count
        primary_count = sum(1 for r in source_rows if (r.source_type or "").upper() == "PRIMARY")
        primary_pct = round((primary_count / unique_sources_count) * 100.0, 1) if unique_sources_count > 0 else 0.0

        # Domain frequency aggregation
        domain_counts: Dict[str, Dict[str, Any]] = {}
        for r in source_rows:
            d = (r.domain or "unknown").lower()
            if d not in domain_counts:
                domain_counts[d] = {
                    "domain": d,
                    "count": 0,
                    "publisher": r.publisher,
                    "source_type": r.source_type
                }
            domain_counts[d]["count"] += 1

        top_domains = [
            DomainCoverageItem(
                domain=data["domain"],
                sources_count=data["count"],
                publisher=data["publisher"],
                source_type=data["source_type"]
            )
            for data in sorted(domain_counts.values(), key=lambda x: x["count"], reverse=True)[:10]
        ]

        # 3. Evidence items and stance direction
        q_ev = (
            db.query(Evidence.direction, func.count(Evidence.id))
            .join(Claim, Evidence.claim_id == Claim.id)
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
        )
        if user_id is not None:
            q_ev = q_ev.filter(VerificationRequest.user_id == user_id)
        ev_dir_rows = dict(q_ev.group_by(Evidence.direction).all())

        total_evidence_passages = sum(ev_dir_rows.values())

        evidence_direction_distribution = {
            "SUPPORTING": ev_dir_rows.get("SUPPORTING", 0),
            "CONTRADICTING": ev_dir_rows.get("CONTRADICTING", 0),
            "CONTEXTUAL": ev_dir_rows.get("CONTEXTUAL", 0),
            "INSUFFICIENT": ev_dir_rows.get("INSUFFICIENT", 0),
        }

        # Averages per claim
        avg_sources_per_claim = round(unique_sources_count / total_claims, 2) if total_claims > 0 else 0.0
        avg_evidence_per_claim = round(total_evidence_passages / total_claims, 2) if total_claims > 0 else 0.0

        # 4. Source comparisons metrics (independence and consistency)
        q_cmp = (
            db.query(
                SourceComparison.source_relationship,
                SourceComparison.evidence_consistency,
                func.count(SourceComparison.id)
            )
            .join(Claim, SourceComparison.claim_id == Claim.id)
            .join(VerificationRequest, Claim.request_id == VerificationRequest.id)
            .filter(
                VerificationRequest.created_at >= from_dt,
                VerificationRequest.created_at <= to_dt
            )
            .group_by(SourceComparison.source_relationship, SourceComparison.evidence_consistency)
        )
        if user_id is not None:
            q_cmp = q_cmp.filter(VerificationRequest.user_id == user_id)
        cmp_rows = q_cmp.all()

        source_independence: Dict[str, int] = {
            "INDEPENDENT": 0,
            "POSSIBLY_SYNDICATED": 0,
            "DUPLICATE": 0,
            "UNKNOWN": 0,
        }
        evidence_consistency: Dict[str, int] = {
            "CONSISTENT_EVIDENCE": 0,
            "CONFLICTING_INFORMATION": 0,
            "COMPLEMENTARY": 0,
            "INSUFFICIENT": 0,
        }

        for rel, const, cnt in cmp_rows:
            rel_u = (rel or "UNKNOWN").upper()
            const_u = (const or "INSUFFICIENT").upper()
            if rel_u in source_independence:
                source_independence[rel_u] += cnt
            if const_u in evidence_consistency:
                evidence_consistency[const_u] += cnt

        notes = (
            "Evidence coverage metrics quantify the volume, domain diversity, and stance distribution "
            "of discovered corroborating documents. High source count alone does not equal veracity: "
            "syndicated duplicates are monitored separately to avoid false corroboration."
        )

        return AnalyticsSourceCoverageResponse(
            unique_sources_count=unique_sources_count,
            unique_domains_count=unique_domains_count,
            total_evidence_passages=total_evidence_passages,
            avg_sources_per_claim=avg_sources_per_claim,
            avg_evidence_per_claim=avg_evidence_per_claim,
            primary_source_count=primary_count,
            primary_source_percentage=primary_pct,
            top_domains=top_domains,
            evidence_direction_distribution=evidence_direction_distribution,
            source_independence=source_independence,
            evidence_consistency=evidence_consistency,
            notes=notes,
            from_date=from_dt.isoformat(),
            to_date=to_dt.isoformat()
        )

    def export_verifications_csv(
        self,
        db: Session,
        user_id: Optional[int] = None,
        query: Optional[str] = None,
        request_type: Optional[str] = None,
        status: Optional[str] = None,
        verdict: Optional[str] = None,
        time_range: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        source_domain: Optional[str] = None,
        limit: int = 1000
    ) -> str:
        """
        Generate a safe, formula-injection-sanitized CSV export of filtered investigations.
        Formula injection characters (=, +, -, @) are sanitized with a leading apostrophe.
        Sensitive filesystem paths and tokens are strictly omitted.
        """
        if time_range:
            from_date, to_date, _ = self.parse_date_range(time_range, from_date, to_date)

        limit = max(1, min(limit, 2000))

        # Query verification requests with joined overall result
        q = db.query(VerificationRequest).outerjoin(
            VerificationResult,
            and_(
                VerificationRequest.id == VerificationResult.request_id,
                VerificationResult.claim_id.is_(None)
            )
        )

        if user_id is not None:
            q = q.filter(VerificationRequest.user_id == user_id)

        if request_type and request_type.lower() != "all":
            q = q.filter(func.lower(VerificationRequest.request_type) == request_type.strip().lower())

        if status and status.lower() != "all":
            q = q.filter(func.lower(VerificationRequest.status) == status.strip().lower())

        if verdict and verdict.lower() != "all":
            q = q.filter(func.upper(VerificationResult.overall_verdict) == verdict.strip().upper())

        if from_date:
            q = q.filter(VerificationRequest.created_at >= from_date)
        if to_date:
            q = q.filter(VerificationRequest.created_at <= to_date)

        if min_confidence is not None:
            q = q.filter(VerificationResult.confidence >= min_confidence)
        if max_confidence is not None:
            q = q.filter(VerificationResult.confidence <= max_confidence)

        if source_domain and source_domain.strip():
            dom = source_domain.strip().lower()
            q = q.filter(
                VerificationRequest.id.in_(
                    select(Claim.request_id)
                    .join(claim_sources, Claim.id == claim_sources.c.claim_id)
                    .join(Source, claim_sources.c.source_id == Source.id)
                    .filter(func.lower(Source.domain) == dom)
                )
            )

        if query and query.strip():
            term = f"%{query.strip().lower()}%"
            claim_match = select(Claim.request_id).filter(func.lower(Claim.claim_text).like(term))
            id_match = [VerificationRequest.id == int(query.strip())] if query.strip().isdigit() else []
            q = q.filter(
                or_(
                    func.lower(VerificationRequest.content).like(term),
                    VerificationRequest.id.in_(claim_match),
                    *id_match
                )
            )

        records = q.order_by(desc(VerificationRequest.created_at)).limit(limit).all()

        output = io.StringIO()
        # UTF-8 BOM for spreadsheet application Unicode support
        output.write("\ufeff")

        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        headers = [
            "Investigation ID",
            "Modality",
            "Status",
            "Overall Verdict",
            "Confidence Score",
            "Confidence Percentage",
            "Claims Count",
            "Created At (UTC)",
            "Completed At (UTC)",
            "Content Preview",
            "Content SHA-256 Hash"
        ]
        writer.writerow(headers)

        for r in records:
            res = r.verification_result
            conf = res.confidence if res else None
            conf_pct = f"{conf * 100.0:.1f}%" if conf is not None else ""
            v_val = res.overall_verdict if res else "PENDING"

            preview = ""
            if r.content:
                preview = r.content.strip().replace("\n", " ").replace("\r", " ")
                if len(preview) > 160:
                    preview = preview[:157] + "..."
            elif r.request_type in ("image", "audio", "video") and r.media_file:
                preview = f"{r.request_type.capitalize()} upload: {r.media_file.original_filename}"
            else:
                preview = f"{r.request_type.capitalize()} investigation"

            row = [
                sanitize_csv_cell(f"REQ-{r.id:06d}"),
                sanitize_csv_cell(r.request_type.upper()),
                sanitize_csv_cell(r.status.upper()),
                sanitize_csv_cell(v_val.upper()),
                sanitize_csv_cell(f"{conf:.3f}" if conf is not None else ""),
                sanitize_csv_cell(conf_pct),
                sanitize_csv_cell(len(r.claims) if r.claims else 0),
                sanitize_csv_cell(r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""),
                sanitize_csv_cell(r.completed_at.strftime("%Y-%m-%d %H:%M:%S") if r.completed_at else ""),
                sanitize_csv_cell(preview),
                sanitize_csv_cell(r.content_hash or "")
            ]
            writer.writerow(row)

        return output.getvalue()


analytics_service = AnalyticsService()
