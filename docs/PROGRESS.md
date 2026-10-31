# Build progress

Deadline: **31 Oct 2026, 9:00 PM IST** (code freeze; submission form closes 10:00 PM).
After the deadline, NO commits are allowed (rulebook section 8).

Update this file in the same commit as the work. Mark a step done only when its
"done when" check actually passes. Add a line to the log at the bottom.

## Steps

| # | Step | Files | Done when | Status |
|---|---|---|---|---|
| 1 | Foundation: config, stable IDs, collections, validators, indexes, `setup`/`doctor` CLI, handoff docs | `guard/config.py`, `guard/ids.py`, `guard/db.py`, `guard/cli.py`, `tests/test_ids.py`, `tests/test_db.py`, docs | `pytest` green; `guard doctor` passes against Atlas | ✅ done (verified on Atlas, MongoDB 8.0) |
| 2 | Checks + demo data | `guard/checks.py`, `data/prompts.json`, `data/test_cases.json`, `tests/test_checks.py`, `guard seed` | each check type has a pass and a fail test; `guard seed` loads 3 versions + 30 cases (idempotent upsert) | ✅ done |
| 3 | Mock model + runner | `guard/mock_model.py`, `guard/runner.py`, `guard run` | `guard run v1` stores 30 results (29 pass); re-running a stored result is ignored; `--simulate-timeouts` works; `guard run v99` exits 3 | ✅ done |
| 4 | Comparison + verdict | `guard/compare.py`, `guard compare`, `tests/test_compare.py` | v1→v2 NOT_SAFE (5 regressed, 1 fixed); v1→v3 RISKY; v1→v3+timeouts INCONCLUSIVE; exit codes correct | ✅ done |
| 5 | API | `guard/api.py` | all endpoints in SPEC §12 respond; runs can be started from HTTP | ✅ done (SSE verified only via polling fallback; check live against Atlas) |
| 6 | Live dashboard | `web/index.html`, SSE endpoints | rows appear live while a run executes; verdict banner updates; buttons for run / compare / timeouts / duplicate / reset | ✅ done (browser-tested against mongomock in polling mode) |
| 7 | Deploy | `render.yaml` or equivalent, README deploy section | public URL works against Atlas; judges can run the full demo from the browser | 🟡 config ready (`render.yaml`, `Dockerfile`, `Procfile`, `docs/DEPLOY.md`); **a team member must deploy** |
| — | **FEATURE FREEZE** at ~6:00 PM IST | | | |
| 8 | Polish + submission | README, architecture diagram, `.explain()` screenshot, PPT, ≤7 min demo video | rulebook section 16 checklist complete | 🟡 README, `docs/DEMO_SCRIPT.md`, `docs/PPT_OUTLINE.md` written; still need: live URL in README, screenshots from Atlas, PPT, video |

If behind schedule, cut in this order: bonus features → `.explain()` screenshot → UI
polish. Never cut the failure-case demo or the INCONCLUSIVE logic.

## What is left (needs a human with Atlas + Render accounts)

1. `python -m guard doctor` against Atlas → all PASS. (Nothing has run against a real
   MongoDB yet; the build sandbox could not reach Atlas.)
2. `uvicorn guard.api:app` locally → header shows **live: change stream** (not polling);
   run the full demo once in the browser.
3. Deploy following `docs/DEPLOY.md`; run its checklist; put the URL in README.
4. Screenshots from the deployed app + Atlas (documents, validator, indexes, explain)
   for the PPT; record the video with `docs/DEMO_SCRIPT.md`.
5. Rulebook section 16 checklist. **Submit by 10 PM; no commits after 9 PM.**

Optional, only if all of the above is done before ~6 PM: real-LLM mode behind a flag
(`call_model` replacement, temperature 0, reads `ANTHROPIC_API_KEY`/other key from env),
`--repeats N`, PR comment bot. Do not risk the working demo for these.

If something breaks on Atlas, likely suspects: `$percentile` (needs 7.0+, has a Python
fallback), change-stream permissions (the API falls back to polling and says so),
`collMod` permissions on M0 (validators are created with the collection; `collMod` only
runs on re-setup).

## Actual demo numbers (mock model, from tests)

| Comparison | Verdict | Counts | p95 | Cost |
|---|---|---|---|---|
| v1→v2 | NOT_SAFE | 5 regressed (tc02, tc07, tc11, tc17, tc23), 1 fixed (tc10) | 782→558 ms (-29%) | -92% |
| v1→v3 | RISKY | 0 regressed, 1 fixed | 782→1091 ms (+40%) | +68% |
| v1→v3 + timeouts tc03,tc05,tc09 | INCONCLUSIVE | 3 unverified | | |

## Log

- 31 Oct 00:30 IST: Step 1 implemented (14 tests passing with mongomock). Atlas not
  reachable from the build sandbox, so `guard doctor` still needs to be run locally.
- 31 Oct 01:00 IST: Step 2 done: `guard/checks.py` (7 check types), `guard/seed.py`, `guard seed` CLI, data files (3 prompt versions, 12 test cases). 49 tests green.
- 31 Oct 01:45 IST: Steps 3+4 done: mock model, runner (resume, timeouts, duplicates), comparison pipeline, stats with $percentile + Python fallback, verdict rules, CLI `run/compare/history/reset/demo-duplicate/demo-incomplete`, failure-case helpers in `guard/demo.py`. 107 tests green.
- 31 Oct 02:15 IST: Step 5 done: `guard/api.py` (REST + SSE via change streams with polling fallback, background runs, auto schema+seed on startup). 116 tests green.
- 31 Oct 03:00 IST: Step 6 dashboard (live table, verdict banner, auto-compare, failure buttons, query plan), `guard explain` + `/api/explain`, deploy config (Render/Docker/Procfile), GitHub Actions (tests + prompt-guard gate example), README, DEPLOY, DEMO_SCRIPT, PPT_OUTLINE. 118 tests green. Dashboard verified in Chromium (desktop + 390px mobile).
- 31 Oct: Atlas verified by the team: dashboard shows MongoDB 8.0 + live change stream, RISKY verdict and IXSCAN plan as expected. Fixed tc12 Spanish output being shown as \u escapes (ensure_ascii=False).
- 31 Oct: Insights added: side-by-side case diff with word highlighting and check-by-check table (auto-opens first regression), version history chart (aggregation + $lookup), readiness score 0-100 in chart, run list and `guard history`. 126 tests green; UI verified in Chromium incl. 390px.
- 31 Oct: Test set expanded 12 → 30 cases (PII, jailbreak, HTML injection, Hinglish, emoji, legal threat, multi-intent, data deletion, ...) and 2 new check types (`not_regex_match`, `json_field_in`). v2 now regresses 5 cases. Verdicts unchanged in kind. Live delay 0.35 → 0.2 s. 153 tests green.
