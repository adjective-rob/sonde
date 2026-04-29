from __future__ import annotations

import asyncio
import difflib
import json
from pathlib import Path
from typing import Any

import yaml

from sonde.engine.dedupe import dedupe_topics
from sonde.engine.diff import diff_topics
from sonde.engine.linter import lint_config
from sonde.engine.loader import get_topic, load_topics
from sonde.engine.runner import run_topics
from sonde.engine.simulate import simulate_topic
from sonde.models.source import TopicSourceConfig
from sonde.models.topic import ScheduleConfig, Topic, TopicStatus

EXPECTED_TOOLS = [
    "lint_topics",
    "dedupe_topics",
    "find_semantic_overlap",
    "diff_topics",
    "simulate_topic",
    "estimate_collection_cost",
    "run_topic_dry_run",
    "create_topic_draft",
    "update_topic_draft",
    "deprecate_topic",
    "promote_topic",
    "rollback_topic_version",
    "generate_aliases",
    "generate_negative_terms",
    "summarize_topic_health",
    "apply_diff",
    "artifact_memory",
]


def list_tools() -> list[str]:
    return EXPECTED_TOOLS


# ---------------------------------------------------------------------------
# Existing tools (improved)
# ---------------------------------------------------------------------------


def lint_topics(config_path: str) -> dict[str, Any]:
    return lint_config(config_path).as_dict()


def dedupe_topics_tool(config_path: str, include_near_overlaps: bool = True) -> dict[str, Any]:
    return dedupe_topics(load_topics(config_path), include_near=include_near_overlaps).as_dict()


def find_semantic_overlap(config_path: str) -> dict[str, Any]:
    """Detect semantic overlap between all topics using fuzzy matching."""
    return dedupe_topics(load_topics(config_path), include_near=True).as_dict()


def diff_topics_tool(old_config_path: str, new_config_path: str) -> dict[str, Any]:
    return diff_topics(load_topics(old_config_path), load_topics(new_config_path)).as_dict()


def simulate_topic_tool(
    config_path: str, topic_id: str, source: str, limit: int = 20
) -> dict[str, Any]:
    topic = get_topic(load_topics(config_path), topic_id)
    return asyncio.run(simulate_topic(topic, source, limit=limit)).as_dict()


def run_topic_dry_run(
    config_path: str,
    topic_id: str,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a dry run — always safe, never writes artifacts."""
    topic = get_topic(load_topics(config_path), topic_id)
    manifest = asyncio.run(
        run_topics(
            [topic],
            source_filter=sources[0] if sources else None,
            dry_run=True,
            db_path=".sonde/sonde.db",
            artifact_path=".sonde/artifacts",
        )
    )
    return manifest.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Topic lifecycle tools
# ---------------------------------------------------------------------------


def _read_and_parse(config_path: str) -> tuple[Path, str, dict[str, Any]]:
    path = Path(config_path)
    original = path.read_text(encoding="utf-8")
    payload = yaml.safe_load(original) or {"topics": []}
    return path, original, payload


def _write_and_diff(path: Path, original: str, payload: dict[str, Any]) -> dict[str, Any]:
    updated = yaml.safe_dump(payload, sort_keys=False)
    diff = "\n".join(
        difflib.unified_diff(original.splitlines(), updated.splitlines(), lineterm="")
    )
    return {"diff": diff, "proposed": updated}


def create_topic_draft(
    config_path: str,
    id: str,
    name: str,
    intent: str,
    queries: list[str],
    sources: list[str],
) -> dict[str, Any]:
    """Create a new draft topic. Returns the proposed diff without writing."""
    path, original, payload = _read_and_parse(config_path)
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
    return _write_and_diff(path, original, payload)


def update_topic_draft(config_path: str, topic_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    """Modify a topic. Returns the proposed diff without writing."""
    path, original, payload = _read_and_parse(config_path)
    for topic in payload.get("topics", []):
        if topic.get("id") == topic_id:
            topic.update(patch)
            break
    result = _write_and_diff(path, original, payload)
    result["version_bump_warning"] = "Review whether this patch requires a version bump."
    return result


def deprecate_topic(
    config_path: str,
    topic_id: str,
    reason: str,
    replacement_id: str | None = None,
) -> dict[str, Any]:
    """Transition a topic to deprecated status. Returns proposed diff."""
    path, original, payload = _read_and_parse(config_path)
    found = False
    for topic in payload.get("topics", []):
        if topic.get("id") == topic_id:
            topic["status"] = "deprecated"
            topic.setdefault("metadata", {})["deprecation_reason"] = reason
            if replacement_id:
                topic["metadata"]["replaced_by"] = replacement_id
            found = True
            break
    if not found:
        return {"error": f"Topic not found: {topic_id}"}
    result = _write_and_diff(path, original, payload)
    result["reason"] = reason
    result["replacement_id"] = replacement_id
    return result


def promote_topic(config_path: str, topic_id: str, owner: str | None = None) -> dict[str, Any]:
    """Promote a draft topic to active. Returns proposed diff."""
    path, original, payload = _read_and_parse(config_path)
    found = False
    for topic in payload.get("topics", []):
        if topic.get("id") == topic_id:
            current = topic.get("status", "draft")
            if current not in ("draft", "paused"):
                return {"error": f"Cannot promote topic with status '{current}'"}
            topic["status"] = "active"
            if owner:
                topic["owner"] = owner
            found = True
            break
    if not found:
        return {"error": f"Topic not found: {topic_id}"}
    return _write_and_diff(path, original, payload)


def rollback_topic_version(
    config_path: str,
    topic_id: str,
    target_version: str,
    db_path: str = ".sonde/sonde.db",
) -> dict[str, Any]:
    """Roll back a topic to a previous version from the registry."""
    from sonde.registry.repository import RegistryRepository

    repo = RegistryRepository(db_path)
    version_config = repo.get_topic_version(topic_id, target_version)
    if version_config is None:
        return {"error": f"Version {target_version} not found for topic {topic_id}"}

    path, original, payload = _read_and_parse(config_path)
    restored = json.loads(version_config)
    for i, topic in enumerate(payload.get("topics", [])):
        if topic.get("id") == topic_id:
            payload["topics"][i] = restored
            break
    result = _write_and_diff(path, original, payload)
    result["rolled_back_to"] = target_version
    return result


# ---------------------------------------------------------------------------
# Generation tools
# ---------------------------------------------------------------------------


def generate_aliases(topic_id: str, intent: str, queries: list[str]) -> dict[str, Any]:
    """Generate query aliases from intent and existing queries."""
    words: set[str] = set()
    for text in [intent, *queries]:
        cleaned = text.replace(",", "").replace(".", "").split()
        words.update(w.lower() for w in cleaned if len(w) > 3)

    # Build bigrams from intent for more useful aliases
    cleaned_intent = intent.replace(",", "").replace(".", "").split()
    intent_words = [w.lower() for w in cleaned_intent if len(w) > 3]
    bigrams = [f"{intent_words[i]} {intent_words[i+1]}" for i in range(len(intent_words) - 1)]

    # Filter out aliases that already exist as queries
    existing = {q.lower() for q in queries}
    candidate_aliases = [b for b in bigrams if b not in existing]

    return {
        "topic_id": topic_id,
        "suggested_aliases": candidate_aliases[:10],
        "suggested_tags": sorted(words)[:10],
    }


def generate_negative_terms(
    topic_id: str,
    intent: str,
    queries: list[str],
) -> dict[str, Any]:
    """Generate negative terms to reduce noise for a topic.

    Uses heuristic patterns for common false-positive categories.
    """
    NOISE_PATTERNS: dict[str, list[str]] = {
        "agent": ["real estate agent", "insurance agent", "travel agent", "booking agent"],
        "model": ["fashion model", "model railroad", "model train", "scale model"],
        "security": ["security guard", "security officer", "home security"],
        "network": ["social network", "network marketing", "networking event"],
        "monitor": ["baby monitor", "monitor lizard", "studio monitor"],
        "intelligence": ["emotional intelligence", "business intelligence"],
        "protocol": ["protocol officer", "diplomatic protocol"],
        "framework": ["legal framework", "regulatory framework"],
        "pipeline": ["oil pipeline", "gas pipeline"],
        "token": ["token gesture", "token economy"],
    }

    query_words: set[str] = set()
    for q in queries:
        query_words.update(w.lower() for w in q.split())

    suggestions: list[str] = []
    for trigger, negatives in NOISE_PATTERNS.items():
        if trigger in query_words or trigger in intent.lower():
            suggestions.extend(negatives)

    # Deduplicate against queries
    query_lower = {q.lower() for q in queries}
    suggestions = [s for s in suggestions if s.lower() not in query_lower]

    return {
        "topic_id": topic_id,
        "suggested_negative_terms": sorted(set(suggestions))[:15],
        "note": "Review suggestions — not all will apply to your topic.",
    }


# ---------------------------------------------------------------------------
# Analysis tools
# ---------------------------------------------------------------------------


def estimate_collection_cost(
    config_path: str, topic_id: str, interval_hours: int = 24
) -> dict[str, Any]:
    """Estimate API requests, artifacts, and storage for a topic."""
    topic = get_topic(load_topics(config_path), topic_id)
    requests = {source.id: len(topic.queries) for source in topic.sources if source.enabled}
    artifacts = {source.id: source.max_results for source in topic.sources if source.enabled}
    runs_per_day = max(1, 24 * 60 // topic.schedule.interval_minutes)
    daily_requests = {k: v * runs_per_day for k, v in requests.items()}
    daily_artifacts = {k: v * runs_per_day for k, v in artifacts.items()}
    return {
        "topic_id": topic_id,
        "interval_hours": interval_hours,
        "schedule_interval_minutes": topic.schedule.interval_minutes,
        "runs_per_day": runs_per_day,
        "requests_per_run": requests,
        "artifacts_per_run": artifacts,
        "daily_requests": daily_requests,
        "daily_artifacts": daily_artifacts,
        "storage_estimate_bytes_per_day": sum(daily_artifacts.values()) * 4096,
        "rate_limit_warnings": [],
    }


def apply_diff(config_path: str, proposed_yaml: str) -> dict[str, Any]:
    """Apply a previously proposed diff to the config file.

    This is the human-in-the-loop step: an agent proposes changes via
    create_topic_draft/update_topic_draft/deprecate_topic/promote_topic,
    the human reviews the diff, then calls apply_diff to write it.
    """
    path = Path(config_path)
    if not path.exists():
        return {"error": f"Config file not found: {config_path}"}

    # Validate the proposed YAML before writing
    try:
        parsed = yaml.safe_load(proposed_yaml)
    except yaml.YAMLError as exc:
        return {"error": f"Invalid YAML: {exc}"}

    if not isinstance(parsed, dict) or "topics" not in parsed:
        return {"error": "Proposed YAML must contain a 'topics' key"}

    # Validate all topics parse correctly
    from sonde.models.topic import TopicPack

    try:
        TopicPack.model_validate(parsed)
    except Exception as exc:
        return {"error": f"Proposed topics failed validation: {exc}"}

    original = path.read_text(encoding="utf-8")
    path.write_text(proposed_yaml, encoding="utf-8")
    return {
        "applied": True,
        "config_path": config_path,
        "topics_count": len(parsed["topics"]),
        "diff": "\n".join(
            difflib.unified_diff(
                original.splitlines(), proposed_yaml.splitlines(), lineterm=""
            )
        ),
    }


def artifact_memory(
    topic_id: str,
    db_path: str = ".sonde/sonde.db",
) -> dict[str, Any]:
    """Return artifact memory stats — how many unique vs recurring artifacts."""
    from sonde.registry.repository import RegistryRepository

    repo = RegistryRepository(db_path)
    return repo.artifact_seen_stats(topic_id)


def summarize_topic_health(
    config_path: str,
    topic_id: str,
    db_path: str = ".sonde/sonde.db",
) -> dict[str, Any]:
    """Health report: yield, noise, staleness, source coverage."""
    from sonde.registry.repository import RegistryRepository

    topic = get_topic(load_topics(config_path), topic_id)
    repo = RegistryRepository(db_path)
    health = repo.topic_health(topic_id)

    # Compute coverage: which configured sources have actually produced artifacts
    configured_sources = {s.id for s in topic.sources if s.enabled}
    active_sources = set(health.get("sources_with_artifacts", []))
    missing_sources = sorted(configured_sources - active_sources)

    return {
        "topic_id": topic_id,
        "status": topic.status.value,
        "version": topic.version,
        "total_runs": health.get("total_runs", 0),
        "total_artifacts": health.get("total_artifacts", 0),
        "total_errors": health.get("total_errors", 0),
        "last_run_at": health.get("last_run_at"),
        "configured_sources": sorted(configured_sources),
        "active_sources": sorted(active_sources),
        "missing_sources": missing_sources,
        "has_negative_terms": len(topic.negative_terms) > 0,
        "query_count": len(topic.queries),
        "alias_count": len(topic.aliases),
        "governance": {
            "owner": topic.owner,
            "last_reviewed_at": str(topic.governance.last_reviewed_at)
            if topic.governance.last_reviewed_at
            else None,
            "review_cycle_days": topic.governance.review_cycle_days,
        },
    }
