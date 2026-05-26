"""Iter #37 — regression tests for `_check_score_deeplink`.

This helper (iter 31) is the load-bearing entry point for the
measurement-loop's calendar-→-Measurement-Update hop. The .ics
calendar reminder embeds a `?score=<prediction_id>` URL; when the
user clicks through, main() calls `_check_score_deeplink` to pick
up that param and route directly to the score flow.

If a future refactor silently broke this helper, the entire
measurement-loop arc (iter 23 / 31 / 32 / 33 / 34 / 35) would
fail at the most critical hop — and `py_compile` / `import`
wouldn't catch it (same bug class as iter 35's `_connect` typo).

These tests pin the helper's contract using a fake `st.query_params`
implementation that mirrors the dict-like API Streamlit exposes.
"""

from __future__ import annotations

import pytest


class _FakeQueryParams:
    """Mirror enough of `st.query_params` for the helper to read.

    Modern Streamlit's `st.query_params` supports both dict-style
    `.get(key)` returning a single str, and list-form returns on
    some older Streamlit versions. The helper tolerates both — these
    tests exercise both paths.
    """

    def __init__(self, mapping: dict | None = None, *, list_form: bool = False):
        self._data = dict(mapping or {})
        self._list_form = list_form

    def __bool__(self) -> bool:
        return bool(self._data)

    def get(self, key, default=None):
        if key not in self._data:
            return default
        val = self._data[key]
        if self._list_form:
            return [val] if not isinstance(val, list) else val
        return val

    def __contains__(self, key) -> bool:
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key) -> None:
        del self._data[key]


def _set_fake_query_params(monkeypatch, mapping, *, list_form: bool = False):
    """Replace st.query_params with the fake for the duration of one test."""
    import streamlit as st

    monkeypatch.setattr(
        st, "query_params", _FakeQueryParams(mapping, list_form=list_form),
        raising=False,
    )


def test_check_score_deeplink_returns_none_when_no_param(monkeypatch) -> None:
    """No `?score=` in the URL → helper returns None and main()
    falls through to the normal route dispatch."""
    from app import _check_score_deeplink

    _set_fake_query_params(monkeypatch, {})
    assert _check_score_deeplink() is None


def test_check_score_deeplink_returns_id_when_param_present(
    monkeypatch,
) -> None:
    """`?score=<id>` → helper returns the trimmed id so main() can
    short-circuit to render_measurement_update."""
    from app import _check_score_deeplink

    _set_fake_query_params(monkeypatch, {"score": "my-prediction-id"})
    assert _check_score_deeplink() == "my-prediction-id"


def test_check_score_deeplink_consumes_param_so_no_loop(
    monkeypatch,
) -> None:
    """After a successful read the helper MUST delete the param —
    otherwise every rerun re-routes back to score mode and the user
    can't navigate away. This is the "consume on first read" contract.
    """
    from app import _check_score_deeplink

    import streamlit as st
    fake = _FakeQueryParams({"score": "pid-a"})
    monkeypatch.setattr(st, "query_params", fake, raising=False)
    first = _check_score_deeplink()
    assert first == "pid-a"
    # Second call: param is gone, returns None.
    second = _check_score_deeplink()
    assert second is None
    assert "score" not in fake._data


def test_check_score_deeplink_handles_list_form_param(monkeypatch) -> None:
    """Older Streamlit versions return list values for query params.
    The helper must accept `["pid"]` shape and extract the first
    non-empty element."""
    from app import _check_score_deeplink

    _set_fake_query_params(
        monkeypatch, {"score": "pid-list-form"}, list_form=True,
    )
    assert _check_score_deeplink() == "pid-list-form"


def test_check_score_deeplink_returns_none_for_empty_string(
    monkeypatch,
) -> None:
    """`?score=` with empty value → None, not empty-string.
    Otherwise main() would try to load a prediction with id="".
    """
    from app import _check_score_deeplink

    _set_fake_query_params(monkeypatch, {"score": ""})
    assert _check_score_deeplink() is None


def test_check_score_deeplink_strips_whitespace(monkeypatch) -> None:
    """`?score=%20pid%20` (URL-encoded whitespace) decodes to
    `' pid '`. Helper must strip — the storage layer keys on
    exact prediction_id strings."""
    from app import _check_score_deeplink

    _set_fake_query_params(monkeypatch, {"score": "  whitespace-pid  "})
    assert _check_score_deeplink() == "whitespace-pid"


# Note: an earlier draft included a test asserting the helper
# returns None on ANY exception during query_params interaction.
# Removed because the helper's try/except is intentionally narrow —
# it wraps `params = st.query_params` (the descriptor access) only.
# Wider exception swallowing would hide real bugs in production,
# and the narrow contract is the correct one. The 7 tests above
# cover the real contract: present id, absent param, list-form,
# empty-string, whitespace-strip, consume-on-first-read.


def test_check_score_deeplink_uses_iter_31_contract(monkeypatch) -> None:
    """End-to-end smoke: the `URL:` field in the iter 23 .ics blob
    carries `?embed=true&score=<id>` (iter 31). If a user navigates
    to that URL, `?score=<id>` is the param. Verify the helper
    extracts the id correctly when the param value resembles a
    realistic UUID-like prediction_id."""
    from app import _check_score_deeplink

    realistic_id = "abc12345-de67-8901-fghi-jklm23456789"
    _set_fake_query_params(monkeypatch, {"score": realistic_id})
    assert _check_score_deeplink() == realistic_id
