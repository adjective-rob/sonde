"""Tests for the apply_diff MCP tool."""
from __future__ import annotations

from pathlib import Path

import yaml

from sonde.mcp_server.tools import apply_diff, create_topic_draft


def test_apply_diff_roundtrip(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(yaml.safe_dump({"topics": []}, sort_keys=False))

    # Step 1: Create a draft (returns proposed YAML)
    proposal = create_topic_draft(
        str(config),
        id="new_topic",
        name="New Topic",
        intent="Track new things",
        queries=["new query"],
        sources=["local_jsonl"],
    )
    assert "proposed" in proposal

    # Step 2: Apply the proposed YAML
    result = apply_diff(str(config), proposal["proposed"])
    assert result["applied"] is True
    assert result["topics_count"] == 1

    # Step 3: Verify file was written
    data = yaml.safe_load(config.read_text())
    assert len(data["topics"]) == 1
    assert data["topics"][0]["id"] == "new_topic"


def test_apply_diff_validates_before_writing(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(yaml.safe_dump({"topics": []}, sort_keys=False))

    # Invalid YAML
    result = apply_diff(str(config), "{{{{invalid yaml")
    assert "error" in result

    # Valid YAML but invalid topic (missing required fields)
    bad_yaml = yaml.safe_dump(
        {"topics": [{"id": "bad"}]}, sort_keys=False
    )
    result = apply_diff(str(config), bad_yaml)
    assert "error" in result

    # File should be unchanged
    data = yaml.safe_load(config.read_text())
    assert data["topics"] == []


def test_apply_diff_missing_topics_key(tmp_path: Path) -> None:
    config = tmp_path / "topics.yaml"
    config.write_text(yaml.safe_dump({"topics": []}, sort_keys=False))
    result = apply_diff(str(config), yaml.safe_dump({"something": "else"}))
    assert "error" in result


def test_apply_diff_file_not_found(tmp_path: Path) -> None:
    result = apply_diff(str(tmp_path / "nonexistent.yaml"), "topics: []")
    assert "error" in result
