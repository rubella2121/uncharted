"""Run the whole test set against one prompt version and store every result.

Key properties (docs/SPEC.md section 8):
- run_id is created once and passed through; resuming a run with the same run_id skips
  results that are already stored (idempotent ingestion).
- A timeout or model error is data, not a crash: it is stored with status
  "timeout"/"error" and passed=False, and the run carries on.
- Duplicate inserts and validator rejections are logged and skipped, never fatal.
"""
import time
from typing import Callable

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, WriteError

from guard import config
from guard.checks import run_checks
from guard.ids import new_run_id, prompt_version_id, result_id, test_set_hash, utcnow
from guard.mock_model import call_model

VALIDATION_ERROR_CODE = 121


class VersionNotFound(ValueError):
    pass


def compute_cost(tokens_in: int, tokens_out: int, prompt_version: dict) -> float:
    return round(
        tokens_in / 1000 * prompt_version["price_per_1k_in"]
        + tokens_out / 1000 * prompt_version["price_per_1k_out"],
        8,
    )


def evaluate_case(prompt_version: dict, test_case: dict, simulate_timeout: bool = False,
                  model_fn: Callable = call_model) -> dict:
    """Call the model for one test case and score it. Returns the result fields that
    depend on the model (no IDs or timestamps), so it is easy to test on its own."""
    try:
        resp = model_fn(prompt_version, test_case, simulate_timeout=simulate_timeout)
    except TimeoutError as e:
        return {"status": "timeout", "passed": False, "error": str(e)}
    except Exception as e:  # any model/client failure is recorded, not raised
        return {"status": "error", "passed": False, "error": f"{type(e).__name__}: {e}"}

    passed, checks = run_checks(test_case["checks"], resp["output"])
    return {
        "status": "ok",
        "passed": passed,
        "output": resp["output"],
        "checks": checks,
        "latency_ms": resp["latency_ms"],
        "tokens_in": resp["tokens_in"],
        "tokens_out": resp["tokens_out"],
        "cost_usd": compute_cost(resp["tokens_in"], resp["tokens_out"], prompt_version),
    }


def store_result(db: Database, doc: dict) -> str:
    """Insert one result. Returns "inserted", "duplicate", or "rejected"."""
    try:
        db[config.EVAL_RESULTS].insert_one(doc)
        return "inserted"
    except DuplicateKeyError:
        return "duplicate"
    except WriteError as e:
        if e.code == VALIDATION_ERROR_CODE:
            return "rejected"
        raise


def get_prompt_version(db: Database, version: str, project_id: str = config.PROJECT_ID) -> dict:
    pv = db[config.PROMPT_VERSIONS].find_one({"_id": prompt_version_id(project_id, version)})
    if pv is None:
        known = sorted(d["version"] for d in
                       db[config.PROMPT_VERSIONS].find({"project_id": project_id}, {"version": 1}))
        raise VersionNotFound(
            f"prompt version '{version}' not found (known: {', '.join(known) or 'none, run seed'})")
    return pv


def start_run(db: Database, version: str, project_id: str = config.PROJECT_ID,
              run_id: str | None = None) -> str:
    """Validate the version and create (or reopen) the eval_runs document. Split out of
    run_eval so the API can return the run_id before the slow part starts."""
    get_prompt_version(db, version, project_id)
    test_cases = list(db[config.TEST_CASES].find({"project_id": project_id}).sort("_id", 1))
    if not test_cases:
        raise ValueError("no test cases found, run `guard seed` first")
    if run_id is None:
        # New run: never collide with a run started in the same second.
        base_id, n = new_run_id(version), 1
        run_id = base_id
        while db[config.EVAL_RUNS].count_documents({"_id": run_id}, limit=1):
            n += 1
            run_id = f"{base_id}_{n}"
    db[config.EVAL_RUNS].update_one(
        {"_id": run_id},
        {"$set": {"status": "running", "test_set_size": len(test_cases),
                  "test_set_hash": test_set_hash(test_cases)},
         "$setOnInsert": {"project_id": project_id, "prompt_version": version,
                          "started_at": utcnow()}},
        upsert=True,
    )
    return run_id


def run_eval(db: Database, version: str, *, simulate_timeouts: set[str] | None = None,
             run_id: str | None = None, on_result: Callable[[dict], None] | None = None,
             delay_s: float = 0.0, model_fn: Callable = call_model,
             project_id: str = config.PROJECT_ID) -> dict:
    """Run every test case against `version`. Returns the final eval_runs document.

    on_result(event) is called once per test case with
    {"test_case_id", "outcome": inserted|duplicate|rejected|skipped, "result": doc|None}.
    delay_s pauses between cases so the live dashboard visibly fills row by row.
    """
    simulate_timeouts = simulate_timeouts or set()
    run_id = start_run(db, version, project_id, run_id)
    pv = get_prompt_version(db, version, project_id)
    test_cases = list(db[config.TEST_CASES].find({"project_id": project_id}).sort("_id", 1))
    already = {d["test_case_id"] for d in
               db[config.EVAL_RESULTS].find({"run_id": run_id}, {"test_case_id": 1})}

    tally = {"inserted": 0, "duplicate": 0, "rejected": 0, "skipped": 0}
    for i, tc in enumerate(test_cases):
        if tc["_id"] in already:  # resumed run: never pay for the same call twice
            tally["skipped"] += 1
            if on_result:
                on_result({"test_case_id": tc["_id"], "outcome": "skipped", "result": None})
            continue
        if delay_s and i:
            time.sleep(delay_s)
        doc = {
            "_id": result_id(run_id, tc["_id"]),
            "project_id": project_id,
            "run_id": run_id,
            "test_case_id": tc["_id"],
            "prompt_version": version,
            **evaluate_case(pv, tc, tc["_id"] in simulate_timeouts, model_fn),
            "timestamp": utcnow(),
        }
        outcome = store_result(db, doc)
        tally[outcome] += 1
        if on_result:
            on_result({"test_case_id": tc["_id"], "outcome": outcome, "result": doc})

    summary = run_summary(db, run_id)
    summary.update({k: tally[k] for k in ("duplicate", "rejected", "skipped")})
    status = "completed" if summary["errors"] == 0 and summary["total"] == len(test_cases) \
        else "completed_with_errors"
    db[config.EVAL_RUNS].update_one(
        {"_id": run_id},
        {"$set": {"status": status, "finished_at": utcnow(), "summary": summary}},
    )
    return db[config.EVAL_RUNS].find_one({"_id": run_id})


def run_summary(db: Database, run_id: str) -> dict:
    """Counts from what is actually stored, so a resumed run reports the full picture."""
    rows = list(db[config.EVAL_RESULTS].aggregate([
        {"$match": {"run_id": run_id}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "passed": {"$sum": {"$cond": [{"$eq": ["$passed", True]}, 1, 0]}},
            "errors": {"$sum": {"$cond": [{"$ne": ["$status", "ok"]}, 1, 0]}},
        }},
    ]))
    if not rows:
        return {"total": 0, "passed": 0, "errors": 0}
    return {k: rows[0][k] for k in ("total", "passed", "errors")}


def fail_run(db: Database, run_id: str, error: str) -> None:
    """Mark a run as failed when something outside a single test case breaks."""
    db[config.EVAL_RUNS].update_one(
        {"_id": run_id}, {"$set": {"status": "failed", "finished_at": utcnow(), "error": error}})
