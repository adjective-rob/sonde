# CODEX.md

This file is intentionally mirrored from `CODEX.md` so Codex and Claude Code
receive the same project guidance.

## Project Intent

Sonde is a local-first Python control plane for declaring, validating,
simulating, running, and governing collection intent. The core artifact is a
versioned topic pack that describes what to watch, where to collect from, how to
score results, and how to preserve lineage.

## Operating Rules

- Keep the project Python 3.12+ and `uv` managed.
- Prefer local, deterministic behavior before adding network features.
- Do not require API tokens for tests or demos.
- Use `local_jsonl` as the default offline demonstration adapter.
- Preserve lineage on every artifact: topic ID, version, config hash, run ID,
  source, source record hash, and adapter version.
- Do not log secrets or write environment variables to manifests.
- MCP write tools should be conservative, diff-oriented, and default collection
  execution to dry runs.

## Development Commands

```bash
uv sync --all-extras
uv run sonde version
uv run sonde lint examples/topics.ai.yaml
uv run sonde dedupe examples/topics.ai.yaml --near
uv run sonde simulate examples/topics.ai.yaml --topic agent_security_model --source local_jsonl
uv run sonde run examples/topics.ai.yaml --topic agent_security_model --source local_jsonl --dry-run
uv run pytest
uv run ruff check .
uv run mypy src
```

## Scope Bias

Build the narrow working thing first: valid topic files, no hard duplicates,
local simulation, run manifests, registry persistence, and MCP tools/resources.
Adapters for remote services should be simple, respectful API clients with
mocked tests.
