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

    analysis = analyze(code)
    constructs = [c["name"] for c in analysis.get("constructs", [])][:12]
    prompt = llm.build_user_prompt(code, analysis.get("summary", ""), constructs)
    try:
        text = llm.call_llm(provider, api_key, model, prompt)
    except llm.AIError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"text": text})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # 0.0.0.0 so the app is reachable from the container preview / LAN.
    app.run(host="0.0.0.0", port=port, debug=False)
