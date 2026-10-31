# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: hackathon judges** (UNCHARTED 2026, Track 3, MongoDB) opening the deployed
  dashboard cold and trying the core flow in about two minutes. They must understand the
  question, run a comparison, see a verdict and grasp why, without a walkthrough.
- **Secondary: developers of LLM-powered apps** who change a prompt or model and need to
  know, before shipping or merging, whether the change made the app worse, slower, or
  more expensive. They meet PARAKH on the dashboard, the `guard` CLI, and as a bot
  comment on their GitHub pull request.

## Product Purpose

PARAKH answers one question: **"Is this prompt or model change safe to ship?"** It runs
a fixed test set against prompt versions, stores every result in MongoDB, compares a
baseline run with a candidate run, and returns one of four verdicts with reasons.
Success: a developer or judge can tell in seconds whether to ship, and in one click which
test case broke and why.

## Positioning

Unit tests plus CI for prompts, built on deterministic checks (no LLM-as-judge), with a
verdict that refuses to call a change safe when evidence is missing. The history lives in
MongoDB, so the same verdict appears in the dashboard, the CLI exit code, and the PR
comment.

## Operating Context

- Demo app under test: **SupportBot**, a JSON customer-support assistant; 30 test cases
  (`data/test_cases.json`), 3 prompt versions (`data/prompts.json`).
- Typical flow: run v1 (baseline) → run a candidate → verdict appears → open the diff of a
  regressed case → check history and cost/latency deltas.
- Also used from the terminal (`python -m guard ...`) and in GitHub Actions
  (`.github/workflows/prompt-guard*.yml`), where exit codes gate merges.
- Judges watch a recorded demo video (≤ 7 min) and a 10-minute live presentation; the
  dashboard is also screenshotted for slides.

## Capabilities and Constraints

- **Four verdicts, fixed:** SAFE, RISKY, NOT SAFE, INCONCLUSIVE. INCONCLUSIVE is never
  presented as a pass. Rule order: any regression → NOT SAFE; missing/unverified data →
  INCONCLUSIVE; p95 > +25% or cost > +30% → RISKY; else SAFE.
- Per-case states: regressed, fixed, still passing, still failing, unverified.
- Live results stream in via MongoDB change streams (polling fallback); failure-case demos
  (duplicate event, incomplete input, timeouts) must stay triggerable from the UI.
- Stack is fixed: FastAPI + a single static `web/index.html` with plain JS, no build step.
- Deployment is compulsory; deadline 31 Oct 2026, 9:00 PM IST, no commits after.
- Internal identifiers stay as they are (`guard` Python package and CLI, collection names,
  the PR-comment marker); only user-facing naming changes to PARAKH.

## Brand Commitments

- Name: **PARAKH** (from Hindi परख, "to test / assay"). Replaces "Prompt Regression Guard"
  in all user-facing places. The core question above is kept as the tagline.
- Built for UNCHARTED 2026 (NEXUS × SVNIT), in collaboration with MongoDB.

## Evidence on Hand

- All results come from a **scripted, deterministic mock model**
  (`guard/mock_model.py`). Numbers (latency, cost, pass rates) are illustrative and must
  never be presented as coming from a real LLM, real customers, or production traffic.
- Real artifacts: GitHub Actions runs and PR bot comments on `rubella2121/uncharted`,
  Atlas verification (MongoDB 8.0, change streams, IXSCAN). No testimonials, users,
  customers or benchmarks exist; do not invent any.

## Product Principles

1. Answer the one question first; detail is one click away, never in the way.
2. Missing evidence is never safety: unverified stays visibly distinct from pass and fail.
3. Every failure explains itself (which check, what it found).
4. Honest about the mock: illustrative data is labeled as such.
5. Show the MongoDB machinery (change streams, indexes, validation, aggregation), because
   it is part of what is being judged.

## Accessibility & Inclusion

WCAG 2.1 AA: text and UI contrast at AA, full keyboard operation, visible focus, and pass
/ fail / unverified never conveyed by color alone (always paired with a word or icon).
