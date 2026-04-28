from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    id: str
    source: str
    source_id: str | None = None
    title: str
    url: str | None = None
    summary: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    collected_at: datetime
    raw_path: str | None = None
    normalized_hash: str
    source_response_hash: str | None = None
    topic_id: str
    topic_version: str
    config_hash: str
    run_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
