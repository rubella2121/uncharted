"""Command-line interface: `guard <command>`.

Implemented so far:  setup, doctor
Planned (see docs/PROGRESS.md):  seed, run, compare, reset
"""
import typer
from pymongo.errors import DuplicateKeyError, WriteError

from guard import config, db as dbmod
from guard.ids import utcnow

app = typer.Typer(add_completion=False, help="Prompt Regression Guard")


@app.command()
def setup():
    """Create collections, validators, and indexes. Safe to run repeatedly."""
    database = dbmod.get_db()
    for line in dbmod.ensure_schema(database):
        typer.echo(f"  {line}")
    typer.secho("Schema ready.", fg=typer.colors.GREEN)


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


if __name__ == "__main__":
    app()
