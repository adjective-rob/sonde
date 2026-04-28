from datetime import UTC, datetime

from topicops.adapters.base import RawSourceRecord
from topicops.adapters.github import GitHubAdapter
from topicops.engine.loader import load_topics


def test_github_normalize(examples_path) -> None:
    topic = load_topics(examples_path)[0]
    record = RawSourceRecord(
        source="github",
        source_id="1",
        title="example/repo",
        url="https://github.com/example/repo",
        raw={"id": 1, "full_name": "example/repo", "html_url": "https://github.com/example/repo"},
        fetched_at=datetime.now(UTC),
        query="agent security model",
        response_hash="sha256:test",
    )
    artifact = GitHubAdapter().normalize(record, topic, "run_1", "sha256:config")
    assert artifact.source == "github"
