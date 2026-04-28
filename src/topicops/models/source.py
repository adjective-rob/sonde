from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceIncludeConfig(BaseModel):
    languages: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    feed_urls: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)


class SourceExcludeConfig(BaseModel):
    languages: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)


class TopicSourceConfig(BaseModel):
    id: str
    enabled: bool = True
    max_results: int = Field(default=20, ge=1, le=1000)
    rate_limit_hint_per_hour: int | None = Field(default=None, ge=1)
    query_override: str | None = None
    include: SourceIncludeConfig = Field(default_factory=SourceIncludeConfig)
    exclude: SourceExcludeConfig = Field(default_factory=SourceExcludeConfig)
    options: dict[str, Any] = Field(default_factory=dict)
