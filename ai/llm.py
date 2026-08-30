"""Optional AI deep-dive: calls an LLM with your own API key.

Providers: openai (any OpenAI-compatible /chat/completions endpoint) or
anthropic. Keys are supplied per-request from the browser (or via env vars)
and are never persisted server-side.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

TIMEOUT = 60


class AIError(Exception):
    pass


SYSTEM_PROMPT = (
    "You are a patient senior Python tutor. The user is a developer who relies on AI to "
    "write scripts and now wants to truly UNDERSTAND Python to review code and pass "
    "interviews. Explain clearly and concretely. Structure the answer with these headings: "
    "1) What this code does, 2) Why the syntax is written this way, 3) Line-by-line notes "
    "(only non-obvious lines), 4) What could be improved (with a short improved snippet), "
    "5) Interview concepts hidden in this code. Be concise; use short code blocks."
)


def _http_json(url: str, headers: dict, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            body = e.read().decode("utf-8", "replace")
            err = json.loads(body)
            detail = err.get("error", {}).get("message") if isinstance(err.get("error"), dict) \
                else str(err.get("error") or body)[:300]
        except Exception:  # noqa: BLE001
            pass
        raise AIError(f"API error {e.code}: {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise AIError(f"Could not reach the API: {e.reason}") from e
    except TimeoutError as e:
        raise AIError("The API request timed out.") from e


def call_llm(provider: str, api_key: str, model: str | None, user_prompt: str) -> str:
    provider = (provider or "").lower().strip()
    if provider == "openai":
        return _call_openai(api_key, model, user_prompt)
    if provider == "anthropic":
        return _call_anthropic(api_key, model, user_prompt)
    raise AIError("Unknown provider — choose 'openai' or 'anthropic'.")


def _call_openai(api_key: str, model: str | None, user_prompt: str) -> str:
    if not api_key:
        raise AIError("No OpenAI API key provided.")
    data = _http_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1800,
            "temperature": 0.3,
        },
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise AIError("Unexpected response shape from OpenAI.") from e


def _call_anthropic(api_key: str, model: str | None, user_prompt: str) -> str:
    if not api_key:
        raise AIError("No Anthropic API key provided.")
    data = _http_json(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        {
            "model": model or "claude-3-5-haiku-latest",
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 1800,
        },
    )
    try:
        return "".join(block.get("text", "") for block in data["content"]
                       if block.get("type") == "text")
    except (KeyError, TypeError) as e:
        raise AIError("Unexpected response shape from Anthropic.") from e


def build_user_prompt(code: str, static_summary: str, constructs: list[str]) -> str:
    parts = [
        "Explain this Python code to a learner:",
        "",
        "```python",
        code[:8000],
        "```",
    ]
    if static_summary:
        parts += ["", "A static analyzer already determined:", static_summary]
    if constructs:
        parts += ["Constructs detected: " + ", ".join(constructs)]
    return "\n".join(parts)


def env_key_for(provider: str) -> str:
    return os.environ.get(f"{provider.upper()}_API_KEY", "").strip()
