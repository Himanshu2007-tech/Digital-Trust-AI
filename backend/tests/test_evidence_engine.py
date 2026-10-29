import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.models.verification_request import VerificationRequest

from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem
)
from app.verification.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.verification.evidence.llm import LLMEvidenceAnalyzer
from app.verification.evidence.hybrid import HybridEvidenceAnalyzer
from app.verification.evidence.comparator import SourceComparator
from app.verification.evidence.service import EvidenceAnalysisService


# ==========================================
# 1. Stance Extraction Unit Tests
# ==========================================

def test_supporting_evidence_extraction():
    analyzer = RuleBasedEvidenceAnalyzer()
    claim_text = "ISRO successfully placed communication satellites in geostationary orbit in August 2025."
    source_title = "ISRO launches communications satellites into orbit"
    source_snippet = "In August 2025, ISRO successfully placed communication satellites into geostationary orbit from Sriharikota."

    item = analyzer.analyze_evidence(
        claim_id=1,
        claim_text=claim_text,
        source_id=10,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://isro.gov.in/press/launch-2025",
        source_domain="isro.gov.in",
        claim_entities=["ISRO"],
        claim_dates=["August 2025"]
    )

    assert item.evidence_type == EvidenceType.SUPPORTING
    assert item.direction == "SUPPORTING"
    assert item.relevance in (EvidenceRelevance.HIGH, EvidenceRelevance.MEDIUM)
    assert "August 2025" in item.evidence_text
    assert "ISRO" in item.evidence_text
    # Traceability: Quote is verbatim from the source snippet
    assert item.evidence_text in source_snippet


def test_contradicting_evidence_extraction():
    analyzer = RuleBasedEvidenceAnalyzer()
    claim_text = "Government approved the proposal for new airline subsidies."
    source_title = "Civil Aviation Ministry updates"
    source_snippet = "The Government rejected and did not approve the proposal for new airline subsidies during yesterday's meeting."

    item = analyzer.analyze_evidence(
        claim_id=2,
        claim_text=claim_text,
        source_id=11,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://reuters.com/business/airline-subsidies",
        claim_entities=["Government"]
    )

    assert item.evidence_type == EvidenceType.CONTRADICTING
    assert item.direction == "CONTRADICTING"
    assert "CONTRADICTING" in item.direction


def test_contextual_evidence_extraction():
    analyzer = RuleBasedEvidenceAnalyzer()
    claim_text = "Government approved the new technology policy."
    source_title = "Technology forum discusses policy"
    source_snippet = "Officials considered and discussed the new technology policy draft, with final decisions expected next year."

    item = analyzer.analyze_evidence(
        claim_id=3,
        claim_text=claim_text,
        source_id=12,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://bbc.com/news/tech-policy",
        claim_entities=["Government"]
    )

    assert item.evidence_type == EvidenceType.CONTEXTUAL
    assert item.direction == "CONTEXTUAL"


def test_insufficient_evidence_extraction():
    analyzer = RuleBasedEvidenceAnalyzer()
    claim_text = "RBI increased repo rate to 7% in June 2026."
    source_title = "Weather report for Mumbai"
    source_snippet = "Heavy monsoon rainfall is expected across coastal Maharashtra throughout the week."

    item = analyzer.analyze_evidence(
        claim_id=4,
        claim_text=claim_text,
        source_id=13,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://weather.com/mumbai",
        claim_entities=["RBI"]
    )

    assert item.evidence_type == EvidenceType.INSUFFICIENT
    assert item.relevance == EvidenceRelevance.LOW


# ==========================================
# 2. Numerical, Temporal & Negation Tests
# ==========================================

def test_numerical_comparison_contradiction():
    analyzer = RuleBasedEvidenceAnalyzer()
    # Claim asserts ₹500 crore, but source specifies ₹300 crore
    claim_text = "Budget allocation was ₹500 crore for regional transport."
    source_title = "Ministry releases budget breakdown"
    source_snippet = "The actual budget allocation was ₹300 crore for regional transport infrastructure."

    item = analyzer.analyze_evidence(
        claim_id=5,
        claim_text=claim_text,
        source_id=14,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://pib.gov.in/release/budget",
        claim_numbers=["₹500 crore"]
    )

    assert item.evidence_type == EvidenceType.CONTRADICTING
    assert "₹300 crore" in item.evidence_text
    assert "Numerical conflict" in (item.explanation or "")


def test_numerical_comparison_match():
    analyzer = RuleBasedEvidenceAnalyzer()
    claim_text = "WHO reported global vaccine coverage reached 84% in 2024."
    source_title = "WHO annual immunization report"
    source_snippet = "According to WHO records, global vaccine coverage reached 84% in 2024 across 194 countries."

    item = analyzer.analyze_evidence(
        claim_id=6,
        claim_text=claim_text,
        source_id=15,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://who.int/reports/vaccine-2024",
        claim_entities=["WHO"],
        claim_numbers=["84%"],
        claim_dates=["2024"]
    )

    assert item.evidence_type == EvidenceType.SUPPORTING
    assert "84%" in item.evidence_text


def test_date_comparison_contradiction():
    analyzer = RuleBasedEvidenceAnalyzer()
    claim_text = "The treaty summit occurred in March 2026."
    source_title = "Treaty summit concludes"
    source_snippet = "The international treaty summit occurred in July 2025 with delegations from forty states."

    item = analyzer.analyze_evidence(
        claim_id=7,
        claim_text=claim_text,
        source_id=16,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://apnews.com/treaty-summit",
        claim_dates=["March 2026"]
    )

    assert item.evidence_type == EvidenceType.CONTRADICTING
    assert "Temporal conflict" in (item.explanation or "")


def test_negation_stability_contradiction():
    analyzer = RuleBasedEvidenceAnalyzer()
    # Claim says "increased", source says "kept unchanged" or "maintained at 6.5%"
    claim_text = "RBI increased the repo rate to 7% in June 2026."
    source_title = "Monetary Policy Committee announcement"
    source_snippet = "The RBI kept the repo rate unchanged at 6.5% during its Monetary Policy review in June 2026."

    item = analyzer.analyze_evidence(
        claim_id=8,
        claim_text=claim_text,
        source_id=17,
        source_title=source_title,
        source_snippet=source_snippet,
        source_url="https://rbi.org.in/mpc-2026",
        claim_entities=["RBI"],
        claim_numbers=["7%"],
        claim_dates=["June 2026"]
    )

    assert item.evidence_type == EvidenceType.CONTRADICTING
    assert "unchanged" in item.evidence_text.lower() or "6.5%" in item.evidence_text


# ==========================================
# 3. Source Comparison & Independence Tests
# ==========================================

def test_duplicate_source_detection():
    comparator = SourceComparator()
    ev1 = ExtractedEvidenceItem(
        claim_id=9,
        source_id=20,
        evidence_text="RBI maintained repo rate at 6.5%.",
        snippet="RBI maintained repo rate at 6.5%.",
        evidence_type=EvidenceType.SUPPORTING,
        direction="SUPPORTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://reuters.com/business/rbi-rate",
        article_title="RBI rate steady",
        domain="reuters.com",
        publisher="Reuters"
    )
    ev2 = ExtractedEvidenceItem(
        claim_id=9,
        source_id=21,
        evidence_text="RBI maintained repo rate at 6.5%.",
        snippet="RBI maintained repo rate at 6.5%.",
        evidence_type=EvidenceType.SUPPORTING,
        direction="SUPPORTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://reuters.com/business/rbi-rate",
        article_title="RBI rate steady",
        domain="reuters.com",
        publisher="Reuters"
    )

    comparisons = comparator.compare_sources_for_claim(claim_id=9, evidence_items=[ev1, ev2])
    pairwise = [c for c in comparisons if c.comparison_type == "PAIRWISE"]
    assert len(pairwise) == 1
    assert pairwise[0].source_relationship == SourceRelationship.DUPLICATE


def test_syndicated_source_detection():
    comparator = SourceComparator()
    ev1 = ExtractedEvidenceItem(
        claim_id=10,
        source_id=22,
        evidence_text="ISRO launched communications satellite into orbit today.",
        snippet="ISRO launched communications satellite into orbit today.",
        evidence_type=EvidenceType.SUPPORTING,
        direction="SUPPORTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://newsportal-a.com/isro-launch",
        article_title="ISRO launches satellite",
        domain="newsportal-a.com",
        publisher="Press Trust of India (PTI)"
    )
    ev2 = ExtractedEvidenceItem(
        claim_id=10,
        source_id=23,
        evidence_text="ISRO launched communications satellite into orbit today.",
        snippet="ISRO launched communications satellite into orbit today.",
        evidence_type=EvidenceType.SUPPORTING,
        direction="SUPPORTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://newsportal-b.com/isro-launch",
        article_title="ISRO launches satellite",
        domain="newsportal-b.com",
        publisher="PTI Wire Service"
    )

    comparisons = comparator.compare_sources_for_claim(claim_id=10, evidence_items=[ev1, ev2])
    pairwise = [c for c in comparisons if c.comparison_type == "PAIRWISE"]
    assert len(pairwise) == 1
    assert pairwise[0].source_relationship == SourceRelationship.POSSIBLY_SYNDICATED


def test_conflicting_sources_comparison():
    comparator = SourceComparator()
    ev1 = ExtractedEvidenceItem(
        claim_id=11,
        source_id=24,
        evidence_text="Source reports event occurred on June 10.",
        snippet="Source reports event occurred on June 10.",
        evidence_type=EvidenceType.SUPPORTING,
        direction="SUPPORTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://source-a.org/event",
        domain="source-a.org",
        publisher="Independent News"
    )
    ev2 = ExtractedEvidenceItem(
        claim_id=11,
        source_id=25,
        evidence_text="Source reports contrary date of June 15.",
        snippet="Source reports contrary date of June 15.",
        evidence_type=EvidenceType.CONTRADICTING,
        direction="CONTRADICTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://source-b.com/event",
        domain="source-b.com",
        publisher="Daily Gazette"
    )

    comparisons = comparator.compare_sources_for_claim(claim_id=11, evidence_items=[ev1, ev2])
    pairwise = [c for c in comparisons if c.comparison_type == "PAIRWISE"]
    assert len(pairwise) == 1
    assert pairwise[0].evidence_consistency == EvidenceConsistency.CONFLICTING_INFORMATION

    group_syn = [c for c in comparisons if c.comparison_type == "GROUP_SYNTHESIS"][0]
    assert group_syn.consensus_verdict == "DISPUTED"
    assert group_syn.supporting_sources_count == 1
    assert group_syn.contradicting_sources_count == 1


# ==========================================
# 4. Hybrid & Fallback Tests
# ==========================================

def test_hybrid_fallback_on_llm_failure():
    mock_llm = MagicMock(spec=LLMEvidenceAnalyzer)
    mock_llm.is_configured.return_value = True
    mock_llm.analyze_evidence.side_effect = TimeoutError("LLM API call timed out")

    rule_analyzer = RuleBasedEvidenceAnalyzer()
    hybrid = HybridEvidenceAnalyzer(rule_analyzer=rule_analyzer, llm_analyzer=mock_llm)

    item = hybrid.analyze_evidence(
        claim_id=12,
        claim_text="Government announced farm subsidy.",
        source_id=26,
        source_title="Ministry announcements",
        source_snippet="Government announced a new farm subsidy program for cultivators today.",
        source_url="https://example.com/subsidy"
    )

    assert item.evidence_type == EvidenceType.SUPPORTING
    assert item.extraction_method == "rule_based"


# ==========================================
# 5. Database Persistence & API Tests
# ==========================================

def test_evidence_persistence_and_service(client: TestClient):
    db = SessionLocal()
    try:
        vr = VerificationRequest(request_type="text", content="Database test", status="extracted")
        db.add(vr)
        db.flush()

        claim = Claim(
            request_id=vr.id,
            claim_text="NASA congratulated the lunar team.",
            normalized_text="NASA congratulated the lunar team.",
            claim_type="PERSON/ORGANIZATION",
            verifiability="VERIFIABLE",
            importance="HIGH",
            original_sentence="NASA congratulated the lunar team."
        )
        db.add(claim)
        db.flush()

        src1 = Source(
            name="NASA News",
            domain="nasa.gov",
            url="https://nasa.gov/news/congrats",
            canonical_url="https://nasa.gov/news/congrats",
            title="NASA sends message to team",
            snippet="NASA congratulated the lunar exploration team on achieving precision landing.",
            publisher="NASA Press",
            source_type="PRIMARY"
        )
        db.add(src1)
        db.flush()

        # Associate source to claim
        claim.sources.append(src1)
        db.commit()

        # Run EvidenceAnalysisService
        service = EvidenceAnalysisService()
        ev_items, comp_items = service.analyze_evidence_for_claim(claim_id=claim.id, db=db)

        assert len(ev_items) == 1
        assert ev_items[0].evidence_type == EvidenceType.SUPPORTING
        assert ev_items[0].claim_id == claim.id

        # Verify DB persistence
        db_ev = db.query(Evidence).filter_by(claim_id=claim.id).first()
        assert db_ev is not None
        assert db_ev.evidence_type == "SUPPORTING"
        assert db_ev.source_id == src1.id
        assert "NASA" in db_ev.evidence_text

        # Verify API endpoint
        response = client.post("/api/verify/claims/evidence", json={"claim_id": claim.id})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["evidence_count"] == 1
        assert data["evidence"][0]["evidence_type"] == "SUPPORTING"
        # Verify NO final verdict or truth confidence is returned
        assert "final_verdict" not in data
        assert "is_true" not in data
    finally:
        db.close()


def test_bulk_request_evidence_api_endpoint(client: TestClient):
    db = SessionLocal()
    try:
        vr = VerificationRequest(request_type="text", content="Bulk request test", status="extracted")
        db.add(vr)
        db.flush()

        claim1 = Claim(
            request_id=vr.id,
            claim_text="WHO released vaccine guidance.",
            normalized_text="WHO released vaccine guidance.",
            claim_type="POLICY",
            verifiability="VERIFIABLE",
            importance="HIGH",
            original_sentence="WHO released vaccine guidance."
        )
        db.add(claim1)
        db.flush()

        src = Source(
            name="WHO Media",
            domain="who.int",
            url="https://who.int/vaccine-guidance",
            canonical_url="https://who.int/vaccine-guidance",
            title="WHO updates global vaccine guidance",
            snippet="WHO released new vaccine guidance today for member nations.",
            publisher="WHO",
            source_type="PRIMARY"
        )
        db.add(src)
        db.flush()
        claim1.sources.append(src)
        db.commit()

        req_id = vr.id
    finally:
        db.close()

    response = client.post(f"/api/verify/requests/{req_id}/evidence")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["request_id"] == req_id
    assert data["claims_analyzed"] == 1
    assert data["total_evidence"] >= 1


def test_consistent_sources_comparison():
    comparator = SourceComparator()
    ev1 = ExtractedEvidenceItem(
        claim_id=15,
        source_id=30,
        evidence_text="Repo rate remained 6.5%.",
        snippet="Repo rate remained 6.5%.",
        evidence_type=EvidenceType.SUPPORTING,
        direction="SUPPORTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://source-a.com/article",
        domain="source-a.com",
        publisher="Daily Financial"
    )
    ev2 = ExtractedEvidenceItem(
        claim_id=15,
        source_id=31,
        evidence_text="RBI maintained repo rate at 6.5%.",
        snippet="RBI maintained repo rate at 6.5%.",
        evidence_type=EvidenceType.SUPPORTING,
        direction="SUPPORTING",
        relevance=EvidenceRelevance.HIGH,
        relevance_score=0.9,
        confidence_in_extraction=1.0,
        stance_confidence=0.9,
        url="https://source-b.org/article",
        domain="source-b.org",
        publisher="Economic Gazette"
    )

    comparisons = comparator.compare_sources_for_claim(claim_id=15, evidence_items=[ev1, ev2])
    pairwise = [c for c in comparisons if c.comparison_type == "PAIRWISE"]
    assert len(pairwise) == 1
    assert pairwise[0].evidence_consistency == EvidenceConsistency.CONSISTENT_EVIDENCE
    # Crucial Part 5 rule: Must NOT convert consistent evidence into "Claim is TRUE"
    assert "claim is true" not in (pairwise[0].details or "").lower()
    assert "verdict" not in (pairwise[0].details or "").lower()


def test_atomic_claim_isolation():
    """
    Tests that two atomic claims decomposed from a compound sentence
    are evaluated independently without conflating evidence.
    """
    analyzer = RuleBasedEvidenceAnalyzer()
    # Atomic Claim 1: India launched Mission X in 2025.
    # Atomic Claim 2: ₹500 crore was allocated.
    claim1_text = "India launched Mission X in 2025."
    claim2_text = "Budget allocation was ₹500 crore."

    source_text = "India launched Mission X in 2025 with an estimated budget of ₹300 crore."

    # Analyze Claim 1 against source -> SUPPORTING
    ev1 = analyzer.analyze_evidence(
        claim_id=16,
        claim_text=claim1_text,
        source_id=32,
        source_title="Mission X launch",
        source_snippet=source_text,
        source_url="https://example.com/mission-x",
        claim_entities=["India", "Mission X"],
        claim_dates=["2025"]
    )
    assert ev1.evidence_type == EvidenceType.SUPPORTING

    # Analyze Claim 2 against same source -> CONTRADICTING (₹500 crore vs ₹300 crore)
    ev2 = analyzer.analyze_evidence(
        claim_id=17,
        claim_text=claim2_text,
        source_id=32,
        source_title="Mission X launch",
        source_snippet=source_text,
        source_url="https://example.com/mission-x",
        claim_numbers=["₹500 crore"]
    )
    assert ev2.evidence_type == EvidenceType.CONTRADICTING


def test_no_source_scenario():
    """Validates graceful handling when a claim has no discovered sources."""
    service = EvidenceAnalysisService()
    db = SessionLocal()
    try:
        vr = VerificationRequest(request_type="text", content="Empty test", status="extracted")
        db.add(vr)
        db.flush()

        claim = Claim(
            request_id=vr.id,
            claim_text="Unreferenced statement with no web sources.",
            normalized_text="Unreferenced statement with no web sources.",
            claim_type="FACTUAL",
            verifiability="VERIFIABLE",
            importance="LOW",
            original_sentence="Unreferenced statement with no web sources."
        )
        db.add(claim)
        db.commit()

        ev, comp = service.analyze_evidence_for_claim(claim_id=claim.id, db=db)
        assert ev == []
        assert comp == []
    finally:
        db.close()


def test_llm_json_parsing_resilience():
    """Validates parsing resilience when LLM wraps JSON in code fences."""
    llm = LLMEvidenceAnalyzer()
    raw_markdown_json = """```json
    {
      "evidence_text": "RBI kept interest rate at 6.5%",
      "evidence_type": "SUPPORTING",
      "relevance": "HIGH",
      "confidence_in_extraction": 0.95,
      "explanation": "Corroborates monetary policy rate."
    }
    ```"""
    parsed_item = llm._parse_evidence_json(
        raw_json_str=raw_markdown_json,
        claim_id=18,
        source_id=35,
        source_url="https://example.com/rbi",
        source_title="RBI update",
        source_snippet="RBI kept interest rate at 6.5%",
        source_domain="example.com",
        source_publisher="Example Press",
        publish_date="2026-06-01"
    )
    assert parsed_item.evidence_type == EvidenceType.SUPPORTING
    assert parsed_item.evidence_text == "RBI kept interest rate at 6.5%"
    assert parsed_item.relevance == EvidenceRelevance.HIGH
    assert parsed_item.confidence_in_extraction == 0.95

