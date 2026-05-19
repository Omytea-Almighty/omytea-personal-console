"""v4.16 P5 — sensitivity → ΔP (Option C) semantics tests.

Verifies:
- `normalize_evidence_record` reads both legacy (sensitivity 0-1) and
  modern (expected_delta_p in pp) schemas.
- `normalize_evidence_list` sorts descending by ΔP.
- `format_delta_p` renders the canonical "±N pp" surface form.
- Backward compat: predictions stored under the legacy schema still
  display correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from console import (  # noqa: E402
    format_delta_p,
    normalize_evidence_list,
    normalize_evidence_record,
)


# ----- normalize_evidence_record -----


def test_modern_schema_passes_through() -> None:
    """expected_delta_p already in pp → unchanged."""
    raw = {
        "evidence_label": "diagnostic_call",
        "expected_delta_p": 18.0,
        "target_branch": "thrive_at_new_role",
        "rationale": "A 45-min call exposes management style.",
    }
    out = normalize_evidence_record(raw)
    assert out["evidence_label"] == "diagnostic_call"
    assert out["expected_delta_p"] == 18.0
    assert out["target_branch"] == "thrive_at_new_role"
    assert "management style" in out["rationale"]


def test_legacy_sensitivity_converts_to_pp() -> None:
    """Legacy 0-1 sensitivity → multiplied by 100 to get pp."""
    raw = {
        "evidence_label": "old_record",
        "sensitivity": 0.70,
    }
    out = normalize_evidence_record(raw)
    assert out["expected_delta_p"] == pytest.approx(70.0)
    # Legacy records have no target_branch or rationale; defaults apply.
    assert out["target_branch"] is None
    assert out["rationale"] == ""


def test_modern_field_wins_over_legacy_when_both_present() -> None:
    """If both schemas are present (transition period), the modern
    field is the canonical value."""
    raw = {
        "evidence_label": "x",
        "expected_delta_p": 22.0,
        "sensitivity": 0.50,  # contradicts new field; should be ignored
    }
    out = normalize_evidence_record(raw)
    assert out["expected_delta_p"] == 22.0


def test_missing_both_fields_yields_zero() -> None:
    """Empty / malformed record → ΔP defaults to 0 (renders cleanly)."""
    raw = {"evidence_label": "no_metric"}
    out = normalize_evidence_record(raw)
    assert out["expected_delta_p"] == 0.0


def test_null_expected_delta_p_falls_back_to_legacy() -> None:
    """expected_delta_p=None → legacy path is taken (LLM may emit nulls)."""
    raw = {
        "evidence_label": "x",
        "expected_delta_p": None,
        "sensitivity": 0.30,
    }
    out = normalize_evidence_record(raw)
    assert out["expected_delta_p"] == pytest.approx(30.0)


def test_delta_p_clamped_to_upper_bound() -> None:
    raw = {"evidence_label": "x", "expected_delta_p": 250.0}
    out = normalize_evidence_record(raw)
    assert out["expected_delta_p"] == 100.0


def test_delta_p_clamped_to_lower_bound() -> None:
    raw = {"evidence_label": "x", "expected_delta_p": -5.0}
    out = normalize_evidence_record(raw)
    assert out["expected_delta_p"] == 0.0


def test_legacy_sensitivity_clamped_to_upper_bound() -> None:
    """An out-of-range legacy sensitivity (>1) shouldn't render >100 pp."""
    raw = {"evidence_label": "x", "sensitivity": 1.5}
    out = normalize_evidence_record(raw)
    assert out["expected_delta_p"] == 100.0


def test_evidence_label_coerces_to_string() -> None:
    """Defensive: even if label arrives as None / int, output is a str."""
    raw = {"evidence_label": 42, "expected_delta_p": 10.0}
    out = normalize_evidence_record(raw)
    assert isinstance(out["evidence_label"], str)
    assert out["evidence_label"] == "42"


def test_target_branch_none_stays_none() -> None:
    raw = {"evidence_label": "x", "expected_delta_p": 10.0,
           "target_branch": None}
    out = normalize_evidence_record(raw)
    assert out["target_branch"] is None


def test_target_branch_coerces_to_string() -> None:
    raw = {"evidence_label": "x", "expected_delta_p": 10.0,
           "target_branch": "thrive_at_new_role"}
    out = normalize_evidence_record(raw)
    assert out["target_branch"] == "thrive_at_new_role"


def test_extra_fields_dropped() -> None:
    """Unknown fields must NOT leak into the normalized record — keeps
    downstream UI / storage schema clean."""
    raw = {
        "evidence_label": "x",
        "expected_delta_p": 10.0,
        "unknown_extra_field": "should_be_dropped",
    }
    out = normalize_evidence_record(raw)
    assert "unknown_extra_field" not in out
    # Output is exactly the canonical four keys.
    assert set(out.keys()) == {
        "evidence_label", "expected_delta_p",
        "target_branch", "rationale",
    }


# ----- normalize_evidence_list -----


def test_list_normalizes_each_and_sorts_desc() -> None:
    raw = [
        {"evidence_label": "low", "expected_delta_p": 5.0},
        {"evidence_label": "high", "expected_delta_p": 25.0},
        {"evidence_label": "mid", "sensitivity": 0.15},  # → 15 pp
    ]
    out = normalize_evidence_list(raw)
    labels = [r["evidence_label"] for r in out]
    assert labels == ["high", "mid", "low"]


def test_list_handles_empty() -> None:
    assert normalize_evidence_list([]) == []


def test_list_handles_all_zero_delta_p() -> None:
    """Ordering should be stable-ish even when all ΔP are zero."""
    raw = [
        {"evidence_label": "a"},
        {"evidence_label": "b"},
    ]
    out = normalize_evidence_list(raw)
    assert len(out) == 2
    assert all(r["expected_delta_p"] == 0.0 for r in out)


# ----- format_delta_p -----


def test_format_delta_p_renders_pp_form() -> None:
    assert format_delta_p(18.0) == "±18 pp"
    assert format_delta_p(0.0) == "±0 pp"
    assert format_delta_p(100.0) == "±100 pp"


def test_format_delta_p_rounds_half_to_nearest() -> None:
    """Banker's rounding via Python's round(); 12.5 → 12, 13.5 → 14."""
    # We just verify it produces an integer with no fractional digits.
    s = format_delta_p(12.49)
    assert "12 pp" in s
    s = format_delta_p(12.51)
    assert "13 pp" in s


def test_format_delta_p_handles_small_values() -> None:
    assert format_delta_p(0.3) == "±0 pp"  # rounds down
    assert format_delta_p(0.7) == "±1 pp"  # rounds up


# ----- Integration: compiler mock + console normalizer -----


def test_compiler_mock_emits_new_schema() -> None:
    """Mock compile output already carries expected_delta_p — confirms
    the v4.16 P5 schema migration landed end-to-end in mock mode."""
    from compiler import _mock_compile

    program = _mock_compile({}, scenario="career_decision")
    for record in program["recommended_evidence"]:
        assert "expected_delta_p" in record
        # Records were updated; legacy sensitivity field is gone.
        assert "sensitivity" not in record
        # Each record carries a rationale + target_branch.
        assert "rationale" in record
        assert "target_branch" in record


def test_mock_backend_emits_new_schema() -> None:
    """The MockBackend canned response should also carry the new schema
    (this is what RotatingBackend + mock fallback returns at runtime)."""
    from llm_backends.mock_backend import _MOCK_BELIEF_PROGRAM

    for record in _MOCK_BELIEF_PROGRAM["recommended_evidence"]:
        assert "expected_delta_p" in record
        assert "sensitivity" not in record
        assert "rationale" in record


def test_legacy_stored_prediction_still_renders() -> None:
    """A prediction stored before v4.16 P5 used the sensitivity schema.
    Going through normalize_evidence_list must keep it usable."""
    legacy_evidence = [
        {"evidence_label": "old_call", "sensitivity": 0.7},
        {"evidence_label": "old_review", "sensitivity": 0.3},
    ]
    out = normalize_evidence_list(legacy_evidence)
    assert out[0]["expected_delta_p"] == pytest.approx(70.0)
    assert out[1]["expected_delta_p"] == pytest.approx(30.0)
    # And format_delta_p turns each into a renderable pp string.
    assert format_delta_p(out[0]["expected_delta_p"]) == "±70 pp"
