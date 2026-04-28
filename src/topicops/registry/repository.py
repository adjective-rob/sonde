from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine

from topicops.engine.lineage import canonical_json, hash_canonical
from topicops.models.artifact import Artifact
from topicops.models.registry import RegistryStats
from topicops.models.run import CollectionRun, RunError
from topicops.models.topic import Topic
from topicops.registry.db import (
    artifacts_table,
    collection_runs_table,
    init_db,
    run_errors_table,
    topic_versions_table,
    topics_table,
)


class RegistryRepository:
    def __init__(self, db_path: str | Path):
        self.engine: Engine = init_db(db_path)

    def upsert_topic(self, topic: Topic, config_hash: str) -> None:
        now = datetime.now(UTC)
        with self.engine.begin() as conn:
            stmt = insert(topics_table).values(
                id=topic.id,
                name=topic.name,
                status=topic.status.value,
                priority=topic.priority.value,
                owner=topic.owner,
                latest_version=topic.version,
                created_at=now,
                updated_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": topic.name,
                    "status": topic.status.value,
                    "priority": topic.priority.value,
                    "owner": topic.owner,
                    "latest_version": topic.version,
                    "updated_at": now,
                },
            )
            conn.execute(stmt)
            version_id = f"{topic.id}:{topic.version}:{config_hash}"
            version_stmt = insert(topic_versions_table).values(
                id=version_id,
                topic_id=topic.id,
                version=topic.version,
                config_hash=config_hash,
                config_json=canonical_json(topic.model_dump(mode="json")),
                created_at=now,
                created_by=topic.owner,
            )
            version_stmt = version_stmt.on_conflict_do_nothing(index_elements=["id"])
            conn.execute(version_stmt)

    def insert_run(self, run: CollectionRun) -> None:
        with self.engine.begin() as conn:
            stmt = insert(collection_runs_table).values(
                id=run.id,
                status=run.status.value,
                started_at=run.started_at,
                completed_at=run.completed_at,
                topic_ids_json=json.dumps(run.topic_ids),
                sources_json=json.dumps(run.sources),
                config_hash=run.config_hash,
                artifact_count=run.artifact_count,
                error_count=run.error_count,
                dry_run=run.dry_run,
                metadata_json=json.dumps(run.metadata, sort_keys=True),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "status": run.status.value,
                    "completed_at": run.completed_at,
                    "artifact_count": run.artifact_count,
                    "error_count": run.error_count,
                    "metadata_json": json.dumps(run.metadata, sort_keys=True),
                },
            )
            conn.execute(stmt)

    def insert_artifacts(self, artifacts: list[Artifact]) -> None:
        with self.engine.begin() as conn:
            for artifact in artifacts:
                stmt = insert(artifacts_table).values(
                    id=artifact.id,
                    source=artifact.source,
                    source_id=artifact.source_id,
                    title=artifact.title,
                    url=artifact.url,
                    summary=artifact.summary,
                    published_at=artifact.published_at,
                    collected_at=artifact.collected_at,
                    normalized_hash=artifact.normalized_hash,
                    source_response_hash=artifact.source_response_hash,
                    topic_id=artifact.topic_id,
                    topic_version=artifact.topic_version,
                    config_hash=artifact.config_hash,
                    run_id=artifact.run_id,
                    metadata_json=json.dumps(artifact.metadata, sort_keys=True, default=str),
                )
                conn.execute(stmt.on_conflict_do_nothing(index_elements=["id"]))

    def insert_errors(self, run_id: str, errors: list[RunError]) -> None:
        with self.engine.begin() as conn:
            for error in errors:
                conn.execute(
                    insert(run_errors_table).values(
                        id=hash_canonical(
                            {
                                "run_id": run_id,
                                "error": error.model_dump(mode="json"),
                                "nonce": str(uuid4()),
                            }
                        ),
                        run_id=run_id,
                        topic_id=error.topic_id,
                        source=error.source,
                        error_type=error.error_type,
                        message=error.message,
                        created_at=datetime.now(UTC),
                        metadata_json=json.dumps(error.metadata, sort_keys=True),
                    )
                )

    def stats(self) -> RegistryStats:
        with self.engine.connect() as conn:
            return RegistryStats(
                topic_count=conn.execute(
                    select(func.count()).select_from(topics_table)
                ).scalar_one(),
                run_count=conn.execute(
                    select(func.count()).select_from(collection_runs_table)
                ).scalar_one(),
                artifact_count=conn.execute(
                    select(func.count()).select_from(artifacts_table)
                ).scalar_one(),
                error_count=conn.execute(
                    select(func.count()).select_from(run_errors_table)
                ).scalar_one(),
            )
