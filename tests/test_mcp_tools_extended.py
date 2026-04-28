"""Tests for the expanded MCP tool surface."""
from __future__ import annotations

from pathlib import Path

import yaml

from sonde.mcp_server.tools import (
    create_topic_draft,
    deprecate_topic,
    estimate_collection_cost,
    generate_aliases,
    generate_negative_terms,
    lint_topics,
    promote_topic,
    summarize_topic_health,
)


def test_lint_topics(examples_path: Path) -> None:
    result = lint_topics(str(examples_path))
    assert result["ok"] is True
    assert result["topics_parsed"] >= 1


def test_create_topic_draft_returns_diff(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(yaml.safe_dump({"topics": []}, sort_keys=False))
    result = create_topic_draft(
        str(config),
        id="test_topic",
        name="Test Topic",
        intent="Track testing frameworks",
        queries=["test framework"],
        sources=["local_jsonl"],
    )
    assert "diff" in result
    assert "proposed" in result
    assert "test_topic" in result["proposed"]
    # File should NOT have been modified (diff-only)
    assert yaml.safe_load(config.read_text())["topics"] == []


def test_deprecate_topic_returns_diff(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {
                        "id": "old_topic",
                        "name": "Old",
                        "intent": "Old stuff",
                        "status": "active",
                        "version": "1.0.0",
                        "queries": ["old query"],
                        "sources": [{"id": "local_jsonl", "enabled": True, "max_results": 10}],
                        "schedule": {"interval_minutes": 1440},
                    }
                ]
            },
            sort_keys=False,
        )
    )
    result = deprecate_topic(str(config), "old_topic", "Too noisy", replacement_id="new_topic")
    assert "diff" in result
    assert result["reason"] == "Too noisy"
    assert result["replacement_id"] == "new_topic"
    # File should NOT have been modified
    data = yaml.safe_load(config.read_text())
    assert data["topics"][0]["status"] == "active"


def test_deprecate_topic_not_found(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(yaml.safe_dump({"topics": []}, sort_keys=False))
    result = deprecate_topic(str(config), "nonexistent", "reason")
    assert "error" in result


def test_promote_topic_returns_diff(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {
                        "id": "draft_topic",
                        "name": "Draft",
                        "intent": "Draft stuff",
                        "status": "draft",
                        "version": "0.1.0",
                        "queries": ["draft query"],
                        "sources": [{"id": "local_jsonl", "enabled": True, "max_results": 10}],
                        "schedule": {"interval_minutes": 1440},
                    }
                ]
            },
            sort_keys=False,
        )
    )
    result = promote_topic(str(config), "draft_topic", owner="testuser")
    assert "diff" in result
    assert "active" in result["proposed"]


def test_promote_rejects_already_active(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {
                        "id": "active_topic",
                        "name": "Active",
                        "intent": "Active stuff",
                        "status": "active",
                        "version": "1.0.0",
                        "queries": ["active query"],
                        "sources": [{"id": "local_jsonl", "enabled": True, "max_results": 10}],
                        "schedule": {"interval_minutes": 1440},
                    }
                ]
            },
            sort_keys=False,
        )
    )
    result = promote_topic(str(config), "active_topic")
    assert "error" in result


def test_generate_aliases() -> None:
    result = generate_aliases(
        "test_topic",
        "Track emerging work on identity and permissioning for AI agents",
        ["agent security model", "AI agent permissioning"],
    )
    assert result["topic_id"] == "test_topic"
    assert isinstance(result["suggested_aliases"], list)
    assert isinstance(result["suggested_tags"], list)


def test_generate_negative_terms() -> None:
    result = generate_negative_terms(
        "test_topic",
        "Track AI agent security models",
        ["agent security model"],
    )
    assert result["topic_id"] == "test_topic"
    assert isinstance(result["suggested_negative_terms"], list)
    # Should suggest "real estate agent" etc. since "agent" is in queries
    assert any("agent" in t for t in result["suggested_negative_terms"])


def test_estimate_collection_cost(examples_path: Path) -> None:
    result = estimate_collection_cost(str(examples_path), "agent_security_model")
    assert result["topic_id"] == "agent_security_model"
    assert "runs_per_day" in result
    assert "daily_requests" in result
    assert "storage_estimate_bytes_per_day" in result


def test_summarize_topic_health(examples_path: Path, tmp_path: Path) -> None:
    result = summarize_topic_health(
        str(examples_path),
        "agent_security_model",
        db_path=str(tmp_path / "test.db"),
    )
    assert result["topic_id"] == "agent_security_model"
    assert result["status"] == "active"
    assert "total_runs" in result
    assert "configured_sources" in result
    assert "governance" in result
