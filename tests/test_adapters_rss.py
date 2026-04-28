from datetime import UTC, datetime

from sonde.adapters.base import RawSourceRecord
from sonde.adapters.rss import RSSAdapter
from sonde.engine.loader import load_topics


def test_rss_normalize(examples_path) -> None:
    topic = load_topics(examples_path)[0]
    record = RawSourceRecord(
        source="rss",
        source_id="x",
        title="Agent Security",
        url="https://example.com",
        raw={"title": "Agent Security", "link": "https://example.com"},
        fetched_at=datetime.now(UTC),
        query="q",
        response_hash="sha256:test",
    )
    artifact = RSSAdapter().normalize(record, topic, "run_1", "sha256:config")
    assert artifact.source == "rss"
