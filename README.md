# TopicOps

TopicOps is an open-source control plane for collection intent across scrapers,
OSINT workflows, feeds, research monitors, and agent-accessible intelligence
systems.

It is not a scraper. It is the layer above scrapers that makes topics, queries,
sources, schedules, scoring rules, and lineage declarative, versioned, testable,
inspectable, and agent-operable.

## Why Collection Intent Matters

Most collection systems hide their actual intent in scattered YAML, scripts,
seed URLs, RSS lists, API queries, and watchlists. TopicOps turns that hidden
layer into a governed topic pack that can live in Git and produce reproducible
run manifests.

Every collected artifact is designed to answer:

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
uv run topicops init
uv run topicops lint examples/topics.ai.yaml
uv run topicops dedupe examples/topics.ai.yaml --near
uv run topicops simulate examples/topics.ai.yaml --topic agent_security_model --source local_jsonl
uv run topicops run examples/topics.ai.yaml --topic agent_security_model --source local_jsonl --dry-run
uv run topicops mcp --config examples/topics.ai.yaml --summary
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
topicops init
topicops lint <config> [--json] [--strict]
topicops dedupe <config> [--near] [--json]
topicops diff <old_config> <new_config> [--json]
topicops simulate <config> --topic <id> --source <source> [--json]
topicops run <config> --topic <id> [--source <source>] [--dry-run] [--json]
topicops status [--json]
topicops export <config> --tag agents --output exports/agents.topicpack.yaml
topicops mcp --config <config>
topicops version
```

## MCP Usage

Start a server:

```bash
uv run topicops mcp --config examples/topics.ai.yaml
```

Inspect the registered surface without starting stdio MCP:

```bash
uv run topicops mcp --config examples/topics.ai.yaml --summary
```

The MCP layer exposes topic resources, schemas, prompts, and tools for linting,
deduplication, diffing, simulation, dry-run execution, draft topic creation, and
cost estimates. MCP `run_topic` defaults to `dry_run: true`.

## Adapters

- `local_jsonl`: offline fixtures and deterministic tests.
- `github`: GitHub repository search API, using `GITHUB_TOKEN` when present.
- `arxiv`: arXiv Atom API.
- `huggingface`: Hugging Face Hub API, using `HF_TOKEN` when present.
- `rss`: public RSS or Atom feeds.

## Lineage

Runs create manifests under `.topicops/artifacts/manifests/`. The registry is a
local SQLite database at `.topicops/topicops.db` by default. Normalized artifacts
are appended to `.topicops/artifacts/normalized/artifacts.jsonl` for non-dry
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

## Roadmap

- Richer topic quality metrics.
- Topic pack install and export workflows.
- Lightweight web UI for topic editing and run history.
- More source adapters.
- Signed manifests and artifact ledgers.

## Contributing

Run the checks before opening a PR:

```bash
uv run ruff check .
uv run mypy src
uv run pytest --cov=topicops
```
