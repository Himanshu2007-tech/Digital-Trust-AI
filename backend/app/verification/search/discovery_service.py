import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.source import Source
from app.models.search_query import SearchQuery
from app.verification.search.base import SearchProvider
from app.verification.search.models import NormalizedSearchResult, SourceType, SearchQueryAudit
from app.verification.search.query_generator import SearchQueryGenerator, GeneratedQuery
from app.verification.search.providers.factory import get_search_provider

logger = logging.getLogger(__name__)


class SourceDiscoveryService:
    """
    Coordinates multi-source web search and source discovery for claims.
    Handles:
    - Query generation across 4 structured levels
    - Provider execution & rate limiting
    - Search Query audit trail logging
    - Source deduplication by canonical URL
    - Relational persistence linking Sources to Claims
    """

    def __init__(
        self,
        provider: Optional[SearchProvider] = None,
        query_generator: Optional[SearchQueryGenerator] = None
    ):
        self.provider = provider
        self.query_generator = query_generator or SearchQueryGenerator()

    def discover_sources_for_claim(
        self,
        claim_id: int,
        db: Session,
        max_queries: int = 3,
        max_results_per_query: int = 5
    ) -> Tuple[List[SearchQueryAudit], List[NormalizedSearchResult]]:
        """
        Loads claim from database and executes full source discovery pipeline.
        """
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim with ID {claim_id} not found in database.")

        provider = self.provider or get_search_provider()

        # 1. Generate search queries
        queries = self.query_generator.generate_queries(
            claim_text=claim.claim_text,
            entities=claim.entities or [],
            dates=claim.dates or [],
            numbers=claim.numbers or [],
            locations=claim.locations or [],
            source_attributions=claim.source_attributions or [],
            max_queries=max_queries
        )

        return self._execute_searches(
            claim=claim,
            queries=queries,
            provider=provider,
            db=db,
            max_results_per_query=max_results_per_query
        )

    def discover_sources_for_text(
        self,
        claim_text: str,
        entities: Optional[List[str]] = None,
        dates: Optional[List[str]] = None,
        numbers: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        source_attributions: Optional[List[str]] = None,
        db: Optional[Session] = None,
        claim_record: Optional[Claim] = None,
        max_queries: int = 3,
        max_results_per_query: int = 5
    ) -> Tuple[List[SearchQueryAudit], List[NormalizedSearchResult]]:
        """
        Discovers sources for an in-memory or unpersisted claim assertion.
        """
        provider = self.provider or get_search_provider()

        queries = self.query_generator.generate_queries(
            claim_text=claim_text,
            entities=entities or [],
            dates=dates or [],
            numbers=numbers or [],
            locations=locations or [],
            source_attributions=source_attributions or [],
            max_queries=max_queries
        )

        return self._execute_searches(
            claim=claim_record,
            queries=queries,
            provider=provider,
            db=db,
            max_results_per_query=max_results_per_query
        )

    def _execute_searches(
        self,
        claim: Optional[Claim],
        queries: List[GeneratedQuery],
        provider: SearchProvider,
        db: Optional[Session],
        max_results_per_query: int
    ) -> Tuple[List[SearchQueryAudit], List[NormalizedSearchResult]]:
        audit_records: List[SearchQueryAudit] = []
        all_results: List[NormalizedSearchResult] = []
        seen_canonical_urls: set = set()

        for q in queries:
            query_audit = SearchQueryAudit(
                claim_id=claim.id if claim else None,
                query_text=q.query_text,
                strategy_level=q.strategy_level,
                search_engine=provider.provider_name,
                results_count=0,
                status="pending"
            )

            raw_results: List[NormalizedSearchResult] = []
            try:
                raw_results = provider.search(q.query_text, max_results=max_results_per_query)
                query_audit.results_count = len(raw_results)
                query_audit.status = "success" if raw_results else "empty"
                query_audit.raw_response_json = [r.model_dump() for r in raw_results]
            except Exception as exc:
                logger.warning(f"Search provider error for query '{q.query_text}': {exc}")
                query_audit.status = "failed"
                query_audit.error_message = str(exc)

            audit_records.append(query_audit)

            # Persist audit record to SearchQuery table if db is provided
            if db and claim:
                sq_entry = SearchQuery(
                    claim_id=claim.id,
                    query_text=query_audit.query_text,
                    search_engine=query_audit.search_engine,
                    results_count=query_audit.results_count,
                    status=query_audit.status,
                    error_message=query_audit.error_message,
                    raw_response_json=query_audit.raw_response_json
                )
                db.add(sq_entry)

            # Collect and deduplicate unique results
            for res in raw_results:
                if res.canonical_url not in seen_canonical_urls:
                    seen_canonical_urls.add(res.canonical_url)
                    all_results.append(res)

                    # Persist to Source table and link to Claim
                    if db and claim:
                        self._persist_source(db, claim, res)

        if db:
            db.commit()

        return audit_records, all_results

    def _persist_source(self, db: Session, claim: Claim, res: NormalizedSearchResult):
        """Finds or creates Source record and associates it with the Claim."""
        existing_source = db.query(Source).filter(
            (Source.canonical_url == res.canonical_url) | (Source.url == res.url)
        ).first()

        if not existing_source:
            existing_source = Source(
                name=res.title[:255] if res.title else res.domain,
                domain=res.domain,
                url=res.url,
                canonical_url=res.canonical_url,
                title=res.title,
                snippet=res.snippet,
                publisher=res.publisher,
                author=res.author,
                country=res.country,
                publication_date=res.published_at,
                query_used=res.query,
                provider=res.provider,
                retrieved_at=datetime.utcnow(),
                syndication_source=res.syndication_source,
                source_type=res.source_type.value,
                credibility_score=None,  # No fake scores
                reliability_tier="unrated"
            )
            db.add(existing_source)
            db.flush()

        # Establish many-to-many link if not already linked
        if existing_source not in claim.sources:
            claim.sources.append(existing_source)
