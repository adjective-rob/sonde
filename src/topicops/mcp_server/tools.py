from __future__ import annotations

import asyncio
import difflib
from pathlib import Path
from typing import Any

import yaml

from topicops.engine.dedupe import dedupe_topics
from topicops.engine.diff import diff_topics
from topicops.engine.linter import lint_config
from topicops.engine.loader import get_topic, load_topics
from topicops.engine.runner import run_topics
from topicops.engine.simulate import simulate_topic
from topicops.models.source import TopicSourceConfig
from topicops.models.topic import ScheduleConfig, Topic, TopicStatus

EXPECTED_TOOLS = [
    "lint_topics",
    "dedupe_topics",
    "diff_topics",
    "simulate_topic",
    "run_topic",
    "create_topic_draft",
    "update_topic_draft",
    "generate_topic_variants",
    "estimate_cost",
    "export_topic_pack",
]


def list_tools() -> list[str]:
    return EXPECTED_TOOLS


def lint_topics(config_path: str) -> dict[str, Any]:
    return lint_config(config_path).as_dict()


def dedupe_topics_tool(config_path: str, include_near_overlaps: bool = True) -> dict[str, Any]:
    return dedupe_topics(load_topics(config_path), include_near=include_near_overlaps).as_dict()


def diff_topics_tool(old_config_path: str, new_config_path: str) -> dict[str, Any]:
    return diff_topics(load_topics(old_config_path), load_topics(new_config_path)).as_dict()


def simulate_topic_tool(
    config_path: str, topic_id: str, source: str, limit: int = 20
) -> dict[str, Any]:
    topic = get_topic(load_topics(config_path), topic_id)
    return asyncio.run(simulate_topic(topic, source, limit=limit)).as_dict()


def run_topic_tool(
    config_path: str,
    topic_id: str,
    sources: list[str] | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    topic = get_topic(load_topics(config_path), topic_id)
    manifest = asyncio.run(
        run_topics(
            [topic],
            source_filter=sources[0] if sources else None,
            dry_run=dry_run,
            db_path=".topicops/topicops.db",
            artifact_path=".topicops/artifacts",
        )
    )
    return manifest.model_dump(mode="json")


def create_topic_draft(
    config_path: str,
    id: str,
    name: str,
    intent: str,
    queries: list[str],
    sources: list[str],
) -> dict[str, Any]:
    path = Path(config_path)
    original = path.read_text(encoding="utf-8")
    payload = yaml.safe_load(original) or {"topics": []}
    topic = Topic(
        id=id,
        name=name,
        intent=intent,
        status=TopicStatus.draft,
        version="0.1.0",
        queries=queries,
        sources=[TopicSourceConfig(id=source, enabled=True, max_results=10) for source in sources],
        schedule=ScheduleConfig(interval_minutes=1440),
    )
    payload.setdefault("topics", []).append(topic.model_dump(mode="json", exclude_none=True))
    updated = yaml.safe_dump(payload, sort_keys=False)
    path.write_text(updated, encoding="utf-8")
    return {
        "diff": "\n".join(
            difflib.unified_diff(original.splitlines(), updated.splitlines(), lineterm="")
        )
    }


def update_topic_draft(config_path: str, topic_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    path = Path(config_path)
    original = path.read_text(encoding="utf-8")
    payload = yaml.safe_load(original) or {"topics": []}
    for topic in payload.get("topics", []):
        if topic.get("id") == topic_id:
            topic.update(patch)
            break
    updated = yaml.safe_dump(payload, sort_keys=False)
    path.write_text(updated, encoding="utf-8")
    return {
        "version_bump_warning": "Review whether this patch requires a version bump.",
        "diff": "\n".join(
            difflib.unified_diff(original.splitlines(), updated.splitlines(), lineterm="")
        ),
    }


def generate_topic_variants(topic_id: str, intent: str, count: int = 10) -> dict[str, Any]:
    words = [word for word in intent.lower().replace(",", "").split() if len(word) > 3]
    return {
        "topic_id": topic_id,
        "queries": [f"{' '.join(words[:3])} {index}" for index in range(1, count + 1)],
        "aliases": sorted(set(words[:count])),
        "negative_terms": ["jobs", "crm", "sales"],
        "sources": ["github", "arxiv", "local_jsonl"],
    }


def estimate_cost(config_path: str, topic_id: str, interval_hours: int = 24) -> dict[str, Any]:
    topic = get_topic(load_topics(config_path), topic_id)
    requests = {source.id: len(topic.queries) for source in topic.sources if source.enabled}
    artifacts = {source.id: source.max_results for source in topic.sources if source.enabled}
    return {
        "topic_id": topic_id,
        "interval_hours": interval_hours,
        "estimated_requests": requests,
        "estimated_artifacts": artifacts,
        "rate_limit_warnings": [],
        "storage_estimate_bytes": sum(artifacts.values()) * 4096,
    }
