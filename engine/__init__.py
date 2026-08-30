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
from .explain import outline, stats, summarize

MAX_CODE_LEN = 40_000


def analyze(code: str) -> dict:
    code = code[:MAX_CODE_LEN]
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        return {
            "ok": False,
            "error": errors_mod.explain_syntax_error(exc),
        }

    analysis = {
        "ok": True,
        "code": code,
        "constructs": collect(tree),
        "walkthrough": outline(tree, code),
        "findings": review_mod.review(tree),
        "stats": stats(tree, code),
    }
    analysis["summary"] = summarize(analysis)
    return analysis


def explain_runtime_error(stderr: str) -> dict | None:
    return errors_mod.explain_exception_text(stderr)


__all__ = ["analyze", "explain_runtime_error"]
