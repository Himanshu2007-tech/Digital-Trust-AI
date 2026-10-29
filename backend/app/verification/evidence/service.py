import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.verification.evidence.base import EvidenceAnalyzer
from app.verification.evidence.hybrid import HybridEvidenceAnalyzer
from app.verification.evidence.comparator import SourceComparator
from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem,
    SourceComparisonItem
)

logger = logging.getLogger(__name__)


class EvidenceAnalysisService:
    """
    Orchestration service for extracting traceable evidence passages from discovered web sources
    and performing pairwise & consensus source comparisons.
    Guarantees idempotency and avoids redundant repeated analysis.
    """

    def __init__(
        self,
        analyzer: Optional[EvidenceAnalyzer] = None,
        comparator: Optional[SourceComparator] = None
    ):
        self.analyzer = analyzer or HybridEvidenceAnalyzer()
        self.comparator = comparator or SourceComparator()

    def analyze_evidence_for_claim(
        self,
        claim_id: int,
        db: Session,
        force_refresh: bool = False
    ) -> Tuple[List[ExtractedEvidenceItem], List[SourceComparisonItem]]:
        """
        Extracts evidence from all sources linked to a claim and performs source comparison.
        Persists results to the database.
        """
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim with ID {claim_id} does not exist.")

        sources = claim.sources
        if not sources:
            logger.info(f"No sources linked to claim {claim_id}. Returning empty evidence.")
            return [], []

        evidence_items: List[ExtractedEvidenceItem] = []

        # Check existing evidence in DB to prevent redundant analysis
        existing_evidence_map = {}
        if not force_refresh:
            existing_db_ev = db.query(Evidence).filter(Evidence.claim_id == claim_id).all()
            for ev in existing_db_ev:
                if ev.source_id is not None:
                    existing_evidence_map[ev.source_id] = ev

        for src in sources:
            if src.id in existing_evidence_map and not force_refresh:
                ev_rec = existing_evidence_map[src.id]
                evidence_items.append(self._db_evidence_to_domain(ev_rec, src))
                continue

            # Run analyzer
            try:
                analyzed_item = self.analyzer.analyze_evidence(
                    claim_id=claim.id,
                    claim_text=claim.claim_text,
                    source_id=src.id,
                    source_title=src.title,
                    source_snippet=src.snippet,
                    source_url=src.url or src.canonical_url or f"https://{src.domain}",
                    source_domain=src.domain,
                    source_publisher=src.publisher,
                    publish_date=src.publication_date,
                    claim_entities=claim.entities or [],
                    claim_numbers=claim.numbers or [],
                    claim_dates=claim.dates or [],
                )

                # Persist or update in DB
                db_ev = Evidence(
                    claim_id=claim.id,
                    source_id=src.id,
                    evidence_type=analyzed_item.evidence_type.value,
                    direction=analyzed_item.direction,
                    evidence_text=analyzed_item.evidence_text,
                    snippet=analyzed_item.snippet,
                    url=analyzed_item.url,
                    article_title=analyzed_item.article_title,
                    publish_date=analyzed_item.publish_date,
                    source_location=analyzed_item.source_location,
                    relevance=analyzed_item.relevance.value,
                    relevance_score=analyzed_item.relevance_score,
                    confidence_in_extraction=analyzed_item.confidence_in_extraction,
                    stance_confidence=analyzed_item.stance_confidence,
                    extraction_method=analyzed_item.extraction_method,
                    extracted_at=analyzed_item.extracted_at or datetime.now(timezone.utc)
                )
                db.add(db_ev)
                db.flush()
                analyzed_item.id = db_ev.id
                evidence_items.append(analyzed_item)
            except Exception as err:
                logger.error(f"Failed to analyze evidence for source {src.id} on claim {claim.id}: {err}")

        # Perform Source Comparison
        comparison_items = self.comparator.compare_sources_for_claim(
            claim_id=claim.id,
            evidence_items=evidence_items
        )

        # Clear previous comparisons for this claim and save new ones
        db.query(SourceComparison).filter(SourceComparison.claim_id == claim.id).delete()
        db.flush()

        for sc in comparison_items:
            db_sc = SourceComparison(
                claim_id=claim.id,
                source_a_id=sc.source_a_id,
                source_b_id=sc.source_b_id,
                comparison_type=sc.comparison_type,
                source_relationship=sc.source_relationship.value,
                evidence_consistency=sc.evidence_consistency.value,
                details=sc.details,
                supporting_sources_count=sc.supporting_sources_count,
                contradicting_sources_count=sc.contradicting_sources_count,
                neutral_sources_count=sc.neutral_sources_count,
                consensus_verdict=sc.consensus_verdict,
                analysis_summary=sc.analysis_summary
            )
            db.add(db_sc)
            db.flush()
            sc.id = db_sc.id

        db.commit()
        return evidence_items, comparison_items

    def analyze_evidence_for_request(
        self,
        request_id: int,
        db: Session,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Bulk analyzes evidence for all claims in a verification request."""
        claims = db.query(Claim).filter(Claim.request_id == request_id).all()
        if not claims:
            raise ValueError(f"No claims found for verification request {request_id}")

        total_evidence = 0
        total_comparisons = 0
        results_per_claim = []

        for c in claims:
            ev_list, comp_list = self.analyze_evidence_for_claim(
                claim_id=c.id, db=db, force_refresh=force_refresh
            )
            total_evidence += len(ev_list)
            total_comparisons += len(comp_list)
            results_per_claim.append({
                "claim_id": c.id,
                "claim_text": c.claim_text,
                "evidence_count": len(ev_list),
                "evidence": [e.model_dump() for e in ev_list],
                "comparisons_count": len(comp_list),
                "comparisons": [cmp.model_dump() for cmp in comp_list]
            })

        return {
            "request_id": request_id,
            "claims_analyzed": len(claims),
            "total_evidence": total_evidence,
            "total_comparisons": total_comparisons,
            "claims": results_per_claim
        }

    def _db_evidence_to_domain(self, ev_rec: Evidence, src: Source) -> ExtractedEvidenceItem:
        """Maps an existing DB Evidence record to domain model."""
        try:
            ev_type = EvidenceType(ev_rec.evidence_type)
        except ValueError:
            ev_type = EvidenceType.CONTEXTUAL

        try:
            rel = EvidenceRelevance(ev_rec.relevance)
        except ValueError:
            rel = EvidenceRelevance.MEDIUM

        return ExtractedEvidenceItem(
            id=ev_rec.id,
            claim_id=ev_rec.claim_id,
            source_id=ev_rec.source_id,
            evidence_text=ev_rec.evidence_text or ev_rec.snippet,
            snippet=ev_rec.snippet,
            evidence_type=ev_type,
            direction=ev_rec.direction or ev_type.value,
            relevance=rel,
            relevance_score=ev_rec.relevance_score,
            confidence_in_extraction=ev_rec.confidence_in_extraction,
            stance_confidence=ev_rec.stance_confidence,
            source_location=ev_rec.source_location,
            extraction_method=ev_rec.extraction_method,
            extracted_at=ev_rec.extracted_at,
            url=ev_rec.url,
            article_title=ev_rec.article_title or src.title,
            publisher=src.publisher,
            domain=src.domain,
            publish_date=ev_rec.publish_date or src.publication_date,
            explanation=f"Stored evidence ({ev_type.value}) with {rel.value} relevance."
        )
