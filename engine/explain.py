"""Builds a human step-by-step walkthrough of the code from its AST."""

from __future__ import annotations

import ast

MAX_DEPTH = 3          # how deep the outline recurses
MAX_BODY = 30          # skip outlining giant bodies


def _src_line(source_lines: list[str], node: ast.AST) -> str:
    line = getattr(node, "lineno", None)
    if line and 1 <= line <= len(source_lines):
        return source_lines[line - 1].strip()
    src = ast.unparse(node) if hasattr(ast, "unparse") else ""
    return src.splitlines()[0][:100] if src else "<expr>"


def _clip(text: str, n: int = 80) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def _fmt_args(node: ast.FunctionDef) -> str:
    a = node.args
    names = [arg.arg for arg in a.posonlyargs + a.args + a.kwonlyargs]
    if a.vararg:
        names.append(f"*{a.vararg.arg}")
    if a.kwarg:
        names.append(f"**{a.kwarg.arg}")
    return ", ".join(names)


def _describe(node: ast.AST, source_lines: list[str]) -> str:
    """One-sentence plain-English description of a statement."""
    if isinstance(node, ast.FunctionDef):
        kind = "method" if _in_class(node) else "function"
        defaults = len([d for d in node.args.defaults if d is not None])
        extra = []
        if node.decorator_list:
            extra.append(f"decorated with @{ast.unparse(node.decorator_list[0])}")
        if defaults:
            extra.append(f"{defaults} default value(s)")
        if node.args.vararg or node.args.kwarg:
            extra.append("*args/**kwargs")
        if node.returns:
            extra.append(f"declared return type {ast.unparse(node.returns)}")
        suffix = f" ({'; '.join(extra)})" if extra else ""
        doc = ast.get_docstring(node)
        docnote = f' — "{_clip(doc, 60)}"' if doc else ""
        return (f"Defines the {kind} {node.name}({_fmt_args(node)}){suffix}"
                f"{docnote}. The body below runs only when it is called.")
    if isinstance(node, ast.AsyncFunctionDef):
        return f"Defines async function {node.name}({_fmt_args(node)}) — a coroutine; it does nothing until awaited."
    if isinstance(node, ast.Return):
        if node.value is None:
            return "Exits the function returning None (no value given)."
        return f"Returns {_clip(ast.unparse(node.value))} to the caller and exits the function."
    if isinstance(node, ast.Assign):
        targets = ", ".join(ast.unparse(t) for t in node.targets)
        value = _clip(ast.unparse(node.value))
        if isinstance(node.value, (ast.ListComp, ast.DictComp, ast.SetComp)):
            return f"Builds {_clip(targets)} using a comprehension: {_clip(ast.unparse(node.value), 90)}."
        return f"Assigns {value} to {targets}."
    if isinstance(node, ast.AnnAssign):
        hint = ast.unparse(node.annotation)
        base = f"Declares {_clip(ast.unparse(node.target))} with a type hint '{hint}'"
        return base + (f" and sets it to {_clip(ast.unparse(node.value))}." if node.value else ".")
    if isinstance(node, ast.AugAssign):
        op = type(node.op).__name__.replace("Add", "+").replace("Sub", "-")
        return f"Updates {ast.unparse(node.target)} in place ({ast.unparse(node.target)} {op}= ...)."
    if isinstance(node, ast.Expr):
        v = node.value
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            return f'Docstring: "{_clip(v.value, 70)}" — documents the code for readers and help().'
        if isinstance(v, ast.Call):
            return f"Executes the call {_clip(ast.unparse(v), 90)}."
        return f"Evaluates {_clip(ast.unparse(v), 70)} (result is discarded)."
    if isinstance(node, ast.If):
        elifs = len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)
        has_else = bool(node.orelse) and not elifs
        parts = [f"Tests the condition {_clip(ast.unparse(node.test))}"]
        parts.append("and runs the first block when it is truthy")
        if elifs:
            parts.append(", with elif/else branches below")
        elif has_else:
            parts.append(", with an else branch below")
        return ". ".join(parts) + "."
    if isinstance(node, ast.For):
        target = ast.unparse(node.target)
        it = _clip(ast.unparse(node.iter), 60)
        return f"Loops over {it}, binding each item to {target}."
    if isinstance(node, ast.While):
        return f"Repeats the block while {_clip(ast.unparse(node.test))} stays true."
    if isinstance(node, ast.With):
        items = ", ".join(_clip(ast.unparse(i.context_expr), 40) for i in node.items)
        return f"Uses context manager(s) {items} — guarantees setup/cleanup (e.g. closing a file) around the block."
    if isinstance(node, ast.Try):
        names = []
        for h in node.handlers:
            names.append(ast.unparse(h.type) if h.type else "everything")
        extra = ""
        if node.finalbody:
            extra = " finally always runs"
        return f"Runs risky code and handles: {', '.join(names)}{extra}."
    if isinstance(node, ast.Raise):
        what = ast.unparse(node.exc) if node.exc else "the active exception"
        return f"Raises {_clip(what, 60)} — aborts normal flow to signal an error."
    if isinstance(node, ast.Import):
        return f"Imports module(s): {', '.join(a.name for a in node.names)}."
    if isinstance(node, ast.ImportFrom):
        names = ", ".join(a.name for a in node.names)
        return f"Imports {names} from the '{node.module}' module."
    if isinstance(node, ast.ClassDef):
        bases = f" (inherits from {', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
        doc = ast.get_docstring(node)
        docnote = f' — "{_clip(doc, 60)}"' if doc else ""
        return f"Defines class {node.name}{bases}{docnote}: a blueprint bundling data and behaviour."
    if isinstance(node, ast.Assert):
        return f"Asserts {_clip(ast.unparse(node.test))} — raises AssertionError if false."
    if isinstance(node, ast.Global):
        return f"Declares {', '.join(node.names)} as global so assignment updates the module-level variable."
    if isinstance(node, ast.Nonlocal):
        return f"Declares {', '.join(node.names)} as nonlocal (belonging to an enclosing function)."
    if isinstance(node, (ast.Break,)):
        return "Exits the innermost loop immediately."
    if isinstance(node, ast.Continue):
        return "Skips to the next iteration of the loop."
    if isinstance(node, ast.Pass):
        return "Does nothing — a placeholder to keep the block syntactically valid."
    if isinstance(node, ast.Delete):
        return "Deletes the given name(s) or attribute(s)."
    if isinstance(node, ast.Match):
        return f"Pattern-matches {_clip(ast.unparse(node.subject))} against the case patterns below (first match wins)."
    fallback = ast.unparse(node) if hasattr(ast, "unparse") else type(node).__name__
    return f"Executes: {_clip(fallback, 90)}"


def _in_class(node: ast.AST) -> bool:
    # Cheap check: functions defined directly inside a ClassDef body have no
    # parent pointers, so we rely on the outline walker passing context.
    return getattr(node, "_in_class", False)


def outline(tree: ast.Module, source: str) -> list[dict]:
    """Structured, indented summary of the program's statements."""
    source_lines = source.splitlines()
    steps: list[dict] = []

    def walk(body: list[ast.stmt], depth: int) -> None:
        if len(body) > MAX_BODY and depth > 0:
            return
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node._in_class = depth > 0 and _parent_is_class(body, node)
            steps.append({
                "line": getattr(node, "lineno", 0),
                "depth": depth,
                "code": _src_line(source_lines, node),
                "text": _describe(node, source_lines),
            })
            if depth >= MAX_DEPTH:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.For, ast.AsyncFor, ast.While, ast.With,
                                 ast.AsyncWith, ast.If)):
                walk(node.body, depth + 1)
                if isinstance(node, ast.If) and node.orelse:
                    walk(node.orelse, depth + 1)
                if isinstance(node, (ast.For, ast.AsyncFor, ast.While)) and node.orelse:
                    walk(node.orelse, depth + 1)
            elif isinstance(node, ast.Try):
                walk(node.body, depth + 1)
                for handler in node.handlers:
                    walk(handler.body, depth + 1)
                if node.orelse:
                    walk(node.orelse, depth + 1)
                if node.finalbody:
                    walk(node.finalbody, depth + 1)

    walk(tree.body, 0)
    return steps


def _parent_is_class(body: list[ast.stmt], node: ast.stmt) -> bool:
    # If we are outlining a ClassDef body, FunctionDef members are methods.
    # The walker calls walk() with the class body; detect via siblings.
    return any(isinstance(s, ast.FunctionDef) for s in body) and node in body


def stats(tree: ast.Module, source: str) -> dict:
    lines = source.splitlines()
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]

    functions = classes = loops = imports_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1
        elif isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            loops += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports_count += 1

    def max_depth(body: list[ast.stmt], d: int = 0) -> int:
        deepest = d
        for node in body:
            child_bodies: list[list[ast.stmt]] = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.If)):
                child_bodies = [node.body]
                if isinstance(node, ast.If) and node.orelse:
                    child_bodies.append(node.orelse)
            elif isinstance(node, ast.Try):
                child_bodies = [node.body] + [h.body for h in node.handlers]
            for b in child_bodies:
                deepest = max(deepest, max_depth(b, d + 1))
        return deepest

    return {
        "total_lines": len(lines),
        "code_lines": len(code_lines),
        "functions": functions,
        "classes": classes,
        "loops": loops,
        "imports": imports_count,
        "max_nesting": max_depth(tree.body),
    }


def summarize(analysis: dict) -> str:
    """One friendly paragraph describing what the code overall is/does."""
    s = analysis["stats"]
    constructs = [c["name"] for c in analysis["constructs"]]
    parts: list[str] = []

    shape = []
    if s["functions"]:
        shape.append(f"{s['functions']} function{'s' if s['functions'] != 1 else ''}")
    if s["classes"]:
        shape.append(f"{s['classes']} class{'es' if s['classes'] != 1 else ''}")
    if shape:
        parts.append(f"This {s['code_lines']}-line script defines " + " and ".join(shape) + ".")
    elif s["code_lines"] > 0:
        parts.append(f"This {s['code_lines']}-line script runs top to bottom as straight-line code.")

    highlight = []
    for name in constructs:
        for token in ("Comprehensions", "Generator", "Decorators", "context manager",
                      "f-strings", "yield", "async", "Dunder", "match / case"):
            if token.lower() in name.lower() and name not in highlight:
                highlight.append(name)
    if highlight:
        parts.append("Notable techniques: " + ", ".join(highlight[:4]) + ".")

    arch = analysis.get("architecture") or {}
    deps = arch.get("dependencies") or []
    if deps:
        parts.append("It builds on " + ", ".join(deps[:5])
                     + (f" (+{len(deps) - 5} more)" if len(deps) > 5 else "") + ".")
    entries = arch.get("entry_points") or []
    if entries:
        parts.append("Execution starts at " + ", ".join(f"{e}()" for e in entries[:3]) + ".")

    groups = analysis.get("finding_groups") or []
    findings = analysis.get("findings", [])
    if groups:
        # Report distinct problems, not raw hit count — 151 hits of 8 rules is 8 problems.
        top = ", ".join(
            g["title"] + (" \u00d7{}".format(g["count"]) if g["count"] > 1 else "")
            for g in groups[:3])
        more = f" (+{len(groups) - 3} more)" if len(groups) > 3 else ""
        parts.append(
            f"The review flagged {len(groups)} distinct issue(s) across {len(findings)} "
            f"location(s): {top}{more}.")
    else:
        parts.append("The automated review found no obvious issues.")

    return " ".join(parts)


# ---------------------------------------------------------------- architecture
# The step-by-step walkthrough answers "what happens next". On a 1000-line file
# it produces hundreds of flat steps and answers nothing about *why* the code is
# shaped the way it is. The helpers below build a structural map instead:
# components, the call graph, entry points and external dependencies — the
# evidence needed to explain why each part exists.

_DUNDER_ENTRY = "__main__"


def _qualname(stack: list[str], name: str) -> str:
    return ".".join([*stack, name])


def _calls_in(node: ast.AST) -> list[str]:
    """Names of things called inside a node (shallow, best-effort)."""
    out: list[str] = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        f = sub.func
        if isinstance(f, ast.Name):
            out.append(f.id)
        elif isinstance(f, ast.Attribute):
            # self.foo() -> foo ; mod.foo() -> mod.foo
            if isinstance(f.value, ast.Name):
                out.append(f.attr if f.value.id == "self" else f"{f.value.id}.{f.attr}")
            else:
                out.append(f.attr)
    return out


def _imported_names(tree: ast.Module) -> dict[str, str]:
    """Map bound name -> owning top-level module."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                bound[(a.asname or a.name).split(".")[0]] = a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                bound[a.asname or a.name] = node.module.split(".")[0]
    return bound


def _role_of(fn: ast.AST, calls: list[str], imports: dict[str, str]) -> str:
    """Best-effort one-word role, so the reader knows why a function exists."""
    name = getattr(fn, "name", "")
    lowered = name.lower()
    called_mods = {imports[c.split(".")[0]] for c in calls if c.split(".")[0] in imports}

    if isinstance(fn, ast.AsyncFunctionDef):
        prefix = "async "
    else:
        prefix = ""
    if any(isinstance(n, ast.Yield) or isinstance(n, ast.YieldFrom) for n in ast.walk(fn)):
        return prefix + "generator — produces values lazily"
    if lowered.startswith(("test_", "check_", "verify_")):
        return prefix + "test/validation"
    if lowered.startswith(("main", "run", "cli", "handle", "process")):
        return prefix + "orchestrator — coordinates other functions"
    if called_mods & {"json", "csv", "pickle", "yaml"}:
        return prefix + "serialisation"
    if called_mods & {"open", "pathlib", "os", "shutil", "io"} or "open" in calls:
        return prefix + "I/O — touches the filesystem"
    if called_mods & {"requests", "urllib", "httpx", "socket"}:
        return prefix + "network I/O"
    if called_mods & {"logging"}:
        return prefix + "logging/diagnostics"
    if lowered.startswith(("get_", "fetch_", "load_", "read_")):
        return prefix + "accessor — retrieves data"
    if lowered.startswith(("set_", "save_", "write_", "store_", "update_")):
        return prefix + "mutator — writes data"
    if lowered.startswith(("to_", "from_", "parse_", "format_", "convert_", "build_", "make_")):
        return prefix + "transformer — converts between shapes"
    if not calls:
        return prefix + "leaf helper — self-contained, calls nothing"
    return prefix + "helper"


def architecture(tree: ast.Module, source: str) -> dict:
    """A structural map of the program: components, call graph, entry points."""
    imports = _imported_names(tree)
    components: list[dict] = []
    functions: dict[str, dict] = {}

    def visit(body: list[ast.stmt], stack: list[str], owner: str | None) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                bases = [ast.unparse(b) for b in node.bases]
                decorators = [ast.unparse(d) for d in node.decorator_list]
                components.append({
                    "kind": "class",
                    "name": _qualname(stack, node.name),
                    "line": node.lineno,
                    "doc": (ast.get_docstring(node) or "").split("\n")[0][:120],
                    "bases": bases,
                    "decorators": decorators,
                    "members": [m.name for m in methods],
                    "why": _class_why(node, bases, decorators, methods),
                })
                visit(node.body, [*stack, node.name], node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = _calls_in(node)
                qn = _qualname(stack, node.name)
                functions[qn] = {
                    "kind": "method" if owner else "function",
                    "name": qn,
                    "short": node.name,
                    "line": node.lineno,
                    "owner": owner,
                    "doc": (ast.get_docstring(node) or "").split("\n")[0][:120],
                    "args": _fmt_args(node),
                    "calls": sorted({c for c in calls}),
                    "role": _role_of(node, calls, imports),
                    "callers": [],
                }
                visit(node.body, [*stack, node.name], owner)

    visit(tree.body, [], None)

    # Resolve callers using short names (best-effort: Python is dynamic).
    by_short: dict[str, list[str]] = {}
    for qn, info in functions.items():
        by_short.setdefault(info["short"], []).append(qn)
    for qn, info in functions.items():
        for callee in info["calls"]:
            for target in by_short.get(callee.split(".")[-1], []):
                if target != qn and qn not in functions[target]["callers"]:
                    functions[target]["callers"].append(qn)

    entry_points = _entry_points(tree, functions)
    for qn, info in functions.items():
        info["entry"] = qn in entry_points

    return {
        "components": components,
        "functions": [functions[k] for k in sorted(functions, key=lambda k: functions[k]["line"])],
        "entry_points": sorted(entry_points),
        "dependencies": sorted(set(imports.values())),
        "orphans": sorted(qn for qn, i in functions.items()
                          if not i["callers"] and not i["entry"] and not i["owner"]
                          and not i["short"].startswith("_")),
    }


def _class_why(node: ast.ClassDef, bases: list[str], decorators: list[str],
               methods: list) -> str:
    names = {m.name for m in methods}
    if any("dataclass" in d for d in decorators):
        return "A @dataclass — exists to carry structured data; the decorator generates __init__/__repr__/__eq__."
    if any(b.endswith("Enum") for b in bases):
        return "An Enum — a closed set of named constants, safer than bare strings."
    if any(b in {"Exception", "BaseException"} or b.endswith("Error") for b in bases):
        return "A custom exception — lets callers catch this specific failure instead of a broad except."
    if {"__enter__", "__exit__"} <= names:
        return "A context manager — guarantees setup/teardown even if the body raises."
    if {"__iter__"} <= names or {"__next__"} <= names:
        return "An iterator/iterable — lets the object be used directly in a for loop."
    if bases:
        return f"Extends {', '.join(bases)} — specialises existing behaviour rather than duplicating it."
    if not names - {"__init__"}:
        return "Mostly data with little behaviour — consider a @dataclass or NamedTuple."
    return "Bundles related state and the operations that act on it."


def _entry_points(tree: ast.Module, functions: dict) -> set[str]:
    """Where execution actually begins."""
    entries: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.If):
            test = ast.unparse(node.test)
            if "__name__" in test and _DUNDER_ENTRY in test:
                for called in _calls_in(node):
                    for qn, info in functions.items():
                        if info["short"] == called.split(".")[-1]:
                            entries.add(qn)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            for called in _calls_in(node):
                for qn, info in functions.items():
                    if info["short"] == called.split(".")[-1]:
                        entries.add(qn)
    return entries


def group_findings(findings: list[dict]) -> list[dict]:
    """Collapse repeated review hits into one entry per rule.

    On a large file the same rule can fire dozens of times; 151 findings is a
    wall, 8 rules with counts is a to-do list.
    """
    grouped: dict[str, dict] = {}
    for f in findings:
        key = f.get("id") or f.get("title")
        g = grouped.get(key)
        if g is None:
            grouped[key] = {
                **{k: f[k] for k in ("id", "severity", "what", "why", "fix", "lesson") if k in f},
                "title": f.get("title", ""),
                "count": 1,
                "lines": [f.get("line")],
            }
        else:
            g["count"] += 1
            g["lines"].append(f.get("line"))
    order = {"bug": 0, "warning": 1, "style": 2, "info": 3}
    out = sorted(grouped.values(),
                 key=lambda g: (order.get(g.get("severity"), 9), -g["count"]))
    for g in out:
        g["lines"] = sorted(l for l in g["lines"] if l is not None)
    return out
