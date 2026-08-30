"""Static code-review checks: bugs, smells, performance and style hints.

Each check walks the AST and yields Finding dicts:
  {id, title, severity, line, what, why, fix, lesson}
Severities: bug > security > warning > perf > style > hint
"""

from __future__ import annotations

import ast
import builtins

BUILTIN_NAMES = {n for n in dir(builtins) if not n.startswith("_")}

SEVERITY_ORDER = {"bug": 0, "security": 1, "warning": 2, "perf": 3, "style": 4, "hint": 5}


class Finding(dict):
    pass


def _finding(id_, title, severity, line, what, why, fix, lesson=None):
    return Finding(id=id_, title=title, severity=severity, line=line,
                   what=what, why=why, fix=fix, lesson=lesson)


MUTABLE_NODES = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)
MUTABLE_CALLS = {"list", "dict", "set", "bytearray", "defaultdict", "Counter", "OrderedDict"}


def _iter_function_defs(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _loop_target_names(node: ast.For) -> set[str]:
    names = set()
    for n in ast.walk(node.target):
        if isinstance(n, ast.Name):
            names.add(n.id)
    return names


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_mutable_default(tree):
    for fn in _iter_function_defs(tree):
        defaults = [d for d in fn.args.defaults if d is not None]
        defaults += [d for d in fn.args.kw_defaults if d is not None]
        for d in defaults:
            is_mutable = isinstance(d, MUTABLE_NODES) or (
                isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                and d.func.id in MUTABLE_CALLS)
            if is_mutable:
                yield _finding(
                    "mutable_default",
                    f"Mutable default argument in {fn.name}()",
                    "bug", d.lineno,
                    f"The parameter default is a mutable object created once, when the def runs — "
                    f"not on every call. All calls that use the default share the SAME object.",
                    "This is Python gotcha #1 in interviews: mutations from one call leak into the "
                    "next call's 'default'. Immutables (int, str, tuple, None) are safe because they "
                    "cannot be changed.",
                    f"def {fn.name}(..., items=None):\n    if items is None:\n        items = []  # fresh object per call",
                    lesson="functions",
                )


def check_bare_except(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            yield _finding(
                "bare_except",
                "Bare except: catches everything",
                "warning", node.lineno,
                "A bare except catches ALL exceptions — including KeyboardInterrupt (Ctrl+C), "
                "SystemExit and genuine bugs like NameError/TypeError.",
                "That hides real errors and makes Ctrl+C 'uncatchable' in practice. Catch the "
                "specific exception you expect, or at minimum 'Exception' which excludes the "
                "control-flow ones.",
                "try:\n    risky()\nexcept ValueError as e:   # specific\n    handle(e)\n# or: except Exception as e:  # at least exclude KeyboardInterrupt/SystemExit",
                lesson="errors",
            )


def check_swallows_exception(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body = [s for s in node.body if not (isinstance(s, ast.Expr)
                 and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
        silent = all(isinstance(s, (ast.Pass,)) or (isinstance(s, ast.Expr)
                     and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis)
                     for s in body)
        if silent and len(body) <= 1:
            yield _finding(
                "swallow_exception",
                "Exception silently swallowed (except: pass)",
                "warning", node.lineno,
                "The handler does nothing, so failures vanish without a trace and debugging "
                "becomes guesswork.",
                "If you truly must ignore an error, say so loudly: log it or add a comment "
                "explaining why silence is safe. Silent excepts are where bugs hide for months.",
                "except KeyError as e:\n    logger.warning(\"missing key, using default: %s\", e)",
                lesson="errors",
            )


def check_eq_none(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        ops = {type(o) for o in node.ops}
        comparators = [node.left, *node.comparators]
        if ({ast.Eq, ast.NotEq} & ops) and any(
                isinstance(c, ast.Constant) and c.value is None for c in comparators):
            yield _finding(
                "eq_none",
                "Comparing to None with == / !=",
                "style", node.lineno,
                "== asks the object whether it equals None; 'is' asks whether it IS the None "
                "object. There is exactly one None, so identity is the precise question.",
                "PEP 8 requires 'is None' / 'is not None': it is faster (no __eq__ call), cannot "
                "be fooled by custom __eq__ implementations, and communicates intent.",
                "if result is None:      # instead of result == None\n    ...\nif result is not None:  # instead of result != None",
                lesson="mutability",
            )


def check_is_literal(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        ops = {type(o) for o in node.ops}
        comparators = [node.left, *node.comparators]
        if ({ast.Is, ast.IsNot} & ops) and any(
                isinstance(c, ast.Constant) and isinstance(c.value, (int, float, str, bytes))
                for c in comparators):
            yield _finding(
                "is_literal",
                "'is' compared against a literal value",
                "warning", node.lineno,
                "'is' compares object identity, but small ints and short strings are cached by "
                "CPython — so 'x is 5' may work in testing and break later.",
                "Identity for value comparison is an implementation detail, not a contract. "
                "Use == for values; reserve 'is' for singletons like None/True/False.",
                "if x == 256:   # value comparison\n    ...\nif x is None:  # identity is correct for singletons",
                lesson="mutability",
            )


def check_type_identity(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or ast.Eq not in {type(o) for o in node.ops}:
            continue
        for c in [node.left, *node.comparators]:
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "type":
                yield _finding(
                    "type_identity",
                    "type(x) == ... instead of isinstance()",
                    "style", node.lineno,
                    "Comparing exact types rejects subclasses and defeats polymorphism.",
                    "isinstance() accepts subclasses and tuples of types, which is what you almost "
                    "always want in object-oriented code.",
                    "if isinstance(x, (int, float)):   # subclass-friendly\n    ...",
                    lesson="oop",
                )


def check_range_len(tree):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        it = node.iter
        if (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"
                and it.args and isinstance(it.args[0], ast.Call)
                and isinstance(it.args[0].func, ast.Name) and it.args[0].func.id == "len"):
            seq = ast.unparse(it.args[0].args[0]) if it.args[0].args else "..."
            yield _finding(
                "range_len",
                "for i in range(len(...)) instead of enumerate()",
                "style", node.lineno,
                "Looping over indices to then index the sequence twice is the C translation "
                "pattern; Python iterates items directly.",
                "'for i, item in enumerate(seq)' is cleaner, avoids off-by-one bugs, and signals "
                "real Python fluency — interviewers notice it.",
                f"for i, item in enumerate({seq}):\n    print(i, item)",
                lesson="loops",
            )


def check_eq_bool(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if {ast.Eq, ast.NotEq} & {type(o) for o in node.ops}:
            comparators = [node.left, *node.comparators]
            if any(isinstance(c, ast.Constant) and isinstance(c.value, bool) for c in comparators):
                yield _finding(
                    "eq_bool",
                    "Comparing with True/False using ==",
                    "style", node.lineno,
                    "Truthy/falsy evaluation is idiomatic Python: 'if flag:' already means "
                    "'if flag is truthy:'.",
                    "Redundant boolean comparisons add noise. Truthiness works for any object "
                    "(empty containers, 0, None are falsy). Use 'is' only if you must "
                    "distinguish False from 0/None.",
                    "if flag:          # instead of flag == True\n    ...\nif not items:      # instead of len(items) == 0\n    ...",
                    lesson="control_flow",
                )


def check_open_without_with(tree):
    withs = {id(n) for n in ast.walk(tree) if isinstance(n, (ast.With, ast.AsyncWith))}
    with_descendants = set()
    for w in ast.walk(tree):
        if isinstance(w, (ast.With, ast.AsyncWith)):
            for sub in ast.walk(w):
                with_descendants.add(id(sub))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            if id(node) not in with_descendants:
                yield _finding(
                    "open_without_with",
                    "open() without a with block",
                    "warning", node.lineno,
                    "Files opened manually stay open until garbage collection — on some platforms "
                    "that means data loss if the process exits before buffers flush.",
                    "The with statement is the guaranteed-cleanup pattern: __exit__ closes the file "
                    "even if an exception is raised inside the block.",
                    "with open(\"data.txt\") as f:\n    text = f.read()\n# f is closed here, even on errors",
                    lesson="files",
                )


def check_mutable_class_attr(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, MUTABLE_NODES):
                names = ", ".join(ast.unparse(t) for t in stmt.targets)
                yield _finding(
                    "mutable_class_attr",
                    f"Mutable class attribute '{names}' shared by all instances",
                    "warning", stmt.lineno,
                    "A list/dict/set defined in the class body lives on the CLASS, so every "
                    "instance reads and writes the same object.",
                    "This is usually a bug: 'self.items.append(...)' mutates the shared list for "
                    "ALL instances. Assign mutable state in __init__ instead.",
                    "class Cart:\n    def __init__(self):\n        self.items = []   # one per instance\n\n    # class-level is fine for CONSTANTS (e.g. MAX_SIZE = 10)",
                    lesson="oop",
                )


def check_late_binding(tree):
    for for_node in ast.walk(tree):
        if not isinstance(for_node, ast.For):
            continue
        targets = _loop_target_names(for_node)
        if not targets:
            continue
        for sub in ast.walk(for_node):
            if sub is for_node:
                continue
            if isinstance(sub, ast.Lambda):
                params = {a.arg for a in sub.args.args + sub.args.kwonlyargs}
                if sub.args.vararg:
                    params.add(sub.args.vararg.arg)
                if sub.args.kwarg:
                    params.add(sub.args.kwarg.arg)
                local = params | {n.id for n in ast.walk(sub)
                                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
                loaded = {n.id for n in ast.walk(sub)
                          if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
                free = loaded - local
                if free & targets:
                    yield _finding(
                        "late_binding",
                        "Closure captures the loop variable by reference (late binding)",
                        "warning", sub.lineno,
                        "The function body looks up the loop variable when CALLED, not when "
                        "defined — after the loop ends, every function sees the final value.",
                        "All the closures share one variable. Fix by binding the current value as "
                        "a default argument (evaluated at definition time) — or better, name it: "
                        "def make_cb(value): return lambda: value.",
                        "callbacks = []\nfor i in range(3):\n    callbacks.append(lambda i=i: i)  # i=i captures now\nprint([c() for c in callbacks])  # [0, 1, 2]",
                        lesson="scoping",
                    )
                    break  # one finding per loop


def check_string_concat_in_loop(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.AugAssign) and isinstance(sub.op, ast.Add) \
                    and isinstance(sub.target, ast.Name):
                name = sub.target.id
                yield _finding(
                    "string_concat_loop",
                    f"String built with += inside a loop ('{name} += ...')",
                    "perf", sub.lineno,
                    "Strings are immutable, so each += builds a brand-new string and copies "
                    "everything so far — O(n²) overall.",
                    "Collect pieces in a list and ''.join(...) once — the standard idiom that "
                    "interviewers expect for building strings efficiently.",
                    f"parts = []\nfor item in ...:\n    parts.append(str(item))\ntext = \"\".join(parts)",
                    lesson="collections",
                )
                break


def check_dangerous_calls(tree):
    risky = {"eval": "arbitrary code execution from strings",
             "exec": "arbitrary code execution from strings",
             "__import__": "dynamic imports from untrusted input",
             }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in risky:
            yield _finding(
                "dangerous_call",
                f"{node.func.id}() — {risky[node.func.id]}",
                "security", node.lineno,
                f"{node.func.id}() executes Python code contained in a string at runtime.",
                "If any part of that string can be influenced by user input, an attacker can run "
                "arbitrary code. Prefer explicit parsing (int(), json.loads(), ast.literal_eval "
                "for literal data structures).",
                "import ast\nobj = ast.literal_eval(user_string)   # safe for literals\n# json.loads() for JSON data",
                lesson=None,
            )


def check_shadow_builtins(tree):
    shadowed = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name) and n.id in BUILTIN_NAMES:
                        shadowed.append((n.id, node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in BUILTIN_NAMES:
            shadowed.append((node.name, node.lineno))
        elif isinstance(node, ast.For):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name) and n.id in BUILTIN_NAMES:
                    shadowed.append((n.id, node.lineno))
    seen = set()
    for name, line in shadowed:
        if name in seen:
            continue
        seen.add(name)
        yield _finding(
            "shadow_builtin",
            f"'{name}' shadows a Python builtin",
            "style", line,
            f"You reused the name of the builtin {name}() — after this line, calls to "
            f"{name}(...) hit YOUR object instead.",
            "Classic examples: list = [], sum = 0, max = values[0]. The bug appears lines later "
            "with 'TypeError: 'int' object is not callable'. Use descriptive names instead.",
            f"total = 0        # instead of: sum = 0\nitems = []       # instead of: list = []",
            lesson=None,
        )


def check_unused_imports(tree):
    imported: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported[name] = node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and not any(a.name == "*" for a in node.names):
            for alias in node.names:
                name = alias.asname or alias.name
                imported[name] = node.lineno
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    # attribute roots count as usage: import os.path -> binds os
    for name, line in sorted(imported.items(), key=lambda kv: kv[1]):
        if name not in used:
            yield _finding(
                "unused_import",
                f"Unused import '{name}'",
                "style", line,
                f"'{name}' is imported but never referenced — dead code left behind.",
                "Unused imports slow startup slightly, clutter the dependency picture, and often "
                "signal refactoring leftovers. Remove them or comment why they are kept.",
                "# delete the line, or:\nimport json  # noqa: F401  (kept for re-export)",
                lesson="modules",
            )


def check_unused_locals(tree):
    for fn in _iter_function_defs(tree):
        params = {a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs}
        if fn.args.vararg:
            params.add(fn.args.vararg.arg)
        if fn.args.kwarg:
            params.add(fn.args.kwarg.arg)
        stored: dict[str, int] = {}
        loaded = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    stored.setdefault(node.id, node.lineno)
                else:
                    loaded.add(node.id)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                loaded.update(node.names)
        for name, line in stored.items():
            if name not in loaded and name not in params and not name.startswith("_"):
                yield _finding(
                    "unused_local",
                    f"Variable '{name}' is assigned but never used in {fn.name}()",
                    "hint", line,
                    f"'{name}' gets a value that nothing ever reads.",
                    "Dead assignments often mean forgotten logic. If the value is a call whose "
                    "side effect you need, call it without assigning; otherwise delete the line. "
                    "(Heuristic check — verify before acting.)",
                    f"# if you need the side effect only:\ndo_work()      # not: result = do_work()\n# if intentional, signal it: _ignored = ...",
                    lesson=None,
                )


def check_missing_docstrings(tree):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and not node.name.startswith("_") and ast.get_docstring(node) is None:
            kind = "function" if not isinstance(node, ast.ClassDef) else "class"
            yield _finding(
                "missing_docstring",
                f"Public {kind} '{node.name}' has no docstring",
                "hint", node.lineno,
                "Docstrings are what help(), IDEs and AI tools read to understand your API.",
                "One line stating what it does and what it returns is enough. This matters twice "
                "as much when AI writes your code — the docstring is how you review it later.",
                f"def {node.name}(x):\n    \"\"\"Explain what this does and what it returns.\"\"\"",
                lesson="functions",
            )


def check_long_function(tree):
    for fn in _iter_function_defs(tree):
        length = (fn.end_lineno or fn.lineno) - fn.lineno
        if length > 60:
            yield _finding(
                "long_function",
                f"{fn.name}() is {length} lines long",
                "hint", fn.lineno,
                "Long functions are hard to test, review and reuse.",
                "Break the function into helpers with names that document each step — 'write "
                "code that reads like the problem statement'.",
                "def process_order(order):\n    validate(order)\n    priced = apply_pricing(order)\n    return persist(priced)",
                lesson="functions",
            )


def check_too_many_args(tree):
    for fn in _iter_function_defs(tree):
        count = len(fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs)
        if count > 6:
            yield _finding(
                "too_many_args",
                f"{fn.name}() takes {count} parameters",
                "hint", fn.lineno,
                "Long parameter lists usually mean a missing object: the parameters belong "
                "together conceptually.",
                "Group related values into a dataclass/NamedTuple, or accept them as keyword "
                "arguments to make call sites self-documenting.",
                "@dataclass\nclass Config:\n    host: str\n    port: int\n    timeout: float\n\ndef connect(config: Config): ...",
                lesson="functions",
            )


def check_deep_nesting(tree):
    def walk_depth(body, depth):
        worst = (depth, None)
        for node in body:
            bodies = []
            if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
                bodies = [node.body] + ([node.orelse] if node.orelse else [])
            elif isinstance(node, ast.Try):
                bodies = [node.body] + [h.body for h in node.handlers]
            for b in bodies:
                worst = max(worst, walk_depth(b, depth + 1))
        return worst

    depth, node = walk_depth(tree.body, 0)
    if node is not None and depth > 4:
        yield _finding(
            "deep_nesting",
            f"Code nested {depth} levels deep",
            "hint", getattr(node, "lineno", 1) or 1,
            "Deeply nested blocks ('arrow code') are the top readability killer and hide edge "
            "cases.",
            "Flatten with early returns ('guard clauses'), continue/break, or extract the inner "
            "block into a helper function.",
            "def process(item):\n    if item is None:\n        return          # guard clause\n    if not item.valid:\n        return\n    do_work(item)       # main path stays at top level",
            lesson="control_flow",
        )


def check_assert_for_validation(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            yield _finding(
                "assert_validation",
                "assert used for a runtime check",
                "warning", node.lineno,
                "assert statements disappear when Python runs with optimizations (-O flag), so "
                "this check silently stops working in production.",
                "Use assert for tests and internal invariants; use explicit raises to validate "
                "inputs that come from users, files or networks.",
                "if price < 0:\n    raise ValueError(f\"price must be >= 0, got {price}\")",
                lesson="errors",
            )


def check_global_statement(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            yield _finding(
                "global_statement",
                f"'{type(node).__name__}' statement used",
                "style", node.lineno,
                "Functions that mutate hidden shared state are hard to test and reason about — "
                "the change is invisible at the call site.",
                "Prefer passing the value in and returning the new value out. Reserve global "
                "state for true singletons (config, caches).",
                "def add_item(item, items):\n    items.append(item)\n    return items   # explicit data flow",
                lesson="scoping",
            )


def check_fstring_no_placeholder(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr) and not any(
                isinstance(v, ast.FormattedValue) for v in node.values):
            yield _finding(
                "fstring_no_placeholder",
                "f-string without any placeholders",
                "hint", node.lineno,
                "The f prefix does nothing here — there are no {expressions} to interpolate.",
                "Drop the f prefix for plain strings, or add the interpolation you intended.",
                "msg = \"plain string\"        # not: msg = f\"plain string\"",
                lesson="strings",
            )


ALL_CHECKS = [
    check_mutable_default,
    check_bare_except,
    check_swallows_exception,
    check_eq_none,
    check_is_literal,
    check_type_identity,
    check_range_len,
    check_eq_bool,
    check_open_without_with,
    check_mutable_class_attr,
    check_late_binding,
    check_string_concat_in_loop,
    check_dangerous_calls,
    check_shadow_builtins,
    check_unused_imports,
    check_unused_locals,
    check_missing_docstrings,
    check_long_function,
    check_too_many_args,
    check_deep_nesting,
    check_assert_for_validation,
    check_global_statement,
    check_fstring_no_placeholder,
]


def review(tree: ast.AST) -> list[Finding]:
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        try:
            findings.extend(check(tree))
        except Exception:  # a broken check must never break the explainer
            continue
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["line"]))
    return findings
