import pytest

from guard import config
from guard.demo import insert_incomplete, replay_duplicate
from guard.runner import run_eval
from guard.seed import seed


def test_replay_duplicate_is_ignored(db):
    seed(db)
    run_eval(db, "v1", run_id="run_v1")
    r = replay_duplicate(db)
    assert r["outcome"] == "duplicate"
    assert r["count_before"] == r["count_after"] == 30


def test_replay_needs_results(db):
    with pytest.raises(ValueError):
        replay_duplicate(db)


def test_incomplete_insert_leaves_no_trace(db):
    insert_incomplete(db)  # mongomock: inserted then cleaned; Atlas: rejected
    assert db[config.EVAL_RESULTS].count_documents({}) == 0
