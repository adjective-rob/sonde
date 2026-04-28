from pathlib import Path

from sonde.cli import app
from sonde.mcp_server.resources import list_resource_templates
from sonde.mcp_server.tools import list_tools


def test_acceptance_mvp(runner, examples_path, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SONDE_DB_PATH", str(tmp_path / "sonde.db"))
    monkeypatch.setenv("SONDE_ARTIFACT_PATH", str(tmp_path / "artifacts"))
    assert runner.invoke(app, ["lint", str(examples_path)]).exit_code == 0
    assert runner.invoke(app, ["dedupe", str(examples_path)]).exit_code == 0
    sim = runner.invoke(
        app,
        [
            "simulate",
            str(examples_path),
            "--topic",
            "agent_security_model",
            "--source",
            "local_jsonl",
        ],
    )
    assert sim.exit_code == 0
    assert "Secure Agent Runtime" in sim.output
    run = runner.invoke(
        app,
        [
            "run",
            str(examples_path),
            "--topic",
            "agent_security_model",
            "--source",
            "local_jsonl",
            "--dry-run",
        ],
    )
    assert run.exit_code == 0
    manifests = list((tmp_path / "artifacts" / "manifests").glob("*.manifest.json"))
    assert manifests
    text = Path(manifests[0]).read_text(encoding="utf-8")
    assert "agent_security_model" in text
    assert "adapter_versions" in text
    assert "artifact_count" in text
    assert "sonde://topics" in list_resource_templates()
    assert "run_topic" in list_tools()
