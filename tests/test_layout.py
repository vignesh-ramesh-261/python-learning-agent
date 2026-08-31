"""Structural checks on the page layout.

There is no browser in this environment, so these assert the DOM/CSS contract
the visualizer depends on. They exist because the card twice ended up somewhere
unusable: first squeezed into the narrow results column, then pushed below eight
stacked analysis cards where nobody would ever scroll to find it.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = (ROOT / "templates" / "index.html").read_text()
CSS = (ROOT / "static" / "style.css").read_text()
JS = (ROOT / "static" / "app.js").read_text()


def grid_children(container_class: str) -> list:
    """Class attributes of the direct <div> children of a grid container."""
    start = HTML.index(f'<div class="{container_class}">')
    depth, kids = 0, []
    for match in re.finditer(r"<(/?)div\b([^>]*)>", HTML[start:]):
        closing, attrs = match.groups()
        if closing:
            depth -= 1
            if depth == 0:
                break
        else:
            if depth == 1:
                found = re.search(r'class="([^"]*)"', attrs)
                kids.append(found.group(1) if found else "")
            depth += 1
    return kids


def test_visualizer_is_a_direct_child_of_the_explain_grid():
    """Nested in .results-col it was ~660px wide with a ~339px code pane."""
    assert any("viz-card" in k for k in grid_children("explain-grid"))


def test_visualizer_is_the_first_grid_child():
    """As the last child it opened below every analysis card, off screen."""
    kids = grid_children("explain-grid")
    assert "viz-card" in kids[0], f"visualizer is child #{kids.index(next(k for k in kids if 'viz-card' in k)) + 1}"


def test_visualizer_spans_both_columns_and_is_pinned_to_the_top_row():
    block = CSS[CSS.index(".viz-card {"):]
    rule = block[: block.index("}")]
    assert "grid-column: 1 / -1" in rule
    assert "grid-row: 1" in rule


def test_visualizer_starts_hidden_so_it_costs_no_space_when_unused():
    match = re.search(r'<div class="([^"]*viz-card[^"]*)"', HTML)
    assert match and "hidden" in match.group(1)
    assert re.search(r"\.hidden\s*{[^}]*display:\s*none", CSS)


def test_internal_breakpoint_matches_the_container_not_the_old_viewport_guess():
    """The card is full width now, so it must collapse with the page grid."""
    assert "@media (max-width: 980px) { .viz-grid" in CSS


def test_stepping_scrolls_the_code_pane_not_the_whole_page():
    viz = JS[JS.index("/* ---------------------------------------------------------- visualizer */"):]
    assert "sourceEl.scrollTop" in viz
    assert ".viz-line.active\").scrollIntoView" not in viz


def test_every_element_the_visualizer_queries_exists_in_the_template():
    viz = JS[JS.index("/* ---------------------------------------------------------- visualizer */"):]
    for element_id in sorted(set(re.findall(r'\$\("#(viz-[a-z-]+)"\)', viz))):
        assert f'id="{element_id}"' in HTML, f"{element_id} is queried but missing from the template"
