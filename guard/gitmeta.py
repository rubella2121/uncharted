"""Which code version produced a run: commit, branch, pull request, repository.

Stored on every eval_runs document so a verdict can be traced back to the exact commit
or PR that changed the prompt. Sources, first match wins:
  GUARD_GIT_SHA / GUARD_GIT_BRANCH / GUARD_PR   explicit (set by our PR workflow)
  GITHUB_*                                       GitHub Actions
  RENDER_GIT_*                                   the Render deployment
  local `git`                                    a developer's machine
Returns None when nothing is known (e.g. a container without .git); never raises.
"""
import os
import re
import subprocess
from functools import lru_cache

from guard import config


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=config.ROOT_DIR, capture_output=True,
                             text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    value = out.stdout.strip()
    return value if out.returncode == 0 and value else None


def parse_repo(remote_url: str | None) -> str | None:
    """'owner/repo' from https, ssh or proxied git remote URLs."""
    if not remote_url:
        return None
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", remote_url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def detect(env: dict | None = None, use_git: bool = True) -> dict | None:
    env = os.environ if env is None else env
    sha = (env.get("GUARD_GIT_SHA") or env.get("GITHUB_SHA") or env.get("RENDER_GIT_COMMIT")
           or (_git("rev-parse", "HEAD") if use_git else None))
    if not sha:
        return None
    branch = (env.get("GUARD_GIT_BRANCH") or env.get("GITHUB_HEAD_REF")
              or env.get("GITHUB_REF_NAME") or env.get("RENDER_GIT_BRANCH")
              or (_git("rev-parse", "--abbrev-ref", "HEAD") if use_git else None))
    repo = (env.get("GITHUB_REPOSITORY") or env.get("RENDER_GIT_REPO_SLUG")
            or (parse_repo(_git("config", "--get", "remote.origin.url")) if use_git else None))
    pr_raw = env.get("GUARD_PR") or ""
    pr = int(pr_raw) if pr_raw.isdigit() else None
    if env.get("GITHUB_ACTIONS") == "true":
        source = "github-actions"
    elif env.get("RENDER_GIT_COMMIT"):
        source = "render"
    else:
        source = "local"
    base = f"https://github.com/{repo}" if repo else None
    return {
        "sha": sha,
        "short": sha[:7],
        "branch": branch,
        "pr": pr,
        "repo": repo,
        "source": source,
        "commit_url": f"{base}/commit/{sha}" if base else None,
        "pr_url": f"{base}/pull/{pr}" if base and pr else None,
    }


@lru_cache(maxsize=1)
def detect_cached() -> dict | None:
    """For the API server: the deployed code version does not change while it runs."""
    return detect()
