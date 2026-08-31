"""Optional AI deep-dive: calls an LLM with your own API key.

Providers: openai (any OpenAI-compatible /chat/completions endpoint) or
anthropic. Keys are supplied per-request from the browser (or via env vars)
and are never persisted server-side.
"""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 60

# Guardrails on client-supplied chat history.
MAX_HISTORY_TURNS = 20
MAX_MESSAGE_CHARS = 8000
# Prompts the SERVER builds (the deep-dive) embed line-numbered source plus a
# whole-file structural map, so they legitimately exceed the per-message cap
# that guards untrusted client input.
MAX_SERVER_PROMPT_CHARS = 60_000

DEFAULT_OPENAI_BASE = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_BASE = "https://api.anthropic.com"

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-latest"

# When someone points the OpenAI-compatible provider at a third-party gateway,
# "gpt-4o-mini" does not exist there. Guess a sane default per known host so the
# very common "I pasted a base URL but left model blank" case still works.
#
# NOTE: providers retire model IDs on a fast cadence (Google shut down
# gemini-2.0-flash on 2026-06-01), so treat every entry here as a best-effort
# hint that WILL go stale. Any of these can be overridden without a code change
# by exporting e.g. PLA_DEFAULT_MODEL_GENERATIVELANGUAGE_GOOGLEAPIS_COM=<model>,
# or globally with PLA_DEFAULT_MODEL. The model box in the UI always wins.
BASE_URL_DEFAULT_MODELS = {
    "generativelanguage.googleapis.com": "gemini-3.6-flash",
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
    """Best-effort default model when the user leaves the model box blank.

    Precedence: per-host env var > global env var > built-in table > fallback.
    The env vars exist so a provider retiring a model ID never requires a code
    change to stay usable.
    """
    override = os.environ.get("PLA_DEFAULT_MODEL", "").strip()
    base = (base_url or "").strip()
    if not base:
        return override or fallback
    if "://" not in base:
        base = "https://" + base
    host = (urllib.parse.urlparse(base).hostname or "").lower()

    host_var = "PLA_DEFAULT_MODEL_" + re.sub(r"[^A-Z0-9]", "_", host.upper())
    per_host = os.environ.get(host_var, "").strip()
    if per_host:
        return per_host
    if override:
        return override
    for known, model in BASE_URL_DEFAULT_MODELS.items():
        if host == known or host.endswith("." + known):
            return model
    return fallback


SYSTEM_PROMPT = (
    "You are a senior Python engineer walking a developer through a codebase. They can "
    "already see WHAT each line does — a static analyser has produced a statement-by-statement "
    "walkthrough for them. Your job is the part a walkthrough cannot give them: WHY the code "
    "is shaped this way, WHY each piece needs to exist, and HOW the pieces fit together.\n\n"
    "Use these headings:\n"
    "1) Purpose — in 2-3 sentences, what problem does this code solve, and for whom? Infer it "
    "from names, docstrings and dependencies. Say plainly if you are inferring.\n"
    "2) How it fits together — trace the main flow from the entry point through the key "
    "functions. Name them. Explain why the work is split this way rather than one big function.\n"
    "3) Why these design choices — for the most significant decisions (a dataclass here, a "
    "generator there, this data structure, this error handling), explain the trade-off being "
    "made and what the alternative would have cost. This is the most valuable section.\n"
    "4) What to check first in review — the riskiest parts and why they are risky. Prefer "
    "issues of consequence over style nits.\n"
    "5) Concepts worth understanding — the transferable Python ideas this code depends on, "
    "and the interview questions they map to.\n\n"
    "Rules: be concrete and reference real names and line numbers from the code. Short code "
    "blocks only where they clarify. Do NOT restate the line-by-line walkthrough — the user "
    "already has it. If you are given only part of a file, reason about what you can see and "
    "say clearly what you could not."
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
             base_url: str | None = None, system: str | None = None) -> str:
    """Single-turn convenience wrapper around call_chat().

    Used for the deep-dive, whose prompt is built server-side and may legitimately
    be much larger than a browser-supplied chat message.
    """
    return call_chat(provider, api_key, model,
                     [{"role": "user", "content": user_prompt}],
                     base_url, system, max_chars=MAX_SERVER_PROMPT_CHARS)


def call_chat(provider: str, api_key: str, model: str | None,
              messages: list[dict], base_url: str | None = None,
              system: str | None = None,
              max_chars: int = MAX_MESSAGE_CHARS) -> str:
    """Multi-turn chat. `messages` is a list of {role: user|assistant, content}."""
    provider = (provider or "").lower().strip()
    messages = sanitize_messages(messages, max_chars=max_chars)
    if not messages:
        raise AIError("No message to send.")
    system = (system or SYSTEM_PROMPT)
    if provider == "openai":
        return _call_openai(api_key, model, messages, base_url, system)
    if provider == "anthropic":
        return _call_anthropic(api_key, model, messages, base_url, system)
    raise AIError("Unknown provider — choose 'openai' or 'anthropic'.")


def sanitize_messages(messages, max_turns: int = MAX_HISTORY_TURNS,
                      max_chars: int = MAX_MESSAGE_CHARS) -> list[dict]:
    """Validate/normalise a client-supplied history.

    Drops anything malformed, forces roles to user/assistant, trims each
    message and keeps only the most recent `max_turns` so the context (and the
    bill) cannot grow without bound. The final message must be from the user.

    `max_chars` guards untrusted browser input; server-built prompts pass a
    larger budget because they embed the source plus a whole-file map.
    """
    if not isinstance(messages, list):
        return []
    clean: list[dict] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "").strip().lower()
        content = m.get("content")
        if not isinstance(content, str):
            continue
        content = content.strip()
        if role not in ("user", "assistant") or not content:
            continue
        clean.append({"role": role, "content": content[:max_chars]})
    if len(clean) > max_turns:
        clean = clean[-max_turns:]
    # Never open the history with an assistant turn (Anthropic rejects it).
    while clean and clean[0]["role"] == "assistant":
        clean.pop(0)
    return clean


def _call_openai(api_key: str, model: str | None, messages: list[dict],
                 base_url: str | None = None, system: str | None = None) -> str:
    if not api_key:
        raise AIError("No API key provided.")
    model = (model or "").strip() or _default_model_for(base_url, DEFAULT_OPENAI_MODEL)
    data = _http_json(
        _endpoint(base_url, DEFAULT_OPENAI_BASE, "/chat/completions"),
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": model,
            "messages": [{"role": "system", "content": system or SYSTEM_PROMPT},
                         *messages],
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
            "'thinking' models that spend the whole budget on reasoning — try a model "
            "with thinking disabled or a lower reasoning effort, or shorten the code."
        )
    if finish in ("content_filter", "safety"):
        raise AIError("The provider's safety filter blocked this response.")
    if message.get("refusal"):
        raise AIError(f"The model refused: {message['refusal']}")
    raise AIError(
        f"The model returned an empty response{f' (finish_reason={finish})' if finish else ''}. "
        "Try a different model."
    )


def _call_anthropic(api_key: str, model: str | None, messages: list[dict],
                    base_url: str | None = None, system: str | None = None) -> str:
    if not api_key:
        raise AIError("No Anthropic API key provided.")
    data = _http_json(
        _endpoint(base_url, DEFAULT_ANTHROPIC_BASE, "/v1/messages"),
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        {
            "model": (model or "").strip() or DEFAULT_ANTHROPIC_MODEL,
            "system": system or SYSTEM_PROMPT,
            "messages": messages,
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


CHAT_SYSTEM_PROMPT = (
    "You are a patient senior Python tutor having a back-and-forth conversation with a "
    "developer who wants to truly UNDERSTAND Python — to review AI-written code and pass "
    "interviews. The user's current code is given below for context; keep referring to it "
    "when relevant, and quote specific lines or names from it.\n\n"
    "Guidelines:\n"
    "- Answer the question that was actually asked. Do NOT re-explain the whole file "
    "unless asked, and do not repeat the 5-heading breakdown.\n"
    "- Be concise and concrete. Short code blocks over long prose.\n"
    "- If the question is ambiguous, state your assumption in one line and answer anyway.\n"
    "- If the question is not about this code, still answer it as a Python tutor.\n"
    "- If the user is wrong about something, correct them directly and explain why.\n"
    "- Where useful, end with one short follow-up question that deepens their understanding."
)


def build_chat_system_prompt(code: str, static_summary: str = "",
                             constructs: list[str] | None = None,
                             architecture: dict | None = None) -> str:
    """System prompt for the Q&A chat: tutor persona + the user's code as context."""
    parts = [CHAT_SYSTEM_PROMPT]
    if code and code.strip():
        shown, shown_lines, total_lines = _numbered(code, MAX_CODE_IN_PROMPT)
        parts += ["", "The user's current code:", "```python", shown, "```"]
        if shown_lines < total_lines:
            parts += [f"(Only lines 1-{shown_lines} of {total_lines} are shown; the structural "
                      "map below covers the whole file. Say so if asked about the rest.)"]
    brief = build_architecture_brief(architecture or {})
    if brief:
        parts += ["", "Structural map of the whole file:", brief]
    if static_summary:
        parts += ["", f"A static analyzer determined: {static_summary}"]
    if constructs:
        parts += ["Constructs detected: " + ", ".join(constructs)]
    return "\n".join(parts)


LESSON_SYSTEM_PROMPT = (
    "You are a patient senior Python tutor helping a developer work through a lesson. "
    "The lesson the user is currently reading is given below for context. They rely on AI to "
    "write scripts and now want to truly UNDERSTAND Python — to review code and pass "
    "interviews.\n\n"
    "Guidelines:\n"
    "- Answer the question that was actually asked. Do NOT summarise the whole lesson unless "
    "asked; the user can already read it.\n"
    "- Stay anchored to the lesson's topic, and build on its examples and vocabulary so the "
    "answer feels continuous with what they just read.\n"
    "- Be concise and concrete. Short runnable snippets beat long prose.\n"
    "- Prefer showing the contrast (what people expect vs what Python does) — that is what "
    "makes these concepts stick.\n"
    "- If they ask about something the lesson does not cover, answer anyway, then note how it "
    "relates back to the topic.\n"
    "- If the user states something incorrect, correct it directly and explain why."
)


def build_lesson_context(lesson: dict, max_chars: int = 6000) -> str:
    """Flatten a lesson dict into compact text for the model's context window.

    Sections come first (they carry the code examples); key points and
    interview questions are appended while there is room.
    """
    if not isinstance(lesson, dict):
        return ""
    out: list[str] = []
    title = str(lesson.get("title") or "").strip()
    if title:
        level = str(lesson.get("level") or "").strip()
        out.append(f"# Lesson: {title}" + (f" ({level})" if level else ""))
    summary = str(lesson.get("summary") or "").strip()
    if summary:
        out.append(summary)

    for sec in lesson.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        heading = str(sec.get("heading") or "").strip()
        body = str(sec.get("body") or "").strip()
        if heading:
            out.append(f"\n## {heading}")
        if body:
            out.append(body)
        code = str(sec.get("code") or "").strip()
        if code:
            out.append("```python\n" + code + "\n```")
        note = str(sec.get("code_note") or "").strip()
        if note:
            out.append(f"Note: {note}")

    points = [str(k).strip() for k in (lesson.get("key_points") or []) if str(k).strip()]
    if points:
        out.append("\n## Key points")
        out += [f"- {p}" for p in points]

    questions = lesson.get("interview_questions") or []
    if questions:
        out.append("\n## Interview questions covered")
        for iq in questions:
            if isinstance(iq, dict) and str(iq.get("q") or "").strip():
                out.append(f"- Q: {iq['q']}")

    text = "\n".join(out)
    return text[:max_chars]


def build_lesson_system_prompt(lesson: dict) -> str:
    """System prompt for lesson Q&A: tutor persona + the lesson as context."""
    context = build_lesson_context(lesson)
    if not context:
        return CHAT_SYSTEM_PROMPT
    return LESSON_SYSTEM_PROMPT + "\n\nThe lesson the user is reading:\n\n" + context


MAX_CODE_IN_PROMPT = 14_000


def _numbered(code: str, limit: int) -> tuple[str, int, int]:
    """Line-number the source so the model can cite locations, clipped to `limit`."""
    lines = code.splitlines()
    out, used = [], 0
    for i, line in enumerate(lines, start=1):
        entry = f"{i:4} | {line}"
        if used + len(entry) > limit:
            return "\n".join(out), i - 1, len(lines)
        out.append(entry)
        used += len(entry) + 1
    return "\n".join(out), len(lines), len(lines)


def build_architecture_brief(arch: dict, max_items: int = 120) -> str:
    """Compact structural map: what exists, what calls what, why each part is there.

    This is what lets the deep-dive reason about a 1000-line file even when the
    raw source has to be clipped — the shape of the whole program still fits.
    """
    if not isinstance(arch, dict) or not arch:
        return ""
    out: list[str] = []
    deps = arch.get("dependencies") or []
    if deps:
        out.append("External dependencies: " + ", ".join(deps))
    entries = arch.get("entry_points") or []
    if entries:
        out.append("Entry points: " + ", ".join(entries))

    components = arch.get("components") or []
    if components:
        out.append("\nClasses:")
        for c in components[:max_items]:
            bits = [f"  L{c['line']} {c['name']}"]
            if c.get("bases"):
                bits.append(f"({', '.join(c['bases'])})")
            if c.get("decorators"):
                bits.append("[@" + ", @".join(c["decorators"]) + "]")
            out.append(" ".join(bits))
            if c.get("doc"):
                out.append(f"      doc: {c['doc']}")
            if c.get("members"):
                out.append(f"      methods: {', '.join(c['members'][:12])}")
        if len(components) > max_items:
            out.append(f"  … +{len(components) - max_items} more classes")

    funcs = arch.get("functions") or []
    if funcs:
        out.append("\nFunctions (line, name, inferred role, what it calls):")
        if len(funcs) <= max_items:
            for f in funcs:
                calls = ", ".join(f.get("calls", [])[:6]) or "—"
                marker = " [ENTRY]" if f.get("entry") else ""
                out.append(f"  L{f['line']} {f['name']}({f.get('args','')}) — {f.get('role','')}"
                           f"{marker}; calls: {calls}")
        else:
            # Too many to describe individually: keep the interesting ones in full
            # and compress the rest to one line each, so the map still spans the
            # whole file instead of stopping partway through.
            def interesting(f):
                return bool(f.get("entry") or f.get("owner") is None and f.get("callers"))
            detailed = [f for f in funcs if interesting(f)][:max_items]
            detailed_names = {f["name"] for f in detailed}
            for f in detailed:
                calls = ", ".join(f.get("calls", [])[:6]) or "—"
                marker = " [ENTRY]" if f.get("entry") else ""
                out.append(f"  L{f['line']} {f['name']}({f.get('args','')}) — {f.get('role','')}"
                           f"{marker}; calls: {calls}")
            rest = [f for f in funcs if f["name"] not in detailed_names]
            if rest:
                out.append(f"  Remaining {len(rest)} functions (name@line):")
                out.append("    " + ", ".join(f"{f['name']}@{f['line']}" for f in rest))

    orphans = arch.get("orphans") or []
    if orphans:
        out.append("\nNever called anywhere in this file: " + ", ".join(orphans[:15]))
    return "\n".join(out)


def build_user_prompt(code: str, static_summary: str, constructs: list[str],
                      architecture: dict | None = None,
                      finding_groups: list[dict] | None = None) -> str:
    """Assemble the deep-dive prompt.

    Large files are clipped, but the architecture brief still describes the whole
    program, and the clipping is stated explicitly so the model never silently
    pretends to have read code it never saw.
    """
    shown, shown_lines, total_lines = _numbered(code, MAX_CODE_IN_PROMPT)
    parts = [
        "Explain the following Python code. Focus on WHY it is built this way, not a "
        "restatement of each line.",
        "",
        "```python",
        shown,
        "```",
    ]
    if shown_lines < total_lines:
        parts += [
            "",
            f"NOTE: only lines 1-{shown_lines} of {total_lines} are shown above "
            f"({total_lines - shown_lines} lines omitted for length). The structural map "
            "below covers the ENTIRE file, including the omitted part. Base your answer on "
            "both, and say explicitly which parts you could not read in full.",
        ]

    brief = build_architecture_brief(architecture or {})
    if brief:
        parts += ["", "Structural map of the whole file:", brief]
    if static_summary:
        parts += ["", "Static analysis summary:", static_summary]
    if constructs:
        parts += ["", "Constructs detected: " + ", ".join(constructs)]
    if finding_groups:
        parts += ["", "Automated review flagged (rule × occurrences):"]
        parts += [f"  - {g['title']} ×{g['count']} (e.g. line {g['lines'][0]})"
                  if g.get("lines") else f"  - {g['title']} ×{g['count']}"
                  for g in finding_groups[:12]]
    return "\n".join(parts)


def env_key_for(provider: str) -> str:
    return os.environ.get(f"{provider.upper()}_API_KEY", "").strip()
