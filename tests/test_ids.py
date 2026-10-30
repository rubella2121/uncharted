from datetime import datetime, timezone

from guard import ids


def test_stable_id_is_deterministic():
    assert ids.result_id("run_a", "tc01") == ids.result_id("run_a", "tc01")


def test_stable_id_differs_per_input():
    assert ids.result_id("run_a", "tc01") != ids.result_id("run_a", "tc02")
    assert ids.result_id("run_a", "tc01") != ids.result_id("run_b", "tc01")


def test_stable_id_format():
    rid = ids.result_id("run_a", "tc01")
    assert rid.startswith("res_") and len(rid) == len("res_") + 16


def test_comparison_id_is_order_sensitive():
    # baseline vs candidate is directional: v1->v2 is not the same comparison as v2->v1
    assert ids.comparison_id("r1", "r2") != ids.comparison_id("r2", "r1")


def test_new_run_id_format():
    t = datetime(2026, 10, 30, 10, 30, 15, tzinfo=timezone.utc)
    assert ids.new_run_id("v2", t) == "run_v2_20261030T103015"


def test_test_set_hash_ignores_order():
    a = [{"_id": "tc01", "input": "x"}, {"_id": "tc02", "input": "y"}]
    assert ids.test_set_hash(a) == ids.test_set_hash(list(reversed(a)))
    assert ids.test_set_hash(a) != ids.test_set_hash(a[:1])


def test_utcnow_is_timezone_aware():
    assert ids.utcnow().tzinfo is not None
