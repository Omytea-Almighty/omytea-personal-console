"""Snapshot the SQLite predictions DB to a JSON dump.

The Streamlit Cloud free tier ships an ephemeral filesystem — the
container's local SQLite file vanishes on restart. This script is
the lightest-weight unblocker for the persistence gap described in
``DEPLOYMENT_GUIDE.md`` §5:

  1. Run this script on a cron (Streamlit Cloud doesn't natively
     support cron, so use a small external worker — Render free tier,
     fly.io free tier, or a GitHub Action on a schedule).
  2. The dump is written to ``<output_dir>/predictions_snapshot_<unix>.json``.
  3. Commit the JSON to a private "predictions-mirror" repo or push
     to a private bucket (your choice — this script doesn't move
     data off-machine, that's the operator's call).

Usage:
    python scripts/snapshot_predictions.py [--db-path PATH] [--output-dir DIR] [--pretty]

Exit codes:
    0  — snapshot written
    1  — DB unreadable / unexpected error
    2  — bad args

Master plan compatibility:
  - §15 Rule #11 — provider-neutral (no cloud SDK; just stdlib + sqlite3).
  - §2.9 negative scope — no PII exfiltration; the dump structure
    is the same as what the local app already serializes; the
    decision to move it off-machine is explicit operator action.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path


_DEFAULT_DB = (
    Path.home() / ".omytea-personal-console" / "predictions.db"
)


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    """Convert a Row to a regular dict; tolerate blob columns."""
    out: dict[str, object] = {}
    for k in row.keys():
        v = row[k]
        if isinstance(v, (bytes, bytearray)):
            try:
                out[k] = v.decode("utf-8", errors="replace")
            except Exception:
                out[k] = repr(v)[:200]
        else:
            out[k] = v
    return out


def snapshot(
    db_path: Path,
    output_dir: Path,
    pretty: bool = False,
) -> Path:
    """Dump every table to JSON. Returns the snapshot file path.

    Tables that don't exist are skipped (forward + backward
    compatibility across schema versions).
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"predictions_snapshot_{int(time.time())}.json"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # List all user tables
        tables_rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        tables = [r["name"] for r in tables_rows]

        snapshot_dict: dict[str, object] = {
            "schema_version": conn.execute(
                "PRAGMA user_version"
            ).fetchone()[0],
            "snapshot_unix": int(time.time()),
            "source_db": str(db_path),
            "tables": {},
        }
        for table in tables:
            try:
                rows = conn.execute(
                    f"SELECT * FROM {table}"  # noqa: S608 — table names from sqlite_master, safe
                ).fetchall()
                snapshot_dict["tables"][table] = [
                    _row_to_dict(r) for r in rows
                ]
            except sqlite3.Error as exc:
                snapshot_dict["tables"][table] = {
                    "_dump_error": str(exc)
                }
    finally:
        conn.close()

    indent = 2 if pretty else None
    out_path.write_text(
        json.dumps(snapshot_dict, indent=indent, default=str),
        encoding="utf-8",
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Snapshot the Personal Future Console predictions DB to "
            "a JSON dump. See DEPLOYMENT_GUIDE.md §5 for the cloud-"
            "persistence pattern."
        ),
    )
    parser.add_argument(
        "--db-path", type=Path, default=_DEFAULT_DB,
        help=f"SQLite DB path (default: {_DEFAULT_DB})",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path.cwd() / "predictions_snapshots",
        help="Directory to write snapshots into (default: ./predictions_snapshots)",
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Indent JSON output (larger files, human-readable).",
    )
    args = parser.parse_args(argv)

    try:
        out_path = snapshot(
            db_path=args.db_path,
            output_dir=args.output_dir,
            pretty=args.pretty,
        )
    except FileNotFoundError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"✗ Snapshot failed: {exc}", file=sys.stderr)
        return 1

    size_kb = out_path.stat().st_size / 1024
    print(f"✓ Snapshot written: {out_path}  ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
