import re
from typing import List, Dict, Optional, Set

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "by", "from", "of", "about", "that", "this", "these", "those", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "it", "its", "they", "them", "their", "we", "us", "our", "you", "your",
    "he", "him", "his", "she", "her", "said", "stated", "announced", "claimed",
    "according", "breaking", "news", "exclusive", "update", "shocking"
}

OFFICIAL_AUTHORITIES = {
    "RBI": "rbi.org.in",
    "Reserve Bank of India": "rbi.org.in",
    "ISRO": "isro.gov.in",
    "WHO": "who.int",
    "World Health Organization": "who.int",
    "NASA": "nasa.gov",
    "Supreme Court": "supremecourtofindia.nic.in",
    "Finance Ministry": "finmin.nic.in",
    "PIB": "pib.gov.in",
    "Election Commission": "eci.gov.in"
}


class GeneratedQuery:
    def __init__(self, query_text: str, strategy_level: str, priority: int = 1):
        self.query_text = query_text
        self.strategy_level = strategy_level
        self.priority = priority

    def to_dict(self) -> Dict[str, str]:
        return {
            "query_text": self.query_text,
            "strategy_level": self.strategy_level
        }


class SearchQueryGenerator:
    """
    Generates high-precision, multi-level search queries from an atomic claim.
    Employs structured strategies: Core -> Entity/Date -> Official -> Fact Check.
    """

    def generate_queries(
        self,
        claim_text: str,
        entities: Optional[List[str]] = None,
        dates: Optional[List[str]] = None,
        numbers: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        source_attributions: Optional[List[str]] = None,
        max_queries: int = 3
    ) -> List[GeneratedQuery]:
        entities = entities or []
        dates = dates or []
        numbers = numbers or []
        locations = locations or []
        source_attributions = source_attributions or []

        generated: List[GeneratedQuery] = []
        seen_queries: Set[str] = set()

        def add_query(text: str, level: str, priority: int):
            clean = self._clean_query_text(text)
            if clean and len(clean) >= 6 and clean.lower() not in seen_queries:
                seen_queries.add(clean.lower())
                generated.append(GeneratedQuery(clean, level, priority))

        # -------------------------------------------------------------
        # Level 1: Core Claim / Near-Exact Distilled Search
        # -------------------------------------------------------------
        core_tokens = self._extract_core_keywords(claim_text)
        if core_tokens:
            add_query(" ".join(core_tokens), "LEVEL_1_EXACT", priority=1)

        # -------------------------------------------------------------
        # Level 2: Entity + Numbers/Events + Dates Search
        # -------------------------------------------------------------
        lvl2_parts = []
        for ent in entities[:2]:
            lvl2_parts.append(ent)
        for num in numbers[:2]:
            lvl2_parts.append(num)
        for dt in dates[:1]:
            lvl2_parts.append(dt)
        for loc in locations[:1]:
            if loc not in lvl2_parts:
                lvl2_parts.append(loc)

        if len(lvl2_parts) >= 2:
            # Add significant verb/subject from claim if not covered
            action_words = [w for w in core_tokens if w.lower() not in [p.lower() for p in lvl2_parts]]
            combined = lvl2_parts + action_words[:2]
            add_query(" ".join(combined), "LEVEL_2_ENTITY_DATE", priority=2)

        # -------------------------------------------------------------
        # Level 3: Official Authority Query (Targeted domain or source)
        # -------------------------------------------------------------
        for ent in entities + source_attributions:
            for authority, domain in OFFICIAL_AUTHORITIES.items():
                if authority.lower() in ent.lower() or ent.lower() in authority.lower():
                    topic_words = [w for w in core_tokens if authority.lower() not in w.lower()][:3]
                    if topic_words:
                        add_query(f"{authority} official {' '.join(topic_words)}", "LEVEL_3_OFFICIAL", priority=3)
                    break

        # -------------------------------------------------------------
        # Level 4: Fact-Check Targeted Query
        # -------------------------------------------------------------
        subject_tokens = entities[:1] or core_tokens[:3]
        if subject_tokens:
            add_query(f"{' '.join(subject_tokens)} fact check", "LEVEL_4_FACT_CHECK", priority=4)

        # Fallback if no queries were generated
        if not generated:
            clean_raw = self._clean_query_text(claim_text)
            add_query(clean_raw, "LEVEL_1_EXACT", priority=1)

        # Sort by priority and cap to max_queries
        generated.sort(key=lambda q: q.priority)
        return generated[:max_queries]

    def _clean_query_text(self, text: str) -> str:
        """Removes punctuation, quotes, multiple spaces, and conversational prefixes."""
        cleaned = re.sub(r"^(?:breaking\s+news:?|update:?|exclusive:?)\s*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^\w\s$%.,-]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _extract_core_keywords(self, text: str) -> List[str]:
        """Filters stopwords and extracts essential query words."""
        cleaned = self._clean_query_text(text)
        words = cleaned.split()
        meaningful = []
        for w in words:
            clean_word = w.strip(".,;:?!")
            if clean_word.lower() not in STOP_WORDS and len(clean_word) > 1:
                meaningful.append(clean_word)
        return meaningful
