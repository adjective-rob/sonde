import pytest

from sonde.models.source import TopicSourceConfig
from sonde.models.topic import ScheduleConfig, Topic


def test_topic_validates() -> None:
    topic = Topic(
        id="agent_security_model",
        name="Agent Security Model",
        intent="Track security models for agents.",
        version="1.0.0",
        queries=["agent security model"],
        sources=[TopicSourceConfig(id="local_jsonl", enabled=True, max_results=10)],
        schedule=ScheduleConfig(interval_minutes=60),
    )
    assert topic.id == "agent_security_model"


def test_invalid_semver_fails() -> None:
    with pytest.raises(ValueError):
        Topic(
            id="agent_security_model",
            name="Agent Security Model",
            intent="Track security models for agents.",
            version="one",
            queries=["agent security model"],
            sources=[TopicSourceConfig(id="local_jsonl", enabled=True, max_results=10)],
            schedule=ScheduleConfig(interval_minutes=60),
        )
