import re
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any

from app.verification.evidence.base import EvidenceAnalyzer
from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    ExtractedEvidenceItem
)
from app.verification.preprocessing import segment_sentences

NEGATION_PATTERNS = [
    r"\bnot\b",
    r"\bno\b",
    r"\bnever\b",
    r"\bdenied\b",
    r"\bdenies\b",
    r"\brejected\b",
    r"\brejects\b",
    r"\brefused\b",
    r"\bfailed to\b",
    r"\buntrue\b",
    r"\bfalse\b",
    r"\bhalted\b",
    r"\bdismissed\b",
    r"\bcontrary to\b",
    r"\brefuted\b",
    r"\bdisputed\b",
    r"\bdebunked\b",
    r"\bdebunks\b",
    r"\bhoax\b",
    r"\bfake\b",
    r"\bfake news\b",
    r"\bfact[- ]check\b",
    r"\bno truth\b",
    r"\bfalsely claimed\b",
    r"\bviral claim is false\b",
    r"\bunfounded\b",
    r"\bmisleading\b",
    r"\bmisinformation\b",
    r"\bdisinformation\b",
    r"\bdoctored\b",
    r"\bmanipulated\b",
    r"\bbogus\b",
    r"\brumou?r\b",
    r"\bclarifies that no\b",
    r"\bdenial\b",
    r"\bincorrect\b",
]

WEAK_CONTEXT_PREDICATES = [
    r"\bconsidered\b",
    r"\bconsidering\b",
    r"\bdiscussed\b",
    r"\bdiscussing\b",
    r"\bproposed\b",
    r"\breviewing\b",
    r"\bunder review\b",
    r"\bplanning\b",
    r"\bweighing\b",
    r"\bmulls\b",
    r"\bmulling\b",
    r"\bmay\b",
    r"\bmight\b",
    r"\bcould\b",
]

STABILITY_PATTERNS = [
    r"\bunchanged\b",
    r"\bmaintained\b",
    r"\bheld steady\b",
    r"\bretained\b",
    r"\bkept steady\b",
    r"\bstatus quo\b",
    r"\bpaused\b",
]

CHANGE_INCREASE_PATTERNS = [
    r"\bincreased\b",
    r"\braised\b",
    r"\bhiked\b",
    r"\bhike\b",
    r"\bsurged\b",
    r"\bgrew\b",
    r"\bclimbed\b",
]

CHANGE_DECREASE_PATTERNS = [
    r"\bdecreased\b",
    r"\blowered\b",
    r"\bcut\b",
    r"\breduced\b",
    r"\bfell\b",
    r"\bdropped\b",
    r"\bslashed\b",
]

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"
]


def extract_numbers_and_units(text: str) -> List[Dict[str, Any]]:
    """Extracts numbers, currencies, percentages, and scale multipliers from text."""
    results = []
    # Match currency values like $5 billion, ₹500 crore, Rs 300 cr
    currency_pattern = re.compile(
        r"([\$€£₹]|rs\.?|inr|usd)?\s*([0-9]+(?:[\.,][0-9]+)?)\s*(%|percent|crore|cr|billion|million|lakh|bn|m|k|trillion)?",
        re.IGNORECASE
    )
    for match in currency_pattern.finditer(text):
        currency, val_str, unit = match.groups()
        if not val_str:
            continue
        try:
            val_clean = val_str.replace(",", "")
            numeric_val = float(val_clean)
        except ValueError:
            continue
        unit_str = (unit or "").lower().strip()
        curr_str = (currency or "").lower().strip()
        raw_token = match.group(0).strip()
        # Avoid standalone single digits unless with currency or unit
        if not curr_str and not unit_str and numeric_val < 10 and len(val_clean) == 1:
            continue
        # Filter standalone 4-digit calendar years so they are handled cleanly by temporal analysis
        if not curr_str and not unit_str and 1900 <= numeric_val <= 2099:
            continue
        results.append({

            "raw": raw_token,
            "value": numeric_val,
            "currency": curr_str,
            "unit": unit_str
        })
    return results


def extract_dates_and_years(text: str) -> List[Dict[str, Any]]:
    """Extracts years, months, and calendar dates from text."""
    dates = []
    # 4-digit years between 1900 and 2099
    year_pattern = re.compile(r"\b(19\d{2}|20\d{2})\b")
    for y_m in year_pattern.finditer(text):
        dates.append({"type": "year", "value": y_m.group(1), "raw": y_m.group(1)})

    # Month + Year like June 2026, March 2025
    month_year_pattern = re.compile(
        r"\b(" + "|".join(MONTH_NAMES) + r")\s+(19\d{2}|20\d{2})\b",
        re.IGNORECASE
    )
    for my_m in month_year_pattern.finditer(text):
        dates.append({
            "type": "month_year",
            "month": my_m.group(1).lower(),
            "year": my_m.group(2),
            "raw": my_m.group(0)
        })

    # Exact day + month like 10 June, June 15
    day_month_pattern = re.compile(
        r"\b(?:([0-3]?[0-9])\s+(" + "|".join(MONTH_NAMES) + r")|(" + "|".join(MONTH_NAMES) + r")\s+([0-3]?[0-9]))\b",
        re.IGNORECASE
    )
    for dm_m in day_month_pattern.finditer(text):
        raw = dm_m.group(0)
        dates.append({"type": "date", "raw": raw.lower()})

    return dates


class RuleBasedEvidenceAnalyzer(EvidenceAnalyzer):
    """
    Deterministic evidence extraction and stance comparison engine.
    Strictly forbids hallucination or synthetic quotes: evidence_text must be
    a verbatim excerpt from the source snippet or text.
    """

    def analyze_evidence(
        self,
        claim_id: int,
        claim_text: str,
        source_id: Optional[int],
        source_title: Optional[str],
        source_snippet: Optional[str],
        source_url: str,
        source_domain: Optional[str] = None,
        source_publisher: Optional[str] = None,
        publish_date: Optional[str] = None,
        claim_entities: Optional[List[str]] = None,
        claim_numbers: Optional[List[str]] = None,
        claim_dates: Optional[List[str]] = None,
    ) -> ExtractedEvidenceItem:
        claim_clean = claim_text.strip()
        combined_source_text = ""
        if source_title:
            combined_source_text += source_title.strip() + ". "
        if source_snippet:
            combined_source_text += source_snippet.strip()

        combined_source_text = combined_source_text.strip()

        # If source text is empty or meaningless
        if not combined_source_text or len(combined_source_text) < 15:
            return ExtractedEvidenceItem(
                claim_id=claim_id,
                source_id=source_id,
                evidence_text=combined_source_text or "No snippet or content available from source.",
                snippet=combined_source_text or "No snippet available",
                evidence_type=EvidenceType.INSUFFICIENT,
                direction=EvidenceType.INSUFFICIENT.value,
                relevance=EvidenceRelevance.LOW,
                relevance_score=0.1,
                confidence_in_extraction=0.9,
                stance_confidence=0.2,
                source_location="metadata",
                extraction_method="rule_based",
                extracted_at=datetime.now(timezone.utc),
                url=source_url,
                article_title=source_title,
                publisher=source_publisher,
                domain=source_domain,
                publish_date=publish_date,
                explanation="Source provides insufficient textual content to evaluate the claim."
            )

        # 1. Select the most relevant sentence/passage from source text
        sentences = segment_sentences(combined_source_text)
        best_passage, passage_score = self._select_best_passage(
            claim_clean, sentences, claim_entities or []
        )

        if not best_passage:
            best_passage = combined_source_text[:300]
            passage_score = 0.2

        # 2. Extract structured elements from claim and chosen passage
        claim_nums = extract_numbers_and_units(claim_clean)
        source_nums = extract_numbers_and_units(best_passage)

        claim_temporal = extract_dates_and_years(claim_clean)
        source_temporal = extract_dates_and_years(best_passage)

        # 3. Check entity overlap
        entity_match, matched_entities = self._evaluate_entities(
            claim_clean, best_passage, claim_entities or []
        )

        # 4. Check for Negation & Stance
        stance, confidence, relevance_tier, explanation = self._determine_stance(
            claim_text=claim_clean,
            source_passage=best_passage,
            entity_match=entity_match,
            matched_entities=matched_entities,
            claim_nums=claim_nums,
            source_nums=source_nums,
            claim_temporal=claim_temporal,
            source_temporal=source_temporal,
            passage_score=passage_score
        )

        norm_rel_score = 0.9 if relevance_tier == EvidenceRelevance.HIGH else (0.6 if relevance_tier == EvidenceRelevance.MEDIUM else 0.25)

        return ExtractedEvidenceItem(
            claim_id=claim_id,
            source_id=source_id,
            evidence_text=best_passage,
            snippet=best_passage,
            evidence_type=stance,
            direction=stance.value,
            relevance=relevance_tier,
            relevance_score=norm_rel_score,
            confidence_in_extraction=confidence,
            stance_confidence=0.85 if stance in (EvidenceType.SUPPORTING, EvidenceType.CONTRADICTING) else 0.6,
            source_location="snippet",
            extraction_method="rule_based",
            extracted_at=datetime.now(timezone.utc),
            url=source_url,
            article_title=source_title,
            publisher=source_publisher,
            domain=source_domain,
            publish_date=publish_date,
            explanation=explanation
        )

    def _select_best_passage(
        self, claim: str, sentences: List[str], entities: List[str]
    ) -> Tuple[str, float]:
        """Finds the source sentence with the highest factual keyword and entity overlap."""
        if not sentences:
            return "", 0.0

        claim_tokens = set(re.findall(r"\b[a-zA-Z0-9_\$₹%]{3,}\b", claim.lower()))
        stop_words = {"the", "and", "for", "that", "this", "with", "from", "were", "been", "have", "said", "also", "into"}
        claim_meaningful = claim_tokens - stop_words

        best_sentence = sentences[0]
        max_score = -1.0

        for sent in sentences:
            sent_lower = sent.lower()
            sent_tokens = set(re.findall(r"\b[a-zA-Z0-9_\$₹%]{3,}\b", sent_lower))
            overlap = claim_meaningful.intersection(sent_tokens)
            score = len(overlap) / max(len(claim_meaningful), 1)

            # Bonus for named entity matches
            for ent in entities:
                if ent.lower() in sent_lower:
                    score += 0.3

            if score > max_score:
                max_score = score
                best_sentence = sent

        return best_sentence, max(max_score, 0.1)

    def _evaluate_entities(
        self, claim: str, source_text: str, entities: List[str]
    ) -> Tuple[bool, List[str]]:
        """Checks if key entities in the claim are referenced in the source text."""
        source_lower = source_text.lower()
        matched = []
        for ent in entities:
            if ent.lower() in source_lower:
                matched.append(ent)

        # Also check capitalized tokens from claim
        claim_capitalized = set(re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", claim))
        for cap in claim_capitalized:
            if cap.lower() in ["the", "in", "on", "at", "for", "and", "according"]:
                continue
            if cap.lower() in source_lower and cap not in matched:
                matched.append(cap)

        return (len(matched) > 0 or len(entities) == 0), matched

    def _determine_stance(
        self,
        claim_text: str,
        source_passage: str,
        entity_match: bool,
        matched_entities: List[str],
        claim_nums: List[Dict[str, Any]],
        source_nums: List[Dict[str, Any]],
        claim_temporal: List[Dict[str, Any]],
        source_temporal: List[Dict[str, Any]],
        passage_score: float
    ) -> Tuple[EvidenceType, float, EvidenceRelevance, str]:
        claim_lower = claim_text.lower()
        source_lower = source_passage.lower()

        # If entities do not match at all and passage overlap is very low -> INSUFFICIENT
        if not entity_match and passage_score < 0.25:
            return (
                EvidenceType.INSUFFICIENT,
                0.85,
                EvidenceRelevance.LOW,
                "Source does not match primary claim entities or key assertions."
            )

        # ==========================================
        # 1. Numerical Analysis (Discrepancy / Match)
        # ==========================================
        if claim_nums and source_nums:
            for c_num in claim_nums:
                c_val = c_num["value"]
                c_unit = c_num["unit"]
                # Look for matching or conflicting number in source
                exact_match_found = False
                conflict_found = False
                conflict_val = None

                for s_num in source_nums:
                    s_val = s_num["value"]
                    s_unit = s_num["unit"]

                    if c_val == s_val and (not c_unit or not s_unit or c_unit == s_unit):
                        exact_match_found = True
                        break
                    elif c_val != s_val and (c_unit == s_unit or (not c_unit and not s_unit)):
                        # If both are percentages, or both have same currency/unit, conflict!
                        conflict_found = True
                        conflict_val = s_num["raw"]

                if conflict_found and not exact_match_found:
                    return (
                        EvidenceType.CONTRADICTING,
                        0.95,
                        EvidenceRelevance.HIGH,
                        f"Numerical conflict: Claim asserts {c_num['raw']}, but source specifies {conflict_val}."
                    )
                if exact_match_found:
                    # Proceed to check if negated or confirmed
                    pass

        # ==========================================
        # 2. Date / Temporal Analysis
        # ==========================================
        if claim_temporal and source_temporal:
            claim_years = [t["value"] for t in claim_temporal if t.get("type") == "year"]
            source_years = [t["value"] for t in source_temporal if t.get("type") == "year"]

            if claim_years and source_years:
                if not any(cy in source_years for cy in claim_years):
                    return (
                        EvidenceType.CONTRADICTING,
                        0.90,
                        EvidenceRelevance.HIGH,
                        f"Temporal conflict: Claim asserts date ({', '.join(claim_years)}), but source references ({', '.join(source_years)})."
                    )

            # Check day/month conflicts if discussing same event
            claim_my = [t for t in claim_temporal if t.get("type") == "month_year"]
            source_my = [t for t in source_temporal if t.get("type") == "month_year"]
            if claim_my and source_my:
                c_m = claim_my[0]
                s_m = source_my[0]
                if c_m["year"] == s_m["year"] and c_m["month"] != s_m["month"]:
                    return (
                        EvidenceType.CONTRADICTING,
                        0.92,
                        EvidenceRelevance.HIGH,
                        f"Temporal conflict: Claim mentions {c_m['raw']}, whereas source states {s_m['raw']}."
                    )

        # ==========================================
        # 3. Negation & Stability vs Change
        # ==========================================
        claim_has_negation = any(re.search(pat, claim_lower) for pat in NEGATION_PATTERNS)
        source_has_negation = any(re.search(pat, source_lower) for pat in NEGATION_PATTERNS)

        claim_has_increase = any(re.search(pat, claim_lower) for pat in CHANGE_INCREASE_PATTERNS)
        source_has_stability = any(re.search(pat, source_lower) for pat in STABILITY_PATTERNS)
        source_has_decrease = any(re.search(pat, source_lower) for pat in CHANGE_DECREASE_PATTERNS)

        # E.g. Claim: "increased repo rate" vs Source: "kept unchanged" or "maintained steady"
        if claim_has_increase and source_has_stability:
            return (
                EvidenceType.CONTRADICTING,
                0.95,
                EvidenceRelevance.HIGH,
                "Action contradiction: Claim asserts increase/change, but source reports status quo / unchanged."
            )

        if claim_has_increase and source_has_decrease:
            return (
                EvidenceType.CONTRADICTING,
                0.95,
                EvidenceRelevance.HIGH,
                "Directional contradiction: Claim asserts increase, whereas source reports cut/reduction."
            )

        # Affirmative claim vs explicitly negated source statement
        if not claim_has_negation and source_has_negation:
            # Check if negation applies to predicate
            neg_match = [pat for pat in NEGATION_PATTERNS if re.search(pat, source_lower)]
            return (
                EvidenceType.CONTRADICTING,
                0.90,
                EvidenceRelevance.HIGH,
                f"Negation contradiction: Source explicitly negates or refutes assertion ({neg_match[0]})."
            )

        # Weak predicates: e.g. "considered" vs "approved"
        source_has_weak_predicate = any(re.search(pat, source_lower) for pat in WEAK_CONTEXT_PREDICATES)
        if source_has_weak_predicate and not any(re.search(pat, claim_lower) for pat in WEAK_CONTEXT_PREDICATES):
            return (
                EvidenceType.CONTEXTUAL,
                0.80,
                EvidenceRelevance.MEDIUM,
                "Contextual overlap: Source indicates discussion, proposal, or review rather than a confirmed outcome."
            )

        # Check if the source passage is purely speculative, rumor-oriented, or a question
        is_speculative_or_question = (
            source_passage.strip().endswith("?")
            or any(re.search(pat, source_lower) for pat in [
                r"\bis it true\b",
                r"\bviral claim\b",
                r"\brumou?rs suggest\b",
                r"\bclaims circulating\b",
                r"\bunconfirmed reports\b",
                r"\bsocial media users claim\b"
            ])
        )
        if is_speculative_or_question and not source_has_negation:
            return (
                EvidenceType.CONTEXTUAL,
                0.75,
                EvidenceRelevance.MEDIUM,
                "Contextual overlap: Source references viral claims, questions, or rumors rather than confirmed facts."
            )

        # ==========================================
        # 4. Confirmation / Supporting
        # ==========================================
        # Extract meaningful claim tokens (excluding entities and generic stop words)
        claim_meaningful_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", claim_lower)) - {
            "that", "with", "from", "were", "been", "have", "said", "also", "into", "this", "about", "their"
        }
        for ent in matched_entities:
            for ent_w in ent.lower().split():
                claim_meaningful_tokens.discard(ent_w)

        source_has_action = any(tok in source_lower for tok in claim_meaningful_tokens)

        # Numerical constraint: If claim has explicit numbers, source must corroborate at least one
        numerical_ok = True
        if claim_nums:
            if not source_nums:
                numerical_ok = False
            else:
                c_vals = {c["value"] for c in claim_nums}
                s_vals = {s["value"] for s in source_nums}
                numerical_ok = bool(c_vals.intersection(s_vals))

        # Temporal constraint: If claim has explicit year/date, source must corroborate if years are present
        temporal_ok = True
        if claim_temporal and source_temporal:
            claim_years = [t["value"] for t in claim_temporal if t.get("type") == "year"]
            source_years = [t["value"] for t in source_temporal if t.get("type") == "year"]
            if claim_years and source_years:
                temporal_ok = any(cy in source_years for cy in claim_years)

        # Strict Supporting evidence standard
        if passage_score >= 0.35 and entity_match and numerical_ok and temporal_ok and (source_has_action or passage_score >= 0.50):
            if claim_nums and source_nums and numerical_ok:
                return (
                    EvidenceType.SUPPORTING,
                    0.92,
                    EvidenceRelevance.HIGH,
                    "Supporting evidence: Source corroborates the assertions, entities, and numerical parameters."
                )
            return (
                EvidenceType.SUPPORTING,
                0.88,
                EvidenceRelevance.HIGH,
                "Supporting evidence: Source contextually confirms the core entities and factual predicates."
            )

        # ==========================================
        # 5. Contextual or Insufficient
        # ==========================================
        if entity_match or passage_score >= 0.2:
            return (
                EvidenceType.CONTEXTUAL,
                0.75,
                EvidenceRelevance.MEDIUM,
                "Contextual information: Source addresses related background or entities without directly confirming or refuting the atomic claim."
            )

        return (
            EvidenceType.INSUFFICIENT,
            0.80,
            EvidenceRelevance.LOW,
            "Insufficient evidence: Source content does not provide conclusive information regarding this claim."
        )
