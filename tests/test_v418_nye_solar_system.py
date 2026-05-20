"""Nye Clock 玄学 view — the real Nye Clock, embedded static.

[OMY-V415 / M2 / Acceptance #64] The founder compared the hand-built
static-SVG recreation of the Nye Clock against the real Nye Clock app,
screenshot for screenshot, and ruled the real app decisively better
looking. Per the founder's instruction —

    "直接嵌入真正的 Nye Clock 的 UI 设计吧，不过我们只要完全静态的
     Nye Clock 就好不需要任何需要计算的运动"

— the 玄学 view no longer hand-draws the celestial scene in SVG. It
embeds a COMPLETELY STATIC, high-resolution still captured off the real
Nye Clock 3-D scene (``~/Downloads/UCSB/Adonyth/tw_.html``): a single
base64 JPEG inside a lightweight SVG. No WebGL, no Three.js, no
``<canvas>``, no animation — it embeds verbatim via ``st.markdown`` and
costs zero per-frame computation.

Omytea's own decision numbers — the focal MODEL probability and the
玄学 consensus — render beneath the still as a clean readout strip, so
the panel still carries live output.

These tests pin: (1) the view is an SVG embedding the real Nye Clock
still; (2) the still asset is a real JPEG; (3) the view is GPU-free and
completely static; (4) the readout strip carries the data-driven
numbers.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _clock  # noqa: E402
import _metaphysics as mp  # noqa: E402


def _readings(year: int = 1993, month: int = 7, day: int = 4,
              hour: int = 15) -> tuple:
    bd = mp.BirthData(year, month, day, hour)
    rb = mp.compute_reading("bazi", birth=bd, seed="nye",
                            outcome="career_success")
    ra = mp.compute_reading("astro", birth=bd, seed="nye",
                            outcome="career_success")
    return rb, ra


def _render(rb, ra, top_value: str = "62%",
            bottom_value: str = "55%") -> str:
    return _clock.render_celestial_svg(
        rb, ra,
        [("branch_a", 0.4, "realistic"), ("branch_b", 0.3, "realistic")],
        center_top_label="MODEL", center_top_value=top_value,
        center_bottom_label="玄学 CONSENSUS", center_bottom_value=bottom_value,
        center_meta="mixture · alpha 0.30",
    )


def _strip_data_uri(svg: str) -> str:
    """Drop base64 payloads so token scans test the SVG structure only."""
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,", svg)


# --------------------------------------------------------------------
# the view is an SVG embedding the real Nye Clock still
# --------------------------------------------------------------------

def test_lens_is_an_svg() -> None:
    """The view embeds verbatim through st.markdown — it is one SVG."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert svg.startswith("<svg ") and svg.endswith("</svg>")


def test_lens_viewbox_is_the_still_plus_readout() -> None:
    """The viewBox is the 1200x845 still plus the 100px readout strip."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert 'viewBox="0 0 1200 945"' in svg


def test_lens_embeds_the_real_nye_clock_still() -> None:
    """The celestial scene is a real Nye Clock still — a base64 JPEG
    inside an SVG <image>, NOT a hand-drawn recreation."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "<image " in svg
    assert "data:image/jpeg;base64," in svg


def test_still_asset_is_a_real_jpeg() -> None:
    """The shipped still (assets/nye_clock.jpg) is a genuine JPEG."""
    b64 = _clock._NYE_CLOCK_STILL_B64
    assert b64, "the Nye Clock still asset must be present"
    raw = base64.b64decode(b64)
    # JPEG magic bytes
    assert raw[:3] == b"\xff\xd8\xff"
    assert len(raw) > 10_000, "the still must be a real, sizeable image"


def test_photo_layout_constants() -> None:
    """The still + readout-strip layout constants are sane."""
    assert _clock._NYE_PHOTO_W == 1200
    assert _clock._NYE_PHOTO_H == 845
    assert _clock._NYE_STRIP_H == 100


def test_lens_has_instrument_wordmark() -> None:
    """A discreet 'NYE CLOCK' wordmark labels the instrument panel."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "NYE CLOCK" in svg


# --------------------------------------------------------------------
# completely static — no WebGL / canvas / animation / computation
# --------------------------------------------------------------------

def test_lens_is_gpu_free_and_static() -> None:
    """CRITICAL — the founder asked for a COMPLETELY STATIC Nye Clock
    with no motion that requires computation. The view must carry no
    WebGL / Three.js / <canvas> / <script> / animation of any kind.
    """
    rb, ra = _readings()
    structure = _strip_data_uri(_render(rb, ra)).lower()
    for forbidden in (
        "<script", "<canvas", "webgl", "three.js", "three.min",
        "requestanimationframe", "<iframe", "<animate",
        "<animatetransform",
    ):
        assert forbidden not in structure, \
            f"the static view must be free of: {forbidden}"


def test_lens_is_lightweight_enough_to_embed() -> None:
    """One inline JPEG — the SVG stays small enough to embed verbatim."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert len(svg) < 400_000


# --------------------------------------------------------------------
# the readout strip carries Omytea's live decision numbers
# --------------------------------------------------------------------

def test_readout_carries_model_and_consensus() -> None:
    """The MODEL value and the 玄学-consensus value both render, with
    their labels, beneath the still."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "62%" in svg
    assert "55%" in svg
    assert "MODEL" in svg
    assert "CONSENSUS" in svg


def test_readout_is_data_driven() -> None:
    """The celestial still is fixed, but the readout is data-driven —
    different decision numbers yield a different SVG."""
    rb, ra = _readings()
    a = _render(rb, ra, top_value="62%", bottom_value="55%")
    b = _render(rb, ra, top_value="71%", bottom_value="48%")
    assert a != b
    assert "71%" in b and "48%" in b
