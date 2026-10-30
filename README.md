# Prompt Regression Guard

> **Is this prompt or model change safe to ship?**

Unit tests plus CI for LLM prompts. Define a small test set with deterministic checks,
run each prompt version against it, store every result in **MongoDB**, and compare
versions to get a release verdict:

| Verdict | Meaning |
|---|---|
| ✅ SAFE | No regressions; latency and cost within limits |
| ⚠️ RISKY | Quality held, but p95 latency or cost grew past the threshold |
| ❌ NOT SAFE | At least one test case that passed before now fails |
| ❔ INCONCLUSIVE | Some cases timed out or errored, so safety cannot be proven |

Built for UNCHARTED 2026 (NEXUS × SVNIT), Track 3: Developer Tools for Production.

## Status

Under construction. See [`docs/PROGRESS.md`](docs/PROGRESS.md) for what works today and
[`docs/SPEC.md`](docs/SPEC.md) for the full design.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # paste your MongoDB Atlas connection string
python -m guard setup       # collections, validators, indexes
python -m guard doctor      # proves duplicate rejection, validation and index use
python -m pytest -q         # unit tests (no database needed)
```

## How MongoDB is used

- **Stable IDs:** each result's `_id` is a hash of `(run_id, test_case_id)`, so
  re-ingesting the same result is rejected by the unique index (idempotent ingestion).
- **Schema validation:** a strict `$jsonSchema` envelope (`run_id`, `status`, `passed`,
  `timestamp`, ...) while `output` and `checks` stay flexible.
- **Indexes** for the questions the tool asks most: results by run, latest results per
  version, recent runs.
- **Aggregation pipelines** classify every test case as regressed / fixed /
  still passing / still failing / unverified, and compute p95 latency and cost.
- **Change streams** push results to the dashboard live as a run executes.

## Contributing (humans and AI agents)

Read [`AGENTS.md`](AGENTS.md) first.
