from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from sonde.adapters.base import BaseAdapter, RawSourceRecord
from sonde.engine.lineage import sha256_digest
from sonde.models.artifact import Artifact
from sonde.models.source import TopicSourceConfig
from sonde.models.topic import Topic


class ArxivAdapter(BaseAdapter):
    id = "arxiv"
    version = "0.1.0"
    endpoint = "https://export.arxiv.org/api/query"

    async def search(
        self, topic: Topic, source_config: TopicSourceConfig, *, limit: int, dry_run: bool = False
    ) -> list[RawSourceRecord]:
        if dry_run:
            return []
        records: list[RawSourceRecord] = []
        async with httpx.AsyncClient(
            timeout=20, headers={"User-Agent": "sonde/0.1.0"}
        ) as client:
            for query in topic.queries:
                response = await client.get(
                    self.endpoint, params={"search_query": f"all:{query}", "max_results": limit}
                )
                response.raise_for_status()
                root = ET.fromstring(response.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
                    source_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
                    raw_xml = ET.tostring(entry, encoding="unicode")
                    records.append(
                        RawSourceRecord(
                            source=self.id,
                            source_id=source_id,
                            title=title,
                            url=source_id,
                            raw={"xml": raw_xml},
                            fetched_at=datetime.now(UTC),
                            query=query,
                            response_hash=sha256_digest(raw_xml),
                        )
                    )
                    if len(records) >= limit:
                        return records
        return records

    def normalize(
        self, record: RawSourceRecord, topic: Topic, run_id: str, config_hash: str
    ) -> Artifact:
        raw = record.raw if isinstance(record.raw, dict) else {}
        xml = str(raw.get("xml", ""))
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = ET.fromstring(xml) if xml else ET.Element("entry")
        authors = [
            node.findtext("atom:name", default="", namespaces=ns)
            for node in entry.findall("atom:author", ns)
        ]
        published = entry.findtext("atom:published", default="", namespaces=ns)
        published_at = (
            datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None
        )
        return self.artifact_from_record(
            record,
            topic,
            run_id,
            config_hash,
            title=(
                entry.findtext("atom:title", default=record.title or "arXiv paper", namespaces=ns)
                or ""
            ).strip(),
            url=record.url,
            summary=(entry.findtext("atom:summary", default="", namespaces=ns) or "").strip(),
            authors=[author for author in authors if author],
            published_at=published_at,
            metadata={"updated_at": entry.findtext("atom:updated", default="", namespaces=ns)},
        )
