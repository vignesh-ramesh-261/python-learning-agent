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
