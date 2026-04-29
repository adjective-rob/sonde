from __future__ import annotations

from sonde.mcp_server.prompts import list_prompts
from sonde.mcp_server.resources import list_resource_templates
from sonde.mcp_server.tools import list_tools


def server_summary(config_path: str) -> dict[str, object]:
    return {
        "config_path": config_path,
        "resources": list_resource_templates(),
        "tools": list_tools(),
        "prompts": list_prompts(),
    }


def run_mcp_server(config_path: str) -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("mcp package is installed but FastMCP could not be imported") from exc

    from sonde.mcp_server.prompts import read_prompt
    from sonde.mcp_server.resources import read_resource
    from sonde.mcp_server.tools import (
        apply_diff,
        artifact_memory,
        create_topic_draft,
        dedupe_topics_tool,
        deprecate_topic,
        diff_topics_tool,
        estimate_collection_cost,
        find_semantic_overlap,
        generate_aliases,
        generate_negative_terms,
        lint_topics,
        promote_topic,
        rollback_topic_version,
        run_topic_dry_run,
        simulate_topic_tool,
        summarize_topic_health,
        update_topic_draft,
    )

    mcp = FastMCP("Sonde")

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    @mcp.resource("sonde://topics")
    def resource_topics() -> str:
        return str(read_resource("sonde://topics", config_path=config_path))

    @mcp.resource("sonde://sources")
    def resource_sources() -> str:
        return str(read_resource("sonde://sources", config_path=config_path))

    @mcp.resource("sonde://runs")
    def resource_runs() -> str:
        return str(read_resource("sonde://runs", config_path=config_path))

    @mcp.resource("sonde://schema/topic")
    def resource_schema_topic() -> str:
        return str(read_resource("sonde://schema/topic", config_path=config_path))

    @mcp.resource("sonde://schema/artifact")
    def resource_schema_artifact() -> str:
        return str(read_resource("sonde://schema/artifact", config_path=config_path))

    @mcp.resource("sonde://topics/{topic_id}")
    def resource_topic(topic_id: str) -> str:
        return str(read_resource(f"sonde://topics/{topic_id}", config_path=config_path))

    @mcp.resource("sonde://topics/{topic_id}/versions")
    def resource_topic_versions(topic_id: str) -> str:
        return str(read_resource(f"sonde://topics/{topic_id}/versions", config_path=config_path))

    @mcp.resource("sonde://topics/{topic_id}/quality")
    def resource_topic_quality(topic_id: str) -> str:
        return str(read_resource(f"sonde://topics/{topic_id}/quality", config_path=config_path))

    @mcp.resource("sonde://runs/{run_id}")
    def resource_run(run_id: str) -> str:
        return str(read_resource(f"sonde://runs/{run_id}", config_path=config_path))

    @mcp.resource("sonde://artifacts/{artifact_id}")
    def resource_artifact(artifact_id: str) -> str:
        return str(read_resource(f"sonde://artifacts/{artifact_id}", config_path=config_path))

    @mcp.resource("sonde://lineage/artifact/{artifact_id}")
    def resource_lineage(artifact_id: str) -> str:
        return str(
            read_resource(f"sonde://lineage/artifact/{artifact_id}", config_path=config_path)
        )

    @mcp.resource("sonde://diffs/{from_version}/{to_version}")
    def resource_diff(from_version: str, to_version: str) -> str:
        return str(
            read_resource(f"sonde://diffs/{from_version}/{to_version}", config_path=config_path)
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @mcp.tool()
    def tool_lint_topics(config_path: str = config_path) -> dict[str, object]:
        """Validate a topic config file. Returns errors, warnings, and topic count."""
        return lint_topics(config_path)

    @mcp.tool()
    def tool_dedupe_topics(
        config_path: str = config_path, include_near: bool = True
    ) -> dict[str, object]:
        """Find duplicate and overlapping topics in a config."""
        return dedupe_topics_tool(config_path, include_near_overlaps=include_near)

    @mcp.tool()
    def tool_find_semantic_overlap(config_path: str = config_path) -> dict[str, object]:
        """Detect semantic overlap between all topics using fuzzy matching."""
        return find_semantic_overlap(config_path)

    @mcp.tool()
    def tool_diff_topics(old_config: str, new_config: str) -> dict[str, object]:
        """Compare two topic config files and show added, removed, changed topics."""
        return diff_topics_tool(old_config, new_config)

    @mcp.tool()
    def tool_simulate_topic(
        topic_id: str, source: str = "local_jsonl", limit: int = 20,
        config_path: str = config_path,
    ) -> dict[str, object]:
        """Sample expected yield and noise for a topic from a source."""
        return simulate_topic_tool(config_path, topic_id, source, limit=limit)

    @mcp.tool()
    def tool_estimate_collection_cost(
        topic_id: str, interval_hours: int = 24, config_path: str = config_path,
    ) -> dict[str, object]:
        """Estimate API requests, artifacts, and storage cost for a topic."""
        return estimate_collection_cost(config_path, topic_id, interval_hours=interval_hours)

    @mcp.tool()
    def tool_run_topic_dry_run(
        topic_id: str,
        sources: list[str] | None = None,
        config_path: str = config_path,
    ) -> dict[str, object]:
        """Execute a dry run for a topic. Safe — never writes artifacts."""
        return run_topic_dry_run(config_path, topic_id, sources=sources)

    @mcp.tool()
    def tool_create_topic_draft(
        id: str,
        name: str,
        intent: str,
        queries: list[str],
        sources: list[str],
        config_path: str = config_path,
    ) -> dict[str, object]:
        """Create a new draft topic. Returns proposed diff — does not write to file."""
        return create_topic_draft(config_path, id, name, intent, queries, sources)

    @mcp.tool()
    def tool_update_topic_draft(
        topic_id: str, patch: dict[str, object], config_path: str = config_path,
    ) -> dict[str, object]:
        """Modify a topic. Returns proposed diff — does not write to file."""
        return update_topic_draft(config_path, topic_id, patch)

    @mcp.tool()
    def tool_deprecate_topic(
        topic_id: str,
        reason: str,
        replacement_id: str | None = None,
        config_path: str = config_path,
    ) -> dict[str, object]:
        """Deprecate a topic with a reason. Returns proposed diff."""
        return deprecate_topic(config_path, topic_id, reason, replacement_id=replacement_id)

    @mcp.tool()
    def tool_promote_topic(
        topic_id: str, owner: str | None = None, config_path: str = config_path,
    ) -> dict[str, object]:
        """Promote a draft or paused topic to active. Returns proposed diff."""
        return promote_topic(config_path, topic_id, owner=owner)

    @mcp.tool()
    def tool_rollback_topic_version(
        topic_id: str, target_version: str, config_path: str = config_path,
    ) -> dict[str, object]:
        """Roll back a topic to a previous version from the registry."""
        return rollback_topic_version(config_path, topic_id, target_version)

    @mcp.tool()
    def tool_generate_aliases(
        topic_id: str, intent: str, queries: list[str],
    ) -> dict[str, object]:
        """Generate query aliases and tags from a topic's intent and queries."""
        return generate_aliases(topic_id, intent, queries)

    @mcp.tool()
    def tool_generate_negative_terms(
        topic_id: str, intent: str, queries: list[str],
    ) -> dict[str, object]:
        """Generate negative terms to reduce noise for a topic."""
        return generate_negative_terms(topic_id, intent, queries)

    @mcp.tool()
    def tool_summarize_topic_health(
        topic_id: str, config_path: str = config_path,
    ) -> dict[str, object]:
        """Health report: yield, noise, staleness, source coverage for a topic."""
        return summarize_topic_health(config_path, topic_id)

    @mcp.tool()
    def tool_apply_diff(
        proposed_yaml: str, config_path: str = config_path,
    ) -> dict[str, object]:
        """Apply a previously proposed diff after human review. Validates before writing."""
        return apply_diff(config_path, proposed_yaml)

    @mcp.tool()
    def tool_artifact_memory(topic_id: str) -> dict[str, object]:
        """Return artifact memory stats: unique vs recurring artifacts across runs."""
        return artifact_memory(topic_id)

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    @mcp.prompt()
    def review_topic_quality(topic_id: str, days: int = 30) -> str:
        """Review topic quality: yield, noise, overlap, and versioning recommendations."""
        template = read_prompt("review_topic_quality")
        return template.replace("{{ topic_id }}", topic_id).replace("{{ days }}", str(days))

    @mcp.prompt()
    def create_collection_strategy(domain: str, sources: str = "github,arxiv") -> str:
        """Design a collection strategy for a domain with topic drafts."""
        template = read_prompt("create_collection_strategy")
        return template.replace("{{ domain }}", domain).replace("{{ sources }}", sources)

    @mcp.prompt()
    def expand_topic_aliases(topic_id: str) -> str:
        """Expand aliases and negative terms for a topic."""
        template = read_prompt("expand_topic_aliases")
        return template.replace("{{ topic_id }}", topic_id)

    @mcp.prompt()
    def deprecate_noisy_topic(topic_id: str, reason: str) -> str:
        """Draft a deprecation decision for a noisy topic."""
        template = read_prompt("deprecate_noisy_topic")
        return template.replace("{{ topic_id }}", topic_id).replace("{{ reason }}", reason)

    @mcp.prompt()
    def write_signal_report(topic_id: str, days: int = 7) -> str:
        """Write a signal report for a topic covering recent days."""
        template = read_prompt("write_signal_report")
        return template.replace("{{ topic_id }}", topic_id).replace("{{ days }}", str(days))

    @mcp.prompt()
    def recommend_topic_deprecations() -> str:
        """Identify topics that are candidates for deprecation."""
        return read_prompt("recommend_topic_deprecations")

    mcp.run()
