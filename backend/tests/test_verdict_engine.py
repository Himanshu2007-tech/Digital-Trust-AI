import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.models.verification_request import VerificationRequest
from app.models.verification_result import VerificationResult

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
    ConfidenceLevel,
    ClaimVerdictItem,
    RequestVerdictResult
)
from app.verification.verdict.evaluator import EvidenceEvaluator
from app.verification.verdict.rule_based import RuleBasedVerdictEngine
from app.verification.verdict.llm import LLMVerdictEngine
from app.verification.verdict.hybrid import HybridVerdictEngine
from app.verification.verdict.service import VerdictService
from app.main import app

client = TestClient(app)


# Helper to build mock ExtractedEvidenceItem
def make_evidence_item(
    id: int,
    claim_id: int,
    evidence_type: EvidenceType,
    relevance: EvidenceRelevance = EvidenceRelevance.HIGH,
    evidence_text: str = "Sample factual passage from reputable reporting.",
    publisher: str = "Reuters",
    domain: str = "reuters.com",
    url: str = "https://reuters.com/article/1",
    publish_date: str = "June 2026",
    confidence_in_extraction: float = 0.95,
    source_type: str = "RELIABLE_NEWS"
) -> ExtractedEvidenceItem:
    return ExtractedEvidenceItem(
        id=id,
        claim_id=claim_id,
        source_id=id + 100,
        evidence_text=evidence_text,
        snippet=evidence_text,
        evidence_type=evidence_type,
        direction=evidence_type.value,
        relevance=relevance,
        relevance_score=0.9 if relevance == EvidenceRelevance.HIGH else 0.6,
        confidence_in_extraction=confidence_in_extraction,
        stance_confidence=0.9,
        source_location="snippet",
        extraction_method="rule_based",
        extracted_at=datetime.now(timezone.utc),
        url=url,
        article_title="Official Report",
        publisher=publisher,
        domain=domain,
        publish_date=publish_date,
        explanation=f"Corresponds to {evidence_type.value}"
    )


# ==============================================================================
# 1. VERDICT CLASSIFICATION UNIT TESTS
# ==============================================================================

def test_verdict_supported():
    """Scenario 1: Corroborating evidence from reputable sources yields SUPPORTED."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(
        id=1, claim_id=1, evidence_type=EvidenceType.SUPPORTING,
        evidence_text="ISRO successfully launched 3 communication satellites into geostationary orbit in August 2025.",
        domain="isro.gov.in", publisher="ISRO", source_type="PRIMARY"
    )
    ev2 = make_evidence_item(
        id=2, claim_id=1, evidence_type=EvidenceType.SUPPORTING,
        evidence_text="India placed 3 satellites in orbit, confirmed by space tracking officials.",
        domain="thehindu.com", publisher="The Hindu", source_type="RELIABLE_NEWS"
    )
    comp = SourceComparisonItem(
        claim_id=1, source_id_a=101, source_id_b=102,
        source_relationship=SourceRelationship.INDEPENDENT,
        consistency_type=EvidenceConsistency.CONSISTENT_EVIDENCE
    )

    verdict_item = engine.determine_verdict(
        claim_id=1,
        claim_text="ISRO launched 3 communication satellites in August 2025.",
        evidence=[ev1, ev2],
        comparisons=[comp]
    )

    assert verdict_item.verdict == VerdictType.SUPPORTED
    assert verdict_item.confidence >= 0.70
    assert 1 in verdict_item.supporting_evidence_ids
    assert 2 in verdict_item.supporting_evidence_ids
    assert len(verdict_item.contradicting_evidence_ids) == 0


def test_verdict_contradicted():
    """Scenario 2: Direct refutation from authoritative sources yields CONTRADICTED."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(
        id=1, claim_id=2, evidence_type=EvidenceType.CONTRADICTING,
        evidence_text="Finance Ministry officially denied and rejected reports of a $5 billion agricultural subsidy.",
        domain="pib.gov.in", publisher="PIB India", source_type="OFFICIAL"
    )

    verdict_item = engine.determine_verdict(
        claim_id=2,
        claim_text="Finance Ministry approved a $5 billion agricultural subsidy.",
        evidence=[ev1],
        comparisons=[]
    )

    assert verdict_item.verdict == VerdictType.CONTRADICTED
    assert 1 in verdict_item.contradicting_evidence_ids
    assert "contradict" in verdict_item.explanation.lower() or "refut" in verdict_item.explanation.lower()


def test_verdict_numerical_mismatch():
    """Scenario 3: Numerical mismatch (7% vs 6.5%) is identified as contradiction/misleading."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(
        id=1, claim_id=3, evidence_type=EvidenceType.CONTRADICTING,
        evidence_text="RBI maintained the repo rate unchanged at 6.50 percent in its June policy meeting.",
        domain="rbi.org.in", publisher="Reserve Bank of India", source_type="PRIMARY"
    )

    verdict_item = engine.determine_verdict(
        claim_id=3,
        claim_text="RBI increased the repo rate to 7% in June 2026.",
        evidence=[ev1],
        comparisons=[],
        claim_numbers=["7%"]
    )

    assert verdict_item.verdict in (VerdictType.CONTRADICTED, VerdictType.MISLEADING)
    assert 1 in verdict_item.contradicting_evidence_ids
    assert "contradict" in verdict_item.explanation.lower() or "mismatch" in verdict_item.explanation.lower()


def test_verdict_date_temporal_mismatch():
    """Scenario 4: Date mismatch or future timeline conflict is flagged."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(
        id=1, claim_id=4, evidence_type=EvidenceType.CONTRADICTING,
        evidence_text="The committee scheduled the policy implementation for December 2028, not March 2024.",
        domain="reuters.com", publisher="Reuters", publish_date="2024-05-01"
    )

    verdict_item = engine.determine_verdict(
        claim_id=4,
        claim_text="New environmental rules took effect in March 2024.",
        evidence=[ev1],
        comparisons=[],
        claim_dates=["March 2024"]
    )

    assert verdict_item.verdict in (VerdictType.CONTRADICTED, VerdictType.MISLEADING)
    assert 1 in verdict_item.contradicting_evidence_ids


def test_verdict_misleading_policy_proposal():
    """Scenario 5: Unfinished draft proposal presented as finalized law is MISLEADING."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(
        id=1, claim_id=5, evidence_type=EvidenceType.CONTEXTUAL,
        evidence_text="The committee only circulated an internal discussion draft proposal; no law has been enacted or approved.",
        domain="thehindu.com", publisher="The Hindu"
    )

    verdict_item = engine.determine_verdict(
        claim_id=5,
        claim_text="Government enacted a nationwide ban on gasoline scooters.",
        evidence=[ev1],
        comparisons=[]
    )

    assert verdict_item.verdict == VerdictType.MISLEADING
    assert 1 in verdict_item.contextual_evidence_ids


def test_verdict_quote_fabrication():
    """Scenario 6: Distorted/fabricated quote with evidence refuting attribution."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(
        id=1, claim_id=6, evidence_type=EvidenceType.CONTRADICTING,
        evidence_text="WHO spokesperson clarified Dr. Sharma never made statements regarding regional vaccine distribution.",
        domain="who.int", publisher="World Health Organization", source_type="OFFICIAL"
    )

    verdict_item = engine.determine_verdict(
        claim_id=6,
        claim_text="Dr. Sharma claimed regional vaccine distribution remains inadequate.",
        evidence=[ev1],
        comparisons=[]
    )

    assert verdict_item.verdict == VerdictType.CONTRADICTED
    assert 1 in verdict_item.contradicting_evidence_ids


def test_verdict_unverified():
    """Scenario 7: Tangential contextual background without direct proof yields UNVERIFIED."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(
        id=1, claim_id=7, evidence_type=EvidenceType.CONTEXTUAL,
        evidence_text="Foreign trade delegations regularly visit trade missions across the capital throughout the quarter.",
        domain="generalnews.com", publisher="General News"
    )

    verdict_item = engine.determine_verdict(
        claim_id=7,
        claim_text="Trade delegation finalized a clandestine defense deal during yesterday's meeting.",
        evidence=[ev1],
        comparisons=[]
    )

    assert verdict_item.verdict == VerdictType.UNVERIFIED
    assert verdict_item.confidence <= 0.40
    assert 1 in verdict_item.contextual_evidence_ids


def test_verdict_insufficient_evidence():
    """Scenario 8: Zero evidence items yields INSUFFICIENT_EVIDENCE with baseline confidence."""
    engine = RuleBasedVerdictEngine()

    verdict_item = engine.determine_verdict(
        claim_id=8,
        claim_text="Completely unknown local statement without any media coverage.",
        evidence=[],
        comparisons=[]
    )

    assert verdict_item.verdict == VerdictType.INSUFFICIENT_EVIDENCE
    assert verdict_item.confidence == 0.15
    assert len(verdict_item.limitations) > 0


# ==============================================================================
# 2. METHODOLOGY & BOUNDARY ENFORCEMENT TESTS
# ==============================================================================

def test_no_binary_true_false():
    """Scenario 9: Verdicts must strictly be from the 6 valid classifications, never binary True/False."""
    engine = RuleBasedVerdictEngine()
    valid_classifications = {v.value for v in VerdictType}

    assert "TRUE" not in valid_classifications
    assert "FALSE" not in valid_classifications

    ev = make_evidence_item(id=1, claim_id=9, evidence_type=EvidenceType.SUPPORTING)
    res = engine.determine_verdict(claim_id=9, claim_text="Sample assertion", evidence=[ev], comparisons=[])

    assert res.verdict.value in valid_classifications
    assert res.verdict.value not in ("TRUE", "FALSE")


def test_no_majority_voting():
    """Scenario 10: One authoritative primary/official source outweighs two low-quality blogs."""
    engine = RuleBasedVerdictEngine()
    # 1 high-quality official refutation
    official_refutation = make_evidence_item(
        id=1, claim_id=10, evidence_type=EvidenceType.CONTRADICTING,
        evidence_text="Ministry confirms the scheme is fraudulent and does not exist.",
        domain="pib.gov.in", publisher="Press Information Bureau", source_type="OFFICIAL"
    )
    # 2 low-credibility blog posts claiming it's true
    blog1 = make_evidence_item(
        id=2, claim_id=10, evidence_type=EvidenceType.SUPPORTING,
        evidence_text="Viral rumors claim new scheme gives money to all citizens.",
        domain="randomblog1.wordpress.com", publisher="Anonymous Blog", source_type="BLOG"
    )
    blog2 = make_evidence_item(
        id=3, claim_id=10, evidence_type=EvidenceType.SUPPORTING,
        evidence_text="Everyone is talking about the upcoming welfare distribution.",
        domain="randomblog2.blogspot.com", publisher="Social Blogger", source_type="BLOG"
    )

    verdict_item = engine.determine_verdict(
        claim_id=10,
        claim_text="Government scheme gives free cash to all citizens.",
        evidence=[official_refutation, blog1, blog2],
        comparisons=[]
    )

    # 1 official source contradicts, 2 blogs support -> Verdict MUST NOT be SUPPORTED
    assert verdict_item.verdict != VerdictType.SUPPORTED
    assert verdict_item.verdict in (VerdictType.CONTRADICTED, VerdictType.MISLEADING)


def test_anti_syndication_discount():
    """Scenario 11: Wire agency syndicated reproductions have capped independence score."""
    ev1 = make_evidence_item(id=1, claim_id=11, evidence_type=EvidenceType.SUPPORTING, domain="site1.com")
    ev2 = make_evidence_item(id=2, claim_id=11, evidence_type=EvidenceType.SUPPORTING, domain="site2.com")

    # Independent comparisons
    indep_comp = SourceComparisonItem(
        claim_id=11, source_id_a=101, source_id_b=102,
        source_relationship=SourceRelationship.INDEPENDENT,
        consistency_type=EvidenceConsistency.CONSISTENT_EVIDENCE
    )
    score_indep, _, comp_indep = EvidenceEvaluator.calculate_confidence_score(
        evidence=[ev1, ev2], comparisons=[indep_comp], verdict=VerdictType.SUPPORTED
    )

    # Syndicated comparisons
    synd_comp = SourceComparisonItem(
        claim_id=11, source_id_a=101, source_id_b=102,
        source_relationship=SourceRelationship.POSSIBLY_SYNDICATED,
        consistency_type=EvidenceConsistency.CONSISTENT_EVIDENCE
    )
    score_synd, _, comp_synd = EvidenceEvaluator.calculate_confidence_score(
        evidence=[ev1, ev2], comparisons=[synd_comp], verdict=VerdictType.SUPPORTED
    )

    # Syndicated sources must yield lower or capped independence score component
    assert comp_synd["independence"] <= 0.60
    assert comp_indep["independence"] >= comp_synd["independence"]
    assert score_indep >= score_synd


def test_confidence_formula_mathematics():
    """Scenario 12: Formula C = 0.25 S_direct + 0.25 S_quality + 0.20 S_indep + 0.20 S_consist + 0.10 S_temporal."""
    ev = make_evidence_item(id=1, claim_id=12, evidence_type=EvidenceType.SUPPORTING, domain="isro.gov.in")
    score, level, breakdown = EvidenceEvaluator.calculate_confidence_score(
        evidence=[ev], comparisons=[], verdict=VerdictType.SUPPORTED
    )

    assert 0.0 <= score <= 1.0
    expected = (
        0.25 * breakdown["directness"]
        + 0.25 * breakdown["source_quality"]
        + 0.20 * breakdown["independence"]
        + 0.20 * breakdown["consistency"]
        + 0.10 * breakdown["temporal"]
    )
    assert pytest.approx(score, 0.01) == expected


def test_traceable_evidence_ids():
    """Scenario 13: All cited evidence IDs strictly match input evidence IDs."""
    engine = RuleBasedVerdictEngine()
    ev1 = make_evidence_item(id=42, claim_id=13, evidence_type=EvidenceType.SUPPORTING)
    ev2 = make_evidence_item(id=99, claim_id=13, evidence_type=EvidenceType.CONTEXTUAL)

    res = engine.determine_verdict(
        claim_id=13,
        claim_text="Sample traceable assertion",
        evidence=[ev1, ev2],
        comparisons=[]
    )

    all_cited = res.supporting_evidence_ids + res.contradicting_evidence_ids + res.contextual_evidence_ids
    for cid in all_cited:
        assert cid in (42, 99)


def test_limitations_detection():
    """Scenario 14: Dynamic limitation generation flags lack of official documentation."""
    ev = make_evidence_item(
        id=1, claim_id=14, evidence_type=EvidenceType.SUPPORTING,
        domain="thehindu.com", publisher="The Hindu", source_type="RELIABLE_NEWS"
    )

    limitations = EvidenceEvaluator.detect_limitations(evidence=[ev], comparisons=[])
    assert len(limitations) > 0
    # Should detect only 1 source was examined
    assert any("single source" in l.lower() or "secondary" in l.lower() for l in limitations)


# ==============================================================================
# 3. MULTI-CLAIM & ENGINE INTEGRATION TESTS
# ==============================================================================

def test_multi_claim_request_all_supported():
    """Scenario 15: VerificationRequest with all supported claims yields overall SUPPORTED."""
    db = SessionLocal()
    try:
        req = VerificationRequest(request_type="text", content="Claim 1 and Claim 2.", status="processing")
        db.add(req)
        db.flush()

        c1 = Claim(request_id=req.id, claim_text="Claim 1", status="extracted")
        c2 = Claim(request_id=req.id, claim_text="Claim 2", status="extracted")
        db.add_all([c1, c2])
        db.flush()

        # Add supporting evidence for both
        ev1 = Evidence(
            claim_id=c1.id, evidence_type="SUPPORTING", evidence_text="Corroboration 1",
            snippet="Corroboration 1", url="https://isro.gov.in/1", relevance="HIGH",
            relevance_score=0.9, confidence_in_extraction=0.95
        )
        ev2 = Evidence(
            claim_id=c2.id, evidence_type="SUPPORTING", evidence_text="Corroboration 2",
            snippet="Corroboration 2", url="https://isro.gov.in/2", relevance="HIGH",
            relevance_score=0.9, confidence_in_extraction=0.95
        )
        db.add_all([ev1, ev2])
        db.commit()

        service = VerdictService(engine=RuleBasedVerdictEngine())
        final_res = service.finalize_request(request_id=req.id, db=db, reevaluate_claims=True)

        assert final_res.overall_verdict == VerdictType.SUPPORTED
        assert final_res.supported_count == 2
        assert final_res.claims_count == 2
        assert final_res.overall_confidence >= 0.70
    finally:
        db.close()


def test_multi_claim_request_mixed():
    """Scenario 16: VerificationRequest with 1 supported and 1 contradicted claim yields MIXED."""
    db = SessionLocal()
    try:
        req = VerificationRequest(request_type="text", content="True fact and false fact.", status="processing")
        db.add(req)
        db.flush()

        c1 = Claim(request_id=req.id, claim_text="True fact", status="extracted")
        c2 = Claim(request_id=req.id, claim_text="False fact", status="extracted")
        db.add_all([c1, c2])
        db.flush()

        # Evidence: 1 supporting, 1 contradicting
        ev1 = Evidence(
            claim_id=c1.id, evidence_type="SUPPORTING", evidence_text="True fact confirmed",
            snippet="True fact confirmed", url="https://reuters.com/1", relevance="HIGH",
            relevance_score=0.9, confidence_in_extraction=0.95
        )
        ev2 = Evidence(
            claim_id=c2.id, evidence_type="CONTRADICTING", evidence_text="False fact refuted",
            snippet="False fact refuted", url="https://pib.gov.in/2", relevance="HIGH",
            relevance_score=0.9, confidence_in_extraction=0.95
        )
        db.add_all([ev1, ev2])
        db.commit()

        service = VerdictService(engine=RuleBasedVerdictEngine())
        final_res = service.finalize_request(request_id=req.id, db=db, reevaluate_claims=True)

        assert final_res.overall_verdict == VerdictType.MIXED
        assert final_res.supported_count == 1
        assert final_res.contradicted_count == 1
        assert "MIXED" in final_res.summary
    finally:
        db.close()


def test_rule_based_engine_fallback():
    """Scenario 17: HybridVerdictEngine gracefully falls back to RuleBased on LLM failure."""
    mock_llm = MagicMock(spec=LLMVerdictEngine)
    mock_llm.is_configured.return_value = True
    mock_llm.determine_verdict.side_effect = RuntimeError("LLM rate limit reached")

    hybrid_engine = HybridVerdictEngine(
        rule_engine=RuleBasedVerdictEngine(),
        llm_engine=mock_llm
    )

    ev = make_evidence_item(id=1, claim_id=17, evidence_type=EvidenceType.SUPPORTING)
    res = hybrid_engine.determine_verdict(
        claim_id=17,
        claim_text="Sample fallback assertion",
        evidence=[ev],
        comparisons=[]
    )

    assert res.verdict == VerdictType.SUPPORTED
    assert res.confidence > 0.0


# ==============================================================================
# 4. REST API ENDPOINT TESTS
# ==============================================================================

def test_verdict_api_single_claim():
    """Scenario 18: POST /api/verify/claims/{claim_id} and GET /api/verify/claims/{claim_id}/verdict."""
    db = SessionLocal()
    try:
        req = VerificationRequest(request_type="text", content="Test single claim API.", status="processing")
        db.add(req)
        db.flush()

        claim = Claim(request_id=req.id, claim_text="ISRO satellites deployed in orbit.", status="extracted")
        db.add(claim)
        db.flush()

        ev = Evidence(
            claim_id=claim.id, evidence_type="SUPPORTING", evidence_text="ISRO confirmed satellite launch.",
            snippet="ISRO confirmed satellite launch.", url="https://isro.gov.in/launch", relevance="HIGH",
            relevance_score=0.9, confidence_in_extraction=0.95
        )
        db.add(ev)
        db.commit()

        # 1. POST evaluate claim
        res_post = client.post(f"/api/verify/claims/{claim.id}")
        assert res_post.status_code == 200
        data_post = res_post.json()
        assert data_post["claim_id"] == claim.id
        assert data_post["verdict"] == "SUPPORTED"
        assert data_post["confidence"] >= 0.70

        # 2. GET retrieved stored verdict
        res_get = client.get(f"/api/verify/claims/{claim.id}/verdict")
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert data_get["claim_id"] == claim.id
        assert data_get["verdict"] == "SUPPORTED"
        assert data_get["confidence"] == data_post["confidence"]
    finally:
        db.close()


def test_verdict_api_finalize_request():
    """Scenario 19: POST /api/verify/requests/{request_id}/finalize and GET /api/verify/requests/{request_id}/verdict."""
    db = SessionLocal()
    try:
        req = VerificationRequest(request_type="text", content="Multi-claim API test.", status="processing")
        db.add(req)
        db.flush()

        c1 = Claim(request_id=req.id, claim_text="Claim A", status="extracted")
        db.add(c1)
        db.flush()

        ev = Evidence(
            claim_id=c1.id, evidence_type="CONTRADICTING", evidence_text="Claim A refutation.",
            snippet="Claim A refutation.", url="https://reuters.com/refute", relevance="HIGH",
            relevance_score=0.9, confidence_in_extraction=0.95
        )
        db.add(ev)
        db.commit()

        # POST finalize
        res_post = client.post(f"/api/verify/requests/{req.id}/finalize", json={"reevaluate_claims": True})
        assert res_post.status_code == 200
        data_post = res_post.json()
        assert data_post["request_id"] == req.id
        assert data_post["overall_verdict"] == "CONTRADICTED"
        assert data_post["contradicted_count"] == 1

        # GET stored request verdict
        res_get = client.get(f"/api/verify/requests/{req.id}/verdict")
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert data_get["request_id"] == req.id
        assert data_get["overall_verdict"] == "CONTRADICTED"
    finally:
        db.close()


def test_end_to_end_verify_text_verdict():
    """Scenario 20: Full POST /api/verify/text pipeline carries through Part 6 verdict synthesis."""
    payload = {
        "text": "The government approved a new space budget. However, rumors of free energy are false.",
        "perform_search": False,  # Keep test fast without hitting external search engine
        "extract_evidence": False,
        "finalize_verdicts": True
    }

    res = client.post("/api/verify/text", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "completed"
    assert data["claims_count"] >= 1
    assert "verdict" in data
    assert data["verdict"] is not None
    assert "overall_verdict" in data["verdict"]
    assert "overall_confidence" in data["verdict"]
    assert "claim_verdicts" in data
