"""AST-based construct detector + knowledge base.

Walks the parsed code, detects which Python constructs are used and where,
and pairs each one with a plain-English explanation:
  * what it is
  * why the syntax is written the way it is
  * a tiny example
  * a related interview question
  * an optional link to a lesson id (see content/lessons.py)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class Construct:
    key: str
    name: str
    category: str
    what: str
    why: str
    example: str
    interview: str
    lesson: str | None
    lines: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "what": self.what,
            "why": self.why,
            "example": self.example,
            "interview": self.interview,
            "lesson": self.lesson,
            "lines": sorted(set(self.lines)),
        }


# ---------------------------------------------------------------------------
# The knowledge base.  key -> explanation fields.
# ---------------------------------------------------------------------------

KB: dict[str, dict] = {
    "assignment": dict(
        name="Variable assignment (=)",
        category="Core",
        what="Binds a value to a name. In Python a variable is just a label "
             "attached to an object, not a box that stores the value itself.",
        why="Python has no type declarations: the type lives on the value, not "
            "the variable. That is why 'x = 1' then 'x = \"hi\"' is legal — you "
            "just re-pointed the label to a different object.",
        example="count = 10\nname = \"Ada\"\nitems = [1, 2, 3]",
        interview="What happens internally when you assign a variable in "
                  "Python? (A name is bound to an object in the current "
                  "namespace; the object carries the type.)",
        lesson="variables",
    ),
    "augmented_assignment": dict(
        name="Augmented assignment (+=, -=, *= ...)",
        category="Core",
        what="Shorthand for 'x = x <op> value'. x += 1 adds 1 to x and rebinds "
             "the name.",
        why="It is shorter and signals intent ('update this value') more "
            "clearly than repeating the variable. For mutable objects like "
            "lists, += actually mutates the list in place instead of creating "
            "a new one — a favourite interview trap.",
        example="total = 0\ntotal += 5   # total is now 5",
        interview="What is the difference between 'l += [1]' and 'l = l + [1]' "
                  "for a list? (+= mutates in place via __iadd__, so other "
                  "names pointing at the same list see the change.)",
        lesson="variables",
    ),
    "annotated_assignment": dict(
        name="Annotated assignment (x: int = 5)",
        category="Core",
        what="Assigns a value and attaches an optional type hint to the name.",
        why="Type hints document intent and let tools (mypy, IDEs, LLMs!) catch "
            "mistakes. Python does not enforce them at runtime — they are "
            "metadata stored in __annotations__, which is why the syntax was "
            "designed to be optional.",
        example="age: int = 25\nnames: list[str] = []",
        interview="Are Python type hints enforced at runtime? (No — they are "
                  "hints for static checkers; wrong types still work unless "
                  "validated manually.)",
        lesson="variables",
    ),
    "function_definition": dict(
        name="Function definition (def)",
        category="Functions",
        what="Creates a reusable, named block of code that runs only when "
             "called. def builds a function object and binds it to a name.",
        why="Python uses indentation (not braces) to mark the function body — "
            "the colon+indent style comes from Python's design goal of "
            "readability. Functions are first-class objects: they can be "
            "passed around, stored in lists, and returned from other "
            "functions.",
        example="def greet(name):\n    return f\"Hello, {name}!\"\n\nprint(greet(\"Ada\"))",
        interview="Are Python functions objects? (Yes — they have attributes "
                  "like __name__ and __doc__ and can be passed as arguments.)",
        lesson="functions",
    ),
    "default_arguments": dict(
        name="Default parameter values",
        category="Functions",
        what="Gives a parameter a fallback value used when the caller omits "
             "the argument.",
        why="Defaults make functions convenient without overloading. The "
            "classic gotcha: the default expression is evaluated ONCE, when "
            "the def is executed — so a mutable default (like a list) is "
            "shared between calls. The idiomatic fix is a None sentinel.",
        example="def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items",
        interview="Why should you avoid mutable default arguments? (The default "
                  "object is created once at definition time and shared across "
                  "all calls that use the default.)",
        lesson="functions",
    ),
    "var_args": dict(
        name="*args / **kwargs",
        category="Functions",
        what="Collects extra positional arguments into a tuple (*args) and "
             "extra keyword arguments into a dict (**kwargs).",
        why="The star syntax lets a function accept 'any number of inputs' — "
            "used for wrappers, decorators and APIs that forward arguments. "
            "The syntax is mirrored at the call site, where * unpacks a "
            "sequence into separate arguments.",
        example="def report(*args, **kwargs):\n    print(args, kwargs)\n\nreport(1, 2, mode=\"fast\")",
        interview="What is the correct parameter order? (positional, *args, "
                  "keyword-only, **kwargs.)",
        lesson="functions",
    ),
    "keyword_arguments": dict(
        name="Keyword arguments (f(x=1))",
        category="Functions",
        what="Passes arguments by parameter name instead of position.",
        why="Keyword arguments make calls self-documenting and order-"
            "independent. You can force callers to use them with a bare * in "
            "the signature — the reason you see 'def f(*, key): ...' in "
            "library code.",
        example="def connect(host, port=5432, *, timeout=10):\n    ...\n\nconnect(\"db.local\", timeout=30)",
        interview="What does a bare * in a parameter list mean? (Everything "
                  "after it must be passed by keyword.)",
        lesson="functions",
    ),
    "return_statement": dict(
        name="return statement",
        category="Functions",
        what="Sends a value back to the caller and exits the function. A "
             "function with no return gives back None.",
        why="Python functions always return something — 'return' with no value "
             "(or falling off the end) returns None, which is why forgetting "
             "a return is a common bug. Returning a tuple lets you 'return "
             "multiple values' (really one tuple that unpacks).",
        example="def min_max(nums):\n    return min(nums), max(nums)\n\nlo, hi = min_max([3, 1, 4])",
        interview="What does a Python function return if it has no return "
                  "statement? (None.)",
        lesson="functions",
    ),
    "docstrings": dict(
        name="Docstrings",
        category="Core",
        what="A string literal placed as the first statement of a module, "
             "function or class. It becomes the object's __doc__ attribute.",
        why="Unlike a comment, a docstring is stored in the object itself and "
             "is what help(), IDEs and documentation generators display. The "
             "position (first statement) is what Python looks for.",
        example="def area(r):\n    \"\"\"Return the area of a circle of radius r.\"\"\"\n    return 3.14159 * r ** 2",
        interview="What is the difference between comments (#) and docstrings? "
                  "(Docstrings are stored on the object as __doc__; comments "
                  "are ignored by the interpreter.)",
        lesson="functions",
    ),
    "type_hints": dict(
        name="Type hints (-> str, x: list[int])",
        category="Modern Python",
        what="Annotations describing expected types for variables, parameters "
             "and return values.",
        why="Hints are optional and not enforced at runtime, but they turn "
            "scripts into self-documenting code and let mypy/pyright catch "
            "bugs before running. Modern syntax like list[str] (3.9+) and "
            "X | None (3.10+) replaced typing.List and Optional[X].",
        example="def average(values: list[float]) -> float | None:\n    if not values:\n        return None\n    return sum(values) / len(values)",
        interview="Do type hints improve performance? (No — they are ignored "
                  "at runtime; their value is tooling and readability.)",
        lesson="functions",
    ),
    "decorators": dict(
        name="Decorators (@decorator)",
        category="Functions",
        what="A decorator wraps a function (or class) in another function to "
             "add behaviour. '@log' above a def is exactly equivalent to "
             "'func = log(func)'.",
        why="The @ syntax exists so the wrapping is visible at the definition "
            "site and you do not repeat the name three times. Decorators rely "
            "on functions being first-class objects, and are used for caching, "
            "timing, auth, routing (Flask routes!) and more.",
        example="def shout(fn):\n    def wrapper(*args, **kwargs):\n        return fn(*args, **kwargs).upper()\n    return wrapper\n\n@shout\ndef greet(name):\n    return f\"hi {name}\"",
        interview="Write a decorator that times a function. (Needs *args/"
                  "**kwargs forwarding and returning the inner wrapper.)",
        lesson="decorators",
    ),
    "lambda": dict(
        name="Lambda expressions",
        category="Functions",
        what="An anonymous single-expression function: lambda args: expression.",
        why="It exists for tiny throwaway functions, mostly as the 'key' "
            "argument to sorted(), max(), min() etc. Python deliberately "
            "limits it to one expression to push multi-line logic into named "
            "functions (readability).",
        example="pairs = [(1, \"b\"), (2, \"a\")]\nsorted(pairs, key=lambda p: p[1])",
        interview="Can a lambda contain statements like if/for? (No — only a "
                  "single expression; conditional expressions x if c else y "
                  "are allowed.)",
        lesson="functions",
    ),
    "classes": dict(
        name="Classes & methods (class, self, __init__)",
        category="OOP",
        what="A class bundles data (attributes) and behaviour (methods) into a "
             "custom type. __init__ initialises new instances; self is the "
             "instance a method is called on.",
        why="self is passed explicitly because Python makes method calls "
            "explicit — 'obj.method()' really calls 'Class.method(obj)'. "
            "Nothing stops you from storing state in dicts, but classes give "
            "you a namespace, inheritance and dunder hooks.",
        example="class Dog:\n    def __init__(self, name):\n        self.name = name\n\n    def speak(self):\n        return f\"{self.name} says woof\"\n\nd = Dog(\"Rex\")\nprint(d.speak())",
        interview="What is the difference between an instance attribute and a "
                  "class attribute? (Instance attributes live on the object; "
                  "class attributes are shared by all instances until "
                  "shadowed.)",
        lesson="oop",
    ),
    "inheritance": dict(
        name="Inheritance (class Child(Parent))",
        category="OOP",
        what="A class can reuse and extend another class. Child gets the "
             "parent's methods and attributes; super() calls parent behaviour.",
        why="Inheritance models 'is-a' relationships and enables polymorphism "
            "— code written against the parent works with any child. "
            "Convention: Python embraces duck typing, so deep inheritance "
            "trees are less common than in Java; composition is often "
            "preferred.",
        example="class Animal:\n    def speak(self):\n        return \"...\"\n\nclass Cat(Animal):\n    def speak(self):\n        return \"meow\"",
        interview="How does Python resolve methods? (MRO — Method Resolution "
                  "Order, computed by C3 linearisation, viewable via Class.__mro__.)",
        lesson="oop",
    ),
    "dunder_methods": dict(
        name="Dunder methods (__init__, __str__, __eq__ ...)",
        category="OOP",
        what="Special 'magic' methods that Python calls implicitly to power "
             "built-in behaviour: construction, printing, iteration, "
             "comparison, operator overloading.",
        why="Dunders are the protocol layer of Python: len(obj) calls "
             "__len__, a + b calls __add__, for-loops use __iter__/__next__. "
             "You rarely call them directly — you implement them so built-in "
             "syntax works with your objects.",
        example="class Point:\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n\n    def __repr__(self):\n        return f\"Point({self.x}, {self.y})\"\n\n    def __eq__(self, other):\n        return (self.x, self.y) == (other.x, other.y)",
        interview="What is the difference between __str__ and __repr__? "
                  "(__str__ is for end users via print(); __repr__ is the "
                  "unambiguous fallback, ideally valid Python.)",
        lesson="oop",
    ),
    "conditional": dict(
        name="if / elif / else",
        category="Control flow",
        what="Runs a block only when a condition is true; elif/else provide "
             "alternative branches.",
        why="The colon+indentation block structure replaces C-style braces and "
            "'end if'. Python evaluates branches top-down and stops at the "
            "first true condition, so ordering conditions from specific to "
            "general matters.",
        example="score = 87\nif score >= 90:\n    grade = \"A\"\nelif score >= 80:\n    grade = \"B\"\nelse:\n    grade = \"C\"",
        interview="What is truthy and falsy in Python? (False, None, 0, 0.0, "
                  "'' , [], {}, set(), and 0-length objects are falsy; almost "
                  "everything else is truthy.)",
        lesson="control_flow",
    ),
    "ternary": dict(
        name="Conditional expression (a if cond else b)",
        category="Control flow",
        what="An expression form of if/else that produces a value inline.",
        why="Read left-to-right: 'value if condition else other'. It exists so "
            "simple choices can live inside expressions (assignments, f-"
            "strings, comprehensions) instead of a 4-line if block. Note the "
            "condition sits in the MIDDLE — a frequent point of confusion "
            "coming from C's cond ? a : b.",
        example="status = \"adult\" if age >= 18 else \"minor\"",
        interview="Is the ternary lazily evaluated? (Yes — only the chosen "
                  "branch is evaluated.)",
        lesson="control_flow",
    ),
    "boolean_logic": dict(
        name="and / or / not (short-circuit logic)",
        category="Control flow",
        what="Combines conditions. 'and'/'or' short-circuit: they stop as soon "
             "as the result is known.",
        why="Unlike some languages, 'and'/'or' RETURN one of their operands, "
            "not a boolean: '0 or \"hi\"' gives 'hi', '\"a\" and \"b\"' gives "
            "'b'. That is why the idioms 'x or default' and value-chaining "
            "work. 'not' always returns a real bool.",
        example="name = user_input or \"anonymous\"   # default fallback\nif user and user.is_active:\n    ...",
        interview="What does print(3 and 5) print? (5 — 'and' returns the last "
                  "operand evaluated.)",
        lesson="control_flow",
    ),
    "comparison_operators": dict(
        name="Comparisons (==, !=, <, >=)",
        category="Control flow",
        what="Compares values and produces True/False.",
        why="'==' compares VALUES (by calling __eq__), which is almost always "
            "what you want for data. Python also allows chaining like "
            "'0 <= x < 10', which reads like maths and evaluates each operand "
            "once.",
        example="if guess == answer:\n    print(\"correct\")\nif 0 <= index < len(items):\n    ...",
        interview="What is the difference between == and is? (== compares "
                  "values; is compares object identity — same memory address.)",
        lesson="mutability",
    ),
    "identity_operator": dict(
        name="is / is not (identity check)",
        category="Control flow",
        what="Tests whether two names point to the SAME object in memory.",
        why="'is' never looks at values, so it is only correct for sentinel "
            "checks like 'x is None' — there is exactly one None. Using 'is' "
            "for numbers/strings appears to work due to interning/caching but "
            "is an implementation detail, not a guarantee.",
        example="if result is None:\n    result = default",
        interview="Why must None comparisons use 'is'? (PEP 8 convention + "
                  "'is' cannot be overridden by __eq__, so it is always an "
                  "identity test.)",
        lesson="mutability",
    ),
    "membership_operator": dict(
        name="in / not in (membership test)",
        category="Control flow",
        what="Checks whether a value is contained in a sequence, container or "
             "string.",
        why="It replaces manual loops: 'x in items' calls __contains__ "
            "(or iterates as fallback). On a list it is an O(n) scan; on a "
            "set or dict key it is O(1) — a common interview optimisation "
            "point.",
        example="if \"error\" in message:\n    ...\nvalid = {\"y\", \"yes\"}\nif answer.lower() in valid:\n    ...",
        interview="Why is 'x in my_list' slower than 'x in my_set'? (List does "
                  "a linear scan O(n); set uses a hash table O(1) average.)",
        lesson="collections",
    ),
    "for_loop": dict(
        name="for loop (iteration)",
        category="Control flow",
        what="Iterates over ANY iterable — lists, strings, dicts, files, "
             "generators — taking one item at a time.",
        why="Python's for is a 'for-each': you loop over items directly, not "
            "over indices. That is why 'for x in list' is preferred and "
            "'for i in range(len(list))' is a code smell. Need the index? "
            "Use enumerate().",
        example="for name in [\"Ada\", \"Grace\"]:\n    print(name)\n\nfor i, name in enumerate([\"Ada\", \"Grace\"], start=1):\n    print(i, name)",
        interview="What does a for loop do under the hood? (Calls iter() on "
                  "the object, then repeatedly next() until StopIteration.)",
        lesson="loops",
    ),
    "while_loop": dict(
        name="while loop",
        category="Control flow",
        what="Repeats a block as long as a condition stays true.",
        why="Use while when the number of iterations is unknown in advance "
             "(retry loops, input validation, consuming a queue). for is for "
             "known collections; mixing them up is a readability smell.",
        example="attempts = 0\nwhile attempts < 3:\n    attempts += 1\n    if try_login():\n        break",
        interview="Does Python have do-while? (No — emulate with "
                  "'while True:' + break.)",
        lesson="loops",
    ),
    "break_continue": dict(
        name="break / continue",
        category="Control flow",
        what="break exits the loop immediately; continue skips to the next "
             "iteration.",
        why="They keep loops flat: 'continue' handles the skip-case early so "
             "the main logic is not nested inside a big if. Bonus fact for "
             "interviews: loops can have an else clause that runs only if the "
             "loop finished WITHOUT break.",
        example="for item in queue:\n    if item is None:\n        continue   # skip empties\n    if item == target:\n        found = item\n        break      # stop searching",
        interview="When does a for-else clause run? (Only if the loop was not "
                  "exited by break.)",
        lesson="loops",
    ),
    "comprehensions": dict(
        name="Comprehensions ([x for x in ...])",
        category="Control flow",
        what="Expression-based syntax for building a list, set or dict from an "
             "iterable, with an optional filter.",
        why="It packs a loop+append into one readable line and is measurably "
            "faster than the equivalent loop because the append bytecode is "
            "specialised. In Python 3 the comprehension runs in its own "
            "scope, so the loop variable does not leak.",
        example="squares = [n ** 2 for n in range(10)]\nevens = [n for n in range(20) if n % 2 == 0]\nlengths = {word: len(word) for word in words}",
        interview="Rewrite a loop that appends to a list as a comprehension. "
                  "(The most common 'show you know Python' request.)",
        lesson="comprehensions",
    ),
    "generator_expressions": dict(
        name="Generator expressions ((x for x in ...))",
        category="Control flow",
        what="Like a comprehension but lazy: values are produced one at a time "
             "on demand instead of building a whole list.",
        why="Parentheses make it a generator — and when it is the single "
             "argument of a function, the extra parens can be dropped: "
             "sum(n * n for n in nums). Ideal for big/infinite data because "
             "memory use is O(1).",
        example="total = sum(len(line) for line in lines)\nany_big = any(len(w) > 20 for w in words)",
        interview="Difference between [x for x in r] and (x for x in r)? "
                  "(List vs generator: list is eager and holds everything in "
                  "memory; the generator is lazy.)",
        lesson="comprehensions",
    ),
    "generators": dict(
        name="Generators (yield)",
        category="Functions",
        what="A function containing yield becomes a generator function: "
             "calling it returns a lazy iterator that produces values one at "
             "a time, pausing between them.",
        why="yield lets the function suspend and resume, keeping its local "
             "state — perfect for streams, pipelines and huge datasets. "
             "Interviewers love it because it shows understanding of the "
             "iterator protocol and lazy evaluation.",
        example="def countdown(n):\n    while n > 0:\n        yield n\n        n -= 1\n\nfor x in countdown(3):\n    print(x)",
        interview="What happens when you call a generator function? (Nothing "
                  "runs — you get a generator object; the body only executes "
                  "as you iterate.)",
        lesson="iterators_generators",
    ),
    "context_manager": dict(
        name="with statement (context managers)",
        category="Core",
        what="Sets up a resource, runs a block, and guarantees cleanup even if "
             "an exception happens — via __enter__/__exit__.",
        why="'with open(...) as f' closes the file no matter what, replacing "
             "try/finally boilerplate. Any resource (locks, DB connections, "
             "temp dirs) should use with; you can build your own with the "
             "contextlib.contextmanager decorator.",
        example="with open(\"data.txt\") as f:\n    text = f.read()\n# file is closed here, even on exceptions",
        interview="How does 'with' guarantee cleanup? (__exit__ is called "
                  "during normal completion AND on exceptions, receiving "
                  "exception info.)",
        lesson="files",
    ),
    "error_handling": dict(
        name="try / except / else / finally",
        category="Errors",
        what="Catches exceptions so the program can react instead of crashing. "
             "else runs when no exception occurred; finally always runs.",
        why="Python's philosophy is EAFP ('Easier to Ask Forgiveness than "
             "Permission') — try the operation and handle failures, rather "
             "than pre-checking everything. Catch SPECIFIC exceptions: 'except "
             "Exception' or bare 'except:' hides real bugs.",
        example="try:\n    value = int(raw)\nexcept ValueError as e:\n    print(\"not a number:\", e)\nelse:\n    print(\"got\", value)\nfinally:\n    print(\"done\")",
        interview="When does finally run? (Always — even if the try block "
                  "returns or raises; a return in finally would even "
                  "override earlier returns.)",
        lesson="errors",
    ),
    "raise_statement": dict(
        name="raise (throwing exceptions)",
        category="Errors",
        what="Raises an exception yourself, either a new one or the active one "
             "with a bare 'raise'.",
        why="Raising early with a clear message ('raise ValueError(f\"bad "
             "input: {x!r}\")') is how functions report misuse. A bare 'raise' "
             "inside except re-raises the current exception preserving the "
             "traceback — the correct way to log-and-propagate.",
        example="def set_age(age):\n    if age < 0:\n        raise ValueError(\"age cannot be negative\")",
        interview="What is exception chaining? ('raise X from Y' links the "
                  "original exception as __cause__ for better tracebacks.)",
        lesson="errors",
    ),
    "assert_statement": dict(
        name="assert statement",
        category="Errors",
        what="A debugging check: raises AssertionError if the condition is "
             "false.",
        why="assert is meant for catching programmer errors and for tests — "
             "NOT for validating user input, because running Python with -O "
             "removes assert statements entirely. That is why libraries use "
             "explicit 'raise ValueError' for input validation.",
        example="def discount(price):\n    assert price >= 0, \"price must be non-negative\"\n    return price * 0.9",
        interview="Why should you not validate user input with assert? (It is "
                  "stripped out under python -O, so validation disappears in "
                  "production.)",
        lesson="errors",
    ),
    "fstring": dict(
        name="f-strings (formatted string literals)",
        category="Core",
        what="String literals prefixed with f that embed expressions directly: "
             "f\"{name} has {n} items\".",
        why="f-strings (Python 3.6+) are evaluated at runtime and are the "
            "modern replacement for %-formatting and .format() — faster and "
            "more readable. Inside the braces you can use any expression, "
            "including format specs like {price:.2f} and {value=}.",
        example="price = 49.987\nprint(f\"Total: ${price:.2f}\")\nprint(f\"{price=}\")  # price=49.987",
        interview="How do you format a float to 2 decimals in an f-string? "
                  "(f\"{x:.2f}\" — format spec after the colon.)",
        lesson="strings",
    ),
    "imports": dict(
        name="import / from ... import",
        category="Modules",
        what="Loads code from another module or package into the current "
             "namespace.",
        why="'import x' requires x.attr access (explicit, no name clashes); "
            "'from x import y' binds y directly; 'from x import y as z' "
            "renames on collision. The 'if __name__ == \"__main__\":' guard "
            "works because __name__ is '__main__' only when a file is run "
            "directly, not when imported.",
        example="import json\nfrom pathlib import Path\nfrom collections import defaultdict as dd",
        interview="What does 'if __name__ == \"__main__\"' do? (Runs the block "
                  "only when the file is executed directly, not when "
                  "imported as a module.)",
        lesson="modules",
    ),
    "global_statement": dict(
        name="global / nonlocal",
        category="Functions",
        what="Declares that a name refers to a module-level variable (global) "
             "or an enclosing function's variable (nonlocal), so assignment "
             "updates it instead of creating a new local.",
        why="Assignment in Python creates a LOCAL name by default — that is "
             "why 'count += 1' inside a function raises UnboundLocalError "
             "without 'global count'. Overusing these is a smell; passing "
             "parameters and returning values is usually cleaner (and easier "
             "to test).",
        example="count = 0\n\ndef increment():\n    global count\n    count += 1",
        interview="Why does 'x = 1' inside a function not change the global "
                  "x? (Assignment binds a new local name unless declared "
                  "global/nonlocal.)",
        lesson="scoping",
    ),
    "walrus": dict(
        name="Walrus operator (:=)",
        category="Modern Python",
        what="Assignment expression (Python 3.8+): assigns a value AND returns "
             "it inside an expression.",
        why="It removes the 'compute, test, then use' duplication: 'if (n := "
            "len(data)) > 10:' computes len once and reuses it. Named after "
            "the eyes-and-tusks look of :=. Use sparingly — it trades a line "
            "of clarity for compactness.",
        example="while (chunk := f.read(8192)):\n    process(chunk)",
        interview="Difference between = and :=? (= is a statement; := is an "
                  "expression that also binds a name — allowed inside "
                  "conditions and comprehensions.)",
        lesson="comprehensions",
    ),
    "match_statement": dict(
        name="match / case (structural pattern matching)",
        category="Modern Python",
        what="Pattern matching (Python 3.10+): compares a value against "
             "patterns and runs the first matching case.",
        why="It is far more powerful than C's switch — cases can destructure "
             "sequences, dicts and objects ('case {\"op\": \"add\", \"args\": "
             "[a, b]}:'). Note: the wildcard case _ acts as the default and "
             "cases are checked top-down.",
        example="match command.split():\n    case [\"go\", direction]:\n        move(direction)\n    case [\"quit\"]:\n        exit()\n    case _:\n        print(\"unknown command\")",
        interview="How is match different from if/elif? (It matches "
                  "STRUCTURE — it can bind parts of the value to names in the "
                  "case pattern.)",
        lesson="control_flow",
    ),
    "async_basics": dict(
        name="async / await (asynchronous code)",
        category="Modern Python",
        what="Defines coroutines: functions that can pause (await) so other "
             "work runs while waiting — usually for I/O.",
        why="One thread can juggle thousands of network calls if each 'await' "
             "yields control instead of blocking — this is how high-"
             "concurrency servers work. Rules: async def returns a coroutine "
             "that does nothing until awaited/scheduled, and you need an "
             "event loop (asyncio.run) to run it.",
        example="import asyncio\n\nasync def fetch():\n    await asyncio.sleep(1)\n    return \"done\"\n\nasyncio.run(fetch())",
        interview="What do you get when you call an async def function? (A "
                  "coroutine object — the body does not run until awaited or "
                  "scheduled.)",
        lesson=None,
    ),
    "slicing": dict(
        name="Slicing (seq[start:stop:step])",
        category="Data structures",
        what="Extracts a sub-sequence. start is included, stop is excluded; "
             "negative indices count from the end; step can skip or reverse.",
        why="The half-open [start, stop) convention makes lengths add up: "
             "len(a[:i]) + len(a[i:]) == len(a). Slices never raise "
             "IndexError — out-of-range bounds are clipped silently, and "
             "'seq[::-1]' is the classic reverse idiom. Slicing copies (for "
             "lists); 'seq[:]' is the copy idiom.",
        example="nums = [0, 1, 2, 3, 4, 5]\nnums[1:4]    # [1, 2, 3]\nnums[-2:]    # [4, 5]\nnums[::-1]   # reversed copy",
        interview="What does [1,2,3,4][1:100] return? ([2, 3, 4] — slices "
                  "clip out-of-range bounds instead of raising.)",
        lesson="collections",
    ),
    "subscripting": dict(
        name="Indexing (seq[i]) & key access (d[key])",
        category="Data structures",
        what="Reads or writes one element: by position for sequences, by key "
             "for dicts.",
        why="Indexing is 0-based, and out-of-range access raises IndexError "
             "(KeyError for dicts) — unlike slicing, it is strict. For 'get "
             "or default' behaviour, dicts offer d.get(key, default), which "
             "avoids the try/KeyError dance.",
        example="first = items[0]\nlast = items[-1]\ncount = counts.get(\"apples\", 0)",
        interview="Difference between d[key] and d.get(key)? (Missing key: [] "
                  "raises KeyError; .get returns None or your default.)",
        lesson="collections",
    ),
    "unpacking": dict(
        name="Unpacking with * (call-site & starred patterns)",
        category="Data structures",
        what="*seq spreads a sequence into separate arguments or elements; "
             "**mapping spreads a dict into keyword arguments.",
        why="One star in a DEFINITION collects (packing); the same star at a "
             "CALL/LITERAL spreads (unpacking). The symmetric design makes "
             "wrapper functions and 'merge these dicts/lists' one-liners "
             "possible.",
        example="def log(*args, **kwargs): ...\n\nparts = [2026, 8, 30]\nprint(*parts, sep=\"-\")          # 2026-8-30\nmerged = {**defaults, **overrides}",
        interview="What does print(*[1, 2, 3]) do? (Unpacks the list into "
                  "three positional arguments: print(1, 2, 3).)",
        lesson="functions",
    ),
    "tuple_unpacking": dict(
        name="Tuple unpacking (a, b = ...)",
        category="Data structures",
        what="Assigns the elements of a tuple/list/dict-items directly to "
             "multiple names in one statement.",
        why="Unpacking replaces index bookkeeping ('first = pair[0]') with "
             " declarative names. Extended unpacking 'a, *rest = items' "
             "grabs 'everything else', which is common in parsing loops.",
        example="name, score = (\"Ada\", 99)\nfirst, *rest = [1, 2, 3, 4]   # first=1, rest=[2, 3, 4]",
        interview="Swap two variables without a temp: (a, b = b, a — builds a "
                  "tuple on the right, then unpacks it.)",
        lesson="collections",
    ),
    "list_literal": dict(
        name="Lists ([1, 2, 3])",
        category="Data structures",
        what="An ordered, MUTABLE sequence: append, insert, remove and sort "
             "in place.",
        why="Lists are the default 'bag of things' in Python. Mutability means "
             "assignment copies the REFERENCE, not the list — 'b = a' then "
             "'b.append' changes what a sees. Use b = a.copy() for an "
             "independent shallow copy.",
        example="nums = [3, 1, 2]\nnums.append(4)\nnums.sort()\n\na = [1, 2]\nb = a          # same object!\nb.append(3)\nprint(a)       # [1, 2, 3]",
        interview="What does b = a.copy() copy? (A shallow copy — outer list "
                  "is new, nested objects are still shared; deep copy needs "
                  "copy.deepcopy.)",
        lesson="collections",
    ),
    "tuple_literal": dict(
        name="Tuples ((1, 2, 3))",
        category="Data structures",
        what="An ordered, IMMUTABLE sequence — fixed once created.",
        why="Immutability makes tuples hashable, so they work as dict keys and "
             "set members, and signals 'this is a fixed record'. Syntax "
             "gotcha: a one-element tuple needs the trailing comma: (1,) — "
             "(1) is just the int 1 in parentheses.",
        example="point = (3, 4)\nrgb = (255, 128, 0)\nsingle = (42,)   # tuple!\nnot_tuple = (42)  # just int 42",
        interview="Can a tuple contain a mutable list, and is it then "
                  "hashable? (It can contain one, but then the tuple is not "
                  "hashable — hashing fails when it meets the list.)",
        lesson="collections",
    ),
    "dict_literal": dict(
        name="Dictionaries ({\"key\": value})",
        category="Data structures",
        what="A hash map from keys to values. Insertion order is preserved "
             "(guaranteed since Python 3.7).",
        why="Dicts give O(1) average lookups and are THE mapping structure in "
             "Python (module namespaces, class attributes, **kwargs are all "
             "dicts). Keys must be hashable — lists cannot be keys, tuples "
             "can. Missing key? Use d.get(k, default) or collections."
             "defaultdict.",
        example="ages = {\"ada\": 36, \"grace\": 45}\nages[\"linus\"] = 55\nfor name, age in ages.items():\n    print(name, age)",
        interview="Are dicts ordered? (Yes — insertion order is guaranteed "
                  "since 3.7; before that it was an implementation detail.)",
        lesson="collections",
    ),
    "set_literal": dict(
        name="Sets ({1, 2, 3})",
        category="Data structures",
        what="An unordered collection of UNIQUE, hashable elements with fast "
             "membership tests and algebra (union |, intersection &, "
             "difference -).",
        why="set() is the go-to for deduplication ('unique = set(items)') and "
             "for O(1) 'in' checks. Note: {} creates an empty DICT, not a "
             "set — the empty set needs set().",
        example="tags = [\"py\", \"web\", \"py\"]\nunique = set(tags)\ncommon = {1, 2, 3} & {2, 3, 4}   # {2, 3}",
        interview="How do you remove duplicates from a list while keeping "
                  "order? (dict.fromkeys(items) — dicts preserve insertion "
                  "order — or a seen-set loop.)",
        lesson="collections",
    ),
    "enumerate": dict(
        name="enumerate()",
        category="Useful builtins",
        what="Yields (index, item) pairs while you iterate — the idiomatic way "
             "to get a counter inside a for loop.",
        why="It replaces the C-style 'for i in range(len(seq))' pattern, is "
            "harder to get wrong (off-by-one), and supports a start offset: "
            "enumerate(seq, start=1) for 1-based numbering.",
        example="for i, task in enumerate(tasks, start=1):\n    print(f\"{i}. {task}\")",
        interview="What does enumerate return? (A lazy iterator of (index, "
                  "item) tuples — wrap in list() to materialise.)",
        lesson="loops",
    ),
    "zip": dict(
        name="zip()",
        category="Useful builtins",
        what="Iterates several iterables in parallel, yielding tuples of "
             "corresponding items.",
        why="zip stops at the SHORTER iterable (in older versions); "
            "zip(a, b, strict=True) (3.10+) raises if lengths differ — safer "
            "when mismatch is a bug. For 'loop two lists with one index', zip "
            "beats range(len(...)).",
        example="names = [\"Ada\", \"Grace\"]\nscores = [91, 99]\nfor name, score in zip(names, scores):\n    print(name, score)",
        interview="How do you 'unzip'? (zip(*pairs) — unpacking transposes "
                  "the pairs back into columns.)",
        lesson="loops",
    ),
    "range_call": dict(
        name="range()",
        category="Useful builtins",
        what="Produces an arithmetic sequence of integers lazily: "
             "range(start, stop, step).",
        why="range is a lazy object — it uses O(1) memory no matter how large "
             "and is a sequence (supports len(), indexing, slicing) while not "
             "being a list. It exists so 'for i in range(1_000_000)' never "
             "builds a million-item list.",
        example="for i in range(5):        # 0..4\n    print(i)\nlist(range(10, 0, -2))  # [10, 8, 6, 4, 2]",
        interview="Is range(10**9) memory-heavy? (No — range stores only "
                  "start/stop/step and computes values on demand.)",
        lesson="loops",
    ),
    "sorted_call": dict(
        name="sorted() vs list.sort()",
        category="Useful builtins",
        what="sorted(iterable, key=..., reverse=...) returns a NEW sorted "
             "list; list.sort() sorts IN PLACE and returns None.",
        why="Choosing between them is about side effects: sort() mutates "
             "(cheap, but the original order is lost); sorted() leaves the "
             "original intact. The key= function decides comparison — e.g. "
             "key=len, key=lambda r: r[1]. Returning None from sort() is why "
             "'l = l.sort()' silently destroys your list.",
        example="by_score = sorted(players, key=lambda p: p[\"score\"], reverse=True)\nnums.sort()  # in place, returns None!",
        interview="Is Python's sort stable? (Yes — Timsort keeps equal "
                  "elements in original order, enabling multi-key sorting by "
                  "sorting twice.)",
        lesson="collections",
    ),
    "isinstance": dict(
        name="isinstance()",
        category="Useful builtins",
        what="Checks whether an object is an instance of a class (or a tuple "
             "of classes), including subclasses.",
        why="isinstance respects inheritance — better than type(x) == T, "
             "which breaks for subclasses. Pythonic style prefers duck typing "
             "('just call the method') with isinstance as the guard for truly "
             "different shapes.",
        example="if isinstance(value, (int, float)):\n    print(value * 2)",
        interview="Why prefer isinstance over type() == ? (Subclasses pass "
                  "isinstance but fail type() equality; plus isinstance "
                  "accepts multiple types at once.)",
        lesson="oop",
    ),
    "map_filter": dict(
        name="map() / filter()",
        category="Useful builtins",
        what="Lazy iterators applying a function to every item (map) or "
             "keeping items that pass a test (filter).",
        why="They are the functional cousins of comprehensions: "
            "[f(x) for x in xs] == list(map(f, xs)). In Python 3 they return "
            "lazy iterators (not lists) — a classic surprise when printing "
            "them directly. Comprehensions are generally preferred for "
            "readability.",
        example="list(map(str.upper, [\"a\", \"b\"]))   # ['A', 'B']\nlist(filter(None, [0, 1, \"\", \"x\"]))  # [1, 'x']",
        interview="map(int, strings) returns what in Python 3? (A map "
                  "iterator — lazy; wrap in list() to see contents.)",
        lesson="comprehensions",
    ),
}

# Call-based builtin triggers:  func-name -> KB key
BUILTIN_CALLS = {
    "enumerate": "enumerate",
    "zip": "zip",
    "range": "range_call",
    "sorted": "sorted_call",
    "isinstance": "isinstance",
    "map": "map_filter",
    "filter": "map_filter",
}

# Node type -> KB key, used by the generic collector.
NODE_KEYS = {
    ast.Assign: "assignment",
    ast.AugAssign: "augmented_assignment",
    ast.AnnAssign: "annotated_assignment",
    ast.FunctionDef: "function_definition",
    ast.AsyncFunctionDef: "function_definition",
    ast.Return: "return_statement",
    ast.If: "conditional",
    ast.IfExp: "ternary",
    ast.BoolOp: "boolean_logic",
    ast.For: "for_loop",
    ast.AsyncFor: "for_loop",
    ast.While: "while_loop",
    ast.Break: "break_continue",
    ast.Continue: "break_continue",
    ast.ListComp: "comprehensions",
    ast.SetComp: "comprehensions",
    ast.DictComp: "comprehensions",
    ast.GeneratorExp: "generator_expressions",
    ast.Lambda: "lambda",
    ast.ClassDef: "classes",
    ast.Yield: "generators",
    ast.YieldFrom: "generators",
    ast.With: "context_manager",
    ast.AsyncWith: "context_manager",
    ast.Try: "error_handling",
    ast.TryStar: "error_handling",
    ast.Raise: "raise_statement",
    ast.Assert: "assert_statement",
    ast.JoinedStr: "fstring",
    ast.Import: "imports",
    ast.ImportFrom: "imports",
    ast.Global: "global_statement",
    ast.Nonlocal: "global_statement",
    ast.NamedExpr: "walrus",
    ast.Match: "match_statement",
    ast.Await: "async_basics",
    ast.Slice: "slicing",
    ast.Starred: "unpacking",
}

# Literal node -> KB key
LITERAL_KEYS = {
    ast.List: "list_literal",
    ast.Tuple: "tuple_literal",
    ast.Dict: "dict_literal",
    ast.Set: "set_literal",
}


class Collector(ast.NodeVisitor):
    """Collects KB keys -> line numbers for every construct found."""

    def __init__(self) -> None:
        self.hits: dict[str, list[int]] = {}
        self._class_stack: list[str] = []

    # -- helpers ------------------------------------------------------------
    def _add(self, key: str, node: ast.AST) -> None:
        line = getattr(node, "lineno", None)
        if line is not None:
            self.hits.setdefault(key, []).append(line)

    # -- special handling ---------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._add("function_definition", node)
        if node.decorator_list:
            self._add("decorators", node)
        if node.args.defaults or node.args.kw_defaults:
            self._add("default_arguments", node)
        if node.args.vararg or node.args.kwarg:
            self._add("var_args", node)
        if node.returns or any(a.annotation for a in node.args.args):
            self._add("type_hints", node)
        self._add("docstrings", node) if _has_docstring(node) else None
        if self._class_stack and node.name.startswith("__") and node.name.endswith("__"):
            self._add("dunder_methods", node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._add("annotated_assignment", node)
        self._add("type_hints", node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add("classes", node)
        if node.bases:
            self._add("inheritance", node)
        self._add("docstrings", node) if _has_docstring(node) else None
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id in BUILTIN_CALLS:
            self._add(BUILTIN_CALLS[func.id], node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        ops = {type(o) for o in node.ops}
        if ast.Is in ops or ast.IsNot in ops:
            self._add("identity_operator", node)
            # 'is' used against a literal is a review matter, not a construct
        elif ast.In in ops or ast.NotIn in ops:
            self._add("membership_operator", node)
        else:
            self._add("comparison_operators", node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._add("assignment", node)
        for target in node.targets:
            if isinstance(target, ast.Tuple):
                if any(isinstance(e, ast.Starred) for e in target.elts):
                    self._add("tuple_unpacking", node)
                elif len(target.elts) > 1:
                    self._add("tuple_unpacking", node)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.slice, ast.Slice):
            self._add("slicing", node)
        else:
            self._add("subscripting", node)
        self.generic_visit(node)

    def visit_keyword(self, node: ast.keyword) -> None:
        if node.arg is not None:
            self._add("keyword_arguments", node)
        self.generic_visit(node)

    # -- generic dispatch ----------------------------------------------------
    def generic_visit(self, node: ast.AST) -> None:
        key = NODE_KEYS.get(type(node))
        if key:
            self._add(key, node)
        lit = LITERAL_KEYS.get(type(node))
        if lit and not isinstance(node, ast.expr_context):
            # Only count actual literals, not e.g. the Tuple used as a
            # for-loop target (visited via its parent anyway).
            self._add(lit, node)
        super().generic_visit(node)


def _has_docstring(node: ast.AST) -> bool:
    body = getattr(node, "body", [])
    return bool(
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    )


def collect(tree: ast.AST) -> list[dict]:
    """Return the constructs used in the tree, ordered by first appearance."""
    collector = Collector()
    collector.visit(tree)
    constructs: list[Construct] = []
    for key, lines in collector.hits.items():
        meta = KB[key]
        constructs.append(
            Construct(key=key, lines=lines, **{k: meta[k] for k in
                                                ("name", "category", "what", "why",
                                                 "example", "interview", "lesson")})
        )
    constructs.sort(key=lambda c: min(c.lines))
    return [c.to_dict() for c in constructs]
