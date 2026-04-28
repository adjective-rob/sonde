from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

from topicops.adapters.base import BaseAdapter, RawSourceRecord
from topicops.engine.lineage import sha256_digest
from topicops.models.artifact import Artifact
from topicops.models.source import TopicSourceConfig
from topicops.models.topic import Topic


class HuggingFaceAdapter(BaseAdapter):
    id = "huggingface"
    version = "0.1.0"
    endpoint = "https://huggingface.co/api/models"

    async def search(
        self, topic: Topic, source_config: TopicSourceConfig, *, limit: int, dry_run: bool = False
    ) -> list[RawSourceRecord]:
        if dry_run:
            return []
        headers = {"User-Agent": "topicops/0.1.0"}
        if token := os.getenv("HF_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
        records: list[RawSourceRecord] = []
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            for query in topic.queries:
                response = await client.get(self.endpoint, params={"search": query, "limit": limit})
                response.raise_for_status()
                for item in response.json():
                    model_id = item.get("modelId") or item.get("id")
                    records.append(
                        RawSourceRecord(
                            source=self.id,
                            source_id=model_id,
                            title=model_id,
                            url=f"https://huggingface.co/{model_id}" if model_id else None,
                            raw=item,
                            fetched_at=datetime.now(UTC),
                            query=query,
                            response_hash=sha256_digest(str(item)),
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
            title=str(raw.get("modelId") or raw.get("id") or record.title or "Hugging Face model"),
            url=record.url,
            summary=None,
            metadata={
                "tags": raw.get("tags", []),
                "downloads": raw.get("downloads"),
                "likes": raw.get("likes"),
                "pipeline_tag": raw.get("pipeline_tag"),
                "last_modified": raw.get("lastModified"),
            },
        )
