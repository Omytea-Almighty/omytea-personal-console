"""Nye-clock instrument — a single dial that reads the same prediction
two ways.

Design intent (per founder critique 2026-05-19):
  • "精妙的小彩蛋" — restraint over showmanship. The dial is dense
    without crowding; everything earns its place. No outer % callouts,
    no axis labels, no legend tags. The shapes themselves carry the
    information; small text only where the number itself is the point.
  • Compact — 480 viewBox so the dial sits comfortably *below* the
    main heatmap card without dominating the page. The result page
    is the canonical home; the dial is the "alternate read" that
    appears when the user opens the lens.
  • Visual rhyme with the v10 marketing demo — same surface card,
    same lavender / teal / coral / amber palette, same Cormorant
    serif for any number that matters.

Visual structure (centre-out):
  1. Soft radial gradient backdrop — barely visible, mimics the
     "instrument glow" feel from the v10 demo (~5% alpha).
  2. Centre disc — `model-only %` (top) and `combined %` (bottom),
     stacked so the user can compare without eye-saccade. Tiny
     uppercase meta tag (dominant element + α value) at the rim.
  3. Inner ring — the model's branches as arcs. Span ∝ probability.
     Colour by branch_type (lavender realistic, teal wishful, coral
     worst). No labels; the heatmap above already carried that.
  4. Outer ring — 五行 sectors as wedges. Thickness ∝ share. The
     dominant element's 汉字 sits on its sector in serif type;
     non-dominant elements get a smaller muted glyph so the eye
     finds the focal one first.
  5. Four corner 八字 pillars in 天干地支, restrained label below
     each pillar in tiny mono.
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
    dominant_element,
    pillar_text,
)


# ----------------------------------------------------------------------
# Geometry constants (viewBox 480×480)
# ----------------------------------------------------------------------
_VB = 480
_CX = _VB / 2
_CY = _VB / 2

_R_OUTER     = 215   # outer ring outside edge
_R_OUTER_IN  = 170   # outer ring inside edge
_R_INNER     = 152   # inner ring outside edge
_R_INNER_IN  = 112   # inner ring inside edge
_R_CORE      = 102   # core circle radius


def _polar(cx: float, cy: float, r: float, theta_deg: float) -> tuple[float, float]:
    """Polar → Cartesian. theta=0 at 12 o'clock, clockwise positive."""
    t = math.radians(theta_deg - 90.0)
    return cx + r * math.cos(t), cy + r * math.sin(t)


def _arc_path(
    cx: float, cy: float, r_outer: float, r_inner: float,
    theta_start: float, theta_end: float,
) -> str:
    """SVG annulus-sector path."""
    if theta_end - theta_start <= 1e-3:
        return ""
    large = 1 if (theta_end - theta_start) > 180 else 0
    x0o, y0o = _polar(cx, cy, r_outer, theta_start)
    x1o, y1o = _polar(cx, cy, r_outer, theta_end)
    x0i, y0i = _polar(cx, cy, r_inner, theta_start)
    x1i, y1i = _polar(cx, cy, r_inner, theta_end)
    return (
        f"M {x0o:.2f} {y0o:.2f} "
        f"A {r_outer:.2f} {r_outer:.2f} 0 {large} 1 {x1o:.2f} {y1o:.2f} "
        f"L {x1i:.2f} {y1i:.2f} "
        f"A {r_inner:.2f} {r_inner:.2f} 0 {large} 0 {x0i:.2f} {y0i:.2f} "
        f"Z"
    )


# ----------------------------------------------------------------------
# Public render
# ----------------------------------------------------------------------

def render_nye_clock_svg(
    bazi: BaZiPattern,
    balance: dict[str, float],
    branch_probabilities: list[tuple[str, float, str]],
    center_top_label: str,      # small uppercase, e.g. "MODEL"
    center_top_value: str,      # large number, e.g. "34.2%"
    center_bottom_label: str,   # small uppercase, e.g. "COMBINED"
    center_bottom_value: str,   # large number, e.g. "52.1%"
    center_meta: str,           # tiny uppercase rim tag, e.g. "WOOD · α=0.30"
) -> str:
    """Render the Nye-clock instrument as a self-contained SVG string."""

    dom_key = dominant_element(balance) if balance else None

    # ---- defs: radial gradient backdrop ----
    defs = (
        '<defs>'
        '<radialGradient id="dial-glow" cx="50%" cy="50%" r="60%">'
        '<stop offset="0%" stop-color="rgba(139,140,255,0.10)"/>'
        '<stop offset="65%" stop-color="rgba(139,140,255,0.02)"/>'
        '<stop offset="100%" stop-color="rgba(139,140,255,0.00)"/>'
        '</radialGradient>'
        '<radialGradient id="core-glow" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="#161a23"/>'
        '<stop offset="100%" stop-color="#11141b"/>'
        '</radialGradient>'
        '</defs>'
    )

    # ---- backdrop ----
    backdrop = (
        f'<rect x="0" y="0" width="{_VB}" height="{_VB}" '
        f'fill="url(#dial-glow)"></rect>'
    )

    # ---- outer ring: five 72° wuxing sectors ----
    sectors: list[str] = []
    sector_angle = 360.0 / 5
    band_min = 5.0
    band_full = _R_OUTER - _R_OUTER_IN  # 45px

    for i, key in enumerate(WUXING_KEYS):
        share = max(0.0, balance.get(key, 0.0))
        thickness = band_min + share * (band_full - band_min)
        r_in = _R_OUTER - thickness
        theta_start = i * sector_angle - sector_angle / 2
        theta_end = theta_start + sector_angle
        color = WUXING_COLOR[key]
        # Softer alpha curve than the original — even the dominant
        # element shouldn't oversaturate.
        alpha = 0.20 + 0.50 * share
        sectors.append(
            f'<path d="{_arc_path(_CX, _CY, _R_OUTER, r_in, theta_start, theta_end)}" '
            f'fill="{color}" fill-opacity="{alpha:.3f}" '
            f'stroke="#0a0c11" stroke-width="1"></path>'
        )
        # Element glyph at sector midpoint. Dominant element gets a
        # larger, brighter serif character; others get a smaller
        # muted glyph so the eye finds the focal element first.
        is_dom = (key == dom_key)
        label_r = (_R_OUTER + _R_OUTER_IN) / 2 + 2
        lx, ly = _polar(_CX, _CY, label_r, (theta_start + theta_end) / 2)
        glyph_size = 22 if is_dom else 15
        glyph_color = "#f0f2f5" if is_dom else "#76808d"
        glyph_weight = 600 if is_dom else 400
        sectors.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" '
            f'font-family="\'Cormorant Garamond\',Georgia,serif" '
            f'font-size="{glyph_size}" fill="{glyph_color}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-weight="{glyph_weight}">{WUXING_HANZI[i]}</text>'
        )

    # ---- inner ring: branch arcs, span 320° (40° open gap bottom) ----
    arc_total = 320.0
    arc_start = 90.0 + 20.0  # start at ~4 o'clock
    arcs: list[str] = []
    n = len(branch_probabilities)
    if n > 0:
        total = sum(max(p, 0.0) for _, p, _ in branch_probabilities) or 1.0
        cursor = arc_start
        for label, prob, branch_type in branch_probabilities:
            span = arc_total * (max(prob, 0.0) / total)
            gap = 1.4
            seg_start = cursor + gap / 2
            seg_end = cursor + span - gap / 2
            if seg_end <= seg_start:
                cursor += span
                continue
            base_alpha = 0.22 + 0.70 * min(1.0, prob)
            if branch_type == "wishful":
                fill = f"rgba(88,197,180,{base_alpha:.3f})"
            elif branch_type == "worst":
                fill = f"rgba(255,94,110,{base_alpha:.3f})"
            else:
                fill = f"rgba(139,140,255,{base_alpha:.3f})"
            arcs.append(
                f'<path d="{_arc_path(_CX, _CY, _R_INNER, _R_INNER_IN, seg_start, seg_end)}" '
                f'fill="{fill}" stroke="#0a0c11" stroke-width="0.5"></path>'
            )
            cursor += span

    # ---- centre disc with core gradient + dual readout ----
    centre_disc = (
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_CORE}" '
        f'fill="url(#core-glow)" stroke="#232834" stroke-width="1"></circle>'
        # subtle inner ring shadow
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_CORE - 6}" '
        f'fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="0.6"></circle>'
    )

    safe_top_label    = _html.escape(center_top_label)[:18]
    safe_top_value    = _html.escape(center_top_value)[:10]
    safe_bottom_label = _html.escape(center_bottom_label)[:18]
    safe_bottom_value = _html.escape(center_bottom_value)[:10]
    safe_meta         = _html.escape(center_meta)[:36]

    # Top number (model-only), divider, bottom number (combined).
    centre_text = (
        # Top — uppercase mono label
        f'<text x="{_CX}" y="{_CY - 44}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
        f'font-size="9.5" fill="#76808d" letter-spacing="0.18em" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{safe_top_label}</text>'
        # Top — big serif number
        f'<text x="{_CX}" y="{_CY - 20}" '
        f'font-family="\'Cormorant Garamond\',Georgia,serif" '
        f'font-size="26" fill="#f0f2f5" font-weight="600" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{safe_top_value}</text>'
        # Centre divider
        f'<line x1="{_CX - 28}" y1="{_CY}" x2="{_CX + 28}" y2="{_CY}" '
        f'stroke="#232834" stroke-width="0.8"></line>'
        # Bottom — uppercase mono label
        f'<text x="{_CX}" y="{_CY + 16}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
        f'font-size="9.5" fill="#76808d" letter-spacing="0.18em" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{safe_bottom_label}</text>'
        # Bottom — big serif number
        f'<text x="{_CX}" y="{_CY + 40}" '
        f'font-family="\'Cormorant Garamond\',Georgia,serif" '
        f'font-size="26" fill="#f0f2f5" font-weight="600" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{safe_bottom_value}</text>'
        # Rim meta tag (just below the core circle)
        f'<text x="{_CX}" y="{_CY + _R_CORE - 10}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
        f'font-size="9" fill="#4b525d" letter-spacing="0.2em" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{safe_meta}</text>'
    )

    # ---- four 八字 pillars at the corners ----
    pillars = (
        (bazi.year_pillar,  "YEAR"),
        (bazi.month_pillar, "MONTH"),
        (bazi.day_pillar,   "DAY"),
        (bazi.hour_pillar,  "HOUR"),
    )
    corner_positions = (
        (28, _VB - 40),       # bottom-left   YEAR
        (_VB - 28, _VB - 40),  # bottom-right  MONTH
        (28, 40),              # top-left      DAY
        (_VB - 28, 40),        # top-right     HOUR
    )
    pillar_svg: list[str] = []
    for (pil, name), (px, py) in zip(pillars, corner_positions):
        text = pillar_text(pil)
        anchor = "start" if px < _CX else "end"
        pillar_svg.append(
            f'<text x="{px:.0f}" y="{py:.0f}" '
            f'font-family="\'Cormorant Garamond\',Georgia,serif" '
            f'font-size="16" fill="#b9bfc8" text-anchor="{anchor}" '
            f'font-weight="500">{_html.escape(text)}</text>'
            f'<text x="{px:.0f}" y="{py + 14:.0f}" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
            f'font-size="8.5" fill="#4b525d" letter-spacing="0.2em" '
            f'text-anchor="{anchor}">{name}</text>'
        )

    # ---- assemble ----
    svg = (
        f'<svg viewBox="0 0 {_VB} {_VB}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" style="display:block;">'
        f'{defs}'
        f'{backdrop}'
        f'{"".join(pillar_svg)}'
        f'{"".join(sectors)}'
        # hairline ring between outer and inner
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_OUTER_IN}" '
        f'fill="none" stroke="#232834" stroke-width="0.6"></circle>'
        f'{"".join(arcs)}'
        # hairline ring between inner and core
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_INNER_IN}" '
        f'fill="none" stroke="#232834" stroke-width="0.6"></circle>'
        f'{centre_disc}'
        f'{centre_text}'
        f'</svg>'
    )
    return svg


__all__ = ["render_nye_clock_svg"]
