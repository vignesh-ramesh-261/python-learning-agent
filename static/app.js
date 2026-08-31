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
      renderArchitecture(analysis.architecture, analysis.stats);
      renderWalkthrough(analysis.walkthrough, analysis.large);
      renderConstructs(analysis.constructs);
      renderFindings(analysis.finding_groups || analysis.findings);
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
  codeChat.reset();
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

/* A flat 400-step list is unreadable. On large files show the first slice and
   let the user opt in to the rest. */
const WALKTHROUGH_PREVIEW = 40;

function renderWalkthrough(steps, isLarge) {
  const list = $("#walkthrough");
  const note = $("#walkthrough-note");
  const toggle = $("#walkthrough-toggle");
  let expanded = !isLarge;

  const item = (step) =>
    el("li", { class: `indent-${Math.min(step.depth, 3)}` },
      el("span", { class: "ln", text: `L${step.line}` }),
      el("div", {},
        el("span", { class: "code", text: step.code }),
        el("span", { class: "desc", text: step.text }),
      ),
    );

  function paint() {
    const shown = expanded ? steps : steps.slice(0, WALKTHROUGH_PREVIEW);
    list.replaceChildren(...shown.map(item));
    toggle.textContent = expanded
      ? "Collapse walkthrough"
      : `Show all ${steps.length} steps →`;
  }

  if (isLarge) {
    note.textContent =
      `This file produces ${steps.length} steps — too many to read end to end. ` +
      "Start with “How it fits together” above; expand this only when you need a specific line.";
    note.classList.remove("hidden");
    toggle.classList.remove("hidden");
    toggle.onclick = () => { expanded = !expanded; paint(); };
  } else {
    note.classList.add("hidden");
    toggle.classList.add("hidden");
  }
  paint();
}

/* The architecture map: what exists, why it exists, and what calls what. */
function renderArchitecture(arch, stats) {
  const wrap = $("#architecture");
  if (!arch || (!arch.components?.length && !arch.functions?.length)) {
    wrap.replaceChildren(el("p", { class: "muted", text:
      "Straight-line script — no functions or classes to map. Read the walkthrough below." }));
    return;
  }
  const nodes = [];

  const meta = [];
  if (arch.dependencies?.length) {
    meta.push(el("p", {}, el("span", { class: "label", text: "Depends on" }),
      arch.dependencies.join(", ")));
  }
  if (arch.entry_points?.length) {
    meta.push(el("p", {}, el("span", { class: "label", text: "Starts at" }),
      arch.entry_points.map((e) => `${e}()`).join(", ")));
  } else if (stats && (stats.functions || stats.classes)) {
    meta.push(el("p", { class: "muted small" },
      "No explicit entry point (no __main__ guard or top-level call) — this file looks like a library/module."));
  }
  if (meta.length) nodes.push(el("div", { class: "arch-meta" }, ...meta));

  if (arch.components?.length) {
    nodes.push(el("h3", { class: "arch-h", text: `Classes (${arch.components.length})` }));
    nodes.push(el("div", { class: "arch-list" }, ...arch.components.map((c) =>
      el("details", { class: "arch-item" },
        el("summary", {},
          el("span", { class: "arch-name", text: c.name }),
          el("span", { class: "arch-line", text: `L${c.line}` }),
        ),
        el("div", { class: "arch-body" },
          c.doc ? el("p", { class: "arch-doc", text: c.doc }) : null,
          el("p", {}, el("span", { class: "label", text: "Why it exists" }), c.why),
          c.members?.length
            ? el("p", { class: "muted small", text: `Methods: ${c.members.join(", ")}` })
            : null,
        ),
      ))));
  }

  if (arch.functions?.length) {
    nodes.push(el("h3", { class: "arch-h", text: `Functions (${arch.functions.length})` }));
    nodes.push(el("div", { class: "arch-list" }, ...arch.functions.map((f) =>
      el("details", { class: "arch-item" },
        el("summary", {},
          el("span", { class: "arch-name", text: `${f.name}(${f.args || ""})` }),
          f.entry ? el("span", { class: "arch-tag entry", text: "entry" }) : null,
          el("span", { class: "arch-role", text: f.role }),
          el("span", { class: "arch-line", text: `L${f.line}` }),
        ),
        el("div", { class: "arch-body" },
          f.doc ? el("p", { class: "arch-doc", text: f.doc }) : null,
          el("p", { class: "small" },
            el("span", { class: "label", text: "Calls" }),
            f.calls?.length ? f.calls.join(", ") : "nothing"),
          el("p", { class: "small" },
            el("span", { class: "label", text: "Called by" }),
            f.callers?.length ? f.callers.join(", ")
              : (f.entry ? "the entry point" : "— nothing in this file")),
          el("div", { class: "lesson-try" },
            el("button", {
              class: "chip-btn", type: "button", text: "💬 Why does this exist?",
              onclick: () => codeChat.ask(
                `Looking at \`${f.name}\` (line ${f.line}) in my code: why does this function ` +
                "exist as a separate unit, what would break if I inlined it, and is its " +
                "current design the right call?"),
            }),
          ),
        ),
      ))));
  }

  if (arch.orphans?.length) {
    nodes.push(el("p", { class: "arch-warn" },
      `Never called in this file: ${arch.orphans.join(", ")} — dead code, or a public API used elsewhere?`));
  }
  wrap.replaceChildren(...nodes);
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
  // Findings arrive grouped by rule (with a count + line list); tolerate the
  // ungrouped shape too so the renderer stays backward compatible.
  wrap.replaceChildren(
    ...findings.map((f) => {
      const lines = f.lines || (f.line != null ? [f.line] : []);
      const count = f.count || lines.length || 1;
      const shown = lines.slice(0, 8);
      const lineLabel = count === 1
        ? `line ${lines[0]}`
        : `${count}× — lines ${shown.join(", ")}${lines.length > shown.length ? "…" : ""}`;
      return el("div", { class: "finding", "data-severity": f.severity },
        el("h3", {},
          el("span", { class: `badge ${f.severity}`, text: f.severity }),
          el("span", { text: f.title }),
          el("span", { class: "ln", text: lineLabel }),
        ),
        el("p", { text: f.what }),
        el("p", { class: "muted", text: f.why }),
        f.fix ? el("pre", { text: f.fix }) : null,
        el("div", { class: "lesson-try" },
          f.lesson ? el("button", {
            class: "lesson-link",
            text: `→ Review the lesson: ${LESSON_TITLES[f.lesson] || f.lesson}`,
            onclick: () => openLesson(f.lesson),
          }) : null,
          el("button", {
            class: "chip-btn", type: "button", text: "💬 Why does this matter here?",
            onclick: () => codeChat.ask(
              `The review flagged "${f.title}"${count > 1 ? ` in ${count} places` : ""} ` +
              `(e.g. line ${lines[0]}). Why does this matter in MY code specifically — ` +
              "what could actually go wrong, and what is the cleanest fix here?"),
          }),
        ),
      );
    }),
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

$("#btn-ai").addEventListener("click", runDeepDive);

async function runDeepDive() {
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
    codeChat.seed([
      { role: "user", content: "Give me a full breakdown of the code I'm working on." },
      { role: "assistant", content: data.text },
    ]);
  } catch (e) {
    aiErrorStatus(e.message, runDeepDive);
  } finally {
    btn.disabled = false;
  }
}

function aiStatus(text) { $("#ai-status").textContent = text; }

/* Providers retire model IDs regularly. Their 404 usually names the
   replacement ("use models/gemini-3.6-flash instead") — offer a one-click fix
   instead of making the user hand-edit the model box. */
function suggestedModelFrom(message) {
  const m = /models\/([A-Za-z0-9._-]+)\s+for the latest|use\s+models\/([A-Za-z0-9._-]+)|try\s+models\/([A-Za-z0-9._-]+)/i
    .exec(message || "");
  const found = m && (m[1] || m[2] || m[3]);
  if (!found) return null;
  return found === $("#ai-model").value.trim() ? null : found;
}

function aiErrorStatus(message, retry) {
  const box = $("#ai-status");
  box.replaceChildren(document.createTextNode(`⚠️ ${message}`));
  const better = suggestedModelFrom(message);
  if (!better) return;
  box.appendChild(document.createTextNode(" "));
  box.appendChild(el("button", {
    class: "chip-btn", type: "button", text: `Switch to ${better} and retry`,
    onclick: () => {
      $("#ai-model").value = better;
      localStorage.setItem(AI_KEYS[2], better);
      aiStatus("");
      if (typeof retry === "function") retry();
    },
  }));
}

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

/* A self-contained chat widget. Used twice: the Explain tab (grounded in the
   editor's code) and the Learn tab (grounded in the open lesson). */
function createChat({ root, endpoint, buildPayload, suggestions, emptyText, missingKeyText }) {
  const logEl = $(".chat-log", root);
  const inputEl = $(".chat-input", root);
  const statusEl = $(".chat-status", root);
  const sendBtn = $(".chat-send", root);
  const suggestEl = $(".chat-suggestions", root);

  let history = [];
  let busy = false;

  const setStatus = (text) => { statusEl.textContent = text || ""; };

  function setError(message) {
    statusEl.replaceChildren(document.createTextNode(`⚠️ ${message}`));
    const better = suggestedModelFrom(message);
    if (!better) return;
    statusEl.appendChild(document.createTextNode(" "));
    statusEl.appendChild(el("button", {
      class: "chip-btn", type: "button", text: `Switch to ${better} and retry`,
      onclick: () => {
        $("#ai-model").value = better;
        localStorage.setItem(AI_KEYS[2], better);
        setStatus("");
        send();
      },
    }));
  }

  function render() {
    logEl.replaceChildren();
    if (!history.length) {
      logEl.appendChild(el("p", { class: "muted small chat-empty", text: emptyText }));
    }
    for (const msg of history) {
      const bubble = el("div", { class: "chat-bubble" });
      if (msg.role === "user") bubble.appendChild(el("p", { text: msg.content }));
      else bubble.replaceChildren(...renderMarkdown(msg.content));
      logEl.appendChild(
        el("div", { class: `chat-msg ${msg.role}` },
          el("div", { class: "chat-role", text: msg.role === "user" ? "You" : "Tutor" }),
          bubble),
      );
    }
    if (busy) {
      logEl.appendChild(
        el("div", { class: "chat-msg assistant" },
          el("div", { class: "chat-role", text: "Tutor" }),
          el("div", { class: "chat-bubble thinking" },
            el("span", { class: "dots", text: "thinking…" })),
        ),
      );
    }
    logEl.scrollTop = logEl.scrollHeight;
  }

  function renderSuggestions(list) {
    suggestEl.replaceChildren(
      ...(list || []).map((q) => el("button", {
        class: "chip-btn", type: "button", text: q,
        onclick: () => { inputEl.value = q; autoGrow(inputEl); send(); },
      })),
    );
  }

  async function send() {
    if (busy) return;
    const question = inputEl.value.trim();
    if (!question) return;
    const settings = aiSettings();
    if (!settings.api_key) { setStatus(missingKeyText); return; }

    history.push({ role: "user", content: question });
    inputEl.value = "";
    autoGrow(inputEl);
    busy = true;
    sendBtn.disabled = true;
    setStatus("");
    render();

    try {
      const data = await api(endpoint, { ...buildPayload(), ...settings, messages: history });
      history.push({ role: "assistant", content: data.text });
    } catch (e) {
      // Keep the question in the box so it isn't lost on a failed request.
      history.pop();
      inputEl.value = question;
      autoGrow(inputEl);
      setError(e.message);
    } finally {
      busy = false;
      sendBtn.disabled = false;
      render();
    }
  }

  inputEl.addEventListener("input", () => autoGrow(inputEl));
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  $(".chat-form", root).addEventListener("submit", (e) => { e.preventDefault(); send(); });
  $(".chat-clear", root).addEventListener("click", () => { history = []; setStatus(""); render(); });

  renderSuggestions(suggestions);
  render();

  return {
    reset(newSuggestions) {
      history = [];
      setStatus("");
      if (newSuggestions) renderSuggestions(newSuggestions);
      render();
    },
    seed(msgs) { history = msgs.slice(); setStatus(""); render(); },
    /* Prefill the box and send — used by the per-example buttons. */
    ask(question) {
      inputEl.value = question;
      autoGrow(inputEl);
      root.scrollIntoView({ behavior: "smooth", block: "nearest" });
      send();
    },
    setSuggestions: renderSuggestions,
    setStatus,
  };
}

const codeChat = createChat({
  root: $("#code-chat"),
  endpoint: "/api/ai/chat",
  buildPayload: () => ({ code: codeEl.value.trim() }),
  suggestions: [
    "Explain line by line",
    "What would break in production?",
    "How would I make this faster?",
    "What interview questions come from this?",
    "Rewrite this the idiomatic way",
  ],
  emptyText: "No questions yet. Ask anything about the code above — or run a deep-dive first, then dig into it.",
  missingKeyText: "⚠️ Add your API key in the box above first.",
});


/* ---------------------------------------------------------------- learn */
const LESSON_TITLES = {};
let lessonsCache = null;
let currentLessonId = null;

/* Suggested questions tailored to the lesson being read. */
function lessonSuggestions(lesson) {
  const base = [
    "Explain this more simply",
    "Show me another example",
    "What do people get wrong here?",
    "Quiz me on this topic",
  ];
  const firstQ = (lesson.interview_questions || [])[0];
  if (firstQ && firstQ.q) base.push(`Interview: ${firstQ.q}`);
  return base;
}

const lessonChat = createChat({
  root: $("#lesson-chat"),
  endpoint: "/api/ai/lesson",
  buildPayload: () => ({ lesson_id: currentLessonId }),
  suggestions: [],
  emptyText: "Stuck on something in this lesson? Ask here — the tutor can see the whole lesson, its examples and its interview questions.",
  missingKeyText: "⚠️ Add your API key in the AI deep-dive box on the Explain tab first.",
});

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
  // Each lesson gets a fresh conversation with its own suggested questions.
  if (currentLessonId !== id) {
    currentLessonId = id;
    lessonChat.reset(lessonSuggestions(lesson));
  }
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
          el("button", {
            class: "btn",
            text: "👁 Visualize",
            onclick: () => {
              codeEl.value = sec.code;
              updateGutter();
              showTab("explain");
              viz.open(sec.code);
            },
          }),
          el("button", {
            class: "btn",
            text: "💬 Ask about this example",
            onclick: () => lessonChat.ask(
              `About the "${sec.heading}" example in this lesson — walk me through what happens and why.`),
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
          el("div", { class: "a" },
            el("p", { text: iq.a }),
            el("button", {
              class: "chip-btn", type: "button", text: "💬 Go deeper on this",
              onclick: () => lessonChat.ask(
                `Interview question from this lesson: "${iq.q}"\n\n` +
                "Go deeper than the short answer — what follow-ups would an interviewer ask, " +
                "and what would a strong answer include?"),
            }),
          ),
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
        // Missing a question is exactly when you want the lesson behind it.
        q.lesson ? el("div", { class: "quiz-actions" },
          el("button", {
            class: "lesson-link",
            text: `→ Review the lesson: ${LESSON_TITLES[q.lesson] || q.lesson}`,
            onclick: () => openLesson(q.lesson),
          }),
          // "What does this print?" is best answered by watching it print.
          q.code ? el("button", {
            class: "chip-btn", type: "button", text: "👁 Watch it run",
            onclick: () => {
              codeEl.value = q.code;
              updateGutter();
              showTab("explain");
              viz.open(q.code);
            },
          }) : null,
          el("button", {
            class: "chip-btn", type: "button", text: "💬 Ask the tutor why",
            onclick: () => {
              openLesson(q.lesson);
              lessonChat.ask(
                `Quiz question: ${q.question}\n` +
                (q.code ? "```python\n" + q.code + "\n```\n" : "") +
                `I answered "${q.options[idx]}". The correct answer is ` +
                `"${q.options[q.answer]}".\n\n` +
                (correct
                  ? "I got it right — explain why the other options are wrong so I really understand it."
                  : "Explain why my answer is wrong and how to reason about this next time."));
            },
          }),
        ) : null,
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

/* ---------------------------------------------------------- visualizer */
/* Renders the /api/trace recording: a step slider driving a highlighted
   source line, the call stack, and the heap. Aliasing is the money shot —
   two names holding the same {t:"ref", id} get the same colour and the same
   object box, so "b = a" visibly shares instead of copying. */
const viz = (() => {
  const card = $("#viz-card");
  if (!card) return { open: () => {} };

  const statusEl = $("#viz-status");
  const noteEl = $("#viz-note");
  const bodyEl = $("#viz-body");
  const sourceEl = $("#viz-source");
  const framesEl = $("#viz-frames");
  const heapEl = $("#viz-heap");
  const stdoutEl = $("#viz-stdout");
  const sliderEl = $("#viz-slider");
  const counterEl = $("#viz-counter");
  const playBtn = $("#viz-play");

  let steps = [];
  let lines = [];
  let index = 0;
  let timer = null;
  let colours = new Map();

  /* Stable colour per heap id, so the same object keeps its colour as you step. */
  const PALETTE = ["#7aa2f7", "#9ece6a", "#e0af68", "#bb9af7", "#7dcfff", "#f7768e", "#73daca"];
  function colourFor(id) {
    if (!colours.has(id)) colours.set(id, PALETTE[colours.size % PALETTE.length]);
    return colours.get(id);
  }

  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
    playBtn.textContent = "▶ Play";
  }

  function renderValue(v) {
    if (!v) return el("span", { class: "viz-val", text: "—" });
    if (v.t === "prim") return el("span", { class: "viz-prim", text: v.v });
    const colour = colourFor(v.id);
    const chip = el("span", { class: "viz-ref", text: "→" });
    chip.style.background = colour;
    chip.title = `object #${v.id}`;
    return chip;
  }

  function renderObject(id, entry) {
    const colour = colourFor(id);
    const box = el("div", { class: "viz-obj" });
    box.style.borderLeftColor = colour;
    const head = el("div", { class: "viz-obj-head" });
    const dot = el("span", { class: "viz-dot" });
    dot.style.background = colour;
    head.appendChild(dot);
    head.appendChild(el("span", { class: "viz-obj-type", text: entry.t }));
    box.appendChild(head);

    const items = el("div", { class: "viz-obj-body" });
    if (entry.kind === "seq" && Array.isArray(entry.v)) {
      entry.v.forEach((item, i) => {
        const cell = el("div", { class: "viz-cell" },
          el("span", { class: "viz-idx", text: String(i) }));
        cell.appendChild(renderValue(item));
        items.appendChild(cell);
      });
      if (entry.more) items.appendChild(el("div", { class: "viz-more", text: `+${entry.more} more` }));
    } else if (entry.kind === "map" && Array.isArray(entry.v)) {
      entry.v.forEach(([k, item]) => {
        const cell = el("div", { class: "viz-cell" },
          el("span", { class: "viz-idx", text: k }));
        cell.appendChild(renderValue(item));
        items.appendChild(cell);
      });
      if (entry.more) items.appendChild(el("div", { class: "viz-more", text: `+${entry.more} more` }));
    } else {
      items.appendChild(el("span", { class: "viz-prim", text: String(entry.v) }));
    }
    box.appendChild(items);
    return box;
  }

  function show(i) {
    if (!steps.length) return;
    index = Math.max(0, Math.min(i, steps.length - 1));
    const step = steps[index];
    sliderEl.value = String(index);
    counterEl.textContent = `Step ${index + 1} / ${steps.length}`;

    /* source with the current line highlighted */
    sourceEl.textContent = "";
    lines.forEach((text, n) => {
      const lineNo = n + 1;
      const row = el("div", { class: "viz-line" + (lineNo === step.line ? " active" : "") });
      row.appendChild(el("span", { class: "viz-lineno", text: String(lineNo) }));
      row.appendChild(el("span", { class: "viz-linetext", text: text || " " }));
      sourceEl.appendChild(row);
    });
    const active = sourceEl.querySelector(".viz-line.active");
    if (active) active.scrollIntoView({ block: "nearest" });

    /* event badge */
    let badge = "";
    if (step.event === "return") badge = "returned " + (step.returned ? step.returned.v || "→" : "");
    if (step.event === "exception") badge = "💥 " + (step.raised || "exception");
    statusEl.textContent = badge ? `Line ${step.line} — ${badge}` : `Line ${step.line}`;
    statusEl.className = "muted small" + (step.event === "exception" ? " viz-err" : "");

    /* frames: innermost last, matching how a traceback reads */
    framesEl.textContent = "";
    step.stack.forEach((frame, depth) => {
      const isTop = depth === step.stack.length - 1;
      const box = el("div", { class: "viz-frame" + (isTop ? " current" : "") });
      box.appendChild(el("div", { class: "viz-frame-name", text: frame.func }));
      if (!frame.locals.length) {
        box.appendChild(el("div", { class: "viz-empty", text: "no variables yet" }));
      }
      const addRow = (name, value, extraClass) => {
        const row = el("div", { class: "viz-var" + (extraClass ? " " + extraClass : "") },
          el("span", { class: "viz-varname", text: name }));
        row.appendChild(renderValue(value));
        if (value && value.t === "ref") {
          const entry = step.heap[value.id];
          row.appendChild(el("span", { class: "viz-hint", text: entry ? entry.t : "" }));
        } else {
          row.appendChild(el("span", { class: "viz-hint", text: "" }));
        }
        box.appendChild(row);
      };
      frame.locals.forEach(([name, value]) => addRow(name, value));
      /* Module-level names the function reads — otherwise the panel looks empty
         even though the code clearly uses them. */
      if (frame.globals && frame.globals.length) {
        box.appendChild(el("div", { class: "viz-scope-label", text: "from module scope" }));
        frame.globals.forEach(([name, value]) => addRow(name, value, "is-global"));
      }
      framesEl.appendChild(box);
    });

    /* heap, plus an explicit note when two names share one object */
    heapEl.textContent = "";
    const ids = Object.keys(step.heap);
    if (!ids.length) heapEl.appendChild(el("div", { class: "viz-empty", text: "no objects yet" }));
    ids.forEach((id) => heapEl.appendChild(renderObject(id, step.heap[id])));

    const names = {};
    step.stack.forEach((f) => f.locals.forEach(([n, v]) => {
      if (v && v.t === "ref") (names[v.id] = names[v.id] || []).push(n);
    }));
    const shared = Object.entries(names).filter(([, ns]) => ns.length > 1);
    if (shared.length) {
      const msg = shared.map(([, ns]) => ns.join(" and ")).join("; ");
      heapEl.appendChild(el("div", { class: "viz-alias", text:
        `${msg} point at the same object — changing one changes the other.` }));
    }

    stdoutEl.textContent = step.stdoutSoFar || "";
  }

  function bind() {
    $("#viz-first").onclick = () => { stop(); show(0); };
    $("#viz-prev").onclick = () => { stop(); show(index - 1); };
    $("#viz-next").onclick = () => { stop(); show(index + 1); };
    $("#viz-last").onclick = () => { stop(); show(steps.length - 1); };
    sliderEl.oninput = () => { stop(); show(Number(sliderEl.value)); };
    playBtn.onclick = () => {
      if (timer) return stop();
      if (index >= steps.length - 1) show(0);
      playBtn.textContent = "⏸ Pause";
      timer = setInterval(() => {
        if (index >= steps.length - 1) return stop();
        show(index + 1);
      }, 600);
    };
    $("#viz-close").onclick = () => { stop(); card.classList.add("hidden"); };
    $("#viz-ask").onclick = () => {
      const step = steps[index];
      if (!step) return;
      const frame = step.stack[step.stack.length - 1];
      const vars = frame.locals.map(([n, v]) =>
        `${n} = ${v.t === "prim" ? v.v : "object #" + v.id}`).join(", ");
      showTab("explain");
      codeChat.ask(
        `While stepping through this code, at step ${index + 1} we are on line ${step.line} ` +
        `inside ${frame.func}, where ${vars || "no variables are set yet"}. ` +
        `Explain what this line does and why the variables look like this.`);
    };
    /* arrow keys, but only when the visualizer is actually on screen */
    document.addEventListener("keydown", (e) => {
      if (card.classList.contains("hidden") || !steps.length) return;
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      if (typing) return;
      if (e.key === "ArrowRight") { stop(); show(index + 1); e.preventDefault(); }
      if (e.key === "ArrowLeft") { stop(); show(index - 1); e.preventDefault(); }
    });
  }

  async function open(code) {
    card.classList.remove("hidden");
    card.scrollIntoView({ behavior: "smooth", block: "start" });
    bodyEl.classList.add("hidden");
    noteEl.classList.add("hidden");
    statusEl.textContent = "Tracing…";
    stop();
    colours = new Map();

    let data;
    try {
      data = await api("/api/trace", { code });
    } catch (err) {
      statusEl.textContent = `⚠️ ${err.message}`;
      return;
    }

    steps = data.steps || [];
    lines = code.split("\n");

    /* stdout is captured for the whole run; approximate "output so far" by
       revealing it proportionally as you step, so Play feels alive. */
    const outLines = (data.stdout || "").split("\n").filter((l) => l !== "");
    steps.forEach((s, i) => {
      const shown = Math.ceil(((i + 1) / steps.length) * outLines.length);
      s.stdoutSoFar = outLines.slice(0, shown).join("\n");
    });

    const bits = [];
    if (data.error) bits.push(`💥 ${data.error}`);
    if (data.note) bits.push(data.note);
    if (bits.length) {
      noteEl.textContent = bits.join("  •  ");
      noteEl.classList.remove("hidden");
    }

    if (!steps.length) {
      statusEl.textContent = data.error ? "" : "Nothing to step through.";
      return;
    }

    sliderEl.max = String(steps.length - 1);
    bodyEl.classList.remove("hidden");
    show(0);
  }

  bind();
  return { open };
})();

$("#btn-visualize").addEventListener("click", () => {
  const code = codeEl.value.trim();
  if (!code) return;
  viz.open(code);
});
