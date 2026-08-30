"""Optional AI deep-dive: calls an LLM with your own API key.

Providers: openai (any OpenAI-compatible /chat/completions endpoint) or
anthropic. Keys are supplied per-request from the browser (or via env vars)
and are never persisted server-side.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 60

DEFAULT_OPENAI_BASE = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_BASE = "https://api.anthropic.com"

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-latest"

# When someone points the OpenAI-compatible provider at a third-party gateway,
# "gpt-4o-mini" does not exist there. Guess a sane default per known host so the
# very common "I pasted a base URL but left model blank" case still works.
BASE_URL_DEFAULT_MODELS = {
    "generativelanguage.googleapis.com": "gemini-2.0-flash",
    "openrouter.ai": "openai/gpt-4o-mini",
    "api.groq.com": "llama-3.3-70b-versatile",
    "api.mistral.ai": "mistral-small-latest",
    "api.deepseek.com": "deepseek-chat",
    "api.together.xyz": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "localhost": "llama3",
    "127.0.0.1": "llama3",
}


class AIError(Exception):
    pass


def _endpoint(base_url: str | None, default_base: str, path: str) -> str:
    """Build a request URL that tolerates how people actually paste base URLs.

    Handles a trailing slash, a base that already includes the endpoint path,
    and a base that is missing its scheme.
    """
    base = (base_url or "").strip() or default_base
    base = base.rstrip("/")
    if not base:
        base = default_base
    if "://" not in base:
        # Local endpoints (Ollama, LM Studio, vLLM) are plain HTTP.
        local = base.startswith(("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))
        base = ("http://" if local else "https://") + base
    path = "/" + path.strip("/")
    # User pasted the full endpoint (".../v1/chat/completions") — don't double it.
    if base.lower().endswith(path.lower()):
        return base
    return base + path


def _default_model_for(base_url: str | None, fallback: str) -> str:
    base = (base_url or "").strip()
    if not base:
        return fallback
    if "://" not in base:
        base = "https://" + base
    host = (urllib.parse.urlparse(base).hostname or "").lower()
    for known, model in BASE_URL_DEFAULT_MODELS.items():
        if host == known or host.endswith("." + known):
            return model
    return fallback


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
            try:
                err = json.loads(body)
            except json.JSONDecodeError:
                detail = body.strip()[:300]
            else:
                if isinstance(err, dict) and isinstance(err.get("error"), dict):
                    detail = (err["error"].get("message")
                              or err["error"].get("status") or "")
                elif isinstance(err, list) and err and isinstance(err[0], dict):
                    # Gemini sometimes returns a list-wrapped error object.
                    inner = err[0].get("error") or {}
                    detail = inner.get("message") if isinstance(inner, dict) else ""
                else:
                    detail = str((isinstance(err, dict) and err.get("error")) or body)[:300]
        except Exception:  # noqa: BLE001
            pass
        detail = (detail or "").strip()
        hint = ""
        if e.code in (401, 403):
            hint = " — check that the API key is correct and enabled for this endpoint."
        elif e.code == 404:
            hint = " — check the model name and the Base URL."
        elif e.code == 429:
            hint = " — rate limit or quota exceeded; wait a moment and retry."
        raise AIError(f"API error {e.code}: {detail or e.reason}{hint}") from e
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, TimeoutError) or isinstance(reason, socket.timeout):
            raise AIError(f"The API request timed out after {TIMEOUT}s.") from e
        raise AIError(
            f"Could not reach the API at {url}: {reason}. "
            "Check the Base URL, your network, and any proxy/firewall."
        ) from e
    except (TimeoutError, socket.timeout) as e:
        raise AIError(f"The API request timed out after {TIMEOUT}s.") from e
    except json.JSONDecodeError as e:
        raise AIError("The API returned a response that was not valid JSON.") from e


def call_llm(provider: str, api_key: str, model: str | None, user_prompt: str,
             base_url: str | None = None) -> str:
    provider = (provider or "").lower().strip()
    if provider == "openai":
        return _call_openai(api_key, model, user_prompt, base_url)
    if provider == "anthropic":
        return _call_anthropic(api_key, model, user_prompt, base_url)
    raise AIError("Unknown provider — choose 'openai' or 'anthropic'.")


def _call_openai(api_key: str, model: str | None, user_prompt: str,
                 base_url: str | None = None) -> str:
    if not api_key:
        raise AIError("No API key provided.")
    model = (model or "").strip() or _default_model_for(base_url, DEFAULT_OPENAI_MODEL)
    data = _http_json(
        _endpoint(base_url, DEFAULT_OPENAI_BASE, "/chat/completions"),
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1800,
            "temperature": 0.3,
        },
    )
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        # Some gateways return HTTP 200 with an error object in the body.
        raise AIError(f"API error: {data['error'].get('message') or data['error']}")

    choices = (data or {}).get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIError("The API returned no choices — the request may have been filtered.")

    choice = choices[0] or {}
    message = choice.get("message") or {}
    content = message.get("content")

    # Some OpenAI-compatible servers return content as a list of parts.
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and part.get("type") in (None, "text", "output_text")
        )

    if isinstance(content, str) and content.strip():
        return content

    # Empty content: explain *why* instead of returning null to the browser.
    finish = choice.get("finish_reason") or choice.get("native_finish_reason") or ""
    if finish == "length":
        raise AIError(
            "The model hit the token limit before writing an answer. This happens with "
            "Gemini 2.5 'thinking' models — try a non-thinking model such as "
            "gemini-2.0-flash, or shorten the code."
        )
    if finish in ("content_filter", "safety"):
        raise AIError("The provider's safety filter blocked this response.")
    if message.get("refusal"):
        raise AIError(f"The model refused: {message['refusal']}")
    raise AIError(
        f"The model returned an empty response{f' (finish_reason={finish})' if finish else ''}. "
        "Try a different model."
    )


def _call_anthropic(api_key: str, model: str | None, user_prompt: str,
                    base_url: str | None = None) -> str:
    if not api_key:
        raise AIError("No Anthropic API key provided.")
    data = _http_json(
        _endpoint(base_url, DEFAULT_ANTHROPIC_BASE, "/v1/messages"),
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        {
            "model": (model or "").strip() or DEFAULT_ANTHROPIC_MODEL,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 1800,
        },
    )
    if isinstance(data, dict) and data.get("type") == "error":
        err = data.get("error") or {}
        raise AIError(f"API error: {err.get('message') or err}")
    blocks = (data or {}).get("content")
    if not isinstance(blocks, list):
        raise AIError("Unexpected response shape from Anthropic.")
    text = "".join(
        b.get("text", "") for b in blocks
        if isinstance(b, dict) and b.get("type") == "text"
    )
    if not text.strip():
        stop = (data or {}).get("stop_reason") or ""
        if stop == "max_tokens":
            raise AIError("The model hit the token limit before writing an answer.")
        raise AIError(
            f"The model returned an empty response{f' (stop_reason={stop})' if stop else ''}."
        )
    return text


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
