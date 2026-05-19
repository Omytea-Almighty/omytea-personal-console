"""Substrate-bridge test — verifies console actually constructs real Omytea
WaveFunction + JointWaveFunction (not pure-dict fallback).

These tests REQUIRE Omytea to be importable. They run WITHOUT mock mode
(OMYTEA_CONSOLE_MOCK unset) AND without Anthropic API (compiler.py mock
mode is independent of OMYTEA_CONSOLE_MOCK — we use a stubbed compiler
output to avoid API dependency).

Per founder review 2026-05-18: until these tests pass, the MVP cannot
honestly claim "real off-diagonal substrate" — only "LLM-generated
correlation description with substrate bridge planned".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _ensure_non_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force non-mock mode for every substrate test, regardless of how
    the test process was launched (e.g., when running alongside the
    mock-mode smoke suite). The substrate bridge contract requires the
    real Omytea import path."""
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Skip the whole module if omytea isn't importable in this environment.
omytea_importable = True
try:
    import omytea.quantum  # noqa: F401
    import omytea.joint_belief  # noqa: F401
    import omytea.models  # noqa: F401
except ImportError:
    omytea_importable = False

pytestmark = pytest.mark.skipif(
    not omytea_importable,
    reason="omytea not installed in test environment; install with "
    "`pip install -e <parent_repo>` to run substrate-bridge tests.",
)


from compiler import CompiledBeliefProgram  # noqa: E402
from console import (  # noqa: E402
    belief_program_to_console,
    availability_status,
)


_FIXTURE_PROGRAM = {
    "scenario": "career_decision",
    "decision_options": ["accept_offer", "stay_current"],
    "branches": [
        {
            "label": "thrive_at_new_role",
            "narrative": "Accept the offer and the role suits you.",
            "probability_prior": 0.4,
            "key_uncertainty_driver": "team_culture_fit",
            "depends_on_decision": "accept_offer",
        },
        {
            "label": "burnout_within_3mo",
            "narrative": "Accept the offer but burn out within 3 months.",
            "probability_prior": 0.2,
            "key_uncertainty_driver": "workload_intensity",
            "depends_on_decision": "accept_offer",
        },
        {
            "label": "stay_and_thrive",
            "narrative": "Stay at current job and conditions improve.",
            "probability_prior": 0.4,
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


def test_omytea_substrate_is_available() -> None:
    """Pre-condition: omytea must be importable + non-mock mode."""
    status = availability_status()
    assert status["omytea_available"] is True, (
        f"omytea not available: {status['omytea_import_error']}. "
        f"Run `pip install -e <parent_repo>` first."
    )
    assert status["mock_mode"] is False, (
        "Test must run without OMYTEA_CONSOLE_MOCK=1. Unset it."
    )


def test_belief_program_constructs_real_wavefunction() -> None:
    """The bridge must produce an honest-to-god omytea.quantum.WaveFunction
    (not the pure-dict fallback)."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    assert result.used_omytea_substrate is True, (
        "console.py fell back to pure-dict; substrate bridge is broken. "
        "Check stderr for the construction error."
    )
    assert result.omytea_wavefunction is not None

    from omytea.quantum import WaveFunction, StateHypothesis

    wf = result.omytea_wavefunction
    assert isinstance(wf, WaveFunction)
    assert wf.object_id == "user_future_self"
    assert wf.label == "user_future_self"
    assert wf.stream_id.startswith("personal_future_career_decision")
    assert len(wf.hypotheses) == 3
    assert all(isinstance(h, StateHypothesis) for h in wf.hypotheses)


def test_wavefunction_weights_match_belief_program_probabilities() -> None:
    """StateHypothesis.weight should carry probability_prior verbatim
    (StateHypothesis.probability is a @property of .weight)."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)
    wf = result.omytea_wavefunction
    assert wf is not None

    weight_by_label = {h.label: h.weight for h in wf.hypotheses}
    assert weight_by_label["thrive_at_new_role"] == pytest.approx(0.4)
    assert weight_by_label["burnout_within_3mo"] == pytest.approx(0.2)
    assert weight_by_label["stay_and_thrive"] == pytest.approx(0.4)

    # And via the .probability property
    prob_by_label = {h.label: h.probability for h in wf.hypotheses}
    assert prob_by_label["thrive_at_new_role"] == pytest.approx(0.4)


def test_state_hypothesis_carries_narrative_in_attributes() -> None:
    """The narrative + key_uncertainty_driver must land in
    StateHypothesis.attributes (since StateHypothesis schema doesn't
    have dedicated fields for them)."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)
    wf = result.omytea_wavefunction
    assert wf is not None

    h_burnout = next(h for h in wf.hypotheses if h.label == "burnout_within_3mo")
    assert h_burnout.attributes.get("narrative", "").startswith("Accept the offer")
    assert h_burnout.attributes.get("key_uncertainty_driver") == "workload_intensity"
    assert h_burnout.attributes.get("depends_on_decision") == "accept_offer"


def test_joint_wavefunction_off_diagonal_with_real_types() -> None:
    """JointWaveFunction must construct with real OffDiagonalEntry instances
    using integer row/col indices (not branch label strings)."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)

    from omytea.joint_belief import (
        JointBranchHypothesis,
        JointWaveFunction,
        OffDiagonalEntry,
    )

    jwf = result.omytea_joint_wavefunction
    assert jwf is not None
    assert isinstance(jwf, JointWaveFunction)
    assert jwf.entity_ids == ("user_future_self",)
    assert len(jwf.hypotheses) == 3
    assert all(isinstance(h, JointBranchHypothesis) for h in jwf.hypotheses)

    # Off-diagonal couplings must use integer indices
    assert len(jwf.off_diagonal_couplings) >= 2
    for entry in jwf.off_diagonal_couplings:
        assert isinstance(entry, OffDiagonalEntry)
        assert isinstance(entry.row, int)
        assert isinstance(entry.col, int)
        assert isinstance(entry.amplitude, complex)
        assert entry.row != entry.col


def test_off_diagonal_couplings_are_hermitian_paired() -> None:
    """OffDiagonalEntry docstring requires explicit Hermitian pairs:
    both (row, col, a) AND (col, row, conj(a)) must be present."""
    program = CompiledBeliefProgram(raw=_FIXTURE_PROGRAM)
    result = belief_program_to_console(program)
    jwf = result.omytea_joint_wavefunction
    assert jwf is not None

    by_pos: dict[tuple[int, int], complex] = {}
    for e in jwf.off_diagonal_couplings:
        by_pos[(e.row, e.col)] = e.amplitude

    for (row, col), amp in list(by_pos.items()):
        pair_key = (col, row)
        assert pair_key in by_pos, (
            f"Missing Hermitian pair for ({row}, {col}); "
            f"expected ({col}, {row}) but it's not in off_diagonal_couplings."
        )
        # amp at (col, row) should be conj of amp at (row, col)
        assert by_pos[pair_key] == amp.conjugate(), (
            f"Hermitian violation: {pair_key} amplitude is {by_pos[pair_key]} "
            f"but conjugate of ({row}, {col})={amp} is {amp.conjugate()}"
        )


def test_skips_invalid_off_diagonal_labels() -> None:
    """If LLM returns coherence between branch labels that don't exist
    in branches, honest-skip rather than crash."""
    bad_program = {
        **_FIXTURE_PROGRAM,
        "joint_offdiag": [
            {
                "branch_a": "nonexistent_branch_xyz",
                "branch_b": "burnout_within_3mo",
                "coherence_strength": 0.5,
                "rationale": "Invalid",
            },
            {
                "branch_a": "thrive_at_new_role",
                "branch_b": "burnout_within_3mo",
                "coherence_strength": -0.3,
                "rationale": "Valid",
            },
        ],
    }
    program = CompiledBeliefProgram(raw=bad_program)
    result = belief_program_to_console(program)
    assert result.used_omytea_substrate is True
    jwf = result.omytea_joint_wavefunction
    assert jwf is not None
    # 1 valid coherence → 2 Hermitian-paired entries
    assert len(jwf.off_diagonal_couplings) == 2
