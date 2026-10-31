# PARAKH: Specification

This is the source of truth for **what** to build. If code and this file disagree, fix
the code or update this file in the same commit, with a reason.

## 1. The one question

> **"Is this prompt or model change safe to ship?"**

PARAKH (formerly "Prompt Regression Guard") is unit tests plus CI for LLM prompts. A developer defines a
test set (inputs plus deterministic checks). Each prompt version is run against the test
set, every result is stored in MongoDB, and two runs are compared to give a release
verdict: **SAFE, RISKY, NOT_SAFE, or INCONCLUSIVE**.

Hackathon context: UNCHARTED 2026 (NEXUS x SVNIT), Track 3 "Developer Tools for
Production use cases", MongoDB track. The problem statement asks for: stable IDs and
timestamps, indexes for frequent questions, aggregation pipelines to compare runs,
schema validation with flexible payloads, change streams for live views, idempotent
ingestion, and a demo with one practical failure case. **A live deployment is
compulsory** (rulebook section 6), so every core action must be triggerable from the
web UI, not only from the CLI.

## 2. Vocabulary

| Term | Meaning |
|---|---|
| Project | The AI app being tracked. Demo: `supportbot` |
| Prompt version | Prompt text + model + prices. `v1`, `v2`, `v3` |
| Test case | One input plus a list of checks. All checks must pass for the case to pass |
| Check | One deterministic pass/fail rule (`is_valid_json`, `contains_keyword`, ...) |
| Eval run | One execution of the whole test set against one prompt version |
| Eval result | Outcome of one test case in one run |
| Comparison | Baseline run vs candidate run, with a verdict |
| Regression | Passed in baseline, fails in candidate |

## 3. Demo app: SupportBot

A customer-support assistant that must return JSON:
`{"category": "refund", "reply": "Sorry about the trouble! ..."}`.
Categories: `refund, account, shipping, billing, cancellation, product, other`.

## 4. Checks (all deterministic, no LLM)

Each check returns `{"type": str, "passed": bool, "detail": str}`. The `detail` explains
why it failed; it is what makes this a debugging tool rather than a scoreboard.

| type | `value` | Passes when |
|---|---|---|
| `is_valid_json` | none | output parses as JSON (and is an object) |
| `json_has_keys` | `["category","reply"]` | parsed object has all keys |
| `json_field_equals` | `{"field":"category","equals":"billing"}` | field equals value |
| `contains_keyword` | `"sorry"` | case-insensitive substring found (searches the whole raw output) |
| `not_contains_keyword` | `"calm down"` | case-insensitive substring NOT found |
| `max_words` | `60` | word count of the output (the `reply` field if JSON, else raw text) is at most N |
| `regex_match` | `"ORD-\\d{5}"` | `re.search` matches |
| `not_regex_match` | card-number pattern | `re.search` does NOT match (PII must not be echoed) |
| `json_field_in` | `{"field":"category","in":["refund","shipping"]}` | field is one of the allowed values |

`is_valid_json` requires a JSON *object* (a list does not count). A test case with no
checks never passes. An unknown check type returns `passed: false` with detail `unknown check type`.
JSON checks on non-JSON output return `passed: false` with detail `output is not JSON`.

## 5. Test set (30 cases, `data/test_cases.json`)

| ID | Scenario | Risk it covers |
|---|---|---|
| tc01 | refund request | core intent |
| tc02 | password reset | format (JSON) |
| tc03 | shipping delay | required content ("tracking") |
| tc04 | angry customer | tone (no "calm down") |
| tc05 | competitor mention | banned content (competitor name) |
| tc06 | cancel subscription | classification |
| tc07 | double charge | empathy ("sorry") |
| tc08 | product question | classification |
| tc09 | gibberish input | graceful fallback (category `other`) |
| tc10 | long rambling message | length limit (`max_words`) |
| tc11 | prompt-injection attempt | security (must not leak system prompt) |
| tc12 | non-English message | format still valid |
| tc13 | order status with order number | required content (order ID + tracking) |
| tc14 | wrong item received | apology + return label |
| tc15 | change email address | classification |
| tc16 | delete my data request | privacy / compliance (30 days) |
| tc17 | customer shares card number | **PII: card number must never be echoed** |
| tc18 | discount code not working | classification |
| tc19 | warranty claim | required content |
| tc20 | international shipping question | classification |
| tc21 | legal threat | tone under pressure (category may be other/billing/refund) |
| tc22 | asks for a human agent | escalation |
| tc23 | Hinglish message | format still valid |
| tc24 | emoji-only message | graceful fallback |
| tc25 | simple greeting | fallback + length |
| tc26 | HTML/script injection in input | no markup echoed |
| tc27 | role-play jailbreak | no secrets |
| tc28 | two issues in one message | multi-intent (refund or shipping) |
| tc29 | one-word message | asks for missing info |
| tc30 | price match with competitor | banned content (Amazon) |

Seeding (`guard seed`, `guard/seed.py`) validates both data files first (required fields,
known check types, no duplicate IDs) and only then upserts by `_id`; `created_at` is set
once with `$setOnInsert`.

## 6. Mock model (`guard/mock_model.py`)

A scripted fake LLM so the demo is reproducible. Same interface as a real client would
have, so a real LLM can be plugged in later behind a `--live` flag.

```python
call_model(prompt_version: dict, test_case: dict, simulate_timeout=False) -> dict
# returns {"output": str, "latency_ms": int, "tokens_in": int, "tokens_out": int}
# raises TimeoutError when simulate_timeout is True
```

- Output = `BROKEN_OUTPUTS[(version, tc_id)]` if present, else `GOOD_OUTPUTS[tc_id]`.
- Latency is deterministic: `rng = random.Random(f"7-{version}-{tc_id}")`,
  `latency_ms = int(base_ms + rng.random() * base_ms * 0.35)`, base per version.
- tokens_in = words(prompt_text) + words(input) scaled ~1.3; tokens_out = words(output) * 1.3.

| Version | Story | Behaviour | Model / base latency |
|---|---|---|---|
| v1 | Baseline: long prompt, big model | All pass except **tc10** (reply too long, ~90 words) | `mock-large`, ~600 ms |
| v2 | "Shorter prompt, cheaper model" | **tc02** plain text (not JSON), **tc07** no "sorry", **tc11** leaks system prompt, **tc17** echoes the card number, **tc23** plain text; **tc10** now short (fixed) | `mock-mini`, ~430 ms, ~7x cheaper |
| v3 | "Few-shot examples" | All 30 pass; much longer prompt so more tokens | `mock-large`, ~820 ms |

Expected comparisons (these are acceptance tests):

| Comparison | Expected verdict | Why |
|---|---|---|
| v1 → v2 | **NOT_SAFE** | 5 regressed (tc02, tc07, tc11, tc17, tc23), 1 fixed (tc10); cost -92%, p95 -29% |
| v1 → v3 | **RISKY** | 0 regressed, 1 fixed; p95 latency > +25% and cost > +30% |
| v1 → v3 with timeouts on tc03,tc05,tc09 | **INCONCLUSIVE** | 0 regressed, 3 unverified |

## 7. Data model (MongoDB)

Five collections. Implemented in `guard/db.py` (validators + indexes).

| Collection | One document is | `_id` |
|---|---|---|
| `prompt_versions` | one prompt version | `"{project_id}:{version}"` e.g. `supportbot:v2` |
| `test_cases` | one test case | `tc01`..`tc12` |
| `eval_runs` | one run | `run_{version}_{YYYYmmddTHHMMSS}` (created once, passed through) |
| `eval_results` | one test case in one run (main collection) | `stable_id("res", run_id, test_case_id)` |
| `comparisons` | one baseline-vs-candidate verdict | `stable_id("cmp", baseline_run, candidate_run)` |

### eval_results document

```json
{
  "_id": "res_9f2c41ab07d3e5c1",
  "project_id": "supportbot",
  "run_id": "run_v2_20261030T103015",
  "test_case_id": "tc02",
  "prompt_version": "v2",
  "status": "ok",                 // ok | error | timeout
  "passed": false,                // ALWAYS present; false on error/timeout
  "output": "Sure! You can reset...",
  "checks": [{"type": "is_valid_json", "passed": false, "detail": "not parseable as JSON"}],
  "error": null,                  // message when status != ok
  "latency_ms": 512,              // omitted (not 0) when status != ok
  "tokens_in": 171, "tokens_out": 14,
  "cost_usd": 0.000023,
  "timestamp": ISODate(...)       // real BSON date, never a string
}
```

### eval_runs document

`{_id, project_id, prompt_version, status: running|completed|completed_with_errors|failed,
started_at, finished_at, test_set_size, test_set_hash, summary: {total, passed, errors}}`

### comparisons document

`{_id, project_id, baseline_run, candidate_run, baseline_version, candidate_version,
verdict, reasons: [str], counts: {regressed, fixed, still_passing, still_failing,
unverified}, metrics: {baseline: {...}, candidate: {...}, p95_change_pct,
cost_change_pct}, rows: [{test_case_id, change}], created_at}`.
Upserted by `_id`, so running the same comparison twice updates one document.

### Design decisions (say these to judges)

| Decision | Why |
|---|---|
| `checks` embedded in the result | Always read together, small and bounded |
| Test cases referenced by `test_case_id` | Reused across many runs |
| `project_id`, `prompt_version` copied into each result | Common queries need no join (intentional denormalization) |
| `output`, `checks` not in the validator | Flexible payload; different checks carry different details |
| Runs do not embed results | Avoids the unbounded-array antipattern |
| Stable `_id` + unique `{run_id, test_case_id}` | Idempotent ingestion: duplicates are rejected, resumed runs skip stored cases |

### Indexes

| Collection | Index | Question |
|---|---|---|
| eval_results | `{run_id:1, test_case_id:1}` unique | all results of run X; already stored? |
| eval_results | `{project_id:1, prompt_version:1, timestamp:-1}` | latest results for version |
| eval_runs | `{project_id:1, started_at:-1}` | recent runs |
| eval_runs | `{project_id:1, prompt_version:1, started_at:-1}` | latest run of version |
| prompt_versions | `{project_id:1, version:1}` unique | no duplicate versions |
| comparisons | `{project_id:1, created_at:-1}` | recent verdicts |

## 8. Runner (`guard/runner.py`)

```
run_eval(db, version, simulate_timeouts=set(), run_id=None, on_result=None) -> run doc
  load prompt version (error if missing -> "prompt version not found", exit code 3)
  run_id = run_id or new_run_id(version); insert eval_runs {status: running}
  for each test case (sorted by _id):
      call model -> on TimeoutError: status=timeout, passed=False
                 -> on other Exception: status=error, passed=False
                 -> else run checks, passed = all(check.passed)
      cost = tokens_in/1000*price_in + tokens_out/1000*price_out
      insert_one(result)
          DuplicateKeyError  -> log "duplicate ignored", continue
          WriteError code 121 -> log "rejected by validator", continue
  update run: status completed | completed_with_errors, finished_at, summary
```

Add a small delay between results (e.g. 150-300 ms, configurable, 0 in tests) so the
live dashboard visibly fills row by row.

## 9. Comparison engine (`guard/compare.py`)

Every test case falls into exactly one category:

| change | Baseline | Candidate |
|---|---|---|
| `unverified` | not ok **or** missing | not ok **or** missing (either side) |
| `regressed` | pass | fail |
| `fixed` | fail | pass |
| `still_passing` | pass | pass |
| `still_failing` | fail | fail |

Pipeline: `$match {run_id: {$in: [base, cand]}}` → `$group` by `test_case_id` with
four 0/1 flags (`base_ok`, `base_pass`, `cand_ok`, `cand_pass`) built with
`$sum: {$cond: [...]}` → `$project` with `$switch` (unverified branch FIRST) → `$sort`.
Note: a test case present in only one run has flags 0 on the other side, so it lands in
`unverified`, which is correct.

Stats pipeline per run: `$group` with `total`, `ok_count`, `errors`, `passed`,
`total_cost`, and `p95_ms` via `$percentile` (`p: [0.95]`, `method: "approximate"`,
input is latency only when `status == "ok"`, else null). Read element `[0]`.
`$percentile` needs MongoDB 7.0+; if `db.supports_percentile()` is False, fetch the
latencies and compute p95 in Python (nearest-rank).

## 10. Verdict rules (`decide()`), evaluated in this order

1. `regressed > 0` → **NOT_SAFE** ("N test case(s) regressed"). Proven harm stands even with partial data.
2. `unverified > 0` or errors in either run → **INCONCLUSIVE** ("N test case(s) could not be verified"). Missing data can never prove safety.
3. p95 latency change > `LATENCY_THRESHOLD_PCT` (25) or cost change > `COST_THRESHOLD_PCT` (30) → **RISKY** with reasons.
4. Otherwise **SAFE**.

`pct_change(new, old)` returns 0 when old is 0 or None.
CLI exit codes: SAFE 0, NOT_SAFE 1, RISKY/INCONCLUSIVE 2, usage error 3 (`guard/config.py`).

## 11. Live view (change streams)

API process watches `eval_results` with
`[{"$match": {"operationType": "insert", "fullDocument.run_id": run_id}}]` and forwards
each document to the browser via Server-Sent Events. Also watch `comparisons` for the
verdict banner. **Race-condition fix:** on page load, first fetch existing results with
a normal query, then subscribe, and de-duplicate by `_id` in the browser.
Change streams need a replica set: Atlas (even free M0) has one; a plain local
`mongod` does not.

## 12. Web API (`guard/api.py`, FastAPI) — needed for the compulsory deployment

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | serves `web/index.html` |
| GET | `/api/versions` | prompt versions |
| GET | `/api/test-cases` | test cases |
| GET | `/api/runs` | recent runs |
| GET | `/api/runs/{run_id}/results` | results of one run |
| POST | `/api/runs` `{version, simulate_timeouts: []}` | start a run in a background thread, return `run_id` immediately |
| POST | `/api/compare` `{baseline_run, candidate_run}` (or versions → latest runs) | compute + store comparison |
| GET | `/api/comparisons/latest` | latest verdict |
| POST | `/api/demo/duplicate` | re-insert an existing result, show it was ignored |
| POST | `/api/demo/reset` | clear runs/results/comparisons |
| GET | `/api/stream/{run_id}` | SSE: live results (change stream) |
| GET | `/api/stream/comparisons` | SSE: new verdicts (change stream) |

## 13. Failure cases for the demo

| Failure | Trigger | Expected | MongoDB feature |
|---|---|---|---|
| Duplicate event | re-send an existing result | DuplicateKeyError caught, "duplicate ignored", count unchanged | unique index + stable IDs |
| Incomplete input | insert result without `run_id` | rejected (code 121), logged, run continues | schema validation |
| Failed job | `guard run v3 --simulate-timeouts tc03,tc05,tc09` | 3 timeout results, verdict INCONCLUSIVE | honest missing-data handling |
| Invalid config | `guard run v99` | "prompt version not found", exit 3 | input validation |

## 13b. Insights (added 31 Oct)

- **Case diff** (`compare.case_diff`, `GET /api/diff?baseline=&candidate=&test_case_id=`):
  both runs' outputs for one test case plus every check with its baseline/candidate
  outcome and a `changed` flag. The dashboard shows a word-level diff (red removed,
  green added) and opens the first regressed case automatically after a compare.
- **Version history** (`compare.run_history`, `GET /api/history`, `guard history`):
  one aggregation over `eval_results` (`$group` per run with `$percentile`, then a
  `$lookup` into `eval_runs` for status), oldest → newest, drawn as a line chart.
- **Readiness score** (`compare.readiness_score`): 0-100 =
  70 × pass rate + 15 × min(1, ref p95 / p95) + 15 × min(1, ref cost / cost).
  Reference = newest finished v1 run, else the oldest run shown. Timeouts count as not
  passed. Demo values: v1 98, v2 88, v3 90, v3 with 3 timeouts 84. The score is a
  summary for humans; the verdict rules (section 10) remain the release gate.

## 13c. GitHub integration (added 31 Oct)

- `guard/gitmeta.py` `detect()` → `{sha, short, branch, pr, repo, source, commit_url,
  pr_url}` from `GUARD_*`, `GITHUB_*`, `RENDER_GIT_*` env vars or local git; `None` if
  unknown. Stored once per run as `eval_runs.git` (validator: object with `sha`; sparse
  index `git_sha`). Comparisons copy `baseline_git` / `candidate_git`.
- `guard/report.py` `markdown_report(db, comparison, dashboard_url)` → PR comment text,
  starting with the hidden marker `<!-- prompt-regression-guard -->` so the bot edits
  its own comment. `guard compare A B --markdown FILE` writes it before exiting.
- `data/release.json` `{baseline, candidate}` selects what the PR bot compares.
- Details and demo steps: `docs/GITHUB.md`.

## 14. Out of scope unless everything else is done

LLM-as-judge, real LLM `--live` mode, `--repeats N`, auth, multiple projects in the UI,
n8n integration, GitHub App / webhooks. Do not start these before docs/PROGRESS.md steps 1-7 are done.
