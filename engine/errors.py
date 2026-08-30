"""Turns tracebacks / syntax errors into friendly, teachable explanations."""

from __future__ import annotations

import re

# exception name -> {what, causes[], fixes[]}
ERROR_KB: dict[str, dict] = {
    "NameError": dict(
        what="You used a name that Python has never seen defined.",
        causes=["Typo in the variable or function name",
                "Using a variable before it is assigned",
                "Referencing a name that only exists inside another function's scope"],
        fixes=["Check spelling (Python is case-sensitive: 'Name' != 'name')",
               "Make sure the assignment runs BEFORE the use",
               "Pass the value in as a parameter instead of reaching into another scope"],
    ),
    "UnboundLocalError": dict(
        what="A local variable was used before assignment — often surprising because a "
             "GLOBAL variable with the same name exists.",
        causes=["Assignment somewhere in the function makes the name local for the WHOLE "
                "function, so reading it earlier fails",
                "Modifying a global (x += 1) without 'global x'"],
        fixes=["Add a parameter or an early assignment before the first read",
               "If you really mean the global, declare 'global x' — though returning values "
               "is the cleaner design"],
    ),
    "TypeError": dict(
        what="An operation was applied to the wrong kind of object.",
        causes=["Mixing incompatible types ('1' + 1)",
                "Calling something that isn't callable — often a None",
                "Wrong number/type of arguments to a function",
                "Indexing with a string instead of an int (or vice versa)"],
        fixes=["print(type(x)) right before the failing line to see what you actually have",
               "Convert explicitly: int(x), str(x)",
               "Check for an accidental 'return' removal that left a function returning None"],
    ),
    "ValueError": dict(
        what="The type was right, but the VALUE is invalid.",
        causes=["int('abc')", "list.remove(x) when x is not present",
                "Invalid arguments like datetime(2026, 13, 1)"],
        fixes=["Validate or clean the input before converting",
               "Use try/except ValueError at the boundary where untrusted data enters",
               "Check membership with 'in' before remove/index"],
    ),
    "KeyError": dict(
        what="The dict has no entry for that key.",
        causes=["Typo or different case in the key",
                "Assuming a key exists in external/JSON data",
                "Using an unhashable or mutated key"],
        fixes=["Print the dict or use d.keys() to see what IS there",
               "Use d.get(key, default) when missing is expected",
               "Use collections.defaultdict(list) for accumulate patterns"],
    ),
    "IndexError": dict(
        what="You asked for a position that does not exist in the sequence.",
        causes=["Off-by-one: len(items) as an index instead of len(items) - 1",
                "Looping over the wrong length",
                "Assuming a list is non-empty"],
        fixes=["Remember: valid indexes are 0 .. len-1; -1 is the last item",
               "Prefer direct iteration (for item in items) over index math",
               "Guard with 'if items:' before items[0]"],
    ),
    "AttributeError": dict(
        what="The object has no such attribute or method.",
        causes=["Typo in the method name",
                "The object is None ('NoneType' object has no attribute ...)",
                "Confusing a module and a function, or str/bytes method mixups",
                "Circular import left the module half-initialized"],
        fixes=["When you see 'NoneType', find where the variable became None",
               "dir(obj) lists what the object actually has",
               "Check the import: 'import x' needs x.y, 'from x import y' binds y directly"],
    ),
    "ModuleNotFoundError": dict(
        what="Python cannot find the module you asked to import.",
        causes=["Package not installed in THIS environment (wrong venv is the #1 cause)",
                "Typo in the module name",
                "Your own file shadows a stdlib/library name (e.g. a file named json.py)"],
        fixes=["pip install <package> inside the activated venv",
               "Check 'which python' / sys.executable matches the venv you installed into",
               "Rename files that shadow installed packages"],
    ),
    "ImportError": dict(
        what="The module exists but the requested name inside it does not.",
        causes=["Typo in 'from package import name'",
                "Version mismatch — the name moved or was removed in a newer/older version",
                "Circular imports"],
        fixes=["Check the installed version: pip show <package>",
               "Read the package docs/changelog for the new import path",
               "Break circular imports by moving shared code to a third module"],
    ),
    "ZeroDivisionError": dict(
        what="A division or modulo by zero.",
        causes=["Denominator computed to 0 (often an empty total or count)",
                "Missing default for an average over an empty list"],
        fixes=["Check the denominator first: 'if n:' before dividing",
               "Decide what the result should be for empty input and return it explicitly"],
    ),
    "RecursionError": dict(
        what="A function called itself until the recursion limit (~1000) was hit.",
        causes=["Missing or unreachable base case",
                "Base case never triggered by the actual input",
                "Mutually recursive functions bouncing forever"],
        fixes=["Write down the base case FIRST and test it",
               "Print the arguments at entry to see the trajectory",
               "Convert to an iterative loop with an explicit stack for deep inputs"],
    ),
    "StopIteration": dict(
        what="next() was called on an exhausted iterator.",
        causes=["Calling next(gen) more times than the generator yields",
                "Manual iteration past the end instead of using a for loop"],
        fixes=["Use for loops — they handle StopIteration for you",
               "next(it, default) supplies a fallback"],
    ),
    "IndentationError": dict(
        what="The indentation is inconsistent or a block is empty.",
        causes=["Mixing tabs and spaces (looks aligned, isn't)",
                "A block with no statements after ':'",
                "Copy-pasted code at the wrong level"],
        fixes=["Use 4 spaces everywhere; configure the editor to expand tabs",
               "Add 'pass' if a block is intentionally empty",
               "Run the file through an autoformatter (black) to normalize"],
    ),
    "TabError": dict(
        what="Tabs and spaces are mixed inconsistently.",
        causes=["Editor inserting tabs while the file uses spaces (or vice versa)"],
        fixes=["Convert all indentation to 4 spaces (editor: 'convert indentation')",
               "Set .editorconfig or editor settings to spaces-only for Python"],
    ),
    "SyntaxError": dict(
        what="Python could not even parse the file — the code is not valid syntax.",
        causes=["Missing colon after def/if/for/while/class",
                "Unbalanced parentheses or quotes",
                "Using '=' (assignment) inside a condition instead of '=='",
                "Python 2 style 'print x' or keywords as variable names"],
        fixes=["Look at the line the caret points to — and the line ABOVE it (the error is "
               "often there)",
               "Count your brackets/quotes on that line",
               "Paste the file into an editor with Python syntax checking"],
    ),
    "OSError": dict(
        what="An operating-system level failure (file/dir/permission).",
        causes=["FileNotFoundError: the path does not exist",
                "PermissionError: no rights to read/write",
                "IsADirectoryError: expected a file, got a directory"],
        fixes=["Check existence with pathlib.Path(p).exists()",
               "Use absolute paths during debugging; print(os.getcwd()) to see where you are",
               "Handle the specific subclass (FileNotFoundError) rather than bare OSError"],
    ),
    "FileNotFoundError": dict(
        what="The file path could not be found.",
        causes=["Relative path resolved against the wrong working directory",
                "Typo or wrong file extension"],
        fixes=["print(os.getcwd()) and build paths with pathlib.Path(__file__).parent / 'data.csv'",
               "Verify the file exists at the exact path you pass"],
    ),
    "KeyboardInterrupt": dict(
        what="You pressed Ctrl+C — the interpreter was interrupted.",
        causes=["Manual interruption", "Long/infinite loop"],
        fixes=["If unexpected: look for a while loop with no progress toward its exit "
               "condition"],
    ),
    "RuntimeError": dict(
        what="A runtime condition failed that doesn't fit another exception class.",
        causes=["asyncio event-loop misuse ('no running event loop')",
                "Re-entering an iterator/generator incorrectly",
                "Library-specific state errors"],
        fixes=["Read the message — it usually names the exact state problem",
               "For asyncio: ensure asyncio.run() wraps your top-level coroutine"],
    ),
    "EOFError": dict(
        what="input() hit end-of-file with nothing to read.",
        causes=["Running with no stdin (piped/CI environment)",
                "Ctrl+D / Ctrl+Z pressed at the prompt"],
        fixes=["Provide input via stdin or arguments in scripts run non-interactively",
               "Wrap input() in try/except EOFError for pipeline use"],
    ),
    "OverflowError": dict(
        what="A numeric result exceeded what the type can represent.",
        causes=["math.exp/math.pow with huge arguments (floats overflow; ints do not!)",
                "Converting an enormous int to float"],
        fixes=["Integers in Python are arbitrary precision — restructure to stay in int",
               "Use logarithms or decimal.Decimal for extreme ranges"],
    ),
    "MemoryError": dict(
        what="The process ran out of memory.",
        causes=["Loading a huge file with read() instead of iterating",
                "Building a list where a generator would do",
                "Accidental O(n²) accumulation"],
        fixes=["Stream: 'for line in f:' instead of f.read().splitlines()",
               "Use generator expressions for intermediate data",
               "Profile: sum(x for x in ...) vs a growing list"],
    ),
}

_EXTRA_HINTS = [
    (r"'NoneType' object is not subscriptable", "Something you indexed is None — a function "
     "returned None (check for a missing return) or a lookup missed."),
    (r"'NoneType' object is not callable", "You called something that is None — often a "
     "misnamed method or a variable shadowing a function."),
    (r"unsupported operand type\(s\) for (\S+): '(\S+)' and '(\S+)'", "The operator doesn't "
     "work between those two types — convert one of them explicitly."),
    (r"missing (\d+) required positional argument", "A function call is missing arguments — "
     "check the signature with help(fn) or the def line."),
    (r"list index out of range", "Index >= len(list). Valid range is 0..len-1; len(list) is "
     "one past the end."),
    (r"invalid literal for int\(\) with base 10", "int() only accepts digit strings — strip "
     "whitespace first, or validate/parse the format."),
    (r"takes (\d+) positional argument[s]? but (\d+) (?:were|was) given", "Count the arguments: "
     "the def and the call disagree (watch out for a missing self in methods)."),
]

_TRACEBACK_EXCEPTION = re.compile(
    r"^(?:[\w\.]+\.)*([A-Za-z_][\w]*(?:Error|Exception|Interrupt|Exit|Warning|Iteration"
    r"|Recursion|StopIteration))\b(?::\s?(.*))?$"
)
_FILE_LINE = re.compile(r'File "([^"]+)", line (\d+)')


def explain_exception_text(stderr: str) -> dict | None:
    """Parse the last traceback frame + exception from stderr."""
    if not stderr or "Traceback" not in stderr:
        return None
    lines = [l for l in stderr.rstrip().splitlines() if l.strip()]
    exc_name, message, file_line = None, "", None
    for line in reversed(lines):
        m = _TRACEBACK_EXCEPTION.match(line.strip())
        if m:
            exc_name, message = m.group(1), (m.group(2) or "").strip()
            break
    if exc_name is None:
        return None
    for line in reversed(lines):
        m = _FILE_LINE.search(line)
        if m:
            file_line = int(m.group(2))
            break
    return build_explanation(exc_name, message, file_line)


def explain_syntax_error(exc: Exception) -> dict:
    """Build the same friendly structure from a SyntaxError instance."""
    name = type(exc).__name__  # SyntaxError / IndentationError / TabError
    message = getattr(exc, "msg", "") or str(exc)
    line = getattr(exc, "lineno", None)
    text = getattr(exc, "text", None)
    explanation = build_explanation(name, message, line)
    explanation["offending_line"] = text.strip() if text else ""
    explanation["offset"] = getattr(exc, "offset", None)
    return explanation


def build_explanation(exc_name: str, message: str, line: int | None) -> dict:
    entry = ERROR_KB.get(exc_name)
    result: dict = {
        "exception": exc_name,
        "message": message,
        "line": line,
        "what": entry["what"] if entry else "The program raised this exception at runtime.",
        "common_causes": entry["causes"] if entry else ["Read the message for the specific cause."],
        "fixes": entry["fixes"] if entry else [],
    }
    # extra message-specific hints
    hints = []
    for pattern, hint in _EXTRA_HINTS:
        if re.search(pattern, message):
            hints.append(hint)
    if hints:
        result["hints"] = hints
    if message and not entry:
        result["what"] = f"{exc_name}: {message}"
    return result
