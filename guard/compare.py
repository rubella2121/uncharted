"""Compare a baseline run with a candidate run and decide whether the change is safe.

All per-test-case classification happens inside MongoDB (aggregation pipeline); Python
only applies the verdict rules. Spec: docs/SPEC.md sections 9 and 10.
"""
import math

from pymongo import DESCENDING
from pymongo.database import Database

from guard import config
from guard import db as dbmod
from guard.ids import comparison_id, utcnow

CHANGES = ("regressed", "fixed", "still_passing", "still_failing", "unverified")
FINISHED = ("completed", "completed_with_errors")


class RunNotFound(ValueError):
    pass


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------

def compare_pipeline(base_run: str, cand_run: str) -> list[dict]:
    """One output row per test case: {_id: test_case_id, change, base_*, cand_*}."""
    is_base = {"$eq": ["$run_id", base_run]}
    is_cand = {"$eq": ["$run_id", cand_run]}
    ok = {"$eq": ["$status", "ok"]}
    passed = {"$eq": ["$passed", True]}

    def flag(*conditions):  # 1 if every condition holds for this document, else 0
        return {"$sum": {"$cond": [{"$and": list(conditions)}, 1, 0]}}

    def eq(field, n):
        return {"$eq": [field, n]}

    return [
        {"$match": {"run_id": {"$in": [base_run, cand_run]}}},  # uses run_id index
        {"$group": {
            "_id": "$test_case_id",
            # The unique {run_id, test_case_id} index guarantees each flag is 0 or 1.
            "base_ok": flag(is_base, ok),
            "base_pass": flag(is_base, ok, passed),
            "cand_ok": flag(is_cand, ok),
            "cand_pass": flag(is_cand, ok, passed),
        }},
        {"$project": {
            "base_ok": 1, "base_pass": 1, "cand_ok": 1, "cand_pass": 1,
            "change": {"$switch": {
                "branches": [
                    # First: no usable result on either side means we cannot judge.
                    {"case": {"$or": [eq("$base_ok", 0), eq("$cand_ok", 0)]},
                     "then": "unverified"},
                    {"case": {"$and": [eq("$base_pass", 1), eq("$cand_pass", 0)]},
                     "then": "regressed"},
                    {"case": {"$and": [eq("$base_pass", 0), eq("$cand_pass", 1)]},
                     "then": "fixed"},
                    {"case": eq("$cand_pass", 1), "then": "still_passing"},
                ],
                "default": "still_failing",
            }},
        }},
        {"$sort": {"_id": 1}},
    ]


def stats_pipeline(run_id: str, use_percentile: bool) -> list[dict]:
    group = {
        "_id": "$run_id",
        "total": {"$sum": 1},
        "ok_count": {"$sum": {"$cond": [{"$eq": ["$status", "ok"]}, 1, 0]}},
        "errors": {"$sum": {"$cond": [{"$ne": ["$status", "ok"]}, 1, 0]}},
        "passed": {"$sum": {"$cond": [{"$eq": ["$passed", True]}, 1, 0]}},
        "total_cost": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
        "avg_latency_ms": {"$avg": "$latency_ms"},  # $avg ignores missing values
    }
    if use_percentile:  # MongoDB 7.0+
        group["p95_ms"] = {"$percentile": {
            # Failed calls feed null, which $percentile ignores, so a 30 s timeout
            # cannot distort the latency tail.
            "input": {"$cond": [{"$eq": ["$status", "ok"]}, "$latency_ms", None]},
            "p": [0.95],
            "method": "approximate",
        }}
    return [{"$match": {"run_id": run_id}}, {"$group": group}]


def p95(values: list[float]) -> float | None:
    """Nearest-rank 95th percentile. Fallback when $percentile is unavailable."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def run_stats(db: Database, run_id: str) -> dict:
    use_pct = dbmod.supports_percentile(db)
    rows = list(db[config.EVAL_RESULTS].aggregate(stats_pipeline(run_id, use_pct)))
    if not rows:
        return {"total": 0, "ok_count": 0, "errors": 0, "passed": 0,
                "total_cost": 0.0, "avg_latency_ms": None, "p95_ms": None}
    stats = rows[0]
    stats.pop("_id", None)
    if use_pct:
        stats["p95_ms"] = (stats.get("p95_ms") or [None])[0]
    else:
        latencies = [d["latency_ms"] for d in db[config.EVAL_RESULTS].find(
            {"run_id": run_id, "status": "ok"}, {"latency_ms": 1}) if "latency_ms" in d]
        stats["p95_ms"] = p95(latencies)
    stats["total_cost"] = round(stats["total_cost"], 8)
    if stats["avg_latency_ms"] is not None:
        stats["avg_latency_ms"] = round(stats["avg_latency_ms"], 1)
    return stats


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def pct_change(new: float | None, old: float | None) -> float:
    if not old or new is None:
        return 0.0
    return round((new - old) / old * 100, 1)


def decide(counts: dict, base_stats: dict, cand_stats: dict,
           rows: list[dict] | None = None) -> tuple[str, list[str]]:
    """Verdict rules, in this order (see SPEC section 10):
    1. any regression          -> NOT_SAFE      (proven harm stands, even with partial data)
    2. anything unverified     -> INCONCLUSIVE  (missing data can never prove safety)
    3. latency/cost over limit -> RISKY
    4. otherwise               -> SAFE
    """
    rows = rows or []

    def ids(change):
        found = [r["_id"] for r in rows if r["change"] == change]
        return f": {', '.join(found)}" if found else ""

    if counts["regressed"] > 0:
        return "NOT_SAFE", [f"{counts['regressed']} test case(s) regressed{ids('regressed')}"]

    if counts["unverified"] > 0 or cand_stats["errors"] > 0 or base_stats["errors"] > 0:
        n = counts["unverified"]
        return "INCONCLUSIVE", [f"{n} test case(s) could not be verified{ids('unverified')}; "
                                "re-run before shipping"]

    reasons = []
    lat = pct_change(cand_stats["p95_ms"], base_stats["p95_ms"])
    cost = pct_change(cand_stats["total_cost"], base_stats["total_cost"])
    if lat > config.LATENCY_THRESHOLD_PCT:
        reasons.append(f"p95 latency +{lat:.0f}% (limit {config.LATENCY_THRESHOLD_PCT:.0f}%)")
    if cost > config.COST_THRESHOLD_PCT:
        reasons.append(f"cost +{cost:.0f}% (limit {config.COST_THRESHOLD_PCT:.0f}%)")
    if reasons:
        return "RISKY", reasons
    return "SAFE", ["no regressions; latency and cost within limits"]


def exit_code(verdict: str) -> int:
    return {"SAFE": config.EXIT_SAFE, "NOT_SAFE": config.EXIT_NOT_SAFE}.get(
        verdict, config.EXIT_RISKY_OR_INCONCLUSIVE)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def resolve_run(db: Database, ref: str, project_id: str = config.PROJECT_ID) -> dict:
    """Accept a run ID or a version name; a version means its latest finished run."""
    run = db[config.EVAL_RUNS].find_one({"_id": ref})
    if run:
        return run
    run = db[config.EVAL_RUNS].find_one(
        {"project_id": project_id, "prompt_version": ref, "status": {"$in": list(FINISHED)}},
        sort=[("started_at", DESCENDING)],
    )
    if run is None:
        raise RunNotFound(f"no finished run found for '{ref}' (run `guard run {ref}` first)")
    return run


def compare_runs(db: Database, baseline: str, candidate: str,
                 project_id: str = config.PROJECT_ID) -> dict:
    """Compare two runs (IDs or version names), store the comparison, and return it.
    Upserted by a stable ID, so comparing the same pair twice updates one document."""
    base_run = resolve_run(db, baseline, project_id)
    cand_run = resolve_run(db, candidate, project_id)
    if base_run["_id"] == cand_run["_id"]:
        raise ValueError("baseline and candidate are the same run")

    rows = list(db[config.EVAL_RESULTS].aggregate(
        compare_pipeline(base_run["_id"], cand_run["_id"])))
    counts = {c: 0 for c in CHANGES}
    for r in rows:
        counts[r["change"]] += 1
    base_stats = run_stats(db, base_run["_id"])
    cand_stats = run_stats(db, cand_run["_id"])
    verdict, reasons = decide(counts, base_stats, cand_stats, rows)

    warnings = []
    if base_run.get("test_set_hash") != cand_run.get("test_set_hash"):
        warnings.append("runs used different test sets; results may not be comparable")

    doc = {
        "_id": comparison_id(base_run["_id"], cand_run["_id"]),
        "project_id": project_id,
        "baseline_run": base_run["_id"],
        "candidate_run": cand_run["_id"],
        "baseline_version": base_run["prompt_version"],
        "candidate_version": cand_run["prompt_version"],
        "baseline_git": base_run.get("git"),
        "candidate_git": cand_run.get("git"),
        "verdict": verdict,
        "reasons": reasons,
        "warnings": warnings,
        "counts": counts,
        "metrics": {
            "baseline": base_stats,
            "candidate": cand_stats,
            "p95_change_pct": pct_change(cand_stats["p95_ms"], base_stats["p95_ms"]),
            "cost_change_pct": pct_change(cand_stats["total_cost"], base_stats["total_cost"]),
        },
        "rows": [{"test_case_id": r["_id"], "change": r["change"]} for r in rows],
        "created_at": utcnow(),
    }
    db[config.COMPARISONS].replace_one({"_id": doc["_id"]}, doc, upsert=True)
    return doc


# ---------------------------------------------------------------------------
# Readiness score, version history, and per-case diff (dashboard insights)
# ---------------------------------------------------------------------------

SCORE_WEIGHTS = {"quality": 70, "speed": 15, "cost": 15}


def readiness_score(stats: dict, reference: dict) -> dict:
    """0-100 "ready to ship" score for one run, relative to a reference run.

    quality: share of all test cases that passed (timeouts count as not passed),
    speed/cost: full marks when p95 / total cost are no worse than the reference,
    shrinking in proportion when they grow (half the points at 2x the reference).
    Quality dominates on purpose: a cheap prompt that breaks cases must score low.
    """
    def ratio(ref, val):
        if not ref or not val:
            return 1.0
        return min(1.0, ref / val)

    quality = stats["passed"] / stats["total"] if stats["total"] else 0.0
    speed = ratio(reference.get("p95_ms"), stats.get("p95_ms"))
    cost = ratio(reference.get("total_cost"), stats.get("total_cost"))
    parts = {
        "quality": round(SCORE_WEIGHTS["quality"] * quality, 1),
        "speed": round(SCORE_WEIGHTS["speed"] * speed, 1),
        "cost": round(SCORE_WEIGHTS["cost"] * cost, 1),
    }
    return {"score": round(sum(parts.values())), **parts}


def history_pipeline(project_id: str, use_percentile: bool, limit: int) -> list[dict]:
    """Per-run quality, cost and latency for the whole project, newest `limit` runs."""
    ok = {"$eq": ["$status", "ok"]}
    group = {
        "_id": "$run_id",
        "version": {"$first": "$prompt_version"},
        "started": {"$min": "$timestamp"},
        "total": {"$sum": 1},
        "passed": {"$sum": {"$cond": [{"$eq": ["$passed", True]}, 1, 0]}},
        "errors": {"$sum": {"$cond": [ok, 0, 1]}},
        "total_cost": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
    }
    if use_percentile:
        group["p95_ms"] = {"$percentile": {"input": {"$cond": [ok, "$latency_ms", None]},
                                           "p": [0.95], "method": "approximate"}}
    else:
        group["latencies"] = {"$push": {"$cond": [ok, "$latency_ms", None]}}
    return [
        {"$match": {"project_id": project_id}},  # project_version_time index
        {"$group": group},
        {"$sort": {"started": -1}},
        {"$limit": limit},
        # Pull each run's status from eval_runs (a join only on this small page).
        {"$lookup": {"from": config.EVAL_RUNS, "localField": "_id",
                     "foreignField": "_id", "as": "run"}},
        {"$addFields": {"status": {"$arrayElemAt": ["$run.status", 0]}}},
        {"$project": {"run": 0}},
    ]


def run_history(db: Database, project_id: str = config.PROJECT_ID, limit: int = 20) -> dict:
    """Runs oldest -> newest with stats and a readiness score. The reference for the
    score is the newest finished v1 run (the baseline), else the oldest run shown."""
    use_pct = dbmod.supports_percentile(db)
    rows = list(db[config.EVAL_RESULTS].aggregate(history_pipeline(project_id, use_pct, limit)))
    rows.reverse()
    runs = []
    for r in rows:
        if use_pct:
            p95_ms = (r.get("p95_ms") or [None])[0]
        else:
            p95_ms = p95([x for x in r.pop("latencies", []) if x is not None])
        runs.append({"run_id": r["_id"], "version": r["version"], "started": r["started"],
                     "status": r.get("status"), "total": r["total"], "passed": r["passed"],
                     "errors": r["errors"], "total_cost": round(r["total_cost"], 8),
                     "p95_ms": p95_ms})
    finished = [r for r in runs if r["status"] in FINISHED]
    reference = next((r for r in reversed(finished) if r["version"] == "v1"), None) \
        or (finished[0] if finished else None)
    for r in runs:
        r["readiness"] = readiness_score(r, reference) if reference else None
    return {"reference_run": reference["run_id"] if reference else None, "runs": runs}


def case_diff(db: Database, baseline_run: str, candidate_run: str, test_case_id: str) -> dict:
    """Both runs' results for one test case, side by side, with the checks whose
    outcome changed. Answers "what exactly broke?" for a regressed case."""
    results = db[config.EVAL_RESULTS]
    base = results.find_one({"run_id": baseline_run, "test_case_id": test_case_id})
    cand = results.find_one({"run_id": candidate_run, "test_case_id": test_case_id})
    tc = db[config.TEST_CASES].find_one({"_id": test_case_id})
    if tc is None:
        raise ValueError(f"test case '{test_case_id}' not found")
    if base is None and cand is None:
        raise ValueError(f"no results for {test_case_id} in either run")

    base_checks = (base or {}).get("checks") or []
    cand_checks = (cand or {}).get("checks") or []
    checks = []
    for i, spec in enumerate(tc["checks"]):  # same test case -> same check order
        b = base_checks[i] if i < len(base_checks) else None
        c = cand_checks[i] if i < len(cand_checks) else None
        checks.append({
            "type": spec["type"], "value": spec.get("value"),
            "baseline": b["passed"] if b else None, "baseline_detail": b["detail"] if b else None,
            "candidate": c["passed"] if c else None, "candidate_detail": c["detail"] if c else None,
            "changed": (b or {}).get("passed") != (c or {}).get("passed"),
        })

    def side(doc):
        if doc is None:
            return None
        return {k: doc.get(k) for k in ("_id", "run_id", "prompt_version", "status", "passed",
                                        "output", "error", "latency_ms", "cost_usd")}

    return {"test_case": {k: tc.get(k) for k in ("_id", "name", "risk", "input")},
            "baseline": side(base), "candidate": side(cand), "checks": checks}
