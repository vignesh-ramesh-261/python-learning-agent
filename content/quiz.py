"""Interview-style quiz bank. answer is the 0-based index of the correct option."""

QUIZ: list[dict] = [
    dict(
        id="mutable_default",
        topic="Functions", difficulty="medium",
        question="What does this print?",
        code="def append_to(item, target=[]):\n    target.append(item)\n    return target\n\nprint(append_to(1))\nprint(append_to(2))",
        options=["[1] then [2]", "[1] then [1, 2]", "[1] then [2, 2]", "TypeError"],
        answer=1,
        explanation="The default list is created ONCE when the def executes, and every call "
                    "using the default shares it. Mutable defaults are Python's most famous "
                    "gotcha — the fix is target=None plus a fresh list inside.",
    ),
    dict(
        id="is_vs_eq",
        topic="Mutability", difficulty="easy",
        question="What does this print?",
        code="a = [1, 2, 3]\nb = [1, 2, 3]\nprint(a == b, a is b)",
        options=["True True", "True False", "False True", "False False"],
        answer=1,
        explanation="== compares VALUES (equal lists), is compares IDENTITY (two separate "
                    "list objects). Use 'is' only for singletons like None.",
    ),
    dict(
        id="late_binding",
        topic="Scope", difficulty="hard",
        question="What does this print?",
        code="funcs = []\nfor i in range(3):\n    funcs.append(lambda: i)\n\nprint([f() for f in funcs])",
        options=["[0, 1, 2]", "[2, 2, 2]", "[3, 3, 3]", "[0, 0, 0]"],
        answer=2,
        explanation="Closures capture the VARIABLE i, not its value at definition time "
                    "(late binding). After the loop, i == 2 for all three lambdas. Fix: "
                    "lambda i=i: i — default args are evaluated at definition time.",
    ),
    dict(
        id="alias_list",
        topic="Mutability", difficulty="easy",
        question="What does this print?",
        code="a = [1, 2]\nb = a\nb.append(3)\nprint(a)",
        options=["[1, 2]", "[1, 2, 3]", "[3]", "TypeError"],
        answer=1,
        explanation="b = a copies the reference, not the list — both names point to the same "
                    "object, so the mutation is visible through both. Use a.copy() for an "
                    "independent shallow copy.",
    ),
    dict(
        id="tuple_one",
        topic="Collections", difficulty="easy",
        question="Which line creates a one-element tuple?",
        code="",
        options=["t = (1)", "t = tuple(1)", "t = (1,)", "t = [1]"],
        answer=2,
        explanation="(1) is just the integer 1 in parentheses. The trailing comma is what "
                    "makes it a tuple. tuple(1) fails — it needs an iterable.",
    ),
    dict(
        id="enumerate_return",
        topic="Loops", difficulty="easy",
        question="What does enumerate([\"a\", \"b\"]) return?",
        options=["A list of (index, item) tuples", "A lazy iterator of (index, item) pairs",
                 "A dict {0: 'a', 1: 'b'}", "A zip object"],
        answer=1,
        explanation="enumerate returns a lazy iterator yielding (index, item) pairs as you "
                    "iterate — no list is built unless you call list() on it.",
    ),
    dict(
        id="short_circuit_or",
        topic="Control flow", difficulty="medium",
        question="What does this print?",
        code="print(0 or \"default\", \"a\" and \"b\", 3 and 0)",
        options=["0 a b", "default b 0", "default a 0", "default b 3"],
        answer=1,
        explanation="and/or return one of their OPERANDS, not a bool: x or y gives x if x is "
                    "truthy else y; x and y gives x if falsy else y. So 0 or 'default' → "
                    "'default', 'a' and 'b' → 'b', 3 and 0 → 0.",
    ),
    dict(
        id="sort_vs_sorted",
        topic="Collections", difficulty="medium",
        question="What's the result?",
        code="nums = [3, 1, 2]\nresult = nums.sort()\nprint(result)",
        options=["[1, 2, 3]", "[3, 1, 2]", "None", "TypeError"],
        answer=2,
        explanation="list.sort() sorts IN PLACE and returns None. sorted(nums) is the version "
                    "that returns a new list. l = l.sort() is a classic way to destroy a list.",
    ),
    dict(
        id="try_finally",
        topic="Errors", difficulty="hard",
        question="What does this print?",
        code="def f():\n    try:\n        return \"try\"\n    finally:\n        return \"finally\"\n\nprint(f())",
        options=["try", "finally", "try then finally", "SyntaxError"],
        answer=1,
        explanation="finally always runs, and a return inside it REPLACES the pending return "
                    "from the try block. Never put control flow in finally.",
    ),
    dict(
        id="dict_get",
        topic="Collections", difficulty="easy",
        question="What does this print if 'x' is not a key in d?",
        code="d = {\"a\": 1}\nprint(d.get(\"x\", 0))",
        options=["KeyError", "None", "0", "x"],
        answer=2,
        explanation="d[key] raises KeyError for missing keys; d.get(key, default) returns the "
                    "default (None if omitted). Both idioms matter in interviews.",
    ),
    dict(
        id="string_reverse",
        topic="Strings", difficulty="easy",
        question="Which expression reverses the string s?",
        options=["s.reverse()", "reversed(s)", "s[::-1]", "s[-1]"],
        answer=2,
        explanation="s[::-1] slices with step -1 and returns a new reversed string. "
                    "str has no .reverse(); reversed(s) returns an iterator you'd need to "
                    "join.",
    ),
    dict(
        id="dict_order",
        topic="Collections", difficulty="medium",
        question="Since which version are dicts guaranteed to keep insertion order?",
        options=["They never are", "Python 3.7", "Python 3.0", "Only OrderedDict keeps order"],
        answer=1,
        explanation="Insertion order preservation became a language guarantee in Python 3.7 "
                    "(implementation detail in 3.6). Before that you needed "
                    "collections.OrderedDict.",
    ),
    dict(
        id="generator_body",
        topic="Iterators", difficulty="medium",
        question="What happens on the last line?",
        code="def gen():\n    print(\"running\")\n    yield 1\n\ng = gen()",
        options=["Prints 'running'", "Raises TypeError", "Nothing — no code runs yet",
                 "Returns 1"],
        answer=2,
        explanation="Calling a generator function creates a generator object; the body only "
                    "executes when you iterate it (next(), for loop...). Laziness is the whole "
                    "point of generators.",
    ),
    dict(
        id="range_type",
        topic="Loops", difficulty="medium",
        question="How much memory does range(1_000_000_000) use (roughly)?",
        options=["~8 GB — it builds the full list", "~4 GB", "A few dozen bytes — values are computed lazily",
                 "~1 MB"],
        answer=2,
        explanation="range is a lazy sequence object storing only start/stop/step. It supports "
                    "len() and indexing without materialising anything. list(range(...)) is "
                    "what would allocate.",
    ),
    dict(
        id="except_order",
        topic="Errors", difficulty="medium",
        question="What's wrong here?",
        code="try:\n    do_work()\nexcept Exception:\n    print(\"generic\")\nexcept ValueError:\n    print(\"specific\")",
        options=["Nothing wrong", "ValueError handler is unreachable — Exception catches it first",
                 "ValueError must come first AND last", "You can't have two except blocks"],
        answer=1,
        explanation="Excepts are checked top-down and the first match wins. Subclasses "
                    "(ValueError) must be caught BEFORE their base (Exception) or they're dead "
                    "code.",
    ),
    dict(
        id="membership_complexity",
        topic="Collections", difficulty="medium",
        question="Why is 'x in s' fast when s is a set but slow when s is a list?",
        options=["Sets are smaller in memory", "Sets use a hash table — O(1) average vs list's O(n) scan",
                 "Lists must be sorted first", "It isn't — both are O(n)"],
        answer=1,
        explanation="Set membership hashes the value and checks one bucket (O(1) average); a "
                    "list membership is a linear scan (O(n)). Converting to a set is the "
                    "standard optimisation for repeated lookups.",
    ),
    dict(
        id="unbound_local",
        topic="Scope", difficulty="hard",
        question="What happens?",
        code="count = 0\n\ndef bump():\n    count += 1\n\nbump()",
        options=["count becomes 1", "UnboundLocalError", "NameError", "Works fine — globals are readable and writable"],
        answer=1,
        explanation="Assignment anywhere in a function makes the name LOCAL for the whole "
                    "body, so count += 1 reads a not-yet-born local. You'd need 'global "
                    "count' — though returning the new value is cleaner design.",
    ),
    dict(
        id="str_immutable",
        topic="Strings", difficulty="easy",
        question="What happens?",
        code="s = \"hello\"\ns[0] = \"H\"",
        options=["s becomes 'Hello'", "TypeError — strings are immutable",
                 "s becomes ['H', 'ello']", "Prints H"],
        answer=1,
        explanation="Strings are immutable: item assignment raises TypeError. Build a new "
                    "string: 'H' + s[1:] or s.replace('h', 'H', 1).",
    ),
    dict(
        id="int_caching",
        topic="Mutability", difficulty="hard",
        question="Most likely output (CPython)?",
        code="a = 256\nb = 256\nprint(a is b)\nc = 257\nd = 257\nprint(c is d)",
        options=["True True", "True False", "False False", "False True"],
        answer=1,
        explanation="CPython caches ints -5..256, so a is b is True. 257 is created as two "
                    "separate objects when run as a script → False. This is exactly why 'is' "
                    "must not be used for value comparison.",
    ),
    dict(
        id="list_comp_scope",
        topic="Comprehensions", difficulty="medium",
        question="What does this print (Python 3)?",
        code="n = 100\nsquares = [n * n for n in range(3)]\nprint(squares, n)",
        options=["[0, 1, 4] 100", "[0, 1, 4] 2", "[0, 1, 4] 0", "[10000, 10000, 10000] 100"],
        answer=0,
        explanation="In Python 3, comprehensions have their OWN scope — the loop variable n "
                    "does NOT leak (unlike Python 2). The outer n stays 100. In Python 2 it "
                    "would print 2.",
    ),
    dict(
        id="kwargs_order",
        topic="Functions", difficulty="medium",
        question="Which signature is valid?",
        options=["def f(**kwargs, *args)", "def f(*args, **kwargs)",
                 "def f(**kwargs, x=1)", "def f(*args, *more)"],
        answer=1,
        explanation="Parameter order: positional, *args, keyword-only, **kwargs. *args must "
                    "come before **kwargs, and there can be only one of each.",
    ),
    dict(
        id="with_file",
        topic="Files", difficulty="easy",
        question="What's the main reason to prefer 'with open(...) as f:' over 'f = open(...)'?",
        options=["with is faster", "with works for binary files only",
                 "with guarantees the file is closed even if an exception occurs",
                 "open() without with raises a DeprecationWarning"],
        answer=2,
        explanation="The with statement calls __exit__ on normal completion AND on exceptions "
                    "— guaranteed cleanup. Manual close() can be skipped entirely when an "
                    "exception intervenes.",
    ),
    dict(
        id="star_call",
        topic="Functions", difficulty="medium",
        question="What does this print?",
        code="parts = [2026, 8, 30]\nprint(*parts, sep=\"-\")",
        options=["[2026, 8, 30]", "2026 8 30", "2026-8-30", "TypeError"],
        answer=2,
        explanation="In a call, * unpacks the sequence into separate positional arguments: "
                    "print(2026, 8, 30, sep='-'). Same star, opposite job: * collects in "
                    "definitions, spreads in calls.",
    ),
    dict(
        id="nested_copy",
        topic="Mutability", difficulty="hard",
        question="What does this print?",
        code="import copy\ngrid = [[1, 2], [3, 4]]\ndup = grid.copy()\ndup[0][0] = 99\nprint(grid[0][0])",
        options=["1", "99", "None", "IndexError"],
        answer=1,
        explanation="list.copy() is SHALLOW: the outer list is new, but the inner lists are "
                    "shared. Mutating dup[0] mutates grid[0]. Use copy.deepcopy(grid) for full "
                    "independence.",
    ),
]


def get_quiz() -> list[dict]:
    return QUIZ
