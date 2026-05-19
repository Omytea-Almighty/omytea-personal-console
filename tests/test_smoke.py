"""Smoke tests — verify the MVP doesn't crash in mock mode.

Run: pytest tests/

No Anthropic API key required; sets OMYTEA_CONSOLE_MOCK=1 in all tests.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest


# Add parent dir to path so we can import the app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage  # noqa: E402
from compiler import compile_belief_program, CompiledBeliefProgram  # noqa: E402
from console import (  # noqa: E402
    ConsoleHypothesis,
    availability_status,
    belief_program_to_console,
    compute_calibration_delta,
)
from scenarios.career_decision import (  # noqa: E402
    INPUT_FIELDS as CAREER_DECISION_FIELDS,
    SCENARIO_NAME as CAREER_DECISION_NAME,
    validate_input,
)


@pytest.fixture(autouse=True)
def _force_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke tests always run offline, independent of collection order."""
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")


def test_mock_mode_active() -> None:
    """Tests must run in mock mode (no API key required)."""
    assert os.environ.get("OMYTEA_CONSOLE_MOCK") == "1"
    status = availability_status()
    assert status["mock_mode"] is True


def test_compiler_mock_returns_valid_belief_program() -> None:
    """compile_belief_program in mock mode → valid JSON with required fields."""
    form_data = {
        "current_role": "Senior eng at startup X",
        "decision_options": "- Accept B\n- Stay",
        "why_considering_change": "Burnout",
        "time_horizon": "6 months",
        "user_id": "test_user_1",
    }
    program = compile_belief_program(form_data, scenario="career_decision")
    assert isinstance(program, CompiledBeliefProgram)
    assert program.scenario == "career_decision"
    assert len(program.branches) >= 3
    assert len(program.decision_options) >= 2

    # Probabilities sum to ~1
    probs = [float(b["probability_prior"]) for b in program.branches]
    assert 0.99 < sum(probs) < 1.01


def test_compiler_mock_has_offdiagonals() -> None:
    """Mock BeliefProgram should populate at least 1 off-diagonal pair."""
    program = compile_belief_program(
        {"current_role": "x", "decision_options": "x", "why_considering_change": "x",
         "time_horizon": "6 months", "user_id": "u"},
        scenario="career_decision",
    )
    assert len(program.joint_offdiag) >= 1


def test_console_conversion_pure_dict_mode() -> None:
    """belief_program_to_console should always succeed via the pure-dict path
    (regardless of whether Omytea is importable)."""
    program = compile_belief_program(
        {"current_role": "x", "decision_options": "x", "why_considering_change": "x",
         "time_horizon": "6 months", "user_id": "u"},
        scenario="career_decision",
    )
    result = belief_program_to_console(program)
    assert result.scenario == "career_decision"
    assert len(result.hypotheses) >= 3
    assert all(isinstance(h, ConsoleHypothesis) for h in result.hypotheses)


def test_calibration_delta_brier_zero_for_perfect_prediction() -> None:
    """If predicted probabilities exactly match outcome, Brier = 0."""
    branches = [
        ConsoleHypothesis(
            label="a", narrative="", probability=1.0,
            key_uncertainty_driver="", depends_on_decision=None,
        ),
        ConsoleHypothesis(
            label="b", narrative="", probability=0.0,
            key_uncertainty_driver="", depends_on_decision=None,
        ),
    ]
    cal = compute_calibration_delta(branches, {"a": 1.0, "b": 0.0})
    assert cal["brier"] == pytest.approx(0.0, abs=1e-9)


def test_calibration_delta_brier_max_for_worst_prediction() -> None:
    """If predicted all on wrong branch, Brier should be maximum."""
    branches = [
        ConsoleHypothesis(
            label="a", narrative="", probability=1.0,
            key_uncertainty_driver="", depends_on_decision=None,
        ),
        ConsoleHypothesis(
            label="b", narrative="", probability=0.0,
            key_uncertainty_driver="", depends_on_decision=None,
        ),
    ]
    cal = compute_calibration_delta(branches, {"a": 0.0, "b": 1.0})
    # (1-0)^2 + (0-1)^2 = 2 for binary case
    assert cal["brier"] == pytest.approx(2.0, abs=1e-6)


def test_storage_roundtrip_prediction() -> None:
    """save_prediction → list_user_predictions returns the same record."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"

        rec = storage.PredictionRecord(
            prediction_id=storage.new_prediction_id(),
            user_id="test_user_xyz",
            scenario="career_decision",
            created_at=storage.now_unix(),
            user_input={"current_role": "test"},
            belief_program={"scenario": "career_decision", "branches": []},
            wavefunction_snapshot={"hypotheses": []},
            joint_offdiag={"entries": []},
        )
        storage.save_prediction(rec, db_path=db)

        out = storage.list_user_predictions("test_user_xyz", db_path=db)
        assert len(out) == 1
        assert out[0].prediction_id == rec.prediction_id
        assert out[0].user_input == {"current_role": "test"}


def test_storage_calibration_aggregate_empty() -> None:
    """get_calibration_aggregate returns empty dict when no data."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        agg = storage.get_calibration_aggregate(db_path=db)
        assert agg == {}


def test_validate_input_catches_missing_required() -> None:
    """validate_input should reject when required fields are empty."""
    is_valid, err = validate_input(
        {"current_role": "", "decision_options": "x", "user_id": "u",
         "why_considering_change": "x", "time_horizon": "6 months"}
    )
    assert is_valid is False
    assert "Missing required field" in err


def test_validate_input_passes_when_all_required_present() -> None:
    is_valid, err = validate_input(
        {"current_role": "x", "decision_options": "x", "user_id": "u",
         "why_considering_change": "x", "time_horizon": "6 months"}
    )
    assert is_valid is True
    assert err == ""


def test_scenario_manifest_has_required_fields() -> None:
    """Career decision scenario manifest must include at least the
    minimum required fields: user_id, time_horizon, decision_options."""
    field_keys = {f.key for f in CAREER_DECISION_FIELDS}
    required_subset = {"current_role", "decision_options", "user_id", "time_horizon"}
    assert required_subset.issubset(field_keys)
