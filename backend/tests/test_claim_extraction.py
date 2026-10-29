import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.exceptions import ValidationException
from app.verification.preprocessing import clean_text, segment_sentences
from app.verification.domain_models import ClaimType, Verifiability, Importance, ExtractedClaimItem
from app.verification.extractors.rule_based import RuleBasedClaimExtractor
from app.verification.extractors.llm import LLMClaimExtractor
from app.verification.extractors.hybrid import HybridClaimExtractor
from app.database.session import SessionLocal
from app.models.verification_request import VerificationRequest
from app.models.claim import Claim


# ==========================================
# 1. Preprocessing & Segmentation Tests
# ==========================================

def test_clean_text_basic():
    raw = "  RBI increased   the repo rate\tto 7%. \n  "
    orig, normalized = clean_text(raw)
    assert normalized == "RBI increased the repo rate to 7%."
    assert orig == "RBI increased   the repo rate\tto 7%."


def test_clean_text_too_short():
    with pytest.raises(ValidationException, match="Input text must contain at least 5 characters"):
        clean_text("abc")


def test_clean_text_too_long():
    oversized = "A" * 20005
    with pytest.raises(ValidationException, match="exceeds maximum allowed limit"):
        clean_text(oversized)


def test_sentence_segmentation_with_abbreviations():
    text = "Dr. Smith met with Prof. Jones in the U.S. at 5 p.m. He announced the new policy."
    sentences = segment_sentences(text)
    assert len(sentences) == 2
    assert sentences[0] == "Dr. Smith met with Prof. Jones in the U.S. at 5 p.m."
    assert sentences[1] == "He announced the new policy."


def test_sentence_segmentation_with_decimals_and_currencies():
    text = "Inflation fell by 3.5% in Q2. Total revenue reached $14.2 billion this year."
    sentences = segment_sentences(text)
    assert len(sentences) == 2
    assert "3.5%" in sentences[0]
    assert "$14.2 billion" in sentences[1]


# ==========================================
# 2. Rule-Based Extractor Unit Tests
# ==========================================

def test_single_atomic_claim_extraction():
    extractor = RuleBasedClaimExtractor()
    text = "The Reserve Bank of India raised interest rates in Mumbai."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 1
    assert "Reserve Bank of India" in claims[0].entities or "RBI" in claims[0].text
    assert claims[0].claim_type in (ClaimType.FACTUAL, ClaimType.PERSON_ORGANIZATION, ClaimType.LOCATION)
    assert claims[0].verifiability == Verifiability.VERIFIABLE


def test_compound_sentence_splitting_and():
    extractor = RuleBasedClaimExtractor()
    text = "India launched 3 communications satellites in 2024 and ISRO placed them into orbit."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 2
    texts = [c.text for c in claims]
    assert any("satellites" in t for t in texts)
    assert any("orbit" in t or "ISRO" in t for t in texts)


def test_compound_sentence_splitting_contrastive():
    extractor = RuleBasedClaimExtractor()
    text = "The Finance Ministry promised tax reductions, but the department introduced an emergency surcharge."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 2


def test_numerical_and_percentage_extraction():
    extractor = RuleBasedClaimExtractor()
    text = "Unemployment rose to 8.4% while the GDP grew by $250 million."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 1
    all_numbers = [num for c in claims for num in c.numbers]
    assert any("8.4%" in n or "8.4" in n for n in all_numbers)
    assert any("250 million" in n or "$250" in n for n in all_numbers)


def test_date_and_temporal_extraction():
    extractor = RuleBasedClaimExtractor()
    text = "The treaty was signed in August 2023 following preliminary meetings in July."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 1
    all_dates = [d for c in claims for d in c.dates]
    assert any("2023" in d or "August 2023" in d for d in all_dates)


def test_source_attribution_extraction():
    extractor = RuleBasedClaimExtractor()
    text = "According to WHO officials, global vaccine access improved significantly."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 1
    attributions = [att for c in claims for att in c.source_attributions]
    assert any("WHO" in att or "officials" in att for att in attributions)


def test_subjective_opinion_classification():
    extractor = RuleBasedClaimExtractor()
    text = "I believe this is the worst policy in modern history."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 1
    assert claims[0].verifiability in (Verifiability.SUBJECTIVE, Verifiability.UNVERIFIABLE)
    assert claims[0].claim_type == ClaimType.OPINION


# ==========================================
# 3. Hybrid Extractor & Fallback Tests
# ==========================================

def test_hybrid_fallback_on_llm_failure():
    mock_llm = MagicMock(spec=LLMClaimExtractor)
    mock_llm.is_configured.return_value = True
    mock_llm.extract_claims.side_effect = TimeoutError("OpenAI API timed out")

    rule_extractor = RuleBasedClaimExtractor()
    hybrid = HybridClaimExtractor(rule_extractor=rule_extractor, llm_extractor=mock_llm)

    text = "NASA launched a lunar mission in October 2024."
    claims = hybrid.extract_claims(text)

    # Should safely catch TimeoutError and return rule-based claims
    assert len(claims) >= 1
    assert "NASA" in claims[0].entities or "NASA" in claims[0].text
    assert claims[0].extraction_method == "rule_based"


def test_hybrid_uses_llm_when_configured():
    mock_llm = MagicMock(spec=LLMClaimExtractor)
    mock_llm.is_configured.return_value = True
    mock_llm.extract_claims.return_value = [
        ExtractedClaimItem(
            id="mock-1",
            text="RBI raised the repo rate to 7%",
            normalized_text="RBI raised the repo rate to 7%",
            claim_type=ClaimType.NUMERICAL,
            verifiability=Verifiability.VERIFIABLE,
            importance=Importance.HIGH,
            entities=["RBI"],
            numbers=["7%"],
            original_sentence="RBI raised the repo rate to 7%",
            extraction_method="llm"
        )
    ]

    rule_extractor = RuleBasedClaimExtractor()
    hybrid = HybridClaimExtractor(rule_extractor=rule_extractor, llm_extractor=mock_llm)

    claims = hybrid.extract_claims("RBI raised the repo rate to 7%")
    assert len(claims) == 1
    assert claims[0].extraction_method == "llm"
    assert claims[0].text == "RBI raised the repo rate to 7%"


# ==========================================
# 4. End-to-End API & Database Persistence
# ==========================================

def test_api_verify_text_endpoint_success(client: TestClient):
    payload = {
        "text": "RBI increased the repo rate to 7% in June 2026. The decision caused inflation to fall sharply. The Finance Ministry announced a new subsidy for farmers.",
        "context": "Financial Daily Press Release"
    }

    response = client.post("/api/verify/text", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "extracted"
    assert data["sentence_count"] >= 3
    assert data["claims_count"] >= 3
    assert len(data["claims"]) == data["claims_count"]
    assert "request_id" in data

    # Verify database persistence
    db = SessionLocal()
    try:
        vr = db.query(VerificationRequest).filter_by(id=data["request_id"]).first()
        assert vr is not None
        assert vr.request_type == "text"
        assert vr.status == "extracted"

        db_claims = db.query(Claim).filter_by(request_id=vr.id).all()
        assert len(db_claims) == data["claims_count"]
        for c in db_claims:
            assert c.claim_text is not None
            assert c.claim_type is not None
            assert c.verifiability is not None
            assert c.original_sentence is not None
    finally:
        db.close()


def test_api_verify_text_invalid_input(client: TestClient):
    # Too short input
    response = client.post("/api/verify/text", json={"text": "Hi"})
    assert response.status_code == 422
