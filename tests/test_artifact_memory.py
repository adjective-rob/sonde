"""Tests for cross-run artifact memory and velocity scoring."""
from __future__ import annotations

from pathlib import Path

from sonde.engine.scoring import score_record
from sonde.models.topic import Topic
from sonde.registry.repository import RegistryRepository


def _make_topic() -> Topic:
    return Topic(
        id="mem_topic",
        name="Memory Topic",
        intent="Test memory",
        status="active",
        version="1.0.0",
        queries=["test query"],
        sources=[{"id": "local_jsonl", "enabled": True, "max_results": 10}],
        schedule={"interval_minutes": 1440},
    )


def test_mark_artifact_seen_first_time(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    result = repo.mark_artifact_seen(
        artifact_hash="hash_abc",
        topic_id="topic_1",
        source="github",
    )
    assert result["seen_count"] == 1
    assert result["is_new"] is True


def test_mark_artifact_seen_increments(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    repo.mark_artifact_seen(artifact_hash="hash_abc", topic_id="topic_1", source="github")
    result = repo.mark_artifact_seen(
        artifact_hash="hash_abc", topic_id="topic_1", source="github"
    )
    assert result["seen_count"] == 2
    assert result["is_new"] is False

    result = repo.mark_artifact_seen(
        artifact_hash="hash_abc", topic_id="topic_1", source="github"
    )
    assert result["seen_count"] == 3


def test_artifact_seen_stats(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    # Two unique artifacts
    repo.mark_artifact_seen(artifact_hash="hash_1", topic_id="topic_1", source="github")
    repo.mark_artifact_seen(artifact_hash="hash_2", topic_id="topic_1", source="github")
    # See hash_1 again
    repo.mark_artifact_seen(artifact_hash="hash_1", topic_id="topic_1", source="github")

    stats = repo.artifact_seen_stats("topic_1")
    assert stats["total_unique_artifacts"] == 2
    assert stats["recurring_artifacts"] == 1
    assert stats["new_artifacts"] == 1
    assert stats["max_seen_count"] == 2
    assert stats["novelty_ratio"] == 0.5


def test_artifact_seen_different_topics_independent(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    r1 = repo.mark_artifact_seen(artifact_hash="hash_x", topic_id="topic_a", source="github")
    r2 = repo.mark_artifact_seen(artifact_hash="hash_x", topic_id="topic_b", source="github")
    assert r1["seen_count"] == 1
    assert r2["seen_count"] == 1  # different topic, independent count


def test_score_record_novelty_decay() -> None:
    topic = _make_topic()
    # First time seen
    s1 = score_record(topic, "test title", "test summary", {}, seen_count=0)
    assert s1["novelty"] == 1.0
    # Seen once before
    s2 = score_record(topic, "test title", "test summary", {}, seen_count=1)
    assert s2["novelty"] == 0.6
    # Seen 3 times
    s3 = score_record(topic, "test title", "test summary", {}, seen_count=3)
    assert s3["novelty"] == 0.3
    # Seen many times
    s4 = score_record(topic, "test title", "test summary", {}, seen_count=10)
    assert s4["novelty"] == 0.1


def test_score_record_velocity() -> None:
    topic = _make_topic()
    # First run, no previous data
    s1 = score_record(
        topic, "test", "summary", {},
        previous_run_artifacts=0, current_run_artifacts=5,
    )
    assert s1["velocity"] == 1.0

    # Growing
    s2 = score_record(
        topic, "test", "summary", {},
        previous_run_artifacts=10, current_run_artifacts=15,
    )
    assert s2["velocity"] == 0.5

    # Shrinking
    s3 = score_record(
        topic, "test", "summary", {},
        previous_run_artifacts=10, current_run_artifacts=5,
    )
    assert s3["velocity"] == -0.5

    # Stable
    s4 = score_record(
        topic, "test", "summary", {},
        previous_run_artifacts=10, current_run_artifacts=10,
    )
    assert s4["velocity"] == 0.0
