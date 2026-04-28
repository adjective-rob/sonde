# Sonde

Sonde is an MCP-native topic registry for GitHub, arXiv, Hugging Face, RSS, and
web monitors. Declare what you're watching, simulate before you collect, and give
agents governed access to fresh signal with full lineage.

It is not a scraper. It is the layer above scrapers that makes topics, queries,
sources, schedules, scoring rules, and lineage declarative, versioned, testable,
inspectable, and agent-operable.

## Why

Most collection systems hide their actual intent in scattered YAML, scripts,
seed URLs, RSS lists, API queries, and watchlists. Sonde turns that hidden
layer into a governed topic pack that can live in Git and produce reproducible
run manifests.

Every collected artifact answers:

- Which topic and topic version produced this?
- Which config hash produced this?
- Which adapter and source query produced this?
- When was it collected?
- What raw or normalized source record did it come from?

## Installation

```bash
uv sync --all-extras
```

## Quickstart

```bash
uv run sonde init
uv run sonde lint examples/topics.ai.yaml
uv run sonde dedupe examples/topics.ai.yaml --near
uv run sonde simulate examples/topics.ai.yaml --topic agent_security_model --source local_jsonl
uv run sonde run examples/topics.ai.yaml --topic agent_security_model --source local_jsonl --dry-run
uv run sonde mcp --config examples/topics.ai.yaml --summary
```

## Example Topic

```yaml
topics:
  - id: "agent_security_model"
    name: "Agent Security Model"
    intent: "Track emerging work on identity, permissioning, isolation, and threat models for AI agents."
    status: "active"
    priority: "high"
    version: "1.0.0"
    owner: "adjective"
    queries:
      - "agent security model"
      - "AI agent permissioning"
    negative_terms:
      - "real estate agent"
      - "insurance agent"
    sources:
      - id: "local_jsonl"
        enabled: true
        max_results: 10
    schedule:
      interval_minutes: 120
```

## CLI

```bash
sonde init
sonde lint <config> [--json] [--strict]
sonde dedupe <config> [--near] [--json]
sonde diff <old_config> <new_config> [--json]
sonde simulate <config> --topic <id> --source <source> [--json]
sonde run <config> --topic <id> [--source <source>] [--dry-run] [--json]
sonde status [--json]
sonde export <config> --tag agents --output exports/agents.topicpack.yaml
sonde mcp --config <config>
sonde version
```

## MCP Server

Start a server:

```bash
uv run sonde mcp --config examples/topics.ai.yaml
```

Inspect the registered surface without starting stdio MCP:

```bash
uv run sonde mcp --config examples/topics.ai.yaml --summary
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `lint_topics` | Validate a topic config |
| `dedupe_topics` | Find duplicate and overlapping topics |
| `find_semantic_overlap` | Detect semantic overlap between topics |
| `diff_topics` | Compare two topic configs |
| `simulate_topic` | Sample expected yield and noise for a topic |
| `estimate_collection_cost` | Estimate API requests, artifacts, and storage |
| `run_topic_dry_run` | Execute a dry run and return the manifest |
| `create_topic_draft` | Create a new draft topic (returns diff) |
| `update_topic_draft` | Modify a topic (returns diff) |
| `deprecate_topic` | Transition a topic to deprecated status |
| `promote_topic` | Promote a draft topic to active |
| `rollback_topic_version` | Roll back to a previous topic version |
| `generate_aliases` | Generate query aliases from intent |
| `generate_negative_terms` | Generate negative terms to reduce noise |
| `summarize_topic_health` | Health report: yield, noise, staleness, coverage |

### MCP Resources

| URI | Description |
|-----|-------------|
| `sonde://topics` | All topics (summary) |
| `sonde://topics/{topic_id}` | Full topic definition |
| `sonde://topics/{topic_id}/versions` | Version history for a topic |
| `sonde://topics/{topic_id}/quality` | Quality metrics for a topic |
| `sonde://sources` | All configured source IDs |
| `sonde://runs` | Recent collection runs |
| `sonde://runs/{run_id}` | Full run manifest |
| `sonde://artifacts/{artifact_id}` | Single artifact with lineage |
| `sonde://lineage/artifact/{artifact_id}` | Lineage chain for an artifact |
| `sonde://diffs/{from_version}/{to_version}` | Diff between topic versions |
| `sonde://schema/topic` | Topic JSON schema |
| `sonde://schema/artifact` | Artifact JSON schema |

### MCP Prompts

| Prompt | Description |
|--------|-------------|
| `review_topic_quality` | Review yield, noise, overlap, and versioning |
| `create_collection_strategy` | Design a collection strategy for a domain |
| `expand_topic_aliases` | Expand aliases and negative terms |
| `deprecate_noisy_topic` | Draft a deprecation decision |
| `write_signal_report` | Summarize recent signal for a topic |
| `recommend_topic_deprecations` | Identify candidates for deprecation |

## Adapters

- `local_jsonl`: offline fixtures and deterministic tests.
- `github`: GitHub repository search API, using `GITHUB_TOKEN` when present.
- `arxiv`: arXiv Atom API.
- `huggingface`: Hugging Face Hub API, using `HF_TOKEN` when present.
- `rss`: public RSS or Atom feeds.

## Lineage

Runs create manifests under `.sonde/artifacts/manifests/`. The registry is a
local SQLite database at `.sonde/sonde.db` by default. Normalized artifacts
are appended to `.sonde/artifacts/normalized/artifacts.jsonl` for non-dry
runs.

## Safety Policy

- Respect robots.txt where applicable.
- Respect API terms of service.
- Do not bypass paywalls, CAPTCHAs, login walls, access controls, or rate limits.
- Do not collect credentials, private personal data, or protected information.
- Do not provide evasion features.
- Use clear user-agent strings for HTTP clients.
- Prefer official APIs, feeds, and public datasets.
- Store secrets only in environment variables.
- Never write tokens into manifests, logs, or artifacts.

## Contributing

Run the checks before opening a PR:

```bash
uv run ruff check .
uv run mypy src
uv run pytest --cov=sonde
```

## License

MIT
