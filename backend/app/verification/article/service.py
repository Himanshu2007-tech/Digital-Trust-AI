import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.verification_request import VerificationRequest
from app.models.article import Article
from app.models.claim import Claim
from app.models.source import Source
from app.verification.article.base import ExtractedArticle
from app.verification.article.fetcher import SafeArticleFetcher
from app.verification.article.extractor import ReadabilityArticleExtractor
from app.verification.extractors.hybrid import HybridClaimExtractor
from app.verification.search.discovery_service import SourceDiscoveryService
from app.verification.evidence.service import EvidenceAnalysisService
from app.verification.verdict.service import VerdictService
from app.verification.history.service import compute_content_hash, record_verification_event

logger = logging.getLogger(__name__)


class ArticleVerificationService:
    """
    End-to-end orchestration service for News URL Article Verification.
    Coordinates:
    1. Safe HTTP fetching with SSRF & size protection
    2. Readability article extraction, DOM cleaning, and hashing
    3. Claim extraction from article body (Part 3)
    4. Origin source tagging as USER_SUBMITTED_ARTICLE (strictly non-self-corroborating)
    5. Independent multi-source web discovery (Part 4)
    6. Evidence extraction and cross-source comparisons (Part 5)
    7. Overall dossier verdict & confidence scoring (Part 6)
    """

    def __init__(
        self,
        fetcher: Optional[SafeArticleFetcher] = None,
        extractor: Optional[ReadabilityArticleExtractor] = None,
        claim_extractor: Optional[HybridClaimExtractor] = None,
        discovery_service: Optional[SourceDiscoveryService] = None,
        evidence_service: Optional[EvidenceAnalysisService] = None,
        verdict_service: Optional[VerdictService] = None,
    ):
        self.fetcher = fetcher or SafeArticleFetcher()
        self.extractor = extractor or ReadabilityArticleExtractor()
        self.claim_extractor = claim_extractor or HybridClaimExtractor()
        self.discovery_service = discovery_service or SourceDiscoveryService()
        self.evidence_service = evidence_service or EvidenceAnalysisService()
        self.verdict_service = verdict_service or VerdictService()

    def verify_url(
        self,
        url: str,
        db: Session,
        user_id: Optional[int] = None,
        perform_search: bool = True,
        extract_evidence: bool = True,
        finalize_verdicts: bool = True,
        max_claims: int = 5
    ) -> Dict[str, Any]:
        """
        Executes complete verification pipeline for a user-submitted news URL.
        """
        # 1. Safe fetch HTML
        html_content, final_url, status_code = self.fetcher.fetch(url)

        # 2. Extract article structure & clean text
        extracted: ExtractedArticle = self.extractor.extract_article(html_content, final_url)

        # 3. Create VerificationRequest
        url_hash = compute_content_hash(extracted.canonical_url or extracted.original_url)
        v_request = VerificationRequest(
            user_id=user_id,
            request_type="url",
            content=extracted.original_url,
            content_hash=url_hash,
            status="processing",
            priority=0
        )
        db.add(v_request)
        db.flush()

        record_verification_event(
            db=db,
            request_id=v_request.id,
            stage_name="initialization",
            event_type="REQUEST_CREATED",
            status="success",
            details={"url": extracted.original_url, "domain": extracted.domain}
        )

        # 4. Save Article record
        db_article = Article(
            request_id=v_request.id,
            original_url=extracted.original_url,
            canonical_url=extracted.canonical_url,
            domain=extracted.domain,
            title=extracted.title,
            publisher=extracted.publisher,
            author=extracted.author,
            published_at=extracted.published_at,
            description=extracted.description,
            language=extracted.language,
            featured_image_url=extracted.featured_image_url,
            article_text=extracted.article_text,
            content_hash=extracted.content_hash,
            content_length=extracted.content_length,
            word_count=extracted.word_count,
            extraction_method=extracted.extraction_method,
            retrieval_status=extracted.retrieval_status,
            retrieved_at=extracted.retrieved_at or datetime.now(timezone.utc)
        )
        db.add(db_article)
        db.flush()

        # 5. Register Submitted Article as origin Source (tagged USER_SUBMITTED_ARTICLE)
        submitted_source = self._get_or_create_submitted_source(db, extracted)

        # 6. Extract Claims from Article Text (Part 3)
        # Cap text for claim extraction to 18,000 chars to respect preprocessing limits
        text_for_claims = extracted.article_text[:18000]
        extracted_claim_items = self.claim_extractor.extract_claims(
            text_for_claims,
            context=f"News article from {extracted.publisher or extracted.domain}: {extracted.title or ''}"
        )

        saved_db_claims: List[Claim] = []
        now_utc = datetime.now(timezone.utc)

        if not extracted_claim_items and extracted.title:
            # Fallback: if body is conversational or dense without clear atomic patterns,
            # use title or lead sentence as the primary verifiable claim
            from app.verification.domain_models import ExtractedClaimItem, ClaimType, Verifiability, Importance
            extracted_claim_items = [
                ExtractedClaimItem(
                    text=extracted.title,
                    normalized_text=extracted.title.lower(),
                    claim_type=ClaimType.FACTUAL,
                    verifiability=Verifiability.VERIFIABLE,
                    importance=Importance.HIGH,
                    entities=[],
                    dates=[extracted.published_at] if extracted.published_at else [],
                    locations=[],
                    numbers=[],
                    source_attributions=[extracted.publisher] if extracted.publisher else [],
                    original_sentence=extracted.title,
                    extraction_method="title_fallback"
                )
            ]

        # Limit to max_claims
        target_claim_items = extracted_claim_items[:max_claims]

        for item in target_claim_items:
            db_claim = Claim(
                request_id=v_request.id,
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
                status="extracted"
            )
            # Link origin submitted source
            db_claim.sources.append(submitted_source)
            db.add(db_claim)
            db.flush()
            saved_db_claims.append(db_claim)

        db.commit()

        # 7. Independent Web Search & Source Discovery (Part 4)
        queries_schemas: List[Dict[str, Any]] = []
        independent_sources_map: Dict[str, Dict[str, Any]] = {}
        active_provider: Optional[str] = None

        if perform_search and saved_db_claims:
            for c_rec in saved_db_claims:
                try:
                    audits, results = self.discovery_service.discover_sources_for_claim(
                        claim_id=c_rec.id,
                        db=db,
                        max_queries=2,
                        max_results_per_query=4
                    )
                    for a in audits:
                        queries_schemas.append({
                            "query_text": a.query_text,
                            "strategy_level": a.strategy_level,
                            "search_engine": a.search_engine,
                            "results_count": a.results_count,
                            "status": a.status,
                            "error_message": a.error_message
                        })
                        if not active_provider:
                            active_provider = a.search_engine

                    for r in results:
                        # CRITICAL: Exclude submitted article's own domain or URL from independent sources
                        r_domain = (r.domain or "").lower().replace("www.", "")
                        sub_domain = extracted.domain.lower().replace("www.", "")

                        if r_domain == sub_domain or r.canonical_url == extracted.canonical_url or r.url == extracted.original_url:
                            logger.info(f"Skipping self-referential search result from same domain: {r.url}")
                            continue

                        if r.canonical_url not in independent_sources_map:
                            independent_sources_map[r.canonical_url] = {
                                "title": r.title,
                                "url": r.url,
                                "canonical_url": r.canonical_url,
                                "domain": r.domain,
                                "snippet": r.snippet,
                                "published_at": r.published_at,
                                "publisher": r.publisher,
                                "author": r.author,
                                "country": r.country,
                                "source_type": r.source_type.value,
                                "source_role": "INDEPENDENT_SOURCE",
                                "query": r.query,
                                "retrieved_at": r.retrieved_at,
                                "provider": r.provider,
                                "syndication_source": r.syndication_source
                            }
                except Exception as s_err:
                    logger.warning(f"Search error for claim {c_rec.id}: {s_err}")
                    queries_schemas.append({
                        "query_text": f"Search failed for claim {c_rec.id}",
                        "strategy_level": "ERROR",
                        "search_engine": "unknown",
                        "results_count": 0,
                        "status": "failed",
                        "error_message": str(s_err)
                    })

        # 8. Evidence Extraction & Source Comparison (Part 5)
        evidence_schemas: List[Dict[str, Any]] = []
        comparison_schemas: List[Dict[str, Any]] = []

        if extract_evidence and saved_db_claims:
            for c_rec in saved_db_claims:
                try:
                    ev_items, comp_items = self.evidence_service.analyze_evidence_for_claim(
                        claim_id=c_rec.id,
                        db=db
                    )
                    for e in ev_items:
                        # If evidence came from the submitted article itself, ensure it is tagged as subject, not independent corroboration
                        if e.source_id == submitted_source.id or (e.domain and e.domain.lower() == extracted.domain.lower()):
                            e.evidence_type = e.evidence_type.__class__.CONTEXTUAL
                            e.explanation = "Assertion from submitted article (subject of verification, does not self-corroborate)."

                        evidence_schemas.append({
                            "id": e.id,
                            "claim_id": e.claim_id,
                            "source_id": e.source_id,
                            "evidence_text": e.evidence_text,
                            "snippet": e.snippet,
                            "evidence_type": e.evidence_type.value,
                            "direction": e.direction,
                            "relevance": e.relevance.value,
                            "relevance_score": e.relevance_score,
                            "confidence_in_extraction": e.confidence_in_extraction,
                            "stance_confidence": e.stance_confidence,
                            "source_location": e.source_location,
                            "extraction_method": e.extraction_method,
                            "extracted_at": e.extracted_at,
                            "url": e.url,
                            "article_title": e.article_title,
                            "publisher": e.publisher,
                            "domain": e.domain,
                            "publish_date": e.publish_date,
                            "explanation": e.explanation
                        })

                    for cmp in comp_items:
                        comparison_schemas.append({
                            "id": cmp.id,
                            "claim_id": cmp.claim_id,
                            "source_a_id": cmp.source_a_id,
                            "source_b_id": cmp.source_b_id,
                            "source_a_title": cmp.source_a_title,
                            "source_b_title": cmp.source_b_title,
                            "source_a_domain": cmp.source_a_domain,
                            "source_b_domain": cmp.source_b_domain,
                            "comparison_type": cmp.comparison_type,
                            "source_relationship": cmp.source_relationship.value,
                            "evidence_consistency": cmp.evidence_consistency.value,
                            "details": cmp.details,
                            "supporting_sources_count": cmp.supporting_sources_count,
                            "contradicting_sources_count": cmp.contradicting_sources_count,
                            "neutral_sources_count": cmp.neutral_sources_count,
                            "consensus_verdict": cmp.consensus_verdict,
                            "analysis_summary": cmp.analysis_summary
                        })
                except Exception as ev_err:
                    logger.warning(f"Evidence extraction error for claim {c_rec.id}: {ev_err}")

        # 9. Verdict Synthesis & Final Dossier (Part 6)
        request_verdict_dict: Optional[Dict[str, Any]] = None
        claim_verdict_dicts: List[Dict[str, Any]] = []

        if finalize_verdicts and saved_db_claims:
            try:
                res_verdict = self.verdict_service.finalize_request(
                    request_id=v_request.id,
                    db=db,
                    reevaluate_claims=False
                )
                for cv in res_verdict.claims:
                    claim_verdict_dicts.append({
                        "id": cv.id,
                        "claim_id": cv.claim_id,
                        "claim_text": cv.claim_text,
                        "verdict": cv.verdict.value,
                        "confidence": cv.confidence,
                        "confidence_level": cv.confidence_level.value,
                        "evidence_strength": cv.evidence_strength.value,
                        "explanation": cv.explanation,
                        "supporting_evidence_ids": cv.supporting_evidence_ids,
                        "contradicting_evidence_ids": cv.contradicting_evidence_ids,
                        "contextual_evidence_ids": cv.contextual_evidence_ids,
                        "limitations": cv.limitations,
                        "methodology_version": cv.methodology_version,
                        "generated_at": cv.generated_at
                    })

                request_verdict_dict = {
                    "id": res_verdict.id,
                    "request_id": res_verdict.request_id,
                    "overall_verdict": res_verdict.overall_verdict.value,
                    "overall_confidence": res_verdict.overall_confidence,
                    "summary": res_verdict.summary,
                    "claims": claim_verdict_dicts,
                    "claims_count": res_verdict.claims_count,
                    "supported_count": res_verdict.supported_count,
                    "contradicted_count": res_verdict.contradicted_count,
                    "misleading_count": res_verdict.misleading_count,
                    "unverified_count": res_verdict.unverified_count,
                    "insufficient_count": res_verdict.insufficient_count,
                    "limitations": res_verdict.limitations,
                    "methodology_notes": res_verdict.methodology_notes,
                    "generated_at": res_verdict.generated_at
                }
            except Exception as v_err:
                logger.warning(f"Verdict synthesis error for request {v_request.id}: {v_err}")

        # 10. Assemble complete response
        retrieved_at_str = (
            submitted_source.retrieved_at.isoformat()
            if hasattr(submitted_source.retrieved_at, "isoformat")
            else str(submitted_source.retrieved_at or datetime.now(timezone.utc).isoformat())
        )

        submitted_source_dict = {
            "title": submitted_source.title,
            "url": submitted_source.url,
            "canonical_url": submitted_source.canonical_url,
            "domain": submitted_source.domain,
            "snippet": submitted_source.snippet,
            "published_at": submitted_source.publication_date,
            "publisher": submitted_source.publisher,
            "author": submitted_source.author,
            "country": submitted_source.country,
            "source_type": submitted_source.source_type,
            "source_role": "USER_SUBMITTED_ARTICLE",
            "query": submitted_source.query_used,
            "retrieved_at": retrieved_at_str,
            "provider": submitted_source.provider,
            "syndication_source": submitted_source.syndication_source
        }

        independent_sources_list = list(independent_sources_map.values())
        all_sources = [submitted_source_dict] + independent_sources_list

        v_request.status = "completed"
        db.commit()

        article_dict = {
            "id": db_article.id,
            "request_id": db_article.request_id,
            "original_url": db_article.original_url,
            "canonical_url": db_article.canonical_url,
            "domain": db_article.domain,
            "title": db_article.title,
            "publisher": db_article.publisher,
            "author": db_article.author,
            "published_at": db_article.published_at,
            "description": db_article.description,
            "language": db_article.language,
            "featured_image_url": db_article.featured_image_url,
            "article_text": db_article.article_text,
            "content_hash": db_article.content_hash,
            "content_length": db_article.content_length,
            "word_count": db_article.word_count,
            "extraction_method": db_article.extraction_method,
            "retrieval_status": db_article.retrieval_status,
            "retrieved_at": db_article.retrieved_at
        }

        claims_response_list = []
        for c in saved_db_claims:
            claims_response_list.append({
                "id": f"claim_{c.id}",
                "db_id": c.id,
                "text": c.claim_text,
                "normalized_text": c.normalized_text,
                "claim_type": c.claim_type,
                "verifiability": c.verifiability,
                "importance": c.importance,
                "entities": c.entities or [],
                "dates": c.dates or [],
                "locations": c.locations or [],
                "numbers": c.numbers or [],
                "source_attributions": c.source_attributions or [],
                "original_sentence": c.original_sentence or c.claim_text,
                "extraction_method": c.extraction_method or "hybrid"
            })

        summary_msg = (
            f"Extracted article from {extracted.domain} ({extracted.word_count} words). "
            f"Evaluated {len(saved_db_claims)} claims across {len(independent_sources_list)} independent sources."
        )

        v_request.status = "completed"
        v_request.completed_at = datetime.now(timezone.utc)
        record_verification_event(
            db=db,
            request_id=v_request.id,
            stage_name="pipeline",
            event_type="PROCESSING_COMPLETED",
            status="success",
            details={"status": "completed", "claims_count": len(claims_response_list)}
        )
        db.commit()

        return {
            "status": "completed",
            "request_id": v_request.id,
            "article": article_dict,
            "claims_count": len(claims_response_list),
            "claims": claims_response_list,
            "sources_count": len(all_sources),
            "sources": all_sources,
            "submitted_source": submitted_source_dict,
            "independent_sources": independent_sources_list,
            "queries": queries_schemas,
            "search_provider": active_provider or "duckduckgo",
            "evidence_count": len(evidence_schemas),
            "evidence": evidence_schemas,
            "comparisons_count": len(comparison_schemas),
            "source_comparisons": comparison_schemas,
            "verdict": request_verdict_dict,
            "claim_verdicts": claim_verdict_dicts,
            "message": summary_msg
        }

    def _get_or_create_submitted_source(self, db: Session, extracted: ExtractedArticle) -> Source:
        """
        Creates or updates the submitted article as a Source record,
        explicitly tagged with source_role='USER_SUBMITTED_ARTICLE'.
        """
        src = db.query(Source).filter(
            (Source.canonical_url == extracted.canonical_url) | (Source.url == extracted.original_url)
        ).first()

        if not src:
            src = Source(
                name=extracted.title[:255] if extracted.title else extracted.domain,
                domain=extracted.domain,
                url=extracted.original_url,
                canonical_url=extracted.canonical_url or extracted.original_url,
                title=extracted.title,
                snippet=(extracted.description or extracted.article_text[:300]),
                publisher=extracted.publisher,
                author=extracted.author,
                country="unknown",
                publication_date=extracted.published_at,
                query_used="USER_SUBMISSION",
                provider="direct_url",
                source_type="NEWS",
                source_role="USER_SUBMITTED_ARTICLE",
                retrieved_at=datetime.utcnow(),
                credibility_score=None,
                reliability_tier="unrated"
            )
            db.add(src)
            db.flush()
        else:
            # Ensure source_role is marked as USER_SUBMITTED_ARTICLE for this verification
            src.source_role = "USER_SUBMITTED_ARTICLE"
            if extracted.title and not src.title:
                src.title = extracted.title
            db.flush()

        return src
