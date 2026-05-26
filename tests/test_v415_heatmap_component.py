"""Interactive heatmap + camera component — OMY-V415 / M2 / Acceptance #59.

The static server-rendered probability-heatmap SVG was replaced with an
embedded HTML/JS component (``_heatmap_component``) ported from the v10
marketing demo ``marketing/console/Omytea Console v10 — see both at
once.html``. The component:

  * renders the branch × time probability grid (NOW → HORIZON);
  * pixel-diffs video frames ~10 fps so the camera drives the heatmap;
  * shows the camera preview side-by-side with the heatmap;
  * has hover-highlight + click cell popovers.

``app.py`` cannot be imported under the test runner (module-level
``st.set_page_config``), so the ``app.py`` integration is checked at the
AST / source level — the same technique the chatbox-layout tests use.
``_heatmap_component`` itself IS import-safe and is exercised directly.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

import _heatmap_component

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_SRC = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)
COMPONENT_PATH = (
    Path(__file__).resolve().parent.parent / "_heatmap_component.py"
)
COMPONENT_SRC = COMPONENT_PATH.read_text(encoding="utf-8")


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


@dataclass
class _FakeHypothesis:
    label: str
    probability: float
    branch_type: str = "realistic"


# --------------------------------------------------------------------
# branches_to_payload — the server prediction → component JSON bridge
# --------------------------------------------------------------------

def test_branches_to_payload_empty_is_empty_list() -> None:
    """No hypotheses (idle) projects to an empty JSON array."""
    assert _heatmap_component.branches_to_payload([]) == []


def test_branches_to_payload_exports_three_fields() -> None:
    """Each branch exports exactly label, probability, branch_type."""
    out = _heatmap_component.branches_to_payload(
        [_FakeHypothesis("Stay", 0.55, "realistic")]
    )
    assert len(out) == 1
    assert set(out[0].keys()) == {"label", "probability", "branch_type"}
    assert out[0]["label"] == "Stay"
    assert out[0]["probability"] == 0.55
    assert out[0]["branch_type"] == "realistic"


def test_branches_to_payload_clamps_negative_probability() -> None:
    """A negative probability is clamped to 0.0 (defensive)."""
    out = _heatmap_component.branches_to_payload(
        [_FakeHypothesis("X", -0.3)]
    )
    assert out[0]["probability"] == 0.0


def test_branches_to_payload_normalizes_unknown_branch_type() -> None:
    """An unexpected branch_type falls back to 'realistic'."""
    out = _heatmap_component.branches_to_payload(
        [_FakeHypothesis("X", 0.4, "bizarre")]
    )
    assert out[0]["branch_type"] == "realistic"


def test_branches_to_payload_tolerates_bad_probability() -> None:
    """A non-numeric probability does not crash the projection."""
    out = _heatmap_component.branches_to_payload(
        [_FakeHypothesis("X", "not-a-number")]  # type: ignore[arg-type]
    )
    assert out[0]["probability"] == 0.0


def test_branches_to_payload_is_json_serializable() -> None:
    """The payload must round-trip through JSON (it is embedded as JSON)."""
    out = _heatmap_component.branches_to_payload(
        [
            _FakeHypothesis("Best case", 0.3, "wishful"),
            _FakeHypothesis("Worst case", 0.1, "worst"),
        ]
    )
    restored = json.loads(json.dumps(out))
    assert restored == out


# --------------------------------------------------------------------
# The component HTML — structural contract
# --------------------------------------------------------------------

def _build_html(branches: list[dict[str, object]]) -> str:
    payload = json.dumps(branches, ensure_ascii=True)
    strings = {
        "title": "T", "reading": "R", "camera_btn": "Camera",
        "video_btn": "Video", "stop_btn": "Stop",
        "preview_title": "Feed", "watching": "watching",
        "camera_off": "off", "no_motion": "no motion",
        "cell_hint": "hint", "now": "now", "horizon": "6 months",
        "iframe_cam_note": "note", "idle_note": "idle",
        "live_note": "live",
    }
    return _heatmap_component._build_component_html(payload, strings)


def test_component_html_is_well_formed_document() -> None:
    """The component is a complete standalone HTML document."""
    html = _build_html([])
    assert html.lstrip().startswith("<!doctype html>")
    assert "</html>" in html


def test_component_embeds_branch_payload_as_json() -> None:
    """The server branch distribution is embedded as a JS JSON array."""
    branches = [{"label": "Stay", "probability": 0.6,
                 "branch_type": "realistic"}]
    html = _build_html(branches)
    assert "var BRANCHES = " in html
    assert '"label": "Stay"' in html
    assert "0.6" in html


def test_component_has_pixel_diff_motion_loop() -> None:
    """The camera-drives-the-math pixel-diff loop is present."""
    html = _build_html([])
    # 80x45 canvas, 10 fps tick, pixel-diff noise floor, EMA smoothing.
    assert 'id="motion-canvas"' in html
    assert "MOTION_W = 80" in html and "MOTION_H = 45" in html
    assert "MOTION_TICK_MS = 100" in html
    assert "getImageData" in html
    assert "MOTION_SMOOTH" in html  # EMA smoothing


def test_component_has_lazy_rerender_thresholds() -> None:
    """Lazy re-render skips the SVG rebuild on sub-threshold deltas."""
    html = _build_html([])
    assert "RERENDER_C" in html and "RERENDER_I" in html


def test_component_has_side_by_side_layout() -> None:
    """A 'live' class drives the side-by-side camera+heatmap grid."""
    html = _build_html([])
    assert ".stage.live" in html
    assert "grid-template-columns" in html
    # Single-column fallback on narrow viewports.
    assert "@media (max-width: 760px)" in html


def test_component_has_interactive_cell_popover() -> None:
    """Heatmap cells are interactive: hover highlight + click popover."""
    html = _build_html([])
    assert "heatmap-cell" in html
    assert ".heatmap-cell:hover" in html  # hover highlight
    assert 'id="cell-popover"' in html
    assert "showCellPopover" in html


def test_component_has_camera_and_video_controls() -> None:
    """Both the camera button and the video-file path are wired."""
    html = _build_html([])
    assert 'id="btn-camera"' in html
    assert 'id="btn-video"' in html
    assert 'id="file-input"' in html
    assert "handleVideoFile" in html
    assert "getUserMedia" in html


def test_component_surfaces_honest_iframe_camera_note() -> None:
    """A getUserMedia block surfaces an honest note, not a dead button.

    The note element must exist AND the catch/failure paths must reveal
    it — this is the v8 'functionally hollow' regression guard.
    """
    html = _build_html([])
    assert 'id="cam-note"' in html
    # Both the no-API path and the getUserMedia .catch reveal the note.
    assert html.count('$("cam-note").classList.add("show")') >= 2


def test_component_has_now_horizon_axis() -> None:
    """The heatmap carries a NOW → HORIZON time axis."""
    html = _build_html([])
    assert "STR.now" in html and "STR.horizon" in html


def test_component_renders_idle_grid_when_no_branches() -> None:
    """With an empty payload the component builds its own idle grid.

    Iter #7 (design-self-explains): idle row labels were renamed from
    "Branch A...E" (academic) to "Your option 1...5" (self-explains
    "each option you type becomes one row").
    """
    html = _build_html([])
    assert "idleBranches" in html
    # idle mirror of _idle_heatmap_branches: 5 rows, "Option N".
    # (Renamed in iter #11 from "Your option N" — the longer form
    # got truncated by the chart's narrow left gutter.)
    assert "Option 1" in html and "Option 5" in html


def test_heatmap_grid_is_fine_and_compact() -> None:
    """The heatmap uses a fine, compact grid (Acceptance #63).

    The founder rejected oversized cells. The fix: many time columns,
    a narrow left gutter, a short canvas, a per-cell height cap and a
    width-capped column — so every cell reads small + precise rather
    than as an oversized block. Lock those values so they cannot
    silently regress back to the wide 9-column grid.
    """
    html = _build_html([])
    # prediction / idle: 24 fine time columns, not the old 9.
    assert "var ncols = 24;" in html
    # left gutter — was 200 (oversized), then 96 (founder-tight), now
    # 124 (iter #17: the old 96 forced 11-char label truncation; the
    # rotated "outcome branch" caption was removed and the gutter
    # widened so anchor labels read in full without re-ballooning cells.
    assert "PADX_L = 124" in html
    # short canvas + per-cell height cap keep rows from ballooning.
    assert "SVG_H = 206" in html
    assert "MAX_CELL_H = 30" in html
    # the forecast column is width-capped so the SVG is not stretched
    # across the full Console width.
    assert ".forecast {" in html and "max-width: 680px" in html


def test_component_exposes_test_hook() -> None:
    """A window.__omyteaHeatmap hook is exposed for verification."""
    html = _build_html([])
    assert "window.__omyteaHeatmap" in html


def test_component_html_has_no_unfilled_format_slots() -> None:
    """Every {slot} is filled — no stray .format placeholders leak."""
    html = _build_html([{"label": "L", "probability": 0.5,
                         "branch_type": "realistic"}])
    # JS uses {{ }} which collapse to { }. A LEAKED slot would look like
    # {word} with no brace neighbours. Scan for the known slot names.
    for slot in (
        "{payload}", "{title}", "{reading}", "{camera_btn}",
        "{horizon}", "{idle_note}", "{live_note}", "{iframe_cam_note}",
    ):
        assert slot not in html, f"unfilled format slot: {slot}"


# --------------------------------------------------------------------
# app.py integration — the delegating wrapper
# --------------------------------------------------------------------

def test_app_imports_the_component() -> None:
    """app.py imports the heatmap component helpers."""
    assert "from _heatmap_component import" in APP_SRC
    assert "render_heatmap_camera_component" in APP_SRC
    assert "branches_to_payload" in APP_SRC


def test_render_probability_heatmap_delegates_to_component() -> None:
    """_render_probability_heatmap now delegates to the JS component.

    It must NOT still be hand-building a static SVG string.
    """
    src = ast.unparse(_func("_render_probability_heatmap"))
    assert "render_heatmap_camera_component" in src
    assert "branches_to_payload" in src
    # The old static-SVG construction is gone.
    assert "<svg viewBox" not in src


def test_render_probability_heatmap_signature_unchanged() -> None:
    """The wrapper keeps (hypotheses, horizon_label) so call sites work."""
    fn = _func("_render_probability_heatmap")
    arg_names = [a.arg for a in fn.args.args]
    assert arg_names == ["hypotheses", "horizon_label"]


def test_result_path_still_calls_heatmap() -> None:
    """_render_result still drives the heatmap with the real branches."""
    src = ast.unparse(_func("_render_result"))
    assert "_render_probability_heatmap" in src
