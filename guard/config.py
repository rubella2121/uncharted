"""Central configuration. Every tunable value lives here, read from the environment.

Other modules import from here instead of calling os.getenv themselves, so there is
exactly one place to look when a setting needs to change.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
WEB_DIR = ROOT_DIR / "web"

load_dotenv(ROOT_DIR / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "")
DB_NAME = os.getenv("GUARD_DB_NAME", "prompt_guard")
PROJECT_ID = os.getenv("GUARD_PROJECT_ID", "supportbot")

# Verdict thresholds (Twist 1). A candidate whose p95 latency or total cost grows by
# more than this percentage over the baseline is RISKY even if quality held.
LATENCY_THRESHOLD_PCT = float(os.getenv("GUARD_LATENCY_THRESHOLD_PCT", "25"))
COST_THRESHOLD_PCT = float(os.getenv("GUARD_COST_THRESHOLD_PCT", "30"))

# CLI exit codes, so the tool can act as a CI merge gate.
EXIT_SAFE = 0
EXIT_NOT_SAFE = 1
EXIT_RISKY_OR_INCONCLUSIVE = 2
EXIT_USAGE_ERROR = 3

# Collection names. Use these constants everywhere; never hard-code the strings.
PROMPT_VERSIONS = "prompt_versions"
TEST_CASES = "test_cases"
EVAL_RUNS = "eval_runs"
EVAL_RESULTS = "eval_results"
COMPARISONS = "comparisons"
