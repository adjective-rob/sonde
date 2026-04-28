from datetime import UTC, datetime

from topicops.adapters.arxiv import ArxivAdapter
from topicops.adapters.base import RawSourceRecord
from topicops.engine.loader import load_topics


def test_arxiv_normalize(examples_path) -> None:
    xml = (
        '<entry xmlns="http://www.w3.org/2005/Atom">'
        "<id>x</id><title>Agent Security</title><summary>AI agents</summary></entry>"
    )
    topic = load_topics(examples_path)[0]
    record = RawSourceRecord(
        source="arxiv",
        source_id="x",
        title="Agent Security",
        url="x",
        raw={"xml": xml},
        fetched_at=datetime.now(UTC),
        query="q",
        response_hash="sha256:test",
    )
    artifact = ArxivAdapter().normalize(record, topic, "run_1", "sha256:config")
    assert artifact.title == "Agent Security"
