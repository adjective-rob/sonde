from __future__ import annotations

from datetime import UTC, datetime

from sonde.adapters import adapter_registry
from sonde.engine.lineage import hash_canonical
from sonde.engine.manifests import write_manifest
from sonde.models.artifact import Artifact
from sonde.models.run import CollectionRun, RunError, RunManifest, RunStatus
from sonde.models.topic import Topic, TopicSnapshot
from sonde.registry.file_backend import ArtifactStore
from sonde.registry.repository import RegistryRepository


def make_run_id() -> str:
    return datetime.now(UTC).strftime("run_%Y%m%d_%H%M%S_%f")


async def run_topics(
    topics: list[Topic],
    *,
    source_filter: str | None,
    dry_run: bool,
    db_path: str,
    artifact_path: str,
) -> RunManifest:
    adapters = adapter_registry()
    run_id = make_run_id()
    sources = sorted(
        {
            source.id
            for topic in topics
            for source in topic.sources
            if source.enabled and (source_filter is None or source.id == source_filter)
        }
    )
    config_hash = hash_canonical([topic.model_dump(mode="json") for topic in topics])
    run = CollectionRun(
        id=run_id,
        started_at=datetime.now(UTC),
        status=RunStatus.running,
        topic_ids=[topic.id for topic in topics],
        sources=sources,
        config_hash=config_hash,
        dry_run=dry_run,
    )
    repo = RegistryRepository(db_path)
    store = ArtifactStore(artifact_path)
    repo.insert_run(run)
    all_artifacts: list[Artifact] = []
    raw_count = 0
    errors: list[RunError] = []
    adapter_versions: dict[str, str] = {}

    for topic in topics:
        topic_hash = hash_canonical(topic.model_dump(mode="json"))
        repo.upsert_topic(topic, topic_hash)
        for source_config in topic.sources:
            if not source_config.enabled or (source_filter and source_config.id != source_filter):
                continue
            adapter = adapters[source_config.id]
            adapter_versions[adapter.id] = adapter.version
            try:
                records = await adapter.search(
                    topic,
                    source_config,
                    limit=source_config.max_results,
                    dry_run=False,
                )
                raw_count += len(records)
                if not dry_run:
                    store.write_raw(run_id, records)
                for record in records:
                    all_artifacts.append(adapter.normalize(record, topic, run_id, topic_hash))
            except Exception as exc:
                errors.append(
                    RunError(
                        topic_id=topic.id,
                        source=source_config.id,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )

    deduped = list({artifact.normalized_hash: artifact for artifact in all_artifacts}.values())
    if not dry_run:
        store.append_artifacts(deduped)
        repo.insert_artifacts(deduped)
    run.status = RunStatus.completed if not errors else RunStatus.failed
    run.completed_at = datetime.now(UTC)
    run.artifact_count = len(deduped)
    run.error_count = len(errors)
    repo.insert_run(run)
    repo.insert_errors(run.id, errors)
    manifest = RunManifest(
        run=run,
        topics=[
            TopicSnapshot(
                id=topic.id,
                version=topic.version,
                config_hash=hash_canonical(topic.model_dump(mode="json")),
            )
            for topic in topics
        ],
        adapter_versions=adapter_versions,
        artifacts_written=0 if dry_run else len(deduped),
        raw_records_written=0 if dry_run else raw_count,
        errors=errors,
    )
    write_manifest(manifest, store.root)
    return manifest
