"""玄学数据库 — four traditional divination systems as user-weighted priors.

This is the Console-side "玄学 database" the founder asked for. It ports
the substrate's `MetaphysicalOperator` math (八字) and extends it with
three more traditions, all behind the same epistemic posture:

    NOT superstition, NOT scientific truth — an explicitly-opted-in
    prior the user CAN choose to weight. The UI always shows both the
    unweighted model output AND the weighted output.

Per `docs/operators/METAPHYSICAL_OP_MATH.md` §0 + §7.

Four systems:
  • 八字  (BaZi / Four Pillars)  — birth datetime → 五行 balance
  • 紫微  (ZiWei Dou Shu)        — birth datetime → 12-palace star chart
  • 易经  (I Ching)             — seeded cast → hexagram (64)
  • 塔罗  (Tarot)               — seeded draw → 3-card spread (Major Arcana)

八字 + 紫微 are deterministic in birth data. 易经 + 塔罗 are a "cast" —
deterministic in a seed (the prediction id) so the same prediction
always shows the same hexagram / spread, but it reads as a draw.

Every system produces:
  • a `Reading` dataclass (system-specific, for the renderer)
  • `outcome_prior` ∈ [0, 1]  — P(focal outcome | reading)
  • `auspice` ∈ [0, 1]        — overall favourability, drives the
    per-branch Bayesian reweight (`apply_lens_to_branches`)

Scope honesty — all four use SIMPLIFIED rule libraries (documented at
each site). A real 节气-corrected 八字, a real 五行局 紫微 placement,
an author-reviewed 64-hexagram interpretation library, and a full
78-card Tarot deck with reversY semantics are v0.5+ work.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


# ======================================================================
# Shared — outcome categories + combination math
# ======================================================================

OUTCOME_CATEGORIES: tuple[str, ...] = (
    "career_success",
    "marriage_stable",
    "wealth_accumulation",
    "health_strong",
    "learning_good",
    "conflict_low",
)

CombinationMode = Literal["mixture", "bayesian", "off"]

SYSTEM_BAZI: str = "bazi"
SYSTEM_ZIWEI: str = "ziwei"
SYSTEM_ICHING: str = "iching"
SYSTEM_TAROT: str = "tarot"
SYSTEM_ASTRO: str = "astro"
SYSTEMS: tuple[str, ...] = (
    SYSTEM_BAZI, SYSTEM_ZIWEI, SYSTEM_ICHING, SYSTEM_TAROT, SYSTEM_ASTRO,
)


def _seed_int(seed: str, salt: str = "") -> int:
    """Deterministic 64-bit int from a string seed (sha256-based)."""
    h = hashlib.sha256(f"{salt}:{seed}".encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def combine_with_model(
    model_prob: float,
    meta_prior: float,
    mode: CombinationMode,
    alpha: float,
) -> float:
    """Combine the model's focal-outcome probability with a 玄学 prior.

    - "off"      → return model_prob unchanged.
    - "mixture"  → α·meta + (1−α)·model.
    - "bayesian" → meta·model (un-normalized; caller renormalizes).

    Returns a value in [0, 1] for off/mixture; an un-normalized product
    for bayesian.
    """
    alpha = max(0.0, min(1.0, alpha))
    model_prob = max(0.0, min(1.0, model_prob))
    meta_prior = max(0.0, min(1.0, meta_prior))
    if mode == "off" or alpha < 1e-9:
        return model_prob
    if mode == "mixture":
        return alpha * meta_prior + (1.0 - alpha) * model_prob
    if mode == "bayesian":
        return max(0.0, meta_prior * model_prob)
    return model_prob


def apply_lens_to_branches(
    branches: list[tuple[str, float, str]],
    auspice: float,
    alpha: float,
) -> list[tuple[str, float, str]]:
    """Per-branch Bayesian reweight driven by the reading's `auspice`.

    The honest per-branch move (no LLM branch-classification needed):
    a *favourable* reading (auspice → 1) nudges probability mass toward
    the wishful anchor and away from the worst anchor; an *unfavourable*
    reading (auspice → 0) does the reverse. Realistic branches stay
    near-neutral. `alpha` scales how hard the nudge pulls.

    Returns a new list of (label, probability, branch_type) with the
    probabilities renormalized to sum to 1. `alpha = 0` is an exact
    no-op (returns the input distribution unchanged).
    """
    if not branches or alpha < 1e-9:
        return [(l, p, t) for l, p, t in branches]

    auspice = max(0.0, min(1.0, auspice))
    alpha = max(0.0, min(1.0, alpha))
    # Favourable reading → factor > 1 for wishful, < 1 for worst.
    # `tilt` ∈ [−1, 1]: −1 fully grim, +1 fully auspicious.
    tilt = 2.0 * auspice - 1.0
    out: list[tuple[str, float, str]] = []
    for label, prob, btype in branches:
        if btype == "wishful":
            factor = 1.0 + alpha * 0.9 * tilt
        elif btype == "worst":
            factor = 1.0 - alpha * 0.9 * tilt
        else:
            # Realistic branches drift gently the opposite way of the
            # anchors so total mass is roughly conserved before renorm.
            factor = 1.0 - alpha * 0.12 * tilt
        out.append((label, max(0.0, prob * factor), btype))

    total = sum(p for _, p, _ in out) or 1.0
    return [(l, p / total, t) for l, p, t in out]


# ======================================================================
# System 1 — 八字 (BaZi / Four Pillars of Destiny)
# ======================================================================

@dataclass(frozen=True, slots=True)
class BirthData:
    """User's birth data for 八字 / 紫微 computation.

    Hour is 0–23 local clock time. Longitude is held for forward
    compatibility (true-solar-time correction is v0.5+); the simplified
    algorithms below ignore it.
    """

    year: int
    month: int   # 1-12
    day: int     # 1-31
    hour: int    # 0-23
    longitude: float = 116.4

    @classmethod
    def from_datetime(cls, dt: datetime, longitude: float = 116.4) -> "BirthData":
        return cls(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour,
                   longitude=longitude)


@dataclass(frozen=True, slots=True)
class BaZiPattern:
    """4-pillar 八字: ((天干, 地支), …)."""

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

WUXING_OF_STEM: tuple[int, ...] = (0, 0, 1, 1, 2, 2, 3, 3, 4, 4)
WUXING_OF_BRANCH: tuple[int, ...] = (4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4)

WUXING_KEYS: tuple[str, ...] = ("wood", "fire", "earth", "metal", "water")
WUXING_HANZI: tuple[str, ...] = ("木", "火", "土", "金", "水")
# Refined per-element palette — a brighter rim tone and a deeper inner
# tone, so the renderer can build a real radial gradient per wedge.
WUXING_COLOR: dict[str, str] = {
    "wood":  "#58c5b4",
    "fire":  "#ff5e6e",
    "earth": "#d8a657",
    "metal": "#c9cdd4",
    "water": "#8b8cff",
}
WUXING_COLOR_DEEP: dict[str, str] = {
    "wood":  "#1f5249",
    "fire":  "#6e2530",
    "earth": "#5e4824",
    "metal": "#4b525d",
    "water": "#33356e",
}


def bazi_from_birth(bd: BirthData) -> BaZiPattern:
    """Compute a SIMPLIFIED 八字 from birth datetime.

    Deterministic. Real 八字 needs solar terms (节气) + true solar time;
    this is a documented placeholder (v0.5+ replaces it).
    """
    sexagenary = (bd.year - 4) % 60
    year_stem = sexagenary % 10
    year_branch = sexagenary % 12

    month_stem = (year_stem * 2 + bd.month) % 10
    month_branch = (bd.month + 1) % 12

    days_since_epoch = (bd.year - 1900) * 365 + bd.month * 30 + bd.day
    day_stem = days_since_epoch % 10
    day_branch = days_since_epoch % 12

    hour_branch = ((bd.hour + 1) // 2) % 12
    hour_stem = (day_stem * 2 + hour_branch) % 10

    return BaZiPattern(
        year_pillar=(year_stem, year_branch),
        month_pillar=(month_stem, month_branch),
        day_pillar=(day_stem, day_branch),
        hour_pillar=(hour_stem, hour_branch),
    )


def wuxing_balance(bazi: BaZiPattern) -> dict[str, float]:
    """五行 distribution across the 8 characters → fractions summing to 1."""
    counts = [0] * 5
    for stem in bazi.stems:
        counts[WUXING_OF_STEM[stem]] += 1
    for branch in bazi.branches:
        counts[WUXING_OF_BRANCH[branch]] += 1
    total = sum(counts) or 1
    return {WUXING_KEYS[i]: counts[i] / total for i in range(5)}


def dominant_element(balance: dict[str, float]) -> str:
    return max(balance.items(), key=lambda kv: kv[1])[0]


def yongshen(balance: dict[str, float]) -> str:
    """Simplified 用神 — the most-lacking element (placeholder)."""
    return min(balance.items(), key=lambda kv: kv[1])[0]


def pillar_text(p: tuple[int, int]) -> str:
    s, b = p
    return f"{HEAVENLY_STEMS[s % 10]}{EARTHLY_BRANCHES[b % 12]}"


_BAZI_PRIOR_TABLE: dict[str, dict[str, float]] = {
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
    """八字 prior P(outcome) via the dominant-element table."""
    dom = dominant_element(wuxing_balance(bazi))
    return _BAZI_PRIOR_TABLE.get(dom, {}).get(outcome, 0.5)


def bazi_auspice(bazi: BaZiPattern) -> float:
    """Overall 八字 favourability ∈ [0, 1].

    A *balanced* 五行 chart is the auspicious case in classical 命理 —
    one element flooding the chart (or one entirely absent) is the
    inauspicious pattern. We map the spread (max−min share) to an
    auspice score: even spread → high, lopsided → low.
    """
    bal = wuxing_balance(bazi)
    spread = max(bal.values()) - min(bal.values())
    # spread ranges ~0 (perfectly even) to ~1 (all in one element).
    return max(0.0, min(1.0, 1.0 - spread))


# ======================================================================
# System 2 — 紫微斗数 (ZiWei Dou Shu / Purple Star Astrology)
# ======================================================================

# The 12 palaces, in chart order starting from 命宫.
ZIWEI_PALACES: tuple[str, ...] = (
    "ming", "siblings", "spouse", "children", "wealth", "health",
    "travel", "friends", "career", "property", "fortune", "parents",
)
ZIWEI_PALACE_HANZI: dict[str, str] = {
    "ming": "命宫", "siblings": "兄弟", "spouse": "夫妻", "children": "子女",
    "wealth": "财帛", "health": "疾厄", "travel": "迁移", "friends": "交友",
    "career": "官禄", "property": "田宅", "fortune": "福德", "parents": "父母",
}
# Which palace governs which outcome category (spec §1.2 PALACE_MAP).
ZIWEI_OUTCOME_PALACE: dict[str, str] = {
    "career_success": "career",
    "marriage_stable": "spouse",
    "wealth_accumulation": "wealth",
    "health_strong": "health",
    "learning_good": "fortune",
    "conflict_low": "friends",
}

# 14 主星. `nature`: +1 auspicious (吉), −1 inauspicious (凶), 0 neutral.
ZIWEI_STARS: tuple[tuple[str, str, int], ...] = (
    ("ziwei",   "紫微", +1), ("tianji",  "天机", +1),
    ("taiyang", "太阳", +1), ("wuqu",    "武曲",  0),
    ("tiantong","天同", +1), ("lianzhen","廉贞", -1),
    ("tianfu",  "天府", +1), ("taiyin",  "太阴", +1),
    ("tanlang", "贪狼",  0), ("jumen",   "巨门", -1),
    ("tianxiang","天相",+1), ("tianliang","天梁",+1),
    ("qisha",   "七杀", -1), ("pojun",   "破军", -1),
)


@dataclass(frozen=True, slots=True)
class ZiWeiChart:
    """A simplified 12-palace 紫微 chart.

    `palace_stars` maps palace key → list of star keys placed there.
    `ming_index` is the 命宫 position in [0, 11].
    """

    ming_index: int
    palace_stars: dict[str, list[str]] = field(default_factory=dict)


def ziwei_chart(bd: BirthData) -> ZiWeiChart:
    """Build a SIMPLIFIED 紫微 chart from birth data.

    Honest scope note: the real placement uses 五行局 + a 紫微-position
    table keyed on birth day. This simplified version (a) derives 命宫
    from month + hour, (b) places 紫微 from birth day, (c) runs the
    紫微 series forward and the 天府 series backward — which is the
    *true structural relationship* between the two star series, even
    though the 紫微 seed position is simplified. Deterministic.
    """
    ming_index = (bd.month - 1 + bd.hour // 2) % 12

    # 紫微 (first of the 紫微 series) seed position.
    ziwei_pos = (bd.day - 1) % 12
    # 紫微 series — 紫微 天机 (skip) 太阳 武曲 天同 (skip) 廉贞, classic
    # offsets compressed for the simplified model.
    ziwei_series = ["ziwei", "tianji", "taiyang", "wuqu", "tiantong", "lianzhen"]
    ziwei_offsets = [0, -1, -3, -4, -5, -8]
    # 天府 series mirrors 紫微 across the chart and runs the other way.
    tianfu_pos = (4 - ziwei_pos) % 12
    tianfu_series = ["tianfu", "taiyin", "tanlang", "jumen",
                     "tianxiang", "tianliang", "qisha", "pojun"]
    tianfu_offsets = [0, 1, 2, 3, 4, 5, 6, 10]

    palace_stars: dict[str, list[str]] = {p: [] for p in ZIWEI_PALACES}

    def palace_at(branch_pos: int) -> str:
        # Palace whose chart-branch is `branch_pos`. 命宫 sits at the
        # ming_index branch; palaces run forward from there.
        return ZIWEI_PALACES[(branch_pos - ming_index) % 12]

    for star, off in zip(ziwei_series, ziwei_offsets):
        palace_stars[palace_at((ziwei_pos + off) % 12)].append(star)
    for star, off in zip(tianfu_series, tianfu_offsets):
        palace_stars[palace_at((tianfu_pos + off) % 12)].append(star)

    return ZiWeiChart(ming_index=ming_index, palace_stars=palace_stars)


_ZIWEI_STAR_NATURE: dict[str, int] = {k: n for k, _, n in ZIWEI_STARS}
_ZIWEI_STAR_HANZI: dict[str, str] = {k: h for k, h, _ in ZIWEI_STARS}


def ziwei_star_hanzi(star_key: str) -> str:
    return _ZIWEI_STAR_HANZI.get(star_key, star_key)


def ziwei_outcome_prior(chart: ZiWeiChart, outcome: str) -> float:
    """紫微 prior P(outcome) — aggregate the star natures in the palace
    that governs `outcome`. Base 0.5 ± 0.12 per net star nature."""
    palace = ZIWEI_OUTCOME_PALACE.get(outcome, "ming")
    stars = chart.palace_stars.get(palace, [])
    net = sum(_ZIWEI_STAR_NATURE.get(s, 0) for s in stars)
    return max(0.05, min(0.95, 0.5 + 0.12 * net))


def ziwei_auspice(chart: ZiWeiChart) -> float:
    """Overall 紫微 favourability — net nature of the stars in 命宫
    plus 福德 (the two palaces that classically set life tone)."""
    key_stars = (chart.palace_stars.get("ming", [])
                 + chart.palace_stars.get("fortune", []))
    net = sum(_ZIWEI_STAR_NATURE.get(s, 0) for s in key_stars)
    return max(0.0, min(1.0, 0.5 + 0.16 * net))


# ======================================================================
# System 3 — 易经 (I Ching / Book of Changes)
# ======================================================================

# 8 trigrams, indexed 0-7 by binary value (bottom line = LSB).
TRIGRAM_HANZI: tuple[str, ...] = ("坤", "艮", "坎", "巽", "震", "离", "兑", "乾")
TRIGRAM_SYMBOL: tuple[str, ...] = ("☷", "☶", "☵", "☴", "☳", "☲", "☱", "☰")

# 64 hexagram names in King Wen order (index 1-64; index 0 unused).
HEXAGRAM_NAMES: tuple[str, ...] = (
    "",  # 0 unused
    "乾", "坤", "屯", "蒙", "需", "讼", "师", "比",
    "小畜", "履", "泰", "否", "同人", "大有", "谦", "豫",
    "随", "蛊", "临", "观", "噬嗑", "贲", "剥", "复",
    "无妄", "大畜", "颐", "大过", "坎", "离", "咸", "恒",
    "遁", "大壮", "晋", "明夷", "家人", "睽", "蹇", "解",
    "损", "益", "夬", "姤", "萃", "升", "困", "井",
    "革", "鼎", "震", "艮", "渐", "归妹", "丰", "旅",
    "巽", "兑", "涣", "节", "中孚", "小过", "既济", "未济",
)

# King Wen lookup: KING_WEN[upper_trigram][lower_trigram] → hexagram no.
# Trigram order for both axes: 乾(7) 兑(6) 离(5) 震(4) 巽(3) 坎(2) 艮(1) 坤(0).
_KW_ORDER = (7, 6, 5, 4, 3, 2, 1, 0)
_KING_WEN_GRID: tuple[tuple[int, ...], ...] = (
    ( 1, 43, 14, 34,  9,  5, 26, 11),  # upper 乾
    (10, 58, 38, 54, 61, 60, 41, 19),  # upper 兑
    (13, 49, 30, 55, 37, 63, 22, 36),  # upper 离
    (25, 17, 21, 51, 42,  3, 27, 24),  # upper 震
    (44, 28, 50, 32, 57, 48, 18, 46),  # upper 巽
    ( 6, 47, 64, 40, 59, 29,  4,  7),  # upper 坎
    (33, 31, 56, 62, 53, 39, 52, 15),  # upper 艮
    (12, 45, 35, 16, 20,  8, 23,  2),  # upper 坤
)


@dataclass(frozen=True, slots=True)
class Hexagram:
    """A cast hexagram.

    `lines` is bottom-to-top: each entry True = yang (⚊), False = yin (⚋).
    `changing` marks which line positions (0-5) are moving lines.
    """

    number: int
    name: str
    lines: tuple[bool, bool, bool, bool, bool, bool]
    changing: tuple[int, ...]

    @property
    def lower_trigram(self) -> int:
        return (self.lines[0] << 0) | (self.lines[1] << 1) | (self.lines[2] << 2)

    @property
    def upper_trigram(self) -> int:
        return (self.lines[3] << 0) | (self.lines[4] << 1) | (self.lines[5] << 2)


def cast_hexagram(seed: str) -> Hexagram:
    """Deterministically 'cast' a hexagram from a string seed.

    Each of the 6 lines is drawn from the seed; ~1/6 of lines are
    marked as changing (moving) lines. Same seed → same hexagram, so a
    given prediction always shows the same reading.
    """
    lines: list[bool] = []
    changing: list[int] = []
    for i in range(6):
        v = _seed_int(seed, f"iching-line-{i}") % 100
        lines.append(v >= 50)            # 50/50 yang/yin
        if v % 6 == 0:                   # ~1/6 moving lines
            changing.append(i)
    lt = (lines[0] << 0) | (lines[1] << 1) | (lines[2] << 2)
    ut = (lines[3] << 0) | (lines[4] << 1) | (lines[5] << 2)
    number = _KING_WEN_GRID[_KW_ORDER.index(ut)][_KW_ORDER.index(lt)]
    return Hexagram(
        number=number,
        name=HEXAGRAM_NAMES[number],
        lines=tuple(lines),  # type: ignore[arg-type]
        changing=tuple(changing),
    )


def hexagram_outcome_prior(hx: Hexagram, outcome: str) -> float:
    """易经 prior P(outcome | hexagram) — a SIMPLIFIED structural model.

    Real 易经 needs an author-reviewed 64-hexagram interpretation
    library. Until then we derive priors from hexagram *structure*,
    which is itself the classical reading logic:
      • yang lines  → drive / action / 刚  → career, wealth.
      • yin  lines  → receptivity / 柔     → marriage, health.
      • a 既济-like balance (alternating) → low conflict, learning.
    """
    yang = sum(hx.lines)
    yin = 6 - yang
    # alternation score: how 'balanced'/woven the lines are.
    alt = sum(1 for i in range(5) if hx.lines[i] != hx.lines[i + 1]) / 5.0
    base = {
        "career_success":     0.40 + 0.10 * yang,
        "wealth_accumulation":0.42 + 0.09 * yang,
        "marriage_stable":    0.42 + 0.09 * yin,
        "health_strong":      0.44 + 0.08 * yin,
        "learning_good":      0.45 + 0.30 * alt,
        "conflict_low":       0.40 + 0.35 * alt,
    }
    return max(0.05, min(0.95, base.get(outcome, 0.5)))


def hexagram_auspice(hx: Hexagram) -> float:
    """Overall hexagram favourability ∈ [0, 1].

    More yang = more forward momentum (read as auspicious here), with a
    bonus for structural balance. Moving lines add mild volatility but
    do not flip the sign.
    """
    yang = sum(hx.lines)
    alt = sum(1 for i in range(5) if hx.lines[i] != hx.lines[i + 1]) / 5.0
    score = 0.30 + 0.45 * (yang / 6.0) + 0.25 * alt
    return max(0.0, min(1.0, score))


# ======================================================================
# System 4 — 塔罗 (Tarot — Major Arcana)
# ======================================================================

# 22 Major Arcana. Each: (key, number, display name, outcome influence
# vector, auspice base). The influence dict shifts the focal-outcome
# prior; auspice is the card's intrinsic favourability when upright.
@dataclass(frozen=True, slots=True)
class TarotCard:
    key: str
    number: int
    name: str
    influence: dict[str, float]   # outcome → signed shift in [-.3, .3]
    auspice: float                # upright favourability in [0, 1]
    glyph: str                    # short symbol name for the renderer


def _tc(key: str, n: int, name: str, glyph: str, auspice: float,
        **infl: float) -> TarotCard:
    return TarotCard(key=key, number=n, name=name, glyph=glyph,
                     auspice=auspice, influence=dict(infl))


TAROT_MAJOR: tuple[TarotCard, ...] = (
    _tc("fool", 0, "The Fool", "spark", 0.60,
        career_success=0.10, learning_good=0.15, wealth_accumulation=-0.05),
    _tc("magician", 1, "The Magician", "wand", 0.78,
        career_success=0.20, wealth_accumulation=0.12, learning_good=0.10),
    _tc("priestess", 2, "The High Priestess", "moon", 0.62,
        learning_good=0.20, health_strong=0.08, conflict_low=0.10),
    _tc("empress", 3, "The Empress", "venus", 0.80,
        marriage_stable=0.20, wealth_accumulation=0.15, health_strong=0.12),
    _tc("emperor", 4, "The Emperor", "throne", 0.72,
        career_success=0.20, conflict_low=-0.05, wealth_accumulation=0.10),
    _tc("hierophant", 5, "The Hierophant", "keys", 0.60,
        learning_good=0.15, marriage_stable=0.12, conflict_low=0.10),
    _tc("lovers", 6, "The Lovers", "heart", 0.82,
        marriage_stable=0.25, conflict_low=0.10),
    _tc("chariot", 7, "The Chariot", "chariot", 0.70,
        career_success=0.18, conflict_low=-0.08),
    _tc("strength", 8, "Strength", "lion", 0.78,
        health_strong=0.20, conflict_low=0.15, career_success=0.08),
    _tc("hermit", 9, "The Hermit", "lantern", 0.55,
        learning_good=0.22, marriage_stable=-0.05),
    _tc("wheel", 10, "Wheel of Fortune", "wheel", 0.68,
        wealth_accumulation=0.18, career_success=0.10),
    _tc("justice", 11, "Justice", "scales", 0.66,
        conflict_low=0.22, career_success=0.08),
    _tc("hanged", 12, "The Hanged Man", "pendulum", 0.42,
        learning_good=0.12, career_success=-0.12),
    _tc("death", 13, "Death", "scythe", 0.40,
        career_success=0.05, conflict_low=-0.05, wealth_accumulation=-0.05),
    _tc("temperance", 14, "Temperance", "chalice", 0.74,
        health_strong=0.20, conflict_low=0.15, marriage_stable=0.10),
    _tc("devil", 15, "The Devil", "chains", 0.30,
        conflict_low=-0.20, wealth_accumulation=0.05, health_strong=-0.12),
    _tc("tower", 16, "The Tower", "tower", 0.22,
        conflict_low=-0.25, career_success=-0.12, wealth_accumulation=-0.15),
    _tc("star", 17, "The Star", "star", 0.85,
        health_strong=0.18, learning_good=0.15, career_success=0.10),
    _tc("moon", 18, "The Moon", "crescent", 0.44,
        conflict_low=-0.10, learning_good=0.08, health_strong=-0.05),
    _tc("sun", 19, "The Sun", "sun", 0.90,
        career_success=0.18, health_strong=0.18, wealth_accumulation=0.12,
        marriage_stable=0.10),
    _tc("judgement", 20, "Judgement", "trumpet", 0.70,
        career_success=0.15, learning_good=0.12),
    _tc("world", 21, "The World", "wreath", 0.88,
        career_success=0.18, wealth_accumulation=0.15, marriage_stable=0.12,
        health_strong=0.10),
)
_TAROT_BY_INDEX: dict[int, TarotCard] = {c.number: c for c in TAROT_MAJOR}


TAROT_POSITIONS: tuple[str, ...] = ("past", "present", "future")


@dataclass(frozen=True, slots=True)
class TarotDraw:
    """A 3-card spread: past / present / future."""

    cards: tuple[TarotCard, TarotCard, TarotCard]
    reversed: tuple[bool, bool, bool]


def draw_tarot(seed: str) -> TarotDraw:
    """Deterministically draw a 3-card Major-Arcana spread from a seed.

    Cards are drawn without replacement. Same seed → same spread.
    """
    pool = list(range(22))
    picked: list[int] = []
    rev: list[bool] = []
    for i in range(3):
        r = _seed_int(seed, f"tarot-pick-{i}")
        idx = pool[r % len(pool)]
        pool.remove(idx)
        picked.append(idx)
        rev.append((_seed_int(seed, f"tarot-rev-{i}") % 100) >= 62)  # ~38% reversed
    cards = tuple(_TAROT_BY_INDEX[i] for i in picked)
    return TarotDraw(cards=cards, reversed=tuple(rev))  # type: ignore[arg-type]


def tarot_outcome_prior(draw: TarotDraw, outcome: str) -> float:
    """塔罗 prior P(outcome) — base 0.5 + summed card influences.

    The 'future' card weighs double; reversed cards invert their
    influence sign and roughly halve the magnitude.
    """
    score = 0.5
    weights = (0.8, 1.0, 1.6)  # past / present / future
    for card, is_rev, w in zip(draw.cards, draw.reversed, weights):
        shift = card.influence.get(outcome, 0.0)
        if is_rev:
            shift = -shift * 0.6
        score += shift * w
    return max(0.05, min(0.95, score))


def tarot_auspice(draw: TarotDraw) -> float:
    """Overall spread favourability — weighted mean of card auspice,
    reversed cards flipped around 0.5."""
    weights = (0.8, 1.0, 1.6)
    total = 0.0
    wsum = 0.0
    for card, is_rev, w in zip(draw.cards, draw.reversed, weights):
        a = (1.0 - card.auspice) if is_rev else card.auspice
        total += a * w
        wsum += w
    return max(0.0, min(1.0, total / (wsum or 1.0)))


# ======================================================================
# System 5 — 占星 (Western astrology — natal chart / 星盘 + 星座)
# ======================================================================

ASTRO_ELEMENTS: tuple[str, ...] = ("fire", "earth", "air", "water")
ASTRO_ELEMENT_COLOR: dict[str, str] = {
    "fire":  "#ff5e6e",
    "earth": "#d8a657",
    "air":   "#8b8cff",
    "water": "#58c5b4",
}


@dataclass(frozen=True, slots=True)
class ZodiacSign:
    key: str
    name: str       # English display name
    glyph: str      # astrological Unicode symbol (♈ …)
    element: str    # fire / earth / air / water
    modality: str   # cardinal / fixed / mutable


# The 12 signs, in zodiac order starting at Aries.
ZODIAC: tuple[ZodiacSign, ...] = (
    ZodiacSign("aries",       "Aries",       "♈", "fire",  "cardinal"),
    ZodiacSign("taurus",      "Taurus",      "♉", "earth", "fixed"),
    ZodiacSign("gemini",      "Gemini",      "♊", "air",   "mutable"),
    ZodiacSign("cancer",      "Cancer",      "♋", "water", "cardinal"),
    ZodiacSign("leo",         "Leo",         "♌", "fire",  "fixed"),
    ZodiacSign("virgo",       "Virgo",       "♍", "earth", "mutable"),
    ZodiacSign("libra",       "Libra",       "♎", "air",   "cardinal"),
    ZodiacSign("scorpio",     "Scorpio",     "♏", "water", "fixed"),
    ZodiacSign("sagittarius", "Sagittarius", "♐", "fire",  "mutable"),
    ZodiacSign("capricorn",   "Capricorn",   "♑", "earth", "cardinal"),
    ZodiacSign("aquarius",    "Aquarius",    "♒", "air",   "fixed"),
    ZodiacSign("pisces",      "Pisces",      "♓", "water", "mutable"),
)

# (month) → (day the *second* sign of that month begins, first-sign index,
# second-sign index). The sun-sign boundaries are exact (tropical zodiac).
_SUN_BOUNDARY: dict[int, tuple[int, int, int]] = {
    1:  (20,  9, 10),   # Capricorn → Aquarius
    2:  (19, 10, 11),   # Aquarius  → Pisces
    3:  (21, 11,  0),   # Pisces    → Aries
    4:  (20,  0,  1),   # Aries     → Taurus
    5:  (21,  1,  2),   # Taurus    → Gemini
    6:  (21,  2,  3),   # Gemini    → Cancer
    7:  (23,  3,  4),   # Cancer    → Leo
    8:  (23,  4,  5),   # Leo       → Virgo
    9:  (23,  5,  6),   # Virgo     → Libra
    10: (23,  6,  7),   # Libra     → Scorpio
    11: (22,  7,  8),   # Scorpio   → Sagittarius
    12: (22,  8,  9),   # Sagittarius → Capricorn
}


def sun_sign(bd: BirthData) -> int:
    """Return the sun-sign index (0-11) — exact tropical-zodiac dates."""
    cut, first, second = _SUN_BOUNDARY[max(1, min(12, bd.month))]
    return second if bd.day >= cut else first


@dataclass(frozen=True, slots=True)
class NatalChart:
    """A simplified natal chart (星盘).

    The sun sign is exact. The moon + rising (ascendant) are SIMPLIFIED
    deterministic placements — a real chart needs an ephemeris + birth
    longitude/latitude (v0.5+). `placements` maps a body key → zodiac
    index, for the renderer.
    """

    sun: int
    moon: int
    rising: int

    @property
    def placements(self) -> dict[str, int]:
        return {"sun": self.sun, "moon": self.moon, "rising": self.rising}


def natal_chart(bd: BirthData) -> NatalChart:
    """Build a simplified natal chart.

    Sun sign is exact. Moon shifts ~1 sign / 2.3 days → a day-driven
    offset; the ascendant shifts ~1 sign / 2 hours → an hour-driven
    offset. Deterministic. Documented as simplified — not an ephemeris.
    """
    sun = sun_sign(bd)
    moon = (sun + (bd.day * 4 + bd.month) // 7) % 12
    rising = (sun + (bd.hour // 2)) % 12
    return NatalChart(sun=sun, moon=moon, rising=rising)


# Outcome prior per element (sun sign). Fire = drive, Earth = ground,
# Air = mind, Water = feeling — mapped to the 6 outcome categories.
_ASTRO_ELEMENT_PRIOR: dict[str, dict[str, float]] = {
    "fire":  {"career_success": 0.72, "marriage_stable": 0.48, "wealth_accumulation": 0.58,
              "health_strong": 0.66, "learning_good": 0.60, "conflict_low": 0.40},
    "earth": {"career_success": 0.62, "marriage_stable": 0.66, "wealth_accumulation": 0.74,
              "health_strong": 0.68, "learning_good": 0.58, "conflict_low": 0.66},
    "air":   {"career_success": 0.60, "marriage_stable": 0.58, "wealth_accumulation": 0.54,
              "health_strong": 0.56, "learning_good": 0.78, "conflict_low": 0.62},
    "water": {"career_success": 0.54, "marriage_stable": 0.70, "wealth_accumulation": 0.52,
              "health_strong": 0.58, "learning_good": 0.66, "conflict_low": 0.58},
}
# Modality nudges the prior slightly: Cardinal favours initiative
# (career), Fixed favours endurance (marriage / wealth), Mutable
# favours adaptability (learning / low conflict).
_ASTRO_MODALITY_NUDGE: dict[str, dict[str, float]] = {
    "cardinal": {"career_success": 0.06, "wealth_accumulation": 0.03},
    "fixed":    {"marriage_stable": 0.06, "wealth_accumulation": 0.04},
    "mutable":  {"learning_good": 0.06, "conflict_low": 0.05},
}


def astro_outcome_prior(chart: NatalChart, outcome: str) -> float:
    """占星 prior P(outcome) from the sun sign's element + modality."""
    sign = ZODIAC[chart.sun]
    base = _ASTRO_ELEMENT_PRIOR.get(sign.element, {}).get(outcome, 0.5)
    base += _ASTRO_MODALITY_NUDGE.get(sign.modality, {}).get(outcome, 0.0)
    return max(0.05, min(0.95, base))


def astro_auspice(chart: NatalChart) -> float:
    """Overall chart favourability ∈ [0, 1].

    The classical 'easy chart' is one where the big three (sun, moon,
    rising) share an element or compatible elements (fire+air, earth+
    water are the harmonious pairs). Concordance → auspicious.
    """
    els = [ZODIAC[i].element for i in (chart.sun, chart.moon, chart.rising)]
    harmonious = {("fire", "air"), ("air", "fire"),
                  ("earth", "water"), ("water", "earth")}
    score = 0.5
    for a in range(3):
        for b in range(a + 1, 3):
            if els[a] == els[b]:
                score += 0.12
            elif (els[a], els[b]) in harmonious:
                score += 0.06
            else:
                score -= 0.04
    return max(0.0, min(1.0, score))


# ======================================================================
# Unified entry point
# ======================================================================

@dataclass(frozen=True, slots=True)
class LensReading:
    """Everything a renderer + the metric readout needs, for any system."""

    system: str
    prior: float           # P(focal outcome | reading)
    auspice: float         # overall favourability ∈ [0, 1]
    # system-specific payloads — exactly one is populated
    bazi: BaZiPattern | None = None
    balance: dict[str, float] | None = None
    ziwei: ZiWeiChart | None = None
    hexagram: Hexagram | None = None
    tarot: TarotDraw | None = None
    natal: NatalChart | None = None


def compute_reading(
    system: str,
    *,
    birth: BirthData,
    seed: str,
    outcome: str,
) -> LensReading:
    """Run the chosen divination system and return a unified reading.

    八字 / 紫微 read from `birth`; 易经 / 塔罗 'cast' from `seed`. The
    `outcome` selects which focal-outcome prior is computed.
    """
    if system == SYSTEM_ZIWEI:
        chart = ziwei_chart(birth)
        return LensReading(
            system=system,
            prior=ziwei_outcome_prior(chart, outcome),
            auspice=ziwei_auspice(chart),
            ziwei=chart,
        )
    if system == SYSTEM_ICHING:
        hx = cast_hexagram(seed)
        return LensReading(
            system=system,
            prior=hexagram_outcome_prior(hx, outcome),
            auspice=hexagram_auspice(hx),
            hexagram=hx,
        )
    if system == SYSTEM_TAROT:
        draw = draw_tarot(seed)
        return LensReading(
            system=system,
            prior=tarot_outcome_prior(draw, outcome),
            auspice=tarot_auspice(draw),
            tarot=draw,
        )
    if system == SYSTEM_ASTRO:
        chart = natal_chart(birth)
        return LensReading(
            system=system,
            prior=astro_outcome_prior(chart, outcome),
            auspice=astro_auspice(chart),
            natal=chart,
        )
    # default — 八字
    bazi = bazi_from_birth(birth)
    balance = wuxing_balance(bazi)
    return LensReading(
        system=SYSTEM_BAZI,
        prior=outcome_prior(bazi, outcome),
        auspice=bazi_auspice(bazi),
        bazi=bazi,
        balance=balance,
    )


__all__ = [
    # shared
    "OUTCOME_CATEGORIES", "CombinationMode", "combine_with_model",
    "apply_lens_to_branches",
    "SYSTEM_BAZI", "SYSTEM_ZIWEI", "SYSTEM_ICHING", "SYSTEM_TAROT",
    "SYSTEM_ASTRO", "SYSTEMS",
    "LensReading", "compute_reading",
    # bazi
    "BirthData", "BaZiPattern", "bazi_from_birth", "wuxing_balance",
    "dominant_element", "yongshen", "pillar_text", "outcome_prior",
    "bazi_auspice", "WUXING_KEYS", "WUXING_HANZI", "WUXING_COLOR",
    "WUXING_COLOR_DEEP", "HEAVENLY_STEMS", "EARTHLY_BRANCHES",
    # ziwei
    "ZIWEI_PALACES", "ZIWEI_PALACE_HANZI", "ZIWEI_STARS", "ZiWeiChart",
    "ziwei_chart", "ziwei_outcome_prior", "ziwei_auspice", "ziwei_star_hanzi",
    # iching
    "TRIGRAM_HANZI", "TRIGRAM_SYMBOL", "HEXAGRAM_NAMES", "Hexagram",
    "cast_hexagram", "hexagram_outcome_prior", "hexagram_auspice",
    # tarot
    "TarotCard", "TarotDraw", "TAROT_MAJOR", "TAROT_POSITIONS", "draw_tarot",
    "tarot_outcome_prior", "tarot_auspice",
    # astrology
    "ZodiacSign", "ZODIAC", "NatalChart", "ASTRO_ELEMENTS",
    "ASTRO_ELEMENT_COLOR", "sun_sign", "natal_chart",
    "astro_outcome_prior", "astro_auspice",
]
