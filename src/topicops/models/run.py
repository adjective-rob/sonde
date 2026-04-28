from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from topicops.models.topic import TopicSnapshot


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class CollectionRun(BaseModel):
    id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: RunStatus
    topic_ids: list[str]
    sources: list[str]
    config_hash: str
    artifact_count: int = 0
    error_count: int = 0
    dry_run: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunError(BaseModel):
    topic_id: str | None = None
    source: str | None = None
    error_type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunManifest(BaseModel):
    run: CollectionRun
    topics: list[TopicSnapshot]
    adapter_versions: dict[str, str]
    artifacts_written: int
    raw_records_written: int
    errors: list[RunError] = Field(default_factory=list)
