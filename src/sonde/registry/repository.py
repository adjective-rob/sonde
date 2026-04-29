from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine

from sonde.engine.lineage import canonical_json, hash_canonical
from sonde.models.artifact import Artifact
from sonde.models.registry import RegistryStats
from sonde.models.run import CollectionRun, RunError
from sonde.models.topic import Topic
from sonde.registry.db import (
    artifact_seen_table,
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

    # ------------------------------------------------------------------
    # Core write operations
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Artifact memory
    # ------------------------------------------------------------------

    def mark_artifact_seen(
        self, *, artifact_hash: str, topic_id: str, source: str
    ) -> dict[str, Any]:
        """Track artifact across runs. Returns seen_count and first/last seen."""
        now = datetime.now(UTC)
        seen_id = hash_canonical(
            {"artifact_hash": artifact_hash, "topic_id": topic_id, "source": source}
        )
        with self.engine.begin() as conn:
            row = conn.execute(
                select(
                    artifact_seen_table.c.seen_count,
                    artifact_seen_table.c.first_seen_at,
                )
                .where(artifact_seen_table.c.id == seen_id)
            ).first()

            if row:
                new_count = row[0] + 1
                conn.execute(
                    artifact_seen_table.update()
                    .where(artifact_seen_table.c.id == seen_id)
                    .values(last_seen_at=now, seen_count=new_count)
                )
                return {
                    "seen_count": new_count,
                    "first_seen_at": str(row[1]),
                    "is_new": False,
                }
            else:
                conn.execute(
                    insert(artifact_seen_table).values(
                        id=seen_id,
                        artifact_id=artifact_hash,
                        topic_id=topic_id,
                        source=source,
                        first_seen_at=now,
                        last_seen_at=now,
                        seen_count=1,
                    )
                )
                return {"seen_count": 1, "first_seen_at": str(now), "is_new": True}

    def previous_run_artifact_count(self, topic_id: str) -> int:
        """Return artifact count from the most recent completed run for a topic."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_count FROM collection_runs "
                    "WHERE topic_ids_json LIKE :pattern "
                    "AND status = 'completed' "
                    "ORDER BY started_at DESC LIMIT 1"
                ),
                {"pattern": f'%"{topic_id}"%'},
            ).first()
            return row[0] if row and row[0] else 0

    def artifact_seen_stats(self, topic_id: str) -> dict[str, Any]:
        """Return artifact memory stats for a topic."""
        with self.engine.connect() as conn:
            total = conn.execute(
                select(func.count()).select_from(artifact_seen_table).where(
                    artifact_seen_table.c.topic_id == topic_id
                )
            ).scalar_one()
            recurring = conn.execute(
                select(func.count()).select_from(artifact_seen_table).where(
                    artifact_seen_table.c.topic_id == topic_id,
                    artifact_seen_table.c.seen_count > 1,
                )
            ).scalar_one()
            max_seen = conn.execute(
                select(func.max(artifact_seen_table.c.seen_count)).where(
                    artifact_seen_table.c.topic_id == topic_id
                )
            ).scalar_one()
            return {
                "topic_id": topic_id,
                "total_unique_artifacts": total,
                "recurring_artifacts": recurring,
                "new_artifacts": total - recurring,
                "max_seen_count": max_seen or 0,
                "novelty_ratio": round(
                    (total - recurring) / max(total, 1), 3
                ),
            }

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

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

    def get_topic_version(self, topic_id: str, version: str) -> str | None:
        """Return the config_json for a specific topic version, or None."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(topic_versions_table.c.config_json).where(
                    topic_versions_table.c.topic_id == topic_id,
                    topic_versions_table.c.version == version,
                )
            ).first()
            return row[0] if row else None

    def topic_versions(self, topic_id: str) -> list[dict[str, Any]]:
        """Return version history for a topic."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    topic_versions_table.c.version,
                    topic_versions_table.c.config_hash,
                    topic_versions_table.c.created_at,
                    topic_versions_table.c.created_by,
                )
                .where(topic_versions_table.c.topic_id == topic_id)
                .order_by(topic_versions_table.c.created_at.desc())
            ).fetchall()
            return [
                {
                    "version": row[0],
                    "config_hash": row[1],
                    "created_at": str(row[2]) if row[2] else None,
                    "created_by": row[3],
                }
                for row in rows
            ]

    def topic_health(self, topic_id: str) -> dict[str, Any]:
        """Return health metrics for a topic from the registry."""
        with self.engine.connect() as conn:
            # Total runs involving this topic
            total_runs = conn.execute(
                text(
                    "SELECT COUNT(*) FROM collection_runs "
                    "WHERE topic_ids_json LIKE :pattern"
                ),
                {"pattern": f'%"{topic_id}"%'},
            ).scalar_one()

            # Total artifacts for this topic
            total_artifacts = conn.execute(
                select(func.count()).select_from(artifacts_table).where(
                    artifacts_table.c.topic_id == topic_id
                )
            ).scalar_one()

            # Total errors for this topic
            total_errors = conn.execute(
                select(func.count()).select_from(run_errors_table).where(
                    run_errors_table.c.topic_id == topic_id
                )
            ).scalar_one()

            # Last run time
            last_run_row = conn.execute(
                text(
                    "SELECT MAX(started_at) FROM collection_runs "
                    "WHERE topic_ids_json LIKE :pattern"
                ),
                {"pattern": f'%"{topic_id}"%'},
            ).first()
            last_run_at = str(last_run_row[0]) if last_run_row and last_run_row[0] else None

            # Sources that have produced artifacts
            source_rows = conn.execute(
                select(artifacts_table.c.source)
                .where(artifacts_table.c.topic_id == topic_id)
                .distinct()
            ).fetchall()
            sources_with_artifacts = [row[0] for row in source_rows]

            return {
                "topic_id": topic_id,
                "total_runs": total_runs,
                "total_artifacts": total_artifacts,
                "total_errors": total_errors,
                "last_run_at": last_run_at,
                "sources_with_artifacts": sources_with_artifacts,
            }

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent collection runs."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(collection_runs_table)
                .order_by(collection_runs_table.c.started_at.desc())
                .limit(limit)
            ).fetchall()
            return [
                {
                    "id": row.id,
                    "status": row.status,
                    "started_at": str(row.started_at) if row.started_at else None,
                    "completed_at": str(row.completed_at) if row.completed_at else None,
                    "topic_ids": json.loads(row.topic_ids_json) if row.topic_ids_json else [],
                    "sources": json.loads(row.sources_json) if row.sources_json else [],
                    "artifact_count": row.artifact_count,
                    "error_count": row.error_count,
                    "dry_run": row.dry_run,
                }
                for row in rows
            ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Return a single run by ID."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(collection_runs_table).where(
                    collection_runs_table.c.id == run_id
                )
            ).first()
            if not row:
                return {"error": f"Run not found: {run_id}"}
            return {
                "id": row.id,
                "status": row.status,
                "started_at": str(row.started_at) if row.started_at else None,
                "completed_at": str(row.completed_at) if row.completed_at else None,
                "topic_ids": json.loads(row.topic_ids_json) if row.topic_ids_json else [],
                "sources": json.loads(row.sources_json) if row.sources_json else [],
                "config_hash": row.config_hash,
                "artifact_count": row.artifact_count,
                "error_count": row.error_count,
                "dry_run": row.dry_run,
            }

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        """Return a single artifact by ID."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(artifacts_table).where(artifacts_table.c.id == artifact_id)
            ).first()
            if not row:
                return {"error": f"Artifact not found: {artifact_id}"}
            return {
                "id": row.id,
                "source": row.source,
                "source_id": row.source_id,
                "title": row.title,
                "url": row.url,
                "summary": row.summary,
                "published_at": str(row.published_at) if row.published_at else None,
                "collected_at": str(row.collected_at) if row.collected_at else None,
                "normalized_hash": row.normalized_hash,
                "source_response_hash": row.source_response_hash,
                "topic_id": row.topic_id,
                "topic_version": row.topic_version,
                "config_hash": row.config_hash,
                "run_id": row.run_id,
                "metadata": json.loads(row.metadata_json) if row.metadata_json else {},
            }

    def artifact_lineage(self, artifact_id: str) -> dict[str, Any]:
        """Return full lineage chain for an artifact."""
        artifact = self.get_artifact(artifact_id)
        if not artifact or "error" in artifact:
            return artifact or {"error": f"Artifact not found: {artifact_id}"}

        run = self.get_run(artifact["run_id"])
        topic_version = self.get_topic_version(artifact["topic_id"], artifact["topic_version"])

        return {
            "artifact": artifact,
            "run": run,
            "topic_version": artifact["topic_version"],
            "config_hash": artifact["config_hash"],
            "topic_config": json.loads(topic_version) if topic_version else None,
        }

    def version_diff(self, version_id_a: str, version_id_b: str) -> dict[str, Any]:
        """Diff two topic versions by their version_id (topic_id:version:hash)."""
        with self.engine.connect() as conn:
            row_a = conn.execute(
                select(topic_versions_table.c.config_json).where(
                    topic_versions_table.c.id == version_id_a
                )
            ).first()
            row_b = conn.execute(
                select(topic_versions_table.c.config_json).where(
                    topic_versions_table.c.id == version_id_b
                )
            ).first()

        if not row_a:
            return {"error": f"Version not found: {version_id_a}"}
        if not row_b:
            return {"error": f"Version not found: {version_id_b}"}

        import difflib

        a_lines = json.dumps(json.loads(row_a[0]), indent=2, sort_keys=True).splitlines()
        b_lines = json.dumps(json.loads(row_b[0]), indent=2, sort_keys=True).splitlines()
        diff = "\n".join(difflib.unified_diff(a_lines, b_lines, lineterm=""))
        return {
            "from": version_id_a,
            "to": version_id_b,
            "diff": diff,
        }
