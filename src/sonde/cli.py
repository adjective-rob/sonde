from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console

from sonde import __version__
from sonde.config import get_settings
from sonde.constants import DEFAULT_ARTIFACT_PATH, DEFAULT_CONFIG, DEFAULT_DB_PATH
from sonde.engine.dedupe import dedupe_topics
from sonde.engine.diff import diff_topics
from sonde.engine.export import export_topic_pack
from sonde.engine.linter import lint_config
from sonde.engine.loader import get_topic, load_topics
from sonde.engine.runner import run_topics
from sonde.engine.simulate import simulate_topic
from sonde.mcp_server.server import run_mcp_server, server_summary
from sonde.registry.file_backend import ArtifactStore
from sonde.registry.repository import RegistryRepository

app = typer.Typer(help="Sonde collection-intent control plane.")
console = Console()


def print_json(payload: object) -> None:
    console.print(json.dumps(payload, indent=2, sort_keys=True, default=str))


@app.command()
def init() -> None:
    """Create a local Sonde workspace."""
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
    console.print("Initialized Sonde workspace")


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
        console.print(f"Sonde lint: {config}")
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
    """Start the Sonde MCP server."""
    if summary:
        print_json(server_summary(str(config)))
        return
    run_mcp_server(str(config))


@app.command()
def health(
    config: Path,
    topic: Annotated[str, typer.Option("--topic")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Show health report for a topic: yield, staleness, coverage, memory."""
    from sonde.mcp_server.tools import artifact_memory, summarize_topic_health

    settings = get_settings()
    report = summarize_topic_health(
        str(config), topic, db_path=str(settings.db_path)
    )
    memory = artifact_memory(topic, db_path=str(settings.db_path))
    report["artifact_memory"] = memory
    if json_output:
        print_json(report)
        return
    console.print(f"Health: {report['topic_id']} ({report['status']} v{report['version']})")
    console.print(f"  Runs: {report['total_runs']}")
    console.print(f"  Artifacts: {report['total_artifacts']}")
    console.print(f"  Errors: {report['total_errors']}")
    console.print(f"  Last run: {report['last_run_at'] or 'never'}")
    console.print(f"  Sources: {', '.join(report['configured_sources'])}")
    if report["missing_sources"]:
        console.print(f"  Missing: {', '.join(report['missing_sources'])}")
    console.print(f"  Queries: {report['query_count']}")
    console.print(f"  Aliases: {report['alias_count']}")
    console.print(f"  Negative terms: {'yes' if report['has_negative_terms'] else 'no'}")
    console.print(f"  Owner: {report['governance']['owner'] or 'unset'}")
    console.print(f"  Unique artifacts seen: {memory['total_unique_artifacts']}")
    console.print(f"  Recurring: {memory['recurring_artifacts']}")
    console.print(f"  Novelty ratio: {memory['novelty_ratio']}")


@app.command()
def inspect(
    artifact_id: str,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect an artifact's full lineage chain."""
    settings = get_settings()
    repo = RegistryRepository(settings.db_path)
    lineage = repo.artifact_lineage(artifact_id)
    if "error" in lineage:
        console.print(f"Error: {lineage['error']}")
        raise typer.Exit(1)
    if json_output:
        print_json(lineage)
        return
    artifact = lineage["artifact"]
    console.print(f"Artifact: {artifact['id']}")
    console.print(f"  Title: {artifact['title']}")
    console.print(f"  Source: {artifact['source']}")
    console.print(f"  URL: {artifact.get('url', 'n/a')}")
    console.print(f"  Collected: {artifact['collected_at']}")
    console.print(f"  Topic: {artifact['topic_id']} v{artifact['topic_version']}")
    console.print(f"  Config hash: {artifact['config_hash'][:12]}...")
    console.print(f"  Run: {artifact['run_id']}")
    run = lineage.get("run")
    if run and "error" not in run:
        console.print(f"  Run status: {run['status']}")
        console.print(f"  Run artifacts: {run['artifact_count']}")


@app.command("version")
def version_cmd() -> None:
    """Print Sonde version."""
    console.print(__version__)
