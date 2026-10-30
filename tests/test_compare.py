import pytest

from guard import config
from guard.compare import (RunNotFound, compare_runs, decide, exit_code, p95,
                           pct_change, resolve_run, run_stats)
from guard.runner import run_eval
from guard.seed import seed


@pytest.fixture
def history(db):
    """The full demo story: v1 baseline, v2 cheap, v3 few-shot, v3 with timeouts."""
    seed(db)
    run_eval(db, "v1", run_id="run_v1")
    run_eval(db, "v2", run_id="run_v2")
    run_eval(db, "v3", run_id="run_v3")
    run_eval(db, "v3", run_id="run_v3_timeouts", simulate_timeouts={"tc03", "tc05", "tc09"})
    return db


def changes(cmp):
    return {r["test_case_id"]: r["change"] for r in cmp["rows"]}


def test_v1_to_v2_is_not_safe(history):
    c = compare_runs(history, "run_v1", "run_v2")
    assert c["verdict"] == "NOT_SAFE"
    assert c["counts"] == {"regressed": 3, "fixed": 1, "still_passing": 8,
                           "still_failing": 0, "unverified": 0}
    ch = changes(c)
    assert [k for k, v in ch.items() if v == "regressed"] == ["tc02", "tc07", "tc11"]
    assert ch["tc10"] == "fixed"
    assert "tc02, tc07, tc11" in c["reasons"][0]
    # cheaper and faster, but still blocked
    assert c["metrics"]["cost_change_pct"] < -80
    assert c["metrics"]["p95_change_pct"] < 0


def test_v1_to_v3_is_risky(history):
    c = compare_runs(history, "run_v1", "run_v3")
    assert c["verdict"] == "RISKY"
    assert c["counts"]["regressed"] == 0 and c["counts"]["fixed"] == 1
    assert c["metrics"]["p95_change_pct"] > config.LATENCY_THRESHOLD_PCT
    assert c["metrics"]["cost_change_pct"] > config.COST_THRESHOLD_PCT
    assert any("p95" in r for r in c["reasons"]) and any("cost" in r for r in c["reasons"])


def test_v1_to_v3_with_timeouts_is_inconclusive(history):
    c = compare_runs(history, "run_v1", "run_v3_timeouts")
    assert c["verdict"] == "INCONCLUSIVE"
    assert c["counts"]["unverified"] == 3
    assert {k for k, v in changes(c).items() if v == "unverified"} == {"tc03", "tc05", "tc09"}


def test_regression_beats_missing_data(history):
    # v2 with timeouts still contains proven regressions -> NOT_SAFE, not INCONCLUSIVE
    run_eval(history, "v2", run_id="run_v2_t", simulate_timeouts={"tc01"})
    assert compare_runs(history, "run_v1", "run_v2_t")["verdict"] == "NOT_SAFE"


def test_identical_versions_are_safe(history):
    run_eval(history, "v1", run_id="run_v1_again")
    c = compare_runs(history, "run_v1", "run_v1_again")
    assert c["verdict"] == "SAFE" and c["counts"]["still_failing"] == 1


def test_missing_case_in_candidate_is_unverified(history):
    history[config.EVAL_RESULTS].delete_one({"run_id": "run_v3", "test_case_id": "tc04"})
    c = compare_runs(history, "run_v1", "run_v3")
    assert changes(c)["tc04"] == "unverified" and c["verdict"] == "INCONCLUSIVE"


def test_comparison_is_upserted_once(history):
    a = compare_runs(history, "run_v1", "run_v2")
    b = compare_runs(history, "run_v1", "run_v2")
    assert a["_id"] == b["_id"]
    assert history[config.COMPARISONS].count_documents({}) == 1


def test_versions_resolve_to_latest_finished_run(history):
    assert resolve_run(history, "v1")["_id"] == "run_v1"
    assert compare_runs(history, "v1", "v2")["candidate_run"] == "run_v2"


def test_unknown_run(history):
    with pytest.raises(RunNotFound):
        compare_runs(history, "v1", "v42")


def test_same_run_rejected(history):
    with pytest.raises(ValueError, match="same run"):
        compare_runs(history, "run_v1", "run_v1")


def test_different_test_sets_warn(history):
    history[config.EVAL_RUNS].update_one({"_id": "run_v2"}, {"$set": {"test_set_hash": "x"}})
    assert compare_runs(history, "run_v1", "run_v2")["warnings"]


def test_stats_ignore_timeouts_for_latency(history):
    s = run_stats(history, "run_v3_timeouts")
    assert s["total"] == 12 and s["errors"] == 3 and s["ok_count"] == 9
    assert s["p95_ms"] is not None and s["p95_ms"] < 2000


def test_stats_of_empty_run(db):
    assert run_stats(db, "nope")["total"] == 0


def test_p95_nearest_rank():
    assert p95([]) is None
    assert p95([5]) == 5
    assert p95(list(range(1, 101))) == 95
    assert p95([500] * 94 + [3000] * 6) == 3000  # the slow tail the average hides


def test_pct_change():
    assert pct_change(110, 100) == 10.0
    assert pct_change(50, 0) == 0.0 and pct_change(None, 10) == 0.0


BASE = {"errors": 0, "p95_ms": 100, "total_cost": 1.0}
ZERO = {c: 0 for c in ("regressed", "fixed", "still_passing", "still_failing", "unverified")}


def test_decide_order():
    assert decide({**ZERO, "regressed": 1, "unverified": 5}, BASE, BASE)[0] == "NOT_SAFE"
    assert decide({**ZERO, "unverified": 1}, BASE, {**BASE, "p95_ms": 999})[0] == "INCONCLUSIVE"
    assert decide(ZERO, BASE, {**BASE, "errors": 1})[0] == "INCONCLUSIVE"
    assert decide(ZERO, BASE, {**BASE, "total_cost": 1.5})[0] == "RISKY"
    assert decide(ZERO, BASE, {**BASE, "p95_ms": 120, "total_cost": 1.2})[0] == "SAFE"


def test_exit_codes():
    assert exit_code("SAFE") == 0 and exit_code("NOT_SAFE") == 1
    assert exit_code("RISKY") == 2 and exit_code("INCONCLUSIVE") == 2
