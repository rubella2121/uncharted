import json

import pytest

from guard import config
from guard.seed import load_json, seed, validate_prompts, validate_test_cases


def test_shipped_data_is_valid():
    prompts = load_json(config.DATA_DIR / "prompts.json")
    cases = load_json(config.DATA_DIR / "test_cases.json")
    validate_prompts(prompts)
    validate_test_cases(cases)
    assert [p["version"] for p in prompts] == ["v1", "v2", "v3"]
    assert [c["_id"] for c in cases] == [f"tc{i:02d}" for i in range(1, 13)]


def test_seed_loads_everything(db):
    seed(db)
    assert db[config.PROMPT_VERSIONS].count_documents({}) == 3
    assert db[config.TEST_CASES].count_documents({}) == 12
    v2 = db[config.PROMPT_VERSIONS].find_one({"_id": "supportbot:v2"})
    assert v2["model"] == "mock-mini" and v2["created_at"] is not None


def test_seed_is_idempotent(db):
    seed(db)
    first = db[config.PROMPT_VERSIONS].find_one({"_id": "supportbot:v1"})["created_at"]
    log = seed(db)
    assert db[config.PROMPT_VERSIONS].count_documents({}) == 3
    assert db[config.TEST_CASES].count_documents({}) == 12
    assert all("updated" in line for line in log)
    assert db[config.PROMPT_VERSIONS].find_one({"_id": "supportbot:v1"})["created_at"] == first


def test_unknown_check_type_rejected():
    bad = [{"_id": "tc99", "project_id": "p", "name": "n", "input": "i",
            "checks": [{"type": "is_nice"}]}]
    with pytest.raises(ValueError, match="unknown check type"):
        validate_test_cases(bad)


def test_duplicate_test_case_rejected():
    tc = {"_id": "tc01", "project_id": "p", "name": "n", "input": "i",
          "checks": [{"type": "is_valid_json"}]}
    with pytest.raises(ValueError, match="duplicate"):
        validate_test_cases([tc, dict(tc)])


def test_prompt_missing_field_rejected():
    with pytest.raises(ValueError, match="missing"):
        validate_prompts([{"version": "v1", "project_id": "p"}])


def test_bad_data_dir_writes_nothing(db, tmp_path):
    (tmp_path / "prompts.json").write_text(json.dumps([{"version": "v1"}]))
    (tmp_path / "test_cases.json").write_text("[]")
    with pytest.raises(ValueError):
        seed(db, tmp_path)
    assert db[config.PROMPT_VERSIONS].count_documents({}) == 0
