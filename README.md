# 🐍 Python Learning Agent

**Paste code → understand it → get better.**
A working prototype of a learning companion for developers who lean on AI to write scripts
and now need to actually *understand* Python — for interviews, for writing code themselves,
and for reviewing what an LLM handed them.

> Built for: *"AI does all my scripting, so I never learned the fundamentals. I need a tool
> where I can drop a piece of code, have it explain what it is and why the syntax is written
> that way, tell me what could be done better — and help me learn the underlying concepts."*

---

## What it does

### 🔍 Explain (the core loop)
Drop any Python snippet — especially AI-generated code — and get:

| Section | What you get |
|---|---|
| **What this code is** | A plain-English summary + stats (functions, classes, nesting…) |
| **Step-by-step walkthrough** | Every statement described in one sentence, indented by block depth |
| **Syntax & concepts used** | Each detected construct with **what** it is, **why the syntax is written that way**, a minimal example, the **interview angle**, and a link to the matching lesson |
| **Code review** | ~23 static checks: bugs, smells, performance, security — each with *what/why* and a **concrete fixed snippet** |
| **Run** | Executes in an isolated subprocess (5s timeout, CPU/memory limits) with **friendly, teachable explanations** when it crashes |
| **AI deep-dive (optional)** | Plug in your own OpenAI/Anthropic-compatible API key for an extra LLM narrative on top of the static analysis |
| **AI tutor chat (optional)** | Ask follow-up questions in a real conversation — grounded in the code in your editor, with history |

The explainer works **fully offline**: it parses your code with Python's own `ast` module and
matches it against a knowledge base of ~45 constructs (comprehensions, decorators, `*args/**kwargs`,
context managers, dunders, walrus operator, pattern matching, slicing, closures…) plus a curated
review-checker pass (mutable default arguments, bare `except`, `range(len(...))`, late-binding
closures, shared mutable class attributes, shadowed builtins, unsafe `eval`, unused imports/locals…).

### 📚 Learn
15 fundamentals lessons — variables, mutability & references, strings, collections,
control flow, loops, functions, scope/closures, comprehensions, exceptions, files & context
managers, OOP & dunders, iterators/generators, decorators, modules & environments.
Each lesson: why-it's-designed-that-way prose, annotated examples (one click sends them to the
Explainer), key points, and real interview Q&As.

### 🎯 Practice
24 interview-style questions built around the classic Python gotchas (mutable defaults, `is` vs
`==`, late-binding closures, shallow copy, `try/finally` return override, short-circuit operands,
dict ordering, generator laziness…) with instant explanations and score tracking.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

Run the test suite:

```bash
pip install pytest
pytest tests/ -v
```

### Optional: AI deep-dive & tutor chat
Set an env var before starting (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`), or paste a key in the
UI. Keys entered in the UI are stored only in your browser's localStorage and forwarded only to
the provider you choose. No key? Everything else still works.

Two modes share the same key:

- **Deep-dive with AI** — a one-shot structured breakdown of the whole snippet.
- **Ask a follow-up** — a real back-and-forth chat with the tutor. The conversation is
  automatically grounded in whatever is in the editor, so you can ask *"why is that a problem
  here?"*, *"show me the fix"*, or *"what would an interviewer ask about this?"* and it answers
  in context. Running a deep-dive seeds the chat, so follow-ups can refer back to the breakdown.

The chat lives in the browser: the server is stateless, keeps no transcripts, and caps history
at the 20 most recent turns so context and cost stay bounded.

**Using the Google Gemini free tier?** Provider `OpenAI-compatible`, Base URL
`https://generativelanguage.googleapis.com/v1beta/openai`, model `gemini-2.0-flash`.
Avoid the `2.5` "thinking" models on this endpoint — they can spend the entire token budget on
reasoning and return an empty message.

---

## Architecture

```
python-learning-agent/
├── app.py                  # Flask server + JSON API
├── engine/                 # the offline brain (pure stdlib: ast + subprocess)
│   ├── constructs.py       #   construct detector + knowledge base (what/why/example/interview)
│   ├── explain.py          #   statement-by-statement walkthrough + summary/stats
│   ├── review.py           #   23 static review checks with concrete fixes
│   ├── errors.py           #   traceback → friendly explanation (cause + fixes)
│   └── runner.py           #   isolated subprocess execution (timeout, rlimits, -I mode)
├── content/
│   ├── lessons.py          # 15 fundamentals lessons (data, rendered by the UI)
│   └── quiz.py             # 24 interview-gotcha questions
├── ai/llm.py               # optional LLM narrative (OpenAI-compatible / Anthropic)
├── templates/index.html    # single-page UI (vanilla JS, no CDN deps)
├── static/                 # styles + frontend logic
└── tests/                  # pytest suite for the engine and runner
```

**API**

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/explain` | POST `{code}` | full static analysis (constructs, walkthrough, findings, stats) |
| `/api/run` | POST `{code}` | sandboxed execution + friendly error explanation |
| `/api/lessons` | GET | the lesson bank |
| `/api/quiz` | GET | the question bank |
| `/api/ai/explain` | POST `{code, provider, api_key?, model?, base_url?}` | optional one-shot LLM narrative |
| `/api/ai/chat` | POST `{messages[], code, provider, api_key?, model?, base_url?}` | multi-turn tutor Q&A grounded in `code` |

---

## Safety notes

- "Run" executes **untrusted code** in a separate process with `python -I`, empty stdin,
  a disposable temp cwd, and CPU/memory/filesize rlimits (Linux). It is a *learning*
  sandbox, not a hardened security boundary — don't expose the server publicly.
- Static analysis never executes your code.

## Roadmap

- [ ] Spaced-repetition deck auto-generated from *your* explained snippets
- [ ] "Refactor challenge" mode: fix the flagged code, get a diff + grade
- [ ] Personal weakness dashboard from concept tags over time
- [ ] Local LLM support (Ollama) for fully-offline AI deep-dives
- [ ] Export a lesson + your snippets as an Anki deck

---

*Prototype built on the `python-learning-agent` repo. Analysis engine: pure stdlib. UI: no build step.*
