from datetime import UTC, datetime

from topicops.adapters.base import RawSourceRecord
from topicops.adapters.huggingface import HuggingFaceAdapter
from topicops.engine.loader import load_topics


def test_huggingface_normalize(examples_path) -> None:
    topic = load_topics(examples_path)[0]
    record = RawSourceRecord(
        source="huggingface",
        source_id="example/model",
        title="example/model",
        url=None,
        raw={"modelId": "example/model"},
        fetched_at=datetime.now(UTC),
        query="q",
        response_hash="sha256:test",
    )
    artifact = HuggingFaceAdapter().normalize(record, topic, "run_1", "sha256:config")
    assert artifact.title == "example/model"
