"""v4.16 P4 — human-narrative presentation helpers.

Verifies:
- ``storyform_narrative`` opener prepending + idempotence
- ``build_branch_comparison_rows`` shape + sort order
- ``build_decision_timeline_mermaid`` syntax + branch tagging
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from console import (  # noqa: E402
    ConsoleHypothesis,
    ConsoleResult,
    build_branch_comparison_rows,
    build_decision_timeline_mermaid,
    storyform_narrative,
)


def _make_hyp(
    label: str,
    branch_type: str = "realistic",
    probability: float = 0.2,
    narrative: str = "",
    depends_on_decision: str | None = None,
    key_uncertainty_driver: str = "x",
) -> ConsoleHypothesis:
    return ConsoleHypothesis(
        label=label,
        narrative=narrative,
        probability=probability,
        key_uncertainty_driver=key_uncertainty_driver,
        depends_on_decision=depends_on_decision,
        branch_type=branch_type,
    )


def _make_result(
    hyps: list[ConsoleHypothesis],
    decision_options: list[str] | None = None,
) -> ConsoleResult:
    return ConsoleResult(
        scenario="career_decision",
        decision_options=decision_options or ["accept_offer", "stay_current"],
        hypotheses=hyps,
        joint_offdiag=[],
        recommended_evidence=[],
        used_omytea_substrate=False,
    )


# ----- storyform_narrative -----


def test_storyform_realistic_prepends_canonical_opener() -> None:
    out = storyform_narrative(
        "Accept the offer and the role mostly suits you.", "realistic",
    )
    assert out.startswith("In this future, ")
    assert "accept" in out  # lowercased


def test_storyform_wishful_uses_aligns_opener() -> None:
    out = storyform_narrative(
        "Team culture is exceptional and you ship great work.", "wishful",
    )
    assert out.startswith("If everything aligns, ")


def test_storyform_worst_uses_worst_opener() -> None:
    out = storyform_narrative(
        "Career trajectory stalls 12-18 months.", "worst",
    )
    assert out.startswith("If things go the worst plausible way, ")


def test_storyform_unknown_branch_type_falls_back_realistic() -> None:
    out = storyform_narrative("Outcome X happens.", "uninvented_type")
    assert out.startswith("In this future, ")


def test_storyform_idempotent_when_already_storyform() -> None:
    """If the LLM already wrote 'In this future, ...' don't double-prefix."""
    already = "In this future, you ship great work."
    assert storyform_narrative(already, "realistic") == already


def test_storyform_idempotent_when_starts_with_lighter_cue() -> None:
    cues = [
        "Imagine accepting the offer.",
        "Picture this: the new role is great.",
        "If everything aligns: team is incredible.",
    ]
    for c in cues:
        assert storyform_narrative(c, "realistic") == c


def test_storyform_empty_input_returns_empty() -> None:
    assert storyform_narrative("", "realistic") == ""
    assert storyform_narrative("   ", "realistic") == ""


def test_storyform_preserves_acronym_casing() -> None:
    """Sentences starting with an acronym should NOT have their first
    char lowercased — 'EIN approved' shouldn't become 'eIN'."""
    out = storyform_narrative("EIN is approved within 14 days.", "realistic")
    assert "EIN" in out  # acronym preserved
    assert out.startswith("In this future, EIN")


def test_storyform_strips_leading_whitespace() -> None:
    out = storyform_narrative("   the new role works.", "realistic")
    # First non-whitespace char was lower → still lower after merge
    assert out == "In this future, the new role works."


# ----- build_branch_comparison_rows -----


def test_comparison_rows_contains_one_per_hypothesis() -> None:
    result = _make_result([
        _make_hyp("a", probability=0.5),
        _make_hyp("b", probability=0.3),
        _make_hyp("c", probability=0.2),
    ])
    rows = build_branch_comparison_rows(result)
    assert len(rows) == 3


def test_comparison_rows_sort_wishful_first_worst_last() -> None:
    result = _make_result([
        _make_hyp("real", "realistic", probability=0.40),
        _make_hyp("worst", "worst", probability=0.05),
        _make_hyp("wish", "wishful", probability=0.05),
    ])
    rows = build_branch_comparison_rows(result)
    types_in_order = [r["Type"] for r in rows]
    assert types_in_order == ["wishful", "realistic", "worst"]


def test_comparison_rows_realistic_sorted_desc_by_probability() -> None:
    result = _make_result([
        _make_hyp("low", "realistic", probability=0.1),
        _make_hyp("hi",  "realistic", probability=0.5),
        _make_hyp("mid", "realistic", probability=0.3),
    ])
    rows = build_branch_comparison_rows(result)
    labels = [r["Branch"] for r in rows]
    assert labels == ["hi", "mid", "low"]


def test_comparison_rows_probability_rendered_as_pct() -> None:
    result = _make_result([_make_hyp("a", probability=0.3245)])
    rows = build_branch_comparison_rows(result)
    assert rows[0]["Probability"] == "32.5%"


def test_comparison_rows_uses_em_dash_for_no_decision() -> None:
    result = _make_result([
        _make_hyp("a", depends_on_decision=None),
    ])
    rows = build_branch_comparison_rows(result)
    assert rows[0]["Decision"] == "—"


def test_comparison_rows_truncates_long_narrative() -> None:
    long_narr = "x" * 200
    result = _make_result([_make_hyp("a", narrative=long_narr)])
    rows = build_branch_comparison_rows(result)
    preview = rows[0]["Narrative (preview)"]
    assert len(preview) <= 120
    assert preview.endswith("…")


def test_comparison_rows_keeps_short_narrative() -> None:
    """A narrative within the limit must not get truncation marker."""
    short = "Accept the offer."
    result = _make_result([_make_hyp("a", narrative=short)])
    rows = build_branch_comparison_rows(result)
    assert rows[0]["Narrative (preview)"] == short
    assert "…" not in rows[0]["Narrative (preview)"]


def test_comparison_rows_sort_key_field_dropped() -> None:
    """Internal _sort_key must NOT leak into rendered rows."""
    result = _make_result([_make_hyp("a")])
    rows = build_branch_comparison_rows(result)
    assert "_sort_key" not in rows[0]


# ----- build_decision_timeline_mermaid -----


def test_timeline_starts_with_flowchart_lr_header() -> None:
    result = _make_result([_make_hyp("a", depends_on_decision="accept_offer")])
    diagram = build_decision_timeline_mermaid(result)
    assert diagram.splitlines()[0].strip() == "flowchart LR"


def test_timeline_has_now_to_horizon_edge() -> None:
    result = _make_result([_make_hyp("a")])
    diagram = build_decision_timeline_mermaid(result)
    assert "Now([Now])" in diagram
    assert "Horizon" in diagram


def test_timeline_renders_each_decision_option() -> None:
    result = _make_result(
        [_make_hyp("a", depends_on_decision="accept_offer"),
         _make_hyp("b", depends_on_decision="stay_current")],
    )
    diagram = build_decision_timeline_mermaid(result)
    assert "Decide: accept_offer" in diagram
    assert "Decide: stay_current" in diagram


def test_timeline_tags_branch_types_with_emoji() -> None:
    result = _make_result([
        _make_hyp("a", "wishful", probability=0.05,
                  depends_on_decision="accept_offer"),
        _make_hyp("b", "worst", probability=0.05,
                  depends_on_decision="accept_offer"),
        _make_hyp("c", "realistic", probability=0.5,
                  depends_on_decision="accept_offer"),
    ])
    diagram = build_decision_timeline_mermaid(result)
    assert "🌟" in diagram
    assert "⚠️" in diagram
    assert "📊" in diagram


def test_timeline_renders_standalone_branches_directly_from_horizon() -> None:
    """A hypothesis with no depends_on_decision should connect from
    Horizon directly, not from any decision option."""
    result = _make_result(
        [_make_hyp("standalone", depends_on_decision=None)],
        decision_options=["accept_offer"],
    )
    diagram = build_decision_timeline_mermaid(result)
    assert "Horizon --> L_standalone" in diagram


def test_timeline_respects_custom_horizon_label() -> None:
    result = _make_result([_make_hyp("a")])
    diagram = build_decision_timeline_mermaid(
        result, time_horizon_label="6 months",
    )
    assert "Horizon[6 months]" in diagram


def test_timeline_empty_result_still_produces_valid_header() -> None:
    """No hypotheses + no decisions → just the Now → Horizon edge."""
    result = _make_result([], decision_options=[])
    diagram = build_decision_timeline_mermaid(result)
    assert diagram.startswith("flowchart LR")
    # And ends with the Now → Horizon edge.
    assert "Now([Now]) --> Horizon[decision horizon]" in diagram
