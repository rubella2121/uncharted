"""Markdown release report for a comparison, posted as a pull-request comment by
.github/workflows/prompt-guard-pr.yml. It answers the reviewer's questions in order:
can I merge? what broke and why? what did it cost? where do I look next?
"""
from pymongo.database import Database

from guard import config

# Hidden marker so the workflow can find and update its own comment.
MARKER = "<!-- prompt-regression-guard -->"

HEADLINE = {
    "SAFE": "✅ SAFE TO SHIP",
    "RISKY": "⚠️ RISKY",
    "NOT_SAFE": "❌ NOT SAFE TO SHIP",
    "INCONCLUSIVE": "❔ INCONCLUSIVE",
}
ADVICE = {
    "SAFE": "No regressions, and latency and cost are within limits.",
    "RISKY": "Quality held, but it is noticeably slower or more expensive. Decide consciously.",
    "NOT_SAFE": "At least one test case that passed before now fails. Fix before merging.",
    "INCONCLUSIVE": "Some cases could not be verified. Re-run before merging.",
}


def _cell(text) -> str:
    return str(text if text is not None else "—").replace("|", "\\|").replace("\n", " ")


def _git_label(git: dict | None) -> str:
    if not git:
        return ""
    sha = f"[`{git['short']}`]({git['commit_url']})" if git.get("commit_url") else f"`{git['short']}`"
    return sha + (f" · PR #{git['pr']}" if git.get("pr") else "")


def _pct(value: float) -> str:
    return f"{value:+.0f}%"


def markdown_report(db: Database, comparison: dict, dashboard_url: str | None = None) -> str:
    c = comparison
    m, b, n = c["metrics"], c["metrics"]["baseline"], c["metrics"]["candidate"]
    by_change: dict[str, list[str]] = {}
    for row in c["rows"]:
        by_change.setdefault(row["change"], []).append(row["test_case_id"])

    names = {tc["_id"]: tc for tc in db[config.TEST_CASES].find(
        {"project_id": c["project_id"]}, {"name": 1, "risk": 1})}
    cand_results = {r["test_case_id"]: r for r in db[config.EVAL_RESULTS].find(
        {"run_id": c["candidate_run"]}, {"test_case_id": 1, "checks": 1, "status": 1, "error": 1})}

    def why(tc_id: str) -> str:
        r = cand_results.get(tc_id) or {}
        if r.get("status") not in (None, "ok"):
            return f"{r['status']}: {r.get('error') or ''}"
        failed = [f"`{k['type']}`: {k['detail']}" for k in r.get("checks") or [] if not k["passed"]]
        return "; ".join(failed) or "—"

    base_label = _git_label(c.get("baseline_git"))
    cand_label = _git_label(c.get("candidate_git"))
    lines = [
        MARKER,
        f"## 🛡️ PARAKH: {HEADLINE[c['verdict']]}",
        "",
        f"**`{c['baseline_version']}`**{' (' + base_label + ')' if base_label else ''} → "
        f"**`{c['candidate_version']}`**{' (' + cand_label + ')' if cand_label else ''}. "
        f"{ADVICE[c['verdict']]}",
        "",
    ]
    lines += [f"- {_cell(r)}" for r in c["reasons"]]
    lines += [f"- ⚠️ {_cell(w)}" for w in c.get("warnings") or []]
    lines += [
        "",
        f"| | `{c['baseline_version']}` | `{c['candidate_version']}` | Change |",
        "|---|---:|---:|---:|",
        f"| Pass rate | {b['passed']}/{b['total']} | {n['passed']}/{n['total']} | "
        f"{n['passed'] - b['passed']:+d} |",
        f"| p95 latency | {b['p95_ms']} ms | {n['p95_ms']} ms | {_pct(m['p95_change_pct'])} |",
        f"| Total cost | ${b['total_cost']:.6f} | ${n['total_cost']:.6f} | "
        f"{_pct(m['cost_change_pct'])} |",
        "",
    ]

    def case_table(title: str, ids: list[str], with_reason: bool) -> None:
        if not ids:
            return
        lines.append(f"### {title} ({len(ids)})")
        lines.append("")
        lines.append("| Case | Scenario | Risk |" + (" Why it fails now |" if with_reason else ""))
        lines.append("|---|---|---|" + ("---|" if with_reason else ""))
        for tc_id in ids:
            tc = names.get(tc_id, {})
            row = f"| `{tc_id}` | {_cell(tc.get('name'))} | {_cell(tc.get('risk'))} |"
            lines.append(row + (f" {_cell(why(tc_id))} |" if with_reason else ""))
        lines.append("")

    case_table("❌ Regressed", by_change.get("regressed", []), True)
    case_table("❔ Could not verify", by_change.get("unverified", []), True)
    case_table("✅ Fixed", by_change.get("fixed", []), False)
    case_table("🟡 Still failing", by_change.get("still_failing", []), True)

    passing = by_change.get("still_passing", [])
    if passing:
        lines += [f"<details><summary>{len(passing)} case(s) still passing</summary>", "",
                  ", ".join(f"`{t}`" for t in passing), "", "</details>", ""]

    exit_code = {"SAFE": 0, "NOT_SAFE": 1}.get(c["verdict"], 2)
    footer = f"<sub>Exit code `{exit_code}` · comparison `{c['_id']}` · " \
             f"runs `{c['baseline_run']}` → `{c['candidate_run']}`"
    if dashboard_url:
        footer += f" · [Open the dashboard]({dashboard_url.rstrip('/')}/)"
    lines.append(footer + "</sub>")
    return "\n".join(lines) + "\n"
