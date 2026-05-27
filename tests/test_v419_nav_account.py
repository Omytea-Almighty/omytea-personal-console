"""Nav-logic cleanup + account sign-in (OMY-V415 / M2 / Acceptance #65).

The founder flagged two problems with the console shell:

  1. The "More" menu exposed 6 secondary surfaces, but 3 of them — the
     玄学 lens, video query, live webcam — ARE the main composer already
     (lens toggle / Attach / Live-video toggle). Routing to them as
     separate full pages was a redundant SECOND entry point.
  2. A secondary surface, once opened, could not be closed — there was
     no "back" affordance, only the differently-named "New prediction".

The fix: trim "More" to the genuinely-standalone surfaces, give every
non-workspace surface a "← back to workspace" bar, and add a
Claude-style account area (Google OIDC via ``st.login``) pinned to the
sidebar bottom-left.

``app.py`` cannot be imported under the test runner (module-level
``st.set_page_config`` needs a script context), so the shell shape is
checked at the AST / source level — the same technique as
``test_v418_history_rail_shell.py``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _i18n  # noqa: E402

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_SRC = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


# --------------------------------------------------------------------
# "More" trimmed to the genuinely-standalone surfaces
# --------------------------------------------------------------------

def test_secondary_modes_trimmed_to_standalone() -> None:
    """SECONDARY_MODES_ALL keeps only the surfaces with no composer home —
    outcome scoring, calibration history, pricing. The 玄学 / video /
    webcam entries (which ARE the composer) are removed.

    Iter #42 B2: `SECONDARY_MODES` is now a back-compat alias for
    `SECONDARY_MODES_ALL` (a tuple literal — the source of truth);
    at runtime the sidebar uses `_secondary_modes()` which can
    filter Pricing during beta. This test reads the literal.
    """
    modes = None
    for node in APP_TREE.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SECONDARY_MODES_ALL"
            for t in node.targets
        ):
            modes = ast.literal_eval(node.value)
    assert modes is not None, "SECONDARY_MODES_ALL not found"
    assert set(modes) == {
        "Measurement update", "Calibration history", "Pricing & pre-order",
    }
    for removed in ("Traditional × Calibrated", "Video query", "Live webcam"):
        assert removed not in modes, f"{removed} should be off the More menu"


def test_main_no_longer_routes_composer_features_as_pages() -> None:
    """main()'s ROUTE_SECONDARY branch no longer opens the
    composer-integrated 玄学 view as a standalone page."""
    main_src = ast.unparse(_func("main"))
    assert "render_traditional_view" not in main_src
    for kept in (
        "render_measurement_update",
        "render_calibration_history",
        "render_pricing_and_preorder",
    ):
        assert kept in main_src, f"{kept} must still be dispatched"


# --------------------------------------------------------------------
# every non-workspace surface is closeable (← back to workspace)
# --------------------------------------------------------------------

def test_back_bar_helper_returns_to_workspace() -> None:
    """_render_back_bar resets the route to the workspace and reruns."""
    src = ast.unparse(_func("_render_back_bar"))
    assert "ROUTE_WORKSPACE" in src
    assert "_route" in src
    assert "st.rerun()" in src


def test_secondary_surfaces_render_the_back_bar() -> None:
    """Every standalone surface — and the history viewer, which is
    render_measurement_update — calls _render_back_bar so it is always
    closeable."""
    for surface in (
        "render_measurement_update",
        "render_calibration_history",
        "render_pricing_and_preorder",
    ):
        src = ast.unparse(_func(surface))
        assert "_render_back_bar()" in src, f"{surface} has no back bar"


# --------------------------------------------------------------------
# Claude-style account area — Google OIDC sign-in
# --------------------------------------------------------------------

def test_account_helpers_exist() -> None:
    for name in ("_account_state", "_render_account_area"):
        assert f"def {name}(" in APP_SRC, f"{name} not defined"


def test_render_sidebar_mounts_the_account_area() -> None:
    assert "_render_account_area()" in ast.unparse(_func("render_sidebar"))


def test_account_area_uses_native_streamlit_auth() -> None:
    """Sign-in is real OIDC — st.login / st.logout / st.user — not a
    hand-rolled password store."""
    state_src = ast.unparse(_func("_account_state"))
    area_src = ast.unparse(_func("_render_account_area"))
    assert "st.user" in state_src
    assert "st.login()" in area_src
    assert "st.logout()" in area_src


def test_account_state_degrades_without_oidc_secrets() -> None:
    """Until [auth] is configured the app must not crash — _account_state
    catches the missing-secrets error and reports 'disabled'."""
    src = ast.unparse(_func("_account_state"))
    assert "disabled" in src
    assert "except" in src


def test_session_user_id_prefers_the_signed_in_account() -> None:
    """A signed-in account owns its history — session_user_id keys off
    the account email when logged in."""
    src = ast.unparse(_func("session_user_id"))
    assert "st.user" in src
    assert "email" in src


# --------------------------------------------------------------------
# i18n — the new keys are complete in all four languages
# --------------------------------------------------------------------

def test_new_nav_and_account_i18n_keys_present() -> None:
    for key in (
        "nav.back_workspace",
        "account.login",
        "account.login_hint",
        "account.logout",
        "account.not_configured",
    ):
        assert key in _i18n.TRANSLATIONS, f"missing i18n key: {key}"
        entry = _i18n.TRANSLATIONS[key]
        for lang in _i18n.SUPPORTED_LANGS:
            assert lang in entry and str(entry[lang]).strip()
