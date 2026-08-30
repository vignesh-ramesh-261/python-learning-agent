"""Tests for the sandboxed runner."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.runner import run_code  # noqa: E402


def test_run_print():
    result = run_code('print("hello")')
    assert result["stdout"].strip() == "hello"
    assert result["exit_code"] == 0
    assert result["timed_out"] is False


def test_run_error_captures_stderr():
    result = run_code("1 / 0")
    assert "ZeroDivisionError" in result["stderr"]
    assert result["exit_code"] != 0


def test_run_timeout():
    result = run_code("while True:\n    pass", timeout=2)
    assert result["timed_out"] is True
    assert result["duration"] < 10
