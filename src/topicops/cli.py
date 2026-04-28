from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console

from topicops import __version__
from topicops.config import get_settings
from topicops.constants import DEFAULT_ARTIFACT_PATH, DEFAULT_CONFIG, DEFAULT_DB_PATH
from topicops.engine.dedupe import dedupe_topics
from topicops.engine.diff import diff_topics
from topicops.engine.export import export_topic_pack
from topicops.engine.linter import lint_config
from topicops.engine.loader import get_topic, load_topics
from topicops.engine.runner import run_topics
from topicops.engine.simulate import simulate_topic
from topicops.mcp_server.server import run_mcp_server, server_summary
from topicops.registry.file_backend import ArtifactStore
from topicops.registry.repository import RegistryRepository

app = typer.Typer(help="TopicOps collection-intent control plane.")
console = Console()


def print_json(payload: object) -> None:
    console.print(json.dumps(payload, indent=2, sort_keys=True, default=str))


@app.command()
def init() -> None:
    """Create a local TopicOps workspace."""
    DEFAULT_CONFIG.write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {
                        "id": "agent_security_model",
                        "name": "Agent Security Model",
                        "intent": "Track AI agent identity, permissioning, and isolation.",
                        "status": "draft",
                        "priority": "medium",
                        "version": "1.0.0",
                        "queries": ["agent security model"],
                        "sources": [{"id": "local_jsonl", "enabled": True, "max_results": 10}],
                        "schedule": {"interval_minutes": 1440},
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    ArtifactStore(DEFAULT_ARTIFACT_PATH).ensure()
    RegistryRepository(DEFAULT_DB_PATH)
    console.print("Initialized TopicOps workspace")


@app.command()
def lint(
    config: Path,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
    strict: bool = False,
) -> None:
    """Validate a topic config."""
    result = lint_config(config)
    if json_output:
        print_json(result.as_dict())
    else:
        console.print(f"TopicOps lint: {config}")
        console.print(f"OK    {result.topics_parsed} topics parsed")
        console.print(f"OK    {result.topics_parsed - len(result.errors)} valid topic rows checked")
        for issue in result.warnings:
            console.print(f"WARN  {issue.message}")
        for issue in result.errors:
            console.print(f"FAIL  {issue.message}")
    if result.errors or (strict and result.warnings):
        raise typer.Exit(1)


@app.command()
def dedupe(
    config: Path,
    near: bool = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Find duplicate and overlapping topics."""
    result = dedupe_topics(load_topics(config), include_near=near)
    if json_output:
        print_json(result.as_dict())
    else:
        console.print(f"Hard duplicates: {len(result.hard_duplicates)}")
        console.print(f"Case-insensitive duplicates: {len(result.case_insensitive_duplicates)}")
        console.print(f"Near overlaps: {len(result.near_overlaps)}")
        for overlap in result.near_overlaps:
            console.print("")
            console.print("Near overlap:")
            console.print(f"  {overlap.left}")
            console.print(f"  {overlap.right}")
            console.print(f"  score: {overlap.score}")
            console.print(f"  reason: {overlap.reason}")
    if result.hard_duplicates:
        raise typer.Exit(1)


@app.command()
def diff(
    old_config: Path,
    new_config: Path,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Compare two topic configs."""
    result = diff_topics(load_topics(old_config), load_topics(new_config))
    if json_output:
        print_json(result.as_dict())
        return
    console.print("Topic diff")
    if result.added:
        console.print("\nAdded:")
        for item in result.added:
            console.print(f"  + {item}")
    if result.removed:
        console.print("\nRemoved:")
        for item in result.removed:
            console.print(f"  - {item}")
    if result.changed:
        console.print("\nChanged:")
        for changed_item in result.changed:
            console.print(
                f"  {changed_item['topic_id']} "
                f"{changed_item['old_version']} -> {changed_item['new_version']}"
            )
            fields = changed_item["fields"]
            if isinstance(fields, list):
                for field in fields:
                    console.print(f"    changed: {field}")
    if result.warnings:
        console.print("\nWarnings:")
        for warning in result.warnings:
            console.print(f"  {warning}")


@app.command()
def simulate(
    config: Path,
    topic: Annotated[str, typer.Option("--topic")],
    source: Annotated[str, typer.Option("--source")] = "local_jsonl",
    limit: int = 20,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Sample expected yield and noise for a topic."""
    selected = get_topic(load_topics(config), topic)
    result = asyncio.run(simulate_topic(selected, source, limit=limit))
    if json_output:
        print_json(result.as_dict())
        return
    console.print(f"Simulation: {result.topic_id}\n")
    console.print(f"Source: {result.source}")
    console.print(f"Queries tested: {result.queries_tested}")
    console.print(f"Records sampled: {result.records_sampled}")
    console.print(f"Potential duplicates: {result.potential_duplicates}")
    console.print(f"Estimated relevance: {result.estimated_relevance}")
    console.print(f"Estimated noise: {result.estimated_noise}")
    console.print(f"Estimated novelty: {result.estimated_novelty}")
    console.print("\nTop records:")
    for index, title in enumerate(result.top_records, start=1):
        console.print(f"{index}. {title}")


@app.command()
def run(
    config: Path,
    topic: Annotated[str | None, typer.Option("--topic")] = None,
    all_active: Annotated[bool, typer.Option("--all-active")] = False,
    source: Annotated[str | None, typer.Option("--source")] = None,
    dry_run: bool = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Execute selected topics and write lineage manifests."""
    topics = load_topics(config)
    if topic:
        selected = [get_topic(topics, topic)]
    elif all_active:
        selected = [item for item in topics if item.status == "active"]
    else:
        raise typer.BadParameter("Use --topic or --all-active")
    settings = get_settings()
    manifest = asyncio.run(
        run_topics(
            selected,
            source_filter=source,
            dry_run=dry_run,
            db_path=str(settings.db_path),
            artifact_path=str(settings.artifact_path),
        )
    )
    if json_output:
        print_json(manifest.model_dump(mode="json"))
    else:
        console.print(f"Run: {manifest.run.id}")
        console.print(f"Status: {manifest.run.status}")
        console.print(f"Artifacts: {manifest.run.artifact_count}")
        console.print(f"Errors: {manifest.run.error_count}")
        manifest_path = settings.artifact_path / "manifests" / f"{manifest.run.id}.manifest.json"
        console.print(f"Manifest: {manifest_path}")
    if manifest.errors:
        raise typer.Exit(1)


@app.command()
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Show local registry status."""
    settings = get_settings()
    stats = RegistryRepository(settings.db_path).stats()
    payload = {
        "db_path": str(settings.db_path),
        "artifact_path": str(settings.artifact_path),
        **stats.model_dump(),
    }
    if json_output:
        print_json(payload)
    else:
        for key, value in payload.items():
            console.print(f"{key}: {value}")


@app.command()
def export(
    config: Path,
    tag: Annotated[str | None, typer.Option("--tag")] = None,
    output: Annotated[Path, typer.Option("--output")] = Path("exports/topicpack.yaml"),
    format: Annotated[str, typer.Option("--format")] = "yaml",
) -> None:
    """Export a filtered topic pack."""
    path = export_topic_pack(load_topics(config), output, tag=tag, fmt=format)
    console.print(f"Exported {path}")


@app.command()
def mcp(
    config: Annotated[Path, typer.Option("--config")] = Path("topics.yaml"),
    summary: Annotated[
        bool, typer.Option("--summary", help="Print registered MCP surface and exit.")
    ] = False,
) -> None:
    """Start the TopicOps MCP server."""
    if summary:
        print_json(server_summary(str(config)))
        return
    run_mcp_server(str(config))


@app.command("version")
def version_cmd() -> None:
    """Print TopicOps version."""
    console.print(__version__)
