import pytest

from guard import config
from guard.runner import VersionNotFound, compute_cost, evaluate_case, run_eval
from guard.seed import seed


@pytest.fixture
def seeded(db):
    seed(db)
    return db


def test_run_v1_stores_30_results(seeded):
    run = run_eval(seeded, "v1", run_id="run_v1_t")
    assert run["status"] == "completed"
    assert run["summary"]["total"] == 30 and run["summary"]["passed"] == 29
    assert seeded[config.EVAL_RESULTS].count_documents({"run_id": "run_v1_t"}) == 30
    tc10 = seeded[config.EVAL_RESULTS].find_one({"run_id": "run_v1_t", "test_case_id": "tc10"})
    assert tc10["passed"] is False and tc10["status"] == "ok"


def test_result_document_shape(seeded):
    run_eval(seeded, "v1", run_id="run_v1_t")
    doc = seeded[config.EVAL_RESULTS].find_one({"run_id": "run_v1_t", "test_case_id": "tc01"})
    for field in ("_id", "project_id", "run_id", "test_case_id", "prompt_version", "status",
                  "passed", "output", "checks", "latency_ms", "tokens_in", "tokens_out",
                  "cost_usd", "timestamp"):
        assert field in doc, field
    assert doc["_id"].startswith("res_")
    assert doc["timestamp"].tzinfo is not None


def test_timeouts_are_recorded_not_raised(seeded):
    run = run_eval(seeded, "v3", run_id="run_v3_t", simulate_timeouts={"tc03", "tc05"})
    assert run["status"] == "completed_with_errors"
    assert run["summary"]["errors"] == 2
    t = seeded[config.EVAL_RESULTS].find_one({"run_id": "run_v3_t", "test_case_id": "tc03"})
    assert t["status"] == "timeout" and t["passed"] is False and "latency_ms" not in t


def test_model_exception_is_recorded_as_error(seeded):
    def broken_model(*_a, **_k):
        raise RuntimeError("rate limited")
    run = run_eval(seeded, "v1", run_id="run_err", model_fn=broken_model)
    doc = seeded[config.EVAL_RESULTS].find_one({"run_id": "run_err"})
    assert doc["status"] == "error" and "rate limited" in doc["error"]
    assert run["summary"]["errors"] == 30


def test_resumed_run_skips_stored_results(seeded):
    run_eval(seeded, "v1", run_id="run_resume")
    calls = []

    def counting_model(*a, **k):
        calls.append(1)
        raise AssertionError("must not be called")
    events = []
    run = run_eval(seeded, "v1", run_id="run_resume", model_fn=counting_model,
                   on_result=events.append)
    assert not calls
    assert run["summary"]["skipped"] == 30 and run["summary"]["total"] == 30
    assert {e["outcome"] for e in events} == {"skipped"}


def test_partial_resume_fills_only_missing(seeded):
    run_eval(seeded, "v1", run_id="run_partial")
    seeded[config.EVAL_RESULTS].delete_many({"run_id": "run_partial", "test_case_id": {"$gt": "tc15"}})
    events = []
    run_eval(seeded, "v1", run_id="run_partial", on_result=events.append)
    outcomes = [e["outcome"] for e in events]
    assert outcomes.count("skipped") == 15 and outcomes.count("inserted") == 15


def test_unknown_version(seeded):
    with pytest.raises(VersionNotFound, match="v99"):
        run_eval(seeded, "v99")


def test_no_test_cases(db):
    seed(db)
    db[config.TEST_CASES].delete_many({})
    with pytest.raises(ValueError, match="no test cases"):
        run_eval(db, "v1")


def test_on_result_called_per_case(seeded):
    events = []
    run_eval(seeded, "v2", run_id="run_cb", on_result=events.append)
    assert [e["test_case_id"] for e in events] == [f"tc{i:02d}" for i in range(1, 31)]


def test_compute_cost():
    pv = {"price_per_1k_in": 0.001, "price_per_1k_out": 0.002}
    assert compute_cost(1000, 500, pv) == pytest.approx(0.002)


def test_evaluate_case_ok():
    pv = {"version": "v1", "prompt_text": "p", "price_per_1k_in": 0.001, "price_per_1k_out": 0.002}
    tc = {"_id": "tc01", "input": "x", "checks": [{"type": "is_valid_json"}]}
    r = evaluate_case(pv, tc)
    assert r["status"] == "ok" and r["passed"] is True and r["cost_usd"] > 0


def test_new_runs_in_same_second_get_distinct_ids(seeded):
    a = run_eval(seeded, "v1")["_id"]
    b = run_eval(seeded, "v1")["_id"]
    assert a != b
    assert seeded[config.EVAL_RESULTS].count_documents({"run_id": b}) == 30
