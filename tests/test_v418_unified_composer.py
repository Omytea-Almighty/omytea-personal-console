"""Stage 2 — unified composer (OMY-V415 / M2 / Acceptance #53).

The "More" surfaces merge into one workspace composer: text conditions
+ a "+" file attach + a live-video toggle + a 玄学-lens toggle + one
"Run prediction". Video query → an attached video; Live webcam → a
toggle. It borrows only the "one composer + attach" affordance — it is
explicitly NOT a turn-by-turn chatbox.

``app.py`` cannot be imported under the test runner (module-level
``st.set_page_config``), so the composer contract is checked at the
AST / source level, the same technique the Stage 1 test uses.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_SRC = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SRC)

I18N_SRC = (
    Path(__file__).resolve().parent.parent / "_i18n.py"
).read_text(encoding="utf-8")


def _func(name: str) -> ast.FunctionDef:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in app.py")


# --------------------------------------------------------------------
# The composer lives inside render_new_prediction
# --------------------------------------------------------------------

def test_composer_has_attach_affordance() -> None:
    """A "+" attach popover with a video uploader sits in the composer."""
    src = ast.unparse(_func("render_new_prediction"))
    assert "st.popover" in src, "composer needs a '+' attach popover"
    assert "_composer_video" in src, "attach popover needs a video uploader"


def test_composer_has_live_video_toggle() -> None:
    """Live webcam becomes a toggle, not a separate mode page."""
    src = ast.unparse(_func("render_new_prediction"))
    assert "_composer_live_toggle" in src
    assert "st.toggle" in src


def test_composer_has_xuanxue_lens_toggle() -> None:
    """The 玄学 lens is an optional toggle inside the workspace."""
    src = ast.unparse(_func("render_new_prediction"))
    assert "_composer_lens_toggle" in src
    # The toggle state must be published for _render_result to read.
    assert "_xuanxue_lens_on" in src


def test_composer_embeds_video_pipeline() -> None:
    """An attached video runs the video pipeline inline (embedded)."""
    src = ast.unparse(_func("render_new_prediction"))
    assert "render_video_query(embedded=True)" in src


def test_composer_embeds_live_pipeline() -> None:
    """The live toggle embeds the webcam panel inline (embedded)."""
    src = ast.unparse(_func("render_new_prediction"))
    assert "render_live_webcam(embedded=True)" in src


def test_composer_still_has_run_prediction_form() -> None:
    """The text-conditions form + a single Generate button survive."""
    src = ast.unparse(_func("render_new_prediction"))
    assert "st.form" in src
    assert "form_submit_button" in src


# --------------------------------------------------------------------
# Secondary render functions gained the `embedded` parameter
# --------------------------------------------------------------------

def test_video_query_accepts_embedded_flag() -> None:
    fn = _func("render_video_query")
    arg_names = [a.arg for a in fn.args.args]
    assert "embedded" in arg_names
    assert fn.args.defaults, "embedded must default (standalone still works)"


def test_live_webcam_accepts_embedded_flag() -> None:
    fn = _func("render_live_webcam")
    arg_names = [a.arg for a in fn.args.args]
    assert "embedded" in arg_names
    assert fn.args.defaults, "embedded must default (standalone still works)"


def _first_real_stmt(fn: ast.FunctionDef) -> ast.stmt:
    """First statement of a function body, skipping the docstring."""
    body = list(fn.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    assert body, "function body is empty"
    return body[0]


def test_embedded_suppresses_video_hero() -> None:
    """When embedded, the standalone hero markdown is gated off.

    The hero must sit under `if not embedded:` so the composer panel
    doesn't show a giant duplicate title.
    """
    first = _first_real_stmt(_func("render_video_query"))
    assert isinstance(first, ast.If), "video hero must be embedded-gated"
    assert "embedded" in ast.unparse(first.test)
    # The gated block must actually contain the hero markdown call.
    assert "st.markdown" in ast.unparse(first)


def test_embedded_suppresses_webcam_hero() -> None:
    first = _first_real_stmt(_func("render_live_webcam"))
    assert isinstance(first, ast.If), "webcam hero must be embedded-gated"
    assert "embedded" in ast.unparse(first.test)
    assert "st.markdown" in ast.unparse(first)


# --------------------------------------------------------------------
# _render_result honors the composer's 玄学-lens toggle
# --------------------------------------------------------------------

def test_render_result_reads_lens_toggle() -> None:
    """The lens expander opens expanded only when the toggle is on."""
    src = ast.unparse(_func("_render_result"))
    assert "_xuanxue_lens_on" in src
    assert "expanded=lens_on" in src


# --------------------------------------------------------------------
# i18n coverage — every composer key exists in all four languages
# --------------------------------------------------------------------

def test_composer_i18n_keys_present() -> None:
    for key in (
        "composer.section",
        "composer.attach",
        "composer.live",
        "composer.lens",
        "composer.scenario",
    ):
        assert f'"{key}"' in I18N_SRC, f"missing i18n key {key}"
