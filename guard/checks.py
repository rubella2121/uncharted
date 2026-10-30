"""Deterministic checks. No LLM, no network: same output always gives the same verdict.

Every check returns {"type": str, "passed": bool, "detail": str}. The detail says why a
check failed, which is what turns a red row into something a developer can fix.
Spec: docs/SPEC.md section 4.
"""
import json
import re


def parse_json_object(output: str) -> dict | None:
    """Parsed JSON object, or None if the output is not a JSON object."""
    try:
        parsed = json.loads(output)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _result(check_type: str, passed: bool, detail: str) -> dict:
    return {"type": check_type, "passed": passed, "detail": detail}


def _text_for_length(output: str) -> str:
    """Length limits apply to what the customer reads: the `reply` field when the output
    is JSON, otherwise the raw text."""
    obj = parse_json_object(output)
    if obj is not None and isinstance(obj.get("reply"), str):
        return obj["reply"]
    return output


def _is_valid_json(output, _value):
    obj = parse_json_object(output)
    if obj is None:
        return False, "not parseable as a JSON object"
    return True, "valid JSON object"


def _json_has_keys(output, keys):
    obj = parse_json_object(output)
    if obj is None:
        return False, "output is not JSON"
    missing = [k for k in keys if k not in obj]
    if missing:
        return False, f"missing keys: {', '.join(missing)}"
    return True, f"has keys: {', '.join(keys)}"


def _json_field_equals(output, value):
    obj = parse_json_object(output)
    if obj is None:
        return False, "output is not JSON"
    field, expected = value["field"], value["equals"]
    if field not in obj:
        return False, f"field '{field}' missing"
    actual = obj[field]
    if actual != expected:
        return False, f"{field} = {actual!r}, expected {expected!r}"
    return True, f"{field} = {expected!r}"


def _contains_keyword(output, keyword):
    if keyword.lower() in output.lower():
        return True, f"found '{keyword}'"
    return False, f"'{keyword}' not found"


def _not_contains_keyword(output, keyword):
    if keyword.lower() in output.lower():
        return False, f"forbidden '{keyword}' found"
    return True, f"'{keyword}' absent"


def _max_words(output, limit):
    count = len(_text_for_length(output).split())
    if count > limit:
        return False, f"{count} words, limit {limit}"
    return True, f"{count} words (limit {limit})"


def _regex_match(output, pattern):
    try:
        found = re.search(pattern, output)
    except re.error as e:
        return False, f"invalid regex: {e}"
    if found:
        return True, f"matched '{found.group(0)}'"
    return False, f"no match for /{pattern}/"


CHECKS = {
    "is_valid_json": _is_valid_json,
    "json_has_keys": _json_has_keys,
    "json_field_equals": _json_field_equals,
    "contains_keyword": _contains_keyword,
    "not_contains_keyword": _not_contains_keyword,
    "max_words": _max_words,
    "regex_match": _regex_match,
}
CHECK_TYPES = frozenset(CHECKS)


def run_check(check: dict, output: str) -> dict:
    check_type = check.get("type")
    fn = CHECKS.get(check_type)
    if fn is None:
        return _result(str(check_type), False, "unknown check type")
    passed, detail = fn(output if isinstance(output, str) else "", check.get("value"))
    return _result(check_type, passed, detail)


def run_checks(checks: list[dict], output: str) -> tuple[bool, list[dict]]:
    """Run every check. A test case passes only if it has checks and all of them pass."""
    results = [run_check(c, output) for c in checks]
    return bool(results) and all(r["passed"] for r in results), results
