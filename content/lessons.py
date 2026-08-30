"""Fundamentals curriculum: lessons as data, rendered by the web UI."""

LESSONS: list[dict] = [
    dict(
        id="variables",
        title="Variables, Types & Names",
        level="beginner",
        summary="What a variable really is in Python, dynamic typing, and how "
                "names bind to objects — the foundation everything else sits on.",
        sections=[
            dict(
                heading="A variable is a label, not a box",
                body="Assignment binds a NAME to an OBJECT. The type belongs to the object, "
                     "not the name — that is dynamic typing. The same name can point to an "
                     "int, then a string, then a function. Variables live in namespaces "
                     "(module globals, function locals, object attributes).",
                code='count = 42          # name "count" -> int object\ncount = "forty-two" # same name, now a str\nprint(type(count))   # <class \'str\'>',
                code_note="No declarations, no types on names — type(x) tells you what the "
                          "name currently points to.",
            ),
            dict(
                heading="Everything is an object",
                body="Ints, strings, functions, classes, modules — all objects with an "
                     "identity (id), a type, and (usually) a value. Functions being objects "
                     "is what enables decorators and passing behaviour around.",
                code='def shout(text):\n    return text.upper()\n\nspeak = shout        # functions are objects\nprint(speak("hi"))   # HI',
                code_note="Binding a second name to a function does NOT copy it — both names "
                          "refer to the same function object.",
            ),
            dict(
                heading="Multiple assignment and swapping",
                body="Python evaluates the right-hand side first, then unpacks into the "
                     "targets. This is why a, b = b, a swaps without a temp variable.",
                code="x, y = 1, 2\nx, y = y, x\nprint(x, y)  # 2 1",
                code_note="The right side builds a tuple (2, 1); the left side unpacks it.",
            ),
        ],
        key_points=[
            "Names are references to objects; types live on objects, not names.",
            "Dynamic typing means no declarations — but also fewer compile-time catches, so tests matter.",
            "id(obj) shows identity; == compares value; is compares identity.",
            "a, b = b, a works because of tuple building + unpacking.",
        ],
        interview_questions=[
            dict(q="Is Python strongly or weakly typed? Dynamically or statically?",
                 a="Statically? No — dynamically: types are checked at runtime and names can "
                   "rebind to any type. Strongly: '1' + 1 raises TypeError; Python will not "
                   "silently coerce strings and numbers."),
            dict(q="What does x = y actually copy?",
                 a="Nothing but the reference. Both names point to the same object — mutating a "
                   "mutable object through one name is visible through the other."),
        ],
    ),
    dict(
        id="mutability",
        title="Mutability, References & Copies",
        level="beginner",
        summary="The single most-tested interview topic: mutable vs immutable objects, "
                "aliasing, shallow vs deep copies, is vs ==.",
        sections=[
            dict(
                heading="Mutable vs immutable",
                body="Lists, dicts, sets (and most custom objects) are MUTABLE — they change "
                     "in place. Ints, floats, strings, tuples, frozensets are IMMUTABLE — "
                     "'changing' them actually creates a new object. This distinction drives "
                     "default arguments, dict keys, and half of Python's surprises.",
                code="a = [1, 2]\nb = a          # alias, same object\nb.append(3)\nprint(a)        # [1, 2, 3]!\n\ns = \"hi\"\ns += \"!\"        # new string object; the old one is untouched",
                code_note="id(a) == id(b) proves they are the same object until you rebind.",
            ),
            dict(
                heading="is vs ==",
                body="== asks 'same value?' (calls __eq__). is asks 'same object?' (compares "
                     "id). Use is ONLY for singletons: None, True, False. Small ints/strings "
                     "are cached by CPython, so 'x is 100' can seem to work — that's an "
                     "implementation detail, not a rule.",
                code="a = [1, 2, 3]\nb = [1, 2, 3]\nprint(a == b)   # True  — equal value\nprint(a is b)   # False — different objects\nprint(None is None)  # True — one None object",
                code_note="PEP 8: always compare None with 'is' / 'is not'.",
            ),
            dict(
                heading="Shallow vs deep copy",
                body="b = a.copy() (or a[:], list(a)) makes a NEW outer container whose "
                     "ELEMENTS still alias the originals — shallow. Nested mutables are still "
                     "shared. copy.deepcopy(x) recursively copies everything.",
                code="import copy\ngrid = [[1, 2], [3, 4]]\nshallow = grid.copy()\nshallow[0].append(9)\nprint(grid)      # [[1, 2, 9], [3, 4]] — inner list shared!\n\ndeep = copy.deepcopy(grid)\ndeep[0].append(7)\nprint(grid)      # unchanged",
                code_note="Interview favourite: 'How do you actually copy a 2-D list?'",
            ),
            dict(
                heading="Pass-by-object-reference",
                body="Arguments are passed by sharing the reference. Rebinding a parameter "
                     "inside the function (x = [1]) does NOT affect the caller; MUTATING the "
                     "object (x.append(1)) DOES. That explains every 'my function didn't "
                     "change it' mystery.",
                code="def tweak(x, y):\n    x.append(99)   # mutation -> caller sees it\n    y = [0]        # rebinding -> caller doesn't\n\nnums, other = [], []\ntweak(nums, other)\nprint(nums, other)  # [99] []",
                code_note="Java folks: it's neither pass-by-value nor pass-by-reference — it's "
                          "pass-by-object-reference.",
            ),
        ],
        key_points=[
            "Mutable: list, dict, set. Immutable: int, float, str, tuple, frozenset, bytes.",
            "b = a aliases; a.copy() is shallow; copy.deepcopy() is deep.",
            "is = identity, == = value; use 'is' only for None/True/False.",
            "Function arguments share objects: mutation escapes, rebinding doesn't.",
        ],
        interview_questions=[
            dict(q="Why shouldn't a function signature be def f(items=[])?",
                 a="The default list is created once at definition time and shared by all calls. "
                   "Mutations persist between calls. Use items=None and create the list inside."),
            dict(q="Why can't lists be dict keys but tuples can?",
                 a="Dict keys must be hashable. Hashability requires the value to never change — "
                   "mutable lists break that contract. Tuples of immutables are hashable."),
            dict(q="What does 'function arguments are passed by object reference' mean?",
                 a="The reference is passed by value: the function gets the same object, so "
                   "mutation is visible to the caller, but rebinding the parameter is not."),
        ],
    ),
    dict(
        id="strings",
        title="Strings & f-strings",
        level="beginner",
        summary="Immutability in action: common string operations, formatting with "
                "f-strings, and the methods interviews expect.",
        sections=[
            dict(
                heading="Strings are immutable sequences",
                body="Every 'modification' returns a NEW string. Indexing and slicing work "
                     "like lists. Immutability is why strings are hashable (usable as dict "
                     "keys) and why += in loops is slow.",
                code="s = \"Python\"\nprint(s[0], s[-1])     # P n\nprint(s[1:4])          # yth\nprint(s[::-1])         # nohtyP\n# s[0] = 'J'  -> TypeError",
                code_note="''.join(parts) instead of += in loops — the classic efficiency answer.",
            ),
            dict(
                heading="f-strings do everything",
                body="Prefix a string with f and embed any expression in {}. Add a format "
                     "spec after a colon: .2f for 2 decimals, , for thousands, >10 for "
                     "alignment. f'{x=}' prints the expression AND its value — great for "
                     "debugging.",
                code="name, price, qty = \"Widget\", 4.5, 3\ntotal = price * qty\nprint(f\"{qty} x {name} = ${total:.2f}\")\nprint(f\"{total=:.2f}\")          # total=13.50\nprint(f\"|{name:>12}|\")          # right-aligned width 12",
                code_note="f-strings (3.6+) replaced %-formatting and .format(); they're also the fastest.",
            ),
            dict(
                heading="Methods interviews expect",
                body="split/join for tokenizing; strip for trimming; startswith/replace for "
                     "cleaning; in for substring tests; enumerate/zip when pairing lines. "
                     "Know that split() with no args splits on any whitespace run and "
                     "handles leading/trailing spaces.",
                code='record = "  Ada, 36, ML  "\nname, age, team = [p.strip() for p in record.split(",")]\nprint(name, int(age), team)\nprint("ml" in team.lower())       # True',
                code_note="Chaining is normal: line.strip().lower().split(':').",
            ),
        ],
        key_points=[
            "Strings are immutable: every method returns a new string.",
            "f-strings: f\"{expr:spec}\" — :.2f, :, >10, {x=} debug form.",
            "''.join(list) beats += in a loop (O(n) vs O(n²)).",
            "split()/strip()/in cover 90% of parsing questions.",
        ],
        interview_questions=[
            dict(q="Reverse a string without a loop?",
                 a="s[::-1] — slicing with step -1. Also ''.join(reversed(s))."),
            dict(q="Check if a string is a palindrome?",
                 a="s == s[::-1] (optionally s.lower() and filter alphanumerics first)."),
        ],
    ),
    dict(
        id="collections",
        title="Lists, Tuples, Dicts & Sets",
        level="beginner",
        summary="The four core containers: what each is for, big-O of their "
                "operations, and how to choose between them.",
        sections=[
            dict(
                heading="The choosing table",
                body="List: ordered, mutable, index by position. Tuple: ordered, immutable, "
                     "fixed record / dict key. Dict: key -> value map, O(1) lookup, insertion-"
                     "ordered (3.7+). Set: unique items, O(1) membership, set algebra. Choosing "
                     "correctly IS the interview answer.",
                code="point   = (3, 4)        # fixed record\ntags    = [\"ml\", \"py\"]   # ordered sequence\nby_name = {\"ada\": 36}    # lookup by key\nunique  = {\"py\", \"ml\"}   # membership/dedup",
                code_note="Ask yourself: do I need order? uniqueness? lookup by key? mutability?",
            ),
            dict(
                heading="List operations & big-O",
                body="append O(1), pop() from the end O(1), insert(0, x)/pop(0) O(n) — use "
                     "collections.deque for queues. 'in' is O(n) on lists but O(1) on sets — "
                     "the standard optimisation when membership is hot.",
                code="from collections import deque\nnums = [3, 1, 2]\nnums.append(4); nums.sort()\nq = deque([1, 2, 3])\nq.append(4); q.popleft()   # O(1) both ends",
                code_note="Sorting is stable (Timsort): equal keys keep their original order.",
            ),
            dict(
                heading="Dict idioms",
                body="d.get(k, default) avoids KeyError. Iterate with .items(). Count with "
                     "dict.get or collections.Counter. Merge with {**a, **b} (later wins) or "
                     "a | b (3.9+). Missing keys on the fly: setdefault or defaultdict.",
                code="from collections import Counter\nwords = \"to be or not to be\".split()\ncounts = Counter(words)\nprint(counts.most_common(2))   # [('to', 2), ('be', 2)]",
                code_note="Counter is just a dict subclass — knowing it exists is the point.",
            ),
            dict(
                heading="Set algebra",
                body="Union |, intersection &, difference -, symmetric difference ^. Perfect "
                     "for 'common/unique/tags' questions. Dedup preserving order: "
                     "list(dict.fromkeys(items)).",
                code="a, b = {1, 2, 3}, {2, 3, 4}\nprint(a & b, a - b, a ^ b)   # {2, 3} {1} {1, 4}\nitems = [\"py\", \"web\", \"py\"]\nprint(list(dict.fromkeys(items)))  # ['py', 'web']",
                code_note="{} is an empty dict; empty set is set().",
            ),
        ],
        key_points=[
            "list=ordered mutable, tuple=ordered immutable, dict=keyed map, set=unique items.",
            "Membership: O(n) list/tuple vs O(1) set/dict — know this trade-off.",
            "dicts preserve insertion order (guaranteed 3.7+).",
            "One-element tuple needs a comma: (1,).",
        ],
        interview_questions=[
            dict(q="List vs tuple — when and why?",
                 a="Tuple for heterogeneous fixed records and hashable keys; list for "
                   "homogeneous, growing collections. Signals intent to readers."),
            dict(q="How do you count occurrences efficiently?",
                 a="collections.Counter(items) — O(n), plus most_common(n) for the top-k."),
            dict(q="How do you find common elements of two lists?",
                 a="set(a) & set(b) — O(n+m) instead of the O(n·m) nested loop."),
        ],
    ),
    dict(
        id="control_flow",
        title="Conditionals & Truthiness",
        level="beginner",
        summary="if/elif/else, truthy and falsy values, ternary expressions, and "
                "short-circuit logic that returns operands.",
        sections=[
            dict(
                heading="Branches, colon + indentation",
                body="if/elif/else pick ONE branch top-down. Conditions don't need "
                     "parentheses; the colon and 4-space indentation define the block. "
                     "Chain comparisons mathematically: 0 <= x < 10.",
                code="score = 87\nif score >= 90:\n    grade = \"A\"\nelif score >= 80:\n    grade = \"B\"\nelse:\n    grade = \"C\"\n\nif 80 <= score < 90:\n    print(\"B range\")",
                code_note="Conditions are evaluated once, top to bottom, first truthy wins.",
            ),
            dict(
                heading="Truthy / falsy",
                body="Falsy: False, None, 0, 0.0, '', [], {}, set(), tuple(), range(0), and "
                     "objects defining __bool__ -> False or __len__ -> 0. Everything else is "
                     "truthy — including negative numbers, 'False' the string, and non-empty "
                     "containers.",
                code="items = []\nif not items:\n    print(\"empty — no len(items) == 0 needed\")\n\nif name := input():  # even walrus conditions use truthiness\n    print(name)",
                code_note="'if x:' is the idiomatic emptiness test — say it in reviews.",
            ),
            dict(
                heading="and/or return OPERANDS",
                body="x and y: returns x if x is falsy, else y. x or y: returns x if truthy, "
                     "else y. That's why defaults work: name = input() or 'anon'. 'not' always "
                     "returns a bool. Short-circuiting also guards: x and x.key.",
                code='print(0 or "hi")     # hi\nprint("a" and "b")   # b\nprint(3 and 5)       # 5\nprint(not [])        # True',
                code_note="Interview one-liner: 'What does and/or return?' — operands, not bools.",
            ),
            dict(
                heading="Ternary & match",
                body="value_if_true if cond else value_if_false — an EXPRESSION, usable inside "
                     "assignments, f-strings, comprehensions. For multi-way matching on "
                     "structure, match/case (3.10+) destructures data — cleaner than elif "
                     "chains over dicts of shapes.",
                code="age = 20\nstatus = \"adult\" if age >= 18 else \"minor\"\n\nmatch (3, 4):\n    case (0, y):\n        print(\"on y axis\", y)\n    case (x, 0):\n        print(\"on x axis\", x)\n    case (x, y):\n        print(\"point\", x, y)",
                code_note="Only the chosen branch executes — lazy evaluation.",
            ),
        ],
        key_points=[
            "Falsy: False, None, 0, '', [], {}, set(). Everything else truthy.",
            "and/or return operands; use 'x or default' idiom knowingly.",
            "Ternary: a if cond else b — condition in the middle.",
            "Chained comparisons evaluate each operand once.",
        ],
        interview_questions=[
            dict(q="Difference between 'x == True' and 'if x:'?",
                 a="'x == True' only passes for x equal to 1/True. 'if x:' accepts any truthy "
                   "value — the idiomatic check. Neither should appear as '== True' in code."),
            dict(q="What does print(bool('False')) show?",
                 a="True — non-empty string, truthy. Only '' is falsy."),
        ],
    ),
    dict(
        id="loops",
        title="Loops, enumerate & zip",
        level="beginner",
        summary="Python's for-each over any iterable, while loops, break/continue, "
                "and the helpers that replace index bookkeeping.",
        sections=[
            dict(
                heading="for = for-each",
                body="Python's for iterates items directly over ANY iterable: lists, strings, "
                     "dicts, files, generators. range(len(seq)) is the C accent — the Pythonic "
                     "form iterates the sequence itself.",
                code='names = ["Ada", "Grace", "Linus"]\nfor name in names:\n    print(name)\n\nfor name in sorted(names):   # iterate a sorted copy\n    print(name)',
                code_note="for x in dict: gives keys; dict.items() gives pairs.",
            ),
            dict(
                heading="Need the index? enumerate()",
                body="enumerate(seq, start=0) yields (index, item) pairs. It replaces the "
                     "range(len(...)) pattern with something you can't get wrong.",
                code="tasks = [\"parse\", \"clean\", \"train\"]\nfor i, task in enumerate(tasks, start=1):\n    print(f\"{i}. {task}\")",
                code_note="Lazy — it produces pairs on demand, no list built.",
            ),
            dict(
                heading="Parallel lists? zip()",
                body="zip(a, b) walks both in lockstep, stopping at the shorter one. Pass "
                     "strict=True (3.10+) to fail loudly on length mismatch. zip(*pairs) "
                     "transposes — the 'unzip'.",
                code="names = [\"Ada\", \"Grace\"]\nscores = [91, 99, 70]\nfor name, score in zip(names, scores):\n    print(name, score)   # stops after Grace\n\npairs = [(\"a\", 1), (\"b\", 2)]\nletters, numbers = zip(*pairs)",
                code_note="Silent truncation is a bug source — that's why strict=True exists.",
            ),
            dict(
                heading="break, continue, and loop-else",
                body="break exits the loop; continue skips to the next iteration. The rare "
                     "loop-else runs only if the loop finished WITHOUT break — a search idiom "
                     "interviewers love to ask about.",
                code="for n in range(2, 30):\n    for d in range(2, n):\n        if n % d == 0:\n            break          # composite\n    else:\n        print(n, \"is prime\")  # no break -> prime",
                code_note="while True + break is the standard 'repeat until valid' pattern.",
            ),
        ],
        key_points=[
            "Iterate items, not indices; enumerate() when you need the counter.",
            "zip() for parallel iteration; strict=True to catch mismatched lengths.",
            "loop-else runs only without break.",
            "while for unknown iteration counts; for for known iterables.",
        ],
        interview_questions=[
            dict(q="What can you loop over in Python?",
                 a="Anything iterable — anything with __iter__ or __getitem__: containers, "
                   "files, range, generators, zip/enumerate results..."),
            dict(q="Why is 'for i in range(len(items))' discouraged?",
                 a="It obscures intent and invites off-by-one bugs; iterate items directly or "
                   "use enumerate when the index is truly needed."),
        ],
    ),
    dict(
        id="functions",
        title="Functions & Arguments",
        level="beginner",
        summary="def, return, default-argument pitfalls, *args/**kwargs, keyword-only "
                "arguments, and first-class functions.",
        sections=[
            dict(
                heading="def, return and scope",
                body="def creates a function object and binds it to a name; the body runs only "
                     "on call. Every function returns something — no return means None. The "
                     "'I set the variable but it changed nothing' bug is usually a missing "
                     "return.",
                code="def add_tax(price, rate=0.2):\n    return price * (1 + rate)\n\ntotal = add_tax(100)          # 120.0\ntotal = add_tax(100, 0.05)    # positional\ntotal = add_tax(100, rate=0.1)  # keyword — self-documenting",
                code_note="Functions returning None accidentally is a classic bug — check your returns.",
            ),
            dict(
                heading="Defaults are evaluated ONCE",
                body="Default values are created when the def line executes — one object, "
                     "shared by every call using the default. Mutable defaults are THE famous "
                     "Python trap; the fix is the None sentinel.",
                code="def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items",
                code_note="Interviewers ask this constantly — know the WHY (definition-time "
                          "evaluation), not just the fix.",
            ),
            dict(
                heading="*args, **kwargs and keyword-only",
                body="*args collects extra positionals into a tuple; **kwargs collects extra "
                     "keywords into a dict. A bare * in the signature forces keyword-only "
                     "parameters — you see it in modern library APIs because it prevents "
                     "positional mistakes.",
                code="def summary(title, *lines, sep=\" | \", **options):\n    print(title, sep.join(lines), options)\n\nsummary(\"Log\", \"start\", \"ok\", verbose=True)\n# Log start|ok {'verbose': True}",
                code_note="Order: positional, *args, keyword-only, **kwargs.",
            ),
            dict(
                heading="Functions are objects",
                body="Functions can be stored, passed, returned — the basis of callbacks, "
                     "sorted(key=...), decorators, and strategy patterns. Docstrings "
                     "(__doc__), annotations and __name__ are all attributes you can read.",
                code="def apply(fn, value):\n    return fn(value)\n\nprint(apply(abs, -5))                 # 5\nprint(apply(lambda s: s.upper(), \"x\"))  # X",
                code_note="sorted(records, key=lambda r: r['score']) — the everyday use.",
            ),
        ],
        key_points=[
            "No return => returns None. Multiple values = a tuple that unpacks.",
            "Mutable defaults are shared across calls — use None sentinel.",
            "Order: positional, *args, keyword-only (bare *), **kwargs.",
            "Functions are first-class: pass them, return them, decorate them.",
        ],
        interview_questions=[
            dict(q="What does this print: def f(x, l=[]): l.append(x); return l — after f(1), f(2)?",
                 a="[1, 2] then [1, 2, 2]... precisely: f(1) -> [1]; f(2) -> [1, 2] because the "
                   "default list is shared. The None-sentinel fix avoids it."),
            dict(q="How do you return two values?",
                 a="return a, b returns a tuple; callers unpack: lo, hi = bounds(data)."),
            dict(q="What is a keyword-only argument and why force one?",
                 a="A parameter after a bare * must be passed by name — prevents positional "
                   "mix-ups in boolean-style flags (connect(host, *, timeout=10))."),
        ],
    ),
    dict(
        id="scoping",
        title="Scope, Closures & LEGB",
        level="intermediate",
        summary="How Python resolves names (LEGB), why assignment creates locals, "
                "global/nonlocal, and how closures capture variables.",
        sections=[
            dict(
                heading="LEGB rule",
                body="Name lookup order: Local (inside the function) -> Enclosing (outer "
                     "functions) -> Global (module) -> Builtins. Python decides a name is "
                     "LOCAL if you assign to it anywhere in the function — unless declared "
                     "global/nonlocal.",
                code="x = \"global\"\ndef outer():\n    x = \"enclosing\"\n    def inner():\n        print(x)      # LEGB: finds enclosing\n    inner()\nouter()               # enclosing",
                code_note="Reading follows LEGB; ASSIGNING creates a local by default.",
            ),
            dict(
                heading="UnboundLocalError explained",
                body="If a function assigns to x ANYWHERE, x is local for the whole function. "
                     "Reading it before the assignment line raises UnboundLocalError — even if "
                     "a global x exists. That's why 'count += 1' without 'global count' fails: "
                     "the read happens before the local is born.",
                code="total = 0\ndef bump():\n    # total += 1 -> UnboundLocalError!\n    global total\n    total += 1\nbump()\nprint(total)   # 1",
                code_note="Cleaner design: return the new value instead of mutating globals.",
            ),
            dict(
                heading="Closures capture variables, not values",
                body="Inner functions remember the ENCLOSING variable itself (late binding). "
                     "All closures over the same loop variable see its FINAL value. Freeze the "
                     "value with a default argument, or a factory function.",
                code="def make_adders():\n    return [lambda x, i=i: x + i for i in range(3)]  # i=i binds now\n\nprint([a(10) for a in make_adders()])   # [10, 11, 12]\n# without the default: [12, 12, 12]",
                code_note="nonlocal lets inner functions REBIND enclosing names (state in "
                          "closures/decorators).",
            ),
        ],
        key_points=[
            "Lookup: Local -> Enclosing -> Global -> Builtins.",
            "Assignment makes a name local for the whole function body.",
            "global/nonlocal let you REBIND outer names — use sparingly.",
            "Closures capture variables (late binding); freeze with default args.",
        ],
        interview_questions=[
            dict(q="Predict: functions from a loop appending lambda: i — what do they return after the loop?",
                 a="All return the final i (late binding). Fix with lambda i=i: i or a factory."),
            dict(q="Why does reading a global inside a function work, but writing fails?",
                 a="Reads follow LEGB and find the global. Assignment would create a NEW local "
                   "(Python's rule), so 'x += 1' fails on the read of the unborn local."),
        ],
    ),
    dict(
        id="comprehensions",
        title="Comprehensions & Generator Expressions",
        level="intermediate",
        summary="The one-line loop idioms every reviewer expects: list/set/dict "
                "comprehensions, filtering, nesting, and when to stay lazy.",
        sections=[
            dict(
                heading="Transform + filter in one line",
                body="[expr for x in it if cond] reads left to right: 'for each x, keep it if "
                     "cond, and put expr in the result'. In Python 3 comprehensions have their "
                     "OWN scope — the loop variable doesn't leak.",
                code="nums = range(10)\nsquares = [n * n for n in nums]\nevens   = [n for n in nums if n % 2 == 0]\nlabels  = [f\"{n:02d}\" for n in nums]",
                code_note="Equivalent loop+append, but ~20-30% faster and more scannable.",
            ),
            dict(
                heading="Dict & set comprehensions",
                body="Same shape with braces: {k_expr: v_expr for ...} builds dicts; "
                     "{expr for ...} builds sets. Perfect for invert-a-map and "
                     "normalize-then-dedup one-liners.",
                code="words = [\"Py\", \"py\", \"WEB\"]\nlengths = {w.lower(): len(w) for w in words}\nunique  = {w.lower() for w in words}\nprint(lengths, unique)",
                code_note="Duplicate keys keep the LAST value — know that when inverting maps.",
            ),
            dict(
                heading="Generator expressions: lazy comprehensions",
                body="Swap [] for () and you get an iterator that computes values on demand — "
                     "O(1) memory for huge data. Inside a single function call, the parens "
                     "can be dropped: sum(n * n for n in nums).",
                code="total = sum(len(line) for line in open(\"big.log\"))\nfirst_big = next((w for w in words if len(w) > 10), None)",
                code_note="Generators can be consumed ONCE — list(gen) after sum(gen) is empty.",
            ),
            dict(
                heading="Taste: when NOT to",
                body="If the comprehension needs nested fors + ifs spanning lines, or side "
                     "effects, a plain loop is more readable. Complex one-liners defeat the "
                     "purpose — comprehensions are for transform/filter, not orchestration.",
                code="# too clever:\nmatrix = [[1, 2], [3, 4]]\nflat_doubled = [x * 2 for row in matrix for x in row if x % 2 == 0]  # ok-ish\n# prefer loops beyond this complexity",
                code_note="Rule of thumb: can you read it aloud? If not, use a loop.",
            ),
        ],
        key_points=[
            "[f(x) for x in xs if c] — transform + filter; own scope in Py3.",
            "{} with colon = dict comp; {} without = set comp.",
            "genexp: lazy, single-use, O(1) memory; parens droppable in calls.",
            "Readability first — nested comps beyond two fors belong in loops.",
        ],
        interview_questions=[
            dict(q="Difference between a list comp and a generator expression?",
                 a="Eager list vs lazy iterator. Memory O(n) vs O(1); reusable vs single-use. "
                   "Use genexps inside sum/any/all/max for large data."),
            dict(q="Flatten a matrix in one line?",
                 a="[x for row in matrix for x in row] — fors read in loop order."),
        ],
    ),
    dict(
        id="errors",
        title="Exceptions & Error Handling",
        level="intermediate",
        summary="try/except/else/finally, raising your own errors, the EAFP philosophy, "
                "and how to catch precisely instead of swallowing.",
        sections=[
            dict(
                heading="The four blocks",
                body="try: risky code. except SpecificError as e: recovery. else: runs only if "
                     "no exception. finally: ALWAYS runs — cleanup. Catch the narrowest "
                     "exception you can handle; let everything else propagate to someone who "
                     "can.",
                code='try:\n    value = int(raw)\nexcept ValueError as e:\n    print(f"bad number: {e}")\nelse:\n    print("parsed", value)\nfinally:\n    print("attempt finished")',
                code_note="Exception hierarchy: lookup order matters — put specific excepts first.",
            ),
            dict(
                heading="EAFP vs LBYL",
                body="Easier to Ask Forgiveness than Permission: try the operation, handle the "
                     "exception. Look Before You Leap: pre-check with if. Python favours EAFP "
                     "— it avoids races (file can vanish between check and open) and is often "
                     "faster because the happy path has no checks.",
                code='# LBYL\nif "price" in item:\n    total += item["price"]\n\n# EAFP (pythonic)\ntry:\n    total += item["price"]\nexcept KeyError:\n    pass',
                code_note="Interview: 'How would you handle a missing dict key?' — mention both, "
                          "prefer EAFP or .get().",
            ),
            dict(
                heading="Raising well: messages, chaining, bare raise",
                body="Raise specific types with actionable messages. 'raise X from err' keeps "
                     "the original cause in the traceback. Inside except, a bare 'raise' "
                     "re-raises unchanged — log-and-propagate without destroying context.",
                code="def parse_age(text):\n    try:\n        return int(text)\n    except ValueError as err:\n        raise ValueError(f\"age must be an integer, got {text!r}\") from err",
                code_note="Custom errors: class ConfigError(Exception): pass — a name says why.",
            ),
        ],
        key_points=[
            "Catch specific exceptions; bare except hides KeyboardInterrupt and bugs.",
            "else = no-exception path; finally = always cleanup.",
            "EAFP is the Pythonic default; use .get() for expected misses.",
            "raise ... from err preserves the cause; bare raise re-raises intact.",
        ],
        interview_questions=[
            dict(q="Can finally override a return?",
                 a="Yes — a return in finally replaces any earlier return/exception. Never put "
                   "control flow in finally."),
            dict(q="except Exception vs bare except?",
                 a="Both catch most things, but bare except also catches KeyboardInterrupt/"
                   "SystemExit and needs no name. Prefer 'except Exception as e' minimum, "
                   "specific types ideally."),
        ],
    ),
    dict(
        id="files",
        title="Files & Context Managers",
        level="intermediate",
        summary="Reading/writing files safely with 'with', path handling with "
                "pathlib, and building your own context managers.",
        sections=[
            dict(
                heading="with open(...) as f",
                body="The with statement guarantees __exit__ runs — the file closes even if an "
                     "exception fires mid-block. Modes: 'r' read (default), 'w' truncate, 'a' "
                     "append, 'x' create-fail-if-exists; add 'b' for bytes. Encoding is not "
                     "optional on Windows — always pass it for text.",
                code='with open("notes.txt", "w", encoding="utf-8") as f:\n    f.write("line 1\\n")\n\nwith open("notes.txt", encoding="utf-8") as f:\n    for line in f:            # streams lazily, O(1) memory\n        print(line.rstrip())',
                code_note="'for line in f' beats f.readlines() for big files — lazy iteration.",
            ),
            dict(
                heading="pathlib over string paths",
                body="pathlib.Path joins with /, exists(), read_text(), write_text(), "
                     "glob('*.py') — and it's cross-platform. os.path string surgery is legacy "
                     "style; reviews love pathlib.",
                code='from pathlib import Path\n\ndata = Path("data")\ndata.mkdir(exist_ok=True)\n(data / "notes.txt").write_text("hello\\n", encoding="utf-8")\nprint(sorted(p.name for p in data.glob("*")))',
                code_note="Path(__file__).parent anchors relative paths to the script, not the cwd.",
            ),
            dict(
                heading="Roll your own context manager",
                body="Any object with __enter__/__exit__ works with with. For quick ones, "
                     "@contextmanager turns a generator into a context manager — everything "
                     "before yield is setup, after is cleanup.",
                code="from contextlib import contextmanager\nimport time\n\n@contextmanager\ndef timer(label):\n    start = time.perf_counter()\n    try:\n        yield          # <- body of the with block runs here\n    finally:\n        print(f\"{label}: {time.perf_counter() - start:.3f}s\")\n\nwith timer(\"work\"):\n    sum(range(1_000_000))",
                code_note="Cleanup goes after yield inside try/finally — same guarantee as with "
                          "open().",
            ),
        ],
        key_points=[
            "with = guaranteed cleanup even on exceptions.",
            "Always pass encoding='utf-8' for text files.",
            "Iterate file objects lazily for large files.",
            "pathlib.Path for paths; @contextmanager for custom with-blocks.",
        ],
        interview_questions=[
            dict(q="Why is 'with' better than f = open(); ...; f.close()?",
                 a="close() is skipped if an exception intervenes. with's __exit__ always runs "
                   "— it's try/finally with better syntax."),
            dict(q="How do you read a 10 GB file in Python?",
                 a="Stream it: iterate the file object line by line (or read fixed-size chunks) "
                   "— never f.read() which loads it all into memory."),
        ],
    ),
    dict(
        id="oop",
        title="OOP: Classes, self & Dunders",
        level="intermediate",
        summary="Why self exists, __init__, instance vs class attributes, inheritance, "
                "and the dunder protocol that powers built-in syntax.",
        sections=[
            dict(
                heading="self and __init__",
                body="Methods receive the instance as their first parameter — named self by "
                     "convention. obj.method(x) is really Class.method(obj, x), which is WHY "
                     "self exists explicitly. __init__ initialises the new object after "
                     "creation (it doesn't create it — __new__ does).",
                code="class Account:\n    def __init__(self, owner, balance=0):\n        self.owner = owner\n        self.balance = balance\n\n    def deposit(self, amount):\n        self.balance += amount\n        return self.balance\n\nacc = Account(\"Ada\")\nacc.deposit(100)",
                code_note="Attributes created in __init__ are per-instance; class-body "
                          "attributes are shared — that's the mutable-class-attr trap.",
            ),
            dict(
                heading="Dunders = syntax hooks",
                body="len(x) calls __len__, print(x) calls __str__, a == b calls __eq__, a + b "
                     "calls __add__, iteration uses __iter__/__next__. Implement dunders to "
                     "make your objects feel native. __repr__ is the developer-facing string "
                     "(and fallback for __str__).",
                code='class Point:\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n\n    def __repr__(self):\n        return f"Point({self.x}, {self.y})"\n\n    def __add__(self, other):\n        return Point(self.x + other.x, self.y + other.y)\n\n    def __eq__(self, other):\n        return (self.x, self.y) == (other.x, other.y)\n\nprint(Point(1, 2) + Point(3, 4))   # Point(4, 6)',
                code_note="Interview: __repr__ should be unambiguous/valid-looking Python; "
                          "__str__ is for end users.",
            ),
            dict(
                heading="Inheritance, super() & when not to",
                body="Child classes extend parents; super().__init__() runs parent setup. "
                     "Python resolves methods via the MRO (Class.__mro__). Prefer composition "
                     "for 'has-a'; reserve inheritance for genuine 'is-a'. Duck typing means "
                     "you often don't need a shared base class at all — just the same methods.",
                code="class Shape:\n    def area(self): raise NotImplementedError\n\nclass Circle(Shape):\n    def __init__(self, r):\n        self.r = r\n    def area(self):\n        return 3.14159 * self.r ** 2\n\nshapes = [Circle(1), Circle(2)]\nprint([round(s.area(), 2) for s in shapes])",
                code_note="Polymorphism = same call, type-dependent behaviour — no instanceof "
                          "chains needed.",
            ),
            dict(
                heading="dataclasses remove the boilerplate",
                body="@dataclass writes __init__, __repr__ and __eq__ from annotated fields — "
                     "the modern default for data-carrying classes. frozen=True gives "
                     "immutability; field(default_factory=list) is the safe mutable default.",
                code="from dataclasses import dataclass, field\n\n@dataclass\nclass Cart:\n    owner: str\n    items: list[str] = field(default_factory=list)\n\n    def total(self, price_of):\n        return sum(price_of(i) for i in items)",
                code_note="dataclass + type hints is how modern Python models records.",
            ),
        ],
        key_points=[
            "self is explicit because methods ARE functions called with the instance.",
            "Class attributes are shared; __init__ attributes are per-instance.",
            "Dunders hook built-in syntax: len, +, ==, iteration, printing.",
            "dataclass for records; composition over inheritance.",
        ],
        interview_questions=[
            dict(q="__str__ vs __repr__?",
                 a="__repr__ = unambiguous, developer-facing, fallback for both. __str__ = "
                   "readable, used by print/str. Define __repr__; often __str__ = __repr__."),
            dict(q="What is the MRO?",
                 a="The Method Resolution Order — the C3-linearised search order for attributes "
                   "across the inheritance tree, visible as Class.__mro__. It's why multiple "
                   "inheritance is deterministic in Python."),
            dict(q="What is @staticmethod vs @classmethod?",
                 a="@staticmethod: no implicit first arg — a plain function in the class "
                   "namespace. @classmethod: receives the CLASS (cls) — alternative "
                   "constructors like dict.fromkeys."),
        ],
    ),
    dict(
        id="iterators_generators",
        title="Iterators & Generators",
        level="intermediate",
        summary="The iterator protocol under every for loop, and yield — laziness, "
                "state, pipelines and memory wins.",
        sections=[
            dict(
                heading="The iterator protocol",
                body="iter(obj) returns an iterator (an object with __next__); next(it) gives "
                     "the next value or raises StopIteration. for loops do exactly this "
                     "behind the scenes. Iterables produce fresh iterators; iterators are "
                     "single-use.",
                code="nums = [1, 2, 3]\nit = iter(nums)\nprint(next(it), next(it), next(it))  # 1 2 3\n# next(it) now -> StopIteration (for-loops catch it silently)",
                code_note="One-pass gotcha: zip/map/generators exhaust — sum() then list() gives "
                          "an empty list.",
            ),
            dict(
                heading="yield makes a generator",
                body="A function with yield returns a generator: the body doesn't run until "
                     "you iterate, and it PAUSES at each yield, resuming with all locals "
                     "intact. Perfect for sequences too big to materialise and for infinite "
                     "streams.",
                code="def fibonacci():\n    a, b = 0, 1\n    while True:\n        yield a\n        a, b = b, a + b\n\ngen = fibonacci()\nprint([next(gen) for _ in range(8)])",
                code_note="Calling fibonacci() runs NOTHING — you get a generator object.",
            ),
            dict(
                heading="Pipelines & memory",
                body="Chain generators into lazy pipelines: each stage processes one item at a "
                     "time, so memory stays flat regardless of data size. sum/any/all/max/min "
                     "consume iterables eagerly once — ideal consumers.",
                code="lines = (l.strip() for l in open(\"huge.log\"))   # stage 1\nerrors = (l for l in lines if \"ERROR\" in l)          # stage 2\nfirst = next(errors, None)                             # consume lazily",
                code_note="Interview: 'Process a 100 GB log?' — generator pipeline, O(1) memory.",
            ),
        ],
        key_points=[
            "for = iter() + next() until StopIteration.",
            "yield = lazy function that pauses/resumes with state.",
            "Generators are single-use; wrap with list() to materialise.",
            "Pipelines of generators keep memory O(1) for big data.",
        ],
        interview_questions=[
            dict(q="What does calling a generator function return, and when does the body run?",
                 a="A generator object; the body runs lazily, one segment between yields per "
                   "next()/loop step."),
            dict(q="yield vs return?",
                 a="return ends the function with one value; yield pauses, hands a value out, "
                   "and resumes later — enabling lazy sequences with internal state."),
        ],
    ),
    dict(
        id="decorators",
        title="Decorators",
        level="advanced",
        summary="Functions that wrap functions: the @ syntax, writing your own, "
                "functools.wraps, and the decorators you'll see in real code.",
        sections=[
            dict(
                heading="@x means f = x(f)",
                body="A decorator is a function taking a function and returning a (usually "
                     "enhanced) function. The @ line is pure sugar executed at definition "
                     "time. Because the wrapper replaces the original, use "
                     "functools.wraps to preserve name/docstring.",
                code="import functools, time\n\ndef timed(fn):\n    @functools.wraps(fn)\n    def wrapper(*args, **kwargs):\n        start = time.perf_counter()\n        result = fn(*args, **kwargs)\n        print(f\"{fn.__name__}: {time.perf_counter() - start:.4f}s\")\n        return result\n    return wrapper\n\n@timed\ndef work(n):\n    return sum(range(n))",
                code_note="wrapper(*args, **kwargs) forwards ANY signature — the universal shape.",
            ),
            dict(
                heading="The built-in decorators you'll meet",
                body="@property exposes a method as a read-only attribute; @staticmethod/"
                     "@classmethod attach plain/class functions; @lru_cache memoises pure "
                     "functions (recursive interview questions!); @dataclass builds classes "
                     "from fields; framework decorators (Flask's @app.route) register handlers.",
                code="from functools import lru_cache\n\n@lru_cache(maxsize=None)\ndef fib(n):\n    return n if n < 2 else fib(n - 1) + fib(n - 2)\n\nprint(fib(80))   # instant — without cache this takes longer than the interview",
                code_note="lru_cache turns O(2^n) recursion into O(n) — a one-line flex.",
            ),
            dict(
                heading="Decorators WITH arguments",
                body="Need @repeat(3)? That's a factory returning a decorator: three nesting "
                     "levels. Read it inside-out: repeat(3) -> decorator -> wrapper.",
                code="def repeat(times):\n    def decorator(fn):\n        def wrapper(*args, **kwargs):\n            for _ in range(times):\n                fn(*args, **kwargs)\n        return wrapper\n    return decorator\n\n@repeat(times=3)\ndef ping():\n    print(\"ping\")",
                code_note="If the syntax confuses you, that's normal — walk the levels: "
                          "argument factory, decorator, wrapper.",
            ),
        ],
        key_points=[
            "@deco == f = deco(f), applied at definition time.",
            "Wrappers use *args/**kwargs and functools.wraps.",
            "@property, @lru_cache, @staticmethod/@classmethod, @dataclass are everyday tools.",
            "Decorator with arguments = function returning a decorator.",
        ],
        interview_questions=[
            dict(q="Write a decorator that counts calls.",
                 a="wrapper increments a counter (in a dict/list or via nonlocal) before "
                   "delegating to fn; expose it as wrapper.count. Must use *args/**kwargs."),
            dict(q="Why does the wrapper need functools.wraps?",
                 a="Without it the wrapper's __name__/__doc__ replace the original's, breaking "
                   "debugging, docs and introspection."),
        ],
    ),
    dict(
        id="modules",
        title="Modules, Imports & Environments",
        level="beginner",
        summary="How Python finds code, what __name__ == '__main__' means, packages, "
                "and virtual environments/pip — the practical glue.",
        sections=[
            dict(
                heading="Modules are just files",
                body="Every .py file is a module; import runs the file ONCE and caches it in "
                     "sys.modules. 'import x' gives you x.y access; 'from x import y' binds y "
                     "directly; 'as' renames. A package is a directory of modules (with "
                     "__init__.py for older-style packages).",
                code="import math                     # namespace kept clean\nfrom collections import Counter  # direct binding\nimport numpy as np               # conventional alias\n\nprint(math.sqrt(16), type(Counter))",
                code_note="Circular imports = two modules importing each other; fix by moving "
                          "shared code to a third module or importing inside functions.",
            ),
            dict(
                heading="The __main__ guard",
                body="__name__ equals '__main__' only when the file is run directly; when "
                     "imported it's the module name. The guard keeps import-time side effects "
                     "away — every script's executable code belongs under it.",
                code="def main():\n    print(\"running as a script\")\n\nif __name__ == \"__main__\":\n    main()",
                code_note="This is why tools can import your file for testing without executing "
                          "it.",
            ),
            dict(
                heading="Environments & pip",
                body="A virtual environment is a private site-packages + interpreter pointer. "
                     "Create once per project, activate, pip install. Pin what you use: "
                     "pip freeze > requirements.txt. 'ModuleNotFoundError' is 90% 'installed "
                     "into a different environment'.",
                code="python -m venv .venv\nsource .venv/bin/activate      # Windows: .venv\\Scripts\\activate\npip install requests\npip freeze > requirements.txt",
                code_note="Check where you are: which python / sys.executable."),
        ],
        key_points=[
            "import executes a module once and caches it in sys.modules.",
            "if __name__ == '__main__': separates script execution from import.",
            "One venv per project; requirements.txt for reproducibility.",
            "from x import * pollutes the namespace — avoid it.",
        ],
        interview_questions=[
            dict(q="What happens when Python imports a module twice?",
                 a="Only the first import executes it; later imports reuse the cached module "
                   "object from sys.modules."),
            dict(q="Why avoid 'from module import *'?",
                 a="It dumps unknown names into your namespace, causing shadowing bugs and "
                   "making static analysis/review much harder."),
        ],
    ),
]


def get_lesson(lesson_id: str) -> dict | None:
    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None
