import json

import pytest

from guard.checks import CHECK_TYPES, parse_json_object, run_check, run_checks

GOOD = json.dumps({"category": "billing",
                   "reply": "Sorry about the double charge! Refund for ORD-12345 started."})
PLAIN = "Sure! You can reset your password from the login page."

# (check, output, expected_passed) - every check type has at least one pass and one fail
CASES = [
    ({"type": "is_valid_json"}, GOOD, True),
    ({"type": "is_valid_json"}, PLAIN, False),
    ({"type": "is_valid_json"}, "[1, 2]", False),  # JSON, but not an object
    ({"type": "json_has_keys", "value": ["category", "reply"]}, GOOD, True),
    ({"type": "json_has_keys", "value": ["category", "order_id"]}, GOOD, False),
    ({"type": "json_has_keys", "value": ["category"]}, PLAIN, False),
    ({"type": "json_field_equals", "value": {"field": "category", "equals": "billing"}}, GOOD, True),
    ({"type": "json_field_equals", "value": {"field": "category", "equals": "refund"}}, GOOD, False),
    ({"type": "json_field_equals", "value": {"field": "missing", "equals": "x"}}, GOOD, False),
    ({"type": "json_field_equals", "value": {"field": "category", "equals": "x"}}, PLAIN, False),
    ({"type": "contains_keyword", "value": "SORRY"}, GOOD, True),  # case-insensitive
    ({"type": "contains_keyword", "value": "apologies"}, GOOD, False),
    ({"type": "not_contains_keyword", "value": "calm down"}, GOOD, True),
    ({"type": "not_contains_keyword", "value": "Double Charge"}, GOOD, False),
    ({"type": "max_words", "value": 60}, GOOD, True),
    ({"type": "max_words", "value": 3}, GOOD, False),
    ({"type": "max_words", "value": 5}, PLAIN, False),
    ({"type": "regex_match", "value": r"ORD-\d{5}"}, GOOD, True),
    ({"type": "regex_match", "value": r"ORD-\d{5}"}, PLAIN, False),
    ({"type": "regex_match", "value": "("}, GOOD, False),  # invalid regex never crashes
    ({"type": "not_regex_match", "value": r"\b\d{4} \d{4} \d{4} \d{4}\b"}, GOOD, True),
    ({"type": "not_regex_match", "value": r"ORD-\d{5}"}, GOOD, False),  # leaked identifier
    ({"type": "not_regex_match", "value": "("}, GOOD, False),
    ({"type": "json_field_in", "value": {"field": "category", "in": ["billing", "refund"]}}, GOOD, True),
    ({"type": "json_field_in", "value": {"field": "category", "in": ["shipping"]}}, GOOD, False),
    ({"type": "json_field_in", "value": {"field": "missing", "in": ["x"]}}, GOOD, False),
    ({"type": "json_field_in", "value": {"field": "category", "in": ["billing"]}}, PLAIN, False),
]


@pytest.mark.parametrize("check,output,expected", CASES)
def test_check(check, output, expected):
    result = run_check(check, output)
    assert result["passed"] is expected
    assert result["type"] == check["type"]
    assert isinstance(result["detail"], str) and result["detail"]


def test_every_check_type_is_covered_both_ways():
    for check_type in CHECK_TYPES:
        outcomes = {exp for c, _, exp in CASES if c["type"] == check_type}
        assert outcomes == {True, False}, check_type


def test_max_words_counts_reply_field_not_json_syntax():
    out = json.dumps({"category": "other", "reply": "one two three"})
    assert run_check({"type": "max_words", "value": 3}, out)["passed"]


def test_failure_detail_explains_why():
    r = run_check({"type": "contains_keyword", "value": "sorry"}, PLAIN)
    assert r["detail"] == "'sorry' not found"


def test_unknown_check_type_fails():
    r = run_check({"type": "is_polite"}, GOOD)
    assert r == {"type": "is_polite", "passed": False, "detail": "unknown check type"}


def test_none_output_does_not_crash():
    assert run_check({"type": "contains_keyword", "value": "x"}, None)["passed"] is False


def test_run_checks_all_must_pass():
    checks = [{"type": "is_valid_json"}, {"type": "contains_keyword", "value": "sorry"}]
    passed, results = run_checks(checks, GOOD)
    assert passed and len(results) == 2
    passed, _ = run_checks(checks + [{"type": "max_words", "value": 2}], GOOD)
    assert not passed


def test_run_checks_empty_list_is_not_a_pass():
    assert run_checks([], GOOD) == (False, [])


def test_parse_json_object():
    assert parse_json_object(GOOD)["category"] == "billing"
    assert parse_json_object(PLAIN) is None
