from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

topics_table = Table(
    "topics",
    metadata,
    __import__("sqlalchemy").Column("id", String, primary_key=True),
    __import__("sqlalchemy").Column("name", String, nullable=False),
    __import__("sqlalchemy").Column("status", String, nullable=False),
    __import__("sqlalchemy").Column("priority", String, nullable=False),
    __import__("sqlalchemy").Column("owner", String),
    __import__("sqlalchemy").Column("latest_version", String, nullable=False),
    __import__("sqlalchemy").Column("created_at", DateTime),
    __import__("sqlalchemy").Column("updated_at", DateTime),
)

topic_versions_table = Table(
    "topic_versions",
    metadata,
    __import__("sqlalchemy").Column("id", String, primary_key=True),
    __import__("sqlalchemy").Column("topic_id", String, nullable=False),
    __import__("sqlalchemy").Column("version", String, nullable=False),
    __import__("sqlalchemy").Column("config_hash", String, nullable=False),
    __import__("sqlalchemy").Column("config_json", Text, nullable=False),
    __import__("sqlalchemy").Column("created_at", DateTime),
    __import__("sqlalchemy").Column("created_by", String),
)

collection_runs_table = Table(
    "collection_runs",
    metadata,
    __import__("sqlalchemy").Column("id", String, primary_key=True),
    __import__("sqlalchemy").Column("status", String, nullable=False),
    __import__("sqlalchemy").Column("started_at", DateTime),
    __import__("sqlalchemy").Column("completed_at", DateTime),
    __import__("sqlalchemy").Column("topic_ids_json", Text),
    __import__("sqlalchemy").Column("sources_json", Text),
    __import__("sqlalchemy").Column("config_hash", String),
    __import__("sqlalchemy").Column("artifact_count", Integer),
    __import__("sqlalchemy").Column("error_count", Integer),
    __import__("sqlalchemy").Column("dry_run", Boolean),
    __import__("sqlalchemy").Column("metadata_json", Text),
)

artifacts_table = Table(
    "artifacts",
    metadata,
    __import__("sqlalchemy").Column("id", String, primary_key=True),
    __import__("sqlalchemy").Column("source", String, nullable=False),
    __import__("sqlalchemy").Column("source_id", String),
    __import__("sqlalchemy").Column("title", String, nullable=False),
    __import__("sqlalchemy").Column("url", String),
    __import__("sqlalchemy").Column("summary", Text),
    __import__("sqlalchemy").Column("published_at", DateTime),
    __import__("sqlalchemy").Column("collected_at", DateTime),
    __import__("sqlalchemy").Column("normalized_hash", String, nullable=False),
    __import__("sqlalchemy").Column("source_response_hash", String),
    __import__("sqlalchemy").Column("topic_id", String, nullable=False),
    __import__("sqlalchemy").Column("topic_version", String, nullable=False),
    __import__("sqlalchemy").Column("config_hash", String, nullable=False),
    __import__("sqlalchemy").Column("run_id", String, nullable=False),
    __import__("sqlalchemy").Column("metadata_json", Text),
)

artifact_seen_table = Table(
    "artifact_seen",
    metadata,
    __import__("sqlalchemy").Column("id", String, primary_key=True),
    __import__("sqlalchemy").Column("artifact_id", String, nullable=False),
    __import__("sqlalchemy").Column("topic_id", String, nullable=False),
    __import__("sqlalchemy").Column("source", String, nullable=False),
    __import__("sqlalchemy").Column("first_seen_at", DateTime),
    __import__("sqlalchemy").Column("last_seen_at", DateTime),
    __import__("sqlalchemy").Column("seen_count", Integer),
)

run_errors_table = Table(
    "run_errors",
    metadata,
    __import__("sqlalchemy").Column("id", String, primary_key=True),
    __import__("sqlalchemy").Column("run_id", String, nullable=False),
    __import__("sqlalchemy").Column("topic_id", String),
    __import__("sqlalchemy").Column("source", String),
    __import__("sqlalchemy").Column("error_type", String, nullable=False),
    __import__("sqlalchemy").Column("message", Text, nullable=False),
    __import__("sqlalchemy").Column("created_at", DateTime),
    __import__("sqlalchemy").Column("metadata_json", Text),
)


def get_engine(db_path: str | Path) -> Engine:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", future=True)


def init_db(db_path: str | Path) -> Engine:
    engine = get_engine(db_path)
    metadata.create_all(engine)
    return engine
