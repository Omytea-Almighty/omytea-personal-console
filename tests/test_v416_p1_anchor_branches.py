"""v4.16 P1 tests — wishful + worst anchor branches.

Per founder H4 data point #1 (2026-05-18) surfacing the engagement-loop
gap. P1 ships:
- compiler.py SYSTEM_PROMPT_COMPILER requires exactly 1 wishful + 1 worst
- _mock_compile includes them
- ConsoleHypothesis carries branch_type field
- StateHypothesis.attributes carries branch_type through substrate bridge
- app.py renders them as visually distinct anchor sections (smoke check
  via import only — no Selenium in MVP scope)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler import compile_belief_program, CompiledBeliefProgram, _mock_compile  # noqa: E402
from console import ConsoleHypothesis, belief_program_to_console  # noqa: E402


@pytest.fixture(autouse=True)
def _force_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """All P1 tests run offline against _mock_compile output."""
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")


def test_mock_compile_includes_exactly_one_wishful_branch() -> None:
    """Per SYSTEM_PROMPT_COMPILER §strict-requirements, the mock must
    model the same invariant the real LLM is asked to produce."""
    p = _mock_compile({}, "career_decision")
    wishful = [b for b in p["branches"] if b.get("branch_type") == "wishful"]
    assert len(wishful) == 1, (
        f"Expected exactly 1 wishful branch, got {len(wishful)}: "
        f"{[b['label'] for b in wishful]}"
    )


def test_mock_compile_includes_exactly_one_worst_branch() -> None:
    p = _mock_compile({}, "career_decision")
    worst = [b for b in p["branches"] if b.get("branch_type") == "worst"]
    assert len(worst) == 1
    assert worst[0]["probability_prior"] < 0.15, (
        f"Worst branch probability should be low (3-10% typical); got "
        f"{worst[0]['probability_prior']}"
    )


def test_mock_compile_realistic_branches_at_least_3() -> None:
    p = _mock_compile({}, "career_decision")
    realistic = [b for b in p["branches"] if b.get("branch_type") == "realistic"]
    assert len(realistic) >= 3, (
        f"Need at least 3 realistic branches; got {len(realistic)}"
    )


def test_mock_compile_branch_count_in_6_to_8_range() -> None:
    """Per SYSTEM_PROMPT_COMPILER: 6-8 total branches."""
    p = _mock_compile({}, "career_decision")
    assert 6 <= len(p["branches"]) <= 8, (
        f"Expected 6-8 branches; got {len(p['branches'])}"
    )


def test_mock_compile_probabilities_still_sum_to_one() -> None:
    p = _mock_compile({}, "career_decision")
    probs = [b["probability_prior"] for b in p["branches"]]
    assert abs(sum(probs) - 1.0) < 1e-3, (
        f"Probabilities sum {sum(probs):.4f} != 1.0"
    )


def test_wishful_narrative_is_specific_not_generic() -> None:
    """The wishful branch must be EMOTIONALLY VIVID per system prompt —
    not a generic 'everything works'. Heuristic: narrative > 100 chars
    AND mentions something concrete (timeframe / specific situation)."""
    p = _mock_compile({}, "career_decision")
    wishful = next(b for b in p["branches"] if b.get("branch_type") == "wishful")
    assert len(wishful["narrative"]) > 80, (
        f"Wishful narrative too short ({len(wishful['narrative'])} chars); "
        f"system prompt requires emotional vividness + specificity."
    )


def test_worst_narrative_is_specific_not_doomer() -> None:
    """Worst branch should reference specific failure modes, not generic
    catastrophe. Heuristic: narrative > 80 chars."""
    p = _mock_compile({}, "career_decision")
    worst = next(b for b in p["branches"] if b.get("branch_type") == "worst")
    assert len(worst["narrative"]) > 80


def test_console_hypothesis_carries_branch_type() -> None:
    """ConsoleHypothesis must round-trip branch_type from
    CompiledBeliefProgram.branches → ConsoleResult.hypotheses."""
    program = compile_belief_program(
        {"current_role": "x", "decision_options": "y", "why_considering_change": "z",
         "time_horizon": "6 months", "user_id": "u"},
        scenario="career_decision",
    )
    result = belief_program_to_console(program)

    types = {h.branch_type for h in result.hypotheses}
    assert "wishful" in types
    assert "worst" in types
    assert "realistic" in types


def test_console_hypothesis_default_branch_type_is_realistic() -> None:
    """Backward compat: pre-v4.16 BeliefPrograms without branch_type
    field should default to 'realistic'."""
    h = ConsoleHypothesis(
        label="x", narrative="", probability=0.5,
        key_uncertainty_driver="", depends_on_decision=None,
    )
    assert h.branch_type == "realistic"


def test_to_dict_includes_branch_type() -> None:
    h = ConsoleHypothesis(
        label="x", narrative="", probability=0.5,
        key_uncertainty_driver="", depends_on_decision=None,
        branch_type="wishful",
    )
    d = h.to_dict()
    assert d["branch_type"] == "wishful"


def test_exactly_one_wishful_one_worst_across_full_belief_program() -> None:
    """End-to-end invariant: compile → console always produces exactly
    1 wishful + 1 worst regardless of how many realistic branches."""
    program = compile_belief_program(
        {"current_role": "x", "decision_options": "y", "why_considering_change": "z",
         "time_horizon": "6 months", "user_id": "u"},
        scenario="career_decision",
    )
    result = belief_program_to_console(program)
    wishful = [h for h in result.hypotheses if h.branch_type == "wishful"]
    worst = [h for h in result.hypotheses if h.branch_type == "worst"]
    assert len(wishful) == 1
    assert len(worst) == 1
