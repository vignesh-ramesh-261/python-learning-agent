"""Execution tracer — runs INSIDE the sandboxed child process.

This file is copied into a disposable temp directory and executed with
``python -I`` by :mod:`engine.tracer`. It is deliberately dependency-free and
never imported by the web app, so nothing here runs in the server process.

It records, for each executed line: the call stack (frames + locals) and a
snapshot of every object those locals reach. Two names bound to one list share
a heap id, which is exactly what makes aliasing visible in the UI.

The trace is written to the file named by ``PLA_TRACE_OUT`` rather than stdout,
because the user's own ``print()`` owns stdout.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys

FILENAME = "<user>"

# Caps (overridable via env so the server can tune them without a code change).
MAX_STEPS = int(os.environ.get("PLA_TRACE_MAX_STEPS", "150"))
MAX_PAYLOAD = int(os.environ.get("PLA_TRACE_MAX_PAYLOAD", str(600 * 1024)))
MAX_ITEMS = int(os.environ.get("PLA_TRACE_MAX_ITEMS", "25"))
MAX_HEAP_PER_STEP = int(os.environ.get("PLA_TRACE_MAX_HEAP", "60"))
MAX_DEPTH = 4
MAX_STDOUT = 10_000

# Names injected by exec() that would just be noise in the variable panel.
HIDDEN = {"__name__", "__builtins__", "__doc__", "__package__",
          "__loader__", "__spec__"}


class _StepLimit(Exception):
    """Raised inside the trace callback to halt the program.

    Stopping the *recording* is not enough: an infinite loop would keep running
    until the wall-clock timeout and the user would get nothing back. Raising
    unwinds the interpreter immediately, so `while True:` returns in milliseconds.
    """


def _short(value: object, limit: int = 60) -> str:
    try:
        text = repr(value)
    except Exception:                      # a broken __repr__ must not kill the trace
        return f"<{type(value).__name__} (repr failed)>"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def encode(value: object, heap: dict, depth: int = 0) -> dict:
    """Encode a value as either an inline primitive or a reference into `heap`.

    Immutable scalars are inlined: they have no identity worth showing, and
    CPython interning would make `id()` confusing rather than instructive.
    Everything else becomes {"t": "ref", "id": ...} so that shared objects are
    visibly shared.
    """
    if isinstance(value, (int, float, bool, str, bytes, complex)) or value is None:
        return {"t": "prim", "v": _short(value)}

    oid = str(id(value))
    if oid in heap:
        return {"t": "ref", "id": oid}
    if len(heap) >= MAX_HEAP_PER_STEP:
        return {"t": "prim", "v": f"<{type(value).__name__}: too many objects>"}

    entry: dict = {"t": type(value).__name__, "v": None}
    heap[oid] = entry                       # insert BEFORE recursing (handles cycles)

    if depth >= MAX_DEPTH:
        entry["v"] = _short(value)
        return {"t": "ref", "id": oid}

    try:
        if isinstance(value, (list, tuple, set, frozenset)):
            items = list(value)[:MAX_ITEMS]
            entry["kind"] = "seq"
            entry["v"] = [encode(x, heap, depth + 1) for x in items]
            entry["more"] = max(0, len(value) - len(items))
        elif isinstance(value, dict):
            items = list(value.items())[:MAX_ITEMS]
            entry["kind"] = "map"
            entry["v"] = [[_short(k, 30), encode(v, heap, depth + 1)] for k, v in items]
            entry["more"] = max(0, len(value) - len(items))
        elif isinstance(value, type):
            entry["t"] = "class"
            entry["kind"] = "scalar"
            entry["v"] = value.__name__
        elif callable(value):
            entry["t"] = "function"
            entry["kind"] = "scalar"
            entry["v"] = getattr(value, "__name__", "<callable>")
        elif hasattr(value, "__dict__") and vars(value):
            entry["t"] = f"{type(value).__name__} instance"
            entry["kind"] = "map"
            attrs = list(vars(value).items())[:MAX_ITEMS]
            entry["v"] = [[str(k), encode(v, heap, depth + 1)] for k, v in attrs]
            entry["more"] = 0
        else:
            entry["kind"] = "scalar"
            entry["v"] = _short(value)
    except Exception:
        entry["kind"] = "scalar"
        entry["v"] = f"<{type(value).__name__}>"
    return {"t": "ref", "id": oid}


def _frames(frame, heap: dict) -> list:
    """Walk the stack, innermost last, keeping only user frames."""
    stack, current = [], frame
    while current is not None:
        if current.f_code.co_filename == FILENAME:
            names = {k: v for k, v in current.f_locals.items() if k not in HIDDEN}
            stack.append({
                "func": current.f_code.co_name,
                "locals": [[k, encode(v, heap)] for k, v in names.items()],
            })
        current = current.f_back
    stack.reverse()
    if stack:
        stack[0]["func"] = "<module>" if stack[0]["func"] == "<module>" else stack[0]["func"]
    return stack


def trace(code: str) -> tuple:
    steps: list = []
    budget = {"used": 0}
    state = {"stopped": None}      # "steps" | "payload"

    def callback(frame, event, arg):
        if frame.f_code.co_filename != FILENAME:
            return None            # never descend into stdlib internals
        if state["stopped"]:
            raise _StepLimit()
        if event not in ("line", "return", "exception"):
            return callback

        if len(steps) >= MAX_STEPS:
            state["stopped"] = "steps"
            raise _StepLimit()
        if budget["used"] >= MAX_PAYLOAD:
            state["stopped"] = "payload"
            raise _StepLimit()

        heap: dict = {}            # fresh each step, so mutation over time is visible
        step = {
            "line": frame.f_lineno,
            "event": event,
            "stack": _frames(frame, heap),
            "heap": heap,
        }
        if event == "return":
            step["returned"] = encode(arg, heap)
        elif event == "exception":
            exc_type, exc_value = arg[0], arg[1]
            step["raised"] = f"{exc_type.__name__}: {_short(exc_value, 80)}"

        try:
            budget["used"] += len(json.dumps(step))
        except Exception:
            return callback        # unserialisable step: skip rather than crash
        steps.append(step)
        return callback

    sys.settrace(callback)
    error = None
    try:
        exec(compile(code, FILENAME, "exec"), {"__name__": "__main__"})
    except _StepLimit:
        pass
    except BaseException as exc:  # noqa: BLE001 - user code crashed
        # Keep the steps recorded so far: the run-up to a crash is the most
        # valuable part of the trace, so it must survive the exception.
        error = f"{type(exc).__name__}: {exc}"
    finally:
        sys.settrace(None)
    return steps, state["stopped"], error


def main() -> None:
    with open(sys.argv[1], encoding="utf-8") as handle:
        code = handle.read()

    buffer = io.StringIO()
    error = None
    steps: list = []
    stopped = None
    with contextlib.redirect_stdout(buffer):
        try:
            steps, stopped, error = trace(code)
        except BaseException as exc:        # noqa: BLE001 - tracer itself failed
            error = f"{type(exc).__name__}: {exc}"

    payload = {
        "steps": steps,
        "stdout": buffer.getvalue()[:MAX_STDOUT],
        "error": error,
        "stopped": stopped,
    }
    with open(os.environ["PLA_TRACE_OUT"], "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


if __name__ == "__main__":
    main()
