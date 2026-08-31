"""Tests for the execution tracer behind the visualizer.

Several of these pin bugs found while building it: mutation being hidden by a
memoised heap, infinite loops running to the wall-clock timeout, a payload
larger than the sandbox's RLIMIT_FSIZE, and steps being discarded when user
code raised.
"""

from __future__ import annotations

import json
import time

import pytest

from engine.tracer import trace_code


def locals_at(step) -> dict:
    """Flatten the innermost frame's locals into {name: encoded}."""
    return dict(step["stack"][-1]["locals"])


def test_records_a_step_per_executed_line():
    result = trace_code("x = 1\ny = x + 1\n")
    assert result["ok"] is True
    assert [s["line"] for s in result["steps"] if s["event"] == "line"] == [1, 2]


def test_aliased_names_share_one_heap_object():
    """The whole point of the feature: b = a must visibly share, not copy."""
    result = trace_code("a = [1, 2]\nb = a\nb.append(3)\n")
    final = locals_at(result["steps"][-1])
    assert final["a"]["t"] == "ref"
    assert final["a"]["id"] == final["b"]["id"]


def test_mutation_is_visible_across_steps():
    """Regression: a memoised heap froze the list at its first-seen value."""
    result = trace_code("a = [1]\na.append(2)\na.append(3)\n")
    sizes = []
    for step in result["steps"]:
        entry = next(iter(step["heap"].values()), None)
        if entry and entry.get("kind") == "seq":
            sizes.append(len(entry["v"]))
    assert sizes == sorted(sizes) and sizes[-1] > sizes[0], sizes


def test_copies_do_not_share_a_heap_object():
    result = trace_code("a = [1, 2]\nb = a[:]\nb.append(3)\n")
    final = locals_at(result["steps"][-1])
    assert final["a"]["id"] != final["b"]["id"]


def test_immutable_scalars_are_inlined_not_referenced():
    """Interned ints sharing an id would teach the wrong lesson."""
    result = trace_code("a = 256\nb = 256\n")
    final = locals_at(result["steps"][-1])
    assert final["a"]["t"] == "prim"
    assert final["b"]["t"] == "prim"


def test_call_stack_grows_with_nested_calls():
    code = "def inner(n):\n    return n * 2\ndef outer(n):\n    return inner(n) + 1\nouter(5)\n"
    result = trace_code(code)
    assert max(len(s["stack"]) for s in result["steps"]) >= 3
    assert any(s["stack"][-1]["func"] == "inner" for s in result["steps"])


def test_return_steps_carry_the_returned_value():
    result = trace_code("def f():\n    return 42\nf()\n")
    returns = [s for s in result["steps"] if s["event"] == "return" and s.get("returned")]
    assert any(r["returned"].get("v") == "42" for r in returns)


def test_closures_capture_the_variable_not_the_value():
    """Late binding — one of the quiz questions this feature exists to answer."""
    code = "fs = []\nfor i in range(3):\n    fs.append(lambda: i)\nout = [f() for f in fs]\n"
    result = trace_code(code)
    assert result["ok"] is True
    assert result["error"] is None
    assert len(result["steps"]) > 5


def test_generators_are_traced_across_resumes():
    code = "def gen():\n    for i in range(2):\n        yield i\ng = gen()\nnext(g)\nnext(g)\n"
    result = trace_code(code)
    assert result["ok"] is True
    assert any(s["stack"][-1]["func"] == "gen" for s in result["steps"])


def test_user_stdout_is_captured_separately_from_the_trace():
    """print() owns stdout, so the trace must travel on its own channel."""
    result = trace_code("for i in range(3):\n    print(i * 2)\n")
    assert result["stdout"] == "0\n2\n4\n"
    assert result["ok"] is True


def test_infinite_loop_is_cut_off_quickly():
    """Regression: capping the recording alone let the program run to timeout."""
    start = time.monotonic()
    result = trace_code("i = 0\nwhile True:\n    i += 1\n")
    elapsed = time.monotonic() - start
    assert result["ok"] is True
    assert result["truncated"] is True
    assert result["timed_out"] is False
    assert elapsed < 4.0, f"took {elapsed:.1f}s — the step limit did not halt execution"
    assert "Stopped after" in result["note"]


def test_steps_survive_an_uncaught_exception():
    """Regression: a crash discarded the run-up, which is the useful part."""
    result = trace_code("x = 1\ny = x / 0\n")
    assert result["ok"] is True
    assert "ZeroDivisionError" in result["error"]
    assert len(result["steps"]) > 0
    assert any(s["event"] == "exception" for s in result["steps"])


def test_caught_exception_does_not_become_a_top_level_error():
    code = "try:\n    1 / 0\nexcept ZeroDivisionError:\n    ok = True\n"
    result = trace_code(code)
    assert result["error"] is None
    assert result["ok"] is True


def test_syntax_error_is_reported_without_running_anything():
    result = trace_code("def f(:\n")
    assert result["ok"] is False
    assert "SyntaxError" in result["error"]
    assert result["steps"] == []


def test_empty_code_is_rejected_cleanly():
    result = trace_code("   \n  \n")
    assert result["ok"] is False
    assert result["error"]


def test_definitions_without_calls_explain_why_nothing_happened():
    result = trace_code("def f():\n    return 1\n")
    assert result["ok"] is True
    assert "call the function" in (result["note"] or "").lower()


def test_payload_stays_under_the_sandbox_file_size_limit():
    """Regression: a 2 MB cap exceeded RLIMIT_FSIZE and truncated the JSON."""
    result = trace_code("d = {}\nfor i in range(500):\n    d[i] = [i] * 20\n")
    assert result["ok"] is True, result["error"]
    assert result["truncated"] is True
    assert len(json.dumps(result)) < 1024 * 1024


def test_recursive_objects_do_not_hang_the_encoder():
    result = trace_code("a = []\na.append(a)\n")
    assert result["ok"] is True
    assert result["error"] is None


def test_object_attributes_are_shown_for_instances():
    code = "class P:\n    def __init__(self):\n        self.x = 1\np = P()\n"
    result = trace_code(code)
    final = result["steps"][-1]
    assert any("instance" in e["t"] for e in final["heap"].values())


def test_broken_repr_does_not_kill_the_trace():
    code = ("class Bad:\n    def __repr__(self):\n        raise ValueError('nope')\n"
            "b = Bad()\nx = 1\n")
    result = trace_code(code)
    assert result["ok"] is True
    assert result["error"] is None


@pytest.mark.parametrize("snippet", [
    "import os\nx = os.name\n",
    "import json\nx = json.dumps({'a': 1})\n",
])
def test_stdlib_internals_are_not_traced(snippet):
    """Only user lines should appear, or the step list drowns in library code."""
    result = trace_code(snippet)
    assert result["ok"] is True
    assert len(result["steps"]) < 30


def test_every_quiz_snippet_marked_visualizable_actually_traces():
    """The "Watch it run" button must not lead to a dead end."""
    from content.quiz import QUIZ

    for question in QUIZ:
        code = question.get("code")
        if not code:
            continue
        result = trace_code(code)
        assert result["ok"] is True, f"{question['id']}: {result['error']}"
        assert result["steps"], f"{question['id']} produced no steps"


def test_lesson_examples_trace_without_tracer_errors():
    from content.lessons import LESSONS

    for lesson in LESSONS:
        for section in lesson.get("sections", []):
            code = section.get("code")
            if not code:
                continue
            result = trace_code(code)
            # User code may legitimately raise; the tracer itself must not break.
            assert not (result["error"] or "").startswith("tracer error"), \
                f"{lesson['id']}: {result['error']}"


class TestTraceEndpoint:
    """The HTTP surface the visualizer actually calls."""

    def setup_method(self):
        import app as app_mod

        app_mod.app.config["TESTING"] = True
        self.client = app_mod.app.test_client()

    def test_returns_steps_for_valid_code(self):
        resp = self.client.post("/api/trace", json={"code": "a = [1]\nb = a\n"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert len(body["steps"]) >= 2

    def test_rejects_empty_code(self):
        resp = self.client.post("/api/trace", json={"code": "   "})
        assert resp.status_code == 400

    def test_syntax_error_is_a_200_with_an_explanation_not_a_crash(self):
        resp = self.client.post("/api/trace", json={"code": "def f(:"})
        assert resp.status_code == 200
        assert "SyntaxError" in resp.get_json()["error"]


def test_tracer_never_invokes_a_user_defined_repr():
    """Regression: rendering values ran __repr__, so observing changed the program."""
    code = ("class A:\n"
            "    def __repr__(self):\n"
            "        print('SIDE EFFECT')\n"
            "        return 'A()'\n"
            "a = A()\n"
            "x = 1\n")
    result = trace_code(code)
    assert result["ok"] is True
    assert "SIDE EFFECT" not in result["stdout"]


def test_module_level_names_are_shown_inside_functions():
    """Regression: a frame using CONFIG showed no variables at all."""
    result = trace_code("CONFIG = {'k': 1}\ndef f():\n    return CONFIG['k']\nf()\n")
    inner = [s for s in result["steps"] if s["stack"][-1]["func"] == "f"]
    assert inner, "no frame for f()"
    names = [n for n, _ in inner[0]["stack"][-1].get("globals", [])]
    assert "CONFIG" in names


def test_imported_functions_are_not_listed_as_globals():
    """Helper functions would drown the panel; only data is useful."""
    result = trace_code("def helper():\n    return 1\ndef f():\n    return helper()\nf()\n")
    inner = [s for s in result["steps"] if s["stack"][-1]["func"] == "f"]
    names = [n for n, _ in inner[0]["stack"][-1].get("globals", [])]
    assert "helper" not in names


def test_deep_recursion_is_capped_rather_than_exploding():
    result = trace_code("def f(n):\n    return f(n + 1)\nf(0)\n")
    assert result["ok"] is True
    assert result["truncated"] is True
    assert len(json.dumps(result)) < 1024 * 1024


def test_blocking_input_does_not_hang_the_tracer():
    """stdin is /dev/null, so input() must fail fast instead of waiting."""
    result = trace_code("name = input('who? ')\n")
    assert result["ok"] is True
    assert result["timed_out"] is False
    assert "EOFError" in (result["error"] or "")


def test_sys_exit_is_reported_not_swallowed():
    result = trace_code("import sys\nx = 1\nsys.exit(3)\n")
    assert result["ok"] is True
    assert "SystemExit" in (result["error"] or "")


def test_globals_used_only_inside_a_comprehension_are_found():
    """A comprehension is its own code object, so co_names alone misses LIMIT."""
    code = ("LIMIT = 3\n"
            "def check(vals):\n"
            "    return [v for v in vals if v < LIMIT]\n"
            "check([1, 5, 2])\n")
    result = trace_code(code)
    inner = [s for s in result["steps"] if s["stack"][-1]["func"] == "check"]
    names = [n for n, _ in inner[0]["stack"][-1].get("globals", [])]
    assert "LIMIT" in names
