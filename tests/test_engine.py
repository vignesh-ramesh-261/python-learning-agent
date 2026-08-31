"""Tests for the analysis engine."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import analyze, explain_runtime_error  # noqa: E402
from engine.constructs import collect  # noqa: E402
from engine.errors import explain_syntax_error  # noqa: E402
from engine.review import review  # noqa: E402


def keys(result):
    return {c["key"] for c in result}


def test_constructs_detection():
    code = '''
import json

@decorator
def process(items, *args, limit=10, **kwargs):
    """Docstring."""
    total: int = 0
    with open("x.txt") as f:
        for i, item in enumerate(items):
            if item is None:
                continue
            total += item
    squares = [n * n for n in range(10)]
    gen = (n for n in squares)
    data = {"a": 1}
    unique = {1, 2}
    point = (3, 4)
    first = point[0]
    text = f"total={total}"
    return lambda x: x + total

class Dog(Animal):
    def __init__(self, name):
        self.name = name
'''
    found = keys(collect(__import__("ast").parse(code)))
    expected = {
        "imports", "decorators", "function_definition", "default_arguments",
        "var_args", "docstrings", "type_hints", "context_manager", "for_loop",
        "enumerate", "range_call", "break_continue", "comprehensions",
        "generator_expressions", "dict_literal", "set_literal", "tuple_literal",
        "fstring", "lambda", "classes", "inheritance", "dunder_methods",
        "conditional", "identity_operator", "augmented_assignment",
        "annotated_assignment", "assignment", "return_statement", "subscripting",
    }
    missing = expected - found
    assert not missing, f"missing constructs: {missing}"


def test_analyze_happy_path():
    result = analyze("def f():\n    return 42\n")
    assert result["ok"] is True
    assert result["stats"]["functions"] == 1
    assert result["summary"]
    assert any(step["line"] == 1 for step in result["walkthrough"])


def test_analyze_syntax_error_is_friendly():
    result = analyze("def f()\n    return 42\n")
    assert result["ok"] is False
    err = result["error"]
    assert err["exception"] == "SyntaxError"
    assert err["line"] == 1
    assert err["what"] and err["common_causes"] and err["fixes"]



def test_mutable_default_finding():
    code = "def add(x, items=[]):\n    items.append(x)\n    return items\n"
    ids = {f["id"] for f in review(__import__("ast").parse(code))}
    assert "mutable_default" in ids


def test_review_bundle_of_smells():
    code = '''
import os
import json
import math  # deliberately unused

def process(data):
    sum = 0
    total = ""
    for i in range(len(data)):
        total += str(data[i])
    try:
        value = json.loads(data)
    except:
        pass
    if value == None:
        return
    if value == True:
        return os
    f = open("out.txt")
    return f

class Bag:
    items = []
'''
    findings = {f["id"]: f for f in review(__import__("ast").parse(code))}
    for expected in [
        "bare_except", "swallow_exception", "eq_none", "eq_bool", "range_len",
        "string_concat_loop", "open_without_with", "mutable_class_attr",
        "unused_import", "shadow_builtin", "missing_docstring",
    ]:
        assert expected in findings, f"expected finding {expected}"


def test_late_binding_closure():
    code = """
funcs = []
for i in range(3):
    funcs.append(lambda: i)
"""
    ids = {f["id"] for f in review(__import__("ast").parse(code))}
    assert "late_binding" in ids


def test_no_false_positive_on_clean_code():
    code = '''
def add(a, b):
    """Add two numbers."""
    return a + b
'''
    findings = [f for f in review(__import__("ast").parse(code)) if f["severity"] in ("bug", "warning", "security")]
    assert not findings


def test_runtime_error_explanation():
    stderr = 'Traceback (most recent call last):\n  File "main.py", line 3, in <module>\n    print(mame)\nNameError: name \'mame\' is not defined'
    err = explain_runtime_error(stderr)
    assert err["exception"] == "NameError"
    assert err["line"] == 3
    assert any("Typo" in c or "typo" in c or "spelling" in c.lower() for c in err["common_causes"])


def test_syntax_error_explanation_structure():
    import ast as _ast
    try:
        _ast.parse("if x == 1\n    pass")
    except SyntaxError as exc:
        err = explain_syntax_error(exc)
        assert err["exception"] == "SyntaxError"
        assert "offending_line" in err


def test_walkthrough_describes_function():
    result = analyze("def greet(name):\n    '''Says hi.'''\n    return name\n")
    texts = [step["text"] for step in result["walkthrough"]]
    assert any("greet" in t for t in texts)
    assert any("Says hi" in t for t in texts)


def test_summary_mentions_findings():
    code = "def f(items=[]):\n    return items\n"
    result = analyze(code)
    assert "improvement" in result["summary"] or "flagged" in result["summary"]


# ------------------------------------------------- /api/ai/lesson endpoint
def _client():
    import app as app_mod
    app_mod.app.config["TESTING"] = True
    return app_mod.app.test_client()


def test_lesson_endpoint_rejects_unknown_lesson():
    r = _client().post("/api/ai/lesson", json={
        "lesson_id": "does-not-exist", "api_key": "k",
        "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400
    assert "Unknown lesson" in r.get_json()["error"]


def test_lesson_endpoint_requires_a_question():
    from content.lessons import LESSONS
    r = _client().post("/api/ai/lesson", json={
        "lesson_id": LESSONS[0]["id"], "api_key": "k", "messages": []})
    assert r.status_code == 400


def test_lesson_endpoint_requires_a_key(monkeypatch):
    from content.lessons import LESSONS
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = _client().post("/api/ai/lesson", json={
        "lesson_id": LESSONS[0]["id"], "api_key": "",
        "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400
    assert "No API key" in r.get_json()["error"]


def test_lesson_endpoint_ignores_client_supplied_lesson_text(monkeypatch):
    """Grounding comes from the server's lesson bank, not the request body."""
    import ai.llm as llm_mod
    from content.lessons import LESSONS
    captured = {}

    def fake_call_chat(provider, api_key, model, messages, base_url, system):
        captured["system"] = system
        return "ok"

    monkeypatch.setattr(llm_mod, "call_chat", fake_call_chat)
    lesson = LESSONS[0]
    r = _client().post("/api/ai/lesson", json={
        "lesson_id": lesson["id"], "api_key": "k",
        "lesson": {"title": "FORGED"}, "code": "FORGED",
        "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    assert "FORGED" not in captured["system"]
    assert lesson["title"] in captured["system"]


# ------------------------------------------------------- quiz ↔ lesson links
def test_every_quiz_question_links_to_a_real_lesson():
    from content.quiz import QUIZ
    from content.lessons import LESSONS
    lesson_ids = {l["id"] for l in LESSONS}
    for q in QUIZ:
        assert q.get("lesson"), f"{q['id']} has no lesson link"
        assert q["lesson"] in lesson_ids, f"{q['id']} -> unknown lesson {q['lesson']!r}"


def test_every_lesson_has_at_least_one_quiz_question():
    """A lesson with no practice question is a hole in the learning loop."""
    from content.quiz import QUIZ
    from content.lessons import LESSONS
    covered = {q["lesson"] for q in QUIZ}
    missing = sorted({l["id"] for l in LESSONS} - covered)
    assert not missing, f"lessons with no quiz question: {missing}"


def test_quiz_questions_are_structurally_valid():
    from content.quiz import QUIZ
    seen = set()
    for q in QUIZ:
        assert q["id"] not in seen, f"duplicate quiz id {q['id']}"
        seen.add(q["id"])
        for field in ("topic", "difficulty", "question", "explanation"):
            assert str(q.get(field, "")).strip(), f"{q['id']} missing {field}"
        assert len(q["options"]) >= 3, f"{q['id']} needs >=3 options"
        assert len(set(q["options"])) == len(q["options"]), f"{q['id']} has duplicate options"
        assert isinstance(q["answer"], int)
        assert 0 <= q["answer"] < len(q["options"]), f"{q['id']} answer out of range"
        assert q["difficulty"] in {"easy", "medium", "hard"}, q["id"]


def test_quiz_endpoint_exposes_the_lesson_field():
    """The UI's 'Review the lesson' button depends on this reaching the client."""
    payload = _client().get("/api/quiz").get_json()
    assert payload and all(q.get("lesson") for q in payload)


# ------------------------------------------------- architecture & large files
BIG_SAMPLE = '''
"""Order service."""
import json
from dataclasses import dataclass


@dataclass
class Order:
    """A customer order."""
    total: float


class OrderError(Exception):
    pass


def load(path):
    """Read orders."""
    return json.load(open(path))


def summarise(orders):
    return sum(o.total for o in orders)


def stream(orders):
    for o in orders:
        yield o.total


def unused_helper():
    return 1


def main():
    data = load("x.json")
    return summarise(data)


if __name__ == "__main__":
    main()
'''


def test_architecture_finds_components_and_roles():
    from engine import analyze
    arch = analyze(BIG_SAMPLE)["architecture"]
    names = {c["name"] for c in arch["components"]}
    assert {"Order", "OrderError"} <= names
    order = next(c for c in arch["components"] if c["name"] == "Order")
    assert "dataclass" in order["why"]
    err = next(c for c in arch["components"] if c["name"] == "OrderError")
    assert "exception" in err["why"].lower()


def test_architecture_detects_entry_point_and_callers():
    from engine import analyze
    arch = analyze(BIG_SAMPLE)["architecture"]
    assert "main" in arch["entry_points"]
    fns = {f["name"]: f for f in arch["functions"]}
    assert fns["main"]["entry"] is True
    # main() calls load() and summarise(), so they must list main as a caller.
    assert "main" in fns["load"]["callers"]
    assert "main" in fns["summarise"]["callers"]


def test_architecture_flags_generators_and_dead_code():
    from engine import analyze
    arch = analyze(BIG_SAMPLE)["architecture"]
    fns = {f["name"]: f for f in arch["functions"]}
    assert "generator" in fns["stream"]["role"]
    assert "unused_helper" in arch["orphans"]
    assert "main" not in arch["orphans"]        # entry points are not orphans
    assert arch["dependencies"] == ["dataclasses", "json"]


def test_findings_are_grouped_by_rule():
    from engine import analyze
    code = "\n".join(f"def f{i}(a=[]):\n    return a\n" for i in range(12))
    a = analyze(code)
    assert len(a["findings"]) >= 12
    groups = a["finding_groups"]
    mutable = [g for g in groups if g["id"] == "mutable_default"]
    assert len(mutable) == 1, "the same rule must collapse into one group"
    assert mutable[0]["count"] >= 12
    assert len(mutable[0]["lines"]) == mutable[0]["count"]
    assert mutable[0]["lines"] == sorted(mutable[0]["lines"])


def test_large_file_is_flagged():
    from engine import analyze, LARGE_FILE_STEPS
    small = analyze("x = 1\n")
    assert small["large"] is False
    big = analyze("\n".join(f"x{i} = {i}" for i in range(LARGE_FILE_STEPS + 20)))
    assert big["large"] is True


def test_summary_reports_distinct_issues_not_raw_hits():
    from engine import analyze
    code = "\n".join(f"def f{i}(a=[]):\n    return a\n" for i in range(10))
    summary = analyze(code)["summary"]
    assert "distinct issue" in summary
    assert "location" in summary
