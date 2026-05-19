"""v4.16 P2 — branch drill-down loop tests.

Covers:
- compile_branch_drilldown in mock mode produces the canonical shape
- mock drill-down tones differ by branch_type
- Drill-down storage round-trip (save + get + list + delete)
- ON CONFLICT UPSERT: re-saving for the same (prediction, branch) pair
  replaces rather than accumulates
- Migration: legacy v2 DB (no branch_drilldowns table) reopens cleanly
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


@pytest.fixture(autouse=True)
def _force_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")


def _seed_prediction(
    tmp_db: Path,
    prediction_id: str = "p1",
    user_id: str = "u1",
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
    )
    storage.save_prediction(rec, db_path=tmp_db)


def _drilldown(
    tmp_db: Path,
    prediction_id: str = "p1",
    branch_label: str = "thrive_at_new_role",
    payload: dict | None = None,
) -> storage.BranchDrilldown:
    return storage.BranchDrilldown(
        drilldown_id=storage.new_drilldown_id(),
        prediction_id=prediction_id,
        branch_label=branch_label,
        created_at=storage.now_unix(),
        drilldown_json=payload or {"branch_label": branch_label},
    )


# ----- compiler.compile_branch_drilldown in mock mode -----


def test_mock_drilldown_returns_expected_shape() -> None:
    from compiler import compile_branch_drilldown

    out = compile_branch_drilldown(
        branch_label="thrive_at_new_role",
        branch_type="wishful",
        full_belief_program={"branches": []},
        user_input={"current_role": "x"},
    )
    for key in (
        "branch_label", "deeper_narrative", "concrete_actions_this_week",
        "conditional_dependencies", "sensitivity_preview",
    ):
        assert key in out
    assert out["branch_label"] == "thrive_at_new_role"


def test_mock_drilldown_has_three_narrative_paragraphs() -> None:
    from compiler import compile_branch_drilldown

    out = compile_branch_drilldown(
        branch_label="x", branch_type="wishful",
        full_belief_program={}, user_input={},
    )
    assert len(out["deeper_narrative"]) == 3
    for para in out["deeper_narrative"]:
        assert len(para) > 30  # not a trivial placeholder


def test_mock_drilldown_actions_have_required_fields() -> None:
    from compiler import compile_branch_drilldown

    out = compile_branch_drilldown(
        branch_label="x", branch_type="realistic",
        full_belief_program={}, user_input={},
    )
    assert len(out["concrete_actions_this_week"]) >= 3
    for a in out["concrete_actions_this_week"]:
        for key in ("action", "expected_effect", "effort"):
            assert key in a
        assert a["effort"] in ("low", "medium", "high")


def test_mock_drilldown_tone_differs_by_branch_type() -> None:
    """Wishful / worst / realistic should produce different opening
    narrative tones — verifies the tone_intro switch works."""
    from compiler import compile_branch_drilldown

    wishful = compile_branch_drilldown(
        branch_label="x", branch_type="wishful",
        full_belief_program={}, user_input={},
    )
    worst = compile_branch_drilldown(
        branch_label="x", branch_type="worst",
        full_belief_program={}, user_input={},
    )
    realistic = compile_branch_drilldown(
        branch_label="x", branch_type="realistic",
        full_belief_program={}, user_input={},
    )
    # First paragraphs should differ because tone_intro varies.
    assert wishful["deeper_narrative"][0] != worst["deeper_narrative"][0]
    assert worst["deeper_narrative"][0] != realistic["deeper_narrative"][0]
    assert "aligns" in wishful["deeper_narrative"][0].lower()
    assert "worst" in worst["deeper_narrative"][0].lower()


def test_mock_drilldown_sensitivity_preview_uses_pp_units() -> None:
    from compiler import compile_branch_drilldown

    out = compile_branch_drilldown(
        branch_label="x", branch_type="wishful",
        full_belief_program={}, user_input={},
    )
    # Each entry must have positive + negative pp values keyed
    # if_positive_delta_p and if_negative_delta_p (P5 schema).
    for s in out["sensitivity_preview"]:
        assert "if_positive_delta_p" in s
        assert "if_negative_delta_p" in s
        # Negative-side ΔP is signed negative (-N pp).
        assert s["if_negative_delta_p"] <= 0
        assert s["if_positive_delta_p"] >= 0


# ----- Schema migration -----


def test_branch_drilldowns_table_exists_after_open(tmp_db: Path) -> None:
    with storage.db_connect(tmp_db) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='branch_drilldowns'"
        )
        assert cur.fetchone() is not None


def test_schema_version_at_least_3(tmp_db: Path) -> None:
    """branch_drilldowns table came in at v3; future migrations may
    push the version higher (P6 added v4)."""
    with storage.db_connect(tmp_db) as conn:
        row = conn.execute("PRAGMA user_version").fetchone()
    assert row[0] >= 3


def test_migration_from_v2_adds_table(tmp_db: Path) -> None:
    """A legacy v2 DB (predictions + measurement_updates with the
    owner-bias column but no branch_drilldowns table) should add the
    table cleanly on reopen."""
    p = tmp_db
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE predictions (
            prediction_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            scenario TEXT NOT NULL,
            created_at REAL NOT NULL,
            user_input_json TEXT NOT NULL,
            belief_program_json TEXT NOT NULL,
            wavefunction_json TEXT NOT NULL,
            joint_offdiag_json TEXT NOT NULL,
            notes TEXT DEFAULT '',
            is_owner_bias_flagged INTEGER DEFAULT 0
        )
        """
    )
    cur.execute("PRAGMA user_version = 2")
    conn.commit()
    conn.close()
    # Reopen → migration should add the new table.
    with storage.db_connect(tmp_db) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='branch_drilldowns'"
        )
        assert cur.fetchone() is not None


# ----- Storage round-trip -----


def test_save_and_get_drilldown(tmp_db: Path) -> None:
    _seed_prediction(tmp_db)
    rec = _drilldown(tmp_db, payload={"branch_label": "thrive", "extra": 1})
    storage.save_drilldown(rec, db_path=tmp_db)
    got = storage.get_drilldown(
        "p1", "thrive_at_new_role", db_path=tmp_db,
    )
    assert got is not None
    assert got.prediction_id == "p1"
    assert got.branch_label == "thrive_at_new_role"
    assert got.drilldown_json["extra"] == 1


def test_get_drilldown_returns_none_when_absent(tmp_db: Path) -> None:
    _seed_prediction(tmp_db)
    assert storage.get_drilldown("p1", "nonexistent", db_path=tmp_db) is None


def test_upsert_replaces_on_conflict(tmp_db: Path) -> None:
    """Re-saving for the same (prediction_id, branch_label) should
    overwrite, not accumulate duplicate rows."""
    _seed_prediction(tmp_db)
    storage.save_drilldown(
        _drilldown(tmp_db, payload={"version": 1}), db_path=tmp_db,
    )
    storage.save_drilldown(
        _drilldown(tmp_db, payload={"version": 2}), db_path=tmp_db,
    )
    drilldowns = storage.list_drilldowns("p1", db_path=tmp_db)
    assert len(drilldowns) == 1
    assert drilldowns[0].drilldown_json["version"] == 2


def test_list_drilldowns_returns_newest_first(tmp_db: Path) -> None:
    _seed_prediction(tmp_db)
    older = storage.BranchDrilldown(
        drilldown_id="d1", prediction_id="p1", branch_label="A",
        created_at=100.0, drilldown_json={},
    )
    newer = storage.BranchDrilldown(
        drilldown_id="d2", prediction_id="p1", branch_label="B",
        created_at=200.0, drilldown_json={},
    )
    storage.save_drilldown(older, db_path=tmp_db)
    storage.save_drilldown(newer, db_path=tmp_db)
    out = storage.list_drilldowns("p1", db_path=tmp_db)
    assert [d.branch_label for d in out] == ["B", "A"]


def test_list_drilldowns_scoped_by_prediction(tmp_db: Path) -> None:
    _seed_prediction(tmp_db, prediction_id="p1")
    _seed_prediction(tmp_db, prediction_id="p2", user_id="u2")
    storage.save_drilldown(
        _drilldown(tmp_db, prediction_id="p1"), db_path=tmp_db,
    )
    storage.save_drilldown(
        _drilldown(tmp_db, prediction_id="p2"), db_path=tmp_db,
    )
    assert len(storage.list_drilldowns("p1", db_path=tmp_db)) == 1
    assert len(storage.list_drilldowns("p2", db_path=tmp_db)) == 1


def test_delete_drilldown_returns_row_count(tmp_db: Path) -> None:
    _seed_prediction(tmp_db)
    storage.save_drilldown(_drilldown(tmp_db), db_path=tmp_db)
    deleted = storage.delete_drilldown(
        "p1", "thrive_at_new_role", db_path=tmp_db,
    )
    assert deleted == 1
    # Cache now empty.
    assert storage.get_drilldown(
        "p1", "thrive_at_new_role", db_path=tmp_db,
    ) is None


def test_delete_drilldown_nonexistent_returns_zero(tmp_db: Path) -> None:
    _seed_prediction(tmp_db)
    assert storage.delete_drilldown(
        "p1", "absent", db_path=tmp_db,
    ) == 0


# ----- BranchDrilldown dataclass -----


def test_branch_drilldown_dataclass_fields() -> None:
    rec = storage.BranchDrilldown(
        drilldown_id="d1",
        prediction_id="p1",
        branch_label="x",
        created_at=1.0,
        drilldown_json={"k": "v"},
    )
    assert rec.drilldown_id == "d1"
    assert rec.drilldown_json["k"] == "v"


def test_new_drilldown_id_returns_unique() -> None:
    a = storage.new_drilldown_id()
    b = storage.new_drilldown_id()
    assert a != b
    assert len(a) > 10  # UUIDv4 format
