from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel

from topicops.engine.lineage import hash_canonical, sha256_digest
from topicops.models.artifact import Artifact
from topicops.models.source import TopicSourceConfig
from topicops.models.topic import Topic


class RawSourceRecord(BaseModel):
    source: str
    source_id: str | None = None
    title: str | None = None
    url: str | None = None
    raw: dict[str, Any] | str
    fetched_at: datetime
    query: str
    response_hash: str


class SourceAdapter(Protocol):
    id: str
    version: str

    async def search(
        self,
        topic: Topic,
        source_config: TopicSourceConfig,
        *,
        limit: int,
        dry_run: bool = False,
    ) -> list[RawSourceRecord]: ...

    def normalize(
        self,
        record: RawSourceRecord,
        topic: Topic,
        run_id: str,
        config_hash: str,
    ) -> Artifact: ...


class BaseAdapter:
    id = "base"
    version = "0.1.0"

    def artifact_from_record(
        self,
        record: RawSourceRecord,
        topic: Topic,
        run_id: str,
        config_hash: str,
        *,
        title: str,
        url: str | None = None,
        summary: str | None = None,
        authors: list[str] | None = None,
        published_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        metadata = metadata or {}
        payload = {
            "source": record.source,
            "source_id": record.source_id,
            "title": title,
            "url": url,
            "summary": summary,
            "authors": authors or [],
            "published_at": published_at.isoformat() if published_at else None,
            "topic_id": topic.id,
            "topic_version": topic.version,
            "metadata": metadata,
        }
        normalized_hash = hash_canonical(payload)
        source_key = record.source_id or url or normalized_hash
        artifact_id = sha256_digest(f"{record.source}:{source_key}:{topic.id}")[:24].replace(
            ":", "_"
        )
        return Artifact(
            id=artifact_id,
            source=record.source,
            source_id=record.source_id,
            title=title,
            url=url,
            summary=summary,
            authors=authors or [],
            published_at=published_at,
            collected_at=datetime.now(UTC),
            normalized_hash=normalized_hash,
            source_response_hash=record.response_hash,
            topic_id=topic.id,
            topic_version=topic.version,
            config_hash=config_hash,
            run_id=run_id,
            metadata={
                **metadata,
                "adapter": self.id,
                "adapter_version": self.version,
                "query": record.query,
            },
        )
