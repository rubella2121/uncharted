# Instructions for AI coding agents (and humans)

This repo is built step by step, possibly by several different AI agents. Read this
whole file before changing anything, then read `docs/SPEC.md` (what to build) and
`docs/PROGRESS.md` (what is done and what is next).

## Project in one line

Prompt Regression Guard answers **"Is this prompt or model change safe to ship?"** by
running a test set against prompt versions, storing every result in MongoDB, comparing
runs with aggregation pipelines, and giving a verdict: SAFE / RISKY / NOT_SAFE /
INCONCLUSIVE. Hackathon: UNCHARTED 2026, Track 3 (MongoDB). Deadline 31 Oct 2026,
9:00 PM IST. **No commits after the deadline.**

## How to work

1. Pick the first step in `docs/PROGRESS.md` that is not done. Do only that step.
2. Follow `docs/SPEC.md` exactly: function signatures, field names, check types,
   expected verdicts. Do not rename fields or collections.
3. Write tests for the step in `tests/`. Run `python -m pytest -q`; it must be green.
4. Update `docs/PROGRESS.md` (status + one log line) in the same commit.
5. Commit with a clear message: `Step N: <what>`.

## Commands

```bash
pip install -r requirements.txt
cp .env.example .env            # then paste the Atlas URI
python -m pytest -q             # unit tests (mongomock, no network needed)
python -m guard setup           # create collections, validators, indexes on Atlas
python -m guard doctor          # verify Atlas: duplicate + validator + index checks
```

Later steps add: `python -m guard seed | run <version> | compare <base> <cand>` and
`uvicorn guard.api:app --reload` for the dashboard.

## Layout

```
guard/config.py      all settings + collection names + thresholds + exit codes
guard/ids.py         stable_id(), result_id(), comparison_id(), new_run_id(), utcnow()
guard/db.py          get_db(), VALIDATORS, INDEXES, ensure_schema(), supports_percentile()
guard/cli.py         typer app (python -m guard ...)
guard/checks.py      [step 2] run_check(check, output), run_checks(checks, output)
guard/mock_model.py  [step 3] call_model(prompt_version, test_case, simulate_timeout)
guard/runner.py      [step 3] run_eval(db, version, simulate_timeouts, run_id, on_result)
guard/compare.py     [step 4] compare_pipeline(), run_stats(), decide(), compare_runs()
guard/api.py         [step 5] FastAPI app, REST + SSE (change streams)
web/index.html       [step 6] single page, plain JS, no build step
data/*.json          [step 2] prompt versions and test cases
tests/               pytest; conftest.py gives a mongomock `db` fixture
```

## Rules that must not be broken

- **Collection names** come from `guard/config.py` constants. Never hard-code them.
- **IDs** come from `guard/ids.py`. A result ID is always `result_id(run_id, test_case_id)`.
  Never use random IDs or ObjectId for results, runs, or comparisons.
- **`run_id` is created once** per run and passed through. Never regenerate it mid-run.
- **Timestamps** are timezone-aware `datetime` objects (`ids.utcnow()`), never strings.
- **Every result has `status` and `passed`.** On timeout/error: `passed=False`,
  `status="timeout"|"error"`, no `latency_ms`.
- **Timeouts/errors are `unverified`,** never counted as pass or fail. The `unverified`
  branch comes first in the `$switch`.
- **Verdict order:** NOT_SAFE (any regression) → INCONCLUSIVE → RISKY → SAFE.
- **Duplicates are expected,** not errors: catch `DuplicateKeyError`, log "duplicate
  ignored", continue. Catch `WriteError` with code 121 (validation) the same way.
- **Comparisons are upserts** by `comparison_id(base, cand)`.
- **The mock model must stay deterministic** (seeded RNG). The demo depends on it.
- **Do not add validator rules for `output` or `checks`** in `eval_results`: the flexible
  payload is a deliberate design point.
- **Never commit `.env`** or any secret. Only `.env.example`.
- **Deployment is compulsory.** Anything the demo shows must be doable from the web UI.
- Keep dependencies minimal (see `requirements.txt`). No frontend build tools.

## Testing notes

- `tests/conftest.py` provides `db`: a fresh mongomock database with `ensure_schema`
  applied. mongomock enforces unique indexes but **not** `$jsonSchema` validators and
  has **no** `$percentile` or change streams. Test validator behaviour via
  `guard doctor` against Atlas; test p95 via the Python fallback path.
- `db.supports_percentile(db)` returns False under mongomock, so compare code must have
  the Python fallback and tests exercise it.

## Style

- Python 3.10+, type hints on public functions, short docstrings that say *why*.
- Small modules, plain functions; no classes unless they clearly help.
- Match the comment density of the existing files.
