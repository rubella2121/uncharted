import pytest

from guard import config
from guard.checks import run_checks
from guard.mock_model import BROKEN_OUTPUTS, GOOD_OUTPUTS, call_model
from guard.seed import load_json

PROMPTS = {p["version"]: p for p in load_json(config.DATA_DIR / "prompts.json")}
CASES = {c["_id"]: c for c in load_json(config.DATA_DIR / "test_cases.json")}


@pytest.mark.parametrize("tc_id", sorted(CASES))
def test_good_output_passes_every_check(tc_id):
    passed, results = run_checks(CASES[tc_id]["checks"], GOOD_OUTPUTS[tc_id])
    assert passed, [r for r in results if not r["passed"]]


@pytest.mark.parametrize("key,expected_failure", [
    (("v1", "tc10"), "max_words"),
    (("v2", "tc02"), "is_valid_json"),
    (("v2", "tc07"), "contains_keyword"),
    (("v2", "tc11"), "not_contains_keyword"),
    (("v2", "tc17"), "not_regex_match"),
    (("v2", "tc23"), "is_valid_json"),
])
def test_broken_output_fails_for_the_intended_reason(key, expected_failure):
    _, results = run_checks(CASES[key[1]]["checks"], BROKEN_OUTPUTS[key])
    failed = [r["type"] for r in results if not r["passed"]]
    assert failed and failed[0] == expected_failure


def test_v2_leak_contains_v2_prompt():
    assert PROMPTS["v2"]["prompt_text"] in BROKEN_OUTPUTS[("v2", "tc11")]


def test_deterministic():
    a = call_model(PROMPTS["v1"], CASES["tc01"])
    b = call_model(PROMPTS["v1"], CASES["tc01"])
    assert a == b


def test_latency_depends_on_version():
    v1 = call_model(PROMPTS["v1"], CASES["tc01"])["latency_ms"]
    v3 = call_model(PROMPTS["v3"], CASES["tc01"])["latency_ms"]
    assert v3 > v1


def test_timeout():
    with pytest.raises(TimeoutError):
        call_model(PROMPTS["v1"], CASES["tc01"], simulate_timeout=True)


def test_longer_prompt_costs_more_tokens():
    tin = {v: call_model(PROMPTS[v], CASES["tc01"])["tokens_in"] for v in PROMPTS}
    assert tin["v2"] < tin["v1"] < tin["v3"]
