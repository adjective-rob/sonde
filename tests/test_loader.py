from topicops.engine.loader import load_topics


def test_load_topics(examples_path) -> None:
    topics = load_topics(examples_path)
    assert topics[0].id == "agent_security_model"
