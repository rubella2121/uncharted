import pytest
from pymongo.errors import DuplicateKeyError

from guard import config, db as dbmod
from guard.ids import result_id, utcnow


def _result(run_id="run_v1_x", tc="tc01"):
    return {
        "_id": result_id(run_id, tc),
        "project_id": "supportbot",
        "run_id": run_id,
        "test_case_id": tc,
        "prompt_version": "v1",
        "status": "ok",
        "passed": True,
        "timestamp": utcnow(),
    }


def test_all_collections_created(db):
    names = set(db.list_collection_names())
    assert set(dbmod.VALIDATORS) <= names


def test_ensure_schema_is_idempotent(db):
    dbmod.ensure_schema(db)  # second run must not raise
    dbmod.ensure_schema(db)


def test_duplicate_result_rejected_by_id(db):
    coll = db[config.EVAL_RESULTS]
    coll.insert_one(_result())
    with pytest.raises(DuplicateKeyError):
        coll.insert_one(_result())
    assert coll.count_documents({}) == 1


def test_unique_run_testcase_index(db):
    coll = db[config.EVAL_RESULTS]
    coll.insert_one(_result())
    dup = _result()
    dup["_id"] = "res_some_other_id"  # different _id, same (run_id, test_case_id)
    with pytest.raises(DuplicateKeyError):
        coll.insert_one(dup)


def test_prompt_version_unique_per_project(db):
    coll = db[config.PROMPT_VERSIONS]
    base = {"project_id": "supportbot", "version": "v1", "prompt_text": "p",
            "model": "mock", "created_at": utcnow()}
    coll.insert_one({"_id": "supportbot:v1", **base})
    with pytest.raises(DuplicateKeyError):
        coll.insert_one({"_id": "other_id", **base})


def test_every_validator_requires_id_and_project():
    for name, schema in dbmod.VALIDATORS.items():
        assert "_id" in schema["required"], name
        assert "project_id" in schema["required"], name


def test_result_payload_fields_stay_flexible():
    props = dbmod.VALIDATORS[config.EVAL_RESULTS]["properties"]
    assert "output" not in props and "checks" not in props


def test_plan_stages_flattens_tree():
    plan = {"stage": "FETCH", "inputStage": {"stage": "IXSCAN", "indexName": "uniq_run_testcase",
                                             "keyPattern": {"run_id": 1, "test_case_id": 1}}}
    stages = dbmod._plan_stages(plan)
    assert [s["stage"] for s in stages] == ["FETCH", "IXSCAN"]
    assert stages[1]["indexName"] == "uniq_run_testcase"


def test_explain_unavailable_on_mongomock(db):
    assert dbmod.explain_run_lookup(db, "run_x")["available"] is False
