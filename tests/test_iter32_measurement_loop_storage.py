"""Iter #35 — regression tests for the measurement-loop storage helpers.

Two functions are now load-bearing for the measurement-loop UI:

  - ``list_recent_measurements_with_predictions`` (iter 32) — backs
    the per-prediction diff cards on Calibration History.
  - ``list_overdue_predictions`` (iter 34) — backs the active
    "Time to score" landing banner.

A silent regression in either would surface as missing cards / missing
banner with no test failure. These tests pin the contract: return
type, key set, ordering, edge cases.

Each test creates a temporary SQLite DB (per-test tmp_path) and
populates fixture predictions + measurements via the real
``save_prediction`` / ``save_measurement`` paths so the JSON round-trip
that happens in production is exercised — not just the helper in
isolation.
"""

from __future__ import annotations

import time as _time
from pathlib import Path

import storage


def _make_prediction(
    *,
    prediction_id: str,
    user_id: str,
    decision: str = "Take the offer",
    horizon: str = "3 months",
    top_branch_label: str = "thrive_at_new_role",
    top_branch_prob: float = 0.26,
    created_at: float | None = None,
) -> storage.PredictionRecord:
    """Build a PredictionRecord with the JSON shapes the helpers
    parse from. Wavefunction has two hypotheses so we exercise the
    top-prob selection branch in list_recent_measurements_*."""
    return storage.PredictionRecord(
        prediction_id=prediction_id,
        user_id=user_id,
        scenario="career_decision",
        created_at=(created_at if created_at is not None else _time.time()),
        user_input={
            "decision_options": decision,
            "time_horizon": horizon,
        },
        belief_program={},
        wavefunction_snapshot={
            "hypotheses": [
                {
                    "label": top_branch_label,
                    "probability": top_branch_prob,
                    "branch_type": "realistic",
                },
                {
                    "label": "burnout_within_3mo",
                    "probability": 0.10,
                    "branch_type": "worst",
                },
            ],
        },
        joint_offdiag={},
        notes="",
        is_owner_bias_flagged=False,
        category_id=None,
    )


def _make_measurement(
    *,
    prediction_id: str,
    user_id: str,
    actual_branch: str = "thrive_at_new_role",
    brier: float = 0.18,
    log_loss: float = 0.42,
) -> storage.MeasurementUpdate:
    """Build a MeasurementUpdate with the JSON shapes
    list_recent_measurements_* extracts from."""
    return storage.MeasurementUpdate(
        update_id=storage.new_update_id(),
        prediction_id=prediction_id,
        user_id=user_id,
        observed_at=_time.time(),
        actual_outcome={"outcome_branch_label": actual_branch},
        calibration_delta={"brier": brier, "log_loss": log_loss},
    )


def test_list_overdue_predictions_skips_not_yet_due(tmp_path: Path) -> None:
    """A prediction created NOW with a 3-month horizon is NOT
    overdue — the helper must not surface it."""
    db = tmp_path / "test.db"
    pid = "pred-fresh"
    storage.save_prediction(
        _make_prediction(
            prediction_id=pid,
            user_id="u1",
            horizon="3 months",
            created_at=_time.time(),  # right now
        ),
        db_path=db,
    )
    result = storage.list_overdue_predictions("u1", db_path=db)
    # No item should be overdue.
    assert all(r["prediction_id"] != pid for r in result), (
        "Fresh prediction must not appear in overdue list"
    )


def test_list_overdue_predictions_surfaces_past_horizon(
    tmp_path: Path,
) -> None:
    """A prediction created 100 days ago with a 3-month horizon
    IS overdue and must surface."""
    db = tmp_path / "test.db"
    pid = "pred-overdue"
    storage.save_prediction(
        _make_prediction(
            prediction_id=pid,
            user_id="u1",
            decision="Long-overdue decision",
            horizon="3 months",
            created_at=_time.time() - (100 * 86400),  # 100 days ago
        ),
        db_path=db,
    )
    result = storage.list_overdue_predictions("u1", db_path=db)
    matched = [r for r in result if r["prediction_id"] == pid]
    assert len(matched) == 1
    rec = matched[0]
    # Contract: required keys
    for key in (
        "prediction_id",
        "user_id",
        "scenario",
        "predicted_at",
        "due_at",
        "horizon_label",
        "decision_label",
    ):
        assert key in rec, f"Missing key in overdue record: {key}"
    assert rec["decision_label"] == "Long-overdue decision"
    # due_at is in the past (overdue).
    assert rec["due_at"] < _time.time()


def test_list_overdue_predictions_excludes_already_scored(
    tmp_path: Path,
) -> None:
    """A prediction that's overdue BUT already has a measurement_update
    must NOT appear — that's the LEFT JOIN ⊥ filter."""
    db = tmp_path / "test.db"
    pid = "pred-overdue-scored"
    storage.save_prediction(
        _make_prediction(
            prediction_id=pid,
            user_id="u1",
            horizon="3 months",
            created_at=_time.time() - (100 * 86400),
        ),
        db_path=db,
    )
    storage.save_measurement(
        _make_measurement(prediction_id=pid, user_id="u1"),
        db_path=db,
    )
    result = storage.list_overdue_predictions("u1", db_path=db)
    assert all(r["prediction_id"] != pid for r in result), (
        "Already-scored prediction must not appear as overdue"
    )


def test_list_overdue_predictions_returns_newest_first(
    tmp_path: Path,
) -> None:
    """When multiple predictions are overdue, most-recent-due
    comes first so the banner shows the freshest."""
    db = tmp_path / "test.db"
    now = _time.time()
    storage.save_prediction(
        _make_prediction(
            prediction_id="older",
            user_id="u1",
            horizon="3 months",
            created_at=now - (200 * 86400),  # 200 days ago
        ),
        db_path=db,
    )
    storage.save_prediction(
        _make_prediction(
            prediction_id="newer",
            user_id="u1",
            horizon="3 months",
            created_at=now - (100 * 86400),  # 100 days ago
        ),
        db_path=db,
    )
    result = storage.list_overdue_predictions("u1", db_path=db)
    pids = [r["prediction_id"] for r in result]
    # newer's due_at should be more recent than older's, so newer is first.
    assert pids.index("newer") < pids.index("older")


def test_list_overdue_predictions_parses_horizon_units(
    tmp_path: Path,
) -> None:
    """The horizon parser must handle months / weeks / days / years
    and fall back to 3 months on unparseable input."""
    db = tmp_path / "test.db"
    now = _time.time()
    # 1 week ago + 1 week horizon → due TODAY (overdue boundary).
    # Use 10 days ago to make it clearly overdue.
    storage.save_prediction(
        _make_prediction(
            prediction_id="weeks",
            user_id="u1",
            horizon="1 week",
            created_at=now - (10 * 86400),
        ),
        db_path=db,
    )
    # 100 days ago + 6 months horizon = NOT overdue (180 days needed).
    storage.save_prediction(
        _make_prediction(
            prediction_id="six_months",
            user_id="u1",
            horizon="6 months",
            created_at=now - (100 * 86400),
        ),
        db_path=db,
    )
    # Unparseable horizon → defaults to 3 months. 100 days ago = overdue.
    storage.save_prediction(
        _make_prediction(
            prediction_id="bad_horizon",
            user_id="u1",
            horizon="immediately!",
            created_at=now - (100 * 86400),
        ),
        db_path=db,
    )
    result = storage.list_overdue_predictions("u1", db_path=db)
    pids = {r["prediction_id"] for r in result}
    assert "weeks" in pids, "1-week horizon should be overdue at 10 days"
    assert "bad_horizon" in pids, (
        "Unparseable horizon should default to 3 months → overdue at 100 days"
    )
    assert "six_months" not in pids, (
        "6-month horizon should NOT be overdue at 100 days"
    )


def test_list_recent_measurements_with_predictions_returns_expected_keys(
    tmp_path: Path,
) -> None:
    """The diff-card helper must return a list of dicts with the
    full key set the Calibration History page reads from."""
    db = tmp_path / "test.db"
    pid = "pred-A"
    storage.save_prediction(
        _make_prediction(
            prediction_id=pid,
            user_id="u1",
            decision="Take the offer",
            top_branch_label="thrive_at_new_role",
            top_branch_prob=0.40,
        ),
        db_path=db,
    )
    storage.save_measurement(
        _make_measurement(
            prediction_id=pid,
            user_id="u1",
            actual_branch="thrive_at_new_role",
            brier=0.15,
            log_loss=0.30,
        ),
        db_path=db,
    )
    result = storage.list_recent_measurements_with_predictions(
        user_id="u1", db_path=db,
    )
    assert len(result) == 1
    rec = result[0]
    # Required key set
    for key in (
        "prediction_id",
        "user_id",
        "predicted_at",
        "observed_at",
        "scenario",
        "decision_label",
        "predicted_top_label",
        "predicted_top_prob",
        "actual_outcome",
        "actual_label",
        "prob_for_actual",
        "brier",
        "log_loss",
    ):
        assert key in rec, f"Missing key: {key}"


def test_list_recent_measurements_with_predictions_computes_prob_for_actual(
    tmp_path: Path,
) -> None:
    """The single most decision-relevant field — `prob_for_actual` —
    must equal the probability the user assigned at prediction time
    to the branch that actually happened. This is the calibration
    truth-moment per record."""
    db = tmp_path / "test.db"
    pid = "pred-truth"
    # Top branch is "thrive" at 40%, but the worst case "burnout" at
    # 10% is what actually materialized.
    storage.save_prediction(
        _make_prediction(
            prediction_id=pid,
            user_id="u1",
            top_branch_label="thrive_at_new_role",
            top_branch_prob=0.40,
        ),
        db_path=db,
    )
    storage.save_measurement(
        _make_measurement(
            prediction_id=pid,
            user_id="u1",
            actual_branch="burnout_within_3mo",  # the worst case branch
            brier=0.60,  # bad calibration
        ),
        db_path=db,
    )
    result = storage.list_recent_measurements_with_predictions(
        user_id="u1", db_path=db,
    )
    rec = result[0]
    assert rec["predicted_top_label"] == "thrive_at_new_role"
    assert abs(rec["predicted_top_prob"] - 0.40) < 1e-6
    assert rec["actual_label"] == "burnout_within_3mo"
    # The "you gave it X% in advance" number — the user gave the
    # actually-happened branch only 10% in advance.
    assert abs(rec["prob_for_actual"] - 0.10) < 1e-6


def test_list_recent_measurements_with_predictions_ordering(
    tmp_path: Path,
) -> None:
    """Records sort by observed_at DESC so the freshest measurement
    is first — what the diff-card UI expects."""
    db = tmp_path / "test.db"
    storage.save_prediction(
        _make_prediction(prediction_id="p1", user_id="u1"),
        db_path=db,
    )
    storage.save_prediction(
        _make_prediction(prediction_id="p2", user_id="u1"),
        db_path=db,
    )
    # Save older measurement first, then newer.
    older_m = _make_measurement(prediction_id="p1", user_id="u1")
    older_m = storage.MeasurementUpdate(
        update_id=older_m.update_id,
        prediction_id=older_m.prediction_id,
        user_id=older_m.user_id,
        observed_at=_time.time() - 1000,
        actual_outcome=older_m.actual_outcome,
        calibration_delta=older_m.calibration_delta,
    )
    storage.save_measurement(older_m, db_path=db)
    storage.save_measurement(
        _make_measurement(prediction_id="p2", user_id="u1"),
        db_path=db,
    )
    result = storage.list_recent_measurements_with_predictions(
        user_id="u1", db_path=db,
    )
    assert len(result) == 2
    # Newer (p2) should come first
    assert result[0]["prediction_id"] == "p2"
    assert result[1]["prediction_id"] == "p1"


def test_list_recent_measurements_returns_empty_for_unknown_user(
    tmp_path: Path,
) -> None:
    """A user with no measurements yields an empty list — not a
    raised exception. The UI relies on this to render the empty
    state cleanly."""
    db = tmp_path / "test.db"
    result = storage.list_recent_measurements_with_predictions(
        user_id="never-existed", db_path=db,
    )
    assert result == []
