"""Self-contained 玄学 / traditional-prior module for the Console.

This is a deliberately self-contained port of
`src/omytea/dynamics/metaphysical.py` (the substrate-side
MetaphysicalOperator) so that the Console can render the
"Time-honored × Calibrated" view without depending on the slim PyPI
substrate having the metaphysical surface.

Doctrine (matches FOUNDING_VISION + the original operator's preamble):
  NOT superstition, NOT scientific truth — an explicitly-opted-in
  prior the user CAN choose to use. The UI must always show both
  the unweighted model output AND the weighted output.

Scope of this lightweight port:
  - 八字 (4-pillar BaZi) derivation from birth datetime
  - 五行 (Wuxing / 5-element) balance
  - 用神 (favorable element) — simplified
  - Outcome prior table per dominant element

Out of scope for v0.4.x (deferred to a later pass with a real rule
library + author review):
  - 紫微斗数
  - 易经 hexagram lookup
  - 节气 (solar-term) correction
  - 真正的 用神 selection (五行 strength + season + 调候)
  - 时区 longitude correction beyond the default Beijing offset
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


# ----------------------------------------------------------------------
# Birth data + 八字 patterns
# ----------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BirthData:
    """User's birth data for 八字 / 五行 computation.

    Hour is 0–23 in local clock time. Longitude is the user's birth
    longitude (defaults to Beijing) and is held here for forward
    compatibility — the simplified algorithm below ignores it.
    """

    year: int
    month: int  # 1-12
    day: int    # 1-31
    hour: int   # 0-23
    longitude: float = 116.4

    @classmethod
    def from_datetime(cls, dt: datetime, longitude: float = 116.4) -> "BirthData":
        return cls(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour,
                   longitude=longitude)


@dataclass(frozen=True, slots=True)
class BaZiPattern:
    """4-pillar 八字: ((天干, 地支), …).

    天干 indices: 0=甲 1=乙 2=丙 3=丁 4=戊 5=己 6=庚 7=辛 8=壬 9=癸.
    地支 indices: 0=子 1=丑 2=寅 3=卯 4=辰 5=巳 6=午 7=未 8=申 9=酉 10=戌 11=亥.
    """

    year_pillar: tuple[int, int]
    month_pillar: tuple[int, int]
    day_pillar: tuple[int, int]
    hour_pillar: tuple[int, int]

    @property
    def stems(self) -> tuple[int, int, int, int]:
        return (self.year_pillar[0], self.month_pillar[0],
                self.day_pillar[0], self.hour_pillar[0])

    @property
    def branches(self) -> tuple[int, int, int, int]:
        return (self.year_pillar[1], self.month_pillar[1],
                self.day_pillar[1], self.hour_pillar[1])


HEAVENLY_STEMS: tuple[str, ...] = (
    "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸",
)
EARTHLY_BRANCHES: tuple[str, ...] = (
    "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥",
)

# 天干 → 五行 (0=甲乙 wood, 1=丙丁 fire, 2=戊己 earth, 3=庚辛 metal, 4=壬癸 water)
WUXING_OF_STEM: tuple[int, ...] = (0, 0, 1, 1, 2, 2, 3, 3, 4, 4)
# 地支 → 五行
WUXING_OF_BRANCH: tuple[int, ...] = (4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4)

# Display order (for the SVG instrument outer ring): start at top
# and rotate clockwise — 木 (growth) → 火 (heat) → 土 (centre) →
# 金 (metal) → 水 (depth).
WUXING_KEYS: tuple[str, ...] = ("wood", "fire", "earth", "metal", "water")
WUXING_HANZI: tuple[str, ...] = ("木", "火", "土", "金", "水")
# Hex colour per element — chosen to match the v10 palette
# (lavender/teal/coral/amber/silver) so the instrument doesn't read
# like a separate brand from the rest of the Console.
WUXING_COLOR: dict[str, str] = {
    "wood":  "#58c5b4",  # teal — growth
    "fire":  "#ff5e6e",  # coral — heat
    "earth": "#d8a657",  # amber — soil
    "metal": "#b9bfc8",  # silver-ink — metal
    "water": "#8b8cff",  # lavender (brand accent) — depth
}


# ----------------------------------------------------------------------
# 八字 derivation (simplified — see module preamble)
# ----------------------------------------------------------------------

def bazi_from_birth(bd: BirthData) -> BaZiPattern:
    """Compute simplified 八字 from birth datetime.

    Simplified algorithm — see docstring. Deterministic; same inputs
    always produce the same pillars.
    """
    # Year pillar — sexagenary cycle anchored at year 4 = 甲子.
    sexagenary = (bd.year - 4) % 60
    year_stem = sexagenary % 10
    year_branch = sexagenary % 12

    # Month pillar — approximate. Real 五虎遁 needs solar terms.
    month_stem = (year_stem * 2 + bd.month) % 10
    month_branch = (bd.month + 1) % 12  # ≈ 寅月 starts in Feb

    # Day pillar — coarse linear cycle since 1900-01-01.
    days_since_epoch = (bd.year - 1900) * 365 + bd.month * 30 + bd.day
    day_stem = days_since_epoch % 10
    day_branch = days_since_epoch % 12

    # Hour pillar — 12 two-hour periods, stem via 五鼠遁 (approx).
    hour_branch = ((bd.hour + 1) // 2) % 12
    hour_stem = (day_stem * 2 + hour_branch) % 10

    return BaZiPattern(
        year_pillar=(year_stem, year_branch),
        month_pillar=(month_stem, month_branch),
        day_pillar=(day_stem, day_branch),
        hour_pillar=(hour_stem, hour_branch),
    )


def wuxing_balance(bazi: BaZiPattern) -> dict[str, float]:
    """Count 五行 distribution across the 8 characters.

    Returns a dict keyed by the EN element key (wood/fire/earth/metal
    /water) → fractional weight summing to 1.0.
    """
    counts = [0] * 5
    for stem in bazi.stems:
        counts[WUXING_OF_STEM[stem]] += 1
    for branch in bazi.branches:
        counts[WUXING_OF_BRANCH[branch]] += 1
    total = sum(counts) or 1
    return {WUXING_KEYS[i]: counts[i] / total for i in range(5)}


def dominant_element(balance: dict[str, float]) -> str:
    """Return the EN key of the element with the largest share."""
    return max(balance.items(), key=lambda kv: kv[1])[0]


def yongshen(balance: dict[str, float]) -> str:
    """Simplified 用神 — the most-lacking element by share.

    Real 用神 selection considers 日主 strength, season, 调候 — this is a
    deliberate placeholder.
    """
    return min(balance.items(), key=lambda kv: kv[1])[0]


def pillar_text(p: tuple[int, int]) -> str:
    """Render a pillar as a 2-char 天干地支 string, e.g. (0, 0) → 甲子."""
    s, b = p
    return f"{HEAVENLY_STEMS[s % 10]}{EARTHLY_BRANCHES[b % 12]}"


# ----------------------------------------------------------------------
# Outcome-category priors
# ----------------------------------------------------------------------

# Outcome categories surfaced to the user. Keep the list short — the
# instrument has limited centre real estate. Keys are stable ASCII
# identifiers; display labels live in _i18n.TRANSLATIONS.
OUTCOME_CATEGORIES: tuple[str, ...] = (
    "career_success",
    "marriage_stable",
    "wealth_accumulation",
    "health_strong",
    "learning_good",
    "conflict_low",
)

# Prior P(outcome) per dominant element. Numbers ported from the
# substrate's MetaphysicalOperator default table; values are
# deliberately moderate (0.4–0.8 range) to avoid implying any single
# birth chart "guarantees" or "rules out" an outcome.
_PRIOR_TABLE: dict[str, dict[str, float]] = {
    "wood":  {"career_success": 0.65, "marriage_stable": 0.55, "wealth_accumulation": 0.50,
              "health_strong": 0.70, "learning_good": 0.75, "conflict_low": 0.55},
    "fire":  {"career_success": 0.70, "marriage_stable": 0.45, "wealth_accumulation": 0.55,
              "health_strong": 0.55, "learning_good": 0.65, "conflict_low": 0.40},
    "earth": {"career_success": 0.55, "marriage_stable": 0.70, "wealth_accumulation": 0.65,
              "health_strong": 0.65, "learning_good": 0.55, "conflict_low": 0.70},
    "metal": {"career_success": 0.75, "marriage_stable": 0.55, "wealth_accumulation": 0.70,
              "health_strong": 0.60, "learning_good": 0.60, "conflict_low": 0.50},
    "water": {"career_success": 0.60, "marriage_stable": 0.60, "wealth_accumulation": 0.55,
              "health_strong": 0.50, "learning_good": 0.80, "conflict_low": 0.65},
}


def outcome_prior(bazi: BaZiPattern, outcome: str) -> float:
    """Return the 玄学 prior P(outcome | 八字).

    Uses the dominant-element table. Unknown outcome keys return 0.5
    (uninformative).
    """
    balance = wuxing_balance(bazi)
    dom = dominant_element(balance)
    return _PRIOR_TABLE.get(dom, {}).get(outcome, 0.5)


# ----------------------------------------------------------------------
# Mixture / Bayesian update
# ----------------------------------------------------------------------

CombinationMode = Literal["mixture", "bayesian", "off"]


def combine_with_model(
    model_prob: float,
    meta_prior: float,
    mode: CombinationMode,
    alpha: float,
) -> float:
    """Combine the model's branch probability with the 玄学 prior.

    - "off" → return ``model_prob`` unchanged.
    - "mixture" → α · meta + (1−α) · model.
    - "bayesian" → meta · model, renormalized externally by the caller
      across branches.

    Returns a value in [0, 1]. Caller is responsible for renormalizing
    the full branch distribution in "bayesian" mode.
    """
    alpha = max(0.0, min(1.0, alpha))
    model_prob = max(0.0, min(1.0, model_prob))
    meta_prior = max(0.0, min(1.0, meta_prior))
    if mode == "off" or alpha < 1e-9:
        return model_prob
    if mode == "mixture":
        return alpha * meta_prior + (1.0 - alpha) * model_prob
    if mode == "bayesian":
        # Unnormalized posterior contribution; caller renormalizes.
        return max(0.0, meta_prior * model_prob)
    return model_prob


__all__ = [
    "BirthData",
    "BaZiPattern",
    "bazi_from_birth",
    "wuxing_balance",
    "dominant_element",
    "yongshen",
    "pillar_text",
    "outcome_prior",
    "combine_with_model",
    "WUXING_KEYS",
    "WUXING_HANZI",
    "WUXING_COLOR",
    "HEAVENLY_STEMS",
    "EARTHLY_BRANCHES",
    "OUTCOME_CATEGORIES",
    "CombinationMode",
]
