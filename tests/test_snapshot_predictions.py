"""Tests for scripts/snapshot_predictions.py — the
DEPLOYMENT_GUIDE.md §5 SQLite-persistence unblocker.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_tiny_db(path: Path) -> None:
    """Build a tiny SQLite DB with a couple of rows so snapshot has
    something to serialize."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA user_version = 5")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS predictions ("
            "prediction_id TEXT PRIMARY KEY, "
            "user_id TEXT, "
            "scenario TEXT, "
            "created_at INTEGER, "
            "data TEXT)"
        )
        conn.executemany(
            "INSERT INTO predictions VALUES (?, ?, ?, ?, ?)",
            [
                ("p1", "u1", "video_scene_query", 1700000000, '{"x": 1}'),
                ("p2", "u2", "career_decision", 1700000100, '{"y": 2}'),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def test_snapshot_writes_json_with_tables(tmp_path: Path) -> None:
    from scripts import snapshot_predictions as snap

    db = tmp_path / "test.db"
    out_dir = tmp_path / "out"
    _make_tiny_db(db)

    out_path = snap.snapshot(db_path=db, output_dir=out_dir, pretty=True)
    assert out_path.exists()

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 5
    assert "predictions" in data["tables"]
    assert len(data["tables"]["predictions"]) == 2
    assert data["tables"]["predictions"][0]["prediction_id"] == "p1"


def test_snapshot_raises_when_db_missing(tmp_path: Path) -> None:
    from scripts import snapshot_predictions as snap
    nonexistent = tmp_path / "nope.db"
    out_dir = tmp_path / "out"
    with pytest.raises(FileNotFoundError):
        snap.snapshot(db_path=nonexistent, output_dir=out_dir)


def test_snapshot_handles_empty_db(tmp_path: Path) -> None:
    """A DB with no tables should still produce a valid snapshot."""
    from scripts import snapshot_predictions as snap
    db = tmp_path / "empty.db"
    db.touch()
    # SQLite will treat an empty file as a valid empty DB on first write
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA user_version = 0")
    conn.close()

    out_dir = tmp_path / "out"
    out_path = snap.snapshot(db_path=db, output_dir=out_dir)
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["tables"] == {}


def test_snapshot_cli_returns_zero_on_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import snapshot_predictions as snap
    db = tmp_path / "cli.db"
    _make_tiny_db(db)
    out_dir = tmp_path / "out"
    code = snap.main([
        "--db-path", str(db),
        "--output-dir", str(out_dir),
        "--pretty",
    ])
    assert code == 0
    captured = capsys.readouterr()
    assert "Snapshot written" in captured.out


def test_snapshot_cli_returns_one_on_missing_db(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import snapshot_predictions as snap
    code = snap.main([
        "--db-path", str(tmp_path / "absent.db"),
        "--output-dir", str(tmp_path / "out"),
    ])
    assert code == 1


def test_snapshot_handles_blob_columns(tmp_path: Path) -> None:
    """Blob columns get decoded best-effort so the JSON is still valid."""
    from scripts import snapshot_predictions as snap
    db = tmp_path / "blob.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE bin (id INTEGER, payload BLOB)")
    conn.execute(
        "INSERT INTO bin VALUES (?, ?)",
        (1, b"\x00\x01\x02\xff\xfe"),
    )
    conn.commit()
    conn.close()
    out = snap.snapshot(db_path=db, output_dir=tmp_path / "out")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "bin" in data["tables"]
    assert data["tables"]["bin"][0]["id"] == 1
    # payload is some printable form
    assert isinstance(data["tables"]["bin"][0]["payload"], str)
