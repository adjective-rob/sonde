from sonde.engine.lineage import hash_canonical, normalize_text, slugify_topic_id


def test_hash_stable() -> None:
    assert hash_canonical({"b": 1, "a": 2}) == hash_canonical({"a": 2, "b": 1})


def test_normalization() -> None:
    assert normalize_text('  "Agent   Security" ') == "agent security"
    assert slugify_topic_id("Agent Security Model") == "agent_security_model"
