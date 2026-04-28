from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from sonde.engine.lineage import normalize_text
from sonde.models.topic import Topic


@dataclass
class NearOverlap:
    left: str
    right: str
    score: float
    reason: str


@dataclass
class DedupeResult:
    hard_duplicates: list[tuple[str, str, str]] = field(default_factory=list)
    case_insensitive_duplicates: list[tuple[str, str, str]] = field(default_factory=list)
    near_overlaps: list[NearOverlap] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "hard_duplicates": self.hard_duplicates,
            "case_insensitive_duplicates": self.case_insensitive_duplicates,
            "near_overlaps": [overlap.__dict__ for overlap in self.near_overlaps],
        }


def topic_terms(topic: Topic) -> set[str]:
    terms: set[str] = set()
    for value in [*topic.queries, *topic.aliases, *topic.tags]:
        terms.update(normalize_text(value).replace("-", " ").split())
    return {term for term in terms if len(term) > 2}


def dedupe_topics(topics: list[Topic], include_near: bool = False) -> DedupeResult:
    result = DedupeResult()
    id_seen: dict[str, str] = {}
    query_seen: dict[str, str] = {}

    for topic in topics:
        normalized_id = normalize_text(topic.id)
        if normalized_id in id_seen:
            result.hard_duplicates.append(("topic_id", id_seen[normalized_id], topic.id))
        id_seen[normalized_id] = topic.id
        for query in topic.queries:
            normalized = normalize_text(query)
            if normalized in query_seen and query_seen[normalized] != topic.id:
                result.hard_duplicates.append(("query", query_seen[normalized], topic.id))
                result.case_insensitive_duplicates.append(
                    ("query", query_seen[normalized], topic.id)
                )
            query_seen[normalized] = topic.id

    if include_near:
        for index, left in enumerate(topics):
            left_terms = topic_terms(left)
            left_text = " ".join([*left.queries, *left.aliases, *left.tags])
            for right in topics[index + 1 :]:
                right_terms = topic_terms(right)
                shared = sorted(left_terms.intersection(right_terms))
                token_score = (
                    fuzz.token_set_ratio(
                        left_text, " ".join([*right.queries, *right.aliases, *right.tags])
                    )
                    / 100
                )
                overlap_score = len(shared) / max(len(left_terms.union(right_terms)), 1)
                score = max(token_score, overlap_score)
                if score >= 0.72 or (len(shared) >= 3 and score >= 0.5):
                    result.near_overlaps.append(
                        NearOverlap(
                            left=left.id,
                            right=right.id,
                            score=round(score, 3),
                            reason=f"shared terms: {', '.join(shared[:8])}",
                        )
                    )
    return result
