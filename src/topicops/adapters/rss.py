from __future__ import annotations

from datetime import UTC, datetime

import feedparser
import httpx

from topicops.adapters.base import BaseAdapter, RawSourceRecord
from topicops.engine.lineage import sha256_digest
from topicops.models.artifact import Artifact
from topicops.models.source import TopicSourceConfig
from topicops.models.topic import Topic


class RSSAdapter(BaseAdapter):
    id = "rss"
    version = "0.1.0"

    async def search(
        self, topic: Topic, source_config: TopicSourceConfig, *, limit: int, dry_run: bool = False
    ) -> list[RawSourceRecord]:
        if dry_run:
            return []
        records: list[RawSourceRecord] = []
        async with httpx.AsyncClient(
            timeout=20, headers={"User-Agent": "topicops/0.1.0"}
        ) as client:
            for url in source_config.include.feed_urls:
                response = await client.get(url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
                for entry in feed.entries:
                    raw = dict(entry)
                    records.append(
                        RawSourceRecord(
                            source=self.id,
                            source_id=entry.get("id") or entry.get("link"),
                            title=entry.get("title"),
                            url=entry.get("link"),
                            raw={**raw, "feed_title": feed.feed.get("title")},
                            fetched_at=datetime.now(UTC),
                            query=url,
                            response_hash=sha256_digest(str(raw)),
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
            title=str(raw.get("title") or record.title or "RSS item"),
            url=raw.get("link") or record.url,
            summary=raw.get("summary"),
            authors=[raw["author"]] if raw.get("author") else [],
            metadata={"feed_title": raw.get("feed_title")},
        )
