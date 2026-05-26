"""Iter #23 — regression tests for the measurement-update calendar bridge.

Locks the RFC 5545 contract of ``_build_review_ics`` so the .ics
download button on the result page never silently regresses
(empty file, malformed escapes, dropped UID, etc.). Also pins
``_dt_today_plus_months`` so the horizon-date computation stays
day-precise.

The calendar bridge is the user's path to the measurement-update
loop — it's how the calibration value lands outside the app, in
the user's actual calendar. Worth defensive tests.
"""

from __future__ import annotations

import datetime as _dt


def test_dt_today_plus_months_returns_date_after_today() -> None:
    """The helper must return a date strictly after today for any
    positive month count."""
    from app import _dt_today_plus_months

    today = _dt.date.today()
    for months in (1, 3, 6, 12, 24):
        result = _dt_today_plus_months(months)
        assert isinstance(result, _dt.date)
        assert result > today, (
            f"{months}-month horizon should land after today; got {result}"
        )


def test_dt_today_plus_months_six_months_is_about_half_a_year() -> None:
    """6 months out should land within a 10-day window of true half-year
    — the 30.44 days/month average is intentionally close-but-imprecise.
    """
    from app import _dt_today_plus_months

    today = _dt.date.today()
    result = _dt_today_plus_months(6)
    delta_days = (result - today).days
    # 6 × 30.44 = ~182.6 days; allow ±10 day wiggle for the rounding.
    assert 170 <= delta_days <= 195, (
        f"6-month horizon should be ~183 days out; got {delta_days}"
    )


def test_build_review_ics_returns_bytes() -> None:
    """The return type must be bytes — st.download_button expects
    bytes/str directly, not str-coerced."""
    from app import _build_review_ics

    review_date = _dt.date(2026, 11, 15)
    blob = _build_review_ics(
        prediction_id="abc123",
        decision_label="Take the offer",
        review_date=review_date,
    )
    assert isinstance(blob, bytes)
    assert len(blob) > 100


def test_build_review_ics_has_required_vcalendar_skeleton() -> None:
    """RFC 5545 minimum: VCALENDAR wrapper, VERSION, PRODID, one
    VEVENT inside. Without these the ics fails to import on macOS
    Calendar / Google Calendar."""
    from app import _build_review_ics

    blob = _build_review_ics(
        prediction_id="test-prediction-id",
        decision_label="Some decision",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")

    assert "BEGIN:VCALENDAR" in blob
    assert "VERSION:2.0" in blob
    assert "PRODID:" in blob
    assert "BEGIN:VEVENT" in blob
    assert "END:VEVENT" in blob
    assert "END:VCALENDAR" in blob
    # CRLF line endings per RFC 5545 §3.1.
    assert "\r\n" in blob


def test_build_review_ics_uid_derives_from_prediction_id() -> None:
    """Re-downloading the same reminder should UPDATE the existing
    calendar event (same UID), not create a duplicate. UID derivation
    from prediction_id locks that contract."""
    from app import _build_review_ics

    blob1 = _build_review_ics(
        prediction_id="prediction-xyz",
        decision_label="Decision A",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    blob2 = _build_review_ics(
        prediction_id="prediction-xyz",
        decision_label="Decision A",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    # Stamps differ each call, but UIDs must be identical.
    assert "UID:omytea-review-prediction-xyz@" in blob1
    assert "UID:omytea-review-prediction-xyz@" in blob2

    # Different prediction → different UID.
    blob3 = _build_review_ics(
        prediction_id="prediction-other",
        decision_label="Decision B",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    assert "UID:omytea-review-prediction-other@" in blob3


def test_build_review_ics_summary_includes_decision_excerpt() -> None:
    """Summary should carry the decision label (truncated) so the
    user sees what the reminder is FOR in their calendar app's
    event list — not just a generic 'Omytea review'."""
    from app import _build_review_ics

    blob = _build_review_ics(
        prediction_id="abc",
        decision_label="Take the ML engineer offer at Anthropic",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    assert "SUMMARY:" in blob
    # Decision label appears (with hyphen prefix as a separator).
    assert "Take the ML engineer" in blob


def test_build_review_ics_escapes_special_chars() -> None:
    """RFC 5545 requires escaping commas, semicolons, backslashes,
    and newlines in TEXT properties. A label with these chars must
    not break the ics — current macOS Calendar silently drops a
    malformed event."""
    from app import _build_review_ics

    blob = _build_review_ics(
        prediction_id="abc",
        decision_label="Move home, or stay; abroad",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    # Commas/semicolons inside TEXT properties must be backslash-escaped.
    # The escaped commas should appear in the output as "\,".
    assert "\\," in blob
    assert "\\;" in blob


def test_build_review_ics_dtstart_matches_review_date() -> None:
    """DTSTART;VALUE=DATE encodes the actual horizon date as
    yyyymmdd. macOS Calendar uses this to place the event."""
    from app import _build_review_ics

    blob = _build_review_ics(
        prediction_id="abc",
        decision_label="X",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    assert "DTSTART;VALUE=DATE:20261115" in blob
    # DTEND is one day later for an all-day event per RFC 5545.
    assert "DTEND;VALUE=DATE:20261116" in blob


def test_build_review_ics_description_carries_prediction_id_and_url() -> None:
    """The description should embed the prediction ID + a deep-link
    back to the public demo URL so the user can score the prediction
    when they arrive at the reminder date."""
    from app import _build_review_ics

    blob = _build_review_ics(
        prediction_id="abc-xyz-123",
        decision_label="X",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    assert "DESCRIPTION:" in blob
    assert "abc-xyz-123" in blob  # prediction ID surfaces
    # URL line should carry the canonical embed URL (iter 20).
    assert "URL:https://omytea-personal-console.streamlit.app/?embed=true" in blob


def test_build_review_ics_url_carries_score_deeplink() -> None:
    """Iter #31 — the URL field in the ics must carry the
    ?score=<prediction_id> deep-link so that opening it from the
    calendar lands the user directly in Measurement Update
    pre-loaded with that prediction (not on the new-prediction
    composer). Closes the measurement-update loop the founder
    identified as the primary PMF lever."""
    from app import _build_review_ics

    blob = _build_review_ics(
        prediction_id="loop-close-id-456",
        decision_label="X",
        review_date=_dt.date(2026, 11, 15),
    ).decode("utf-8")
    # URL field must include the &score=<id> deep-link suffix.
    assert "URL:" in blob
    assert "score=loop-close-id-456" in blob
    # Backward-compat: the description still mentions the id directly.
    assert "Prediction ID: loop-close-id-456" in blob
