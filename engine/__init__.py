"""Python Learning Agent — analysis engine.

analyze(code) is the one-call API used by the web app:
    compile -> friendly syntax error OR
    { summary, walkthrough, constructs, findings, stats }
"""

from __future__ import annotations

import ast

from . import errors as errors_mod
from . import review as review_mod
from .constructs import collect
from .explain import architecture, group_findings, outline, stats, summarize

MAX_CODE_LEN = 40_000

# Above this many statements the flat walkthrough stops being readable; the UI
# leads with the architecture map instead.
LARGE_FILE_STEPS = 120


def analyze(code: str) -> dict:
    code = code[:MAX_CODE_LEN]
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        return {
            "ok": False,
            "error": errors_mod.explain_syntax_error(exc),
        }

    findings = review_mod.review(tree)
    walkthrough = outline(tree, code)
    analysis = {
        "ok": True,
        "code": code,
        "constructs": collect(tree),
        "walkthrough": walkthrough,
        "findings": findings,
        "finding_groups": group_findings(findings),
        "architecture": architecture(tree, code),
        "stats": stats(tree, code),
    }
    analysis["large"] = len(walkthrough) > LARGE_FILE_STEPS
    analysis["summary"] = summarize(analysis)
    return analysis


def explain_runtime_error(stderr: str) -> dict | None:
    return errors_mod.explain_exception_text(stderr)


__all__ = ["analyze", "explain_runtime_error"]
