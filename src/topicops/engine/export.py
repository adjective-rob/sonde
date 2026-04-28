from __future__ import annotations

import json
from pathlib import Path

import yaml

from topicops.models.topic import Topic


def export_topic_pack(
    topics: list[Topic], output_path: str | Path, *, tag: str | None = None, fmt: str = "yaml"
) -> Path:
    selected = [topic for topic in topics if tag is None or tag in topic.tags]
    payload = {"topics": [topic.model_dump(mode="json", exclude_none=True) for topic in selected]}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json" or path.suffix == ".json":
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path
