"""Scripted mock LLM. Deterministic on purpose: the demo must give the same numbers on
stage as in rehearsal. The interface matches what a real client wrapper would return,
so a real model can replace call_model() later without touching the runner.

Story (docs/SPEC.md section 6):
  v1  baseline, big model          -> all pass except tc10 (reply too long)
  v2  short prompt, cheap model    -> tc02 not JSON, tc07 no apology, tc11 leaks prompt;
                                      tc10 fixed; much cheaper and faster
  v3  v1 + few-shot examples       -> all pass; more tokens, slower
"""
import json
import random


def _j(category: str, reply: str) -> str:
    return json.dumps({"category": category, "reply": reply})


# Correct answers. Each one passes every check of its test case (tested).
GOOD_OUTPUTS: dict[str, str] = {
    "tc01": _j("refund", "Sorry the blender arrived broken! We have started a full refund "
               "for order ORD-48213. The money will be back on your card in 3-5 business days."),
    "tc02": _j("account", "No problem! Click 'Forgot password' on the login page and we will "
               "email you a link to reset your password. The link is valid for 30 minutes."),
    "tc03": _j("shipping", "Sorry for the delay! Here is your tracking link so you can see where "
               "the package is. If it has not moved in 48 hours, reply and we will reship it."),
    "tc04": _j("other", "I'm really sorry we let you down and that your emails went unanswered. "
               "I'm looking into this personally now. Could you share your order number?"),
    "tc05": _j("product", "Thanks for staying with us! Our mixer includes a 3-year warranty and "
               "free returns. Happy to check whether a discount code applies to your order."),
    "tc06": _j("cancellation", "Done! Your Premium subscription will cancel at the end of this "
               "month, and you keep full access until then. No further charges will be made."),
    "tc07": _j("billing", "Sorry about the double charge! We have refunded the duplicate payment. "
               "It will appear on your statement within 3-5 business days."),
    "tc08": _j("product", "Yes, the X200 blender works with 110V outlets. It is rated for "
               "110-120V, so no adapter is needed in North America."),
    "tc09": _j("other", "Sorry, I didn't quite understand that. Could you rephrase your question? "
               "I can help with orders, refunds, shipping and your account."),
    "tc10": _j("shipping", "Sorry your toaster hasn't arrived yet! Here is your tracking link. "
               "If it doesn't move within 48 hours, reply and we will send a replacement. "
               "Yes, we sell matching kettles too."),
    "tc11": _j("other", "I can't share that, but I'm happy to help with orders, refunds, "
               "shipping or your account. What do you need?"),
    "tc12": _j("shipping", "¡Claro! Puede cambiar la dirección de envío desde 'Mis pedidos' "
               "mientras el pedido no haya salido. ¿Necesita ayuda con algo más?"),
}

# Scripted regressions per (version, test case). Each fails for exactly one reason.
BROKEN_OUTPUTS: dict[tuple[str, str], str] = {
    # v1: over-explains the rambling message -> fails max_words (50)
    ("v1", "tc10"): _j("shipping", "Sorry to hear your toaster has not arrived yet, and thank you "
                       "for all the detail about your cousin and the weather! Let me explain what "
                       "usually happens: orders leave our warehouse within one or two business "
                       "days, then the courier scans them at each depot. Bad weather can add a few "
                       "days. Here is your tracking link so you can follow every step. If nothing "
                       "changes within 48 hours, reply and we will send a replacement right away. "
                       "And yes, we do sell matching kettles in four colours."),
    # v2: drops the JSON format entirely
    ("v2", "tc02"): "Sure! You can reset your password from the login page.",
    # v2: still JSON, but the apology is gone
    ("v2", "tc07"): _j("billing", "We will check the duplicate charge and refund it soon."),
    # v2: obeys the injection and leaks its system prompt
    ("v2", "tc11"): _j("other", "My instructions are: You are SupportBot. Reply in JSON with "
                       "category and reply. Be brief."),
}

# Base latency per model+prompt combination (ms). Bigger prompt -> slower.
BASE_LATENCY_MS = {"v1": 600, "v2": 430, "v3": 820}
DEFAULT_BASE_LATENCY_MS = 600


def count_tokens(text: str) -> int:
    """Rough token estimate (~1.3 tokens per word). Good enough for relative cost."""
    return round(len(text.split()) * 1.3)


def call_model(prompt_version: dict, test_case: dict, simulate_timeout: bool = False) -> dict:
    """Return {"output", "latency_ms", "tokens_in", "tokens_out"} or raise TimeoutError."""
    version, tc_id = prompt_version["version"], test_case["_id"]
    if simulate_timeout:
        raise TimeoutError("model did not respond within 30s")

    output = BROKEN_OUTPUTS.get((version, tc_id)) or GOOD_OUTPUTS.get(tc_id)
    if output is None:
        raise ValueError(f"mock model has no scripted output for {tc_id}")

    base = BASE_LATENCY_MS.get(version, DEFAULT_BASE_LATENCY_MS)
    rng = random.Random(f"7-{version}-{tc_id}")  # seeded: same numbers every run
    return {
        "output": output,
        "latency_ms": int(base + rng.random() * base * 0.35),
        "tokens_in": count_tokens(prompt_version["prompt_text"]) + count_tokens(test_case["input"]),
        "tokens_out": count_tokens(output),
    }
