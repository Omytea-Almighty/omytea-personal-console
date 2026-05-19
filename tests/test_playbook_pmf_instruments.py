"""v4.16 playbook-adopt — Sean Ellis test + effort test PMF instruments.

Adapted from the Anthropic founder's playbook (2026-05-14) §4 (MVP).
Tests cover:
- Schema v4 → v5 migration (idempotent ADD COLUMN)
- MeasurementUpdate dataclass new fields
- Save / read round-trip with new fields
- get_sean_ellis_summary: counts, percentages, threshold flag,
  per-user filter, bias filter, missing-data exclusion
- get_effort_test_summary: same axes
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage  # noqa: E402


@pytest.fixture
def tmp_db() -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test.db"


def _seed_prediction(
    tmp_db: Path,
    prediction_id: str = "p1",
    user_id: str = "u1",
    is_owner_bias_flagged: bool = False,
) -> None:
    rec = storage.PredictionRecord(
        prediction_id=prediction_id,
        user_id=user_id,
        scenario="career_decision",
        created_at=storage.now_unix(),
        user_input={},
        belief_program={},
        wavefunction_snapshot={"hypotheses": []},
        joint_offdiag={"entries": []},
        is_owner_bias_flagged=is_owner_bias_flagged,
    )
    storage.save_prediction(rec, db_path=tmp_db)


def _save_measurement(
    tmp_db: Path,
    prediction_id: str = "p1",
    user_id: str = "u1",
    sean_ellis: str = "",
    effort: str = "",
) -> None:
    upd = storage.MeasurementUpdate(
        update_id=storage.new_update_id(),
        prediction_id=prediction_id,
        user_id=user_id,
        observed_at=storage.now_unix(),
        actual_outcome={},
        calibration_delta={"brier": 0.25},
        user_satisfaction=7,
        sean_ellis_response=sean_ellis,
        effort_test_response=effort,
    )
    storage.save_measurement(upd, db_path=tmp_db)


# ----- Schema migration -----


def test_schema_version_at_least_5(tmp_db: Path) -> None:
    with storage.db_connect(tmp_db) as conn:
        row = conn.execute("PRAGMA user_version").fetchone()
    assert row[0] >= 5


def test_sean_ellis_column_exists(tmp_db: Path) -> None:
    with storage.db_connect(tmp_db) as conn:
        assert storage._column_exists(
            conn, "measurement_updates", "sean_ellis_response",
        )


def test_effort_test_column_exists(tmp_db: Path) -> None:
    with storage.db_connect(tmp_db) as conn:
        assert storage._column_exists(
            conn, "measurement_updates", "effort_test_response",
        )


def test_migration_from_v4_idempotent(tmp_db: Path) -> None:
    """Build a legacy v4 schema (no playbook columns) by hand, then
    reopen via storage.db_connect; the migration should add both
    columns + bump user_version to 5."""
    p = tmp_db
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE measurement_updates (
            update_id            TEXT PRIMARY KEY,
            prediction_id        TEXT NOT NULL,
            user_id              TEXT NOT NULL,
            observed_at          REAL NOT NULL,
            actual_outcome_json  TEXT NOT NULL,
            calibration_json     TEXT NOT NULL,
            user_satisfaction    INTEGER,
            user_notes           TEXT DEFAULT ''
        )
        """
    )
    cur.execute(
        "INSERT INTO measurement_updates VALUES "
        "('u1','p1','user1',1.0,'{}','{}',7,'')"
    )
    cur.execute("PRAGMA user_version = 4")
    conn.commit()
    conn.close()
    # Reopen → migrate.
    with storage.db_connect(tmp_db) as conn:
        assert storage._column_exists(
            conn, "measurement_updates", "sean_ellis_response",
        )
        # Legacy row preserved with empty defaults.
        row = conn.execute(
            "SELECT sean_ellis_response, effort_test_response "
            "FROM measurement_updates WHERE update_id='u1'"
        ).fetchone()
        assert row["sean_ellis_response"] == ""
        assert row["effort_test_response"] == ""


# ----- MeasurementUpdate dataclass -----


def test_measurement_update_default_empty_responses() -> None:
    upd = storage.MeasurementUpdate(
        update_id="u",
        prediction_id="p",
        user_id="user",
        observed_at=1.0,
        actual_outcome={},
        calibration_delta={},
    )
    assert upd.sean_ellis_response == ""
    assert upd.effort_test_response == ""


def test_save_and_read_measurement_persists_new_fields(tmp_db: Path) -> None:
    _seed_prediction(tmp_db)
    _save_measurement(
        tmp_db,
        sean_ellis="very_disappointed",
        effort="self_returned",
    )
    with storage.db_connect(tmp_db) as conn:
        row = conn.execute(
            "SELECT sean_ellis_response, effort_test_response "
            "FROM measurement_updates"
        ).fetchone()
    assert row["sean_ellis_response"] == "very_disappointed"
    assert row["effort_test_response"] == "self_returned"


# ----- get_sean_ellis_summary -----


def test_sean_ellis_summary_empty_when_no_responses(tmp_db: Path) -> None:
    assert storage.get_sean_ellis_summary(db_path=tmp_db) == {}


def test_sean_ellis_summary_excludes_empty_string_responses(
    tmp_db: Path,
) -> None:
    _seed_prediction(tmp_db, prediction_id="p1")
    _save_measurement(tmp_db, prediction_id="p1", sean_ellis="")
    assert storage.get_sean_ellis_summary(db_path=tmp_db) == {}


def test_sean_ellis_summary_counts_each_bucket(tmp_db: Path) -> None:
    _seed_prediction(tmp_db, prediction_id="p1", user_id="u1")
    _seed_prediction(tmp_db, prediction_id="p2", user_id="u2")
    _seed_prediction(tmp_db, prediction_id="p3", user_id="u3")
    _seed_prediction(tmp_db, prediction_id="p4", user_id="u4")
    _seed_prediction(tmp_db, prediction_id="p5", user_id="u5")
    _save_measurement(tmp_db, "p1", "u1", "very_disappointed")
    _save_measurement(tmp_db, "p2", "u2", "very_disappointed")
    _save_measurement(tmp_db, "p3", "u3", "somewhat_disappointed")
    _save_measurement(tmp_db, "p4", "u4", "somewhat_disappointed")
    _save_measurement(tmp_db, "p5", "u5", "not_disappointed")

    s = storage.get_sean_ellis_summary(
        bias_filter="all", db_path=tmp_db,
    )
    assert s["n"] == 5
    assert s["very_disappointed"] == 2
    assert s["somewhat_disappointed"] == 2
    assert s["not_disappointed"] == 1
    assert s["very_disappointed_pct"] == pytest.approx(40.0)
    # 40.0 >= 40.0 boundary inclusive
    assert s["meets_threshold"] is True


def test_sean_ellis_meets_threshold_below_40(tmp_db: Path) -> None:
    """3/10 very_disappointed = 30% → below threshold."""
    for i in range(10):
        _seed_prediction(tmp_db, prediction_id=f"p{i}", user_id=f"u{i}")
    responses = (
        ["very_disappointed"] * 3
        + ["somewhat_disappointed"] * 4
        + ["not_disappointed"] * 3
    )
    for i, r in enumerate(responses):
        _save_measurement(tmp_db, f"p{i}", f"u{i}", r)

    s = storage.get_sean_ellis_summary(
        bias_filter="all", db_path=tmp_db,
    )
    assert s["very_disappointed_pct"] == pytest.approx(30.0)
    assert s["meets_threshold"] is False


def test_sean_ellis_excludes_owner_by_default(tmp_db: Path) -> None:
    """Default bias_filter='exclude_owner' — playbook intent is
    market signal, so owner self-tests should be excluded by default."""
    _seed_prediction(
        tmp_db, prediction_id="owner_p", user_id="owner",
        is_owner_bias_flagged=True,
    )
    _seed_prediction(tmp_db, prediction_id="real_p", user_id="real")
    _save_measurement(tmp_db, "owner_p", "owner", "very_disappointed")
    _save_measurement(tmp_db, "real_p", "real", "not_disappointed")

    # Default
    s = storage.get_sean_ellis_summary(db_path=tmp_db)
    assert s["n"] == 1  # only real_p
    assert s["very_disappointed"] == 0
    assert s["not_disappointed"] == 1


def test_sean_ellis_invalid_bias_filter_raises(tmp_db: Path) -> None:
    with pytest.raises(ValueError):
        storage.get_sean_ellis_summary(
            db_path=tmp_db, bias_filter="bogus",
        )


def test_sean_ellis_per_user_filter(tmp_db: Path) -> None:
    _seed_prediction(tmp_db, prediction_id="p1", user_id="u1")
    _seed_prediction(tmp_db, prediction_id="p2", user_id="u2")
    _save_measurement(tmp_db, "p1", "u1", "very_disappointed")
    _save_measurement(tmp_db, "p2", "u2", "not_disappointed")
    s = storage.get_sean_ellis_summary(
        user_id="u1", bias_filter="all", db_path=tmp_db,
    )
    assert s["n"] == 1
    assert s["very_disappointed"] == 1


# ----- get_effort_test_summary -----


def test_effort_summary_empty_when_no_responses(tmp_db: Path) -> None:
    assert storage.get_effort_test_summary(db_path=tmp_db) == {}


def test_effort_summary_excludes_empty_string(tmp_db: Path) -> None:
    _seed_prediction(tmp_db, prediction_id="p1")
    _save_measurement(tmp_db, prediction_id="p1", effort="")
    assert storage.get_effort_test_summary(db_path=tmp_db) == {}


def test_effort_summary_counts_each_bucket(tmp_db: Path) -> None:
    for i in range(4):
        _seed_prediction(tmp_db, prediction_id=f"p{i}", user_id=f"u{i}")
    _save_measurement(tmp_db, "p0", "u0", effort="self_returned")
    _save_measurement(tmp_db, "p1", "u1", effort="self_returned")
    _save_measurement(tmp_db, "p2", "u2", effort="self_returned")
    _save_measurement(tmp_db, "p3", "u3", effort="needed_reminder")
    s = storage.get_effort_test_summary(
        bias_filter="all", db_path=tmp_db,
    )
    assert s["n"] == 4
    assert s["self_returned"] == 3
    assert s["needed_reminder"] == 1
    assert s["did_not_return"] == 0
    assert s["self_returned_pct"] == pytest.approx(75.0)
    assert s["leans_pull"] is True


def test_effort_summary_leans_pull_threshold(tmp_db: Path) -> None:
    """50% boundary — leans_pull is True only when strictly > 50%."""
    for i in range(2):
        _seed_prediction(tmp_db, prediction_id=f"p{i}", user_id=f"u{i}")
    _save_measurement(tmp_db, "p0", "u0", effort="self_returned")
    _save_measurement(tmp_db, "p1", "u1", effort="needed_reminder")
    s = storage.get_effort_test_summary(
        bias_filter="all", db_path=tmp_db,
    )
    assert s["self_returned_pct"] == pytest.approx(50.0)
    assert s["leans_pull"] is False  # 50% is not strictly > 50%


def test_effort_summary_excludes_owner_by_default(tmp_db: Path) -> None:
    _seed_prediction(
        tmp_db, prediction_id="owner_p", user_id="owner",
        is_owner_bias_flagged=True,
    )
    _seed_prediction(tmp_db, prediction_id="real_p", user_id="real")
    _save_measurement(tmp_db, "owner_p", "owner", effort="self_returned")
    _save_measurement(tmp_db, "real_p", "real", effort="did_not_return")
    s = storage.get_effort_test_summary(db_path=tmp_db)
    assert s["n"] == 1
    assert s["did_not_return"] == 1
    assert s["self_returned"] == 0


# ----- Public surface -----


def test_summary_helpers_callable() -> None:
    assert callable(storage.get_sean_ellis_summary)
    assert callable(storage.get_effort_test_summary)
