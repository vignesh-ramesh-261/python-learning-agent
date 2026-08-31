"""Step-by-step execution tracing for the visualizer.

Runs the user's code in the same isolated-subprocess sandbox as
:mod:`engine.runner` (``python -I``, rlimits, disposable cwd, no stdin) with
``engine/_trace_child.py`` as the entry point, and returns a list of steps the
UI can scrub through.

The visualizer is for *small* programs — a 15-line aliasing demo, a closure, a
recursive call. Caps are therefore tight and explicit: exceeding one is
reported to the user rather than silently truncating the story.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from .runner import _limits

DEFAULT_TIMEOUT = 5.0
MAX_CODE_LEN = 20_000

# Defaults for the child's caps. Env-overridable at the process level so these
# can be tuned against real usage without editing code.
MAX_STEPS = int(os.environ.get("PLA_TRACE_MAX_STEPS", "150"))
# Must stay comfortably under runner._limits' RLIMIT_FSIZE (1 MiB), or the child
# is killed mid-write and leaves truncated JSON behind.
MAX_PAYLOAD = int(os.environ.get("PLA_TRACE_MAX_PAYLOAD", str(600 * 1024)))

_CHILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_trace_child.py")

_STOP_NOTES = {
    "steps": (
        "Stopped after {n} steps — the visualizer is built for short programs. "
        "Everything up to this point is accurate; shrink the code (or the loop "
        "range) to see it run to completion."
    ),
    "payload": (
        "Stopped after {n} steps because the recorded data grew too large. This "
        "usually means the program builds a big list or dict — try smaller data."
    ),
}


def _defines_callables(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               for n in ast.walk(tree))


def _idle_note(code: str, steps: list) -> str | None:
    """Explain an empty-looking recording instead of showing a blank panel."""
    if not steps:
        return "Nothing ran, so there are no steps to show."
    entered_a_call = any(len(step["stack"]) > 1 for step in steps)
    if not entered_a_call and _defines_callables(code):
        return ("Only definitions ran. Defining a function doesn't execute its body — "
                "call the function to watch it work.")
    return None


def trace_code(code: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Execute `code` under the tracer and return a step-by-step recording.

    Always returns a dict with an ``ok`` flag; never raises for user error.
    """
    start = time.monotonic()
    result = {
        "ok": False,
        "steps": [],
        "stdout": "",
        "error": None,
        "note": None,
        "timed_out": False,
        "truncated": False,
        "duration": 0.0,
    }

    code = (code or "")[:MAX_CODE_LEN]
    if not code.strip():
        result["error"] = "There is no code to visualize yet."
        return result

    # Compile in the parent purely to turn syntax errors into a clean message —
    # the sandboxed child still does its own compile before executing.
    try:
        compile(code, "<user>", "exec")
    except SyntaxError as exc:
        result["error"] = f"SyntaxError: {exc.msg} (line {exc.lineno})"
        return result
    except ValueError as exc:
        result["error"] = f"Could not compile that code: {exc}"
        return result

    try:
        with tempfile.TemporaryDirectory(prefix="pla_trace_") as tmp:
            main_py = os.path.join(tmp, "main.py")
            child_py = os.path.join(tmp, "_trace_child.py")
            out_json = os.path.join(tmp, "trace.json")
            with open(main_py, "w", encoding="utf-8") as handle:
                handle.write(code)
            shutil.copyfile(_CHILD, child_py)

            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": tmp,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PLA_TRACE_OUT": out_json,
                "PLA_TRACE_MAX_STEPS": str(MAX_STEPS),
                "PLA_TRACE_MAX_PAYLOAD": str(MAX_PAYLOAD),
            }
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", child_py, main_py],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
                    cwd=tmp,
                    env=env,
                    # NB: must be a callable run in the CHILD after fork —
                    # calling _limits(timeout) here would cap the web server.
                    preexec_fn=lambda: _limits(timeout),
                )
            except subprocess.TimeoutExpired:
                result["timed_out"] = True
                result["error"] = (
                    f"Tracing stopped after {timeout:g}s. Infinite loops are cut off "
                    "automatically, so this usually means the program is doing heavy work."
                )
                return result

            if not os.path.exists(out_json):
                detail = (proc.stderr or "").strip().splitlines()
                result["error"] = detail[-1] if detail else "The tracer produced no output."
                return result

            try:
                with open(out_json, encoding="utf-8") as handle:
                    payload = json.load(handle)
            except json.JSONDecodeError:
                result["error"] = (
                    "The recording was too large to save. Try a smaller program or "
                    "less data."
                )
                return result
    except Exception as exc:  # noqa: BLE001 - surface anything odd rather than 500
        result["error"] = f"tracer error: {exc}"
        return result
    finally:
        result["duration"] = round(time.monotonic() - start, 3)

    steps = payload.get("steps") or []
    result["ok"] = True
    result["steps"] = steps
    result["stdout"] = payload.get("stdout", "")
    result["error"] = payload.get("error")

    stopped = payload.get("stopped")
    if stopped in _STOP_NOTES:
        result["truncated"] = True
        result["note"] = _STOP_NOTES[stopped].format(n=len(steps))

    if not result["error"] and not result["note"]:
        result["note"] = _idle_note(code, steps)
    result["duration"] = round(time.monotonic() - start, 3)
    return result
