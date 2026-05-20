"""Live-video output surface = the v10 demo embedded WHOLE.

OMY-V415 / M2 / Acceptance #65.

Previous attempts RECREATED the v10 marketing demo's live-video piece by
piece inside Streamlit (heatmap as a separate component, camera separate,
layout via ``st.container``). Every piece degraded below the v10 demo.

This change STOPS recreating. The v10 file is a single complete, working
HTML/JS app — camera + pixel-diff motion loop + live heatmap +
see-both-at-once layout, all integrated. It is copied verbatim into
``static/live_video_v10.html`` and, when the composer's "Live video"
toggle is on, embedded WHOLE as the output surface.

The camera — the one hard part — is solved by embedding the v10 file
through a **top-document iframe** written with
``st.markdown(unsafe_allow_html=True)``, carrying
``allow="camera; microphone; fullscreen"``. That iframe sits in the TOP
Streamlit document (which CAN hold a camera permission grant), NOT inside
a permission-stripped ``components.html`` sandbox. A prominent
"▸ Open live video" button opens the same v10 static URL in a new tab as
the guaranteed-working fallback.

``app.py`` cannot be imported under the test runner (module-level
``st.set_page_config``), so its integration is checked at the AST /
source level — the same technique the other v415 tests use.
``_heatmap_component`` is import-safe and is exercised directly with a
minimal fake ``st``.
"""

from __future__ import annotations

import ast
import importlib
import sys
import types
from pathlib import Path

import pytest

import _heatmap_component

CONSOLE_DIR = Path(__file__).resolve().parent.parent
APP_PATH = CONSOLE_DIR / "app.py"
APP_SRC = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)
STATIC_DIR = CONSOLE_DIR / "static"
CONFIG_PATH = CONSOLE_DIR / ".streamlit" / "config.toml"
V10_SOURCE = (
    CONSOLE_DIR.parent
    / "marketing"
    / "console"
    / "Omytea Console v10 — see both at once.html"
)


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


# --------------------------------------------------------------------
# The v10 static asset — copied WHOLE, byte-identical to the marketing
# demo (the founder's instruction: embed v10 whole, do not recreate).
# --------------------------------------------------------------------

def test_v10_static_asset_exists() -> None:
    """The v10 app is shipped as a static file the console can serve."""
    asset = STATIC_DIR / _heatmap_component.LIVE_VIDEO_V10_FILE
    assert asset.is_file(), f"{asset} missing"


def test_v10_static_asset_is_verbatim_copy_of_marketing_demo() -> None:
    """The static asset is the v10 file embedded WHOLE — byte-identical.

    Not a recreation, not a port — a verbatim copy. This is the whole
    point of Acceptance #65: the live-video surface BECOMES the v10
    file, one integrated unit.

    The ``marketing/`` source tree lives only in the monorepo; the
    standalone public mirror ships ``static/live_video_v10.html``
    without it. Where the source is absent the byte-equality guard is
    moot — skip rather than fail, so the suite is green in both
    checkouts.
    """
    if not V10_SOURCE.is_file():
        pytest.skip("v10 marketing source absent (standalone mirror)")
    asset = STATIC_DIR / _heatmap_component.LIVE_VIDEO_V10_FILE
    assert asset.read_bytes() == V10_SOURCE.read_bytes()


def test_v10_static_asset_is_a_complete_app() -> None:
    """The copied file is a complete HTML app, not a fragment."""
    asset = STATIC_DIR / _heatmap_component.LIVE_VIDEO_V10_FILE
    html = asset.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in html
    # v10's own integrated pieces: camera button, scenario picker,
    # pixel-diff motion loop, getUserMedia — all in the one file.
    assert 'id="input-camera"' in html
    assert 'id="scenario-card"' in html
    assert "getUserMedia" in html
    assert "live_perception" in html


# --------------------------------------------------------------------
# render_live_video_v10 — exercised directly with a fake ``st``.
#
# The embed has NO serving dependency: ``enableStaticServing`` is not
# honoured on Streamlit Community Cloud, and GitHub raw / jsDelivr serve
# ``.html`` as ``text/plain``. So the v10 app is inlined whole into a
# top-document ``<iframe srcdoc="…">`` — same-origin, camera works.
# --------------------------------------------------------------------

class _FakeSt:
    """Minimal fake Streamlit recording the calls the embed makes."""

    def __init__(self) -> None:
        self.markdown_calls: list[tuple[str, dict]] = []
        self.caption_calls: list[str] = []
        self.error_calls: list[str] = []

    def markdown(self, body: str, **kw: object) -> None:
        self.markdown_calls.append((body, kw))

    def caption(self, body: str, **kw: object) -> None:
        self.caption_calls.append(body)

    def error(self, body: str, **kw: object) -> None:
        self.error_calls.append(body)


def _render_with_fake_st() -> _FakeSt:
    """Reload ``_heatmap_component`` with a fake ``st`` and render once."""
    fake = _FakeSt()
    real_st = sys.modules.get("streamlit")
    fake_module = types.ModuleType("streamlit")
    for attr in ("markdown", "caption", "error"):
        setattr(fake_module, attr, getattr(fake, attr))
    # components.v1.html is referenced at import time elsewhere in the
    # module; provide a no-op so the import stays clean.
    comp_v1 = types.ModuleType("streamlit.components.v1")
    comp_v1.html = lambda *a, **k: None
    components = types.ModuleType("streamlit.components")
    components.v1 = comp_v1
    fake_module.components = components
    sys.modules["streamlit"] = fake_module
    sys.modules["streamlit.components"] = components
    sys.modules["streamlit.components.v1"] = comp_v1
    try:
        mod = importlib.reload(_heatmap_component)
        mod.render_live_video_v10()
    finally:
        if real_st is not None:
            sys.modules["streamlit"] = real_st
        importlib.reload(_heatmap_component)
    return fake


def test_render_live_video_v10_embeds_a_top_document_iframe() -> None:
    """The embed writes an <iframe> through st.markdown (top document).

    NOT ``components.html`` — a markdown iframe sits in the top
    Streamlit document, which can hold a camera permission grant.
    """
    fake = _render_with_fake_st()
    assert fake.markdown_calls, "no st.markdown call — no iframe written"
    body, kw = fake.markdown_calls[0]
    assert "<iframe" in body
    assert kw.get("unsafe_allow_html") is True


def test_embedded_iframe_carries_camera_allow_attribute() -> None:
    """The iframe carries ``allow="camera; microphone; fullscreen"``.

    This is the load-bearing attribute: a top-document iframe with this
    ``allow`` value inherits the page's camera permission.
    """
    fake = _render_with_fake_st()
    body = fake.markdown_calls[0][0]
    assert 'allow="camera; microphone; fullscreen"' in body


def test_embedded_iframe_inlines_the_v10_app_via_srcdoc() -> None:
    """The iframe carries the v10 app inline through ``srcdoc``.

    There is no served URL — ``enableStaticServing`` is not honoured on
    Streamlit Community Cloud — so the whole v10 HTML is inlined. A
    ``srcdoc`` iframe is same-origin with the parent, which is what lets
    getUserMedia run inside it.
    """
    fake = _render_with_fake_st()
    body = fake.markdown_calls[0][0]
    assert 'srcdoc="' in body
    # v10's own integrated pieces survive html-escaping unchanged (these
    # tokens carry no <>&"' chars) — proof the WHOLE app is inlined.
    assert "getUserMedia" in body
    assert "input-camera" in body
    assert "scenario-card" in body


def test_embed_has_no_static_serving_url() -> None:
    """No ``app/static`` URL — the embed must not depend on serving."""
    fake = _render_with_fake_st()
    body = fake.markdown_calls[0][0]
    assert "app/static" not in body


def test_embedded_iframe_is_a_single_physical_line() -> None:
    """The iframe markdown is ONE physical line.

    ``st.markdown`` keeps a raw ``<iframe>`` intact only as a single
    HTML block; a newline inside the ``srcdoc`` attribute would split
    the block and spill v10 source as rendered markdown. ``_v10_srcdoc``
    collapses every newline to a numeric ref to guarantee this.
    """
    fake = _render_with_fake_st()
    body = fake.markdown_calls[0][0]
    assert "\n" not in body


def test_embedded_iframe_is_not_a_components_html_sandbox() -> None:
    """The embed must NOT route through ``components.html``.

    ``components.html`` renders inside a sandboxed iframe with no
    ``allow="camera"`` — exactly the path that blocks the camera. The
    embed uses ``st.markdown`` instead; assert no sandbox attribute is
    written on the iframe.
    """
    fake = _render_with_fake_st()
    body = fake.markdown_calls[0][0]
    assert "sandbox" not in body


def test_v10_srcdoc_preserves_the_verbatim_v10_app() -> None:
    """``_v10_srcdoc`` escaping is loss-free; only the scope block is added.

    HTML-unescaping the ``srcdoc`` attribute (what the browser does when
    it parses the iframe) yields the v10 file with exactly one injected
    block — ``_V10_EMBED_SCOPE``. Strip that block back out and the
    result is the v10 file byte-for-byte: the embed runs v10's real
    code, only scoped to the see-both panel.
    """
    import html as _html_mod

    srcdoc = _heatmap_component._v10_srcdoc()
    assert srcdoc is not None
    rebuilt = _html_mod.unescape(srcdoc)
    assert "omytea-embed-scope" in rebuilt
    verbatim = (
        STATIC_DIR / _heatmap_component.LIVE_VIDEO_V10_FILE
    ).read_text(encoding="utf-8")
    stripped = rebuilt.replace(_heatmap_component._V10_EMBED_SCOPE, "", 1)
    assert stripped == verbatim


def test_embed_scope_hides_onboarding_and_forces_side_by_side() -> None:
    """The injected scope block hides v10's onboarding and forces the
    camera | heatmap side-by-side grid at the console's embed width.

    These are the load-bearing CSS rules behind the founder's two
    requirements: the output region holds output only (no v10 input
    chrome), and the camera sits BESIDE the heatmap, not above it.
    """
    scope = _heatmap_component._V10_EMBED_SCOPE
    # Onboarding chrome hidden — output region has no input surface.
    for selector in ("#scenario-card", "#input-file", ".topbar"):
        assert selector in scope
    assert "display:none" in scope
    # Side-by-side grid forced (v10's own grid only fires >=1100px).
    assert "body.camera-active main" in scope
    assert "grid" in scope


# --------------------------------------------------------------------
# app.py integration — the live-video toggle owns the output surface.
# --------------------------------------------------------------------

def test_app_imports_render_live_video_v10() -> None:
    """app.py imports the v10 embed entry point."""
    assert "render_live_video_v10" in APP_SRC


def test_workspace_output_renders_v10_when_live_video_on() -> None:
    """When live video is on, the output region embeds v10 whole.

    The output surface BECOMES the v10 app — the founder's instruction.
    """
    src = ast.get_source_segment(APP_SRC, _func("_render_workspace_output"))
    assert src is not None
    assert "_live_video_enabled()" in src
    assert "render_live_video_v10()" in src


def test_live_video_enabled_helper_reads_composer_toggle() -> None:
    """``_live_video_enabled`` reads the persisted composer toggle key.

    The output region renders before the composer on a Streamlit rerun,
    so it must read the toggle WIDGET key directly.
    """
    src = ast.get_source_segment(APP_SRC, _func("_live_video_enabled"))
    assert src is not None
    assert "_composer_live_toggle" in src


def test_non_video_default_is_still_the_quantum_heatmap() -> None:
    """Live video is opt-in; the heatmap stays the non-video default.

    With the toggle off, the idle / prediction quantum heatmap still
    renders — the live-video embed must not displace the default.
    """
    src = ast.get_source_segment(APP_SRC, _func("_render_workspace_output"))
    assert src is not None
    # The idle path still calls the heatmap component.
    assert "_render_probability_heatmap" in src
    # The live-video branch returns early — it does not run alongside.
    assert src.index("_live_video_enabled()") < src.index(
        "_render_probability_heatmap"
    )


def test_composer_does_not_recreate_a_webcam_panel() -> None:
    """The composer no longer embeds a recreated webcam panel inline.

    The live-video experience is the v10 app in the output region — the
    composer only confirms the toggle is on; it must not re-embed
    ``render_live_webcam`` (the old recreated path).
    """
    src = ast.get_source_segment(
        APP_SRC, _func("_render_workspace_composer_body")
    )
    assert src is not None
    assert "render_live_webcam" not in src
