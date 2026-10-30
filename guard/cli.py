"""Command-line interface: `guard <command>`.

Commands: setup, doctor, seed, run, compare, history, explain, reset, demo-duplicate, demo-incomplete
"""
import typer
from pymongo.errors import DuplicateKeyError, WriteError

from guard import config, db as dbmod
from guard import compare as cmp
from guard import demo as demomod
from guard import runner
from guard.ids import utcnow
from guard.seed import seed as seed_data

app = typer.Typer(add_completion=False, help="Prompt Regression Guard")


@app.command()
def setup():
    """Create collections, validators, and indexes. Safe to run repeatedly."""
    database = dbmod.get_db()
    for line in dbmod.ensure_schema(database):
        typer.echo(f"  {line}")
    typer.secho("Schema ready.", fg=typer.colors.GREEN)


@app.command()
def seed():
    """Load data/prompts.json and data/test_cases.json into MongoDB (idempotent upsert)."""
    database = dbmod.get_db()
    dbmod.ensure_schema(database)
    try:
        log = seed_data(database)
    except ValueError as e:
        typer.secho(f"Invalid data file: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=config.EXIT_USAGE_ERROR)
    for line in log:
        typer.echo(f"  {line}")
    typer.secho("Seed complete.", fg=typer.colors.GREEN)


@app.command()
def doctor():
    """Check the Atlas connection and prove that validation, unique IDs, and indexes work.

    Inserts a probe result, re-inserts it (must be rejected as a duplicate), inserts an
    incomplete document (must be rejected by the validator), checks that a run lookup
    uses an index, then deletes the probe.
    """
    database = dbmod.get_db()
    ok = True

    def report(passed: bool, label: str, detail: str = ""):
        nonlocal ok
        ok &= passed
        mark = typer.style("PASS", fg=typer.colors.GREEN) if passed \
            else typer.style("FAIL", fg=typer.colors.RED)
        typer.echo(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))

    version = ".".join(map(str, dbmod.server_version(database)))
    report(True, "connected", f"MongoDB {version}, db '{config.DB_NAME}'")
    report(dbmod.supports_percentile(database), "$percentile available (needs 7.0+)",
           "" if dbmod.supports_percentile(database) else "compare will use Python fallback")

    dbmod.ensure_schema(database)
    results = database[config.EVAL_RESULTS]
    probe = {
        "_id": "res_doctor_probe",
        "project_id": "__doctor__",
        "run_id": "run___doctor__",
        "test_case_id": "tc_probe",
        "prompt_version": "v0",
        "status": "ok",
        "passed": True,
        "timestamp": utcnow(),
    }
    results.delete_many({"project_id": "__doctor__"})
    try:
        results.insert_one(dict(probe))
        report(True, "valid result inserted")

        try:
            results.insert_one(dict(probe))
            report(False, "duplicate rejected", "duplicate was stored!")
        except DuplicateKeyError:
            report(True, "duplicate rejected", "DuplicateKeyError")

        incomplete = {k: v for k, v in probe.items() if k != "run_id"}
        incomplete["_id"] = "res_doctor_incomplete"
        try:
            results.insert_one(incomplete)
            report(False, "incomplete result rejected", "validator did not fire")
        except WriteError as e:
            report(e.code == 121, "incomplete result rejected", f"code {e.code}")

        plan = results.find({"run_id": probe["run_id"]}).explain()
        stages = str(plan.get("queryPlanner", {}).get("winningPlan", {}))
        report("IXSCAN" in stages, "run lookup uses an index",
               "IXSCAN" if "IXSCAN" in stages else "COLLSCAN")
    finally:
        results.delete_many({"project_id": "__doctor__"})

    if ok:
        typer.secho("All checks passed.", fg=typer.colors.GREEN)
    else:
        typer.secho("Some checks failed. See above.", fg=typer.colors.RED)
        raise typer.Exit(code=1)


CHANGE_STYLE = {
    "regressed": ("REGRESSED", typer.colors.RED),
    "fixed": ("FIXED", typer.colors.GREEN),
    "still_passing": ("pass", None),
    "still_failing": ("still failing", typer.colors.YELLOW),
    "unverified": ("UNVERIFIED", typer.colors.BRIGHT_BLACK),
}
VERDICT_STYLE = {
    "SAFE": ("SAFE TO SHIP", typer.colors.GREEN),
    "RISKY": ("RISKY", typer.colors.YELLOW),
    "NOT_SAFE": ("NOT SAFE TO SHIP", typer.colors.RED),
    "INCONCLUSIVE": ("INCONCLUSIVE", typer.colors.MAGENTA),
}


def _fail(message: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=config.EXIT_USAGE_ERROR)


@app.command()
def run(
    version: str = typer.Argument(..., help="Prompt version, e.g. v1"),
    simulate_timeouts: str = typer.Option(
        "", "--simulate-timeouts", help="Comma-separated test case IDs that time out"),
    run_id: str = typer.Option(None, "--run-id", help="Resume this run instead of starting a new one"),
    delay: float = typer.Option(0.0, "--delay", help="Seconds between test cases (for the live view)"),
):
    """Run the test set against one prompt version and store every result."""
    database = dbmod.get_db()
    timeouts = {t.strip() for t in simulate_timeouts.split(",") if t.strip()}

    def show(event):
        r = event["result"]
        if event["outcome"] == "skipped":
            typer.echo(f"  {event['test_case_id']}  already stored, skipped")
        elif event["outcome"] != "inserted":
            typer.secho(f"  {event['test_case_id']}  {event['outcome']} (not stored)",
                        fg=typer.colors.YELLOW)
        elif r["status"] != "ok":
            typer.secho(f"  {r['test_case_id']}  {r['status'].upper():7}  {r['error']}",
                        fg=typer.colors.BRIGHT_BLACK)
        else:
            failed = [c["detail"] for c in r["checks"] if not c["passed"]]
            mark = typer.style("PASS", fg=typer.colors.GREEN) if r["passed"] \
                else typer.style("FAIL", fg=typer.colors.RED)
            typer.echo(f"  {r['test_case_id']}  {mark}  {r['latency_ms']:5} ms"
                       + (f"  {'; '.join(failed)}" if failed else ""))

    try:
        doc = runner.run_eval(database, version, simulate_timeouts=timeouts,
                              run_id=run_id, on_result=show, delay_s=delay)
    except ValueError as e:
        _fail(str(e))
    s = doc["summary"]
    typer.secho(f"Run {doc['_id']}: {s['passed']}/{s['total']} passed, {s['errors']} "
                f"error/timeout, status {doc['status']}", bold=True)


@app.command()
def compare(
    baseline: str = typer.Argument(..., help="Baseline version or run ID, e.g. v1"),
    candidate: str = typer.Argument(..., help="Candidate version or run ID, e.g. v2"),
):
    """Compare two runs and print the release verdict. Exit code: 0 SAFE, 1 NOT SAFE,
    2 RISKY/INCONCLUSIVE (use it as a CI gate)."""
    database = dbmod.get_db()
    try:
        c = cmp.compare_runs(database, baseline, candidate)
    except ValueError as e:
        _fail(str(e))

    typer.echo(f"Baseline  {c['baseline_run']}\nCandidate {c['candidate_run']}\n")
    for row in c["rows"]:
        label, color = CHANGE_STYLE[row["change"]]
        typer.secho(f"  {row['test_case_id']}  {label}", fg=color)
    m, b, n = c["metrics"], c["metrics"]["baseline"], c["metrics"]["candidate"]
    typer.echo(f"\n  pass rate   {b['passed']}/{b['total']}  ->  {n['passed']}/{n['total']}")
    typer.echo(f"  p95 latency {b['p95_ms']} ms -> {n['p95_ms']} ms  ({m['p95_change_pct']:+.0f}%)")
    typer.echo(f"  total cost  ${b['total_cost']:.6f} -> ${n['total_cost']:.6f}  "
               f"({m['cost_change_pct']:+.0f}%)")
    label, color = VERDICT_STYLE[c["verdict"]]
    typer.secho(f"\n  VERDICT: {label}", fg=color, bold=True)
    for reason in c["reasons"]:
        typer.echo(f"  - {reason}")
    for warning in c["warnings"]:
        typer.secho(f"  ! {warning}", fg=typer.colors.YELLOW)
    raise typer.Exit(code=cmp.exit_code(c["verdict"]))


@app.command()
def history(limit: int = typer.Option(10, help="How many runs to show")):
    """List the most recent runs of the project."""
    database = dbmod.get_db()
    for r in database[config.EVAL_RUNS].find({"project_id": config.PROJECT_ID}) \
            .sort("started_at", -1).limit(limit):
        s = r.get("summary", {})
        typer.echo(f"  {r['_id']:28} {r['prompt_version']:4} {r['status']:22} "
                   f"{s.get('passed', '-')}/{s.get('total', '-')}")


@app.command()
def explain(run: str = typer.Argument(..., help="Run ID or version (latest run)")):
    """Show the query plan for "all results of a run" (IXSCAN = index used)."""
    database = dbmod.get_db()
    try:
        run_id = cmp.resolve_run(database, run)["_id"]
    except ValueError as e:
        _fail(str(e))
    plan = dbmod.explain_run_lookup(database, run_id)
    if not plan["available"]:
        _fail(plan["reason"])
    typer.echo(f"  query     db.eval_results.find({{run_id: '{run_id}'}})")
    typer.echo(f"  plan      {' <- '.join(s['stage'] for s in plan['stages'])}")
    typer.echo(f"  index     {plan['index']}")
    typer.echo(f"  examined  {plan['keys_examined']} keys, {plan['docs_examined']} docs "
               f"-> {plan['n_returned']} returned in {plan['time_ms']} ms")
    typer.secho("  IXSCAN: index used" if plan["uses_index"] else "  COLLSCAN: no index!",
                fg=typer.colors.GREEN if plan["uses_index"] else typer.colors.RED, bold=True)


@app.command()
def reset(yes: bool = typer.Option(False, "--yes", help="Skip the confirmation")):
    """Delete all runs, results and comparisons (keeps prompts and test cases)."""
    if not yes:
        typer.confirm("Delete all runs, results and comparisons?", abort=True)
    dbmod.reset_runs(dbmod.get_db())
    typer.secho("Run history cleared.", fg=typer.colors.GREEN)


@app.command("demo-duplicate")
def demo_duplicate(run_id: str = typer.Option(None, "--run-id")):
    """Failure case: re-send a stored result and show it is ignored."""
    try:
        r = demomod.replay_duplicate(dbmod.get_db(), run_id)
    except ValueError as e:
        _fail(str(e))
    typer.echo(f"  re-sent {r['result_id']} ({r['test_case_id']} of {r['run_id']})")
    typer.secho(f"  outcome: {r['outcome']}  (results in run: {r['count_before']} -> "
                f"{r['count_after']})", fg=typer.colors.GREEN if r["outcome"] == "duplicate"
                else typer.colors.RED)


@app.command("demo-incomplete")
def demo_incomplete():
    """Failure case: send a result with no run_id and show the validator rejects it."""
    r = demomod.insert_incomplete(dbmod.get_db())
    typer.secho(f"  result without {r['missing_field']}: {r['outcome']}",
                fg=typer.colors.GREEN if r["outcome"] == "rejected" else typer.colors.RED)


if __name__ == "__main__":
    app()
