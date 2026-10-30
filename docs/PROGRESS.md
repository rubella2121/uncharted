# Build progress

Deadline: **31 Oct 2026, 9:00 PM IST** (code freeze; submission form closes 10:00 PM).
After the deadline, NO commits are allowed (rulebook section 8).

Update this file in the same commit as the work. Mark a step done only when its
"done when" check actually passes. Add a line to the log at the bottom.

## Steps

| # | Step | Files | Done when | Status |
|---|---|---|---|---|
| 1 | Foundation: config, stable IDs, collections, validators, indexes, `setup`/`doctor` CLI, handoff docs | `guard/config.py`, `guard/ids.py`, `guard/db.py`, `guard/cli.py`, `tests/test_ids.py`, `tests/test_db.py`, docs | `pytest` green; `guard doctor` passes against Atlas | ✅ code done (Atlas check pending: run `python -m guard doctor`) |
| 2 | Checks + demo data | `guard/checks.py`, `data/prompts.json`, `data/test_cases.json`, `tests/test_checks.py`, `guard seed` | each check type has a pass and a fail test; `guard seed` loads 3 versions + 12 cases (idempotent upsert) | ⬜ |
| 3 | Mock model + runner | `guard/mock_model.py`, `guard/runner.py`, `guard run` | `guard run v1` stores 12 results (11 pass); re-running a stored result is ignored; `--simulate-timeouts` works; `guard run v99` exits 3 | ✅ done |
| 4 | Comparison + verdict | `guard/compare.py`, `guard compare`, `tests/test_compare.py` | v1→v2 NOT_SAFE (3 regressed, 1 fixed); v1→v3 RISKY; v1→v3+timeouts INCONCLUSIVE; exit codes correct | ✅ done |
| 5 | API | `guard/api.py` | all endpoints in SPEC §12 respond; runs can be started from HTTP | ⬜ |
| 6 | Live dashboard | `web/index.html`, SSE endpoints | rows appear live while a run executes; verdict banner updates; buttons for run / compare / timeouts / duplicate / reset | ⬜ |
| 7 | Deploy | `render.yaml` or equivalent, README deploy section | public URL works against Atlas; judges can run the full demo from the browser | ⬜ |
| — | **FEATURE FREEZE** at ~6:00 PM IST | | | |
| 8 | Polish + submission | README, architecture diagram, `.explain()` screenshot, PPT, ≤7 min demo video | rulebook section 16 checklist complete | ⬜ |

If behind schedule, cut in this order: bonus features → `.explain()` screenshot → UI
polish. Never cut the failure-case demo or the INCONCLUSIVE logic.

## Notes for the next step (Step 5: API)

- Reuse, do not re-implement: `runner.start_run()` (validates + returns run_id fast),
  `runner.run_eval(run_id=...)` in a background thread (`delay_s≈0.25` for the live view;
  wrap in try/except and call `runner.fail_run()` on crash), `compare.compare_runs()`,
  `demo.replay_duplicate()`, `demo.insert_incomplete()`, `db.reset_runs()`.
- Map `VersionNotFound`/`RunNotFound`/`ValueError` to HTTP 404/400 with the message.
- Datetimes must be JSON-serialised (ISO strings) in responses and SSE events.
- Change streams: `db.eval_results.watch([{"$match": {"operationType": "insert",
  "fullDocument.run_id": run_id}}])`. Blocking iterator: run it in a thread or use
  `try_next()` in a loop with `await asyncio.sleep`. mongomock has no `watch`, so test
  SSE manually against Atlas; unit-test the REST endpoints with FastAPI TestClient.

## Actual demo numbers (mock model, from tests)

| Comparison | Verdict | Counts | p95 | Cost |
|---|---|---|---|---|
| v1→v2 | NOT_SAFE | 3 regressed (tc02, tc07, tc11), 1 fixed (tc10) | 797→558 ms (-30%) | -92% |
| v1→v3 | RISKY | 0 regressed, 1 fixed | 797→1101 ms (+38%) | +61% |
| v1→v3 + timeouts tc03,tc05,tc09 | INCONCLUSIVE | 3 unverified | | |

## Log

- 31 Oct 00:30 IST: Step 1 implemented (14 tests passing with mongomock). Atlas not
  reachable from the build sandbox, so `guard doctor` still needs to be run locally.
- 31 Oct 01:00 IST: Step 2 done: `guard/checks.py` (7 check types), `guard/seed.py`, `guard seed` CLI, data files (3 prompt versions, 12 test cases). 49 tests green.
- 31 Oct 01:45 IST: Steps 3+4 done: mock model, runner (resume, timeouts, duplicates), comparison pipeline, stats with $percentile + Python fallback, verdict rules, CLI `run/compare/history/reset/demo-duplicate/demo-incomplete`, failure-case helpers in `guard/demo.py`. 107 tests green.
