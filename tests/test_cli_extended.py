"""Tests for the extended CLI commands: health, inspect."""
from __future__ import annotations

from datetime import UTC, datetime

from sonde.cli import app
from sonde.models.artifact import Artifact
from sonde.models.run import CollectionRun, RunStatus
from sonde.models.topic import Topic
from sonde.registry.repository import RegistryRepository


def test_health_command(runner, examples_path, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SONDE_DB_PATH", str(tmp_path / "sonde.db"))
    monkeypatch.setenv("SONDE_ARTIFACT_PATH", str(tmp_path / "artifacts"))
    result = runner.invoke(
        app,
        ["health", str(examples_path), "--topic", "agent_security_model"],
    )
    assert result.exit_code == 0
    assert "agent_security_model" in result.output
    assert "Runs:" in result.output
    assert "Novelty ratio:" in result.output


def test_health_command_json(runner, examples_path, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SONDE_DB_PATH", str(tmp_path / "sonde.db"))
    monkeypatch.setenv("SONDE_ARTIFACT_PATH", str(tmp_path / "artifacts"))
    result = runner.invoke(
        app,
        ["health", str(examples_path), "--topic", "agent_security_model", "--json"],
    )
    assert result.exit_code == 0
    assert "artifact_memory" in result.output


def test_inspect_command(runner, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SONDE_DB_PATH", str(tmp_path / "sonde.db"))
    monkeypatch.setenv("SONDE_ARTIFACT_PATH", str(tmp_path / "artifacts"))

    # Set up a real artifact in the registry
    repo = RegistryRepository(tmp_path / "sonde.db")
    topic = Topic(
        id="inspect_topic",
        name="Inspect Test",
        intent="Test inspect",
        status="active",
        version="1.0.0",
        queries=["inspect test"],
        sources=[{"id": "local_jsonl", "enabled": True, "max_results": 10}],
        schedule={"interval_minutes": 1440},
    )
    repo.upsert_topic(topic, "hash1")
    run = CollectionRun(
        id="run_inspect",
        started_at=datetime.now(UTC),
        status=RunStatus.completed,
        topic_ids=["inspect_topic"],
        sources=["local_jsonl"],
        config_hash="hash1",
        artifact_count=1,
    )
    repo.insert_run(run)
    artifact = Artifact(
        id="art_inspect_001",
        source="local_jsonl",
        title="Inspectable Artifact",
        url="https://example.com/test",
        collected_at=datetime.now(UTC),
        normalized_hash="nhash_inspect",
        topic_id="inspect_topic",
        topic_version="1.0.0",
        config_hash="hash1",
        run_id="run_inspect",
    )
    repo.insert_artifacts([artifact])

    result = runner.invoke(app, ["inspect", "art_inspect_001"])
    assert result.exit_code == 0
    assert "Inspectable Artifact" in result.output
    assert "local_jsonl" in result.output
    assert "run_inspect" in result.output


def test_inspect_not_found(runner, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SONDE_DB_PATH", str(tmp_path / "sonde.db"))
    result = runner.invoke(app, ["inspect", "nonexistent"])
    assert result.exit_code == 1
    assert "Error" in result.output
