import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.claim import Claim
from app.models.search_query import SearchQuery
from app.schemas.search import (
    ClaimSearchRequest,
    ClaimSearchResponse,
    DiscoveredSourceSchema,
    SearchQueryAuditSchema
)
from app.verification.search.discovery_service import SourceDiscoveryService

logger = logging.getLogger(__name__)

router = APIRouter()
discovery_service = SourceDiscoveryService()


@router.post(
    "/search/claim",
    response_model=ClaimSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Web Sources for a Claim",
    description=(
        "Executes multi-level search queries across real web search engines for a factual claim. "
        "Normalizes, deduplicates, and classifies retrieved sources into primary, reliable news, "
        "and fact-check tiers while logging search queries for transparency."
    )
)
def search_claim(
    payload: ClaimSearchRequest,
    db: Session = Depends(get_db)
):
    if not payload.claim_id and not (payload.claim_text and payload.claim_text.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'claim_id' or non-empty 'claim_text' must be provided."
        )

    target_text = payload.claim_text
    claim_record = None

    if payload.claim_id:
        claim_record = db.query(Claim).filter(Claim.id == payload.claim_id).first()
        if not claim_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim with ID {payload.claim_id} not found."
            )
        target_text = claim_record.claim_text

    try:
        if claim_record:
            audit_records, sources = discovery_service.discover_sources_for_claim(
                claim_id=claim_record.id,
                db=db,
                max_queries=payload.max_queries,
                max_results_per_query=payload.max_results_per_query
            )
        else:
            audit_records, sources = discovery_service.discover_sources_for_text(
                claim_text=target_text,
                db=db,
                max_queries=payload.max_queries,
                max_results_per_query=payload.max_results_per_query
            )
    except Exception as exc:
        logger.error(f"Search discovery failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Web search discovery encountered an error: {str(exc)}"
        )

    # Format response
    audit_schemas = [
        SearchQueryAuditSchema(
            query_text=a.query_text,
            strategy_level=a.strategy_level,
            search_engine=a.search_engine,
            results_count=a.results_count,
            status=a.status,
            error_message=a.error_message
        )
        for a in audit_records
    ]

    source_schemas = [
        DiscoveredSourceSchema(
            title=s.title,
            url=s.url,
            canonical_url=s.canonical_url,
            domain=s.domain,
            snippet=s.snippet,
            published_at=s.published_at,
            publisher=s.publisher,
            author=s.author,
            country=s.country,
            source_type=s.source_type.value,
            query=s.query,
            retrieved_at=s.retrieved_at,
            provider=s.provider,
            syndication_source=s.syndication_source
        )
        for s in sources
    ]

    provider_name = audit_records[0].search_engine if audit_records else "duckduckgo"
    message = (
        f"Discovered {len(source_schemas)} sources across {len(audit_schemas)} search queries. "
        "Evidence analysis and final verdicts will be evaluated in a subsequent phase."
    ) if source_schemas else "No relevant sources were found for this claim."

    return ClaimSearchResponse(
        status="success",
        claim_id=claim_record.id if claim_record else None,
        claim_text=target_text,
        queries_count=len(audit_schemas),
        sources_count=len(source_schemas),
        queries=audit_schemas,
        sources=source_schemas,
        provider=provider_name,
        message=message
    )


@router.get(
    "/search/audit/{claim_id}",
    response_model=List[SearchQueryAuditSchema],
    summary="Get Search Audit Trail for a Claim",
    description="Returns the transparent log of search queries performed by TruthLens AI for a specific claim."
)
def get_search_audit(
    claim_id: int,
    db: Session = Depends(get_db)
):
    queries = db.query(SearchQuery).filter(SearchQuery.claim_id == claim_id).order_by(SearchQuery.created_at.asc()).all()
    return [
        SearchQueryAuditSchema(
            query_text=q.query_text,
            strategy_level="LOGGED",
            search_engine=q.search_engine,
            results_count=q.results_count,
            status=q.status,
            error_message=q.error_message
        )
        for q in queries
    ]
