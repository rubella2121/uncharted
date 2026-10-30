"""Failure-case demonstrations (docs/SPEC.md section 13). Shared by the CLI and the API
so the judges can trigger them from the deployed web page too."""
from pymongo import DESCENDING
from pymongo.database import Database

from guard import config
from guard.ids import utcnow
from guard.runner import store_result


def replay_duplicate(db: Database, run_id: str | None = None) -> dict:
    """Re-send an already-stored result, exactly as a retrying client would.
    The stable _id makes MongoDB reject it, so the document count does not change."""
    results = db[config.EVAL_RESULTS]
    query = {"run_id": run_id} if run_id else {}
    original = results.find_one(query, sort=[("timestamp", DESCENDING)])
    if original is None:
        raise ValueError("no stored results to replay; run an eval first")
    before = results.count_documents({"run_id": original["run_id"]})
    outcome = store_result(db, dict(original))
    after = results.count_documents({"run_id": original["run_id"]})
    return {"result_id": original["_id"], "run_id": original["run_id"],
            "test_case_id": original["test_case_id"], "outcome": outcome,
            "count_before": before, "count_after": after}


def insert_incomplete(db: Database) -> dict:
    """Send a result with no run_id. On Atlas the $jsonSchema validator rejects it
    (code 121). mongomock has no validators, so there it would be stored; we clean up."""
    doc = {"_id": "res_incomplete_demo", "project_id": config.PROJECT_ID,
           "test_case_id": "tc01", "prompt_version": "v1", "status": "ok",
           "passed": True, "timestamp": utcnow()}
    outcome = store_result(db, doc)
    if outcome == "inserted":
        db[config.EVAL_RESULTS].delete_one({"_id": doc["_id"]})
    return {"missing_field": "run_id", "outcome": outcome}
