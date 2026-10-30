# Presentation deck outline

Required by the submission form: problem, solution, implementation, technology
choices, impact. Aim for 10 to 12 slides with large text and one idea per slide.
Screenshots should come from the deployed app.

| # | Slide | Content |
|---|---|---|
| 1 | Title | Prompt Regression Guard. Subtitle: "Is this prompt change safe to ship?" Team name, 3 members, UNCHARTED 2026 Track 3. |
| 2 | Problem | AI teams edit prompts daily with no tests. Priya's story: a cheaper prompt breaks JSON, drops the apology, and leaks the system prompt; she finds out from customers 2 days later. |
| 3 | Solution | Unit tests plus CI for prompts. Test set → run each version → store in MongoDB → compare → verdict. The 4-verdict table (SAFE / RISKY / NOT SAFE / INCONCLUSIVE). |
| 4 | Demo screenshot: NOT SAFE | v1→v2: 3 regressed, 1 fixed, cost −92%. "Cheaper and faster, and still blocked." |
| 5 | Demo screenshot: RISKY and INCONCLUSIVE | v3: quality up, latency +38%, cost +61%. Timeouts → INCONCLUSIVE. |
| 6 | Architecture | Diagram from README (CLI/API → runner → MongoDB → change stream → dashboard). |
| 7 | MongoDB data model | 5 collections; example `eval_results` document; embedded vs referenced; denormalised `project_id` and `prompt_version`. |
| 8 | Reliability | Stable IDs plus unique index (duplicate ignored), `$jsonSchema` envelope with a flexible payload (incomplete rejected), timeouts are data, not crashes. |
| 9 | Aggregation | The comparison pipeline (`$match` → `$group` flags → `$switch`) and `$percentile` p95; the explain output showing IXSCAN. |
| 10 | Technology choices | Python, FastAPI, pymongo, Server-Sent Events, plain HTML/JS, MongoDB Atlas, Render. Why each one (simple, fast to build, few moving parts). |
| 11 | Impact and next steps | CI gate via exit codes (GitHub Actions workflow included). Next: real-LLM mode, LLM-judge checks, PR comments, production baseline pinning. |
| 12 | Thank you | Live URL, GitHub URL, QR code. |
