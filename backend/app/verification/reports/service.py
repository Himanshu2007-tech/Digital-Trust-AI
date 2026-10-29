"""
TruthLens AI — Professional Report Management Service (Part 12)
Handles database persistence, secure file storage, SHA-256 fingerprinting,
and path-traversal-safe download resolution for PDF dossiers.
"""

import os
import uuid
import time
import hashlib
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.core.exceptions import TruthLensException
from app.models.report import Report
from app.models.verification_request import VerificationRequest
from app.verification.history.service import HistoryService, record_verification_event
from app.verification.reports.dossier_report import DossierReportGenerator

logger = logging.getLogger(__name__)


class ReportService:
    """Enterprise report lifecycle service for generating, listing, retrieving, and safely deleting verification reports."""

    def __init__(self):
        self.history_service = HistoryService()

    def generate_report(
        self,
        db: Session,
        request_id: int,
        user_id: Optional[int] = None,
        title: Optional[str] = None
    ) -> Report:
        """
        Generate and persist a professional PDF verification dossier for a saved request.
        Computes SHA-256 integrity hash and records lifecycle audit events.
        """
        start_time = time.time()

        # 1. Verify existence of verification request
        vr = db.query(VerificationRequest).filter(VerificationRequest.id == request_id).first()
        if not vr:
            raise TruthLensException(
                message=f"Verification request #{request_id} does not exist.",
                status_code=404
            )

        # 2. Fetch authentic verification dossier from database
        dossier = self.history_service.get_history_detail(request_id=request_id, db=db, user_id=None)
        if not dossier:
            raise TruthLensException(
                message=f"Failed to retrieve verification dossier for request #{request_id}.",
                status_code=404
            )

        # 3. Compile report metadata
        report_uuid = f"rep_{uuid.uuid4().hex[:16]}"
        default_title = f"TruthLens Verification Dossier — {vr.request_type.capitalize()} #{request_id}"
        final_title = title.strip() if (title and title.strip()) else default_title

        # Ensure reports storage folder exists
        storage_dir = Path(settings.REPORTS_STORAGE_PATH).resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{report_uuid}.pdf"
        file_path = str(storage_dir / filename)

        try:
            # 4. Generate multi-page PDF bytes
            generator = DossierReportGenerator(report_uuid=report_uuid, version="1.0")
            dossier_dict = dossier.model_dump()
            pdf_bytes = generator.generate_dossier_pdf(dossier_dict, report_title=final_title)

            # 5. Compute cryptographic SHA-256 hash of PDF bytes
            sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
            file_size_bytes = len(pdf_bytes)

            # 6. Write file atomically to disk
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)

            generation_time_ms = int((time.time() - start_time) * 1000)

            # 7. Persist Report record in database
            report = Report(
                report_uuid=report_uuid,
                request_id=request_id,
                user_id=user_id or vr.user_id,
                title=final_title,
                format="pdf",
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                mime_type="application/pdf",
                sha256_hash=sha256_hash,
                status="generated",
                version="1.0",
                generated_at=datetime.now(timezone.utc),
                generation_time_ms=generation_time_ms,
                error_message=None
            )
            db.add(report)
            db.commit()
            db.refresh(report)

            # 8. Record audit event
            record_verification_event(
                db=db,
                request_id=request_id,
                stage_name="report_generation",
                event_type="pdf_generated",
                status="success",
                details={
                    "report_id": report.id,
                    "report_uuid": report_uuid,
                    "file_size_bytes": file_size_bytes,
                    "sha256_hash": sha256_hash,
                    "generation_time_ms": generation_time_ms
                }
            )

            logger.info("Generated PDF report %s (%d bytes) for request %d in %d ms", report_uuid, file_size_bytes, request_id, generation_time_ms)
            return report

        except Exception as exc:
            db.rollback()
            logger.exception("Failed generating report for request %d: %s", request_id, exc)
            # Create failed record if needed
            failed_report = Report(
                report_uuid=report_uuid,
                request_id=request_id,
                user_id=user_id or vr.user_id,
                title=final_title,
                format="pdf",
                file_path=None,
                file_size_bytes=None,
                mime_type="application/pdf",
                sha256_hash=None,
                status="failed",
                version="1.0",
                generated_at=None,
                generation_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(exc)
            )
            db.add(failed_report)
            db.commit()
            db.refresh(failed_report)

            record_verification_event(
                db=db,
                request_id=request_id,
                stage_name="report_generation",
                event_type="pdf_failed",
                status="error",
                details={"error": str(exc), "report_uuid": report_uuid}
            )
            raise TruthLensException(
                message=f"PDF generation failed: {exc}",
                status_code=500
            )

    def get_reports(
        self,
        db: Session,
        request_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Report], int]:
        """List reports with pagination and filtering."""
        q = db.query(Report)

        if request_id is not None:
            q = q.filter(Report.request_id == request_id)
        if user_id is not None:
            q = q.filter(Report.user_id == user_id)
        if status is not None and status.strip():
            q = q.filter(Report.status == status.strip().lower())

        total_count = q.count()
        offset = max(0, (page - 1) * page_size)
        reports = q.order_by(desc(Report.created_at)).offset(offset).limit(page_size).all()
        return reports, total_count

    def get_report_by_id(
        self,
        db: Session,
        report_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Report]:
        """Retrieve a specific report by database ID."""
        q = db.query(Report).filter(Report.id == report_id)
        if user_id is not None:
            q = q.filter(Report.user_id == user_id)
        return q.first()

    def get_report_by_uuid(
        self,
        db: Session,
        report_uuid: str,
        user_id: Optional[int] = None
    ) -> Optional[Report]:
        """Retrieve a specific report by report UUID."""
        q = db.query(Report).filter(Report.report_uuid == report_uuid)
        if user_id is not None:
            q = q.filter(Report.user_id == user_id)
        return q.first()

    def get_report_file_path(self, report: Report) -> str:
        """
        Validate and resolve secure absolute file path on disk.
        Prevents path traversal attacks and verifies physical file existence.
        """
        if not report.file_path:
            raise TruthLensException(
                message=f"Report #{report.id} does not have an associated file.",
                status_code=404
            )

        storage_root = Path(settings.REPORTS_STORAGE_PATH).resolve()
        target_path = Path(report.file_path).resolve()

        # Strict path traversal check: target path must be inside storage_root
        try:
            target_path.relative_to(storage_root)
        except ValueError:
            logger.error("Security alert: Attempted path traversal for report %d: %s", report.id, report.file_path)
            raise TruthLensException(
                message="Access to the requested report file path is unauthorized.",
                status_code=403
            )

        if not target_path.is_file():
            logger.warning("Report file missing on disk: %s", target_path)
            raise TruthLensException(
                message="The physical report file is no longer available on disk.",
                status_code=404
            )

        # Cryptographic integrity check: verify disk file against recorded SHA-256 fingerprint
        if report.sha256_hash:
            try:
                with open(target_path, "rb") as f:
                    disk_hash = hashlib.sha256(f.read()).hexdigest()
                if disk_hash.lower() != report.sha256_hash.lower():
                    logger.error(
                        "Integrity alert: Report %d file hash mismatch (stored=%s, disk=%s)",
                        report.id, report.sha256_hash, disk_hash
                    )
                    raise TruthLensException(
                        message="Report file failed integrity verification (file has been modified or corrupted).",
                        status_code=409
                    )
            except TruthLensException:
                raise
            except Exception as e:
                logger.error("Failed to read report file for hash verification: %s", e)
                raise TruthLensException(
                    message="Error verifying report file integrity.",
                    status_code=500
                )

        return str(target_path)

    def delete_report(
        self,
        db: Session,
        report_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """Safely delete a report record and its file on disk."""
        report = self.get_report_by_id(db, report_id, user_id=user_id)
        if not report:
            return False

        # Attempt to delete file from disk
        if report.file_path:
            try:
                storage_root = Path(settings.REPORTS_STORAGE_PATH).resolve()
                p = Path(report.file_path).resolve()
                if p.is_relative_to(storage_root) and p.is_file():
                    p.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Failed to delete report file %s: %s", report.file_path, e)

        db.delete(report)
        db.commit()
        return True


report_service = ReportService()
