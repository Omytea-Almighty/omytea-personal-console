"""Iter #40 phase-1 — measurement-loop helpers extracted from app.py.

Founder round-3 audit (#4): `app.py` had grown to 6208 lines covering
Streamlit UI, routing, measurement-loop, rendering, ICS, traditional
lens all in one file — a real bug-density risk (bug-038 in iter 35
was a direct symptom of that coupling).

This module is the FIRST decomposition slice — pure-Python helpers
with no Streamlit-render side-effects, no `st.*` calls except the
single `st.query_params` read in `_check_score_deeplink`. Self-
contained, easy to test, easy to reason about. Phases 2/3 will
extract the rendering layer + routing.

The four helpers moved here:
  - `_humanize_id` — snake_case → natural prose (iter 30 #4).
  - `_dt_today_plus_months` — date offset for review reminders (iter 23).
  - `_build_review_ics` — RFC 5545 .ics blob for calendar export (iter 23).
  - `_check_score_deeplink` — `?score=<id>` URL param helper (iter 31).

`app.py` re-imports them so any existing `from app import _humanize_id`
references in tests + plumbing continue to work — this is a pure
relocation, not a behavior change.
"""

from __future__ import annotations

import datetime as _dt

import streamlit as st

import _brand


# Iter #30 — humanize snake_case identifiers for user-visible display.
# Founder round-2 audit: "Why this probability? 需要更像人话: 不要只
# 列 branch id / hinge id, 应解释成 '这个概率主要因为三件事...'".
# The compile step produces snake_case fields like
# `team_culture_actual_vs_pitch` that read as dev internals when
# surfaced raw. This helper converts to natural prose on render:
#   accept_offer → "Accept the offer"
#   team_culture_actual_vs_pitch → "Team culture: actual vs. pitch"
#   stay_and_thrive_after_renegotiation → "Stay and thrive after
#       renegotiation"
def _humanize_id(identifier: str) -> str:
    """Convert a snake_case identifier to natural-language prose.

    Empty string returns empty. The transformation is deterministic:
    - Replace `_` with spaces
    - Capitalize first letter only (preserves "vs" mid-string as
      lowercase because that's the natural English form)
    - Heuristic: `_vs_` becomes ": actual vs." which reads as a
      contrast clause in user prose
    """
    if not identifier:
        return ""
    text = str(identifier).strip()
    # Special-case the common contrast pattern that appears in our
    # career scenarios: "X_actual_vs_pitch" → "X: actual vs. pitch".
    text = text.replace("_actual_vs_", ": actual vs. ")
    text = text.replace("_vs_", " vs. ")
    # Generic underscore-to-space.
    text = text.replace("_", " ")
    # First-letter cap; rest stays as written so "vs." stays lowercase.
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


# Iter #23 — review-date helpers for the measurement-update CTA. Kept
# at module scope so the function under test is straightforward and the
# ics generator is reusable by future surfaces (e.g. a "schedule
# review" button on the calibration-history page).
def _dt_today_plus_months(months: int):
    """Return today's date + ~months later. Uses 30-day months for the
    offset — accurate to a few days at 12-month horizons and avoids
    pulling python-dateutil for a single calculation. The downstream
    .ics format only needs day-precision."""
    today = _dt.date.today()
    days = max(1, int(round(float(months) * 30.44)))
    return today + _dt.timedelta(days=days)


def _build_review_ics(
    *,
    prediction_id: str,
    decision_label: str,
    review_date,
) -> bytes:
    """Return a minimal RFC 5545 .ics calendar blob for a one-day
    review reminder on the horizon date.

    Encoded fields:
      - SUMMARY: "Score your Omytea prediction"
      - DESCRIPTION: short narrative + prediction ID + deep link
        back to the demo's measurement-update tab.
      - DTSTART / DTEND: all-day event on the review date.
      - UID: derived from the prediction ID so re-downloading the
        same reminder updates the existing event rather than
        creating duplicates.

    The blob is bytes (utf-8) so it can be piped straight into a
    streamlit download_button without further encoding gymnastics.
    """
    decision_excerpt = (decision_label or "").strip().replace("\n", " · ")[:80]
    dtstart = review_date.strftime("%Y%m%d")
    dtend = (review_date + _dt.timedelta(days=1)).strftime("%Y%m%d")
    # Iter 24 follow-up: utcnow() is deprecated in py3.12+; use the
    # timezone-aware now(UTC) instead. The Z suffix on the formatted
    # output declares UTC explicitly.
    dtstamp = _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    uid = f"omytea-review-{prediction_id}@omytea-personal-console"

    # ICS escapes commas, semicolons, backslashes and newlines.
    def _esc(text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace(",", "\\,")
            .replace(";", "\\;")
            .replace("\n", "\\n")
        )
    # Iter #31 — measurement-loop deep-link. The URL field now
    # carries `?score=<prediction_id>` so the user clicking through
    # from their calendar lands DIRECTLY in Measurement Update
    # pre-loaded with this prediction, not on the new-prediction
    # composer. _check_score_deeplink() in main() catches it.
    score_url = (
        f"{_brand.BRAND_LIVE_DEMO_URL}/?embed=true&score={prediction_id}"
    )
    description = (
        "Time to score your Omytea prediction against what actually "
        "happened — that's the calibration loop. "
        f"Prediction ID: {prediction_id}. "
        "Open this link to land in the Measurement Update flow "
        f"pre-loaded with this prediction: {score_url}"
    )
    body = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Omytea Personal Console//Review Reminder//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{dtstamp}\r\n"
        f"DTSTART;VALUE=DATE:{dtstart}\r\n"
        f"DTEND;VALUE=DATE:{dtend}\r\n"
        f"SUMMARY:{_esc('Score your Omytea prediction')}"
    )
    if decision_excerpt:
        body += f" — {_esc(decision_excerpt)}"
    body += "\r\n"
    body += f"DESCRIPTION:{_esc(description)}\r\n"
    # Iter #31 — URL also carries the score deep-link so a calendar
    # app's "open URL" action lands directly in Measurement Update.
    body += f"URL:{score_url}\r\n"
    body += "TRANSP:TRANSPARENT\r\n"
    body += "END:VEVENT\r\n"
    body += "END:VCALENDAR\r\n"
    return body.encode("utf-8")


def _check_score_deeplink() -> str | None:
    """Iter #31 — measurement-loop part 1: detect `?score=<prediction_id>`
    URL param.

    The founder's product judgment (round-2 audit): the real PMF
    candidate is the closed loop "prediction → calendar reminder →
    return in N months → score against reality". Iter 23 shipped the
    .ics calendar export but the URL field in the event pointed at the
    bare app — users who clicked the reminder landed on the new-
    prediction composer, not on the measurement-update flow.

    This helper closes the loop: when the .ics-embedded URL carries
    `?score=<id>`, main() short-circuits the normal route dispatch and
    sends the user straight to the Measurement Update page pre-loaded
    with that prediction. The query param is consumed on first read
    so subsequent reruns don't re-trigger the route override.

    Returns the prediction_id string if present + non-empty, else None.
    """
    try:
        params = st.query_params
    except Exception:
        return None
    raw = params.get("score") if params else None
    if not raw:
        return None
    # query_params may return a single value or a list depending on
    # Streamlit version; normalize to the first non-empty entry.
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
    if not raw:
        return None
    pid = str(raw).strip()
    if not pid:
        return None
    # Consume the param so navigating away inside the app (clicking a
    # different sidebar entry, opening Settings, etc.) doesn't keep
    # re-routing back to score-mode. The user's address bar updates
    # but the prediction is still pre-loaded for this turn.
    try:
        del params["score"]
    except Exception:
        pass
    return pid


__all__ = [
    "_humanize_id",
    "_dt_today_plus_months",
    "_build_review_ics",
    "_check_score_deeplink",
]
