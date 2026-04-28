from __future__ import annotations

from pathlib import Path
from typing import Any

from sonde.engine.loader import get_topic, load_topics

EXPECTED_RESOURCES = [
    "sonde://topics",
    "sonde://topics/{topic_id}",
    "sonde://topics/{topic_id}/versions",
    "sonde://topics/{topic_id}/quality",
    "sonde://sources",
    "sonde://runs",
    "sonde://runs/{run_id}",
    "sonde://artifacts/{artifact_id}",
    "sonde://lineage/artifact/{artifact_id}",
    "sonde://diffs/{from_version}/{to_version}",
    "sonde://schema/topic",
    "sonde://schema/artifact",
]


def list_resource_templates() -> list[str]:
    return EXPECTED_RESOURCES


def _schema_path(name: str) -> Path:
    return Path(__file__).parent.parent / "schema" / f"{name}.schema.json"


def read_resource(
    uri: str,
    *,
    config_path: str = "topics.yaml",
    db_path: str = ".sonde/sonde.db",
) -> Any:
    topics = load_topics(config_path) if Path(config_path).exists() else []

    # sonde://topics
    if uri == "sonde://topics":
        return [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status.value,
                "priority": t.priority.value,
                "version": t.version,
                "owner": t.owner,
                "query_count": len(t.queries),
                "source_count": len([s for s in t.sources if s.enabled]),
            }
            for t in topics
        ]

    # sonde://sources
    if uri == "sonde://sources":
        return sorted({source.id for topic in topics for source in topic.sources})

    # sonde://schema/topic
    if uri == "sonde://schema/topic":
        return _schema_path("topic").read_text(encoding="utf-8")

    # sonde://schema/artifact
    if uri == "sonde://schema/artifact":
        return _schema_path("artifact").read_text(encoding="utf-8")

    # sonde://topics/{topic_id}/versions
    if uri.startswith("sonde://topics/") and uri.endswith("/versions"):
        topic_id = uri.removeprefix("sonde://topics/").removesuffix("/versions")
        from sonde.registry.repository import RegistryRepository

        repo = RegistryRepository(db_path)
        return repo.topic_versions(topic_id)

    # sonde://topics/{topic_id}/quality
    if uri.startswith("sonde://topics/") and uri.endswith("/quality"):
        topic_id = uri.removeprefix("sonde://topics/").removesuffix("/quality")
        from sonde.registry.repository import RegistryRepository

        repo = RegistryRepository(db_path)
        return repo.topic_health(topic_id)

    # sonde://topics/{topic_id}
    if uri.startswith("sonde://topics/"):
        topic_id = uri.removeprefix("sonde://topics/")
        return get_topic(topics, topic_id).model_dump(mode="json")

    # sonde://runs/{run_id}
    if uri.startswith("sonde://runs/"):
        run_id = uri.removeprefix("sonde://runs/")
        from sonde.registry.repository import RegistryRepository

        repo = RegistryRepository(db_path)
        return repo.get_run(run_id)

    # sonde://runs
    if uri == "sonde://runs":
        from sonde.registry.repository import RegistryRepository

        repo = RegistryRepository(db_path)
        return repo.recent_runs(limit=20)

    # sonde://artifacts/{artifact_id}
    if uri.startswith("sonde://artifacts/"):
        artifact_id = uri.removeprefix("sonde://artifacts/")
        from sonde.registry.repository import RegistryRepository

        repo = RegistryRepository(db_path)
        return repo.get_artifact(artifact_id)

    # sonde://lineage/artifact/{artifact_id}
    if uri.startswith("sonde://lineage/artifact/"):
        artifact_id = uri.removeprefix("sonde://lineage/artifact/")
        from sonde.registry.repository import RegistryRepository

        repo = RegistryRepository(db_path)
        return repo.artifact_lineage(artifact_id)

    # sonde://diffs/{from_version}/{to_version}
    if uri.startswith("sonde://diffs/"):
        parts = uri.removeprefix("sonde://diffs/").split("/")
        if len(parts) == 2:
            from sonde.registry.repository import RegistryRepository

            repo = RegistryRepository(db_path)
            return repo.version_diff(parts[0], parts[1])

    return {"uri": uri, "error": "unknown_resource"}
