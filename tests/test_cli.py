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


def test_ingest_and_trace_cli(tmp_repo: Path, monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_repo)
    assert runner.invoke(app, ["init", "test-person", "--class", "self"]).exit_code == 0

    drop = tmp_path / "talk.md"
    drop.write_text("# Talk\nnotes")
    result = runner.invoke(app, ["ingest", "test-person", "--source", f"file={drop}"])
    assert result.exit_code == 0, result.output
    assert "1 new items" in result.output
    # Incremental: second run adds nothing.
    result = runner.invoke(app, ["ingest", "test-person", "--source", f"file={drop}"])
    assert "0 new items" in result.output

    result = runner.invoke(app, ["trace", "test-person"])
    assert result.exit_code == 0, result.output
    assert "1 traces" in result.output
    assert "Compilability:" in result.output
    assert (tmp_repo / "personas" / "test-person" / "traces" / "traces.jsonl").is_file()


def test_ingest_bad_source_spec(tmp_repo: Path, monkeypatch):
    monkeypatch.chdir(tmp_repo)
    assert runner.invoke(app, ["init", "test-person", "--class", "other"]).exit_code == 0
    result = runner.invoke(app, ["ingest", "test-person", "--source", "nonsense"])
    assert result.exit_code == 2
    result = runner.invoke(app, ["ingest", "missing", "--source", "file=/x"])
    assert result.exit_code == 1


def test_ingest_corrupt_zip_clean_error(tmp_repo: Path, monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_repo)
    assert runner.invoke(app, ["init", "test-person", "--class", "self"]).exit_code == 0
    bad_zip = tmp_path / "archive.zip"
    bad_zip.write_bytes(b"not a zip file")
    result = runner.invoke(app, ["ingest", "test-person", "--source", f"x-archive={bad_zip}"])
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_ingest_malformed_feed_clean_error(tmp_repo: Path, monkeypatch):
    import httpx

    from peoplereadme import cli as cli_mod
    from peoplereadme.ingest.rss import ingest_rss

    monkeypatch.chdir(tmp_repo)
    assert runner.invoke(app, ["init", "test-person", "--class", "self"]).exit_code == 0
    client = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text="<rss><chan"))
    )
    monkeypatch.setattr(cli_mod, "ingest_rss", lambda url: ingest_rss(url, client=client))
    result = runner.invoke(app, ["ingest", "test-person", "--source", "rss=https://x.example/f"])
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
