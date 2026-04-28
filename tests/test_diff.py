from sonde.engine.diff import diff_topics
from sonde.engine.loader import load_topics


def test_diff_same_empty(examples_path) -> None:
    topics = load_topics(examples_path)
    result = diff_topics(topics, topics)
    assert result.added == []
    assert result.changed == []
