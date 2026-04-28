from topicops.cli import app


def test_cli_version(runner) -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_lint(runner, examples_path) -> None:
    result = runner.invoke(app, ["lint", str(examples_path)])
    assert result.exit_code == 0
    assert "topics parsed" in result.output
