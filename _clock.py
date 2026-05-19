"""Nye-clock instrument — single centerpiece for the "古法 × 校准" view.

Reframes the founder's earlier critique of v4: "我们要有概率分布函数的输出"
+ ChatGPT/Nye-Clock minimalism. The instrument is one large SVG dial:

  • Outer ring — five 72° sectors, one per 五行 element. The sector's
    radial extent (a wedge of the ring) is proportional to how much
    that element appears in the user's 八字 balance. The wedge colours
    come from `_metaphysics.WUXING_COLOR` and match the v10 palette.

  • Inner ring — the model's calibrated branch probabilities, rendered
    as arcs whose angular span is proportional to probability. Wishful
    and worst anchors get a tag dot at the outer edge.

  • Centre — the dominant 五行 character + the model's headline
    outcome + the combined posterior.

No JS; static SVG drawn server-side from a dict of inputs. The hover
/ scrub interactivity from the marketing v5 mock-up is deliberately
out of scope for the Streamlit surface — we lose nothing important by
keeping it static.
"""

from __future__ import annotations

import html as _html
import math
from typing import Any

from _metaphysics import (
    WUXING_COLOR,
    WUXING_HANZI,
    WUXING_KEYS,
    BaZiPattern,
    pillar_text,
    wuxing_balance,
)


# ----------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------

# Canvas is a square viewBox so the disc renders cleanly at any width.
_VB = 640
_CX = _VB / 2
_CY = _VB / 2

# Ring radii (measured from disc centre).
_R_OUTER = 280   # outer ring outside edge
_R_OUTER_IN = 215  # outer ring inside edge
_R_INNER = 195   # inner ring outside edge
_R_INNER_IN = 145  # inner ring inside edge
_R_CORE = 130    # core circle radius


def _polar(cx: float, cy: float, r: float, theta_deg: float) -> tuple[float, float]:
    """Polar → Cartesian. theta=0 is at 12 o'clock, clockwise positive."""
    theta_rad = math.radians(theta_deg - 90.0)
    return cx + r * math.cos(theta_rad), cy + r * math.sin(theta_rad)


def _arc_path(
    cx: float, cy: float, r_outer: float, r_inner: float,
    theta_start_deg: float, theta_end_deg: float,
) -> str:
    """SVG path for a ring-segment (annulus sector).

    Goes outer-arc clockwise from start→end, jumps inward, inner-arc
    back end→start, then closes. Handles the >180° large-arc-flag.
    """
    if theta_end_deg - theta_start_deg <= 1e-3:
        return ""
    large_arc = 1 if (theta_end_deg - theta_start_deg) > 180 else 0
    x0o, y0o = _polar(cx, cy, r_outer, theta_start_deg)
    x1o, y1o = _polar(cx, cy, r_outer, theta_end_deg)
    x0i, y0i = _polar(cx, cy, r_inner, theta_start_deg)
    x1i, y1i = _polar(cx, cy, r_inner, theta_end_deg)
    return (
        f"M {x0o:.2f} {y0o:.2f} "
        f"A {r_outer:.2f} {r_outer:.2f} 0 {large_arc} 1 {x1o:.2f} {y1o:.2f} "
        f"L {x1i:.2f} {y1i:.2f} "
        f"A {r_inner:.2f} {r_inner:.2f} 0 {large_arc} 0 {x0i:.2f} {y0i:.2f} "
        f"Z"
    )


# ----------------------------------------------------------------------
# Public render
# ----------------------------------------------------------------------

def render_nye_clock_svg(
    bazi: BaZiPattern,
    balance: dict[str, float],
    branch_probabilities: list[tuple[str, float, str]],
    center_headline: str,
    center_subline: str,
    center_meta: str,
) -> str:
    """Render the Nye-clock instrument as an SVG string.

    Parameters
    ----------
    bazi
        The user's 八字 pattern (for the 4 pillar labels around the rim).
    balance
        Wuxing balance dict (keys in _metaphysics.WUXING_KEYS, values
        summing to ~1).
    branch_probabilities
        Ordered list of (label, probability, branch_type) tuples — one
        per model branch. probability ∈ [0, 1]; branch_type ∈
        {"wishful", "worst", "realistic"}.
    center_headline
        Large serif headline text (one short phrase).
    center_subline
        Smaller mono caption directly under the headline.
    center_meta
        Tiny uppercase tag at the bottom of the centre disc (e.g.
        "BAZI · WOOD-DOMINANT").

    Returns a complete <svg>…</svg> string suitable for
    st.markdown(..., unsafe_allow_html=True).
    """

    # ---------- outer ring: 5 wuxing sectors, 72° each ----------
    sectors: list[str] = []
    sector_angle = 360.0 / 5
    # Min/max wedge radial extent — every sector renders even when its
    # share is 0, but at minimum thickness so the ring stays visually
    # complete.
    band_min = 4.0
    band_full = _R_OUTER - _R_OUTER_IN  # 65px

    for i, key in enumerate(WUXING_KEYS):
        share = max(0.0, balance.get(key, 0.0))
        # Map share linearly into [band_min, band_full]; even 0%
        # elements get a thin shell so the ring stays continuous.
        thickness = band_min + share * (band_full - band_min)
        r_in = _R_OUTER - thickness
        theta_start = i * sector_angle - sector_angle / 2  # centre top at 木
        theta_end = theta_start + sector_angle
        color = WUXING_COLOR[key]
        alpha = 0.30 + 0.65 * share  # tint intensity ∝ share
        sectors.append(
            f'<path d="{_arc_path(_CX, _CY, _R_OUTER, r_in, theta_start, theta_end)}" '
            f'fill="{color}" fill-opacity="{alpha:.3f}" '
            f'stroke="#0a0c11" stroke-width="1.5"></path>'
        )
        # Sector label (汉字 in serif) at mid-angle, sitting on the rim.
        label_r = (_R_OUTER + _R_OUTER_IN) / 2 + 6
        lx, ly = _polar(_CX, _CY, label_r, (theta_start + theta_end) / 2)
        sectors.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" '
            f'font-family="\'Cormorant Garamond\',Georgia,serif" '
            f'font-size="22" fill="#f0f2f5" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-weight="600">{WUXING_HANZI[i]}</text>'
        )
        # Share % in tiny mono, just outside the rim at the sector
        # midpoint.
        out_r = _R_OUTER + 16
        ox, oy = _polar(_CX, _CY, out_r, (theta_start + theta_end) / 2)
        sectors.append(
            f'<text x="{ox:.2f}" y="{oy:.2f}" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
            f'font-size="10.5" fill="#76808d" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f'{share * 100:.0f}%</text>'
        )

    # ---------- inner ring: branch arcs, total span 320° ----------
    arc_total = 320.0     # leave a 40° "open" wedge at the bottom
    arc_start = 90.0 + 20.0  # start at lower-right (just past 4 o'clock)
    arcs: list[str] = []
    n = len(branch_probabilities)
    if n > 0:
        # Renormalize visible probability so the inner ring always
        # fills the 320° span (otherwise low-probability anchors
        # disappear visually).
        total = sum(max(p, 0.0) for _, p, _ in branch_probabilities) or 1.0
        cursor = arc_start
        for label, prob, branch_type in branch_probabilities:
            span = arc_total * (max(prob, 0.0) / total)
            # Gap between segments so individual branches read.
            gap = 1.2
            seg_start = cursor + gap / 2
            seg_end = cursor + span - gap / 2
            if seg_end <= seg_start:
                cursor += span
                continue
            # Arc fill: lavender for realistic; teal/coral for the
            # named anchors. Alpha scales with raw (un-renormalized)
            # probability so the anchors visually match the rest of
            # the Console's heatmap.
            base_alpha = 0.20 + 0.75 * min(1.0, prob)
            if branch_type == "wishful":
                fill = f"rgba(88,197,180,{base_alpha:.3f})"
            elif branch_type == "worst":
                fill = f"rgba(255,94,110,{base_alpha:.3f})"
            else:
                fill = f"rgba(139,140,255,{base_alpha:.3f})"
            arcs.append(
                f'<path d="{_arc_path(_CX, _CY, _R_INNER, _R_INNER_IN, seg_start, seg_end)}" '
                f'fill="{fill}" stroke="#0a0c11" stroke-width="0.75"></path>'
            )
            # % readout sitting at the radial midpoint of the segment.
            label_r = (_R_INNER + _R_INNER_IN) / 2
            mid = (seg_start + seg_end) / 2
            lx, ly = _polar(_CX, _CY, label_r, mid)
            arcs.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" '
                f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
                f'font-size="10.5" fill="#f0f2f5" '
                f'text-anchor="middle" dominant-baseline="middle">'
                f'{prob * 100:.1f}%</text>'
            )
            cursor += span

    # ---------- centre disc + headline / subline / meta ----------
    centre_safe_headline = _html.escape(center_headline)[:48]
    centre_safe_subline = _html.escape(center_subline)[:80]
    centre_safe_meta = _html.escape(center_meta)[:36]

    centre_circle = (
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_CORE}" '
        f'fill="#11141b" stroke="#232834" stroke-width="1.5"></circle>'
    )
    centre_text = (
        f'<text x="{_CX}" y="{_CY - 24}" '
        f'font-family="\'Cormorant Garamond\',Georgia,serif" '
        f'font-size="28" fill="#f0f2f5" font-weight="600" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{centre_safe_headline}</text>'
        f'<text x="{_CX}" y="{_CY + 6}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
        f'font-size="13" fill="#b9bfc8" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{centre_safe_subline}</text>'
        f'<text x="{_CX}" y="{_CY + 36}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
        f'font-size="10" fill="#76808d" letter-spacing="0.15em" '
        f'text-transform="uppercase" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{centre_safe_meta}</text>'
    )

    # ---------- 八字 pillars around the rim ----------
    pillars = (
        (bazi.year_pillar,  "YEAR"),
        (bazi.month_pillar, "MONTH"),
        (bazi.day_pillar,   "DAY"),
        (bazi.hour_pillar,  "HOUR"),
    )
    pillar_svg: list[str] = []
    pillar_positions = (
        (32, _VB - 50),       # bottom-left   YEAR
        (_VB - 32, _VB - 50),  # bottom-right  MONTH
        (32, 50),              # top-left      DAY
        (_VB - 32, 50),        # top-right     HOUR
    )
    for (pil, name), (px, py) in zip(pillars, pillar_positions):
        text = pillar_text(pil)
        anchor = "start" if px < _CX else "end"
        pillar_svg.append(
            f'<text x="{px:.0f}" y="{py:.0f}" '
            f'font-family="\'Cormorant Garamond\',Georgia,serif" '
            f'font-size="18" fill="#f0f2f5" text-anchor="{anchor}" '
            f'font-weight="600">{_html.escape(text)}</text>'
            f'<text x="{px:.0f}" y="{py + 18:.0f}" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
            f'font-size="9.5" fill="#76808d" letter-spacing="0.18em" '
            f'text-anchor="{anchor}">{name}</text>'
        )

    svg = (
        f'<svg viewBox="0 0 {_VB} {_VB}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" style="display:block;">'
        f'{"".join(pillar_svg)}'
        f'{"".join(sectors)}'
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_OUTER_IN}" '
        f'fill="none" stroke="#232834" stroke-width="0.8"></circle>'
        f'{"".join(arcs)}'
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_INNER_IN}" '
        f'fill="none" stroke="#232834" stroke-width="0.8"></circle>'
        f'{centre_circle}'
        f'{centre_text}'
        f'</svg>'
    )
    return svg


__all__ = ["render_nye_clock_svg"]
