from datetime import UTC, datetime

from sonde.models.run import CollectionRun, RunManifest, RunStatus
from sonde.models.topic import TopicSnapshot


def test_manifest_model() -> None:
    run = CollectionRun(
        id="run_1",
        started_at=datetime.now(UTC),
        status=RunStatus.completed,
        topic_ids=["agent_security_model"],
        sources=["local_jsonl"],
        config_hash="sha256:test",
    )
    manifest = RunManifest(
        run=run,
        topics=[
            TopicSnapshot(id="agent_security_model", version="1.0.0", config_hash="sha256:test")
        ],
        adapter_versions={"local_jsonl": "0.1.0"},
        artifacts_written=1,
        raw_records_written=1,
    )
    assert manifest.run.id == "run_1"
