from pathlib import Path

from typer.testing import CliRunner

from peoplereadme import __version__
from peoplereadme.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_and_validate_via_cli(tmp_repo: Path, monkeypatch):
    monkeypatch.chdir(tmp_repo)
    result = runner.invoke(app, ["init", "test-person", "--class", "other"])
    assert result.exit_code == 0, result.output
    assert "Schema validation passed." in result.output

    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0, result.output
    assert "test-person: ok" in result.output
