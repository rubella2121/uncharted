# GitHub integration

Two workflows plus commit tracking turn the guard into a merge gate.

| Piece | File | What it does |
|---|---|---|
| Manual gate | `.github/workflows/prompt-guard.yml` | Actions → prompt-guard → Run workflow with any two versions; red unless SAFE; report in the job summary |
| **PR bot** | `.github/workflows/prompt-guard-pr.yml` | On every PR touching `data/**` or `guard/**`: runs baseline and candidate from `data/release.json`, **comments the verdict on the PR** (updates the same comment on re-runs), writes the job summary, and fails the check unless SAFE |
| **Commit tracking** | `guard/gitmeta.py` | Every run stores `git: {sha, branch, pr, repo, source, commit_url, pr_url}`; the dashboard links runs and verdicts to the commit/PR; `eval_runs` has a `git.sha` index |

## One-time setup

1. Repository secret `MONGODB_URI` (Settings → Secrets and variables → Actions → Secrets).
   Already done if the manual gate has run.
2. Optional: repository **variable** `GUARD_DASHBOARD_URL` = your deployed URL
   (Settings → Secrets and variables → Actions → Variables). The comment then links to it.
3. Optional, for a real merge block: Settings → Branches → add a rule for `main` →
   *Require status checks to pass* → select **guard**.

## Demo: a PR that the bot blocks (about 5 minutes)

1. On GitHub, open `data/release.json` on `main` → ✏️ Edit.
2. Change `"candidate": "v3"` to `"candidate": "v2"` (the cheap prompt).
3. **Commit changes** → choose *Create a new branch* (e.g. `cheaper-prompt`) → **Propose changes** → **Create pull request**.
4. Wait about 1 minute. The **guard** check turns red, and the bot comments:
   **❌ NOT SAFE TO SHIP**, a metrics table, and the 5 regressed cases with the reason each
   one fails (for example the card number leak in tc17).
5. Open the dashboard: the new runs appear tagged `⎇ <commit> · PR #N · CI`.
6. Optional: edit `data/release.json` in the same PR to `"candidate": "v1"` → the bot
   **updates its comment** to ✅ SAFE and the check turns green.

Take screenshots of the PR comment and the red/green checks for the slides.

## Notes

- Forked PRs do not receive secrets, so the bot runs only for branches in this repo.
- Each CI run writes real runs into the same database, so they show up in the dashboard
  history. Click **Reset run history** before recording the demo if needed.
