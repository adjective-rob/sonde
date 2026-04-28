from sonde.engine.linter import lint_config


def test_lint_examples_passes(examples_path) -> None:
    result = lint_config(examples_path)
    assert result.ok
    assert result.topics_parsed >= 2
