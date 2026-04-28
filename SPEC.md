# TopicOps SPEC

This repository implements TopicOps: an open-source control plane for declaring,
validating, simulating, running, and governing collection intent across
scrapers, OSINT workflows, feeds, research monitors, and agent-accessible
intelligence systems.

The full seed specification is tracked in the initial project request. The
working implementation in this repository prioritizes the v0.1.0 MVP:

- Pydantic topic, run, artifact, and manifest models.
- YAML/JSON topic loading.
- CLI commands for init, lint, dedupe, diff, simulate, run, status, export, MCP,
  and version.
- Offline `local_jsonl` adapter and simple remote adapter implementations.
- SQLite registry and JSONL/file-backed artifact storage.
- MCP resource, tool, and prompt registration helpers.
- Examples, tests, CI, and autonomous iteration guidance.
