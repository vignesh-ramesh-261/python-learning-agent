"""Python Learning Agent — web app (Flask).

Run:  python app.py   (then open http://localhost:5000)
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from ai import llm
from content import lessons as lessons_mod
from content import quiz as quiz_mod
from engine import analyze, explain_runtime_error
from engine.runner import run_code
from engine.tracer import trace_code

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB request cap


def _bad_request(message: str):
    return jsonify({"error": message}), 400


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/explain")
def api_explain():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return _bad_request("No code provided.")
    return jsonify(analyze(code))


@app.post("/api/run")
def api_run():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return _bad_request("No code provided.")
    result = run_code(code)
    error = explain_runtime_error(result.get("stderr", ""))
    result["error_explanation"] = error
    return jsonify(result)


@app.post("/api/trace")
def api_trace():
    """Step-by-step execution recording for the visualizer."""
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return _bad_request("No code provided.")
    return jsonify(trace_code(code))


@app.get("/api/lessons")
def api_lessons():
    return jsonify(lessons_mod.LESSONS)


@app.get("/api/quiz")
def api_quiz():
    return jsonify(quiz_mod.QUIZ)


@app.post("/api/ai/explain")
def api_ai_explain():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return _bad_request("No code provided.")
    provider = (data.get("provider") or "openai").lower()
    api_key = (data.get("api_key") or "").strip() or llm.env_key_for(provider)
    model = (data.get("model") or "").strip() or None
    base_url = (data.get("base_url") or "").strip() or None

    analysis = analyze(code)
    constructs = [c["name"] for c in analysis.get("constructs", [])][:12]
    prompt = llm.build_user_prompt(
        code, analysis.get("summary", ""), constructs,
        analysis.get("architecture"), analysis.get("finding_groups"))
    if not api_key:
        return _bad_request(
            "No API key provided. Paste your key in the AI deep-dive box, or set "
            f"{provider.upper()}_API_KEY in the server environment."
        )
    try:
        text = llm.call_llm(provider, api_key, model, prompt, base_url)
    except llm.AIError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001 - never 500 with an empty body
        app.logger.exception("AI deep-dive failed")
        return jsonify({"error": f"Unexpected error calling the AI provider: {exc}"}), 500
    if not (text or "").strip():
        return jsonify({"error": "The model returned an empty response."}), 400
    return jsonify({"text": text})


@app.post("/api/ai/chat")
def api_ai_chat():
    """Multi-turn Q&A with the tutor, grounded in the user's current code.

    The browser owns the conversation and posts the full history each time —
    the server stays stateless and never persists keys or transcripts.
    """
    data = request.get_json(silent=True) or {}
    messages = llm.sanitize_messages(data.get("messages"))
    if not messages:
        return _bad_request("No question provided.")
    if messages[-1]["role"] != "user":
        return _bad_request("The last message must be from the user.")

    provider = (data.get("provider") or "openai").lower()
    api_key = (data.get("api_key") or "").strip() or llm.env_key_for(provider)
    model = (data.get("model") or "").strip() or None
    base_url = (data.get("base_url") or "").strip() or None
    if not api_key:
        return _bad_request(
            "No API key provided. Paste your key in the AI deep-dive box, or set "
            f"{provider.upper()}_API_KEY in the server environment."
        )

    code = (data.get("code") or "").strip()
    summary, constructs, arch = "", [], None
    if code:
        try:
            analysis = analyze(code)
            summary = analysis.get("summary", "")
            constructs = [c["name"] for c in analysis.get("constructs", [])][:12]
            arch = analysis.get("architecture")
        except Exception:  # noqa: BLE001 - unparseable code must not block the chat
            pass
    system = llm.build_chat_system_prompt(code, summary, constructs, arch)

    return _chat_reply(provider, api_key, model, messages, base_url, system)


@app.post("/api/ai/lesson")
def api_ai_lesson():
    """Multi-turn Q&A about a lesson from the Learn tab.

    The client sends only a lesson_id; the lesson text is looked up here so the
    grounding context cannot be forged from the browser.
    """
    data = request.get_json(silent=True) or {}
    messages = llm.sanitize_messages(data.get("messages"))
    if not messages:
        return _bad_request("No question provided.")
    if messages[-1]["role"] != "user":
        return _bad_request("The last message must be from the user.")

    lesson_id = (data.get("lesson_id") or "").strip()
    lesson = next((l for l in lessons_mod.LESSONS if l.get("id") == lesson_id), None)
    if lesson is None:
        return _bad_request("Unknown lesson.")

    provider = (data.get("provider") or "openai").lower()
    api_key = (data.get("api_key") or "").strip() or llm.env_key_for(provider)
    model = (data.get("model") or "").strip() or None
    base_url = (data.get("base_url") or "").strip() or None
    if not api_key:
        return _bad_request(
            "No API key provided. Paste your key in the AI deep-dive box on the Explain "
            f"tab, or set {provider.upper()}_API_KEY in the server environment."
        )

    system = llm.build_lesson_system_prompt(lesson)
    return _chat_reply(provider, api_key, model, messages, base_url, system)


def _chat_reply(provider, api_key, model, messages, base_url, system):
    """Shared LLM call + error envelope for the chat endpoints."""
    try:
        text = llm.call_chat(provider, api_key, model, messages, base_url, system)
    except llm.AIError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("AI chat failed")
        return jsonify({"error": f"Unexpected error calling the AI provider: {exc}"}), 500
    if not (text or "").strip():
        return jsonify({"error": "The model returned an empty response."}), 400
    return jsonify({"text": text})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # 0.0.0.0 so the app is reachable from the container preview / LAN.
    app.run(host="0.0.0.0", port=port, debug=False)
