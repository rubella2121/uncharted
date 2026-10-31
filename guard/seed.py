"""Load prompt versions and test cases from data/*.json into MongoDB.

Seeding is an idempotent upsert keyed on _id: running it twice leaves one copy of each
document, and created_at keeps its first value ($setOnInsert). Data files are validated
before anything is written, so a typo in a check type fails loudly instead of producing
a test case that can never pass.
"""
import json
from pathlib import Path

from pymongo.database import Database

from guard import config
from guard.checks import CHECK_TYPES
from guard.ids import prompt_version_id, utcnow

PROMPT_FIELDS = ("version", "project_id", "model", "prompt_text",
                 "price_per_1k_in", "price_per_1k_out")
TEST_CASE_FIELDS = ("_id", "project_id", "name", "input", "checks")


def load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_prompts(prompts: list[dict]) -> None:
    seen = set()
    for p in prompts:
        missing = [f for f in PROMPT_FIELDS if f not in p]
        if missing:
            raise ValueError(f"prompt {p.get('version', '?')}: missing {', '.join(missing)}")
        key = (p["project_id"], p["version"])
        if key in seen:
            raise ValueError(f"prompt {p['version']}: duplicate version")
        seen.add(key)


def validate_test_cases(test_cases: list[dict]) -> None:
    seen = set()
    for tc in test_cases:
        missing = [f for f in TEST_CASE_FIELDS if f not in tc]
        if missing:
            raise ValueError(f"test case {tc.get('_id', '?')}: missing {', '.join(missing)}")
        if tc["_id"] in seen:
            raise ValueError(f"test case {tc['_id']}: duplicate _id")
        seen.add(tc["_id"])
        if not tc["checks"]:
            raise ValueError(f"test case {tc['_id']}: has no checks")
        for check in tc["checks"]:
            if check.get("type") not in CHECK_TYPES:
                raise ValueError(f"test case {tc['_id']}: unknown check type {check.get('type')!r}")


def _upsert(coll, doc: dict) -> bool:
    """Insert or update by _id. Returns True if the document was newly inserted."""
    fields = {k: v for k, v in doc.items() if k != "_id"}
    res = coll.update_one(
        {"_id": doc["_id"]},
        {"$set": fields, "$setOnInsert": {"created_at": utcnow()}},
        upsert=True,
    )
    return res.upserted_id is not None


def seed(db: Database, data_dir: Path = config.DATA_DIR) -> list[str]:
    """Validate and upsert data/prompts.json and data/test_cases.json. Returns log lines."""
    prompts = load_json(data_dir / "prompts.json")
    test_cases = load_json(data_dir / "test_cases.json")
    validate_prompts(prompts)
    validate_test_cases(test_cases)

    log = []
    for p in prompts:
        doc = {"_id": prompt_version_id(p["project_id"], p["version"]), **p}
        new = _upsert(db[config.PROMPT_VERSIONS], doc)
        log.append(f"prompt {doc['_id']}: {'inserted' if new else 'updated'}")
    for tc in test_cases:
        new = _upsert(db[config.TEST_CASES], tc)
        log.append(f"test case {tc['_id']}: {'inserted' if new else 'updated'}")
    return log
