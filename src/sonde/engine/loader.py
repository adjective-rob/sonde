from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from sonde.errors import ConfigLoadError, TopicNotFoundError
from sonde.models.topic import Topic, TopicPack


def load_raw_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigLoadError(f"Could not read {config_path}: {exc}") from exc

    try:
        data = json.loads(text) if config_path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigLoadError(f"Invalid config syntax in {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigLoadError("Config must be a mapping with a topics key")
    return data


def load_topic_pack(path: str | Path) -> TopicPack:
    data = load_raw_config(path)
    try:
        return TopicPack.model_validate(data)
    except ValidationError as exc:
        raise ConfigLoadError(str(exc)) from exc


def load_topics(path: str | Path) -> list[Topic]:
    return load_topic_pack(path).topics


def get_topic(topics: list[Topic], topic_id: str) -> Topic:
    for topic in topics:
        if topic.id == topic_id:
            return topic
    raise TopicNotFoundError(f"Topic not found: {topic_id}")
