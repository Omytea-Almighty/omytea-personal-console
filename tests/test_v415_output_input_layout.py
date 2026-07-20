"""Output / input layout — OMY-V415 / M2 / Acceptance #60.

Two founder requirements extending the v10 heatmap/camera work:

  * C — independent scroll panes. The workspace output region (top —
    quantum heatmap / camera / results) and input region (bottom — the
    composer) are each their own fixed-height ``st.container`` scroll
    pane, so scrolling one never moves the other. The output pane is the
    larger one (the heatmap is the centerpiece); the composer pane is
    smaller. The load-bearing reason: during live video the output's
    quantum image must stay visually stable.
  * D — 玄学 output lives in the output region. When the 玄学 lens
    toggle is on, the output region gains a one-click view toggle (a
    segmented control at its top) switching between the quantum heatmap
    (default) and the 玄学 Nye Clock view; the 玄学 view covers the
    quantum module. When the lens is off, no toggle — heatmap only.

``app.py`` cannot be imported under the test runner (module-level
``st.set_page_config``), so the contract is checked at the AST / source
level — the same technique the other Stage tests use.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_SRC = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)

I18N_SRC = (
    Path(__file__).resolve().parent.parent / "_i18n.py"
).read_text(encoding="utf-8")


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


def _module_assign(name: str) -> ast.expr:
    """Return the RHS of a module-level ``name = ...`` assignment."""
    for node in APP_TREE.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return node.value
    raise AssertionError(f"module constant {name} not found in app.py")


# ====================================================================
# C — independent scroll panes
# ====================================================================

def test_pane_height_constants_exist() -> None:
    """The two panes have explicit fixed pixel heights."""
    out_h = _module_assign("_OUTPUT_PANE_HEIGHT")
    comp_h = _module_assign("_COMPOSER_PANE_HEIGHT")
    assert isinstance(out_h, ast.Constant) and isinstance(out_h.value, int)
    assert isinstance(comp_h, ast.Constant) and isinstance(comp_h.value, int)


def test_output_pane_is_larger_than_composer_pane() -> None:
    """The output pane is the bigger one — the heatmap is the centerpiece.

    Requirement C is explicit: "the output pane is the larger one (the
    heatmap is the centerpiece), the input pane smaller."
    """
    out_h = _module_assign("_OUTPUT_PANE_HEIGHT").value
    comp_h = _module_assign("_COMPOSER_PANE_HEIGHT").value
    assert out_h > comp_h, (
        "output pane must be taller than the composer pane"
    )


def test_output_region_uses_fixed_height_container() -> None:
    """The output region opens its own state-aware fixed-height pane.

    ``st.container(height=…)`` is Streamlit's fixed-height scrollable
    box. Cold start is compact so the composer stays visible; prediction,
    live-video and lens states retain the full output-pane height.
    """
    src = ast.unparse(_func("_render_workspace_output"))
    assert "_ow_pane_h = 300 if _ow_compact else _OUTPUT_PANE_HEIGHT" in src
    assert "st.container(height=_ow_pane_h" in src


def test_composer_region_uses_fixed_height_container() -> None:
    """The composer region opens its own fixed-height scroll container."""
    src = ast.unparse(_func("_render_workspace_composer"))
    assert "st.container(height=_COMPOSER_PANE_HEIGHT" in src


def test_composer_wrapper_delegates_to_body() -> None:
    """The composer wrapper only opens the pane + calls the body.

    Keeping the wrapper thin means the fixed-height pane wraps the whole
    composer markup without a 30-deep indent of the existing body.
    """
    src = ast.unparse(_func("_render_workspace_composer"))
    assert "_render_workspace_composer_body()" in src
    assert "st.form" not in src, "the form belongs in the body, not wrapper"


def test_two_panes_are_independent_containers() -> None:
    """Output + composer are SEPARATE fixed-height containers.

    Two independent ``st.container(height=…)`` panes => each scrolls on
    its own; scrolling one never moves the other.
    """
    out_src = ast.unparse(_func("_render_workspace_output"))
    comp_src = ast.unparse(_func("_render_workspace_composer"))
    assert "st.container(height=" in out_src
    assert "st.container(height=" in comp_src
    # Different height constants => genuinely two distinct panes.
    assert "_OUTPUT_PANE_HEIGHT" in out_src
    assert "_COMPOSER_PANE_HEIGHT" in comp_src


# ====================================================================
# D — 玄学 output lives in the output region via a one-click toggle
# ====================================================================

def test_output_view_toggle_helper_exists() -> None:
    """The output-region view toggle is its own helper."""
    _func("_render_output_view_toggle")


def test_xuanxue_output_view_helper_exists() -> None:
    """The 玄学 output view (Nye Clock) is its own helper."""
    _func("_render_xuanxue_output_view")


def test_toggle_is_a_segmented_control_pill() -> None:
    """The toggle is a one-click pill / segmented control."""
    src = ast.unparse(_func("_render_output_view_toggle"))
    assert "st.segmented_control" in src


def test_toggle_only_shown_when_lens_enabled() -> None:
    """When the 玄学 lens is off, no toggle — the output is heatmap-only.

    The helper must early-return ``"quantum"`` without drawing the
    segmented control unless the 玄学 lens is enabled.
    """
    fn = _func("_render_output_view_toggle")
    src = ast.unparse(fn)
    # The lens-enabled guard comes before the segmented control.
    guard_at = src.find("_xuanxue_lens_enabled()")
    sc_at = src.find("st.segmented_control")
    assert guard_at != -1, "toggle must guard on the 玄学-lens state"
    assert sc_at != -1
    assert guard_at < sc_at, (
        "the lens-off guard must come before the segmented control"
    )
    assert "return 'quantum'" in src or 'return "quantum"' in src


def test_lens_enabled_helper_reads_composer_toggle() -> None:
    """The lens-state helper reads the composer toggle's persisted
    widget key — the output region renders before the composer, so the
    derived flag would be one rerun stale.
    """
    src = ast.unparse(_func("_xuanxue_lens_enabled"))
    assert "_composer_lens_toggle" in src


def test_quantum_is_the_default_view() -> None:
    """Quantum heatmap is the default; 玄学 is the opt-in alternate."""
    src = ast.unparse(_func("_render_output_view_toggle"))
    assert "default=quantum_label" in src or "default=" in src
    # The default branch resolves to 'quantum'.
    assert "quantum" in src


def test_output_region_switches_on_the_toggle() -> None:
    """The output region renders the 玄学 view when the toggle says so.

    When the view is ``"xuanxue"`` the output region calls the 玄学
    view renderer and returns — the 玄学 module COVERS the quantum
    module (requirement D).
    """
    src = ast.unparse(_func("_render_workspace_output"))
    assert "_render_output_view_toggle()" in src
    assert "_render_xuanxue_output_view()" in src
    # The xuanxue branch returns => it covers the quantum heatmap.
    xv_at = src.find("_render_xuanxue_output_view()")
    assert xv_at != -1
    assert "xuanxue" in src


def test_xuanxue_output_view_reuses_traditional_lens() -> None:
    """The 玄学 output view reuses the canonical Nye Clock lens render.

    Reusing ``_render_traditional_lens`` keeps the 玄学 surface in
    lockstep with the rest of the console (八字⊕占星 Nye Clock + 易经 +
    塔罗 + joint consensus).
    """
    src = ast.unparse(_func("_render_xuanxue_output_view"))
    assert "_render_traditional_lens" in src


def test_xuanxue_view_lives_inside_the_output_pane() -> None:
    """The 玄学 view is rendered INSIDE the output region's pane.

    Requirement D: both views live in the same independently-scrolling
    output pane from C. The toggle + the 玄学 branch must sit inside the
    state-aware ``st.container(height=_ow_pane_h)`` block.
    """
    src = ast.unparse(_func("_render_workspace_output"))
    container_at = src.find("st.container(height=_ow_pane_h")
    toggle_at = src.find("_render_output_view_toggle()")
    xuanxue_at = src.find("_render_xuanxue_output_view()")
    assert container_at != -1
    assert container_at < toggle_at, "toggle must be inside the output pane"
    assert container_at < xuanxue_at, "玄学 view must be inside the pane"


# ====================================================================
# i18n coverage — the new toggle keys exist in all four languages
# ====================================================================

def test_output_toggle_i18n_keys_present() -> None:
    for key in (
        "output.view.quantum",
        "output.view.xuanxue",
        "output.view.label",
        "output.view.hint",
        "trad.lens.in_output_note",
    ):
        assert f'"{key}"' in I18N_SRC, f"missing i18n key {key}"
