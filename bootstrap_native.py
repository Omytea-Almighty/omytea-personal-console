"""Native launcher for the Omytea Personal Future Console.

This is the entry point PyInstaller compiles into the standalone
binary. When a user double-clicks the bundled app, this script:

  1. Resolves the bundled ``app.py`` path (PyInstaller stores assets
     under ``sys._MEIPASS`` at runtime, so we use the bundle-aware
     ``_resolve_resource`` helper).
  2. Programmatically runs Streamlit via its ``bootstrap.run`` API,
     bound to ``127.0.0.1`` only (never exposed externally).
  3. Spawns a daemon thread that opens the user's default browser
     to ``http://127.0.0.1:8501`` after a short delay.

Tier 2 native packaging objective per
``DELIVERABLE_PLAN.md``: users should be able to download a single
folder bundle and run the Console without any Python install. The
bundle still requires Ollama for the vision LLM (vision models are
several GB and out of scope for embedding), so the first-run UX
includes a "Ollama not detected" hint when applicable — but the
Console UI itself launches and is usable in mock mode without Ollama.

Master plan §10 multi-substrate portability: this launcher does
nothing platform-specific beyond ``webbrowser.open()`` — the same
script supports macOS, Linux, and (with PyInstaller built on
Windows) Windows binaries.

Why not ``streamlit run`` directly? PyInstaller's bundle doesn't
expose the ``streamlit`` CLI as a binary on PATH, and shelling out
to it would re-spawn Python which defeats the point. Programmatic
``bootstrap.run`` keeps everything in the same process.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser


def _resolve_resource(name: str) -> str:
    """Resolve a bundled resource path.

    When PyInstaller runs the bundle, it sets ``sys._MEIPASS`` to
    the runtime extraction directory. When running from source for
    development, fall back to the directory of this file.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, name)  # type: ignore[attr-defined]
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, name)


def _open_browser_after_delay(host: str, port: int, delay: float) -> None:
    """Wait briefly, then open the user's default browser.

    The delay accounts for Streamlit's bind-and-serve latency. If
    ``webbrowser.open`` fails (headless environment), it's a
    no-op — the user can still navigate manually."""
    time.sleep(delay)
    url = f"http://{host}:{port}"
    try:
        webbrowser.open(url, new=1)
    except Exception:
        pass


def main() -> None:
    # ---- Set Streamlit config via env vars BEFORE importing the
    # streamlit module. The flag_options arg of bootstrap.run is
    # observed inconsistently across streamlit versions; env vars
    # are read at config-import time which makes them the most
    # reliable channel.
    #
    # Security: bind to loopback only. The bundle is desktop
    # software — exposing the Streamlit server on 0.0.0.0 would
    # let anyone on the user's local network read their predictions.
    os.environ.setdefault("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
    os.environ.setdefault("STREAMLIT_SERVER_PORT", "8501")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    # Privacy first — opt the user out of telemetry by default.
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    # Allow generous video upload sizes; users may try real videos.
    os.environ.setdefault("STREAMLIT_SERVER_MAX_UPLOAD_SIZE", "200")

    # ---- Belt-and-suspenders: also call the Python-level set_option
    # API after import, since some streamlit versions read env vars
    # only at module-import (which has happened by the time the user
    # script runs) and others read them lazily.
    from streamlit import config as stconfig  # noqa: WPS433
    from streamlit.web import bootstrap  # noqa: WPS433
    stconfig.set_option("server.address", "127.0.0.1")
    stconfig.set_option("server.port", 8501)
    stconfig.set_option("server.headless", True)
    stconfig.set_option("browser.gatherUsageStats", False)
    stconfig.set_option("server.maxUploadSize", 200)

    app_path = _resolve_resource("app.py")

    flag_options: dict[str, object] = {
        "server.address": "127.0.0.1",
        "server.port": 8501,
        "server.headless": True,
        "browser.gatherUsageStats": False,
        "server.maxUploadSize": 200,
    }

    # Open the browser in a daemon thread so it happens after
    # Streamlit binds.
    threading.Thread(
        target=_open_browser_after_delay,
        args=("127.0.0.1", 8501, 2.0),
        daemon=True,
    ).start()

    sys.argv = ["streamlit", "run", app_path]
    # Note: streamlit's bootstrap.run signature varies across versions.
    # Older: run(main_script_path, command_line, args, flag_options)
    # Newer: run(main_script_path, is_hello, args, flag_options)
    # An empty string in arg 2 is falsy, satisfying both bool and str
    # contracts — works on both signatures.
    bootstrap.run(app_path, "", [], flag_options)


if __name__ == "__main__":
    main()
