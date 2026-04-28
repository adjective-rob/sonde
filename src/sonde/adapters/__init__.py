from sonde.adapters.arxiv import ArxivAdapter
from sonde.adapters.base import SourceAdapter
from sonde.adapters.github import GitHubAdapter
from sonde.adapters.huggingface import HuggingFaceAdapter
from sonde.adapters.local_jsonl import LocalJsonlAdapter
from sonde.adapters.rss import RSSAdapter


def adapter_registry() -> dict[str, SourceAdapter]:
    adapters: list[SourceAdapter] = [
        LocalJsonlAdapter(),
        GitHubAdapter(),
        ArxivAdapter(),
        HuggingFaceAdapter(),
        RSSAdapter(),
    ]
    return {adapter.id: adapter for adapter in adapters}


__all__ = ["adapter_registry", "SourceAdapter"]
