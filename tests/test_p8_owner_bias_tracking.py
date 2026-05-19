"""v4.16 P8 — founder-as-user bias tracking on calibration aggregates.

These tests verify the new storage schema column + bias-filtered
calibration aggregate functions added per H4 data point #1's
self-reported ownership-bias caveat. Pure SQLite tests; no Streamlit,
no Omytea dependency.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage  # noqa: E402


@pytest.fixture
def tmp_db() -> Path:
    """Per-test isolated SQLite DB path."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test.db"


def _make_prediction(
    user_id: str = "u1",
    is_owner_bias_flagged: bool = False,
    prediction_id: str | None = None,
) -> storage.PredictionRecord:
    return storage.PredictionRecord(
        prediction_id=prediction_id or storage.new_prediction_id(),
        user_id=user_id,
        scenario="career_decision",
        created_at=storage.now_unix(),
        user_input={"role": "x"},
        belief_program={"branches": []},
        wavefunction_snapshot={"hypotheses": []},
        joint_offdiag={"entries": []},
        is_owner_bias_flagged=is_owner_bias_flagged,
    )


def _make_measurement(
    prediction_id: str,
    user_id: str = "u1",
    brier: float = 0.25,
    log_loss: float = 1.4,
) -> storage.MeasurementUpdate:
    return storage.MeasurementUpdate(
        update_id=storage.new_update_id(),
        prediction_id=prediction_id,
        user_id=user_id,
        observed_at=storage.now_unix(),
        actual_outcome={"branch_a": 1.0},
        calibration_delta={"brier": brier, "log_loss": log_loss},
        user_satisfaction=5,
    )


# ----- Schema / default field -----


def test_prediction_record_default_owner_bias_false() -> None:
    rec = _make_prediction()
    assert rec.is_owner_bias_flagged is False


def test_prediction_record_owner_bias_can_be_true() -> None:
    rec = _make_prediction(is_owner_bias_flagged=True)
    assert rec.is_owner_bias_flagged is True


def test_schema_includes_owner_bias_column(tmp_db: Path) -> None:
    """After connect, predictions table must have the new column."""
    with storage.db_connect(tmp_db) as conn:
        assert storage._column_exists(
            conn, "predictions", "is_owner_bias_flagged",
        )


def test_schema_version_at_least_2(tmp_db: Path) -> None:
    """PRAGMA user_version reflects at least the P8 migration. Future
    migrations (P2 drilldown cache etc.) may push it higher; the
    constraint here is 'P8 column exists at or after v2'."""
    with storage.db_connect(tmp_db) as conn:
        row = conn.execute("PRAGMA user_version").fetchone()
    assert row[0] >= 2


# ----- Migration from v1 DB -----


def test_schema_migrates_existing_v1_db_idempotently(tmp_db: Path) -> None:
    """If a DB was created at SCHEMA_VERSION=1 (without the column),
    reopening it should ALTER TABLE and add the column without losing
    existing rows."""
    # Manually create the legacy v1 schema (no is_owner_bias_flagged).
    import sqlite3
    p = tmp_db
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE predictions (
            prediction_id        TEXT PRIMARY KEY,
            user_id              TEXT NOT NULL,
            scenario             TEXT NOT NULL,
            created_at           REAL NOT NULL,
            user_input_json      TEXT NOT NULL,
            belief_program_json  TEXT NOT NULL,
            wavefunction_json    TEXT NOT NULL,
            joint_offdiag_json   TEXT NOT NULL,
            notes                TEXT DEFAULT ''
        )
        """
    )
    cur.execute(
        "INSERT INTO predictions VALUES "
        "('p1','u1','x',1.0,'{}','{}','{}','{}','')"
    )
    cur.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()

    # Reopen via storage.db_connect — should migrate.
    with storage.db_connect(tmp_db) as conn:
        assert storage._column_exists(
            conn, "predictions", "is_owner_bias_flagged",
        )
        # Legacy row preserved
        row = conn.execute(
            "SELECT is_owner_bias_flagged FROM predictions WHERE prediction_id='p1'"
        ).fetchone()
        assert row[0] == 0  # default 0 after ALTER


# ----- Round-trip save / list -----


def test_save_and_list_preserves_owner_bias_false(tmp_db: Path) -> None:
    rec = _make_prediction(is_owner_bias_flagged=False, prediction_id="p_a")
    storage.save_prediction(rec, db_path=tmp_db)
    got = storage.list_user_predictions("u1", db_path=tmp_db)
    assert len(got) == 1
    assert got[0].is_owner_bias_flagged is False


def test_save_and_list_preserves_owner_bias_true(tmp_db: Path) -> None:
    rec = _make_prediction(is_owner_bias_flagged=True, prediction_id="p_b")
    storage.save_prediction(rec, db_path=tmp_db)
    got = storage.list_user_predictions("u1", db_path=tmp_db)
    assert len(got) == 1
    assert got[0].is_owner_bias_flagged is True


# ----- bias_filter validation -----


def test_invalid_bias_filter_raises(tmp_db: Path) -> None:
    with pytest.raises(ValueError, match="bias_filter must be"):
        storage.get_calibration_aggregate(
            db_path=tmp_db, bias_filter="invalid_value",
        )


def test_valid_bias_filters_accepted(tmp_db: Path) -> None:
    for f in ("all", "exclude_owner", "owner_only"):
        # Should not raise even when DB is empty.
        out = storage.get_calibration_aggregate(db_path=tmp_db, bias_filter=f)
        assert out == {}


# ----- get_calibration_aggregate with bias_filter -----


def _seed_two_predictions_one_each(tmp_db: Path) -> None:
    """Owner-flagged prediction p_owner (brier=0.10) + neutral prediction
    p_user (brier=0.40)."""
    storage.save_prediction(
        _make_prediction(
            user_id="founder", is_owner_bias_flagged=True,
            prediction_id="p_owner",
        ),
        db_path=tmp_db,
    )
    storage.save_prediction(
        _make_prediction(
            user_id="real_user", is_owner_bias_flagged=False,
            prediction_id="p_user",
        ),
        db_path=tmp_db,
    )
    storage.save_measurement(
        _make_measurement(
            prediction_id="p_owner", user_id="founder", brier=0.10,
        ),
        db_path=tmp_db,
    )
    storage.save_measurement(
        _make_measurement(
            prediction_id="p_user", user_id="real_user", brier=0.40,
        ),
        db_path=tmp_db,
    )


def test_aggregate_all_includes_both(tmp_db: Path) -> None:
    _seed_two_predictions_one_each(tmp_db)
    agg = storage.get_calibration_aggregate(db_path=tmp_db, bias_filter="all")
    assert agg["n_measurements"] == 2.0
    assert agg["mean_brier"] == pytest.approx(0.25)


def test_aggregate_exclude_owner_drops_owner_data(tmp_db: Path) -> None:
    _seed_two_predictions_one_each(tmp_db)
    agg = storage.get_calibration_aggregate(
        db_path=tmp_db, bias_filter="exclude_owner",
    )
    assert agg["n_measurements"] == 1.0
    assert agg["mean_brier"] == pytest.approx(0.40)


def test_aggregate_owner_only_keeps_only_owner_data(tmp_db: Path) -> None:
    _seed_two_predictions_one_each(tmp_db)
    agg = storage.get_calibration_aggregate(
        db_path=tmp_db, bias_filter="owner_only",
    )
    assert agg["n_measurements"] == 1.0
    assert agg["mean_brier"] == pytest.approx(0.10)


def test_aggregate_per_user_respects_bias_filter(tmp_db: Path) -> None:
    """user_id filter + bias filter compose correctly."""
    _seed_two_predictions_one_each(tmp_db)
    # founder + exclude_owner → empty
    agg = storage.get_calibration_aggregate(
        user_id="founder", db_path=tmp_db, bias_filter="exclude_owner",
    )
    assert agg == {}
    # real_user + owner_only → empty
    agg = storage.get_calibration_aggregate(
        user_id="real_user", db_path=tmp_db, bias_filter="owner_only",
    )
    assert agg == {}
    # founder + owner_only → 1 measurement
    agg = storage.get_calibration_aggregate(
        user_id="founder", db_path=tmp_db, bias_filter="owner_only",
    )
    assert agg["n_measurements"] == 1.0


# ----- get_calibration_bias_breakdown -----


def test_breakdown_returns_three_buckets(tmp_db: Path) -> None:
    _seed_two_predictions_one_each(tmp_db)
    out = storage.get_calibration_bias_breakdown(db_path=tmp_db)
    assert set(out.keys()) == {"all", "exclude_owner", "owner_only"}
    assert out["all"]["n_measurements"] == 2.0
    assert out["exclude_owner"]["n_measurements"] == 1.0
    assert out["owner_only"]["n_measurements"] == 1.0


def test_breakdown_empty_when_no_measurements(tmp_db: Path) -> None:
    out = storage.get_calibration_bias_breakdown(db_path=tmp_db)
    assert out == {"all": {}, "exclude_owner": {}, "owner_only": {}}


def test_breakdown_brier_deltas_visible(tmp_db: Path) -> None:
    """The headline use case: founder scored 0.10, real user 0.40 →
    exclude_owner Brier 0.40, owner_only Brier 0.10, gap = +0.30
    interpretable as ownership bias."""
    _seed_two_predictions_one_each(tmp_db)
    out = storage.get_calibration_bias_breakdown(db_path=tmp_db)
    assert out["owner_only"]["mean_brier"] == pytest.approx(0.10)
    assert out["exclude_owner"]["mean_brier"] == pytest.approx(0.40)
    gap = (out["owner_only"]["mean_brier"]
           - out["exclude_owner"]["mean_brier"])
    assert gap == pytest.approx(-0.30)


# ----- Backwards compatibility -----


def test_aggregate_default_bias_filter_is_all(tmp_db: Path) -> None:
    """Callers that don't pass bias_filter must see legacy behavior."""
    _seed_two_predictions_one_each(tmp_db)
    legacy_call = storage.get_calibration_aggregate(db_path=tmp_db)
    explicit_all = storage.get_calibration_aggregate(
        db_path=tmp_db, bias_filter="all",
    )
    assert legacy_call == explicit_all
