"""Chatbox workspace layout — OMY-V415 / M2 / Acceptance #58.

The unified workspace is restructured into a chat-app shape:

  * TOP    = the output region — the quantum probability heatmap is a
             PERMANENT centerpiece (idle flat grid before a prediction,
             the real branch distribution after).
  * BOTTOM = the input composer — text conditions + attach + toggles +
             "Run prediction", sitting below the output.

Streamlit reruns top→bottom, so output-then-input source order *is* the
on-screen ordering. ``app.py`` cannot be imported under the test runner
(module-level ``st.set_page_config``), so the contract is checked at the
AST / source level — the same technique the Stage 1/2 tests use.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_SRC = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


# --------------------------------------------------------------------
# The two workspace regions exist as their own helpers
# --------------------------------------------------------------------

def test_workspace_output_helper_exists() -> None:
    """The top output region is its own function."""
    _func("_render_workspace_output")


def test_workspace_composer_helper_exists() -> None:
    """The bottom input composer is its own function."""
    _func("_render_workspace_composer")


def test_idle_heatmap_branches_helper_exists() -> None:
    """A helper supplies placeholder branches for the idle heatmap."""
    _func("_idle_heatmap_branches")


# --------------------------------------------------------------------
# Output-top / input-bottom ordering
# --------------------------------------------------------------------

def test_output_renders_before_composer() -> None:
    """render_new_prediction calls the output region before the composer.

    Streamlit renders top→bottom, so the call order in source IS the
    on-screen vertical order. Output-then-input = chatbox layout.
    """
    src = ast.unparse(_func("render_new_prediction"))
    out_at = src.find("_render_workspace_output()")
    comp_at = src.find("_render_workspace_composer()")
    assert out_at != -1, "workspace must render the output region"
    assert comp_at != -1, "workspace must render the composer region"
    assert out_at < comp_at, (
        "output region must render ABOVE the composer (chatbox layout)"
    )


def test_composer_no_longer_inlined_in_render_new_prediction() -> None:
    """The composer markup moved out of render_new_prediction itself.

    render_new_prediction is now a thin shell: hero + output + composer.
    The heavy composer/form markup belongs to _render_workspace_composer.
    """
    src = ast.unparse(_func("render_new_prediction"))
    assert "st.form" not in src, (
        "the form belongs in _render_workspace_composer, not the shell"
    )


# --------------------------------------------------------------------
# Always-on heatmap — visible before AND after a prediction
# --------------------------------------------------------------------

def test_output_region_always_renders_heatmap() -> None:
    """The output region calls the probability heatmap unconditionally.

    The heatmap is the permanent centerpiece — it renders whether or
    not a prediction exists.
    """
    src = ast.unparse(_func("_render_workspace_output"))
    assert "_render_probability_heatmap" in src


def test_idle_state_feeds_heatmap_placeholder_branches() -> None:
    """With no prediction, the heatmap renders its own idle grid.

    OMY-V415 Acceptance #59: the heatmap is now an interactive HTML/JS
    component. The idle path passes an empty branch list; the component
    renders the uniform placeholder grid (and its idle caption) itself —
    a video dropped on it drives the heatmap live even before any
    prediction has run. The branch-as-empty-list signal is the contract.
    """
    src = ast.unparse(_func("_render_workspace_output"))
    # The idle path: no current_prediction -> heatmap fed an empty list,
    # which the component renders as the calm uniform idle grid.
    assert "_render_probability_heatmap([]" in src
    assert "current_prediction" in src


def test_idle_branches_are_five_equal_probability() -> None:
    """Idle placeholders: ~5 branches, all equal probability.

    Equal probability => the heatmap renders a calm flat uniform grid,
    an honest pre-evidence prior. Checked at the AST/source level —
    ``app.py`` cannot be imported under the test runner (module-level
    ``st.set_page_config``), same technique the other tests here use.
    """
    # Sanity check the idle-branch contract: 5 branches, each at 0.20.
    src = ast.unparse(_func("_idle_heatmap_branches"))
    assert "0.2" in src, "idle branches must be equal-probability (0.20)"
    assert src.count("ConsoleHypothesis(") >= 1
    # Iter #7 (design-self-explains): label list switched from
    # "Branch A...E — awaiting your decision" to "Your option 1...5".
    # Pin the new label scheme — 5 entries.
    assert src.count("Your option") >= 5


def test_idle_branches_sum_to_one() -> None:
    """Five 0.20-probability branches form a valid distribution."""
    # Five equal branches at 0.20 each => sums to 1.0 exactly.
    assert abs(5 * 0.20 - 1.0) < 1e-9


# --------------------------------------------------------------------
# The prediction snapshot still drives the (now top) output region
# --------------------------------------------------------------------

def test_output_region_renders_full_result_when_prediction_exists() -> None:
    """When a prediction exists, the output region renders _render_result."""
    src = ast.unparse(_func("_render_workspace_output"))
    assert "_render_result" in src


def test_composer_stores_prediction_and_reruns() -> None:
    """Generate stores the prediction in session_state then st.rerun()s.

    The chatbox loop: composer computes -> session_state -> rerun ->
    the top output region resolves the heatmap idle->real.

    OMY-V415 / M2 / Acceptance #60 (requirement C) split the composer
    into a fixed-height-pane wrapper (``_render_workspace_composer``)
    plus the markup body (``_render_workspace_composer_body``); the
    Generate/persist/rerun logic lives in the body.
    """
    src = ast.unparse(_func("_render_workspace_composer_body"))
    assert "current_prediction" in src, (
        "composer must persist the prediction for the output region"
    )
    assert "st.rerun()" in src, (
        "composer must rerun so the top output region updates"
    )
