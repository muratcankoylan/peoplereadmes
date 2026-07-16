import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from peoplereadme.evidence import EvidenceItem


def make_client(tmp_repo: Path, monkeypatch) -> TestClient:
    import peoplereadme.webapp.server as server

    monkeypatch.chdir(tmp_repo)
    return TestClient(server.app)


def wait_job(client: TestClient, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_create_list_and_summary(tmp_repo: Path, monkeypatch):
    client = make_client(tmp_repo, monkeypatch)
    resp = client.post(
        "/api/personas", json={"persona_id": "web-test", "persona_class": "self"}
    )
    assert resp.status_code == 200
    assert resp.json()["persona_class"] == "self"
    # Duplicate -> 409, invalid class -> 422
    assert (
        client.post(
            "/api/personas", json={"persona_id": "web-test", "persona_class": "self"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/personas", json={"persona_id": "x", "persona_class": "bogus"}
        ).status_code
        == 422
    )
    ids = [p["persona_id"] for p in client.get("/api/personas").json()]
    assert "web-test" in ids
    assert client.get("/api/personas/missing").status_code == 404


def test_ingest_job_runs_sources_and_traces(tmp_repo: Path, monkeypatch):
    import peoplereadme.webapp.server as server

    client = make_client(tmp_repo, monkeypatch)
    client.post("/api/personas", json={"persona_id": "web-p", "persona_class": "self"})

    def fake_run_source(spec: str):
        assert spec == "github=someone"
        items = [
            EvidenceItem(
                source="github",
                url=f"https://github.com/someone/r/commit/{i}",
                timestamp=f"2026-01-{i:02d}T00:00:00Z",
                content=f"commit message {i}",
                kind="commit",
                extra={"repo": "someone/r"},
            )
            for i in range(1, 6)
        ]
        return items, items[-1].timestamp

    monkeypatch.setattr(server, "run_source", fake_run_source)
    job = client.post(
        "/api/personas/web-p/ingest", json={"github_username": "someone"}
    ).json()
    job = wait_job(client, job["id"])
    assert job["status"] == "done", job["error"]
    assert job["result"]["n_traces"] == 5

    summary = client.get("/api/personas/web-p").json()
    assert summary["n_traces"] == 5
    assert summary["evidence"]["github"] == 5
    traces = client.get("/api/personas/web-p/traces").json()
    assert len(traces) == 5
    evidence = client.get("/api/personas/web-p/evidence").json()
    assert len(evidence) == 5
    # Empty request rejected
    assert client.post("/api/personas/web-p/ingest", json={}).status_code == 422


def test_ingest_job_survives_source_failure(tmp_repo: Path, monkeypatch):
    import peoplereadme.webapp.server as server

    client = make_client(tmp_repo, monkeypatch)
    client.post("/api/personas", json={"persona_id": "web-f", "persona_class": "self"})

    import httpx

    def failing_run_source(spec: str):
        if spec.startswith("x-api"):
            raise ValueError("X account @nobody has zero tweets according to the API")
        raise httpx.HTTPStatusError(
            "rate limit exceeded", request=httpx.Request("GET", "https://api.github.com"),
            response=httpx.Response(403),
        )

    monkeypatch.setattr(server, "run_source", failing_run_source)
    job = client.post(
        "/api/personas/web-f/ingest",
        json={"x_username": "nobody", "github_username": "nobody"},
    ).json()
    job = wait_job(client, job["id"])
    assert job["status"] == "done"
    assert any("zero tweets" in line for line in job["log"])
    assert any("rate limit" in line for line in job["log"])
    assert job["result"]["added"] == 0


def test_generate_package_condition(tmp_repo: Path, monkeypatch):
    import peoplereadme.webapp.server as server

    client = make_client(tmp_repo, monkeypatch)
    client.post("/api/personas", json={"persona_id": "web-g", "persona_class": "self"})

    class FakeLM:
        model = "fake"

        def complete(self, system: str, user: str) -> str:
            return f"persona output for: {user}"

    monkeypatch.setattr(server, "build_lm", lambda *a, **kw: FakeLM())
    resp = client.post(
        "/api/personas/web-g/generate", json={"task": "write a short post"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["condition"] == "package"
    assert "write a short post" in body["output"]


def test_pairs_endpoint_joins_answers(tmp_repo: Path, monkeypatch):
    client = make_client(tmp_repo, monkeypatch)
    client.post("/api/personas", json={"persona_id": "web-pairs", "persona_class": "self"})
    cal_dir = tmp_repo / "personas" / "web-pairs" / "evals" / "fidelity" / "calibration"
    cal_dir.mkdir(parents=True)
    row = {
        "pair_id": "trace_000001",
        "candidate_a": "real text",
        "candidate_b": "generated text",
    }
    (cal_dir / "2026-01-01.jsonl").write_text(json.dumps(row) + "\n")
    (cal_dir / "2026-01-01.answers.json").write_text(
        json.dumps({"trace_000001": {"real": "A", "judge_pick": "B"}})
    )
    pairs = client.get("/api/personas/web-pairs/pairs").json()
    assert pairs[0]["real"] == "real text"
    assert pairs[0]["generated"] == "generated text"
    assert pairs[0]["judge_correct"] is False


def test_index_served(tmp_repo: Path, monkeypatch):
    client = make_client(tmp_repo, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "peoplereadme" in resp.text
