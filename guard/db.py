"""MongoDB connection, collection validators, and indexes.

Run `guard setup` (or call ensure_schema(db)) once per database. It is safe to run
repeatedly: existing collections get their validator updated with collMod, and
create_index is a no-op when the index already exists.

Design rules enforced here (see docs/SPEC.md section "Data model"):
- Each collection validates a strict *envelope* of required fields.
- Source-specific payloads (eval_results.output, eval_results.checks, comparisons.rows)
  are deliberately NOT listed in the schema, so they stay flexible.
- Idempotency comes from stable _id values plus unique indexes.
"""
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from guard import config

# ---------------------------------------------------------------------------
# Validators ($jsonSchema). One per collection.
# ---------------------------------------------------------------------------

_STR = {"bsonType": "string"}
_DATE = {"bsonType": "date"}
_NONNEG = {"bsonType": ["int", "long", "double", "decimal"], "minimum": 0}

VALIDATORS: dict[str, dict] = {
    config.PROMPT_VERSIONS: {
        "bsonType": "object",
        "required": ["_id", "project_id", "version", "prompt_text", "model", "created_at"],
        "properties": {
            "_id": _STR,
            "project_id": _STR,
            "version": _STR,
            "prompt_text": _STR,
            "model": _STR,
            "temperature": _NONNEG,
            "price_per_1k_in": _NONNEG,
            "price_per_1k_out": _NONNEG,
            "created_at": _DATE,
        },
    },
    config.TEST_CASES: {
        "bsonType": "object",
        "required": ["_id", "project_id", "name", "input", "checks"],
        "properties": {
            "_id": _STR,
            "project_id": _STR,
            "name": _STR,
            "input": _STR,
            # Each check must name its type; its "value" shape depends on the type.
            "checks": {
                "bsonType": "array",
                "minItems": 1,
                "items": {
                    "bsonType": "object",
                    "required": ["type"],
                    "properties": {"type": _STR},
                },
            },
        },
    },
    config.EVAL_RUNS: {
        "bsonType": "object",
        "required": ["_id", "project_id", "prompt_version", "status", "started_at"],
        "properties": {
            "_id": _STR,
            "project_id": _STR,
            "prompt_version": _STR,
            "status": {"enum": ["running", "completed", "completed_with_errors", "failed"]},
            "started_at": _DATE,
            "finished_at": _DATE,
            "test_set_size": _NONNEG,
            "test_set_hash": _STR,
        },
    },
    config.EVAL_RESULTS: {
        "bsonType": "object",
        "required": [
            "_id", "project_id", "run_id", "test_case_id",
            "prompt_version", "status", "passed", "timestamp",
        ],
        "properties": {
            "_id": _STR,
            "project_id": _STR,
            "run_id": _STR,
            "test_case_id": _STR,
            "prompt_version": _STR,
            "status": {"enum": ["ok", "error", "timeout"]},
            "passed": {"bsonType": "bool"},
            "latency_ms": _NONNEG,
            "tokens_in": _NONNEG,
            "tokens_out": _NONNEG,
            "cost_usd": _NONNEG,
            "timestamp": _DATE,
            # output, checks, error: deliberately unconstrained (flexible payload).
        },
    },
    config.COMPARISONS: {
        "bsonType": "object",
        "required": [
            "_id", "project_id", "baseline_run", "candidate_run", "verdict", "created_at",
        ],
        "properties": {
            "_id": _STR,
            "project_id": _STR,
            "baseline_run": _STR,
            "candidate_run": _STR,
            "verdict": {"enum": ["SAFE", "RISKY", "NOT_SAFE", "INCONCLUSIVE"]},
            "reasons": {"bsonType": "array", "items": _STR},
            "created_at": _DATE,
        },
    },
}

# ---------------------------------------------------------------------------
# Indexes. Each one exists to answer a specific, frequent question.
# Format: collection -> list of (keys, options)
# ---------------------------------------------------------------------------

INDEXES: dict[str, list[tuple[list, dict]]] = {
    config.EVAL_RESULTS: [
        # "All results of run X" (compare $match) and "is this result already stored?"
        ([("run_id", ASCENDING), ("test_case_id", ASCENDING)],
         {"unique": True, "name": "uniq_run_testcase"}),
        # "Latest results for version v2 of this project"
        ([("project_id", ASCENDING), ("prompt_version", ASCENDING), ("timestamp", DESCENDING)],
         {"name": "project_version_time"}),
    ],
    config.EVAL_RUNS: [
        # "Most recent runs of this project" (dashboard run list, `guard compare` defaults)
        ([("project_id", ASCENDING), ("started_at", DESCENDING)],
         {"name": "project_started"}),
        # "Latest run of version v2"
        ([("project_id", ASCENDING), ("prompt_version", ASCENDING), ("started_at", DESCENDING)],
         {"name": "project_version_started"}),
    ],
    config.PROMPT_VERSIONS: [
        # No two "v2"s in one project
        ([("project_id", ASCENDING), ("version", ASCENDING)],
         {"unique": True, "name": "uniq_project_version"}),
    ],
    config.TEST_CASES: [
        ([("project_id", ASCENDING)], {"name": "project"}),
    ],
    config.COMPARISONS: [
        ([("project_id", ASCENDING), ("created_at", DESCENDING)],
         {"name": "project_created"}),
    ],
}


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    if not config.MONGODB_URI:
        raise RuntimeError(
            "MONGODB_URI is not set. Copy .env.example to .env and paste your Atlas URI."
        )
    # tz_aware=True: dates come back as timezone-aware UTC datetimes.
    return MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=8000, tz_aware=True)


def get_db() -> Database:
    return get_client()[config.DB_NAME]


def is_mongomock(db: Database) -> bool:
    """mongomock (used in unit tests) cannot store validators; real MongoDB can."""
    return type(db).__module__.startswith("mongomock")


# ---------------------------------------------------------------------------
# Schema setup
# ---------------------------------------------------------------------------

def ensure_schema(db: Database) -> list[str]:
    """Create collections with validators and all indexes. Idempotent.

    Returns a list of human-readable log lines describing what was done.
    """
    log = []
    existing = set(db.list_collection_names())
    for name, schema in VALIDATORS.items():
        if is_mongomock(db):
            if name not in existing:
                db.create_collection(name)
            log.append(f"{name}: created (validator skipped: mongomock)")
            continue
        validator = {"$jsonSchema": schema}
        if name in existing:
            db.command("collMod", name, validator=validator,
                       validationLevel="strict", validationAction="error")
            log.append(f"{name}: validator updated")
        else:
            db.create_collection(name, validator=validator,
                                 validationLevel="strict", validationAction="error")
            log.append(f"{name}: created with validator")

    for name, specs in INDEXES.items():
        for keys, options in specs:
            db[name].create_index(keys, **options)
            log.append(f"{name}: index {options['name']} ready")
    return log


def server_version(db: Database) -> tuple[int, ...]:
    """MongoDB server version as a tuple, e.g. (8, 0, 4)."""
    version = db.client.server_info()["version"]
    return tuple(int(p) for p in version.split("-")[0].split(".") if p.isdigit())


def supports_percentile(db: Database) -> bool:
    """$percentile needs MongoDB 7.0+. compare.py falls back to Python when False."""
    if is_mongomock(db):
        return False
    return server_version(db) >= (7, 0)


def reset_runs(db: Database) -> None:
    """Delete all run data (runs, results, comparisons) but keep prompts and test
    cases. Used before a demo to start from a clean history."""
    for name in (config.EVAL_RUNS, config.EVAL_RESULTS, config.COMPARISONS):
        db[name].delete_many({})


def _plan_stages(plan: dict) -> list[dict]:
    """Flatten a winningPlan / executionStages tree into a list, outermost first."""
    stages = []
    while plan:
        stages.append({k: plan[k] for k in ("stage", "indexName", "keyPattern") if k in plan})
        plan = plan.get("inputStage") or (plan.get("inputStages") or [None])[0]
    return stages


def explain_run_lookup(db: Database, run_id: str) -> dict:
    """Explain the query the tool runs most ("all results of run X") with executionStats.
    Proves the unique {run_id, test_case_id} index is used (IXSCAN, not COLLSCAN)."""
    if is_mongomock(db):
        return {"available": False, "reason": "explain needs a real MongoDB server"}
    out = db.command("explain", {"find": config.EVAL_RESULTS, "filter": {"run_id": run_id}},
                     verbosity="executionStats")
    winning = out.get("queryPlanner", {}).get("winningPlan", {})
    winning = winning.get("queryPlan", winning)  # 7.0+ slot-based engine nests the plan
    stats = out.get("executionStats", {})
    stages = _plan_stages(winning)
    return {
        "available": True,
        "filter": {"run_id": run_id},
        "stages": stages,
        "uses_index": any(s["stage"] == "IXSCAN" for s in stages),
        "index": next((s.get("indexName") for s in stages if s.get("indexName")), None),
        "n_returned": stats.get("nReturned"),
        "keys_examined": stats.get("totalKeysExamined"),
        "docs_examined": stats.get("totalDocsExamined"),
        "time_ms": stats.get("executionTimeMillis"),
    }
