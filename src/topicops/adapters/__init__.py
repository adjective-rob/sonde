from topicops.adapters.arxiv import ArxivAdapter
from topicops.adapters.base import SourceAdapter
from topicops.adapters.github import GitHubAdapter
from topicops.adapters.huggingface import HuggingFaceAdapter
from topicops.adapters.local_jsonl import LocalJsonlAdapter
from topicops.adapters.rss import RSSAdapter


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
