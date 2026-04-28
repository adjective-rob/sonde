"""Tests for the expanded MCP resource surface."""
from __future__ import annotations

from pathlib import Path

from sonde.mcp_server.resources import list_resource_templates, read_resource


def test_resource_templates_complete() -> None:
    templates = list_resource_templates()
    assert "sonde://topics" in templates
    assert "sonde://topics/{topic_id}" in templates
    assert "sonde://topics/{topic_id}/versions" in templates
    assert "sonde://topics/{topic_id}/quality" in templates
    assert "sonde://sources" in templates
    assert "sonde://runs" in templates
    assert "sonde://runs/{run_id}" in templates
    assert "sonde://artifacts/{artifact_id}" in templates
    assert "sonde://lineage/artifact/{artifact_id}" in templates
    assert "sonde://diffs/{from_version}/{to_version}" in templates
    assert "sonde://schema/topic" in templates
    assert "sonde://schema/artifact" in templates


def test_read_topics(examples_path: Path) -> None:
    result = read_resource("sonde://topics", config_path=str(examples_path))
    assert isinstance(result, list)
    assert len(result) >= 1
    topic = result[0]
    assert "id" in topic
    assert "status" in topic
    assert "query_count" in topic
    assert "source_count" in topic


def test_read_single_topic(examples_path: Path) -> None:
    result = read_resource(
        "sonde://topics/agent_security_model", config_path=str(examples_path)
    )
    assert result["id"] == "agent_security_model"
    assert "queries" in result


def test_read_sources(examples_path: Path) -> None:
    result = read_resource("sonde://sources", config_path=str(examples_path))
    assert isinstance(result, list)
    assert "local_jsonl" in result


def test_read_runs_empty(tmp_path: Path) -> None:
    result = read_resource(
        "sonde://runs",
        config_path=str(tmp_path / "nonexistent.yaml"),
        db_path=str(tmp_path / "test.db"),
    )
    assert isinstance(result, list)
    assert len(result) == 0


def test_read_topic_versions(examples_path: Path, tmp_path: Path) -> None:
    result = read_resource(
        "sonde://topics/agent_security_model/versions",
        config_path=str(examples_path),
        db_path=str(tmp_path / "test.db"),
    )
    assert isinstance(result, list)


def test_read_topic_quality(examples_path: Path, tmp_path: Path) -> None:
    result = read_resource(
        "sonde://topics/agent_security_model/quality",
        config_path=str(examples_path),
        db_path=str(tmp_path / "test.db"),
    )
    assert "topic_id" in result
    assert "total_runs" in result


def test_read_unknown_resource() -> None:
    result = read_resource("sonde://unknown/path")
    assert "error" in result


def test_read_artifact_not_found(tmp_path: Path) -> None:
    result = read_resource(
        "sonde://artifacts/nonexistent-id",
        config_path=str(tmp_path / "nonexistent.yaml"),
        db_path=str(tmp_path / "test.db"),
    )
    assert "error" in result
