from topicops.engine.dedupe import dedupe_topics
from topicops.engine.loader import load_topics


def test_dedupe_no_hard_duplicates(examples_path) -> None:
    result = dedupe_topics(load_topics(examples_path), include_near=True)
    assert result.hard_duplicates == []
    assert result.case_insensitive_duplicates == []
