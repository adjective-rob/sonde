import asyncio

from topicops.adapters.local_jsonl import LocalJsonlAdapter
from topicops.engine.loader import load_topics


def test_local_jsonl_adapter(examples_path) -> None:
    topic = load_topics(examples_path)[0]
    source = topic.sources[0]
    records = asyncio.run(LocalJsonlAdapter().search(topic, source, limit=10))
    assert records
    assert "Insurance" not in " ".join(record.title or "" for record in records)
