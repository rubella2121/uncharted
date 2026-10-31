# PARAKH demo video script (target 6:30, hard limit 7:00)

Team Veni Vidi Vici · Gautam Jain (G) · Het Zaveri (H) · Vaishnavi Singh (V)

## Before you record (15 minutes)

- [ ] Open the **deployed URL** a minute early (Render's free tier sleeps; the first load is slow).
- [ ] On the dashboard click **Reset run history**, so the demo starts clean.
- [ ] Check the header says **MongoDB 8.x** and **Live: change stream**.
- [ ] Tabs ready, in order: slides (cover) · dashboard · MongoDB Atlas (or Compass) on `prompt_guard` · GitHub PR #1 · a terminal in the repo folder.
- [ ] Browser zoom 110–125% so text is readable in the video; hide bookmarks and notifications.
- [ ] Record at 1080p (OBS, or Windows `Win + Alt + R`). One take per section is fine; cut them together.
- [ ] Speak slowly. ~140 words a minute. Pause after each verdict appears.

---

## 0:00–0:35 · Hook and who we are (G) · ~85 words

**Screen:** slide 1 (cover with the release-check card).

> Hi, we are team Veni Vidi Vici from SVNIT: Gautam, Het and Vaishnavi. This is PARAKH, Hindi for “to test”.
> Every AI team changes its prompts all the time: to cut cost, to fix one complaint, to switch models. And they test those changes by trying two or three messages by hand.
> PARAKH answers one question for them: **is this prompt or model change safe to ship?**
> On the right is a real result: a prompt that was 92% cheaper, and still not safe to ship.

## 0:35–1:15 · Problem and solution (G) · ~95 words

**Screen:** slide 2, then slide 3 (workflow).

> The problem: prompts have no unit tests, so customers find the failures first.
> Our solution works in five steps. We define a test set once: 30 realistic support-chat cases, each with automatic checks for JSON format, routing, tone, banned words and leaked data. We run any prompt version against it, store every result in MongoDB, compare two runs with an aggregation pipeline, and get one verdict with the reasons: SAFE, RISKY, NOT SAFE or INCONCLUSIVE.
> Let’s see it live.

## 1:15–2:00 · Demo 1: baseline run (H) · ~80 words

**Screen:** dashboard. Point at the header, then select **v1**, click **Run evaluation**.

> This is our deployed dashboard, connected to MongoDB Atlas. The yellow label is honest: the model here is a scripted mock, so every number is reproducible.
> I run v1, our baseline prompt. Watch the rows: each one appears the moment MongoDB writes it, through a change stream. No polling.
> 29 of 30 pass. One case, a long rambling message, fails because the reply is too long, and the table says exactly why: 89 words, limit 50.

## 2:00–3:00 · Demo 2: the trap, NOT SAFE (H) · ~120 words

**Screen:** select **v2**, run it. When the verdict appears, pause. The diff opens on tc02 by itself; then click **tc17** in the grid.

> Now the realistic change: a much shorter prompt on a cheaper model. Cost drops 92%.
> And PARAKH says **NOT SAFE TO SHIP**. Five cases that passed before now fail.
> It opens the first one for us: password reset. On the left v1 answered in JSON; on the right v2 answers in plain text, which would crash the app’s parser. Every check is listed: three failed.
> And this one, tc17: the customer typed their card number, and the cheaper prompt reads it back to them. That is a privacy incident nobody would catch by hand.
> The verdict names exactly which two runs it compared, and the CI exit code is 1: blocked.

## 3:00–3:45 · Demo 3: RISKY and INCONCLUSIVE (H) · ~95 words

**Screen:** run **v3** → RISKY. Then open **Simulate timeouts**, tick tc03, tc05, tc09, run v3 again → INCONCLUSIVE.

> v3 adds examples to the prompt. Every case passes, but it is 40% slower and 68% more expensive, over our limits. So the verdict is **RISKY**: not a bug, a business decision.
> Now a failed job: three cases time out. Most tools would show 27 out of 27, 100%. PARAKH says **INCONCLUSIVE**, because missing data can never prove safety. And it offers a one-click re-run.

**Optional (if time):** scroll to the **Version history** chart: “every run is kept in MongoDB, so the whole history is one aggregation.”

## 3:45–4:50 · MongoDB under the hood (V) · ~150 words

**Screen:** dashboard **Failure handling** buttons, then Atlas, then the query plan button.

> Under the hood, MongoDB does the hard work. Three guarantees.
> One: idempotent ingestion. I re-send a stored result. It is ignored, and the count stays the same. Every result’s ID is a hash of its run and test case, protected by a unique index, so retries and crashed runs never create duplicates.
> Two: validation. I send a result without a run_id: MongoDB’s $jsonSchema validator rejects it, while the model’s output itself stays flexible.

**Screen:** Atlas → `eval_results`, open one document; show the Validation tab and the Indexes tab.

> Here is a stored result: run, test case, status, every check, latency and cost. Checks are embedded; test cases are referenced.
> Three: the comparison itself is an aggregation pipeline: $group and $switch label every case as regressed, fixed or unverified, and $percentile gives p95 latency.

**Screen:** click **Show query plan**.

> And lookups use an index: IXSCAN, not a full scan.

## 4:50–5:45 · GitHub merge gate (V) · ~110 words

**Screen:** terminal: `python -m guard compare v1 v2` then `echo $?` (shows 1). Then GitHub PR #1: the bot comment and the red check. Then dashboard run history showing the commit and PR link.

> The same verdict works where developers live. In the terminal, compare exits 0 for SAFE, 1 for NOT SAFE, 2 for RISKY or INCONCLUSIVE.
> On GitHub, every pull request that touches a prompt runs PARAKH automatically. A bot posts the verdict as a comment, updates it on every push, and the check only goes green when the verdict is SAFE. Here it is on our own pull request: RISKY, so the merge waits for a human.
> And every run in MongoDB is linked to the commit and pull request that produced it.

## 5:45–6:30 · Impact and close (G) · ~95 words

**Screen:** slide 5 (impact), then slide 1 to finish.

> So who benefits? Developers catch regressions before merging, and see exactly why. Teams can cut model costs safely, with a history of every prompt version. And end users stop getting broken replies or leaked data.
> PARAKH is deterministic, honest about missing data, and built on MongoDB: stable IDs, validation, aggregation and change streams.
> Next, we would plug in real models at temperature zero and compare every pull request against the version in production.
> We are Veni Vidi Vici. PARAKH: test the change before your users do. Thank you.

---

## Timing table

| Section | Speaker | Time |
|---|---|---|
| Hook | Gautam | 0:00–0:35 |
| Problem and solution | Gautam | 0:35–1:15 |
| Baseline run | Het | 1:15–2:00 |
| NOT SAFE + diff | Het | 2:00–3:00 |
| RISKY + INCONCLUSIVE | Het | 3:00–3:45 |
| MongoDB | Vaishnavi | 3:45–4:50 |
| GitHub gate | Vaishnavi | 4:50–5:45 |
| Impact and close | Gautam | 5:45–6:30 |

**If you run long:** drop the optional history-chart line and shorten the Atlas tour to one document. Never cut the NOT SAFE diff, the INCONCLUSIVE timeouts, or the duplicate/validator demo: they are what the judges score.

## Rulebook checks

- Video is **at most 7 minutes**, explains the project and demonstrates key functionality.
- Show the **deployed URL** (not localhost) in the dashboard part; a local-only video does not replace deployment.
- Do not show `.env`, the Atlas connection string, passwords or API keys on screen.
- Upload as unlisted YouTube or a Google Drive link with "anyone with the link can view", and test the link in a private window before submitting (by 10:00 PM IST).
