from __future__ import annotations

from pathlib import Path
from typing import Any

from sonde.engine.loader import get_topic, load_topics

EXPECTED_RESOURCES = [
    "sonde://topics",
    "sonde://topics/{topic_id}",
    "sonde://topics/{topic_id}/versions",
    "sonde://topics/{topic_id}/quality",
    "sonde://sources",
    "sonde://runs",
    "sonde://runs/{run_id}",
    "sonde://artifacts",
    "sonde://artifacts/{artifact_id}",
    "sonde://manifests/{run_id}",
    "sonde://schema/topic",
    "sonde://schema/artifact",
]


def list_resource_templates() -> list[str]:
    return EXPECTED_RESOURCES


def read_resource(uri: str, *, config_path: str = "topics.yaml") -> Any:
    topics = load_topics(config_path) if Path(config_path).exists() else []
    if uri == "sonde://topics":
        return [
            topic.model_dump(mode="json", exclude={"queries", "aliases", "negative_terms"})
            for topic in topics
        ]
    if uri.startswith("sonde://topics/") and "/quality" not in uri and "/versions" not in uri:
        topic_id = uri.removeprefix("sonde://topics/")
        return get_topic(topics, topic_id).model_dump(mode="json")
    if uri == "sonde://sources":
        return sorted({source.id for topic in topics for source in topic.sources})
    if uri == "sonde://schema/topic":
        return Path("src/sonde/schema/topic.schema.json").read_text(encoding="utf-8")
    if uri == "sonde://schema/artifact":
        return Path("src/sonde/schema/artifact.schema.json").read_text(encoding="utf-8")
    return {"uri": uri, "status": "not_implemented_yet"}
