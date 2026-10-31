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
python -m guard seed            # load data/*.json into Atlas (safe to repeat)
```

Demo flow on the CLI:

```bash
python -m guard run v1
python -m guard run v2
python -m guard compare v1 v2                      # NOT SAFE, exit 1
python -m guard run v3
python -m guard compare v1 v3                      # RISKY, exit 2
python -m guard run v3 --simulate-timeouts tc03,tc05,tc09
python -m guard compare v1 v3                      # INCONCLUSIVE, exit 2
python -m guard demo-duplicate                     # duplicate ignored
python -m guard demo-incomplete                    # rejected by validator (Atlas only)
python -m guard reset --yes                        # clear run history
```

## Layout

```
guard/config.py      all settings + collection names + thresholds + exit codes
guard/ids.py         stable_id(), result_id(), comparison_id(), new_run_id(), utcnow()
guard/db.py          get_db(), VALIDATORS, INDEXES, ensure_schema(), supports_percentile()
guard/cli.py         typer app (python -m guard ...)
guard/checks.py      run_check(check, output) -> {type, passed, detail}; run_checks() -> (passed, results)
guard/seed.py        seed(db): validate data/*.json, then idempotent upsert
guard/mock_model.py  call_model(prompt_version, test_case, simulate_timeout) + scripted outputs
guard/runner.py      start_run(), run_eval(db, version, simulate_timeouts=, run_id=, on_result=, delay_s=)
guard/compare.py     compare_pipeline(), run_stats(), decide(), compare_runs(db, base, cand)
guard/demo.py        replay_duplicate(), insert_incomplete()  (failure-case demos)
guard/api.py         FastAPI app: REST + /api/stream SSE (change streams); `uvicorn guard.api:app --reload`
web/index.html       dashboard: single page, plain JS, no build step (REST first, then SSE)
data/*.json          prompts.json (v1,v2,v3), test_cases.json (tc01..tc30)
tests/               pytest; conftest.py gives a mongomock `db` fixture
docs/                SPEC (design), PROGRESS (status), DEPLOY, DEMO_SCRIPT, PPT_OUTLINE
render.yaml, Dockerfile, Procfile   deployment (always 1 worker)
.github/workflows/   tests.yml (pytest on push), prompt-guard.yml (CI gate example)
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
