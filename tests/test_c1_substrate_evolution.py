"""C1 tests — Lindblad evolution of off-diagonal coherence over time.

These tests verify the substrate runtime layer: that calling
`evolve_offdiagonal_coherence()` on a ConsoleResult with real Omytea
substrate actually invokes LindbladOperator and produces time-snapshot
data showing coherence decay.

Skipped automatically if Omytea isn't importable (e.g. CI without
WMDB parent repo installed).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force non-mock mode for substrate tests
@pytest.fixture(autouse=True)
def _ensure_non_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)

omytea_importable = True
try:
    import omytea.quantum  # noqa: F401
    import omytea.joint_belief  # noqa: F401
    import omytea.dynamics.lindblad  # noqa: F401
    import omytea.dynamics.protocol  # noqa: F401
except ImportError:
    omytea_importable = False

pytestmark = pytest.mark.skipif(
    not omytea_importable,
    reason="omytea + omytea.dynamics not installed; substrate evolution tests skip.",
)


from compiler import CompiledBeliefProgram  # noqa: E402
from console import (  # noqa: E402
    _parse_time_horizon_to_steps,
    _short_label,
    belief_program_to_console,
    build_coherence_chart_data,
    evolve_offdiagonal_coherence,
    evolve_from_time_horizon_string,
)


_FIXTURE_PROGRAM = {
    "scenario": "career_decision",
    "decision_options": ["accept_offer", "stay_current"],
    "branches": [
        {
            "label": "thrive_at_new_role",
            "branch_type": "realistic",
            "narrative": "Accept the offer and the role suits you.",
            "probability_prior": 0.40,
            "key_uncertainty_driver": "team_culture_fit",
            "depends_on_decision": "accept_offer",
        },
        {
            "label": "burnout_within_3mo",
            "branch_type": "realistic",
            "narrative": "Accept the offer but burn out within 3 months.",
            "probability_prior": 0.20,
            "key_uncertainty_driver": "workload_intensity",
            "depends_on_decision": "accept_offer",
        },
        {
            "label": "stay_and_thrive",
            "branch_type": "realistic",
            "narrative": "Stay at current job and conditions improve.",
            "probability_prior": 0.40,
            "key_uncertainty_driver": "manager_willingness",
            "depends_on_decision": "stay_current",
        },
    ],
    "joint_offdiag": [
        {
            "branch_a": "burnout_within_3mo",
            "branch_b": "stay_and_thrive",
            "coherence_strength": -0.5,
            "rationale": "Mutually exclusive paths.",
        },
        {
            "branch_a": "thrive_at_new_role",
            "branch_b": "burnout_within_3mo",
            "coherence_strength": -0.3,
            "rationale": "Same-decision exclusive outcomes.",
        },
    ],
    "recommended_evidence": [
        {"evidence_label": "diagnostic_call", "sensitivity": 0.7},
    ],
}


# ----- Time horizon parser -----


def test_parse_time_horizon_matches_known_strings() -> None:
    assert _parse_time_horizon_to_steps("3 months") == 3
    assert _parse_time_horizon_to_steps("6 months") == 6
    assert _parse_time_horizon_to_steps("12 months") == 12
    assert _parse_time_horizon_to_steps("24 months") == 24


def test_parse_time_horizon_disambiguates_overlapping_substrings() -> None:
    """'12 months' should NOT match the '3' substring → 3, etc.
    Sorted descending checks 24 → 12 → 6 → 3 in order so '12' returns 12
    rather than 6 (which would happen if we matched '6' substring naively)."""
    assert _parse_time_horizon_to_steps("12 months") == 12


def test_parse_time_horizon_defaults_to_6_on_empty() -> None:
    assert _parse_time_horizon_to_steps("") == 6


def test_parse_time_horizon_fallback_to_first_int() -> None:
    """If a non-standard value comes through (e.g. "9 months"), extract
    the first integer."""
    assert _parse_time_horizon_to_steps("9 months") == 9


# ----- evolve_offdiagonal_coherence behavior -----


def test_evolve_skips_when_no_substrate() -> None:
    """If we pass a ConsoleResult with used_omytea_substrate=False,
    must return {skipped: True, reason: 'no_substrate'}."""
    from console import ConsoleHypothesis, ConsoleOffDiagonal, ConsoleResult

    result = ConsoleResult(
        scenario="x",
        decision_options=["a"],
        hypotheses=[
            ConsoleHypothesis(
                label="h1", narrative="", probability=1.0,
                key_uncertainty_driver="", depends_on_decision=None,
            ),
        ],
        joint_offdiag=[],
        recommended_evidence=[],
        used_omytea_substrate=False,
    )
    out = evolve_offdiagonal_coherence(result, time_horizon_months=6)
    assert out["skipped"] is True
    assert out["reason"] == "no_substrate"


def test_evolve_produces_snapshot_per_tick() -> None:
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)
    assert result.used_omytea_substrate is True

    out = evolve_offdiagonal_coherence(
        result, time_horizon_months=6, decoherence_rate_per_month=0.05,
    )
    assert out["skipped"] is False
    # Should have N+1 snapshots: tick 0 + ticks 1..N
    assert len(out["evolved"]) == 7
    assert out["evolved"][0]["tick"] == 0
    assert out["evolved"][-1]["tick"] == 6


def test_evolve_off_diagonal_magnitudes_decay_over_time() -> None:
    """Lindblad's purpose: |ρ_kl| decays exponentially at rate γ.
    With γ=0.05/month, after 6 months magnitude should multiply by
    exp(-0.30) ≈ 0.741 of original."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_offdiagonal_coherence(
        result, time_horizon_months=6, decoherence_rate_per_month=0.05,
        use_branch_energies=False,  # disable rotation; pure decay
    )
    assert out["skipped"] is False

    # Walk pairs at tick 0 vs tick 6
    initial = {(e["row_label"], e["col_label"]): e["amplitude_magnitude"]
               for e in out["evolved"][0]["off_diagonal_entries"]}
    final = {(e["row_label"], e["col_label"]): e["amplitude_magnitude"]
             for e in out["evolved"][-1]["off_diagonal_entries"]}

    for key in initial:
        if initial[key] > 0.01:  # skip near-zero amplitudes
            ratio = final[key] / initial[key]
            expected_ratio = math.exp(-0.05 * 6)
            assert abs(ratio - expected_ratio) < 0.05, (
                f"Decay ratio for {key} = {ratio:.3f}, expected ≈ "
                f"{expected_ratio:.3f}"
            )


def test_evolve_with_branch_energies_rotates_phase() -> None:
    """With branch_energies=True, the unitary part should rotate the
    complex phase. Amplitude magnitudes still decay; but imaginary part
    should grow from 0 if rotation is happening."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_offdiagonal_coherence(
        result, time_horizon_months=6, decoherence_rate_per_month=0.05,
        use_branch_energies=True,
    )
    assert out["skipped"] is False

    # At tick 0, all imag parts should be 0 (real amplitudes from LLM)
    initial_imags = [abs(e["amplitude_imag"])
                     for e in out["evolved"][0]["off_diagonal_entries"]]
    assert all(im < 1e-9 for im in initial_imags), (
        "Initial off-diagonals should be real-valued from LLM output"
    )

    # At tick 6, some imag parts should be non-zero IF E_k ≠ E_l for
    # any pair. Branches have different probabilities → different
    # energies → some rotation.
    final_imags = [abs(e["amplitude_imag"])
                   for e in out["evolved"][-1]["off_diagonal_entries"]]
    # At least one pair should have meaningful rotation
    assert any(im > 0.01 for im in final_imags), (
        "Expected non-trivial phase rotation with branch energies enabled"
    )


def test_evolve_without_energies_no_rotation() -> None:
    """When use_branch_energies=False, imag part stays 0 (pure decay)."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_offdiagonal_coherence(
        result, time_horizon_months=6, decoherence_rate_per_month=0.05,
        use_branch_energies=False,
    )
    final_imags = [abs(e["amplitude_imag"])
                   for e in out["evolved"][-1]["off_diagonal_entries"]]
    assert all(im < 1e-9 for im in final_imags)


def test_evolve_zero_decoherence_preserves_magnitude() -> None:
    """γ=0 → no decay; magnitudes unchanged across ticks."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_offdiagonal_coherence(
        result, time_horizon_months=10, decoherence_rate_per_month=0.0,
        use_branch_energies=False,
    )
    initial = sorted(e["amplitude_magnitude"]
                     for e in out["evolved"][0]["off_diagonal_entries"])
    final = sorted(e["amplitude_magnitude"]
                   for e in out["evolved"][-1]["off_diagonal_entries"])
    for i, f in zip(initial, final):
        assert abs(i - f) < 1e-9


def test_evolve_high_decoherence_collapses_to_zero() -> None:
    """γ=1.0/month: after 10 months, magnitudes are exp(-10) ≈ 4.5e-5,
    effectively zero (classical correlation lost)."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_offdiagonal_coherence(
        result, time_horizon_months=10, decoherence_rate_per_month=1.0,
        use_branch_energies=False,
    )
    final_mags = [e["amplitude_magnitude"]
                  for e in out["evolved"][-1]["off_diagonal_entries"]]
    assert all(m < 1e-3 for m in final_mags), (
        f"High γ should collapse off-diagonals; final mags = {final_mags}"
    )


def test_evolve_snapshot_labels_match_original_branches() -> None:
    """Snapshot entries should reference branch_label strings, not
    integer indices."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_offdiagonal_coherence(result, time_horizon_months=3)
    entries = out["evolved"][0]["off_diagonal_entries"]
    known_labels = {h.label for h in result.hypotheses}
    for e in entries:
        assert e["row_label"] in known_labels, (
            f"Unknown label in evolved snapshot: {e['row_label']}"
        )
        assert e["col_label"] in known_labels


def test_evolve_from_time_horizon_string_parses_and_evolves() -> None:
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_from_time_horizon_string(result, "6 months")
    assert out["skipped"] is False
    assert out["n_steps"] == 6
    assert len(out["evolved"]) == 7


def test_evolve_horizon_24_months_produces_24_snapshots() -> None:
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    out = evolve_from_time_horizon_string(result, "24 months")
    assert out["n_steps"] == 24
    assert len(out["evolved"]) == 25


# ----- Short-label helper -----


def test_short_label_passthrough_when_short() -> None:
    assert _short_label("abc") == "abc"


def test_short_label_truncates_with_ellipsis() -> None:
    out = _short_label("thrive_at_new_role_with_amazing_team", max_len=18)
    assert len(out) == 18
    assert out.endswith("…")


def test_short_label_respects_custom_max_len() -> None:
    assert _short_label("a" * 30, max_len=10) == "a" * 9 + "…"


# ----- build_coherence_chart_data — C1 UI shaping -----


def test_chart_data_returns_none_when_no_substrate() -> None:
    """If the result wasn't built on real Omytea substrate, the helper
    must return None so the UI degrades gracefully."""
    from console import ConsoleHypothesis, ConsoleResult

    result = ConsoleResult(
        scenario="x",
        decision_options=["a"],
        hypotheses=[
            ConsoleHypothesis(
                label="h1", narrative="", probability=1.0,
                key_uncertainty_driver="", depends_on_decision=None,
            ),
        ],
        joint_offdiag=[],
        recommended_evidence=[],
        used_omytea_substrate=False,
    )
    assert build_coherence_chart_data(result, time_horizon_months=6) is None


def test_chart_data_has_expected_keys() -> None:
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(
        result, time_horizon_months=6, decoherence_rate_per_month=0.05,
    )
    assert chart is not None
    for key in (
        "tick_labels", "magnitude_series", "pairs_summary",
        "n_steps", "decoherence_rate", "use_branch_energies",
        "expected_decay_ratio",
    ):
        assert key in chart


def test_chart_data_tick_labels_match_horizon() -> None:
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(result, time_horizon_months=6)
    assert chart is not None
    assert len(chart["tick_labels"]) == 7  # t=0 plus 1..6
    assert chart["tick_labels"][0] == "t=0"
    assert chart["tick_labels"][-1] == "t=6mo"


def test_chart_data_dedupes_hermitian_pairs() -> None:
    """JointWaveFunction stores both (a,b) and (b,a) for each off-diagonal
    coupling. The chart should only plot each unordered pair once."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)
    # The fixture has 2 user-facing off-diagonal couplings, so the
    # JointWaveFunction has 4 Hermitian entries — but the chart should
    # collapse them to 2 unique pairs.
    chart = build_coherence_chart_data(result, time_horizon_months=3)
    assert chart is not None
    assert len(chart["magnitude_series"]) == 2
    assert len(chart["pairs_summary"]) == 2


def test_chart_data_magnitude_series_lengths_match_ticks() -> None:
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(result, time_horizon_months=12)
    assert chart is not None
    for series in chart["magnitude_series"].values():
        assert len(series) == 13  # t=0..12


def test_chart_data_pairs_summary_sorted_by_initial_magnitude_desc() -> None:
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(result, time_horizon_months=6)
    assert chart is not None
    initials = [p["initial"] for p in chart["pairs_summary"]]
    assert initials == sorted(initials, reverse=True)


def test_chart_data_decay_pct_positive_for_decoherence() -> None:
    """With γ>0, every pair's final magnitude must be lower than its
    initial. decay_pct should be > 0."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(
        result, time_horizon_months=6, decoherence_rate_per_month=0.1,
    )
    assert chart is not None
    for p in chart["pairs_summary"]:
        assert p["final"] < p["initial"] + 1e-9
        assert p["decay_pct"] > 0.0


def test_chart_data_zero_decoherence_yields_zero_decay() -> None:
    """γ=0 → magnitudes preserved → decay_pct ≈ 0 for every pair."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(
        result, time_horizon_months=6, decoherence_rate_per_month=0.0,
    )
    assert chart is not None
    for p in chart["pairs_summary"]:
        assert abs(p["decay_pct"]) < 1e-6


def test_chart_data_expected_decay_ratio_matches_analytic() -> None:
    """expected_decay_ratio = exp(-γ·N). Sanity-check it lines up with
    the pure-decay observed in pairs_summary."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(
        result, time_horizon_months=6, decoherence_rate_per_month=0.05,
        use_branch_energies=False,
    )
    assert chart is not None
    expected = chart["expected_decay_ratio"]
    assert abs(expected - math.exp(-0.30)) < 1e-9
    # Strongest-coherence pair should decay by approximately that ratio.
    for p in chart["pairs_summary"]:
        if p["initial"] > 0.01:
            ratio = p["final"] / p["initial"]
            assert abs(ratio - expected) < 0.05


def test_chart_data_legend_labels_truncate_long_names() -> None:
    """Series legend keys must be short enough to fit a Streamlit chart
    legend (helper uses 18-char truncation)."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(result, time_horizon_months=3)
    assert chart is not None
    for legend in chart["magnitude_series"].keys():
        # Format is "|(a, b)|" where a, b each capped at 18 chars; total
        # length is bounded by 2*18 + 6 punctuation chars.
        assert len(legend) <= 2 * 18 + 6


def test_chart_data_carries_rationale_back_into_summary() -> None:
    """Each pairs_summary row should re-attach the user-facing rationale
    string from result.joint_offdiag so the UI can show 'why this pair
    matters' alongside the numbers."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    chart = build_coherence_chart_data(result, time_horizon_months=3)
    assert chart is not None
    # The fixture's two couplings carry "Mutually exclusive paths." and
    # "Same-decision exclusive outcomes." rationales.
    rationales = {p["rationale"] for p in chart["pairs_summary"]}
    assert "Mutually exclusive paths." in rationales
    assert "Same-decision exclusive outcomes." in rationales
