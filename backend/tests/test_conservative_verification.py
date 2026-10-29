import pytest
from datetime import datetime, timezone
from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem,
    SourceComparisonItem
)
from app.verification.verdict.models import (
    VerdictType,
    EvidenceStrength,
    ConfidenceLevel
)
from app.verification.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.verification.verdict.rule_based import RuleBasedVerdictEngine
from app.verification.verdict.evaluator import EvidenceEvaluator


def make_item(
    id: int,
    claim_id: int,
    evidence_type: EvidenceType,
    domain: str,
    publisher: str,
    evidence_text: str,
    relevance: EvidenceRelevance = EvidenceRelevance.HIGH,
    url: str = None
) -> ExtractedEvidenceItem:
    return ExtractedEvidenceItem(
        id=id,
        claim_id=claim_id,
        source_id=id + 10,
        evidence_text=evidence_text,
        snippet=evidence_text,
        evidence_type=evidence_type,
        direction=evidence_type.value,
        relevance=relevance,
        relevance_score=0.9 if relevance == EvidenceRelevance.HIGH else 0.6,
        confidence_in_extraction=0.95,
        stance_confidence=0.9,
        source_location="snippet",
        extraction_method="rule_based",
        extracted_at=datetime.now(timezone.utc),
        url=url or f"https://{domain}/article-{id}",
        article_title="News Report",
        publisher=publisher,
        domain=domain,
        publish_date="2026-10-15",
        explanation=f"Testing {evidence_type.value}"
    )


def test_fake_news_keyword_overlap_not_supported():
    """
    Test: A fake claim discussing RBI currency notes matches topical keywords in news,
    but the news does NOT confirm the cancellation. Stance analyzer must NOT mark it SUPPORTING,
    and verdict engine must NOT mark it SUPPORTED.
    """
    analyzer = RuleBasedEvidenceAnalyzer()
    engine = RuleBasedVerdictEngine()

    claim = "RBI cancelled and banned all 500 rupee notes starting tomorrow."
    source_snippet = (
        "Reserve Bank of India officials held a press conference discussing digital currency "
        "and banknotes circulation in Mumbai."
    )

    ev_item = analyzer.analyze_evidence(
        claim_id=1,
        claim_text=claim,
        source_id=1,
        source_title="RBI Governor speaks on banknotes and liquidity",
        source_snippet=source_snippet,
        source_url="https://timesofindia.indiatimes.com/business/rbi-notes",
        source_domain="timesofindia.indiatimes.com",
        claim_entities=["RBI", "500 rupee notes"]
    )

    # Must be contextual, NOT supporting, because "banned" / "cancelled" predicate is absent
    assert ev_item.evidence_type != EvidenceType.SUPPORTING
    assert ev_item.evidence_type in (EvidenceType.CONTEXTUAL, EvidenceType.INSUFFICIENT)

    verdict_res = engine.determine_verdict(
        claim_id=1,
        claim_text=claim,
        evidence=[ev_item],
        comparisons=[]
    )

    # Must be UNVERIFIED or INSUFFICIENT, NEVER SUPPORTED
    assert verdict_res.verdict != VerdictType.SUPPORTED
    assert verdict_res.verdict in (VerdictType.UNVERIFIED, VerdictType.INSUFFICIENT_EVIDENCE)


def test_fact_check_debunk_yields_contradicted():
    """
    Test: When a fact-checker debunks a viral claim, it must be classified as CONTRADICTING
    and lead to a CONTRADICTED verdict.
    """
    analyzer = RuleBasedEvidenceAnalyzer()
    engine = RuleBasedVerdictEngine()

    claim = "Government declared a 3-day nationwide holiday due to solar storm."
    source_snippet = (
        "Fact Check: Viral claim claiming a 3-day nationwide holiday due to solar storm is fake and debunked."
    )

    ev_item = analyzer.analyze_evidence(
        claim_id=2,
        claim_text=claim,
        source_id=2,
        source_title="Fact Check: Solar storm holiday claim is false",
        source_snippet=source_snippet,
        source_url="https://altnews.in/fact-check-solar-storm",
        source_domain="altnews.in",
        claim_entities=["Government"]
    )

    assert ev_item.evidence_type == EvidenceType.CONTRADICTING

    verdict_res = engine.determine_verdict(
        claim_id=2,
        claim_text=claim,
        evidence=[ev_item],
        comparisons=[]
    )

    assert verdict_res.verdict == VerdictType.CONTRADICTED


def test_rumor_blog_single_source_cannot_support():
    """
    Test: An unverified blog or forum repeating a rumor cannot give a SUPPORTED verdict.
    Must abstain to UNVERIFIED.
    """
    engine = RuleBasedVerdictEngine()
    ev = make_item(
        id=1,
        claim_id=3,
        evidence_type=EvidenceType.SUPPORTING,
        domain="viralnewsblog.wordpress.com",
        publisher="Viral Blog",
        evidence_text="Claim circulating online that new tech was launched.",
        relevance=EvidenceRelevance.HIGH
    )

    verdict_res = engine.determine_verdict(
        claim_id=3,
        claim_text="New tech was launched in stealth mode.",
        evidence=[ev],
        comparisons=[]
    )

    assert verdict_res.verdict == VerdictType.UNVERIFIED
    assert "lacks sufficient independent cross-corroboration" in verdict_res.explanation


def test_syndicated_articles_do_not_falsely_multiply_credibility():
    """
    Test: If 2 articles are syndicated copies of the same wire, they must not count
    as 2 independent investigations.
    """
    engine = RuleBasedVerdictEngine()
    ev1 = make_item(
        id=1, claim_id=4, evidence_type=EvidenceType.SUPPORTING,
        domain="sitea.com", publisher="Site A",
        evidence_text="New policy announced yesterday.",
        relevance=EvidenceRelevance.MEDIUM
    )
    ev2 = make_item(
        id=2, claim_id=4, evidence_type=EvidenceType.SUPPORTING,
        domain="siteb.com", publisher="Site B",
        evidence_text="New policy announced yesterday.",
        relevance=EvidenceRelevance.MEDIUM
    )

    synd_comp = SourceComparisonItem(
        claim_id=4, source_id_a=11, source_id_b=12,
        comparison_type="PAIRWISE",
        source_relationship=SourceRelationship.POSSIBLY_SYNDICATED,
        evidence_consistency=EvidenceConsistency.CONSISTENT_EVIDENCE
    )

    verdict_res = engine.determine_verdict(
        claim_id=4,
        claim_text="New policy announced yesterday.",
        evidence=[ev1, ev2],
        comparisons=[synd_comp]
    )

    # Because they are syndicated and from non-primary sources, it must not be supported
    assert verdict_res.verdict == VerdictType.UNVERIFIED


def test_primary_official_source_supports():
    """
    Test: An official primary source (isro.gov.in) with high relevance directly confirms the claim.
    """
    engine = RuleBasedVerdictEngine()
    ev = make_item(
        id=1, claim_id=5, evidence_type=EvidenceType.SUPPORTING,
        domain="isro.gov.in", publisher="ISRO",
        evidence_text="ISRO confirmed the successful mission deployment of the weather satellite.",
        relevance=EvidenceRelevance.HIGH,
        url="https://isro.gov.in/mission-success"
    )

    verdict_res = engine.determine_verdict(
        claim_id=5,
        claim_text="ISRO deployed the weather satellite successfully.",
        evidence=[ev],
        comparisons=[]
    )

    assert verdict_res.verdict == VerdictType.SUPPORTED
    assert "directly supports" in verdict_res.explanation


def test_credible_conflicting_sources_yield_mixed():
    """
    Test: When credible news sources report contradictory findings on a topic,
    verdict must be MIXED.
    """
    engine = RuleBasedVerdictEngine()
    ev_supp = make_item(
        id=1, claim_id=6, evidence_type=EvidenceType.SUPPORTING,
        domain="thehindu.com", publisher="The Hindu",
        evidence_text="Officials reported the bridge completed on schedule.",
        relevance=EvidenceRelevance.HIGH
    )
    ev_contra = make_item(
        id=2, claim_id=6, evidence_type=EvidenceType.CONTRADICTING,
        domain="indianexpress.com", publisher="The Indian Express",
        evidence_text="Engineers inspect incomplete bridge, construction remains stalled.",
        relevance=EvidenceRelevance.HIGH
    )

    verdict_res = engine.determine_verdict(
        claim_id=6,
        claim_text="The bridge construction was fully completed on schedule.",
        evidence=[ev_supp, ev_contra],
        comparisons=[]
    )

    assert verdict_res.verdict == VerdictType.MIXED
    assert "Conflicting reporting" in verdict_res.explanation
