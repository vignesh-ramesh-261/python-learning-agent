/* Python Learning Agent — frontend logic (vanilla JS, no dependencies) */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of children) {
    if (child == null) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

/* ---------------------------------------------------------------- tabs */
$("#tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  $$(".tab").forEach((t) => t.classList.toggle("active", t === btn));
  $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${btn.dataset.tab}`));
});

function showTab(name) {
  $(`.tab[data-tab="${name}"]`).click();
}

/* ---------------------------------------------------------------- editor */
const codeEl = $("#code");
const gutterEl = $("#gutter");

function updateGutter() {
  const lines = codeEl.value.split("\n").length;
  gutterEl.textContent = Array.from({ length: Math.max(lines, 1) }, (_, i) => i + 1).join("\n");
}
codeEl.addEventListener("input", updateGutter);
codeEl.addEventListener("scroll", () => { gutterEl.scrollTop = codeEl.scrollTop; });
codeEl.addEventListener("keydown", (e) => {
  if (e.key === "Tab") {
    e.preventDefault();
    const { selectionStart: s, selectionEnd: eEnd } = codeEl;
    codeEl.value = codeEl.value.slice(0, s) + "    " + codeEl.value.slice(eEnd);
    codeEl.selectionStart = codeEl.selectionEnd = s + 4;
    updateGutter();
  }
});
updateGutter();

/* ---------------------------------------------------------------- samples */
const SAMPLES = {
  basics: `"""A small everyday script: functions, defaults, f-strings, dicts."""
MENU = {"coffee": 3.5, "tea": 2.8, "cake": 4.0}


def order(item, qty=1, tip_percent=0.1):
    """Return the total price for an order."""
    if item not in MENU:
        raise ValueError(f"we don't sell {item!r}")
    price = MENU[item] * qty
    return round(price * (1 + tip_percent), 2)


def main():
    for item in ["coffee", "tea", "juice"]:
        try:
            total = order(item, qty=2)
        except ValueError as err:
            print(f"skip: {err}")
        else:
            print(f"{item:>8}: \${total:.2f}")


if __name__ == "__main__":
    main()`,
  comprehensions: `"""Comprehensions, generator pipelines, and laziness."""
import json

ORDERS = [
    {"id": 1, "user": "ada", "amount": 120},
    {"id": 2, "user": "grace", "amount": 80},
    {"id": 3, "user": "ada", "amount": 45},
]

by_user = {o["user"]: 0 for o in ORDERS}
for order in ORDERS:
    user = order["user"]
    by_user[user] += order["amount"]

top = sorted(by_user.items(), key=lambda kv: kv[1], reverse=True)

def amounts_over(orders, floor):
    return (o["amount"] for o in orders if o["amount"] > floor)

print(dict(top))
print(f"big orders: {sum(amounts_over(ORDERS, 50))}")

def paginate(records, size):
    for start in range(0, len(records), size):
        yield records[start:start + size]

print(json.dumps(list(paginate(ORDERS, 2)), indent=2))`,
  classes: `"""Classes, dataclasses, dunders and decorators."""
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class Student:
    name: str
    grades: list[float] = field(default_factory=list)

    @property
    def average(self):
        return sum(self.grades) / len(self.grades) if self.grades else 0.0


class GradeBook:
    def __init__(self):
        self._students = {}

    def add(self, student):
        self._students[student.name] = student

    def __len__(self):
        return len(self._students)

    def __getitem__(self, name):
        return self._students[name]


def retry(times):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as err:
                    print(f"attempt {attempt} failed: {err}")
            raise RuntimeError("all retries failed")
        return wrapper
    return decorator


@retry(times=3)
@lru_cache(maxsize=None)
def flaky(value):
    if value < 2:
        raise ValueError("too small")
    return value


book = GradeBook()
book.add(Student("Ada", [90, 85, 95]))
book.add(Student("Grace", [78, 92]))
print(len(book), book["Ada"].average, flaky(5))`,
  files: `"""Files, context managers and error handling."""
from pathlib import Path


def parse_scores(path):
    scores = {}
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                name, raw = line.split(",")
                scores[name] = int(raw)
            except ValueError as err:
                print(f"line {line_no}: {err}")
    return scores


def save_report(path, scores):
    lines = [f"{name}: {score}" for name, score in sorted(scores.items())]
    Path(path).write_text("\\n".join(lines), encoding="utf-8")


try:
    scores = parse_scores("scores.txt")
except FileNotFoundError:
    print("scores.txt missing — creating a demo one")
    Path("scores.txt").write_text("ada,90\\ngrace,78\\nbad-row\\n", encoding="utf-8")
    scores = parse_scores("scores.txt")

save_report("report.txt", scores)
print(scores)`,
  ai_script: `"""A 'typical' AI-generated script — the review should find several issues."""
import json
import os


def load_data(filename, cache={}):
    file = open(filename)
    data = file.read()
    return json.loads(data)


def process(items):
    result = ""
    for i in range(len(items)):
        if items[i] > 0:
            result = result + str(items[i]) + ","
    return result


def get_value(config, key):
    try:
        return config[key]
    except:
        pass


class Counter:
    total = []

    def add(self, x):
        self.total.append(x)


if True:
    eval(input("enter expression: "))`,
};

$("#samples").addEventListener("change", (e) => {
  const sample = SAMPLES[e.target.value];
  if (sample) {
    codeEl.value = sample;
    updateGutter();
    explain();
  }
  e.target.value = "";
});

/* ---------------------------------------------------------------- explain */
const resultsEl = $("#results");

async function api(path, body) {
  const resp = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || `Request failed (${resp.status})`);
  return data;
}

async function explain() {
  const code = codeEl.value.trim();
  if (!code) return;
  const btn = $("#btn-explain");
  btn.disabled = true;
  btn.textContent = "Analyzing…";
  $("#explain-error").classList.add("hidden");
  $("#run-results").classList.add("hidden");
  try {
    const analysis = await api("/api/explain", { code });
    if (!analysis.ok) {
      renderSyntaxError(analysis.error);
    } else {
      resultsEl.classList.remove("hidden");
      renderSummary(analysis);
      renderWalkthrough(analysis.walkthrough);
      renderConstructs(analysis.constructs);
      renderFindings(analysis.findings);
    }
    resultsEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    renderSyntaxError({ exception: "Request failed", message: err.message, what: err.message });
  } finally {
    btn.disabled = false;
    btn.textContent = "Explain code";
  }
}

$("#btn-explain").addEventListener("click", explain);
$("#btn-clear").addEventListener("click", () => {
  codeEl.value = "";
  updateGutter();
  resultsEl.classList.add("hidden");
  $("#explain-error").classList.add("hidden");
  $("#run-results").classList.add("hidden");
  $("#ai-output").classList.add("hidden");
  chatHistory = [];
  renderChat();
  chatStatus("");
});

function renderSyntaxError(err) {
  const card = $("#explain-error");
  card.classList.remove("hidden");
  resultsEl.classList.add("hidden");
  card.replaceChildren(
    el("h2", { text: `Can't run this yet — ${err.exception}` }),
    err.offending_line ? el("pre", { text: `${err.offending_line}\n${" ".repeat(Math.max((err.offset || 1) - 1, 0))}^` }) : null,
    el("p", { text: err.message || "" }),
    el("div", { class: "err-explain" },
      el("h4", { text: err.what || "" }),
      err.common_causes ? el("ul", {}, ...err.common_causes.map((c) => el("li", { text: c }))) : null,
      err.fixes && err.fixes.length ? el("ul", {}, ...err.fixes.map((f) => el("li", { text: `Fix: ${f}` }))) : null,
    ),
  );
}

function renderSummary(analysis) {
  $("#summary-text").textContent = analysis.summary;
  const s = analysis.stats;
  $("#stats-row").replaceChildren(
    chip("lines", s.code_lines),
    chip("functions", s.functions),
    chip("classes", s.classes),
    chip("loops", s.loops),
    chip("imports", s.imports),
    chip("max nesting", s.max_nesting),
    chip("review flags", analysis.findings.length),
  );
  function chip(label, value) {
    return el("span", { class: "chip" }, el("b", { text: String(value) }), ` ${label}`);
  }
}

function renderWalkthrough(steps) {
  const list = $("#walkthrough");
  list.replaceChildren(
    ...steps.map((step) =>
      el("li", { class: `indent-${Math.min(step.depth, 3)}` },
        el("span", { class: "ln", text: `L${step.line}` }),
        el("div", {},
          el("span", { class: "code", text: step.code }),
          el("span", { class: "desc", text: step.text }),
        ),
      ),
    ),
  );
}

function renderConstructs(constructs) {
  const wrap = $("#constructs");
  if (!constructs.length) {
    wrap.replaceChildren(el("p", { class: "muted", text: "No recognizable constructs — add some code!" }));
    return;
  }
  wrap.replaceChildren(
    ...constructs.map((c, idx) => {
      const lessonBtn = c.lesson
        ? el("button", {
            class: "lesson-link",
            text: `→ Review the lesson: ${LESSON_TITLES[c.lesson] || c.lesson}`,
            onclick: () => openLesson(c.lesson),
          })
        : null;
      const body = el("div", { class: "construct-body" },
        el("p", {}, el("span", { class: "label", text: "What" }), c.what),
        el("p", {}, el("span", { class: "label", text: "Why this syntax" }), c.why),
        c.example ? el("pre", { text: c.example }) : null,
        el("div", { class: "interview-note" }, "🎙️ Interview angle: ", c.interview),
        lessonBtn,
      );
      const first = idx === 0;
      return el("details", { class: "construct", open: first ? "" : null },
        el("summary", {},
          el("span", { class: "construct-title", text: c.name }),
          el("span", { class: "construct-meta", text: `${c.category} · line${c.lines.length > 1 ? "s" : ""} ${c.lines.slice(0, 4).join(", ")}${c.lines.length > 4 ? "…" : ""}` }),
        ),
        body,
      );
    }),
  );
}

function renderFindings(findings) {
  const wrap = $("#findings");
  if (!findings.length) {
    wrap.replaceChildren(el("p", { class: "all-clear", text: "✓ No issues found by the automated review. Nice code!" }));
    return;
  }
  wrap.replaceChildren(
    ...findings.map((f) =>
      el("div", { class: "finding", "data-severity": f.severity },
        el("h3", {},
          el("span", { class: `badge ${f.severity}`, text: f.severity }),
          el("span", { text: f.title }),
          el("span", { class: "ln", text: `line ${f.line}` }),
        ),
        el("p", { text: f.what }),
        el("p", { class: "muted", text: f.why }),
        f.fix ? el("pre", { text: f.fix }) : null,
        f.lesson ? el("button", {
          class: "lesson-link",
          text: `→ Review the lesson: ${LESSON_TITLES[f.lesson] || f.lesson}`,
          onclick: () => openLesson(f.lesson),
        }) : null,
      ),
    ),
  );
}

/* ---------------------------------------------------------------- run */
$("#btn-run").addEventListener("click", async () => {
  const code = codeEl.value.trim();
  if (!code) return;
  const btn = $("#btn-run");
  btn.disabled = true;
  btn.textContent = "Running…";
  const card = $("#run-results");
  const body = $("#run-body");
  card.classList.remove("hidden");
  body.replaceChildren(el("p", { class: "muted", text: "Executing in an isolated subprocess (max 5s)…" }));
  try {
    const result = await api("/api/run", { code });
    body.replaceChildren();
    if (result.stdout) body.appendChild(el("pre", { class: "run-stdout", text: result.stdout }));
    if (result.stderr) body.appendChild(el("pre", { class: "run-stderr", text: result.stderr }));
    if (!result.stdout && !result.stderr) {
      body.appendChild(el("p", { class: "muted", text: "(no output — the code ran without printing anything)" }));
    }
    if (result.timed_out) {
      body.appendChild(el("p", { class: "run-stderr", text: "Timed out after 5 seconds — infinite loop?" }));
    }
    const err = result.error_explanation;
    if (err) {
      body.appendChild(renderErrorExplanation(err));
    } else if (!result.timed_out) {
      body.appendChild(el("p", { class: "run-meta", text: `exit code ${result.exit_code} · ${result.duration}s` }));
    }
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    body.replaceChildren(el("p", { class: "run-stderr", text: e.message }));
  } finally {
    btn.disabled = false;
    btn.textContent = "▶ Run";
  }
});

function renderErrorExplanation(err) {
  return el("div", { class: "err-explain" },
    el("h4", { text: `🩺 ${err.exception}${err.line ? ` (line ${err.line})` : ""}: ${err.message}` }),
    el("p", { class: "small", text: err.what }),
    err.hints ? el("ul", {}, ...err.hints.map((h) => el("li", { text: h }))) : null,
    el("ul", {}, ...err.common_causes.map((c) => el("li", { text: `Likely cause: ${c}` }))),
    err.fixes.length ? el("ul", {}, ...err.fixes.map((f) => el("li", { text: `Fix: ${f}` }))) : null,
  );
}

/* ---------------------------------------------------------------- AI deep-dive */
const AI_KEYS = ["pla_ai_provider", "pla_ai_key", "pla_ai_model", "pla_ai_baseurl"];
$("#ai-provider").value = localStorage.getItem(AI_KEYS[0]) || "openai";
$("#ai-key").value = localStorage.getItem(AI_KEYS[1]) || "";
$("#ai-model").value = localStorage.getItem(AI_KEYS[2]) || "";
$("#ai-baseurl").value = localStorage.getItem(AI_KEYS[3]) || "";

$("#btn-ai").addEventListener("click", async () => {
  const code = codeEl.value.trim();
  if (!code) { aiStatus("Load some code first."); return; }
  const provider = $("#ai-provider").value;
  const api_key = $("#ai-key").value.trim();
  const model = $("#ai-model").value.trim();
  const base_url = $("#ai-baseurl").value.trim();
  localStorage.setItem(AI_KEYS[0], provider);
  localStorage.setItem(AI_KEYS[1], api_key);
  localStorage.setItem(AI_KEYS[2], model);
  localStorage.setItem(AI_KEYS[3], base_url);

  const out = $("#ai-output");
  out.classList.add("hidden");
  aiStatus("Asking the AI for a deep-dive… (can take ~20s)");
  const btn = $("#btn-ai");
  btn.disabled = true;
  try {
    const data = await api("/api/ai/explain", { code, provider, api_key, model, base_url });
    out.replaceChildren(...renderMarkdown(data.text));
    out.classList.remove("hidden");
    aiStatus("Done — now ask follow-up questions in the chat below.");
    // Seed the conversation so follow-ups can refer to "this breakdown".
    chatHistory = [
      { role: "user", content: "Give me a full breakdown of the code I'm working on." },
      { role: "assistant", content: data.text },
    ];
    renderChat();
  } catch (e) {
    aiStatus(`⚠️ ${e.message}`);
  } finally {
    btn.disabled = false;
  }
});

function aiStatus(text) { $("#ai-status").textContent = text; }

/* Inline markdown → DOM nodes. Text-only (textContent), so it is XSS-safe. */
function renderInline(line) {
  const out = [];
  // Split on **bold** and `code`, keeping the delimiters' contents.
  const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      out.push(el("strong", { text: part.slice(2, -2) }));
    } else if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      out.push(el("code", { text: part.slice(1, -1) }));
    } else {
      out.push(document.createTextNode(part));
    }
  }
  return out;
}

function renderMarkdown(text) {
  const nodes = [];
  let inCode = false;
  let codeBuf = [];
  let list = null;

  const closeList = () => { if (list) { nodes.push(list); list = null; } };

  for (const line of (text || "").split("\n")) {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        nodes.push(el("pre", { text: codeBuf.join("\n") }));
        codeBuf = [];
      } else {
        closeList();
      }
      inCode = !inCode;
      continue;
    }
    if (inCode) { codeBuf.push(line); continue; }

    const heading = line.match(/^\s*(#{1,4})\s+(.*)/);
    if (heading) { closeList(); nodes.push(el("h4", { text: heading[2] })); continue; }

    const bullet = line.match(/^\s*[-*+]\s+(.*)/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)/);
    if (bullet || numbered) {
      const wantTag = bullet ? "ul" : "ol";
      if (!list || list.tagName.toLowerCase() !== wantTag) { closeList(); list = el(wantTag); }
      list.appendChild(el("li", {}, ...renderInline((bullet || numbered)[1])));
      continue;
    }

    if (!line.trim()) { closeList(); continue; }
    closeList();
    nodes.push(el("p", {}, ...renderInline(line)));
  }
  closeList();
  if (codeBuf.length) nodes.push(el("pre", { text: codeBuf.join("\n") }));
  return nodes.length ? nodes : [el("p", { class: "muted", text: "(empty response)" })];
}

/* ------------------------------------------------------------- AI chat Q&A */
const SUGGESTED_QUESTIONS = [
  "Explain line by line",
  "What would break in production?",
  "How would I make this faster?",
  "What interview questions come from this?",
  "Rewrite this the idiomatic way",
];

let chatHistory = [];   // [{role: 'user'|'assistant', content}]
let chatBusy = false;

const chatLogEl = $("#chat-log");
const chatInputEl = $("#chat-input");
const chatStatusEl = $("#chat-status");

function chatStatus(text) { chatStatusEl.textContent = text || ""; }

function aiSettings() {
  return {
    provider: $("#ai-provider").value,
    api_key: $("#ai-key").value.trim(),
    model: $("#ai-model").value.trim(),
    base_url: $("#ai-baseurl").value.trim(),
  };
}

function autoGrow(el_) {
  el_.style.height = "auto";
  el_.style.height = Math.min(el_.scrollHeight, 160) + "px";
}
chatInputEl.addEventListener("input", () => autoGrow(chatInputEl));

function renderChat() {
  chatLogEl.replaceChildren();
  if (!chatHistory.length) {
    chatLogEl.appendChild(el("p", { class: "muted small chat-empty", text:
      "No questions yet. Ask anything about the code above — or run a deep-dive first, then dig into it." }));
  }
  for (const msg of chatHistory) {
    const row = el("div", { class: `chat-msg ${msg.role}` });
    row.appendChild(el("div", { class: "chat-role", text: msg.role === "user" ? "You" : "Tutor" }));
    const bubble = el("div", { class: "chat-bubble" });
    if (msg.role === "user") bubble.appendChild(el("p", { text: msg.content }));
    else bubble.replaceChildren(...renderMarkdown(msg.content));
    row.appendChild(bubble);
    chatLogEl.appendChild(row);
  }
  if (chatBusy) {
    chatLogEl.appendChild(
      el("div", { class: "chat-msg assistant" },
        el("div", { class: "chat-role", text: "Tutor" }),
        el("div", { class: "chat-bubble thinking" }, el("span", { class: "dots", text: "thinking…" })),
      ),
    );
  }
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
}

function renderSuggestions() {
  $("#chat-suggestions").replaceChildren(
    ...SUGGESTED_QUESTIONS.map((q) =>
      el("button", {
        class: "chip-btn", type: "button", text: q,
        onclick: () => { chatInputEl.value = q; autoGrow(chatInputEl); sendChat(); },
      })),
  );
}

async function sendChat() {
  if (chatBusy) return;
  const question = chatInputEl.value.trim();
  if (!question) return;
  const { provider, api_key, model, base_url } = aiSettings();
  if (!api_key) { chatStatus("⚠️ Add your API key in the box above first."); return; }

  chatHistory.push({ role: "user", content: question });
  chatInputEl.value = "";
  autoGrow(chatInputEl);
  chatBusy = true;
  $("#btn-chat-send").disabled = true;
  chatStatus("");
  renderChat();

  try {
    const data = await api("/api/ai/chat", {
      messages: chatHistory,
      code: codeEl.value.trim(),
      provider, api_key, model, base_url,
    });
    chatHistory.push({ role: "assistant", content: data.text });
  } catch (e) {
    // Keep the question in the box so it isn't lost on a failed request.
    chatHistory.pop();
    chatInputEl.value = question;
    autoGrow(chatInputEl);
    chatStatus(`⚠️ ${e.message}`);
  } finally {
    chatBusy = false;
    $("#btn-chat-send").disabled = false;
    renderChat();
  }
}

$("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat(); });
chatInputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
});
$("#btn-chat-clear").addEventListener("click", () => {
  chatHistory = [];
  chatStatus("");
  renderChat();
});

renderSuggestions();
renderChat();

/* ---------------------------------------------------------------- learn */
const LESSON_TITLES = {};
let lessonsCache = null;

async function loadLessons() {
  if (lessonsCache) return lessonsCache;
  lessonsCache = await api("/api/lessons");
  for (const lesson of lessonsCache) LESSON_TITLES[lesson.id] = lesson.title;
  return lessonsCache;
}

async function renderLessonNav(activeId = null) {
  const lessons = await loadLessons();
  const nav = $("#lesson-nav");
  nav.replaceChildren();
  const levels = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };
  for (const [level, label] of Object.entries(levels)) {
    const group = lessons.filter((l) => l.level === level);
    if (!group.length) continue;
    nav.appendChild(el("div", { class: "group", text: label }));
    for (const lesson of group) {
      nav.appendChild(el("button", {
        class: lesson.id === activeId ? "active" : "",
        text: lesson.title,
        onclick: () => selectLesson(lesson.id),
      }));
    }
  }
}

async function selectLesson(id) {
  await renderLessonNav(id);
  const lessons = await loadLessons();
  const lesson = lessons.find((l) => l.id === id);
  if (!lesson) return;
  const content = $("#lesson-content");
  content.replaceChildren(
    el("h2", { text: lesson.title }),
    el("p", { class: "summary", text: lesson.summary }),
    ...lesson.sections.map((sec) =>
      el("section", {},
        el("h3", { text: sec.heading }),
        el("p", { text: sec.body }),
        sec.code ? el("pre", { text: sec.code }) : null,
        sec.code_note ? el("p", { class: "code-note", text: `↳ ${sec.code_note}` }) : null,
        sec.code ? el("div", { class: "lesson-try" },
          el("button", {
            class: "btn",
            text: "🔍 Explain this example",
            onclick: () => {
              codeEl.value = sec.code;
              updateGutter();
              showTab("explain");
              explain();
            },
          }),
        ) : null,
      ),
    ),
    el("section", {},
      el("h3", { text: "Key points to remember" }),
      el("ul", { class: "key-points" }, ...lesson.key_points.map((k) => el("li", { text: k }))),
    ),
    el("section", {},
      el("h3", { text: "Interview questions" }),
      ...lesson.interview_questions.map((iq) =>
        el("details", { class: "iq" },
          el("summary", { text: `Q: ${iq.q}` }),
          el("div", { class: "a", text: iq.a }),
        ),
      ),
    ),
  );
}

function openLesson(id) {
  showTab("learn");
  selectLesson(id);
}

/* ---------------------------------------------------------------- practice */
let quizState = null;

async function startQuiz(shuffled = true) {
  const questions = await api("/api/quiz");
  const order = questions.map((_, i) => i);
  if (shuffled) order.sort(() => Math.random() - 0.5);
  quizState = { questions, order, pos: 0, score: 0, answered: 0, done: false };
  renderQuiz();
}

function renderQuiz() {
  const card = $("#quiz-card");
  const st = quizState;
  if (!st) return;
  const total = st.order.length;
  if (st.pos >= total) {
    const pct = Math.round((st.score / total) * 100);
    card.replaceChildren(
      el("div", { class: "quiz-score-final" },
        el("h2", { text: "Round complete 🎉" }),
        el("div", { class: "big", text: `${st.score} / ${total}` }),
        el("p", { class: "muted", text:
          pct >= 85 ? "Interview-ready on these topics. Try a fresh shuffle or dig into the lessons."
          : pct >= 60 ? "Solid base — revisit the explanations you missed and go again."
          : "Great starting point! Read the linked lessons, then reshuffle — these gotchas are very learnable." }),
        el("div", { class: "quiz-nav", style: "justify-content:center" },
          el("button", { class: "btn primary", text: "Shuffle & restart", onclick: () => startQuiz(true) }),
        ),
      ),
    );
    return;
  }
  const q = st.questions[st.order[st.pos]];
  card.replaceChildren(
    el("div", { class: "quiz-top" },
      el("span", { class: "muted", text: `Question ${st.pos + 1} of ${total}` }),
      el("span", {}, el("span", { class: "tag", text: q.topic }), " ", el("span", { class: "tag", text: q.difficulty })),
      el("span", { class: "muted", text: `Score ${st.score}` }),
    ),
    el("div", { class: "progress" }, el("div", { style: `width:${(st.pos / total) * 100}%` })),
    el("p", { class: "quiz-question", text: q.question }),
    q.code ? el("pre", { class: "quiz-code", text: q.code }) : null,
    el("div", { class: "options" }, ...q.options.map((opt, idx) =>
      el("button", { text: `${String.fromCharCode(65 + idx)}. ${opt}`, onclick: () => answer(idx) })),
    ),
  );

  function answer(idx) {
    if (card.dataset.answered === "1") return;
    card.dataset.answered = "1";
    const buttons = $$(".options button", card);
    buttons.forEach((b) => (b.disabled = true));
    const correct = idx === q.answer;
    buttons[q.answer].classList.add("correct");
    if (!correct) buttons[idx].classList.add("wrong");
    st.answered += 1;
    if (correct) st.score += 1;
    card.appendChild(
      el("div", { class: `quiz-feedback ${correct ? "ok" : "no"}` },
        el("strong", { text: correct ? "✓ Correct. " : `✗ Not quite — answer: ${q.options[q.answer]}. ` }),
        el("span", { text: q.explanation }),
      ),
    );
    card.appendChild(
      el("div", { class: "quiz-nav" },
        el("button", { class: "btn primary", text: st.pos + 1 >= total ? "See results" : "Next question →",
          onclick: () => { card.dataset.answered = ""; st.pos += 1; renderQuiz(); } }),
      ),
    );
    $$(".progress > div", card.parentElement).forEach(() => {});
  }
}

/* ---------------------------------------------------------------- boot */
(async function boot() {
  const lessons = await loadLessons();
  await renderLessonNav();
  if (lessons.length) await selectLesson(lessons[0].id);
  await startQuiz(true);
})();
