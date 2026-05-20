"""Stage 4 — user-organized history tree (OMY-V415 / M2 / Acceptance #55).

The flat date-grouped rail grows into a tree the user owns: user-defined
categories (folders) + free-form labels (tags). The app imposes no fixed
taxonomy. Storage gains a `categories` table, a `predictions.category_id`
column, and a `prediction_labels` table — all migrated via the existing
`_ensure_schema`.

Storage has no Streamlit dependency, so the CRUD layer is tested
directly with a temp DB. The UI wiring in app.py is checked at the
AST / source level.
"""

from __future__ import annotations

import ast
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage  # noqa: E402


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    return tmp_path / "tree_test.db"


def _make_prediction(
    db_path: Path, user_id: str = "u1", pid: str | None = None,
) -> storage.PredictionRecord:
    rec = storage.PredictionRecord(
        prediction_id=pid or storage.new_prediction_id(),
        user_id=user_id,
        scenario="career_decision",
        created_at=storage.now_unix(),
        user_input={"current_role": "Engineer"},
        belief_program={},
        wavefunction_snapshot={"hypotheses": []},
        joint_offdiag={},
    )
    storage.save_prediction(rec, db_path=db_path)
    return rec


# --------------------------------------------------------------------
# Schema migration
# --------------------------------------------------------------------

def test_schema_version_bumped() -> None:
    assert storage.SCHEMA_VERSION >= 6


def test_categories_and_labels_tables_created(db: Path) -> None:
    """Opening a fresh DB creates the Stage 4 tables + the new column."""
    with storage.db_connect(db) as conn:
        tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "categories" in tables
        assert "prediction_labels" in tables
        cols = {
            r["name"] for r in conn.execute(
                "PRAGMA table_info(predictions)"
            ).fetchall()
        }
        assert "category_id" in cols


def test_legacy_v5_db_migrates(tmp_path: Path) -> None:
    """A pre-Stage-4 predictions table (no category_id) upgrades cleanly
    and its rows stay readable."""
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE predictions (prediction_id TEXT PRIMARY KEY, "
        "user_id TEXT NOT NULL, scenario TEXT NOT NULL, "
        "created_at REAL NOT NULL, user_input_json TEXT NOT NULL, "
        "belief_program_json TEXT NOT NULL, wavefunction_json TEXT "
        "NOT NULL, joint_offdiag_json TEXT NOT NULL, notes TEXT "
        "DEFAULT '')"
    )
    conn.execute(
        "INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?)",
        ("p1", "u1", "career_decision", 1.0, "{}", "{}", "{}", "{}", ""),
    )
    conn.execute("PRAGMA user_version = 5")
    conn.commit()
    conn.close()

    # Opening via storage runs the migration.
    preds = storage.list_user_predictions("u1", db_path=db)
    assert len(preds) == 1
    assert preds[0].category_id is None  # new column reads as None
    # the new tables now work
    cat = storage.create_category("u1", "Box", db_path=db)
    storage.assign_prediction_category("p1", cat.category_id, db_path=db)
    assert storage.list_user_predictions(
        "u1", db_path=db,
    )[0].category_id == cat.category_id


# --------------------------------------------------------------------
# Categories — create / list / rename / delete
# --------------------------------------------------------------------

def test_create_and_list_categories(db: Path) -> None:
    a = storage.create_category("u1", "Career", db_path=db)
    b = storage.create_category("u1", "Investing", db_path=db)
    cats = storage.list_categories("u1", db_path=db)
    assert [c.name for c in cats] == ["Career", "Investing"]
    assert {c.category_id for c in cats} == {a.category_id, b.category_id}


def test_categories_scoped_per_user(db: Path) -> None:
    storage.create_category("u1", "Mine", db_path=db)
    storage.create_category("u2", "Theirs", db_path=db)
    assert [c.name for c in storage.list_categories("u1", db_path=db)] == [
        "Mine"
    ]
    assert [c.name for c in storage.list_categories("u2", db_path=db)] == [
        "Theirs"
    ]


def test_rename_category(db: Path) -> None:
    cat = storage.create_category("u1", "Old", db_path=db)
    storage.rename_category(cat.category_id, "New", db_path=db)
    assert storage.list_categories("u1", db_path=db)[0].name == "New"


def test_delete_category_keeps_predictions(db: Path) -> None:
    """Deleting a category must NOT destroy its predictions — they fall
    back to uncategorized."""
    cat = storage.create_category("u1", "Temp", db_path=db)
    rec = _make_prediction(db, "u1")
    storage.assign_prediction_category(
        rec.prediction_id, cat.category_id, db_path=db,
    )
    storage.delete_category(cat.category_id, db_path=db)
    # category gone
    assert storage.list_categories("u1", db_path=db) == []
    # prediction survives, now uncategorized
    preds = storage.list_user_predictions("u1", db_path=db)
    assert len(preds) == 1
    assert preds[0].category_id is None


def test_assign_and_unassign_category(db: Path) -> None:
    cat = storage.create_category("u1", "Box", db_path=db)
    rec = _make_prediction(db, "u1")
    storage.assign_prediction_category(
        rec.prediction_id, cat.category_id, db_path=db,
    )
    assert storage.list_user_predictions(
        "u1", db_path=db,
    )[0].category_id == cat.category_id
    # passing None moves it back out
    storage.assign_prediction_category(
        rec.prediction_id, None, db_path=db,
    )
    assert storage.list_user_predictions(
        "u1", db_path=db,
    )[0].category_id is None


# --------------------------------------------------------------------
# Labels — add / remove / list / dedupe
# --------------------------------------------------------------------

def test_add_and_list_labels(db: Path) -> None:
    rec = _make_prediction(db, "u1")
    storage.add_label(rec.prediction_id, "urgent", db_path=db)
    storage.add_label(rec.prediction_id, "big-decision", db_path=db)
    # alphabetical
    assert storage.list_labels(rec.prediction_id, db_path=db) == [
        "big-decision", "urgent",
    ]


def test_add_label_is_idempotent(db: Path) -> None:
    """Adding the same label twice is a no-op (composite-unique)."""
    rec = _make_prediction(db, "u1")
    storage.add_label(rec.prediction_id, "dup", db_path=db)
    storage.add_label(rec.prediction_id, "dup", db_path=db)
    assert storage.list_labels(rec.prediction_id, db_path=db) == ["dup"]


def test_add_blank_label_is_noop(db: Path) -> None:
    rec = _make_prediction(db, "u1")
    storage.add_label(rec.prediction_id, "   ", db_path=db)
    assert storage.list_labels(rec.prediction_id, db_path=db) == []


def test_remove_label(db: Path) -> None:
    rec = _make_prediction(db, "u1")
    storage.add_label(rec.prediction_id, "keep", db_path=db)
    storage.add_label(rec.prediction_id, "drop", db_path=db)
    storage.remove_label(rec.prediction_id, "drop", db_path=db)
    assert storage.list_labels(rec.prediction_id, db_path=db) == ["keep"]


def test_list_user_labels_distinct(db: Path) -> None:
    """list_user_labels gives every distinct label across the user's
    predictions."""
    r1 = _make_prediction(db, "u1")
    r2 = _make_prediction(db, "u1")
    storage.add_label(r1.prediction_id, "shared", db_path=db)
    storage.add_label(r2.prediction_id, "shared", db_path=db)
    storage.add_label(r2.prediction_id, "unique", db_path=db)
    assert storage.list_user_labels("u1", db_path=db) == [
        "shared", "unique",
    ]


def test_labels_for_predictions_batch(db: Path) -> None:
    r1 = _make_prediction(db, "u1")
    r2 = _make_prediction(db, "u1")
    storage.add_label(r1.prediction_id, "a", db_path=db)
    storage.add_label(r1.prediction_id, "b", db_path=db)
    batch = storage.labels_for_predictions(
        [r1.prediction_id, r2.prediction_id], db_path=db,
    )
    assert batch[r1.prediction_id] == ["a", "b"]
    assert batch[r2.prediction_id] == []


def test_labels_for_predictions_empty_input(db: Path) -> None:
    assert storage.labels_for_predictions([], db_path=db) == {}


# --------------------------------------------------------------------
# UI wiring (AST-level — app.py can't be imported under the runner)
# --------------------------------------------------------------------

APP_SRC = (
    Path(__file__).resolve().parent.parent / "app.py"
).read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


def test_history_rail_helper_exists() -> None:
    assert "def _render_history_rail(" in APP_SRC


def test_history_rail_supports_categories_and_labels() -> None:
    src = ast.unparse(_func("_render_history_rail"))
    # create-category control
    assert "storage.create_category" in src
    assert "storage.rename_category" in src
    assert "storage.delete_category" in src
    # group-by-category + filter-by-label
    assert "storage.list_categories" in src
    assert "storage.list_user_labels" in src
    assert "_history_label_filter" in src


def test_prediction_organizer_exists() -> None:
    assert "def _render_prediction_organizer(" in APP_SRC
    src = ast.unparse(_func("_render_prediction_organizer"))
    # assign a category + add / remove labels on a prediction
    assert "storage.assign_prediction_category" in src
    assert "storage.add_label" in src
    assert "storage.remove_label" in src


def test_measurement_update_invokes_organizer() -> None:
    """Opening a past prediction surfaces the category/label organizer."""
    src = ast.unparse(_func("render_measurement_update"))
    assert "_render_prediction_organizer(" in src
