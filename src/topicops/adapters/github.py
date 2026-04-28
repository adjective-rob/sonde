from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

from topicops.adapters.base import BaseAdapter, RawSourceRecord
from topicops.engine.lineage import sha256_digest
from topicops.models.artifact import Artifact
from topicops.models.source import TopicSourceConfig
from topicops.models.topic import Topic


class GitHubAdapter(BaseAdapter):
    id = "github"
    version = "0.1.0"
    endpoint = "https://api.github.com/search/repositories"

    async def search(
        self, topic: Topic, source_config: TopicSourceConfig, *, limit: int, dry_run: bool = False
    ) -> list[RawSourceRecord]:
        if dry_run:
            return []
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "topicops/0.1.0"}
        if token := os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
        records: list[RawSourceRecord] = []
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            for query in topic.queries:
                response = await client.get(
                    self.endpoint, params={"q": query, "per_page": min(limit, 100)}
                )
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("items", []):
                    raw_text = str(item)
                    records.append(
                        RawSourceRecord(
                            source=self.id,
                            source_id=str(item.get("id")),
                            title=item.get("full_name"),
                            url=item.get("html_url"),
                            raw=item,
                            fetched_at=datetime.now(UTC),
                            query=query,
                            response_hash=sha256_digest(raw_text),
                        )
                    )
                    if len(records) >= limit:
                        return records
        return records

    def normalize(
        self, record: RawSourceRecord, topic: Topic, run_id: str, config_hash: str
    ) -> Artifact:
        raw = record.raw if isinstance(record.raw, dict) else {}
        return self.artifact_from_record(
            record,
            topic,
            run_id,
            config_hash,
            title=str(raw.get("full_name") or record.title or "GitHub repository"),
            url=raw.get("html_url"),
            summary=raw.get("description"),
            metadata={
                "stars": raw.get("stargazers_count"),
                "forks": raw.get("forks_count"),
                "language": raw.get("language"),
                "topics": raw.get("topics", []),
                "created_at": raw.get("created_at"),
                "updated_at": raw.get("updated_at"),
            },
        )
