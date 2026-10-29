import re
from typing import List, Dict, Any, Optional, Tuple

from app.verification.evidence.models import (
    EvidenceType,
    SourceRelationship,
    EvidenceConsistency,
    ExtractedEvidenceItem,
    SourceComparisonItem
)


def calculate_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Calculates Jaccard word similarity between two texts."""
    tokens_a = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", text_a.lower()))
    tokens_b = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


WIRE_SERVICES = {"reuters", "associated press", "ap", "pti", "press trust of india", "ani", "afp", "bloomberg"}


class SourceComparator:
    """
    Compares evidence across discovered sources to evaluate independence,
    reproduction/syndication, and factual agreement versus contradiction.
    Strictly avoids assigning credibility winners or final truth verdicts.
    """

    def compare_sources_for_claim(
        self,
        claim_id: int,
        evidence_items: List[ExtractedEvidenceItem]
    ) -> List[SourceComparisonItem]:
        comparisons: List[SourceComparisonItem] = []
        if not evidence_items:
            return comparisons

        # 1. Pairwise Comparisons (limit to top 6 sources for performant pairings)
        items_to_pair = evidence_items[:6]
        n = len(items_to_pair)

        for i in range(n):
            for j in range(i + 1, n):
                item_a = items_to_pair[i]
                item_b = items_to_pair[j]

                rel, consistency, detail = self._compare_source_pair(item_a, item_b)

                comparisons.append(SourceComparisonItem(
                    claim_id=claim_id,
                    source_a_id=item_a.source_id,
                    source_b_id=item_b.source_id,
                    source_a_title=item_a.article_title or item_a.domain or "Source A",
                    source_b_title=item_b.article_title or item_b.domain or "Source B",
                    source_a_domain=item_a.domain,
                    source_b_domain=item_b.domain,
                    comparison_type="PAIRWISE",
                    source_relationship=rel,
                    evidence_consistency=consistency,
                    details=detail
                ))

        # 2. Group Synthesis Record
        supp_count = sum(1 for e in evidence_items if e.evidence_type == EvidenceType.SUPPORTING)
        contra_count = sum(1 for e in evidence_items if e.evidence_type == EvidenceType.CONTRADICTING)
        neutral_count = sum(1 for e in evidence_items if e.evidence_type in (EvidenceType.CONTEXTUAL, EvidenceType.INSUFFICIENT))

        if supp_count > 0 and contra_count > 0:
            consensus = "DISPUTED"
            summary = (
                f"Conflicting reporting detected: {supp_count} source(s) support the assertion "
                f"while {contra_count} source(s) provide contradicting evidence."
            )
            group_consistency = EvidenceConsistency.CONFLICTING_INFORMATION
        elif supp_count > 0 and contra_count == 0:
            consensus = "CONSISTENT_SUPPORTING"
            summary = (
                f"Consistent supporting coverage: {supp_count} source(s) corroborate the claim "
                f"without direct contradictions among retrieved items."
            )
            group_consistency = EvidenceConsistency.CONSISTENT_EVIDENCE
        elif contra_count > 0 and supp_count == 0:
            consensus = "CONSISTENT_CONTRADICTING"
            summary = (
                f"Consistent refutation: {contra_count} source(s) contradict the assertion "
                f"with contrary metrics, dates, or negations."
            )
            group_consistency = EvidenceConsistency.CONFLICTING_INFORMATION
        else:
            consensus = "INSUFFICIENT_EVIDENCE"
            summary = (
                f"Retrieved sources ({neutral_count} contextual/insufficient) do not provide "
                f"definitive confirmation or refutation."
            )
            group_consistency = EvidenceConsistency.INSUFFICIENT

        comparisons.append(SourceComparisonItem(
            claim_id=claim_id,
            comparison_type="GROUP_SYNTHESIS",
            source_relationship=SourceRelationship.UNKNOWN,
            evidence_consistency=group_consistency,
            details=summary,
            supporting_sources_count=supp_count,
            contradicting_sources_count=contra_count,
            neutral_sources_count=neutral_count,
            consensus_verdict=consensus,
            analysis_summary=summary
        ))

        return comparisons

    def _compare_source_pair(
        self, item_a: ExtractedEvidenceItem, item_b: ExtractedEvidenceItem
    ) -> Tuple[SourceRelationship, EvidenceConsistency, str]:
        domain_a = (item_a.domain or "").lower()
        domain_b = (item_b.domain or "").lower()
        pub_a = (item_a.publisher or "").lower()
        pub_b = (item_b.publisher or "").lower()

        # Check duplicate
        if domain_a and domain_a == domain_b and item_a.url == item_b.url:
            return (
                SourceRelationship.DUPLICATE,
                EvidenceConsistency.CONSISTENT_EVIDENCE,
                f"Duplicate entry: Both records refer to the identical URL on {domain_a}."
            )

        # Check lexical similarity between snippets or titles
        title_sim = calculate_jaccard_similarity(item_a.article_title or "", item_b.article_title or "")
        snippet_sim = calculate_jaccard_similarity(item_a.evidence_text, item_b.evidence_text)

        is_wire_a = any(w in pub_a for w in WIRE_SERVICES)
        is_wire_b = any(w in pub_b for w in WIRE_SERVICES)

        if title_sim > 0.75 or snippet_sim > 0.65 or (is_wire_a and is_wire_b):
            rel = SourceRelationship.POSSIBLY_SYNDICATED
            rel_reason = "High textual overlap or shared news wire attribution detected (likely syndicated)."
        elif domain_a and domain_b and domain_a != domain_b and pub_a != pub_b:
            rel = SourceRelationship.INDEPENDENT
            rel_reason = f"Independent reporting across distinct domains ({domain_a} vs {domain_b})."
        else:
            rel = SourceRelationship.UNKNOWN
            rel_reason = "Insufficient provenance metadata to establish reporting independence."

        # Consistency
        type_a = item_a.evidence_type
        type_b = item_b.evidence_type

        if type_a == EvidenceType.SUPPORTING and type_b == EvidenceType.SUPPORTING:
            consistency = EvidenceConsistency.CONSISTENT_EVIDENCE
            msg = f"{rel_reason} Both sources provide supporting evidence for the claim."
        elif type_a == EvidenceType.CONTRADICTING and type_b == EvidenceType.CONTRADICTING:
            consistency = EvidenceConsistency.CONSISTENT_EVIDENCE
            msg = f"{rel_reason} Both sources consistently contradict the claim."
        elif (type_a == EvidenceType.SUPPORTING and type_b == EvidenceType.CONTRADICTING) or \
             (type_a == EvidenceType.CONTRADICTING and type_b == EvidenceType.SUPPORTING):
            consistency = EvidenceConsistency.CONFLICTING_INFORMATION
            msg = f"{rel_reason} Conflict detected: One source supports the claim while the other refutes or contradicts it."
        elif type_a in (EvidenceType.SUPPORTING, EvidenceType.CONTRADICTING) or type_b in (EvidenceType.SUPPORTING, EvidenceType.CONTRADICTING):
            consistency = EvidenceConsistency.COMPLEMENTARY
            msg = f"{rel_reason} One source provides direct stance evidence while the other offers context."
        else:
            consistency = EvidenceConsistency.INSUFFICIENT
            msg = f"{rel_reason} Neither source provides definitive stance verification."

        return rel, consistency, msg
