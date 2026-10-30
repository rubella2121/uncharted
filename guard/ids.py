"""Stable, deterministic IDs. This is what makes ingestion idempotent.

The same logical event always gets the same _id, so inserting it twice collides on the
unique _id index and the second insert is rejected instead of creating a duplicate.
"""
import hashlib
import json
from datetime import datetime, timezone


def stable_id(prefix: str, *parts) -> str:
    """Hash the parts into a short, readable ID such as 'res_9f2c41ab07d3e5c1'."""
    raw = "|".join(str(p) for p in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def result_id(run_id: str, test_case_id: str) -> str:
    return stable_id("res", run_id, test_case_id)


def comparison_id(baseline_run_id: str, candidate_run_id: str) -> str:
    return stable_id("cmp", baseline_run_id, candidate_run_id)


def prompt_version_id(project_id: str, version: str) -> str:
    return f"{project_id}:{version}"


def new_run_id(version: str, now: datetime | None = None) -> str:
    """Create a run ID once at the start of a run. It is then passed through, never
    regenerated, so a resumed run reuses it and already-stored results are skipped."""
    now = now or utcnow()
    return f"run_{version}_{now.strftime('%Y%m%dT%H%M%S')}"


def test_set_hash(test_cases: list[dict]) -> str:
    """Fingerprint of the test set, stored on each run. Two runs with different hashes
    were evaluated against different test sets and should not be compared blindly."""
    canonical = json.dumps(
        sorted(test_cases, key=lambda tc: tc["_id"]), sort_keys=True, default=str
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def utcnow() -> datetime:
    """Timezone-aware UTC now. Stored as a real BSON date, never as a string."""
    return datetime.now(timezone.utc)
