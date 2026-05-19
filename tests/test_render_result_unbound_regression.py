"""Regression: `_render_result` must not leak unbound locals.

2026-05-19 bug:
    File "app.py", line 856, in _render_result
        f"with prediction ID `{rec.prediction_id}`."
    UnboundLocalError: cannot access local variable 'rec' where it is not
    associated with a value

The `rec` variable was only created inside `if prediction_id is None:`,
but the function's downstream code referenced `rec.prediction_id`
unconditionally. When the caller passed a non-None `prediction_id`
(the standard path post-v4.16 P2 refactor that landed in
render_new_prediction), the `rec = storage.PredictionRecord(...)`
block was skipped — and the downstream `rec.prediction_id` raised
UnboundLocalError.

This test pins the function's f-string + identifier surface so the bug
can't silently come back.

Note: we don't call _render_result with Streamlit's full machinery
(needs a Streamlit runtime); we use a source-level AST + grep check
on the function body. Cheap, reliable, sidesteps the Streamlit-test-
runner dependency.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path


def _read_render_result_source() -> str:
    """Pull the source text of `_render_result` out of app.py.

    We do this via filesystem read (not by importing app, which pulls
    in the full Streamlit stack). Keeps the test hermetic + fast."""
    app_py = Path(__file__).resolve().parent.parent / "app.py"
    text = app_py.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "_render_result"
        ):
            return ast.get_source_segment(text, node) or ""
    raise AssertionError("_render_result not found in app.py")


def test_render_result_does_not_reference_rec_after_conditional_block() -> None:
    """`rec` is defined only inside `if prediction_id is None:`; outside
    that branch the function must use `prediction_id` (which is
    guaranteed populated) instead.

    Specifically: after the conditional block ends, NO bare `rec`
    identifier reference should remain in the function body."""
    source = _read_render_result_source()
    tree = ast.parse(source).body[0]
    assert isinstance(tree, ast.FunctionDef)

    # Find the `if prediction_id is None:` block — `rec` is bound inside it.
    rec_binding_block_end_lineno: int | None = None
    for stmt in tree.body:
        if not isinstance(stmt, ast.If):
            continue
        cond = stmt.test
        if (
            isinstance(cond, ast.Compare)
            and isinstance(cond.left, ast.Name)
            and cond.left.id == "prediction_id"
            and len(cond.ops) == 1
            and isinstance(cond.ops[0], ast.Is)
            and len(cond.comparators) == 1
            and isinstance(cond.comparators[0], ast.Constant)
            and cond.comparators[0].value is None
        ):
            # Found `if prediction_id is None:` — last stmt of its body
            # ends the rec-binding region.
            if stmt.body:
                rec_binding_block_end_lineno = stmt.body[-1].end_lineno

    assert rec_binding_block_end_lineno is not None, (
        "Could not find the `if prediction_id is None:` block in "
        "_render_result — refactor likely changed shape; update this "
        "regression test to match new structure."
    )

    # Walk function body and find any `rec` identifier reference whose
    # line number is AFTER the conditional block. Those are the bug
    # surface — they must not exist.
    leaked_refs: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "rec":
            if node.lineno > rec_binding_block_end_lineno:
                leaked_refs.append((node.lineno, ast.dump(node)))
        if isinstance(node, ast.Attribute):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "rec"
                and node.lineno > rec_binding_block_end_lineno
            ):
                leaked_refs.append(
                    (node.lineno, f"rec.{node.attr}")
                )

    assert not leaked_refs, (
        f"`rec` identifier referenced outside the `if prediction_id is "
        f"None:` block (this caused the 2026-05-19 friend-tester "
        f"UnboundLocalError). Leaked references at lines: {leaked_refs}. "
        f"Use the `prediction_id` local instead — it's guaranteed "
        f"populated in both branches."
    )


def test_render_result_signature_has_prediction_id_param() -> None:
    """The fix relies on `prediction_id` being a function parameter
    (so it's always in scope). Pin that contract."""
    source = _read_render_result_source()
    tree = ast.parse(source).body[0]
    assert isinstance(tree, ast.FunctionDef)
    arg_names = [a.arg for a in tree.args.args]
    assert "prediction_id" in arg_names, (
        "_render_result must accept `prediction_id` as a parameter "
        "for the post-v4.16 P2 caller path to work."
    )


def test_render_result_footer_uses_prediction_id_local() -> None:
    """The come-back-later info banner must format `{prediction_id}`
    (the function parameter) somewhere in its body — that's the marker
    that the fix landed.

    The "no rec.X outside the conditional block" invariant is covered
    more rigorously by `test_render_result_does_not_reference_rec_after_
    conditional_block` above; this test is the lighter-weight sanity
    that the prediction_id local IS in use.
    """
    source = _read_render_result_source()
    assert "{prediction_id}" in source, (
        "Expected the fix to format `{prediction_id}` somewhere in "
        "the function body (likely the come-back-later nudge). "
        "If the wording changed, double-check the right local is "
        "being referenced."
    )
