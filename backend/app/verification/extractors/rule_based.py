import re
from typing import List, Optional, Set, Tuple
from app.verification.domain_models import (
    ClaimType,
    Verifiability,
    Importance,
    ExtractedClaimItem
)
from app.verification.extractors.base import ClaimExtractor
from app.verification.preprocessing import clean_text, segment_sentences

# Known prominent institutions, government bodies, and agencies
KNOWN_ENTITIES = [
    "RBI", "Reserve Bank of India",
    "Supreme Court", "High Court",
    "Finance Ministry", "Ministry of Finance", "Ministry of Home Affairs", "Ministry of Defence",
    "Prime Minister", "Chief Minister", "President",
    "Government of India", "Government", "Parliament", "Lok Sabha", "Rajya Sabha",
    "WHO", "World Health Organization",
    "NASA", "ISRO", "DRDO",
    "UN", "United Nations", "UNICEF",
    "IMF", "World Bank", "WTO",
    "CDC", "FDA", "White House",
    "Congress", "BJP", "Election Commission"
]

# Patterns for extraction
PERCENTAGE_REGEX = re.compile(r"\b\d+(?:\.\d+)?%", re.IGNORECASE)
CURRENCY_REGEX = re.compile(
    r"(?:[$₹€£]|Rs\.?|INR|USD)\s*[\d,]+(?:\.\d+)?(?:\s*(?:crore|lakh|billion|million|trillion))?",
    re.IGNORECASE
)
GENERAL_NUMBER_REGEX = re.compile(
    r"\b\d+(?:,\d+)*(?:\.\d+)?\s*(?:crore|lakh|billion|million|trillion|percent|basis points|bps|km|miles|tons)?\b",
    re.IGNORECASE
)

DATE_REGEX = re.compile(
    r"\b(?:"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,4}"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)(?:\s+\d{2,4})?"
    r"|\b(?:19|20)\d{2}\b"
    r"|\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|yesterday|today|tomorrow)\b"
    r"|\b(?:in\s+)?(?:\w+\s+)?(?:months?|weeks?|years?|days?|decades?)\b"
    r")",
    re.IGNORECASE
)

ATTRIBUTION_REGEX = re.compile(
    r"(?:according\s+to\s+([A-Z][a-zA-Z0-9\s&]+?)(?:,|\.|\s+that)|([A-Z][a-zA-Z0-9\s&]+?)\s+(?:announced|stated|said|reported|claimed|tweeted|declared|confirmed|warned|revealed)\s+that)",
    re.IGNORECASE
)

CAUSAL_WORDS = {"caused", "causing", "led to", "leading to", "resulted in", "resulting in", "triggered", "spurred", "due to", "responsible for"}
COMPARATIVE_WORDS = {"more than", "less than", "higher than", "lower than", "faster than", "slower than", "increased by", "decreased by", "rose by", "fell by", "doubled", "tripled"}
POLICY_WORDS = {"subsidy", "scheme", "law", "act", "ordinance", "bill", "mandate", "regulations", "policy", "reform", "budget", "tax", "tariff", "repo rate"}
OPINION_WORDS = {"best", "worst", "shocking", "amazing", "terrible", "unbelievable", "greatest", "disgrace", "heroic", "corrupt", "masterpiece", "pathetic", "brilliant"}
NON_VERIFIABLE_PATTERNS = [
    re.compile(r"\b(?:please\s+)?(?:share|forward|subscribe|click\s+here|follow\s+us|retweet)\b", re.IGNORECASE),
    re.compile(r"\b(?:wow|omg|unbelievable|shocking)!+\b", re.IGNORECASE),
    re.compile(r"^\s*(?:what\s+do\s+you\s+think|agree\?|thoughts\?)\s*$", re.IGNORECASE)
]


class RuleBasedClaimExtractor(ClaimExtractor):
    """
    Robust rule-based claim extraction using linguistic structure,
    named entity heuristics, atomic clause splitting, and classification.
    """

    def extract_claims(self, text: str, context: Optional[str] = None) -> List[ExtractedClaimItem]:
        original_text, normalized_text = clean_text(text)
        sentences = segment_sentences(normalized_text)

        raw_claims: List[Tuple[str, str, Optional[str]]] = []  # (claim_text, original_sentence, antecedent_subject)
        last_subject = None

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Detect leading subject from previous context if applicable
            current_subject = self._extract_leading_subject(sentence) or last_subject

            # Split compound clauses into atomic assertions
            atomic_clauses = self._split_atomic_clauses(sentence, current_subject)
            for clause in atomic_clauses:
                raw_claims.append((clause, sentence, current_subject))

            if current_subject:
                last_subject = current_subject

        # Process, enrich, and classify each atomic claim
        extracted_items: List[ExtractedClaimItem] = []
        seen_normalized: Set[str] = set()
        claim_counter = 1

        for claim_text, original_sentence, antecedent in raw_claims:
            claim_text = claim_text.strip()
            if not claim_text or len(claim_text) < 5:
                continue

            # Normalization
            norm_claim = self._normalize_claim_text(claim_text)
            canonical_key = self._canonical_key(norm_claim)

            # Deduplication
            if canonical_key in seen_normalized:
                continue
            seen_normalized.add(canonical_key)

            # Extract entities, numbers, dates, attribution
            entities = self._extract_entities(claim_text)
            if context and context.strip() and context.strip() not in entities:
                entities.append(context.strip())

            numbers = self._extract_numbers(claim_text)
            dates = self._extract_dates(claim_text)
            locations = self._extract_locations(claim_text)
            attributions = self._extract_attributions(claim_text, original_sentence)

            # Classification
            claim_type = self._classify_claim_type(claim_text, numbers, dates, attributions)
            verifiability = self._classify_verifiability(claim_text, claim_type)
            importance = self._classify_importance(claim_text, claim_type, numbers, entities)

            claim_item = ExtractedClaimItem(
                id=f"claim_{claim_counter:03d}",
                text=claim_text,
                normalized_text=norm_claim,
                claim_type=claim_type,
                verifiability=verifiability,
                importance=importance,
                entities=entities,
                dates=dates,
                locations=locations,
                numbers=numbers,
                source_attributions=attributions,
                original_sentence=original_sentence,
                extraction_method="rule_based"
            )
            extracted_items.append(claim_item)
            claim_counter += 1

        return extracted_items

    def _extract_leading_subject(self, sentence: str) -> Optional[str]:
        """Identifies the primary noun phrase subject of a sentence."""
        for ent in KNOWN_ENTITIES:
            if re.search(r"\b" + re.escape(ent) + r"\b", sentence, re.IGNORECASE):
                return ent

        # Match first capitalized word phrase
        match = re.match(r"^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", sentence)
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in {"the", "a", "an", "on", "in", "according", "when", "as", "it", "this"}:
                return candidate
        return None

    def _split_atomic_clauses(self, sentence: str, subject_hint: Optional[str]) -> List[str]:
        """
        Splits compound sentences with coordinating conjunctions ('and', 'but', 'while')
        into discrete atomic factual assertions.
        """
        # Conjunction split pattern joining independent clauses
        # e.g., "India launched the satellite in 2024 and it successfully entered orbit."
        split_pattern = re.compile(
            r"\s+(?:and|but|while|whereas)\s+(?=(?:it|they|the\s+\w+|he|she|[A-Z][a-zA-Z]+)\s+[a-z]+)",
            re.IGNORECASE
        )

        parts = split_pattern.split(sentence)
        if len(parts) <= 1:
            return [sentence]

        atomic = []
        for i, part in enumerate(parts):
            part = part.strip().rstrip(",;.")
            if not part:
                continue

            # Ensure proper terminal punctuation
            if not part.endswith("."):
                part += "."

            # Context preservation / Anaphora resolution for second clause
            if i > 0:
                # If clause begins with pronoun ("it", "they") and we have a preceding noun phrase
                sub_match = re.search(r"\b(satellite|scheme|policy|mission|project|rocket|decision|ordinance)\b", parts[0], re.IGNORECASE)
                if sub_match and part.lower().startswith("it "):
                    part = f"The {sub_match.group(1).lower()}" + part[2:]
                elif subject_hint and part.lower().startswith("it "):
                    part = f"The {subject_hint.lower()}" + part[2:]

            # Ensure capitalized first letter
            part = part[0].upper() + part[1:] if len(part) > 1 else part
            atomic.append(part)

        return atomic if atomic else [sentence]

    def _extract_entities(self, text: str) -> List[str]:
        """Extracts recognized institutions, government bodies, and named entities."""
        found = []
        for entity in KNOWN_ENTITIES:
            if re.search(r"\b" + re.escape(entity) + r"\b", text, re.IGNORECASE):
                if entity not in found:
                    found.append(entity)

        # Regex for additional capitalized multi-word proper nouns
        proper_nouns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text)
        for pn in proper_nouns:
            if pn not in found and pn not in {"The Decision", "June 2026", "On Monday"}:
                found.append(pn)

        return found

    def _extract_numbers(self, text: str) -> List[str]:
        """Extracts percentages, currencies, and quantitative metrics."""
        numbers: List[str] = []

        # 1. Percentages
        for pct in PERCENTAGE_REGEX.findall(text):
            if pct not in numbers:
                numbers.append(pct)

        # 2. Currency
        for curr in CURRENCY_REGEX.findall(text):
            curr_str = curr.strip()
            if curr_str not in numbers:
                numbers.append(curr_str)

        # 3. Specific quantities with units
        for num in GENERAL_NUMBER_REGEX.findall(text):
            num_str = num.strip()
            # Avoid single digit non-quantities or pure 4-digit years
            if re.match(r"^(?:19|20)\d{2}$", num_str):
                continue
            if len(num_str) > 1 and num_str not in numbers and not any(num_str in n for n in numbers):
                numbers.append(num_str)

        return numbers

    def _extract_dates(self, text: str) -> List[str]:
        """Extracts dates, years, and time periods."""
        dates: List[str] = []
        for match in DATE_REGEX.finditer(text):
            d_str = match.group(0).strip()
            # Clean leading prepositions
            clean_d = re.sub(r"^(?:in|on|since|from)\s+", "", d_str, flags=re.IGNORECASE).strip()
            if clean_d and clean_d not in dates:
                dates.append(clean_d)
        return dates

    def _extract_locations(self, text: str) -> List[str]:
        """Extracts geographic locations."""
        known_places = [
            "India", "United States", "US", "China", "Russia", "Ukraine", "United Kingdom", "UK",
            "Delhi", "New Delhi", "Mumbai", "Bengaluru", "Washington", "London", "Tokyo", "Paris",
            "Mars", "Moon"
        ]
        locations = []
        for place in known_places:
            if re.search(r"\b" + re.escape(place) + r"\b", text, re.IGNORECASE):
                if place not in locations:
                    locations.append(place)
        return locations

    def _extract_attributions(self, text: str, original_sentence: str) -> List[str]:
        """Identifies attributed speakers or reporting organizations."""
        attributions = []
        match = ATTRIBUTION_REGEX.search(original_sentence)
        if match:
            attr = (match.group(1) or match.group(2) or "").strip()
            if attr and attr not in attributions:
                attributions.append(attr)

        # Look for direct "RBI announced...", "Ministry stated..."
        for entity in KNOWN_ENTITIES:
            if re.search(r"\b" + re.escape(entity) + r"\s+(?:announced|stated|said|reported|claimed|decided)\b", text, re.IGNORECASE):
                if entity not in attributions:
                    attributions.append(entity)

        return attributions

    def _classify_claim_type(
        self,
        text: str,
        numbers: List[str],
        dates: List[str],
        attributions: List[str]
    ) -> ClaimType:
        """Classifies claim into structured categories."""
        lower = text.lower()

        # Check for non-verifiable or opinion first
        for pat in NON_VERIFIABLE_PATTERNS:
            if pat.search(text):
                return ClaimType.NON_VERIFIABLE

        if any(w in lower.split() for w in OPINION_WORDS):
            return ClaimType.OPINION

        # Causal claim
        if any(w in lower for w in CAUSAL_WORDS):
            return ClaimType.CAUSAL

        # Comparative claim
        if any(w in lower for w in COMPARATIVE_WORDS):
            return ClaimType.COMPARATIVE

        # Policy claim
        if any(w in lower for w in POLICY_WORDS):
            return ClaimType.POLICY

        # Numerical claim
        if numbers:
            return ClaimType.NUMERICAL

        # Quote / attribution claim
        if attributions:
            return ClaimType.QUOTE_ATTRIBUTION

        # Temporal claim
        if dates and len(text.split()) < 10:
            return ClaimType.TEMPORAL

        return ClaimType.FACTUAL

    def _classify_verifiability(self, text: str, claim_type: ClaimType) -> Verifiability:
        """Determines if the statement can be objectively evaluated with evidence."""
        if claim_type == ClaimType.NON_VERIFIABLE:
            return Verifiability.UNVERIFIABLE
        if claim_type == ClaimType.OPINION:
            return Verifiability.SUBJECTIVE
        return Verifiability.VERIFIABLE

    def _classify_importance(
        self,
        text: str,
        claim_type: ClaimType,
        numbers: List[str],
        entities: List[str]
    ) -> Importance:
        """Calculates extraction importance for later verification prioritization."""
        # High signals: economic numbers, government announcements, causal impacts, policy changes
        if claim_type in {ClaimType.NUMERICAL, ClaimType.CAUSAL, ClaimType.POLICY}:
            return Importance.HIGH
        if len(entities) >= 2 or (entities and numbers):
            return Importance.HIGH

        if claim_type in {ClaimType.FACTUAL, ClaimType.EVENT, ClaimType.QUOTE_ATTRIBUTION}:
            return Importance.MEDIUM

        return Importance.LOW

    def _normalize_claim_text(self, text: str) -> str:
        """Produces a canonical whitespace-normalized representation."""
        clean = re.sub(r"\s+", " ", text).strip()
        # Remove trailing periods for normalization
        return clean.rstrip(".")

    def _canonical_key(self, text: str) -> str:
        """Extracts a lowercase token signature to detect duplicates."""
        words = re.findall(r"\b[a-z0-9]+\b", text.lower())
        stop_words = {"the", "a", "an", "is", "was", "in", "on", "at", "to", "for", "of"}
        meaningful = [w for w in words if w not in stop_words]
        return " ".join(sorted(meaningful))
