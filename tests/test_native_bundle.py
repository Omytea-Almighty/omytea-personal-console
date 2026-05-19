"""Tests for the Tier 2 PyInstaller native-bundle helpers.

These don't actually run PyInstaller (that's a 1-5 minute heavy
operation, gated to ``scripts/build_native.sh`` for explicit user
invocation). They verify the helper module's API works in both
source-mode and bundle-mode, and that the .spec file parses as
valid Python.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_resolve_resource_source_mode() -> None:
    """When not running inside a PyInstaller bundle, resources
    resolve relative to the bootstrap_native.py file."""
    import bootstrap_native
    out = bootstrap_native._resolve_resource("app.py")
    assert out.endswith("app.py")
    assert os.path.isabs(out)


def test_resolve_resource_bundle_mode() -> None:
    """When PyInstaller sets sys._MEIPASS, resources resolve under it.

    Done by hand (not monkeypatch.setattr) because monkeypatch's
    teardown of a not-previously-present attribute on a module via
    delattr races with our own cleanup paths.
    """
    import bootstrap_native
    had_meipass = hasattr(sys, "_MEIPASS")
    prev = getattr(sys, "_MEIPASS", None)
    sys._MEIPASS = "/tmp/_meipass_fake"  # type: ignore[attr-defined]
    try:
        out = bootstrap_native._resolve_resource("app.py")
        assert out == os.path.join("/tmp/_meipass_fake", "app.py")
    finally:
        if had_meipass:
            sys._MEIPASS = prev  # type: ignore[attr-defined]
        else:
            try:
                del sys._MEIPASS  # type: ignore[attr-defined]
            except AttributeError:
                pass


def test_open_browser_helper_doesnt_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The browser-open helper must never raise even if the platform
    has no browser launcher (e.g. headless CI)."""
    import bootstrap_native

    called: list[str] = []

    def fake_open(url: str, new: int) -> None:
        called.append(url)

    monkeypatch.setattr("webbrowser.open", fake_open)
    # delay=0 to keep the test fast
    bootstrap_native._open_browser_after_delay("127.0.0.1", 8501, 0.0)
    assert called == ["http://127.0.0.1:8501"]


def test_open_browser_swallows_webbrowser_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If webbrowser.open raises (some headless boxes), bootstrap
    must continue without crashing."""
    import bootstrap_native

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("no browser available")

    monkeypatch.setattr("webbrowser.open", boom)
    # Should NOT raise
    bootstrap_native._open_browser_after_delay("127.0.0.1", 8501, 0.0)


def test_spec_file_parses_as_python() -> None:
    """The .spec is plain Python that PyInstaller exec()s. Make sure
    it compiles to bytecode without syntax errors."""
    repo_dir = Path(__file__).resolve().parent.parent
    spec_path = repo_dir / "omytea-console.spec"
    assert spec_path.exists()
    text = spec_path.read_text(encoding="utf-8")
    # Compile to bytecode — this is what PyInstaller does internally.
    compile(text, str(spec_path), "exec")


def test_build_script_exists_and_is_executable() -> None:
    repo_dir = Path(__file__).resolve().parent.parent
    script_path = repo_dir / "scripts" / "build_native.sh"
    assert script_path.exists()
    # On POSIX, check the executable bit.
    if os.name == "posix":
        st = os.stat(script_path)
        assert st.st_mode & 0o111 != 0, "build_native.sh must be executable"


def test_bootstrap_native_has_main_entry() -> None:
    """The bootstrap module must expose a ``main()`` so PyInstaller
    has a stable entry point."""
    import bootstrap_native
    assert callable(getattr(bootstrap_native, "main", None))
