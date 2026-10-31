import pytest
from typer.testing import CliRunner

from guard import cli, config, db as dbmod
from guard.compare import compare_runs
from guard.report import MARKER, markdown_report
from guard.runner import run_eval
from guard.seed import seed

GIT = {"sha": "a1b2c3d4e5f6", "short": "a1b2c3d", "pr": 4, "branch": "cheaper-prompt",
       "repo": "team/uncharted", "source": "github-actions",
       "commit_url": "https://github.com/team/uncharted/commit/a1b2c3d4e5f6",
       "pr_url": "https://github.com/team/uncharted/pull/4"}


@pytest.fixture
def runs(db):
    seed(db)
    run_eval(db, "v1", run_id="run_v1")
    run_eval(db, "v2", run_id="run_v2", git=GIT)
    run_eval(db, "v3", run_id="run_v3")
    run_eval(db, "v3", run_id="run_v3_t", simulate_timeouts={"tc03"})
    return db


def test_run_stores_git_metadata(runs):
    assert runs[config.EVAL_RUNS].find_one({"_id": "run_v2"})["git"]["pr"] == 4
    assert "git" not in runs[config.EVAL_RUNS].find_one({"_id": "run_v1"})


def test_comparison_carries_git(runs):
    c = compare_runs(runs, "run_v1", "run_v2")
    assert c["candidate_git"]["short"] == "a1b2c3d" and c["baseline_git"] is None


def test_not_safe_report(runs):
    md = markdown_report(runs, compare_runs(runs, "run_v1", "run_v2"), "https://guard.example.com")
    assert md.startswith(MARKER)
    assert "❌ NOT SAFE TO SHIP" in md
    assert "PR #4" in md and "[`a1b2c3d`](https://github.com/team/uncharted/commit/a1b2c3d4e5f6)" in md
    assert "### ❌ Regressed (5)" in md
    # each regression explains itself with the failing check
    assert "customer shares card number" in md and "forbidden match '4111 1111 1111 1111'" in md
    assert "`contains_keyword`: 'sorry' not found" in md
    assert "### ✅ Fixed (1)" in md and "`tc10`" in md
    assert "24 case(s) still passing" in md
    assert "Exit code `1`" in md and "[Open the dashboard](https://guard.example.com/)" in md


def test_risky_and_inconclusive_reports(runs):
    risky = markdown_report(runs, compare_runs(runs, "run_v1", "run_v3"))
    assert "⚠️ RISKY" in risky and "p95 latency +" in risky and "Regressed" not in risky
    assert "Open the dashboard" not in risky
    inc = markdown_report(runs, compare_runs(runs, "run_v1", "run_v3_t"))
    assert "❔ INCONCLUSIVE" in inc and "### ❔ Could not verify (1)" in inc
    assert "timeout: model did not respond" in inc


def test_pipes_in_text_do_not_break_tables(runs):
    runs[config.TEST_CASES].update_one({"_id": "tc02"}, {"$set": {"name": "a | b"}})
    md = markdown_report(runs, compare_runs(runs, "run_v1", "run_v2"))
    assert "a \\| b" in md


def test_cli_compare_writes_markdown_even_when_failing(runs, monkeypatch, tmp_path):
    monkeypatch.setattr(dbmod, "get_db", lambda: runs)
    out = tmp_path / "report.md"
    res = CliRunner().invoke(cli.app, ["compare", "run_v1", "run_v2", "--markdown", str(out)])
    assert res.exit_code == 1
    assert "NOT SAFE TO SHIP" in out.read_text(encoding="utf-8")
