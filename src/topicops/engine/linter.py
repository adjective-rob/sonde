from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from pydantic import ValidationError

from topicops.constants import KNOWN_SOURCE_IDS
from topicops.engine.lineage import normalize_text
from topicops.engine.loader import load_raw_config
from topicops.models.topic import TopicPack, TopicStatus


@dataclass
class LintIssue:
    level: str
    code: str
    message: str
    topic_id: str | None = None


@dataclass
class LintResult:
    path: str
    topics_parsed: int = 0
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [issue for issue in self.issues if issue.level == "FAIL"]

    @property
    def warnings(self) -> list[LintIssue]:
        return [issue for issue in self.issues if issue.level == "WARN"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "path": self.path,
            "topics_parsed": self.topics_parsed,
            "warnings": [issue.__dict__ for issue in self.warnings],
            "errors": [issue.__dict__ for issue in self.errors],
        }


def lint_config(path: str | Path) -> LintResult:
    result = LintResult(path=str(path))
    try:
        raw = load_raw_config(path)
    except Exception as exc:
        result.issues.append(LintIssue("FAIL", "invalid_config", str(exc)))
        return result

    if "topics" not in raw:
        result.issues.append(LintIssue("FAIL", "missing_topics", "Missing required topics key"))
        return result

    raw_topics = raw.get("topics")
    if not isinstance(raw_topics, list):
        result.issues.append(LintIssue("FAIL", "invalid_topics", "topics must be a list"))
        return result

    ids = [topic.get("id") for topic in raw_topics if isinstance(topic, dict)]
    for topic_id, count in Counter(ids).items():
        if topic_id and count > 1:
            result.issues.append(
                LintIssue("FAIL", "duplicate_topic_id", f"Duplicate topic id: {topic_id}", topic_id)
            )

    query_owner: dict[str, str] = {}
    for raw_topic in raw_topics:
        if not isinstance(raw_topic, dict):
            result.issues.append(LintIssue("FAIL", "invalid_topic", "Each topic must be a mapping"))
            continue
        topic_id = str(raw_topic.get("id", "<missing>"))
        queries = raw_topic.get("queries", [])
        if isinstance(queries, list):
            for query in queries:
                normalized = normalize_text(str(query)) if query is not None else ""
                if not normalized:
                    result.issues.append(
                        LintIssue("FAIL", "empty_query", "Topic contains an empty query", topic_id)
                    )
                previous = query_owner.get(normalized)
                if normalized and previous and previous != topic_id:
                    result.issues.append(
                        LintIssue(
                            "FAIL",
                            "duplicate_query_across_topics",
                            f"Duplicate query across topics: {query}",
                            topic_id,
                        )
                    )
                elif normalized:
                    query_owner[normalized] = topic_id

    try:
        pack = TopicPack.model_validate(raw)
    except ValidationError as exc:
        result.issues.append(LintIssue("FAIL", "schema_validation", str(exc)))
        return result

    result.topics_parsed = len(pack.topics)
    today = date.today()
    for topic in pack.topics:
        unknown = [source.id for source in topic.sources if source.id not in KNOWN_SOURCE_IDS]
        for source_id in unknown:
            result.issues.append(
                LintIssue("FAIL", "unknown_source", f"Unknown source id: {source_id}", topic.id)
            )
        if topic.status == TopicStatus.active and not topic.owner:
            result.issues.append(
                LintIssue("WARN", "missing_owner", "Active topic is missing owner", topic.id)
            )
        if topic.governance.last_reviewed_at:
            due = topic.governance.last_reviewed_at + timedelta(
                days=topic.governance.review_cycle_days
            )
            if due < today:
                result.issues.append(
                    LintIssue("WARN", "overdue_review", "Topic is overdue for review", topic.id)
                )
        if (
            topic.status == TopicStatus.active
            and len(topic.sources) == 1
            and not topic.sources[0].enabled
        ):
            result.issues.append(
                LintIssue("FAIL", "disabled_only_source", "Only source is disabled", topic.id)
            )
        broad = any(len(normalize_text(query).split()) <= 2 for query in topic.queries)
        if broad and not topic.negative_terms:
            result.issues.append(
                LintIssue(
                    "WARN",
                    "missing_negative_terms",
                    "Broad topic has no negative_terms",
                    topic.id,
                )
            )
    return result
