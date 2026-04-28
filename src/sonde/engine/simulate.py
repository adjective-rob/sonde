from __future__ import annotations

from dataclasses import dataclass, field

from sonde.adapters import adapter_registry
from sonde.engine.lineage import hash_canonical
from sonde.engine.scoring import score_record
from sonde.models.topic import Topic


@dataclass
class SimulationResult:
    topic_id: str
    source: str
    queries_tested: int
    records_sampled: int
    potential_duplicates: int
    estimated_relevance: float
    estimated_noise: float
    estimated_novelty: float
    top_records: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return self.__dict__


async def simulate_topic(topic: Topic, source_id: str, *, limit: int = 20) -> SimulationResult:
    adapters = adapter_registry()
    adapter = adapters[source_id]
    source_config = next(source for source in topic.sources if source.id == source_id)
    records = await adapter.search(topic, source_config, limit=limit, dry_run=False)
    seen: set[str] = set()
    duplicate_count = 0
    relevance_total = 0.0
    noise_total = 0.0
    novelty_total = 0.0
    top_records: list[str] = []
    config_hash = hash_canonical(topic.model_dump(mode="json"))
    for record in records:
        artifact = adapter.normalize(record, topic, "simulation", config_hash)
        if artifact.normalized_hash in seen:
            duplicate_count += 1
        seen.add(artifact.normalized_hash)
        scores = score_record(topic, artifact.title, artifact.summary, artifact.metadata)
        relevance_total += scores["relevance"]
        noise_total += scores["noise"]
        novelty_total += scores["novelty"]
        top_records.append(artifact.title)
    count = max(len(records), 1)
    return SimulationResult(
        topic_id=topic.id,
        source=source_id,
        queries_tested=len(topic.queries),
        records_sampled=len(records),
        potential_duplicates=duplicate_count,
        estimated_relevance=round(relevance_total / count, 3),
        estimated_noise=round(noise_total / count, 3),
        estimated_novelty=round(novelty_total / count, 3),
        top_records=top_records[:10],
    )
