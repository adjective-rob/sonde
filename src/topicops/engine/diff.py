from __future__ import annotations

from dataclasses import dataclass, field

from topicops.engine.lineage import hash_canonical
from topicops.models.topic import Topic


@dataclass
class TopicDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[dict[str, object]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return self.__dict__


def diff_topics(old_topics: list[Topic], new_topics: list[Topic]) -> TopicDiff:
    result = TopicDiff()
    old_by_id = {topic.id: topic for topic in old_topics}
    new_by_id = {topic.id: topic for topic in new_topics}
    for topic_id in sorted(new_by_id.keys() - old_by_id.keys()):
        result.added.append(f"{topic_id} {new_by_id[topic_id].version}")
    for topic_id in sorted(old_by_id.keys() - new_by_id.keys()):
        result.removed.append(f"{topic_id} {old_by_id[topic_id].version}")
    for topic_id in sorted(old_by_id.keys() & new_by_id.keys()):
        old = old_by_id[topic_id]
        new = new_by_id[topic_id]
        old_payload = old.model_dump(mode="json")
        new_payload = new.model_dump(mode="json")
        if hash_canonical(old_payload) == hash_canonical(new_payload):
            continue
        fields = [
            field
            for field in new_payload
            if old_payload.get(field) != new_payload.get(field) and field != "version"
        ]
        result.changed.append(
            {
                "topic_id": topic_id,
                "old_version": old.version,
                "new_version": new.version,
                "fields": fields,
            }
        )
        if old.version == new.version:
            result.warnings.append(f"{topic_id} changed but version did not change")
        if "queries" in fields and old.version.split(".")[0:2] == new.version.split(".")[0:2]:
            result.warnings.append(f"{topic_id} changed queries without a minor or major bump")
    return result
