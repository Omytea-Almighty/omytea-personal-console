"""Stage 1 — history-rail shell (OMY-V415 / M2 / Acceptance #52).

The console's IA was rewritten from 7 sidebar modes into a ChatGPT-shaped
shell: brand → New prediction → a date-grouped history of past
predictions → a "More" expander for secondary surfaces → Settings →
footer. ``render_sidebar()`` returns a route tuple; ``main()`` dispatches
it.

These tests pin that contract. ``app.py`` cannot be imported under the
test runner (module-level ``st.set_page_config`` needs a Streamlit
script context, and Streamlit is not a test-env dependency), so the
shell shape is checked at the AST / source level — the same technique
``test_render_result_unbound_regression.py`` uses. The pure helper
logic (``_date_bucket``, ``_history_item_label``) is exercised by
exec-ing the extracted function source against a tiny stub.
"""

from __future__ import annotations

import ast
import sys
import time
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage  # noqa: E402

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_SRC = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


# --------------------------------------------------------------------
# Route contract — render_sidebar returns a tuple, main dispatches it
# --------------------------------------------------------------------

def test_route_constants_defined() -> None:
    """The three route kinds are module-level string constants."""
    for const in ("ROUTE_WORKSPACE", "ROUTE_HISTORY", "ROUTE_SECONDARY"):
        assert f"{const} = " in APP_SRC, f"{const} not defined"


def test_render_sidebar_returns_tuple_annotation() -> None:
    """render_sidebar's signature must promise a route tuple, not a str.

    The old shell returned a bare mode string; the new shell returns
    (kind, payload). The annotation is the machine-checkable contract.
    """
    fn = _func("render_sidebar")
    assert fn.returns is not None
    ann = ast.unparse(fn.returns)
    assert "tuple" in ann.lower(), f"expected tuple return, got {ann}"


def test_render_sidebar_returns_route_value() -> None:
    """render_sidebar's last statement returns the assembled route."""
    fn = _func("render_sidebar")
    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
    assert returns, "render_sidebar has no return"
    assert any(
        isinstance(r.value, ast.Name) and r.value.id == "route"
        for r in returns
    ), "render_sidebar should return the `route` tuple"


def test_main_dispatches_by_route_kind() -> None:
    """main() unpacks the route tuple and branches on the kind."""
    fn = _func("main")
    src = ast.unparse(fn)
    assert "render_sidebar()" in src
    assert "ROUTE_HISTORY" in src
    assert "ROUTE_SECONDARY" in src
    # The default fall-through must still reach the composer.
    assert "render_new_prediction()" in src


def test_main_routes_history_into_measurement_update() -> None:
    """A history-rail click opens the measurement-update viewer.

    Per the redesign spec, render_measurement_update *is* the
    past-prediction viewer; history routes there pre-loaded by id.
    """
    fn = _func("main")
    src = ast.unparse(fn)
    assert "render_measurement_update(preloaded_prediction_id=" in src


def test_measurement_update_accepts_preloaded_id() -> None:
    """render_measurement_update gained an optional preloaded id param."""
    fn = _func("render_measurement_update")
    arg_names = [a.arg for a in fn.args.args]
    assert "preloaded_prediction_id" in arg_names
    # It must be optional (a default exists) so the standalone surface
    # still works with no argument.
    assert fn.args.defaults, "preloaded_prediction_id must have a default"


def test_session_user_id_helper_exists() -> None:
    """A single session-stable user id feeds both composer and rail."""
    assert "def session_user_id()" in APP_SRC
    # render_new_prediction must use the shared helper, not re-roll its
    # own random handle (that would desync the rail from saved records).
    fn = _func("render_new_prediction")
    assert "session_user_id()" in ast.unparse(fn)


def test_all_seven_legacy_surfaces_still_reachable() -> None:
    """No feature dropped — every legacy render_* stays wired in main()."""
    main_src = ast.unparse(_func("main"))
    for surface in (
        "render_new_prediction",
        "render_traditional_view",
        "render_video_query",
        "render_live_webcam",
        "render_measurement_update",
        "render_calibration_history",
        "render_pricing_and_preorder",
    ):
        assert surface in main_src, f"{surface} no longer reachable"


# --------------------------------------------------------------------
# Pure helper logic — exec the extracted source against a stub
# --------------------------------------------------------------------

def _load_helper(name: str) -> object:
    """Exec a single app.py helper in an isolated namespace.

    Only pure helpers (no Streamlit calls) can be loaded this way.
    ``T`` is the real _i18n.T; ``storage`` is the real module.
    """
    import _i18n

    fn = _func(name)
    ns: dict = {
        "T": _i18n.T,
        "storage": storage,
        "Any": object,
    }
    exec(  # noqa: S102 — test-only, source is our own file
        compile(ast.Module(body=[fn], type_ignores=[]), "<app-helper>", "exec"),
        ns,
    )
    return ns[name]


def test_date_bucket_today() -> None:
    bucket = _load_helper("_date_bucket")
    assert bucket(time.time()) == "Today"


def test_date_bucket_yesterday() -> None:
    bucket = _load_helper("_date_bucket")
    assert bucket(time.time() - 26 * 3600) == "Yesterday"


def test_date_bucket_prev_7_and_30() -> None:
    bucket = _load_helper("_date_bucket")
    assert bucket(time.time() - 3 * 86400) == "Previous 7 days"
    assert bucket(time.time() - 14 * 86400) == "Previous 30 days"


def test_date_bucket_old_falls_to_year_month() -> None:
    """Anything older than 30 days groups by a YYYY-MM stamp."""
    bucket = _load_helper("_date_bucket")
    label = bucket(time.time() - 200 * 86400)
    assert len(label) == 7 and label[4] == "-"


def _make_record(user_input: dict, scenario: str = "career_decision"):
    return storage.PredictionRecord(
        prediction_id="abcdef0123456789",
        user_id="tester-x",
        scenario=scenario,
        created_at=time.time(),
        user_input=user_input,
        belief_program={},
        wavefunction_snapshot={},
        joint_offdiag={},
    )


def test_history_label_prefers_human_field() -> None:
    label_fn = _load_helper("_history_item_label")
    rec = _make_record({"current_role": "Senior backend engineer"})
    assert label_fn(rec) == "Senior backend engineer"


def test_history_label_truncates_long_text() -> None:
    label_fn = _load_helper("_history_item_label")
    rec = _make_record({"question": "x" * 80})
    label = label_fn(rec)
    assert len(label) <= 38 and label.endswith("…")


def test_history_label_falls_back_to_scenario() -> None:
    """An empty input never yields a blank row."""
    label_fn = _load_helper("_history_item_label")
    rec = _make_record({}, scenario="career_decision")
    label = label_fn(rec)
    assert "career decision" in label
    assert "abcdef" in label


def test_history_label_ignores_non_string_fields() -> None:
    label_fn = _load_helper("_history_item_label")
    rec = _make_record({"current_role": 123, "question": "Real question"})
    assert label_fn(rec) == "Real question"
