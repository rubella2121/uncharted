# Demo script

Two versions: the **demo video** (7 minutes maximum, part of the submission) and the
**final presentation** (10 minutes plus 2 minutes Q&A, top 16 teams only). Rehearse
each at least three times, and reset the run history before recording.

## Opening line (both)

> "AI teams change prompts all the time, and nothing tells them whether the change broke
> something. We built a guard that answers one question: **is this prompt or model
> change safe to ship?**"

## Demo video (about 6 minutes)

| Time | Show | Say |
|---|---|---|
| 0:00–0:40 | Title slide → dashboard | Problem: no unit tests for prompts. Story: SupportBot must reply in JSON, and Priya edits the prompt to cut cost. |
| 0:40–1:30 | Test cases (expand a row) | 30 cases, deterministic checks: valid JSON, routing, required words, banned words, length, prompt injection, jailbreaks, card-number leaks. No LLM judge, so the result is reproducible. |
| 1:30–2:15 | **Run v1** (rows stream in live) | "Each row is a MongoDB document, and the page updates from a change stream." Result: 29/30, and tc10 is too long. |
| 2:15–3:15 | **Run v2**, verdict appears | "Shorter prompt, cheaper model. Cost fell 92%, and the tool still says **NOT SAFE**: password reset is no longer JSON, the apology is gone, it leaks its system prompt, and it reads a customer's card number back to them." The diff opens on tc02 automatically: v1 JSON struck out in red, v2 plain text in green. Click tc17 to show the card number leak, a real compliance problem. |
| 3:15–3:50 | **Run v3** | Few-shot prompt: all 30 pass, but **RISKY**: p95 +40%, cost +68%. "It is a decision aid, not just pass/fail." |
| 3:50–4:40 | **Run v3 with timeouts tc03, tc05, tc09** | **INCONCLUSIVE**. "Most tools would report 27 of 27 = 100% and be wrong. Missing data can never prove safety." Then scroll to the **version history chart**: readiness 98 → 88 → 90 → 84, the whole story in one picture from one aggregation. |
| 4:40–5:30 | Failure buttons + MongoDB Atlas (Compass or the Atlas UI) | Re-send a result → duplicate ignored, count unchanged (stable ID + unique index). Result without run_id → rejected by `$jsonSchema`. Show a result document, the validator and the indexes; click **Show query plan** → IXSCAN. |
| 5:30–6:00 | Terminal: `python -m guard compare v1 v2; echo $?` → 1 | "Exit codes make it a CI merge gate; there is a GitHub Actions workflow in the repo." Closing line. |

## Final presentation (10 minutes)

1. **Problem (1 min):** prompts change constantly and have no tests; the Priya story.
2. **Solution (1 min):** one question, four verdicts. Show the verdict table.
3. **Live demo (4 min):** v1 → v2 NOT SAFE → v3 RISKY → timeouts INCONCLUSIVE → duplicate.
4. **MongoDB design (2.5 min):** architecture diagram; the five collections;
   embedded checks vs referenced test cases; stable IDs + unique index; validator
   envelope with a flexible payload; the comparison pipeline (`$group` → `$switch`);
   `$percentile` for p95; change streams for the live view; explain → IXSCAN.
5. **Impact and next steps (1 min):** CI gate via exit codes; next: real-LLM mode,
   LLM-judge checks, GitHub PR comments, pinned production baseline.
6. **Close (30 s):** "One question, deterministic checks, history in MongoDB, and a
   verdict a developer can put in CI."

## Likely judge questions

| Question | Answer |
|---|---|
| Why a mock model? | Reproducible demo. `call_model()` is the only thing to swap for a real LLM at temperature 0; the runner, checks, storage and comparison stay the same. |
| Why not a spreadsheet? | The value is history across versions: queries for what regressed since v1, idempotent ingestion, live updates, and indexes. |
| Why not an LLM judge? | Deterministic checks are free, instant and reproducible. An LLM judge can disagree with itself between runs. It is a planned bonus. |
| p95 over 30 samples? | 30 latencies per run is enough for a rough tail estimate; for production we would add repeated runs per case. |
| Why is INCONCLUSIVE checked after NOT_SAFE? | Missing data cannot prove safety, but it does not erase a regression we already observed. |
| Why embed checks but reference test cases? | Checks are small, bounded, and always read with the result. Test cases are reused by every run. |
| What happens if the runner crashes mid-run? | Resume with the same run ID: stored cases are skipped (unique index), so nothing is duplicated and no model call is repeated. |
| Why 0.0.0.0/0 in Atlas network access? | The free host uses changing IPs. In production you would use private networking or a fixed egress IP. |
