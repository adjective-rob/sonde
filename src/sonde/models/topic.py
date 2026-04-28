from __future__ import annotations

import re
from datetime import date
from enum import StrEnum

import semver
from pydantic import BaseModel, Field, field_validator, model_validator

from sonde.engine.lineage import normalize_text
from sonde.models.scoring import ScoringConfig
from sonde.models.source import TopicSourceConfig


class TopicStatus(StrEnum):
    draft = "draft"
    active = "active"
    paused = "paused"
    deprecated = "deprecated"
    archived = "archived"


class TopicPriority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ScheduleConfig(BaseModel):
    interval_minutes: int = Field(default=1440, ge=1)


class GovernanceConfig(BaseModel):
    created_at: date | None = None
    last_reviewed_at: date | None = None
    review_cycle_days: int = Field(default=30, ge=1)
    reviewers: list[str] = Field(default_factory=list)


class LineageConfig(BaseModel):
    retain_config_hash: bool = True
    retain_source_response_hash: bool = True


class Topic(BaseModel):
    id: str
    name: str
    description: str | None = None
    intent: str
    status: TopicStatus = TopicStatus.draft
    priority: TopicPriority = TopicPriority.medium
    version: str
    owner: str | None = None
    queries: list[str]
    aliases: list[str] = Field(default_factory=list)
    negative_terms: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    sources: list[TopicSourceConfig]
    schedule: ScheduleConfig
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    lineage: LineageConfig = Field(default_factory=LineageConfig)

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
            raise ValueError(
                "id must be slug-like lowercase letters, numbers, underscores, hyphens"
            )
        return value

    @field_validator("version")
    @classmethod
    def valid_semver(cls, value: str) -> str:
        try:
            semver.Version.parse(value)
        except ValueError as exc:
            raise ValueError("version must be valid semver") from exc
        return value

    @field_validator("queries")
    @classmethod
    def non_empty_queries(cls, value: list[str]) -> list[str]:
        cleaned = [query for query in value if query and query.strip()]
        if not cleaned:
            raise ValueError("queries must contain at least one non-empty string")
        return value

    @model_validator(mode="after")
    def validate_topic(self) -> Topic:
        query_norms = [normalize_text(query) for query in self.queries]
        if len(query_norms) != len(set(query_norms)):
            raise ValueError("duplicate queries after normalization")

        alias_norms = [normalize_text(alias) for alias in self.aliases]
        if len(alias_norms) != len(set(alias_norms)):
            raise ValueError("duplicate aliases after normalization")

        neg_norms = {normalize_text(term) for term in self.negative_terms}
        overlaps = neg_norms.intersection(query_norms).union(neg_norms.intersection(alias_norms))
        if overlaps:
            raise ValueError("negative_terms must not duplicate queries or aliases")

        terminal = {TopicStatus.draft, TopicStatus.deprecated, TopicStatus.archived}
        if self.status not in terminal and not any(source.enabled for source in self.sources):
            raise ValueError("non-draft topics must contain at least one enabled source")
        return self


class TopicPack(BaseModel):
    topics: list[Topic]


class TopicSnapshot(BaseModel):
    id: str
    version: str
    config_hash: str
