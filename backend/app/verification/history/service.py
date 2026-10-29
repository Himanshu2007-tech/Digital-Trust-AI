import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from sqlalchemy import func, or_, and_, desc, asc, cast, String, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.verification_request import VerificationRequest
from app.models.verification_event import VerificationEvent
from app.models.verification_result import VerificationResult
from app.models.claim import Claim
from app.models.source import Source, claim_sources
from app.models.evidence import Evidence

from app.models.source_comparison import SourceComparison
from app.models.search_query import SearchQuery
from app.models.article import Article
from app.models.image_verification import ImageVerification
from app.models.media_verification import MediaVerification
from app.models.media_file import MediaFile
from app.schemas.history import (
    HistoryItemSchema,
    HistoryListResponse,
    HistoryFiltersResponse,
    HistoryDetailResponse,
    DuplicateCheckResponse,
    ReverifyResponse,
    VerificationEventSchema,
)

logger = logging.getLogger(__name__)


def compute_content_hash(data: Union[str, bytes]) -> str:
    """Compute cryptographic SHA-256 fingerprint for duplicate detection."""
    if isinstance(data, str):
        # Normalize whitespace and casing for consistent canonical hashing
        normalized = " ".join(data.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    elif isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()


def record_verification_event(
    db: Session,
    request_id: int,
    stage_name: str,
    event_type: str,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None,
) -> VerificationEvent:
    """
    Safely persist a genuine verification lifecycle event.
    Never fabricates historical events.
    """
    event = VerificationEvent(
        request_id=request_id,
        stage_name=stage_name,
        event_type=event_type,
        status=status,
        details=details,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    try:
        db.flush()
    except Exception as e:
        logger.warning(f"Could not persist VerificationEvent for request {request_id}: {e}")
    return event


class HistoryService:
    """Enterprise-grade service for verification history, details, duplicate detection, and re-verification."""

    def get_history(
        self,
        db: Session,
        user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
        query: Optional[str] = None,
        request_type: Optional[str] = None,
        status: Optional[str] = None,
        verdict: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        source_domain: Optional[str] = None,
        is_archived: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> HistoryListResponse:
        """Query verification requests with filtering, pagination, search, and sorting."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        # Base query joined with overall VerificationResult
        q = db.query(VerificationRequest).outerjoin(
            VerificationResult,
            and_(
                VerificationRequest.id == VerificationResult.request_id,
                VerificationResult.claim_id.is_(None),
            ),
        )

        # 1. User ownership filtering if scoped
        if user_id is not None:
            q = q.filter(VerificationRequest.user_id == user_id)

        # 2. Archival filtering
        q = q.filter(VerificationRequest.is_archived == is_archived)

        # 3. Verification Type filtering
        if request_type and request_type.lower() != "all":
            types_list = [t.strip().lower() for t in request_type.split(",") if t.strip()]
            if types_list:
                q = q.filter(func.lower(VerificationRequest.request_type).in_(types_list))

        # 4. Status filtering
        if status and status.lower() != "all":
            status_clean = status.strip().lower()
            q = q.filter(func.lower(VerificationRequest.status) == status_clean)

        # 5. Verdict filtering
        if verdict and verdict.lower() != "all":
            verdict_clean = verdict.strip().upper()
            q = q.filter(func.upper(VerificationResult.overall_verdict) == verdict_clean)

        # 6. Date Range filtering
        if from_date:
            q = q.filter(VerificationRequest.created_at >= from_date)
        if to_date:
            q = q.filter(VerificationRequest.created_at <= to_date)

        # 7. Confidence Range filtering
        if min_confidence is not None:
            q = q.filter(VerificationResult.confidence >= min_confidence)
        if max_confidence is not None:
            q = q.filter(VerificationResult.confidence <= max_confidence)

        # 8. Source Domain filtering
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

        # 9. Search query (request ID, raw content, or claim text)
        if query and query.strip():
            search_term = f"%{query.strip().lower()}%"
            # Subquery for matching claim text
            claim_match_stmt = select(Claim.request_id).filter(
                func.lower(Claim.claim_text).like(search_term)
            )

            id_matches = []
            if query.strip().isdigit():
                id_matches.append(VerificationRequest.id == int(query.strip()))

            q = q.filter(
                or_(
                    func.lower(VerificationRequest.content).like(search_term),
                    VerificationRequest.id.in_(claim_match_stmt),
                    *id_matches,
                )
            )


        # 9. Count total matching records
        total_count = q.with_entities(func.count(func.distinct(VerificationRequest.id))).scalar() or 0

        # 10. Sorting
        order_fn = desc if sort_order.lower() == "desc" else asc
        if sort_by == "confidence":
            q = q.order_by(order_fn(VerificationResult.confidence))
        elif sort_by == "status":
            q = q.order_by(order_fn(VerificationRequest.status))
        elif sort_by == "request_type":
            q = q.order_by(order_fn(VerificationRequest.request_type))
        elif sort_by == "id":
            q = q.order_by(order_fn(VerificationRequest.id))
        else:
            q = q.order_by(order_fn(VerificationRequest.created_at))

        # 11. Pagination & Eager Loading
        offset = (page - 1) * page_size
        records = (
            q.options(
                joinedload(VerificationRequest.verification_result),
                selectinload(VerificationRequest.claims),
            )
            .distinct()
            .offset(offset)
            .limit(page_size)
            .all()
        )

        # 12. Build response items
        items: List[HistoryItemSchema] = []
        for r in records:
            res = r.verification_result
            conf = res.confidence if res else None
            conf_pct = round(conf * 100, 1) if conf is not None else None

            # Generate concise, non-sensitive content preview
            preview = ""
            if r.content:
                preview = r.content.strip()
                if len(preview) > 120:
                    preview = preview[:117] + "..."
            elif r.request_type in ["image", "audio", "video"] and r.media_file:
                preview = f"{r.request_type.capitalize()} upload: {r.media_file.original_filename}"
            else:
                preview = f"{r.request_type.capitalize()} verification"

            items.append(
                HistoryItemSchema(
                    id=r.id,
                    request_type=r.request_type,
                    status=r.status,
                    created_at=r.created_at.isoformat() if r.created_at else None,
                    completed_at=r.completed_at.isoformat() if r.completed_at else None,
                    content_preview=preview,
                    content_hash=r.content_hash,
                    parent_request_id=r.parent_request_id,
                    is_archived=r.is_archived,
                    claims_count=len(r.claims) if r.claims else 0,
                    verdict=res.overall_verdict if res else None,
                    confidence=conf,
                    confidence_percentage=conf_pct,
                    error_message=r.error_message,
                )
            )

        total_pages = max(1, (total_count + page_size - 1) // page_size) if total_count > 0 else 1

        return HistoryListResponse(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    def get_history_detail(
        self,
        request_id: int,
        db: Session,
        user_id: Optional[int] = None,
    ) -> Optional[HistoryDetailResponse]:
        """Retrieve the authentic, complete verification dossier stored in the database."""
        q = (
            db.query(VerificationRequest)
            .filter(VerificationRequest.id == request_id)
            .options(
                joinedload(VerificationRequest.verification_result),
                selectinload(VerificationRequest.claims).selectinload(Claim.verification_result),
                selectinload(VerificationRequest.claims).selectinload(Claim.occurrences),
                selectinload(VerificationRequest.claims).selectinload(Claim.evidence),
                selectinload(VerificationRequest.claims).selectinload(Claim.source_comparisons),
                selectinload(VerificationRequest.claims).selectinload(Claim.search_queries),
                selectinload(VerificationRequest.events),
                joinedload(VerificationRequest.article),
                joinedload(VerificationRequest.image_verification),
                joinedload(VerificationRequest.media_verification).selectinload(MediaVerification.segments),
                joinedload(VerificationRequest.media_verification).selectinload(MediaVerification.frames),
            )
        )

        if user_id is not None:
            q = q.filter(VerificationRequest.user_id == user_id)

        r = q.first()
        if not r:
            return None

        # Overall verdict details
        overall_res = r.verification_result
        conf = overall_res.confidence if overall_res else None

        # Build claims list with their verdicts and occurrences
        claims_list = []
        evidence_list = []
        comparisons_list = []
        queries_list = []
        seen_evidence_ids = set()
        seen_comparison_ids = set()
        seen_query_ids = set()

        # Query all sources associated with this request's claims
        discovered_sources = (
            db.query(Source)
            .join(Claim.sources)
            .filter(Claim.request_id == r.id)
            .distinct()
            .all()
        )
        sources_list = [
            {
                "id": s.id,
                "title": s.title or s.name,
                "url": s.url,
                "domain": s.domain,
                "snippet": s.snippet,
                "publisher": s.publisher,
                "provider": s.provider,
                "source_type": s.source_type,
                "source_role": s.source_role,
                "publication_date": s.publication_date,
            }
            for s in discovered_sources
        ]

        for c in r.claims:
            claim_verdict = c.verification_result
            claims_list.append({
                "id": c.id,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "verifiability": c.verifiability,
                "importance": c.importance,
                "entities": c.entities or [],
                "dates": c.dates or [],
                "numbers": c.numbers or [],
                "status": c.status,
                "verdict": claim_verdict.verdict if claim_verdict else None,
                "confidence": claim_verdict.confidence if claim_verdict else None,
                "explanation": claim_verdict.explanation if claim_verdict else None,
                "limitations": claim_verdict.limitations if claim_verdict else [],
                "occurrences": [
                    {
                        "id": occ.id,
                        "source_type": occ.source_type,
                        "timestamp_start": occ.timestamp_start,
                        "timestamp_end": occ.timestamp_end,
                        "text": occ.text,
                        "confidence": occ.confidence,
                    }
                    for occ in (c.occurrences or [])
                ],
            })

            # Collect evidence
            for ev in (c.evidence or []):
                if ev.id not in seen_evidence_ids:
                    seen_evidence_ids.add(ev.id)
                    src_obj = ev.source if hasattr(ev, "source") else None
                    evidence_list.append({
                        "id": ev.id,
                        "claim_id": ev.claim_id,
                        "source_id": ev.source_id,
                        "evidence_text": ev.evidence_text,
                        "snippet": ev.snippet,
                        "direction": ev.direction,
                        "relevance_score": ev.relevance_score,
                        "publisher": getattr(ev, "publisher", None) or (src_obj.publisher if src_obj else None),
                        "domain": getattr(ev, "domain", None) or (src_obj.domain if src_obj else None),
                        "url": getattr(ev, "url", None) or (src_obj.url if src_obj else None),
                        "explanation": getattr(ev, "explanation", None),
                    })


            # Collect comparisons
            for cmp in (c.source_comparisons or []):
                if cmp.id not in seen_comparison_ids:
                    seen_comparison_ids.add(cmp.id)
                    comparisons_list.append({
                        "id": cmp.id,
                        "claim_id": cmp.claim_id,
                        "consensus_verdict": cmp.consensus_verdict,
                        "evidence_consistency": cmp.evidence_consistency.value if hasattr(cmp.evidence_consistency, "value") else str(cmp.evidence_consistency),
                        "analysis_summary": cmp.analysis_summary,
                        "supporting_sources_count": cmp.supporting_sources_count,
                        "contradicting_sources_count": cmp.contradicting_sources_count,
                        "neutral_sources_count": cmp.neutral_sources_count,
                    })

            # Collect queries
            for qy in (c.search_queries or []):
                if qy.id not in seen_query_ids:
                    seen_query_ids.add(qy.id)
                    queries_list.append({
                        "id": qy.id,
                        "query_text": qy.query_text,
                        "strategy_level": qy.strategy_level,
                        "search_engine": qy.search_engine,
                        "results_count": qy.results_count,
                        "status": qy.status,
                    })

        # Sub-entity data
        article_data = None
        if r.article:
            article_data = {
                "id": r.article.id,
                "title": r.article.title,
                "original_url": r.article.original_url,
                "canonical_url": r.article.canonical_url,
                "domain": r.article.domain,
                "publisher": r.article.publisher,
                "author": r.article.author,
                "published_at": r.article.published_at,
                "word_count": r.article.word_count,
                "content_length": r.article.content_length,
                "article_text": r.article.article_text,
                "content_hash": r.article.content_hash,
            }

        image_data = None
        if r.image_verification:
            iv = r.image_verification
            raw_text = getattr(iv, "raw_ocr_text", getattr(iv, "ocr_raw_text", ""))
            w_count = getattr(iv, "word_count", None)
            if w_count is None and raw_text:
                w_count = len(raw_text.split())
            image_data = {
                "id": iv.id,
                "width": getattr(iv, "image_width", getattr(iv, "width", None)),
                "height": getattr(iv, "image_height", getattr(iv, "height", None)),
                "mime_type": getattr(iv, "image_format", getattr(iv, "mime_type", None)),
                "ocr_raw_text": raw_text,
                "ocr_confidence": getattr(iv, "ocr_confidence", None),
                "word_count": w_count or 0,
                "detected_urls": getattr(iv, "detected_urls", None) or [],
                "detected_dates": getattr(iv, "detected_dates", None) or [],
                "detected_metrics": getattr(iv, "detected_metrics", None) or {},
                "blocks": getattr(iv, "ocr_blocks", None) or [],
            }


        media_data = None
        if r.media_verification:
            media_data = {
                "id": r.media_verification.id,
                "media_type": r.media_verification.media_type,
                "duration_seconds": r.media_verification.duration_seconds,
                "raw_transcript": r.media_verification.raw_transcript,
                "normalized_transcript": r.media_verification.normalized_transcript,
                "transcription_confidence": r.media_verification.transcription_confidence,
                "language": r.media_verification.language,
                "detected_urls": r.media_verification.detected_urls or [],
                "detected_quotes": r.media_verification.detected_quotes or [],
                "technical_indicators": r.media_verification.technical_indicators or {},
                "segments": [
                    {
                        "sequence": seg.sequence,
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "text": seg.text,
                        "confidence": seg.confidence,
                    }
                    for seg in (r.media_verification.segments or [])
                ],
                "frames": [
                    {
                        "frame_number": f.frame_number,
                        "timestamp": f.timestamp,
                        "selection_method": f.selection_method,
                        "image_hash": f.image_hash,
                        "ocr_text": f.ocr_text,
                        "visual_context": f.visual_context,
                    }
                    for f in (r.media_verification.frames or [])
                ],
            }

        # Lifecycle events
        events_list = [
            VerificationEventSchema(
                id=evt.id,
                request_id=evt.request_id,
                stage_name=evt.stage_name,
                event_type=evt.event_type,
                status=evt.status,
                details=evt.details,
                created_at=evt.created_at.isoformat() if evt.created_at else "",
            )
            for evt in (r.events or [])
        ]

        # Calculate counts
        supported = 0
        contradicted = 0
        misleading = 0
        unverified = 0
        insufficient = 0
        for c_dict in claims_list:
            v = (c_dict.get("verdict") or "").upper()
            if v == "SUPPORTED":
                supported += 1
            elif v == "CONTRADICTED":
                contradicted += 1
            elif v == "MISLEADING":
                misleading += 1
            elif v == "UNVERIFIED":
                unverified += 1
            else:
                insufficient += 1

        return HistoryDetailResponse(
            id=r.id,
            request_type=r.request_type,
            status=r.status,
            content=r.content,
            content_hash=r.content_hash,
            media_file_id=r.media_file_id,
            parent_request_id=r.parent_request_id,
            is_archived=r.is_archived,
            created_at=r.created_at.isoformat() if r.created_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            error_message=r.error_message,
            verdict=overall_res.overall_verdict if overall_res else None,
            confidence=conf,
            confidence_percentage=round(conf * 100, 1) if conf is not None else None,
            summary=overall_res.summary if overall_res else None,
            limitations=overall_res.limitations if overall_res and overall_res.limitations else [],
            methodology_notes=overall_res.methodology_notes if overall_res else None,
            supported_count=supported,
            contradicted_count=contradicted,
            misleading_count=misleading,
            unverified_count=unverified,
            insufficient_count=insufficient,
            claims=claims_list,
            sources=sources_list,
            evidence=evidence_list,
            comparisons=comparisons_list,
            queries=queries_list,
            events=events_list,
            article=article_data,
            image_verification=image_data,
            media_verification=media_data,
        )

    def archive_request(
        self,
        request_id: int,
        db: Session,
        archive: bool = True,
        user_id: Optional[int] = None,
    ) -> Optional[VerificationRequest]:
        """Safely toggle soft-archive status and record audit event."""
        q = db.query(VerificationRequest).filter(VerificationRequest.id == request_id)
        if user_id is not None:
            q = q.filter(VerificationRequest.user_id == user_id)
        r = q.first()
        if not r:
            return None

        r.is_archived = archive
        record_verification_event(
            db=db,
            request_id=r.id,
            stage_name="history_management",
            event_type="REQUEST_ARCHIVED" if archive else "REQUEST_UNARCHIVED",
            status="success",
            details={"is_archived": archive},
        )
        db.commit()
        return r

    def check_duplicates(
        self,
        db: Session,
        content_hash: Optional[str] = None,
        text: Optional[str] = None,
        url: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        exclude_request_id: Optional[int] = None,
    ) -> DuplicateCheckResponse:
        """
        Check for identical or highly matching historical verifications.
        Never suppresses new verifications.
        """
        target_hash = content_hash
        if not target_hash:
            if file_bytes:
                target_hash = compute_content_hash(file_bytes)
            elif url:
                target_hash = compute_content_hash(url)
            elif text:
                target_hash = compute_content_hash(text)

        if not target_hash:
            return DuplicateCheckResponse(
                has_duplicate=False,
                match_type=None,
                matched_request=None,
                matches_count=0,
                message="No content provided to perform duplicate checking.",
            )

        # 1. Check for exact cryptographic hash match
        q = (
            db.query(VerificationRequest)
            .filter(VerificationRequest.content_hash == target_hash)
            .options(joinedload(VerificationRequest.verification_result))
            .order_by(VerificationRequest.created_at.desc())
        )
        if exclude_request_id is not None:
            q = q.filter(VerificationRequest.id != exclude_request_id)

        exact_match = q.first()
        total_matches = q.count()

        if exact_match:
            res = exact_match.verification_result
            conf = res.confidence if res else None
            matched_item = HistoryItemSchema(
                id=exact_match.id,
                request_type=exact_match.request_type,
                status=exact_match.status,
                created_at=exact_match.created_at.isoformat() if exact_match.created_at else None,
                completed_at=exact_match.completed_at.isoformat() if exact_match.completed_at else None,
                content_preview=exact_match.content[:100] if exact_match.content else "",
                content_hash=exact_match.content_hash,
                parent_request_id=exact_match.parent_request_id,
                is_archived=exact_match.is_archived,
                verdict=res.overall_verdict if res else None,
                confidence=conf,
                confidence_percentage=round(conf * 100, 1) if conf is not None else None,
            )
            return DuplicateCheckResponse(
                has_duplicate=True,
                match_type="exact",
                matched_request=matched_item,
                matches_count=total_matches,
                message=f"Exact match found: Request #{exact_match.id} ({exact_match.request_type}) was verified on {exact_match.created_at.strftime('%Y-%m-%d %H:%M')}.",
            )

        # 2. Check for potential URL or text match if text/url provided
        if url:
            article_match = (
                db.query(Article)
                .filter(or_(Article.original_url == url, Article.canonical_url == url))
                .order_by(Article.created_at.desc())
                .first()
            )
            if article_match and article_match.request_id != exclude_request_id:
                pot_req = db.query(VerificationRequest).filter_by(id=article_match.request_id).first()
                if pot_req:
                    return DuplicateCheckResponse(
                        has_duplicate=True,
                        match_type="potential",
                        matched_request=HistoryItemSchema(
                            id=pot_req.id,
                            request_type=pot_req.request_type,
                            status=pot_req.status,
                            created_at=pot_req.created_at.isoformat() if pot_req.created_at else None,
                            content_preview=pot_req.content[:100] if pot_req.content else "",
                            content_hash=pot_req.content_hash,
                        ),
                        matches_count=1,
                        message=f"Potential article URL match previously verified in Request #{pot_req.id}.",
                    )

        return DuplicateCheckResponse(
            has_duplicate=False,
            match_type=None,
            matched_request=None,
            matches_count=0,
            message="No identical historical investigations found in database.",
        )

    def get_filter_options(self, db: Session) -> HistoryFiltersResponse:
        """Return available unique options for UI dropdown filters."""
        # Query distinct non-null request types from DB
        db_types = [
            t[0] for t in db.query(VerificationRequest.request_type).distinct().all() if t[0]
        ]
        request_types = sorted(list(set(["text", "url", "image", "audio", "video"] + db_types)))

        statuses = ["completed", "processing", "partial", "failed", "created"]
        verdicts = [
            "SUPPORTED",
            "CONTRADICTED",
            "MISLEADING",
            "MIXED",
            "UNVERIFIED",
            "INSUFFICIENT_EVIDENCE",
        ]
        sort_options = ["created_at", "confidence", "status", "request_type", "id"]

        return HistoryFiltersResponse(
            request_types=request_types,
            statuses=statuses,
            verdicts=verdicts,
            sort_options=sort_options,
        )

    def reverify_request(
        self,
        request_id: int,
        db: Session,
        user_id: Optional[int] = None,
    ) -> ReverifyResponse:
        """
        Execute genuine re-verification:
        1. Preserves original request completely.
        2. Creates new child request with parent_request_id pointing to original.
        3. Re-runs existing verification pipeline for that input format.
        """
        original = db.query(VerificationRequest).filter_by(id=request_id).first()
        if not original:
            return ReverifyResponse(
                status="failed",
                message=f"Original request #{request_id} not found.",
                original_request_id=request_id,
                new_request_id=0,
                new_status="failed",
            )

        # Record REVERIFY event on original request
        record_verification_event(
            db=db,
            request_id=original.id,
            stage_name="reverification",
            event_type="REQUEST_REVERIFIED",
            status="info",
            details={"action": "reverify_triggered"},
        )
        db.commit()

        # Route to appropriate re-verification pipeline based on request_type
        req_type = original.request_type.lower()

        if req_type == "text":
            return self._reverify_text(original, db, user_id)
        elif req_type == "url":
            return self._reverify_url(original, db, user_id)
        elif req_type == "image":
            return self._reverify_image(original, db, user_id)
        elif req_type in ["audio", "video"]:
            return self._reverify_media(original, db, user_id)
        else:
            return ReverifyResponse(
                status="failed",
                message=f"Unsupported verification format '{original.request_type}' for re-verification.",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )

    def _reverify_text(self, original: VerificationRequest, db: Session, user_id: Optional[int]) -> ReverifyResponse:
        from app.verification.preprocessing import clean_text
        from app.verification.extractors.hybrid import HybridClaimExtractor
        from app.verification.search.discovery_service import SourceDiscoveryService
        from app.verification.evidence.service import EvidenceAnalysisService
        from app.verification.verdict.service import VerdictService

        text = original.content or ""
        if not text:
            return ReverifyResponse(
                status="failed",
                message="Cannot re-verify: original text input is empty.",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )

        # 1. Create new child request
        new_req = VerificationRequest(
            user_id=user_id or original.user_id,
            request_type="text",
            content=text,
            content_hash=original.content_hash or compute_content_hash(text),
            parent_request_id=original.id,
            status="processing",
            priority=0,
        )
        db.add(new_req)
        db.flush()

        record_verification_event(
            db=db,
            request_id=new_req.id,
            stage_name="initialization",
            event_type="REQUEST_CREATED",
            status="success",
            details={"parent_request_id": original.id, "reverified": True},
        )

        try:
            # 2. Extract claims
            _, normalized_text = clean_text(text)
            extractor = HybridClaimExtractor()
            extracted_items = extractor.extract_claims(normalized_text)

            saved_claims: List[Claim] = []
            for item in extracted_items:
                c = Claim(
                    request_id=new_req.id,
                    claim_text=item.text,
                    normalized_text=item.normalized_text,
                    claim_type=item.claim_type.value,
                    verifiability=item.verifiability.value,
                    importance=item.importance.value,
                    entities=item.entities,
                    dates=item.dates,
                    locations=item.locations,
                    numbers=item.numbers,
                    source_attributions=item.source_attributions,
                    original_sentence=item.original_sentence,
                    extraction_method=item.extraction_method,
                    status="extracted",
                )
                db.add(c)
                db.flush()
                saved_claims.append(c)

            record_verification_event(
                db=db,
                request_id=new_req.id,
                stage_name="claim_extraction",
                event_type="CLAIM_EXTRACTION_COMPLETED",
                status="success",
                details={"claims_count": len(saved_claims)},
            )

            # 3. Discover sources
            discovery = SourceDiscoveryService()
            for c in saved_claims:
                try:
                    discovery.discover_sources_for_claim(claim_id=c.id, db=db, max_queries=2, max_results_per_query=4)
                except Exception as s_err:
                    logger.warning(f"Re-verification search error: {s_err}")

            record_verification_event(
                db=db,
                request_id=new_req.id,
                stage_name="search",
                event_type="SEARCH_COMPLETED",
                status="success",
            )

            # 4. Analyze evidence
            ev_service = EvidenceAnalysisService()
            for c in saved_claims[:3]:
                try:
                    ev_service.analyze_evidence_for_claim(claim_id=c.id, db=db)
                except Exception as e_err:
                    logger.warning(f"Re-verification evidence error: {e_err}")

            # 5. Finalize verdict
            verdict_svc = VerdictService()
            req_verdict = verdict_svc.finalize_request(request_id=new_req.id, db=db, reevaluate_claims=False)

            new_req.status = "completed"
            new_req.completed_at = datetime.now(timezone.utc)

            record_verification_event(
                db=db,
                request_id=new_req.id,
                stage_name="verdict_synthesis",
                event_type="VERDICT_SYNTHESIS_COMPLETED",
                status="success",
                details={"overall_verdict": req_verdict.overall_verdict.value, "confidence": req_verdict.overall_confidence},
            )
            record_verification_event(
                db=db,
                request_id=new_req.id,
                stage_name="pipeline",
                event_type="PROCESSING_COMPLETED",
                status="success",
            )
            db.commit()

            return ReverifyResponse(
                status="completed",
                message=f"Re-verification succeeded. New Request #{new_req.id} created.",
                original_request_id=original.id,
                new_request_id=new_req.id,
                new_status="completed",
                verdict=req_verdict.overall_verdict.value,
                confidence=req_verdict.overall_confidence,
            )
        except Exception as exc:
            db.rollback()
            new_req.status = "failed"
            new_req.error_message = str(exc)
            new_req.completed_at = datetime.now(timezone.utc)
            db.commit()
            return ReverifyResponse(
                status="failed",
                message=f"Re-verification failed: {exc}",
                original_request_id=original.id,
                new_request_id=new_req.id,
                new_status="failed",
            )

    def _reverify_url(self, original: VerificationRequest, db: Session, user_id: Optional[int]) -> ReverifyResponse:
        from app.verification.article.service import ArticleVerificationService

        url = original.content
        if original.article and original.article.original_url:
            url = original.article.original_url

        if not url:
            return ReverifyResponse(
                status="failed",
                message="Cannot re-verify: original URL is missing.",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )

        article_service = ArticleVerificationService()
        try:
            result = article_service.verify_url(
                url=url,
                db=db,
                user_id=user_id or original.user_id,
                perform_search=True,
                extract_evidence=True,
                finalize_verdicts=True,
                max_claims=5,
            )
            new_req_id = result.get("request_id")
            # Update child request to point to original
            if new_req_id:
                new_req = db.query(VerificationRequest).filter_by(id=new_req_id).first()
                if new_req:
                    new_req.parent_request_id = original.id
                    record_verification_event(
                        db=db,
                        request_id=new_req.id,
                        stage_name="reverification",
                        event_type="REQUEST_CREATED",
                        status="success",
                        details={"parent_request_id": original.id},
                    )
                    db.commit()

            verdict_val = result.get("verdict", {}).get("overall_verdict") if result.get("verdict") else None
            conf_val = result.get("verdict", {}).get("overall_confidence") if result.get("verdict") else None

            return ReverifyResponse(
                status="completed",
                message=f"Re-verification of article URL succeeded. New Request #{new_req_id} generated.",
                original_request_id=original.id,
                new_request_id=new_req_id or 0,
                new_status="completed",
                verdict=verdict_val,
                confidence=conf_val,
            )
        except Exception as exc:
            return ReverifyResponse(
                status="failed",
                message=f"Re-verification of article URL failed: {exc}",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )

    def _reverify_image(self, original: VerificationRequest, db: Session, user_id: Optional[int]) -> ReverifyResponse:
        from app.verification.image.service import ImageVerificationService

        media_file = original.media_file
        if not media_file or not media_file.file_path or not os.path.exists(media_file.file_path):
            return ReverifyResponse(
                status="failed",
                message="Cannot re-verify: original image file is no longer available in storage.",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )

        with open(media_file.file_path, "rb") as f:
            file_bytes = f.read()

        image_service = ImageVerificationService()
        try:
            result = image_service.verify_image(
                file_bytes=file_bytes,
                original_filename=media_file.original_filename,
                db=db,
                user_id=user_id or original.user_id,
                perform_search=True,
                extract_evidence=True,
                finalize_verdicts=True,
                max_claims=5,
            )
            new_req_id = result.get("request_id")
            if new_req_id:
                new_req = db.query(VerificationRequest).filter_by(id=new_req_id).first()
                if new_req:
                    new_req.parent_request_id = original.id
                    record_verification_event(
                        db=db,
                        request_id=new_req.id,
                        stage_name="reverification",
                        event_type="REQUEST_CREATED",
                        status="success",
                        details={"parent_request_id": original.id},
                    )
                    db.commit()

            verdict_val = result.get("verdicts", {}).get("overall_verdict") if result.get("verdicts") else None
            conf_val = result.get("verdicts", {}).get("overall_confidence") if result.get("verdicts") else None

            return ReverifyResponse(
                status="completed",
                message=f"Re-verification of image succeeded. New Request #{new_req_id} generated.",
                original_request_id=original.id,
                new_request_id=new_req_id or 0,
                new_status="completed",
                verdict=verdict_val,
                confidence=conf_val,
            )
        except Exception as exc:
            return ReverifyResponse(
                status="failed",
                message=f"Re-verification of image failed: {exc}",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )

    def _reverify_media(self, original: VerificationRequest, db: Session, user_id: Optional[int]) -> ReverifyResponse:
        from app.verification.media.service import MediaVerificationService

        media_file = original.media_file
        if not media_file or not media_file.file_path or not os.path.exists(media_file.file_path):
            return ReverifyResponse(
                status="failed",
                message="Cannot re-verify: original audio/video file is no longer available in storage.",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )

        with open(media_file.file_path, "rb") as f:
            file_bytes = f.read()

        media_service = MediaVerificationService()
        try:
            result = media_service.verify_media(
                file_bytes=file_bytes,
                original_filename=media_file.original_filename,
                db=db,
                user_id=user_id or original.user_id,
                perform_search=True,
                extract_evidence=True,
                finalize_verdicts=True,
                max_claims=5,
            )
            new_req_id = result.get("request_id")
            if new_req_id:
                new_req = db.query(VerificationRequest).filter_by(id=new_req_id).first()
                if new_req:
                    new_req.parent_request_id = original.id
                    record_verification_event(
                        db=db,
                        request_id=new_req.id,
                        stage_name="reverification",
                        event_type="REQUEST_CREATED",
                        status="success",
                        details={"parent_request_id": original.id},
                    )
                    db.commit()

            verdict_val = result.get("verdicts", {}).get("overall_verdict") if result.get("verdicts") else None
            conf_val = result.get("verdicts", {}).get("overall_confidence") if result.get("verdicts") else None

            return ReverifyResponse(
                status="completed",
                message=f"Re-verification of multimedia succeeded. New Request #{new_req_id} generated.",
                original_request_id=original.id,
                new_request_id=new_req_id or 0,
                new_status="completed",
                verdict=verdict_val,
                confidence=conf_val,
            )
        except Exception as exc:
            return ReverifyResponse(
                status="failed",
                message=f"Re-verification of multimedia failed: {exc}",
                original_request_id=original.id,
                new_request_id=0,
                new_status="failed",
            )
