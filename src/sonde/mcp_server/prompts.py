from __future__ import annotations

from pathlib import Path

EXPECTED_PROMPTS = [
    "review_topic_quality",
    "create_collection_strategy",
    "expand_topic_aliases",
    "deprecate_noisy_topic",
    "write_signal_report",
    "recommend_topic_deprecations",
]


def list_prompts() -> list[str]:
    return EXPECTED_PROMPTS


def read_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.md"
    return path.read_text(encoding="utf-8")
