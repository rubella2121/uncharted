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
| 3 | Mock model + runner | `guard/mock_model.py`, `guard/runner.py`, `guard run` | `guard run v1` stores 12 results (11 pass); re-running a stored result is ignored; `--simulate-timeouts` works; `guard run v99` exits 3 | ⬜ |
| 4 | Comparison + verdict | `guard/compare.py`, `guard compare`, `tests/test_compare.py` | v1→v2 NOT_SAFE (3 regressed, 1 fixed); v1→v3 RISKY; v1→v3+timeouts INCONCLUSIVE; exit codes correct | ⬜ |
| 5 | API | `guard/api.py` | all endpoints in SPEC §12 respond; runs can be started from HTTP | ⬜ |
| 6 | Live dashboard | `web/index.html`, SSE endpoints | rows appear live while a run executes; verdict banner updates; buttons for run / compare / timeouts / duplicate / reset | ⬜ |
| 7 | Deploy | `render.yaml` or equivalent, README deploy section | public URL works against Atlas; judges can run the full demo from the browser | ⬜ |
| — | **FEATURE FREEZE** at ~6:00 PM IST | | | |
| 8 | Polish + submission | README, architecture diagram, `.explain()` screenshot, PPT, ≤7 min demo video | rulebook section 16 checklist complete | ⬜ |

If behind schedule, cut in this order: bonus features → `.explain()` screenshot → UI
polish. Never cut the failure-case demo or the INCONCLUSIVE logic.

## Notes for the next step (Step 3: mock model + runner)

- Write `GOOD_OUTPUTS[tc_id]` so each output passes **every** check of that case in
  `data/test_cases.json` (add a test that asserts this for all 12).
- Scripted failures must fail for the intended reason only:
  v1/tc10 reply > 50 words; v2/tc02 plain text (not JSON); v2/tc07 JSON without "sorry";
  v2/tc11 output contains "You are SupportBot"; v2/tc10 uses the short good output.
- Cost targets (SPEC §6): v1→v2 about -85%, v1→v3 above +30%; p95 v1→v3 above +25%.
  Tune token counts / base latency in `mock_model.py`, not the prices in `prompts.json`,
  and add a test that checks these targets.

## Log

- 31 Oct 00:30 IST: Step 1 implemented (14 tests passing with mongomock). Atlas not
  reachable from the build sandbox, so `guard doctor` still needs to be run locally.
- 31 Oct 01:00 IST: Step 2 done: `guard/checks.py` (7 check types), `guard/seed.py`, `guard seed` CLI, data files (3 prompt versions, 12 test cases). 49 tests green.
