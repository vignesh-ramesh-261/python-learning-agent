"""Regression tests for the AI deep-dive (ai/llm.py).

These never touch the network — _http_json is monkeypatched.
"""

from __future__ import annotations

import pytest

from ai import llm

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


def _capture(monkeypatch, response):
    """Patch _http_json, recording the URL/headers/payload it was called with."""
    seen = {}

    def fake(url, headers, payload):
        seen.update(url=url, headers=headers, payload=payload)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(llm, "_http_json", fake)
    return seen


OK = {"choices": [{"finish_reason": "stop",
                   "message": {"role": "assistant", "content": "Hello"}}]}


# --------------------------------------------------------------- endpoints
@pytest.mark.parametrize("base,expected", [
    (None, "https://api.openai.com/v1/chat/completions"),
    ("", "https://api.openai.com/v1/chat/completions"),
    (GEMINI_BASE, GEMINI_BASE + "/chat/completions"),
    # trailing slash must not create a double slash
    (GEMINI_BASE + "/", GEMINI_BASE + "/chat/completions"),
    ("   " + GEMINI_BASE + "   ", GEMINI_BASE + "/chat/completions"),
    # user pasted the whole endpoint: don't duplicate the path
    (GEMINI_BASE + "/chat/completions", GEMINI_BASE + "/chat/completions"),
    # missing scheme
    ("generativelanguage.googleapis.com/v1beta/openai",
     GEMINI_BASE + "/chat/completions"),
    # local endpoints default to http, not https
    ("localhost:11434/v1", "http://localhost:11434/v1/chat/completions"),
])
def test_openai_endpoint_normalisation(monkeypatch, base, expected):
    seen = _capture(monkeypatch, OK)
    llm.call_llm("openai", "key", "some-model", "prompt", base)
    assert seen["url"] == expected


def test_anthropic_endpoint_and_headers(monkeypatch):
    seen = _capture(monkeypatch, {"content": [{"type": "text", "text": "hi"}]})
    assert llm.call_llm("anthropic", "key", None, "prompt") == "hi"
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["headers"]["x-api-key"] == "key"
    assert seen["payload"]["model"] == llm.DEFAULT_ANTHROPIC_MODEL


# ------------------------------------------------------------------ models
def test_blank_model_against_gemini_base_does_not_send_gpt(monkeypatch):
    """The original bug: model defaulted to gpt-4o-mini -> 404 on Gemini."""
    seen = _capture(monkeypatch, OK)
    llm.call_llm("openai", "key", None, "prompt", GEMINI_BASE)
    assert seen["payload"]["model"] == "gemini-2.0-flash"


def test_blank_model_against_openai_keeps_default(monkeypatch):
    seen = _capture(monkeypatch, OK)
    llm.call_llm("openai", "key", "", "prompt")
    assert seen["payload"]["model"] == llm.DEFAULT_OPENAI_MODEL


def test_model_is_stripped(monkeypatch):
    seen = _capture(monkeypatch, OK)
    llm.call_llm("openai", "key", "  gemini-2.0-flash  ", "prompt", GEMINI_BASE)
    assert seen["payload"]["model"] == "gemini-2.0-flash"


# --------------------------------------------------------------- responses
def test_thinking_model_empty_content_raises_actionable_error(monkeypatch):
    """Gemini 2.5 burns the budget on reasoning and returns content: None."""
    _capture(monkeypatch, {"choices": [
        {"finish_reason": "length", "message": {"content": None}}]})
    with pytest.raises(llm.AIError, match="token limit"):
        llm.call_llm("openai", "key", "gemini-2.5-flash", "prompt", GEMINI_BASE)


def test_never_returns_none(monkeypatch):
    _capture(monkeypatch, {"choices": [{"message": {"content": None}}]})
    with pytest.raises(llm.AIError):
        llm.call_llm("openai", "key", "m", "prompt", GEMINI_BASE)


def test_list_shaped_content_is_joined(monkeypatch):
    _capture(monkeypatch, {"choices": [{"message": {"content": [
        {"type": "text", "text": "part1 "}, {"type": "text", "text": "part2"}]}}]})
    assert llm.call_llm("openai", "key", "m", "p", GEMINI_BASE) == "part1 part2"


def test_error_object_in_200_body(monkeypatch):
    _capture(monkeypatch, {"error": {"message": "API key not valid"}})
    with pytest.raises(llm.AIError, match="API key not valid"):
        llm.call_llm("openai", "key", "m", "p", GEMINI_BASE)


def test_no_choices(monkeypatch):
    _capture(monkeypatch, {"choices": []})
    with pytest.raises(llm.AIError, match="no choices"):
        llm.call_llm("openai", "key", "m", "p", GEMINI_BASE)


def test_content_filter(monkeypatch):
    _capture(monkeypatch, {"choices": [
        {"finish_reason": "content_filter", "message": {"content": ""}}]})
    with pytest.raises(llm.AIError, match="safety filter"):
        llm.call_llm("openai", "key", "m", "p", GEMINI_BASE)


# ----------------------------------------------------------------- guards
def test_missing_key_and_unknown_provider():
    with pytest.raises(llm.AIError, match="No API key"):
        llm.call_llm("openai", "", "m", "p")
    with pytest.raises(llm.AIError, match="Unknown provider"):
        llm.call_llm("gemini", "key", "m", "p")


def test_build_user_prompt_includes_code_and_constructs():
    prompt = llm.build_user_prompt("print(1)", "A script.", ["f-string"])
    assert "print(1)" in prompt
    assert "A script." in prompt
    assert "f-string" in prompt
