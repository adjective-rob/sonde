"""Tests for the expanded registry repository methods."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sonde.models.artifact import Artifact
from sonde.models.run import CollectionRun, RunStatus
from sonde.models.topic import Topic
from sonde.registry.repository import RegistryRepository


def _make_topic() -> Topic:
    return Topic(
        id="test_topic",
        name="Test Topic",
        intent="Test intent",
        status="active",
        version="1.0.0",
        owner="tester",
        queries=["test query"],
        sources=[{"id": "local_jsonl", "enabled": True, "max_results": 10}],
        schedule={"interval_minutes": 1440},
    )


def test_topic_versions(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    topic = _make_topic()
    repo.upsert_topic(topic, "hash_v1")
    topic.version = "1.1.0"
    repo.upsert_topic(topic, "hash_v2")

    versions = repo.topic_versions("test_topic")
    assert len(versions) == 2
    version_strings = {v["version"] for v in versions}
    assert "1.0.0" in version_strings
    assert "1.1.0" in version_strings


def test_get_topic_version(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    topic = _make_topic()
    repo.upsert_topic(topic, "hash_v1")

    config_json = repo.get_topic_version("test_topic", "1.0.0")
    assert config_json is not None
    parsed = json.loads(config_json)
    assert parsed["id"] == "test_topic"

    missing = repo.get_topic_version("test_topic", "99.0.0")
    assert missing is None


def test_topic_health(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    topic = _make_topic()
    repo.upsert_topic(topic, "hash1")

    run = CollectionRun(
        id="run_001",
        started_at=datetime.now(UTC),
        status=RunStatus.completed,
        topic_ids=["test_topic"],
        sources=["local_jsonl"],
        config_hash="hash1",
        artifact_count=2,
    )
    repo.insert_run(run)

    artifact = Artifact(
        id="art_001",
        source="local_jsonl",
        title="Test Artifact",
        collected_at=datetime.now(UTC),
        normalized_hash="nhash1",
        topic_id="test_topic",
        topic_version="1.0.0",
        config_hash="hash1",
        run_id="run_001",
    )
    repo.insert_artifacts([artifact])

    health = repo.topic_health("test_topic")
    assert health["topic_id"] == "test_topic"
    assert health["total_runs"] == 1
    assert health["total_artifacts"] == 1
    assert "local_jsonl" in health["sources_with_artifacts"]


def test_recent_runs(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    run = CollectionRun(
        id="run_002",
        started_at=datetime.now(UTC),
        status=RunStatus.completed,
        topic_ids=["topic_a"],
        sources=["github"],
        config_hash="hash2",
    )
    repo.insert_run(run)

    runs = repo.recent_runs(limit=10)
    assert len(runs) == 1
    assert runs[0]["id"] == "run_002"
    assert runs[0]["topic_ids"] == ["topic_a"]


def test_get_run(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    run = CollectionRun(
        id="run_003",
        started_at=datetime.now(UTC),
        status=RunStatus.completed,
        topic_ids=["topic_b"],
        sources=["arxiv"],
        config_hash="hash3",
    )
    repo.insert_run(run)

    result = repo.get_run("run_003")
    assert result["id"] == "run_003"

    missing = repo.get_run("nonexistent")
    assert "error" in missing


def test_get_artifact(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    artifact = Artifact(
        id="art_002",
        source="github",
        title="Test Repo",
        url="https://github.com/test/repo",
        collected_at=datetime.now(UTC),
        normalized_hash="nhash2",
        topic_id="test_topic",
        topic_version="1.0.0",
        config_hash="hash1",
        run_id="run_001",
    )
    repo.insert_artifacts([artifact])

    result = repo.get_artifact("art_002")
    assert result["id"] == "art_002"
    assert result["title"] == "Test Repo"

    missing = repo.get_artifact("nonexistent")
    assert "error" in missing


def test_artifact_lineage(tmp_path: Path) -> None:
    repo = RegistryRepository(tmp_path / "test.db")
    topic = _make_topic()
    repo.upsert_topic(topic, "hash1")

    run = CollectionRun(
        id="run_lineage",
        started_at=datetime.now(UTC),
        status=RunStatus.completed,
        topic_ids=["test_topic"],
        sources=["local_jsonl"],
        config_hash="hash1",
    )
    repo.insert_run(run)

    artifact = Artifact(
        id="art_lineage",
        source="local_jsonl",
        title="Lineage Test",
        collected_at=datetime.now(UTC),
        normalized_hash="nhash_lineage",
        topic_id="test_topic",
        topic_version="1.0.0",
        config_hash="hash1",
        run_id="run_lineage",
    )
    repo.insert_artifacts([artifact])

    lineage = repo.artifact_lineage("art_lineage")
    assert lineage["artifact"]["id"] == "art_lineage"
    assert lineage["run"]["id"] == "run_lineage"
    assert lineage["topic_version"] == "1.0.0"
    assert lineage["topic_config"] is not None
