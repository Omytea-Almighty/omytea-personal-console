"""SQLite-compatible persistence for predictions + measurement updates.

Schema versioned via PRAGMA user_version. Tables:
- predictions: each user prediction snapshot
- measurement_updates: actual outcomes reported later
- branch_drilldowns: cached drill-down LLM outputs (one per
  prediction × branch)
- entitlements, preorder_interest: pricing-tier holdings + PMF
  research

Migrations are idempotent — opening a legacy DB performs ADD COLUMN
/ CREATE TABLE IF NOT EXISTS as needed and bumps user_version.

Iter #44 — durable backing store. The console can now persist to
**Turso** (a hosted libSQL service, 100% SQLite-compatible) when
the env vars ``OMYTEA_TURSO_URL`` + ``OMYTEA_TURSO_AUTH_TOKEN``
are set. Without them, behavior is unchanged: local SQLite at
``DEFAULT_DB_PATH``. Streamlit Cloud's filesystem is ephemeral
so the local-SQLite path **does not survive a redeploy**; Turso
is what makes the PMF measurement loop (predict → wait → score)
survive across N months. See ``SETUP_TURSO.md`` at the repo
root for the founder's ~3-minute setup (turso db create +
secrets paste).

Privacy: local-SQLite path stays on the local disk; Turso path
stores rows on Turso's edge (their privacy posture applies).
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 6  # v4.18 Stage 4: + categories + prediction_labels tables

DEFAULT_DB_PATH = Path(
    os.environ.get(
        "OMYTEA_CONSOLE_DB",
        str(Path.home() / ".omytea-personal-console" / "predictions.db"),
    )
)


# Iter #44 — Turso (libSQL) detection. Env-var gated so the local
# tests + local dev unchanged. App.py bridges st.secrets → env vars
# at startup so a Streamlit Cloud deploy with `[turso]` block in
# secrets.toml automatically uses the durable backing store.
_TURSO_URL = os.environ.get("OMYTEA_TURSO_URL", "").strip()
_TURSO_AUTH_TOKEN = os.environ.get("OMYTEA_TURSO_AUTH_TOKEN", "").strip()
_USING_TURSO = bool(_TURSO_URL)

# libsql_experimental is optional — if the wheel didn't install
# (which can happen on some platforms) gracefully fall back to
# local SQLite + emit a one-time stderr warning so the founder
# sees it in the Streamlit Cloud logs.
_libsql = None
if _USING_TURSO:
    try:
        import libsql_experimental as _libsql  # type: ignore
    except ImportError:
        try:
            # Fallback module name — the package has been renamed
            # across versions.
            import libsql as _libsql  # type: ignore
        except ImportError:
            import sys
            print(
                "[storage] WARNING: OMYTEA_TURSO_URL is set but "
                "neither `libsql_experimental` nor `libsql` is "
                "installed; falling back to local SQLite. The "
                "demo's data will be ephemeral. Add "
                "`libsql-experimental` to requirements.txt or "
                "see SETUP_TURSO.md.",
                file=sys.stderr,
            )
            _USING_TURSO = False


def using_turso() -> bool:
    """Diagnostic — used by the footer + tests to verify durable
    storage is active. Returns True only when both the env vars
    are set AND the libsql module imported successfully."""
    return _USING_TURSO and _libsql is not None


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    """One user prediction snapshot.

    ``is_owner_bias_flagged`` lets a prediction explicitly opt in to
    being tagged as project-owner / self-test data so the aggregate
    calibration view can show "with owner data point / without it" —
    addresses the project-owner-as-user bias risk that early adopters
    may score the system more generously than a neutral user would.
    """

    prediction_id: str
    user_id: str
    scenario: str  # e.g. "career_decision"
    created_at: float  # unix epoch
    user_input: dict[str, Any]  # raw form data
    belief_program: dict[str, Any]  # compiler output
    wavefunction_snapshot: dict[str, Any]  # branch list with probabilities
    joint_offdiag: dict[str, Any]  # off-diagonal joint hypotheses
    notes: str = ""
    is_owner_bias_flagged: bool = False
    # v4.18 Stage 4 — the user-defined category (folder) this prediction
    # sits in. None = uncategorized. Read-only on the record; mutated
    # via assign_prediction_category().
    category_id: str | None = None


@dataclass(frozen=True, slots=True)
class Category:
    """v4.18 Stage 4 — a user-defined history category (folder).

    The app imposes no fixed taxonomy. The user creates / renames /
    deletes their own categories, exactly like Notion folders or a
    file manager. Scoped per user_id.
    """

    category_id: str
    user_id: str
    name: str
    created_at: float


@dataclass(frozen=True, slots=True)
class Entitlement:
    """Which tier a user holds. Hibernates until real billing (Stripe
    / equivalent) is plumbed; until then rows are created only by
    operator / admin scripts."""

    entitlement_id: str
    user_id: str
    tier_id: str       # one of pricing.TIER_*
    granted_at: float  # unix epoch
    expires_at: float | None = None  # None = perpetual (lifetime / hw)
    source: str = "manual"  # "manual" | "stripe" | "promo" | future
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PreorderInterest:
    """User expressed willingness to pay $N for tier X. Pre-revenue
    PMF research; no payment is taken. Multiple records per user_id
    are allowed (people change their minds; capture the history)."""

    interest_id: str
    user_id: str
    tier_id: str
    expressed_at: float
    willing_to_pay_usd: float
    locale: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class BranchDrilldown:
    """v4.16 P2 — cached drill-down output for one (prediction, branch)
    pair. We cache because LLM calls are slow + cost real quota; each
    user-click on "drill down" can otherwise repeat the same call."""

    drilldown_id: str
    prediction_id: str
    branch_label: str
    created_at: float
    drilldown_json: dict[str, Any]  # the LLM output


@dataclass(frozen=True, slots=True)
class MeasurementUpdate:
    """One actual-outcome observation, keyed to a prior prediction.

    Adopts the Anthropic founder's playbook (2026-05-14) PMF
    instruments:
      - sean_ellis_response: canonical Sean Ellis question
        ("How would you feel if you could no longer use this
        product?") with three buckets — `very_disappointed`,
        `somewhat_disappointed`, `not_disappointed`. >40% in
        ``very_disappointed`` across users is the playbook's PMF
        threshold.
      - effort_test_response: did the user self-return to the
        product over the 6-week measurement window, or only when
        the operator nudged them? Buckets — `self_returned`,
        `needed_reminder`, `did_not_return`. Pre-PMF retention
        requires "heroic founder energy"; post-PMF the product
        "starts doing that work on its own." Captures that
        push→pull transition signal.

    Empty strings = not yet captured (legacy rows or older
    questionnaire iterations). Aggregate queries should treat the
    empty-string state as "missing", not as a fourth bucket.
    """

    update_id: str
    prediction_id: str
    user_id: str
    observed_at: float  # unix epoch
    actual_outcome: dict[str, Any]  # which branch(es) materialized
    calibration_delta: dict[str, float]  # Brier / log-loss vs original
    user_satisfaction: int | None = None  # NPS-style 0-10
    user_notes: str = ""
    sean_ellis_response: str = ""
    effort_test_response: str = ""


def _column_exists(
    conn: sqlite3.Connection, table: str, column: str,
) -> bool:
    """SQLite-portable column existence check (PRAGMA table_info)."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotent schema creation + migration. Run on every connect."""
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
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
        """
        CREATE TABLE IF NOT EXISTS measurement_updates (
            update_id            TEXT PRIMARY KEY,
            prediction_id        TEXT NOT NULL,
            user_id              TEXT NOT NULL,
            observed_at          REAL NOT NULL,
            actual_outcome_json  TEXT NOT NULL,
            calibration_json     TEXT NOT NULL,
            user_satisfaction    INTEGER,
            user_notes           TEXT DEFAULT '',
            FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
        )
        """
    )

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_updates_prediction "
        "ON measurement_updates(prediction_id)"
    )

    # v4.16 P8 migration: tag owner-bias predictions on the predictions
    # table so the calibration aggregate can split with/without.
    # The flag lives on predictions only; measurement_updates inherits
    # it via JOIN on prediction_id. Idempotent: ALTER TABLE ADD COLUMN
    # only runs when the column is genuinely missing.
    if not _column_exists(conn, "predictions", "is_owner_bias_flagged"):
        cur.execute(
            "ALTER TABLE predictions "
            "ADD COLUMN is_owner_bias_flagged INTEGER DEFAULT 0"
        )

    # v4.16 P2 migration: branch_drilldowns cache. Composite uniqueness
    # on (prediction_id, branch_label) — only one cached drilldown per
    # prediction × branch. Cache invalidation = drop the row.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS branch_drilldowns (
            drilldown_id    TEXT PRIMARY KEY,
            prediction_id   TEXT NOT NULL,
            branch_label    TEXT NOT NULL,
            created_at      REAL NOT NULL,
            drilldown_json  TEXT NOT NULL,
            UNIQUE (prediction_id, branch_label),
            FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_drilldowns_prediction "
        "ON branch_drilldowns(prediction_id)"
    )

    # v4.16 P6 migration: entitlements + preorder_interest tables.
    # Both are independent of the prediction graph; the user_id is
    # the common key.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS entitlements (
            entitlement_id  TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            tier_id         TEXT NOT NULL,
            granted_at      REAL NOT NULL,
            expires_at      REAL,
            source          TEXT NOT NULL DEFAULT 'manual',
            notes           TEXT DEFAULT ''
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_entitlements_user "
        "ON entitlements(user_id)"
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS preorder_interest (
            interest_id          TEXT PRIMARY KEY,
            user_id              TEXT NOT NULL,
            tier_id              TEXT NOT NULL,
            expressed_at         REAL NOT NULL,
            willing_to_pay_usd   REAL NOT NULL,
            locale               TEXT DEFAULT '',
            notes                TEXT DEFAULT ''
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_preorder_tier "
        "ON preorder_interest(tier_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_preorder_user "
        "ON preorder_interest(user_id)"
    )

    # v4.16 playbook-adopt migration: Sean Ellis test + effort test
    # columns on measurement_updates. Both default to empty string so
    # legacy rows stay legible. ALTER TABLE IF NOT EXISTS is gated by
    # _column_exists since SQLite < 3.35 lacks the IF NOT EXISTS form.
    if not _column_exists(conn, "measurement_updates", "sean_ellis_response"):
        cur.execute(
            "ALTER TABLE measurement_updates "
            "ADD COLUMN sean_ellis_response TEXT DEFAULT ''"
        )
    if not _column_exists(conn, "measurement_updates", "effort_test_response"):
        cur.execute(
            "ALTER TABLE measurement_updates "
            "ADD COLUMN effort_test_response TEXT DEFAULT ''"
        )

    # v4.18 Stage 4 migration: user-organized history tree. The app
    # imposes no fixed taxonomy — the user creates their own categories
    # (folders) and labels (tags). Three pieces:
    #   • categories       — user-defined folders, scoped per user_id.
    #   • predictions.category_id — which folder a prediction sits in
    #     (NULL = uncategorized). ON DELETE the category is set NULL so
    #     deleting a folder never destroys predictions.
    #   • prediction_labels — free-form tags; a prediction may carry
    #     several. Composite-unique on (prediction_id, label) so the
    #     same tag can't be added twice.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            category_id   TEXT PRIMARY KEY,
            user_id       TEXT NOT NULL,
            name          TEXT NOT NULL,
            created_at    REAL NOT NULL
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_categories_user "
        "ON categories(user_id)"
    )
    if not _column_exists(conn, "predictions", "category_id"):
        cur.execute(
            "ALTER TABLE predictions ADD COLUMN category_id TEXT DEFAULT NULL"
        )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_labels (
            label_id        TEXT PRIMARY KEY,
            prediction_id   TEXT NOT NULL,
            label           TEXT NOT NULL,
            created_at      REAL NOT NULL,
            UNIQUE (prediction_id, label),
            FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_pred_labels_prediction "
        "ON prediction_labels(prediction_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_pred_labels_label "
        "ON prediction_labels(label)"
    )

    cur.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


@contextmanager
def db_connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open SQLite-compatible connection; ensure schema; close on exit.

    Iter #44 — durable storage. When ``OMYTEA_TURSO_URL`` is set
    (and the explicit ``db_path`` override isn't passed by a test),
    the connection points at Turso's hosted libSQL — same SQL,
    same Python DB-API, but the rows survive any Streamlit Cloud
    redeploy. Otherwise the original local-SQLite path runs
    unchanged.

    Test overrides + the ``db_path`` parameter always bypass the
    Turso path so unit tests stay deterministic and offline.
    """
    if _USING_TURSO and _libsql is not None and db_path is None:
        # Turso libSQL — the connect() signature is the same as
        # sqlite3.connect() with an additional auth_token kw.
        # Connections are network-backed but the Python API matches
        # sqlite3.Connection closely enough that the existing
        # cursor / execute / commit calls all work verbatim.
        conn = _libsql.connect(
            database=_TURSO_URL,
            auth_token=_TURSO_AUTH_TOKEN,
        )
        try:
            # libsql_experimental's Connection doesn't accept the
            # `row_factory = sqlite3.Row` assignment, but its
            # `.execute()` returns row-objects that behave like
            # tuples + support index/column-name access — close
            # enough to sqlite3.Row that downstream code works.
            try:
                conn.row_factory = sqlite3.Row  # type: ignore[attr-defined]
            except Exception:
                pass
            _ensure_schema(conn)
            yield conn
            try:
                conn.commit()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return

    # Local SQLite — unchanged behavior. Test suite always hits
    # this path because db_path overrides bypass the Turso branch.
    p = db_path or DEFAULT_DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def save_prediction(rec: PredictionRecord, db_path: Path | None = None) -> None:
    """Persist a new prediction snapshot."""
    with db_connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO predictions (
                prediction_id, user_id, scenario, created_at,
                user_input_json, belief_program_json,
                wavefunction_json, joint_offdiag_json, notes,
                is_owner_bias_flagged, category_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.prediction_id,
                rec.user_id,
                rec.scenario,
                rec.created_at,
                json.dumps(rec.user_input, ensure_ascii=False),
                json.dumps(rec.belief_program, ensure_ascii=False),
                json.dumps(rec.wavefunction_snapshot, ensure_ascii=False),
                json.dumps(rec.joint_offdiag, ensure_ascii=False),
                rec.notes,
                1 if rec.is_owner_bias_flagged else 0,
                rec.category_id,
            ),
        )
        conn.commit()


def save_measurement(rec: MeasurementUpdate, db_path: Path | None = None) -> None:
    """Persist a measurement-update (actual-outcome) record."""
    with db_connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO measurement_updates (
                update_id, prediction_id, user_id, observed_at,
                actual_outcome_json, calibration_json,
                user_satisfaction, user_notes,
                sean_ellis_response, effort_test_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.update_id,
                rec.prediction_id,
                rec.user_id,
                rec.observed_at,
                json.dumps(rec.actual_outcome, ensure_ascii=False),
                json.dumps(rec.calibration_delta, ensure_ascii=False),
                rec.user_satisfaction,
                rec.user_notes,
                rec.sean_ellis_response,
                rec.effort_test_response,
            ),
        )
        conn.commit()


def list_user_predictions(
    user_id: str, db_path: Path | None = None,
) -> list[PredictionRecord]:
    """Return all predictions for a given user, newest first."""
    out: list[PredictionRecord] = []
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        for r in rows:
            # is_owner_bias_flagged / category_id may be missing for old
            # rows from a pre-migration DB (defensive read).
            owner_flag = 0
            try:
                owner_flag = int(r["is_owner_bias_flagged"] or 0)
            except (IndexError, KeyError):
                owner_flag = 0
            category_id = None
            try:
                category_id = r["category_id"]
            except (IndexError, KeyError):
                category_id = None
            out.append(
                PredictionRecord(
                    prediction_id=r["prediction_id"],
                    user_id=r["user_id"],
                    scenario=r["scenario"],
                    created_at=r["created_at"],
                    user_input=json.loads(r["user_input_json"]),
                    belief_program=json.loads(r["belief_program_json"]),
                    wavefunction_snapshot=json.loads(r["wavefunction_json"]),
                    joint_offdiag=json.loads(r["joint_offdiag_json"]),
                    notes=r["notes"] or "",
                    is_owner_bias_flagged=bool(owner_flag),
                    category_id=category_id,
                )
            )
    return out


def delete_user_predictions(
    user_id: str, db_path: Path | None = None,
) -> int:
    """Delete every prediction belonging to ``user_id``; return the row
    count removed.

    Wired to Settings -> Data & privacy "clear history". Streamlit
    Cloud's filesystem is ephemeral, so the prediction DB does not
    survive a container restart regardless — this clears the live
    session's rows on demand.
    """
    with db_connect(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM predictions WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        return int(cur.rowcount)


def get_calibration_aggregate(
    user_id: str | None = None,
    db_path: Path | None = None,
    bias_filter: str = "all",
) -> dict[str, float]:
    """Aggregate calibration metrics across all (or per-user) measurement updates.

    Args:
      user_id: if set, restrict to that user; else aggregate across all
        users.
      db_path: override default DB location.
      bias_filter: one of ``"all"`` (default), ``"exclude_owner"`` (drop
        measurements on predictions tagged as owner-bias), or
        ``"owner_only"`` (only measurements on owner-flagged
        predictions). v4.16 P8 — addresses founder-as-user bias surfaced
        in H4 data point #1.

    Returns:
      Dict with mean Brier score, mean log-loss, sample count.
      Empty dict if no measurements match the filter.
    """
    if bias_filter not in ("all", "exclude_owner", "owner_only"):
        raise ValueError(
            f"bias_filter must be 'all' | 'exclude_owner' | 'owner_only', "
            f"got {bias_filter!r}"
        )

    # JOIN to the predictions table to read the bias flag — the flag
    # lives on predictions (single source of truth) and is inherited by
    # measurement_updates via prediction_id.
    bias_where = ""
    if bias_filter == "exclude_owner":
        bias_where = " AND COALESCE(p.is_owner_bias_flagged, 0) = 0"
    elif bias_filter == "owner_only":
        bias_where = " AND COALESCE(p.is_owner_bias_flagged, 0) = 1"

    with db_connect(db_path) as conn:
        if user_id:
            sql = (
                "SELECT m.calibration_json FROM measurement_updates m "
                "JOIN predictions p ON p.prediction_id = m.prediction_id "
                "WHERE m.user_id = ?" + bias_where
            )
            rows = conn.execute(sql, (user_id,)).fetchall()
        else:
            sql = (
                "SELECT m.calibration_json FROM measurement_updates m "
                "JOIN predictions p ON p.prediction_id = m.prediction_id "
                "WHERE 1=1" + bias_where
            )
            rows = conn.execute(sql).fetchall()
    if not rows:
        return {}
    briers: list[float] = []
    log_losses: list[float] = []
    for r in rows:
        cal = json.loads(r["calibration_json"])
        if "brier" in cal:
            briers.append(float(cal["brier"]))
        if "log_loss" in cal:
            log_losses.append(float(cal["log_loss"]))
    out: dict[str, float] = {"n_measurements": float(len(rows))}
    if briers:
        out["mean_brier"] = sum(briers) / len(briers)
    if log_losses:
        out["mean_log_loss"] = sum(log_losses) / len(log_losses)
    return out


def get_sean_ellis_summary(
    user_id: str | None = None,
    bias_filter: str = "exclude_owner",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """v4.16 playbook-adopt — Sean Ellis disappointment aggregate.

    Anthropic's playbook §4 (MVP) calls out the canonical PMF
    indicator: among active users, the share who answer "very
    disappointed" to "How would you feel if you could no longer use
    this product?" If >40% say very_disappointed, that's a meaningful
    PMF signal.

    Args:
      user_id: optional user filter (None = aggregate across users).
      bias_filter: default ``"exclude_owner"`` — playbook intent is
        market signal, so owner self-tests should be excluded by
        default. Pass ``"all"`` if you want every response.
      db_path: override db path.

    Returns:
      Dict with keys:
        - ``n``: total measurements with a Sean Ellis response set
          (rows whose response is "" are excluded as missing data)
        - ``very_disappointed``, ``somewhat_disappointed``,
          ``not_disappointed``: raw counts
        - ``very_disappointed_pct``: percentage of n in
          very_disappointed bucket
        - ``meets_threshold``: bool — True if
          very_disappointed_pct ≥ 40 (the playbook threshold)
      Empty dict if no responses recorded yet.
    """
    if bias_filter not in ("all", "exclude_owner", "owner_only"):
        raise ValueError(
            f"bias_filter must be 'all' | 'exclude_owner' | 'owner_only'"
        )
    bias_where = ""
    if bias_filter == "exclude_owner":
        bias_where = " AND COALESCE(p.is_owner_bias_flagged, 0) = 0"
    elif bias_filter == "owner_only":
        bias_where = " AND COALESCE(p.is_owner_bias_flagged, 0) = 1"

    with db_connect(db_path) as conn:
        if user_id:
            sql = (
                "SELECT m.sean_ellis_response FROM measurement_updates m "
                "JOIN predictions p ON p.prediction_id = m.prediction_id "
                "WHERE m.user_id = ? AND m.sean_ellis_response != ''"
                + bias_where
            )
            rows = conn.execute(sql, (user_id,)).fetchall()
        else:
            sql = (
                "SELECT m.sean_ellis_response FROM measurement_updates m "
                "JOIN predictions p ON p.prediction_id = m.prediction_id "
                "WHERE 1=1 AND m.sean_ellis_response != ''"
                + bias_where
            )
            rows = conn.execute(sql).fetchall()
    if not rows:
        return {}

    very = sum(1 for r in rows if r["sean_ellis_response"] == "very_disappointed")
    somewhat = sum(1 for r in rows if r["sean_ellis_response"] == "somewhat_disappointed")
    not_d = sum(1 for r in rows if r["sean_ellis_response"] == "not_disappointed")
    n = len(rows)
    very_pct = (very / n) * 100.0 if n > 0 else 0.0
    return {
        "n": n,
        "very_disappointed": very,
        "somewhat_disappointed": somewhat,
        "not_disappointed": not_d,
        "very_disappointed_pct": very_pct,
        "meets_threshold": very_pct >= 40.0,
    }


def get_effort_test_summary(
    user_id: str | None = None,
    bias_filter: str = "exclude_owner",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """v4.16 playbook-adopt — effort test (push→pull transition).

    Anthropic's playbook §4 (MVP): pre-PMF retention requires
    "heroic founder energy" pushing users; post-PMF the product
    "starts doing that work on its own." Captures whether users
    self-returned to the product over the measurement window, or
    only when the operator nudged them.

    Returns:
      Dict with:
        - n
        - self_returned, needed_reminder, did_not_return (raw counts)
        - self_returned_pct
        - leans_pull: bool — True if self_returned > 50% of n
      Empty dict if no responses.
    """
    if bias_filter not in ("all", "exclude_owner", "owner_only"):
        raise ValueError(
            f"bias_filter must be 'all' | 'exclude_owner' | 'owner_only'"
        )
    bias_where = ""
    if bias_filter == "exclude_owner":
        bias_where = " AND COALESCE(p.is_owner_bias_flagged, 0) = 0"
    elif bias_filter == "owner_only":
        bias_where = " AND COALESCE(p.is_owner_bias_flagged, 0) = 1"

    with db_connect(db_path) as conn:
        if user_id:
            sql = (
                "SELECT m.effort_test_response FROM measurement_updates m "
                "JOIN predictions p ON p.prediction_id = m.prediction_id "
                "WHERE m.user_id = ? AND m.effort_test_response != ''"
                + bias_where
            )
            rows = conn.execute(sql, (user_id,)).fetchall()
        else:
            sql = (
                "SELECT m.effort_test_response FROM measurement_updates m "
                "JOIN predictions p ON p.prediction_id = m.prediction_id "
                "WHERE 1=1 AND m.effort_test_response != ''"
                + bias_where
            )
            rows = conn.execute(sql).fetchall()
    if not rows:
        return {}

    self_r = sum(1 for r in rows if r["effort_test_response"] == "self_returned")
    needed = sum(1 for r in rows if r["effort_test_response"] == "needed_reminder")
    didnt = sum(1 for r in rows if r["effort_test_response"] == "did_not_return")
    n = len(rows)
    self_pct = (self_r / n) * 100.0 if n > 0 else 0.0
    return {
        "n": n,
        "self_returned": self_r,
        "needed_reminder": needed,
        "did_not_return": didnt,
        "self_returned_pct": self_pct,
        "leans_pull": self_pct > 50.0,
    }


def get_calibration_bias_breakdown(
    user_id: str | None = None, db_path: Path | None = None,
) -> dict[str, dict[str, float]]:
    """v4.16 P8 — return calibration aggregates for three buckets:

      - ``"all"``: every measurement (default get_calibration_aggregate)
      - ``"exclude_owner"``: only measurements on non-owner predictions
      - ``"owner_only"``: only measurements on owner-bias-flagged
        predictions

    Lets the UI show "with vs without owner data point — distribution
    shifts X → Y" so the founder-as-user bias is visible at a glance.
    Empty dicts inside the buckets when nothing matches.
    """
    return {
        "all": get_calibration_aggregate(
            user_id=user_id, db_path=db_path, bias_filter="all",
        ),
        "exclude_owner": get_calibration_aggregate(
            user_id=user_id, db_path=db_path, bias_filter="exclude_owner",
        ),
        "owner_only": get_calibration_aggregate(
            user_id=user_id, db_path=db_path, bias_filter="owner_only",
        ),
    }


def get_prediction_by_id(
    prediction_id: str,
    db_path: Path | None = None,
) -> PredictionRecord | None:
    """Iter #41 — cross-device deep-link lookup.

    Founder round-4 audit P0: `?score=<id>` URL deep-link only worked
    on the same browser session because the lookup went through
    `session_user_id()` which is a random `tester-xxxx` per anonymous
    session. A user who clicked the .ics calendar reminder from
    another device (e.g. opened from email on phone vs. predicted on
    laptop) would land on "prediction not found" — silently breaking
    the entire measurement-loop arc.

    This helper does a direct prediction_id → record lookup with NO
    user_id filter. Used by `render_measurement_update` when called
    via the `?score=<id>` deep-link path so the cross-device case
    works regardless of session state.

    Privacy posture: prediction_id is a UUID, so this is effectively
    unguessable in practice — exposing the function is no worse than
    sharing the .ics calendar invite, which already contains the id.
    Returns None when the id is unknown.
    """
    with db_connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE prediction_id = ?",
            (prediction_id,),
        ).fetchone()
        if not row:
            return None
        owner_flag = 0
        try:
            owner_flag = int(row["is_owner_bias_flagged"] or 0)
        except (IndexError, KeyError):
            owner_flag = 0
        category_id = None
        try:
            category_id = row["category_id"]
        except (IndexError, KeyError):
            category_id = None
        return PredictionRecord(
            prediction_id=row["prediction_id"],
            user_id=row["user_id"],
            scenario=row["scenario"],
            created_at=row["created_at"],
            user_input=json.loads(row["user_input_json"]),
            belief_program=json.loads(row["belief_program_json"]),
            wavefunction_snapshot=json.loads(row["wavefunction_json"]),
            joint_offdiag=json.loads(row["joint_offdiag_json"]),
            notes=row["notes"] or "",
            is_owner_bias_flagged=bool(owner_flag),
            category_id=category_id,
        )


def list_overdue_predictions(
    user_id: str,
    horizon_seconds_default: int = 90 * 86400,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Iter #33 — measurement-loop part 4: predictions past their horizon
    date without a measurement yet.

    The .ics calendar reminder (iter 23) is passive — the user has to
    actually open their calendar app at month +3 to act on it. This
    helper backs the ACTIVE complement: when the user lands in the
    Omytea app for any reason, surface a banner saying "you have
    predictions waiting to be scored".

    Returns a list of dicts (newest-overdue-first) with:
      - prediction_id, decision_label (best-effort excerpt from
        input_json.decision_options), predicted_at (unix epoch),
        horizon_label (the raw "3 months" / "6 months" string),
        due_at (unix epoch when the horizon was reached),
        scenario.

    horizon_seconds_default fallback: when input_json doesn't carry a
    `time_horizon` field, assume 3 months — better than treating it
    as never-due. Cap at one year of "lag" to avoid surfacing
    decade-old predictions if storage isn't ever cleaned.
    """
    import re as _re
    with db_connect(db_path) as conn:
        # LEFT JOIN — keep predictions with NO matching measurement row.
        # `user_input_json` is the production column name (the helper
        # I wrote earlier had a typo: `input_json`). Aliased here so
        # the local key stays `input_json` for parser-style reads.
        rows = conn.execute(
            "SELECT p.prediction_id, p.user_id, p.scenario, "
            "       p.created_at, p.user_input_json AS input_json "
            "FROM predictions p "
            "LEFT JOIN measurement_updates m "
            "  ON m.prediction_id = p.prediction_id "
            "WHERE p.user_id = ? AND m.update_id IS NULL "
            "ORDER BY p.created_at DESC",
            (user_id,),
        ).fetchall()

    now = time.time()
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            inp = json.loads(r["input_json"] or "{}")
        except Exception:
            inp = {}
        # Parse the human-readable horizon. "3 months" / "6 months" /
        # "1 year" — extract a numeric month count; fall back to the
        # default if anything looks wrong.
        horizon_label = str(inp.get("time_horizon", ""))
        months: float = 3.0
        m = _re.match(r"\s*(\d+(?:\.\d+)?)\s*(month|year|week|day)", horizon_label.lower())
        if m:
            n = float(m.group(1))
            unit = m.group(2)
            if unit == "month":
                months = n
            elif unit == "year":
                months = n * 12.0
            elif unit == "week":
                months = n / 4.345
            elif unit == "day":
                months = n / 30.44
        # Cap at 24 months so a malformed entry doesn't surface
        # decade-old predictions.
        months = max(0.25, min(months, 24.0))
        horizon_seconds = months * 30.44 * 86400
        due_at = float(r["created_at"] or 0.0) + horizon_seconds
        if due_at >= now:
            # not yet overdue — skip.
            continue
        # decision_label — best-effort.
        decision_raw = (
            inp.get("decision_options")
            or inp.get("decision")
            or ""
        )
        decision_label = str(decision_raw).split("\n")[0][:80]
        out.append({
            "prediction_id": str(r["prediction_id"]),
            "user_id": str(r["user_id"]),
            "scenario": str(r["scenario"] or ""),
            "predicted_at": float(r["created_at"] or 0.0),
            "due_at": due_at,
            "horizon_label": horizon_label,
            "decision_label": decision_label,
        })
    # Most-recent-due first so the banner shows the freshest item.
    out.sort(key=lambda d: -d["due_at"])
    return out


def list_recent_measurements_with_predictions(
    user_id: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Iter #32 — measurement-loop part 2: per-prediction diff records.

    Joins ``predictions`` and ``measurement_updates`` to return a list
    of records suitable for rendering "what you predicted vs. what
    actually happened" diff cards on the Calibration History page —
    the founder-thesis "校准记录可视化 / 当初哪些判断错了" direct
    delivery.

    Each record is a dict with keys:
      - ``prediction_id``       : str
      - ``user_id``             : str
      - ``predicted_at``        : float (unix epoch, from predictions)
      - ``observed_at``         : float (unix epoch, from measurement)
      - ``scenario``            : str   (from predictions.scenario)
      - ``decision_label``      : str   (best-effort excerpt of the
                                          user's decision_options input)
      - ``predicted_top_label`` : str   (the most-probable branch at
                                          prediction time)
      - ``predicted_top_prob``  : float in [0, 1]
      - ``actual_outcome``      : dict  (the user's reported outcome)
      - ``actual_label``        : str   (best-effort label of which
                                          branch materialized)
      - ``prob_for_actual``     : float in [0, 1] — the probability
                                  the user assigned at prediction time
                                  to the branch that actually happened.
                                  This is the single number the user
                                  most wants to see: "I gave the
                                  outcome that actually happened X%
                                  in advance".
      - ``brier``               : float | None
      - ``log_loss``            : float | None
      - ``user_satisfaction``   : int | None
      - ``user_notes``          : str

    Sorted by ``observed_at`` descending so the most recent
    measurement is first. ``limit`` caps the list; pass a larger
    value for export-style views.
    """
    with db_connect(db_path) as conn:
        q = (
            "SELECT m.update_id, m.prediction_id, m.user_id, "
            "       m.observed_at, m.actual_outcome_json, "
            "       m.calibration_json, m.user_satisfaction, "
            "       m.user_notes, p.created_at AS predicted_at, "
            "       p.scenario, p.user_input_json AS input_json, "
            "       p.wavefunction_json "
            "FROM measurement_updates m "
            "JOIN predictions p ON p.prediction_id = m.prediction_id "
        )
        params: list[Any] = []
        if user_id:
            q += "WHERE m.user_id = ? "
            params.append(user_id)
        q += "ORDER BY m.observed_at DESC LIMIT ?"
        params.append(int(limit))
        rows = conn.execute(q, params).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            wf = json.loads(r["wavefunction_json"] or "{}")
        except Exception:
            wf = {}
        try:
            actual = json.loads(r["actual_outcome_json"] or "{}")
        except Exception:
            actual = {}
        try:
            cal = json.loads(r["calibration_json"] or "{}")
        except Exception:
            cal = {}
        try:
            inp = json.loads(r["input_json"] or "{}")
        except Exception:
            inp = {}

        # Find the most-probable branch at prediction time.
        hypotheses = wf.get("hypotheses", []) or []
        top_label = ""
        top_prob = 0.0
        for h in hypotheses:
            p = float(h.get("probability", 0.0) or 0.0)
            if p > top_prob:
                top_prob = p
                top_label = str(h.get("label", ""))

        # Find which branch actually happened + its predicted prob.
        # The actual_outcome dict varies by collection form; common
        # shapes: {"outcome_branch_label": "X"} or
        # {"outcome": "X"} or {"branch": "X"}.
        actual_label = (
            actual.get("outcome_branch_label")
            or actual.get("outcome")
            or actual.get("branch")
            or actual.get("realized_branch")
            or ""
        )
        actual_label = str(actual_label) if actual_label else ""
        prob_for_actual = 0.0
        if actual_label and hypotheses:
            for h in hypotheses:
                if str(h.get("label", "")) == actual_label:
                    prob_for_actual = float(h.get("probability", 0.0) or 0.0)
                    break

        # Decision label — best-effort excerpt of the first
        # decision_options entry, truncated to 80 chars for card use.
        decision_raw = (
            inp.get("decision_options")
            or inp.get("decision")
            or ""
        )
        decision_label = str(decision_raw).split("\n")[0][:80]

        out.append({
            "prediction_id": str(r["prediction_id"]),
            "user_id": str(r["user_id"]),
            "predicted_at": float(r["predicted_at"] or 0.0),
            "observed_at": float(r["observed_at"] or 0.0),
            "scenario": str(r["scenario"] or ""),
            "decision_label": decision_label,
            "predicted_top_label": top_label,
            "predicted_top_prob": top_prob,
            "actual_outcome": actual,
            "actual_label": actual_label,
            "prob_for_actual": prob_for_actual,
            "brier": cal.get("brier"),
            "log_loss": cal.get("log_loss"),
            "user_satisfaction": r["user_satisfaction"],
            "user_notes": str(r["user_notes"] or ""),
        })
    return out


def new_prediction_id() -> str:
    return str(uuid.uuid4())


def new_update_id() -> str:
    return str(uuid.uuid4())


def new_drilldown_id() -> str:
    return str(uuid.uuid4())


def now_unix() -> float:
    return time.time()


def new_category_id() -> str:
    return str(uuid.uuid4())


def new_label_id() -> str:
    return str(uuid.uuid4())


# ============================================================
# v4.18 Stage 4 — user-organized history tree (categories + labels)
#
# The app imposes no fixed taxonomy. These functions back a Notion-
# style sidebar tree the user owns: create / rename / delete their
# own categories, assign predictions to them, and add / remove
# free-form labels on a prediction.
# ============================================================


def create_category(
    user_id: str, name: str, db_path: Path | None = None,
) -> Category:
    """Create a new user-defined category (folder)."""
    cat = Category(
        category_id=new_category_id(),
        user_id=user_id,
        name=name.strip(),
        created_at=now_unix(),
    )
    with db_connect(db_path) as conn:
        conn.execute(
            "INSERT INTO categories (category_id, user_id, name, "
            "created_at) VALUES (?, ?, ?, ?)",
            (cat.category_id, cat.user_id, cat.name, cat.created_at),
        )
        conn.commit()
    return cat


def list_categories(
    user_id: str, db_path: Path | None = None,
) -> list[Category]:
    """All categories owned by a user, oldest-first (stable order)."""
    out: list[Category] = []
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM categories WHERE user_id = ? "
            "ORDER BY created_at ASC",
            (user_id,),
        ).fetchall()
        for r in rows:
            out.append(
                Category(
                    category_id=r["category_id"],
                    user_id=r["user_id"],
                    name=r["name"],
                    created_at=r["created_at"],
                )
            )
    return out


def rename_category(
    category_id: str, new_name: str, db_path: Path | None = None,
) -> None:
    """Rename a category in place."""
    with db_connect(db_path) as conn:
        conn.execute(
            "UPDATE categories SET name = ? WHERE category_id = ?",
            (new_name.strip(), category_id),
        )
        conn.commit()


def delete_category(
    category_id: str, db_path: Path | None = None,
) -> None:
    """Delete a category. Predictions in it are NOT destroyed — their
    category_id is reset to NULL (back to uncategorized)."""
    with db_connect(db_path) as conn:
        conn.execute(
            "UPDATE predictions SET category_id = NULL "
            "WHERE category_id = ?",
            (category_id,),
        )
        conn.execute(
            "DELETE FROM categories WHERE category_id = ?",
            (category_id,),
        )
        conn.commit()


def assign_prediction_category(
    prediction_id: str,
    category_id: str | None,
    db_path: Path | None = None,
) -> None:
    """Move a prediction into a category (or out — pass None)."""
    with db_connect(db_path) as conn:
        conn.execute(
            "UPDATE predictions SET category_id = ? "
            "WHERE prediction_id = ?",
            (category_id, prediction_id),
        )
        conn.commit()


def add_label(
    prediction_id: str, label: str, db_path: Path | None = None,
) -> None:
    """Add a free-form label to a prediction. Idempotent — adding the
    same label twice is a no-op (composite-unique constraint)."""
    clean = label.strip()
    if not clean:
        return
    with db_connect(db_path) as conn:
        conn.execute(
            "INSERT INTO prediction_labels (label_id, prediction_id, "
            "label, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (prediction_id, label) DO NOTHING",
            (new_label_id(), prediction_id, clean, now_unix()),
        )
        conn.commit()


def remove_label(
    prediction_id: str, label: str, db_path: Path | None = None,
) -> None:
    """Remove a label from a prediction."""
    with db_connect(db_path) as conn:
        conn.execute(
            "DELETE FROM prediction_labels "
            "WHERE prediction_id = ? AND label = ?",
            (prediction_id, label.strip()),
        )
        conn.commit()


def list_labels(
    prediction_id: str, db_path: Path | None = None,
) -> list[str]:
    """All labels on one prediction, alphabetical."""
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT label FROM prediction_labels "
            "WHERE prediction_id = ? ORDER BY label ASC",
            (prediction_id,),
        ).fetchall()
        return [r["label"] for r in rows]


def list_user_labels(
    user_id: str, db_path: Path | None = None,
) -> list[str]:
    """Every distinct label the user has ever used, alphabetical.

    Joins prediction_labels to predictions so a label is only listed
    if it sits on one of this user's predictions.
    """
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT pl.label FROM prediction_labels pl "
            "JOIN predictions p ON p.prediction_id = pl.prediction_id "
            "WHERE p.user_id = ? ORDER BY pl.label ASC",
            (user_id,),
        ).fetchall()
        return [r["label"] for r in rows]


def labels_for_predictions(
    prediction_ids: list[str], db_path: Path | None = None,
) -> dict[str, list[str]]:
    """Batch label lookup — {prediction_id: [labels]} for many
    predictions at once (one query for the whole history rail)."""
    out: dict[str, list[str]] = {pid: [] for pid in prediction_ids}
    if not prediction_ids:
        return out
    placeholders = ",".join("?" for _ in prediction_ids)
    with db_connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT prediction_id, label FROM prediction_labels "
            f"WHERE prediction_id IN ({placeholders}) "
            f"ORDER BY label ASC",
            tuple(prediction_ids),
        ).fetchall()
        for r in rows:
            out.setdefault(r["prediction_id"], []).append(r["label"])
    return out


# ============================================================
# v4.16 P2 — Branch drill-down cache
# ============================================================


def save_drilldown(
    rec: BranchDrilldown, db_path: Path | None = None,
) -> None:
    """Persist a drill-down. INSERT-or-REPLACE on the
    (prediction_id, branch_label) composite unique key, so repeated
    drill-downs overwrite (cache refresh) rather than accumulate."""
    with db_connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO branch_drilldowns (
                drilldown_id, prediction_id, branch_label,
                created_at, drilldown_json
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (prediction_id, branch_label) DO UPDATE SET
                drilldown_id = excluded.drilldown_id,
                created_at = excluded.created_at,
                drilldown_json = excluded.drilldown_json
            """,
            (
                rec.drilldown_id,
                rec.prediction_id,
                rec.branch_label,
                rec.created_at,
                json.dumps(rec.drilldown_json, ensure_ascii=False),
            ),
        )
        conn.commit()


def get_drilldown(
    prediction_id: str,
    branch_label: str,
    db_path: Path | None = None,
) -> BranchDrilldown | None:
    """Read a cached drill-down. Returns None if not cached."""
    with db_connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM branch_drilldowns "
            "WHERE prediction_id = ? AND branch_label = ?",
            (prediction_id, branch_label),
        ).fetchone()
    if row is None:
        return None
    return BranchDrilldown(
        drilldown_id=row["drilldown_id"],
        prediction_id=row["prediction_id"],
        branch_label=row["branch_label"],
        created_at=row["created_at"],
        drilldown_json=json.loads(row["drilldown_json"]),
    )


def list_drilldowns(
    prediction_id: str, db_path: Path | None = None,
) -> list[BranchDrilldown]:
    """All cached drill-downs for one prediction, newest first."""
    out: list[BranchDrilldown] = []
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM branch_drilldowns "
            "WHERE prediction_id = ? ORDER BY created_at DESC",
            (prediction_id,),
        ).fetchall()
        for r in rows:
            out.append(BranchDrilldown(
                drilldown_id=r["drilldown_id"],
                prediction_id=r["prediction_id"],
                branch_label=r["branch_label"],
                created_at=r["created_at"],
                drilldown_json=json.loads(r["drilldown_json"]),
            ))
    return out


def delete_drilldown(
    prediction_id: str,
    branch_label: str,
    db_path: Path | None = None,
) -> int:
    """Drop one cached drill-down. Returns deleted row count."""
    with db_connect(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM branch_drilldowns "
            "WHERE prediction_id = ? AND branch_label = ?",
            (prediction_id, branch_label),
        )
        conn.commit()
        return cur.rowcount


# ============================================================
# v4.16 P6 — Entitlements + pre-order interest capture
# ============================================================


def new_entitlement_id() -> str:
    return str(uuid.uuid4())


def new_interest_id() -> str:
    return str(uuid.uuid4())


def save_entitlement(
    rec: Entitlement, db_path: Path | None = None,
) -> None:
    with db_connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO entitlements (
                entitlement_id, user_id, tier_id,
                granted_at, expires_at, source, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.entitlement_id, rec.user_id, rec.tier_id,
                rec.granted_at, rec.expires_at,
                rec.source, rec.notes,
            ),
        )
        conn.commit()


def list_user_entitlements(
    user_id: str, db_path: Path | None = None,
) -> list[Entitlement]:
    """All entitlements for a given user, newest first."""
    out: list[Entitlement] = []
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM entitlements WHERE user_id = ? "
            "ORDER BY granted_at DESC",
            (user_id,),
        ).fetchall()
        for r in rows:
            out.append(Entitlement(
                entitlement_id=r["entitlement_id"],
                user_id=r["user_id"],
                tier_id=r["tier_id"],
                granted_at=r["granted_at"],
                expires_at=r["expires_at"],
                source=r["source"] or "manual",
                notes=r["notes"] or "",
            ))
    return out


def user_has_active_entitlement(
    user_id: str,
    tier_id: str,
    now_unix_ts: float | None = None,
    db_path: Path | None = None,
) -> bool:
    """Check whether the user holds an active (non-expired) entitlement
    for the given tier."""
    now_ts = now_unix_ts if now_unix_ts is not None else time.time()
    for ent in list_user_entitlements(user_id, db_path=db_path):
        if ent.tier_id != tier_id:
            continue
        if ent.expires_at is None or ent.expires_at > now_ts:
            return True
    return False


def save_preorder_interest(
    rec: PreorderInterest, db_path: Path | None = None,
) -> None:
    with db_connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO preorder_interest (
                interest_id, user_id, tier_id,
                expressed_at, willing_to_pay_usd,
                locale, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.interest_id, rec.user_id, rec.tier_id,
                rec.expressed_at, float(rec.willing_to_pay_usd),
                rec.locale, rec.notes,
            ),
        )
        conn.commit()


def list_preorder_interest(
    tier_id: str | None = None,
    user_id: str | None = None,
    db_path: Path | None = None,
) -> list[PreorderInterest]:
    """List pre-order interest records, optionally filtered by tier
    and/or user. Newest first."""
    sql = "SELECT * FROM preorder_interest WHERE 1=1"
    params: list[Any] = []
    if tier_id is not None:
        sql += " AND tier_id = ?"
        params.append(tier_id)
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    sql += " ORDER BY expressed_at DESC"
    out: list[PreorderInterest] = []
    with db_connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        for r in rows:
            out.append(PreorderInterest(
                interest_id=r["interest_id"],
                user_id=r["user_id"],
                tier_id=r["tier_id"],
                expressed_at=r["expressed_at"],
                willing_to_pay_usd=float(r["willing_to_pay_usd"]),
                locale=r["locale"] or "",
                notes=r["notes"] or "",
            ))
    return out


def preorder_interest_summary(
    tier_id: str, db_path: Path | None = None,
) -> dict[str, float]:
    """Aggregate pre-order interest for one tier.

    Returns:
      Dict with n (count), mean_usd, median_usd, max_usd.
      Empty dict if no records.
    """
    records = list_preorder_interest(tier_id=tier_id, db_path=db_path)
    if not records:
        return {}
    amounts = sorted(r.willing_to_pay_usd for r in records)
    n = len(amounts)
    mean_usd = sum(amounts) / n
    if n % 2 == 1:
        median_usd = amounts[n // 2]
    else:
        median_usd = 0.5 * (amounts[n // 2 - 1] + amounts[n // 2])
    return {
        "n": float(n),
        "mean_usd": mean_usd,
        "median_usd": median_usd,
        "max_usd": amounts[-1],
        "min_usd": amounts[0],
    }
