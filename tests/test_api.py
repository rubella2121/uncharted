import time

import pytest
from fastapi.testclient import TestClient

from guard import api, config, db as dbmod


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(dbmod, "get_db", lambda: db)
    monkeypatch.setattr(api, "LIVE_DELAY_S", 0)
    with TestClient(api.app) as c:  # runs lifespan: schema + auto-seed
        yield c


def wait_for_run(client, run_id, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()["run"]
        if run["status"] != "running":
            return run
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def test_startup_seeds_demo_data(client):
    assert [v["version"] for v in client.get("/api/versions").json()] == ["v1", "v2", "v3"]
    assert len(client.get("/api/test-cases").json()) == 12


def test_background_run_then_compare(client):
    r1 = client.post("/api/runs", json={"version": "v1"}).json()
    assert r1["status"] == "running"
    assert wait_for_run(client, r1["run_id"])["status"] == "completed"
    r2 = client.post("/api/runs", json={"version": "v2"}).json()
    wait_for_run(client, r2["run_id"])

    detail = client.get(f"/api/runs/{r2['run_id']}").json()
    assert len(detail["results"]) == 12
    assert isinstance(detail["results"][0]["timestamp"], str)  # serialised as ISO

    res = client.post("/api/compare", json={"baseline": "v1", "candidate": "v2"}).json()
    assert res["verdict"] == "NOT_SAFE" and res["exit_code"] == 1
    assert client.get("/api/comparisons/latest").json()["verdict"] == "NOT_SAFE"
    assert len(client.get("/api/runs").json()) == 2


def test_synchronous_run_with_timeouts(client):
    client.post("/api/runs", json={"version": "v1", "wait": True})
    run = client.post("/api/runs", json={"version": "v3", "wait": True,
                                         "simulate_timeouts": ["tc03", "tc05", "tc09"]}).json()
    assert run["status"] == "completed_with_errors"
    res = client.post("/api/compare", json={"baseline": "v1", "candidate": "v3"}).json()
    assert res["verdict"] == "INCONCLUSIVE"


def test_errors_map_to_http_codes(client):
    assert client.post("/api/runs", json={"version": "v99"}).status_code == 404
    assert client.post("/api/compare", json={"baseline": "v1", "candidate": "v2"}).status_code == 404
    assert client.get("/api/runs/run_nope").status_code == 404
    assert client.post("/api/demo/duplicate").status_code == 400


def test_demo_endpoints(client, db):
    client.post("/api/runs", json={"version": "v1", "wait": True})
    dup = client.post("/api/demo/duplicate").json()
    assert dup["outcome"] == "duplicate" and dup["count_before"] == dup["count_after"]
    assert "outcome" in client.post("/api/demo/incomplete").json()
    assert client.post("/api/demo/reset").json() == {"ok": True}
    assert db[config.EVAL_RESULTS].count_documents({}) == 0


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["project_id"] == config.PROJECT_ID


def test_stream_falls_back_to_polling_without_change_streams(client):
    # mongomock has no change streams, so the stream must say "polling" and end cleanly
    with client.stream("GET", "/api/stream") as resp:
        body = "".join(resp.iter_text())
    assert "event: mode" in body and '"polling"' in body


def test_index_page(client):
    assert client.get("/").status_code == 200


def test_change_stream_pipeline_filters_collections():
    match = api.change_stream_pipeline()[0]["$match"]
    assert set(match["ns.coll"]["$in"]) == {config.EVAL_RESULTS, config.EVAL_RUNS,
                                            config.COMPARISONS}
