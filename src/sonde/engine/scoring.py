from __future__ import annotations

from sonde.engine.lineage import normalize_text
from sonde.models.topic import Topic


def score_record(
    topic: Topic,
    title: str | None,
    summary: str | None,
    metadata: dict[str, object],
    *,
    seen_count: int = 0,
    previous_run_artifacts: int = 0,
    current_run_artifacts: int = 0,
) -> dict[str, float]:
    text = normalize_text(
        " ".join([title or "", summary or "", " ".join(map(str, metadata.values()))])
    )
    query_terms = {term for query in topic.queries for term in normalize_text(query).split()}
    alias_terms = {term for alias in topic.aliases for term in normalize_text(alias).split()}
    negative_terms = [normalize_text(term) for term in topic.negative_terms]
    hits = sum(1 for term in query_terms.union(alias_terms) if term in text)
    relevance = min(1.0, hits / max(len(query_terms), 1))
    noise = 0.0
    for term in negative_terms:
        if term in text:
            noise += 0.35
    if not title or not summary:
        noise += 0.2

    # Novelty: decays with repeated sightings
    if seen_count == 0:
        novelty = 1.0
    elif seen_count == 1:
        novelty = 0.6
    elif seen_count <= 3:
        novelty = 0.3
    else:
        novelty = 0.1

    # Velocity: rate of change in artifact yield between runs
    velocity = 0.0
    if previous_run_artifacts > 0:
        velocity = round(
            (current_run_artifacts - previous_run_artifacts) / previous_run_artifacts, 3
        )
    elif current_run_artifacts > 0:
        velocity = 1.0

    return {
        "relevance": round(max(0.0, relevance - noise * 0.25), 3),
        "noise": round(min(1.0, noise), 3),
        "novelty": round(novelty, 3),
        "velocity": velocity,
    }
