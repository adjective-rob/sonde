from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def examples_path() -> Path:
    return Path("examples/topics.ai.yaml")
