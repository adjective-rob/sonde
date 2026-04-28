from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sonde.adapters.base import BaseAdapter, RawSourceRecord
from sonde.engine.lineage import normalize_text, sha256_digest
from sonde.models.artifact import Artifact
from sonde.models.source import TopicSourceConfig
from sonde.models.topic import Topic


class LocalJsonlAdapter(BaseAdapter):
    id = "local_jsonl"
    version = "0.1.0"

    async def search(
        self,
        topic: Topic,
        source_config: TopicSourceConfig,
        *,
        limit: int,
        dry_run: bool = False,
    ) -> list[RawSourceRecord]:
        paths = source_config.include.paths or ["examples/fixtures/local_records.jsonl"]
        records: list[RawSourceRecord] = []
        query_terms = [normalize_text(query) for query in topic.queries + topic.aliases]
        negatives = [normalize_text(term) for term in topic.negative_terms]
        for path_value in paths:
            path = Path(path_value)
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                raw: dict[str, Any] = json.loads(line)
                text = normalize_text(
                    " ".join([str(raw.get("title", "")), str(raw.get("summary", ""))])
                )
                if any(term in text for term in negatives):
                    continue
                if query_terms and not any(
                    any(word in text for word in query.split()) for query in query_terms
                ):
                    continue
                records.append(
                    RawSourceRecord(
                        source=self.id,
                        source_id=str(raw.get("source_id"))
                        if raw.get("source_id") is not None
                        else None,
                        title=raw.get("title"),
                        url=raw.get("url"),
                        raw=raw,
                        fetched_at=datetime.now(UTC),
                        query=topic.queries[0],
                        response_hash=sha256_digest(line),
                    )
                )
                if len(records) >= limit:
                    return records
        return records

    def normalize(
        self,
        record: RawSourceRecord,
        topic: Topic,
        run_id: str,
        config_hash: str,
    ) -> Artifact:
        raw = record.raw if isinstance(record.raw, dict) else {}
        published = raw.get("published_at")
        published_at = (
            datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None
        )
        return self.artifact_from_record(
            record,
            topic,
            run_id,
            config_hash,
            title=str(raw.get("title") or record.title or "Untitled"),
            url=raw.get("url") or record.url,
            summary=raw.get("summary"),
            authors=list(raw.get("authors", [])),
            published_at=published_at,
            metadata=dict(raw.get("metadata", {})),
        )
