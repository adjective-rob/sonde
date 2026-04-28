from __future__ import annotations

from pathlib import Path
from typing import Any

from topicops.engine.loader import get_topic, load_topics

EXPECTED_RESOURCES = [
    "topicops://topics",
    "topicops://topics/{topic_id}",
    "topicops://topics/{topic_id}/versions",
    "topicops://topics/{topic_id}/quality",
    "topicops://sources",
    "topicops://runs",
    "topicops://runs/{run_id}",
    "topicops://artifacts",
    "topicops://artifacts/{artifact_id}",
    "topicops://manifests/{run_id}",
    "topicops://schema/topic",
    "topicops://schema/artifact",
]


def list_resource_templates() -> list[str]:
    return EXPECTED_RESOURCES


def read_resource(uri: str, *, config_path: str = "topics.yaml") -> Any:
    topics = load_topics(config_path) if Path(config_path).exists() else []
    if uri == "topicops://topics":
        return [
            topic.model_dump(mode="json", exclude={"queries", "aliases", "negative_terms"})
            for topic in topics
        ]
    if uri.startswith("topicops://topics/") and "/quality" not in uri and "/versions" not in uri:
        topic_id = uri.removeprefix("topicops://topics/")
        return get_topic(topics, topic_id).model_dump(mode="json")
    if uri == "topicops://sources":
        return sorted({source.id for topic in topics for source in topic.sources})
    if uri == "topicops://schema/topic":
        return Path("src/topicops/schema/topic.schema.json").read_text(encoding="utf-8")
    if uri == "topicops://schema/artifact":
        return Path("src/topicops/schema/artifact.schema.json").read_text(encoding="utf-8")
    return {"uri": uri, "status": "not_implemented_yet"}
