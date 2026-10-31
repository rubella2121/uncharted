import pytest
from typer.testing import CliRunner

from guard import cli, db as dbmod

runner = CliRunner()


@pytest.fixture(autouse=True)
def fake_db(db, monkeypatch):
    monkeypatch.setattr(dbmod, "get_db", lambda: db)
    return db


def invoke(*args):
    return runner.invoke(cli.app, list(args))


def test_full_demo_flow_exit_codes():
    assert invoke("seed").exit_code == 0
    assert invoke("run", "v1").exit_code == 0
    assert invoke("run", "v2").exit_code == 0
    res = invoke("compare", "v1", "v2")
    assert res.exit_code == 1 and "NOT SAFE" in res.output and "REGRESSED" in res.output
    invoke("run", "v3")
    assert invoke("compare", "v1", "v3").exit_code == 2


def test_timeouts_give_inconclusive():
    invoke("seed")
    invoke("run", "v1")
    res = invoke("run", "v3", "--simulate-timeouts", "tc03,tc05,tc09")
    assert "TIMEOUT" in res.output
    res = invoke("compare", "v1", "v3")
    assert res.exit_code == 2 and "INCONCLUSIVE" in res.output


def test_unknown_version_exits_3():
    invoke("seed")
    res = invoke("run", "v99")
    assert res.exit_code == 3 and "not found" in res.output


def test_compare_without_runs_exits_3():
    invoke("seed")
    assert invoke("compare", "v1", "v2").exit_code == 3


def test_demo_duplicate_and_history_and_reset(fake_db):
    invoke("seed")
    invoke("run", "v1")
    assert "duplicate" in invoke("demo-duplicate").output
    assert "run_v1_" in invoke("history").output
    assert invoke("reset", "--yes").exit_code == 0
    assert fake_db["eval_results"].count_documents({}) == 0
