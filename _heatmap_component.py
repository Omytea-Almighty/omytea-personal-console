"""Embedded interactive heatmap + camera component (v10 port).

[OMY-V415 / M2 / Acceptance #59] Live heatmap+camera for the Console.

This module ports the v10 marketing demo's **"see both at once"** heatmap
+ camera + motion-loop into the Omytea Personal Console as an embedded
HTML/JS component rendered via ``st.components.v1.html``.

What it reproduces from
``marketing/console/Omytea Console v10 — see both at once.html``:

* **Camera drives the math** — a hidden 80×45 canvas grabs a video frame
  ~10 fps, pixel-diffs it against the previous frame, sums motion mass
  per column, derives a weighted motion centroid + intensity, and feeds
  that into the heatmap distribution function. The heatmap updates LIVE
  and continuously — no submit click. A motion overlay ring tracks the
  centroid on the video; a motion status badge reports state.
* **See both at once** — when a video source is active, the camera
  preview and the heatmap sit SIDE BY SIDE in one frame (preview
  sticky). On narrow viewports the layout collapses to a single column.
* **Interactive, precise cells** — every heatmap cell has a hover
  highlight; clicking a cell opens a popover with the cell number + a
  plain-English reading. Branch × time grid, NOW → HORIZON axis.
* **Smooth loop** — ~100 ms tick, EMA smoothing (α=0.55), lazy
  re-render (skip the SVG rebuild on sub-threshold deltas).

Camera-in-iframe honesty
------------------------
``st.components.v1.html`` renders the component inside a sandboxed
iframe. Streamlit's component iframe does **not** carry an
``allow="camera"`` permission attribute, and ``html()`` exposes no API
to add one — so a *live* ``getUserMedia`` call inside this component is
blocked by the browser's Permissions Policy in most setups. We do NOT
ship a dead camera button:

* The **uploaded-video** pixel-diff path works in ANY iframe (it never
  calls ``getUserMedia`` — it diffs frames of a ``<video>`` the user
  picked with a file input). This is the always-working live driver and
  is wired fully.
* The component still *attempts* ``getUserMedia`` when the user clicks
  "Use my camera"; if the Permissions Policy blocks it the component
  surfaces an honest inline message ("the live webcam is blocked inside
  this embedded panel — use the *Live webcam* tab, or drop a video
  file here") rather than a silently-hollow button.
* For genuine live webcam capture the Console already depends on
  ``streamlit-webrtc`` (see ``render_live_webcam``); that surface is the
  sanctioned live path and is unaffected by this component.

The server-side prediction's branch distribution is passed in as JSON
(:func:`branches_to_payload`); when present the heatmap renders the real
distribution sharpening uniform → predicted across the horizon. Idle
(no prediction, no video) renders a calm uniform grid.
"""

from __future__ import annotations

import html as _html
import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from _i18n import T

__all__ = [
    "branches_to_payload",
    "render_heatmap_camera_component",
    "render_live_video_v10",
    "LIVE_VIDEO_V10_FILE",
]

# The v10 marketing demo — a complete HTML/JS app: camera + pixel-diff
# motion loop + live heatmap + see-both-at-once layout. Kept verbatim in
# ``static/``; ``render_live_video_v10`` embeds it but SCOPES it down to
# just the see-both-at-once panel (camera | heatmap) — see _V10_EMBED_SCOPE.
LIVE_VIDEO_V10_FILE = "live_video_v10.html"
_V10_PATH = Path(__file__).resolve().parent / "static" / LIVE_VIDEO_V10_FILE

# Embedded-iframe pixel height. Sized to sit inside the workspace output
# pane (one-screen layout) without the pane itself scrolling.
_LIVE_VIDEO_HEIGHT = 392

# CSS injected into the embedded v10 copy so the console surfaces ONLY
# v10's "see-both-at-once" panel — the camera preview beside the quantum
# heatmap. v10's own onboarding chrome (scenario picker, branding topbar,
# upload card, info drawers, now-banner) is hidden: the console composer
# owns ALL prediction input, so the output region must hold output only.
# v10's side-by-side grid normally needs >=1100px; the console embeds it
# narrower, so the grid is forced on here regardless of width.
_V10_EMBED_SCOPE = """
<style id="omytea-embed-scope">
.topbar,#scenario-card,#input-file,#input-scenario,
.now-banner,.hero-head,.more-row,footer.footer{display:none!important;}
main{max-width:none!important;margin:0!important;padding:12px 14px!important;}
body.camera-active main{display:grid!important;
 grid-template-columns:minmax(240px,38%) 1fr!important;
 gap:16px!important;max-width:none!important;}
/* once the camera runs, the "Use my camera" start card is redundant —
 hide it so the grid is exactly camera | heatmap, side by side. */
body.camera-active .input-row{display:none!important;}
#preview-card{top:0!important;}
.input-row{justify-content:center!important;}
#input-camera{max-width:460px!important;}
body{background:#0a0c11!important;}
@media (max-width:560px){
 body.camera-active main{grid-template-columns:1fr!important;}}
</style>
"""


def branches_to_payload(hypotheses: list[Any]) -> list[dict[str, Any]]:
    """Project ``ConsoleHypothesis`` objects to the component's JSON shape.

    Only the three fields the JS heatmap needs are exported: the branch
    ``label``, its calibrated ``probability``, and the ``branch_type``
    (drives the row dot colour — wishful / worst / realistic). This keeps
    the component payload minimal and avoids leaking internal structure
    into the browser.
    """
    payload: list[dict[str, Any]] = []
    for h in hypotheses:
        try:
            prob = max(0.0, float(getattr(h, "probability", 0.0)))
        except (TypeError, ValueError):
            prob = 0.0
        label = (getattr(h, "label", "") or "").strip()
        btype = str(getattr(h, "branch_type", "realistic"))
        if btype not in ("wishful", "worst", "realistic"):
            btype = "realistic"
        payload.append(
            {"label": label, "probability": prob, "branch_type": btype}
        )
    return payload


def _v10_srcdoc() -> str | None:
    """Read the v10 app, scope it to the see-both panel, escape for srcdoc.

    Returns ``None`` if the static file is missing (a deploy fault).

    Two transforms:

    1. ``_V10_EMBED_SCOPE`` is injected before ``</body>`` so the embed
       shows only v10's camera | heatmap see-both-at-once panel — v10's
       own onboarding chrome is hidden (the console composer owns input).
    2. The result is escaped for a double-quoted ``srcdoc`` attribute
       (:func:`html.escape`), then every newline is collapsed to a
       numeric character reference so the iframe stays ONE physical line
       — ``st.markdown`` keeps a raw ``<iframe>`` intact only as a single
       HTML block. The browser restores the newlines parsing srcdoc.
    """
    try:
        raw = _V10_PATH.read_text(encoding="utf-8")
    except OSError:
        return None
    if "</body>" in raw:
        raw = raw.replace("</body>", _V10_EMBED_SCOPE + "</body>", 1)
    else:
        raw = raw + _V10_EMBED_SCOPE
    escaped = _html.escape(raw, quote=True)
    # Collapse newlines to numeric refs — \r and \n kept distinct so the
    # browser rebuilds the document faithfully when it parses srcdoc.
    return escaped.replace("\r", "&#13;").replace("\n", "&#10;")


def render_live_video_v10(*, height: int = _LIVE_VIDEO_HEIGHT) -> None:
    """Embed the v10 live-video app WHOLE as the live-video surface.

    [OMY-V415 / M2 / Acceptance #65]

    The console's live-video output surface IS the v10 marketing demo
    (``static/live_video_v10.html``) — its camera, pixel-diff motion
    loop, live heatmap and see-both-at-once layout. Only v10's
    see-both-at-once panel (camera beside the heatmap) is surfaced;
    v10's onboarding chrome (scenario picker, branding, upload, info
    drawers) is hidden so the output region holds output only. It is
    v10's real code — scoped by ``_V10_EMBED_SCOPE``, never recreated.

    Camera permission — the one hard part, solved honestly
    ------------------------------------------------------
    v10's camera is a plain ``getUserMedia`` call. ``st.components.v1``
    ``.html`` renders inside a sandboxed iframe with no ``allow="camera"``
    and no API to add one, so getUserMedia is blocked there. Serving the
    file over a URL is not dependable either: ``enableStaticServing`` is
    not honoured on Streamlit Community Cloud, and GitHub raw / jsDelivr
    serve ``.html`` as ``text/plain`` (anti-abuse) so it cannot be
    framed as a page.

    So the v10 app is embedded with **no server round-trip at all** —
    its full HTML is inlined into a top-document ``<iframe srcdoc="…">``
    written through ``st.markdown(unsafe_allow_html=True)``:

    * a ``srcdoc`` iframe's document inherits the parent's origin, so it
      is same-origin and a secure context — getUserMedia is allowed;
    * the iframe carries ``allow="camera; microphone; fullscreen"``;
    * it sits in the TOP Streamlit document, NOT a components.html
      sandbox, so nothing strips the camera permission.

    The user grants the camera once and the embedded v10 app gets it.

    Parameters
    ----------
    height:
        Embedded-iframe pixel height.
    """
    srcdoc = _v10_srcdoc()
    if srcdoc is None:  # pragma: no cover - deploy fault; asset always ships
        st.error(
            "Live-video asset unavailable — static/live_video_v10.html "
            "is missing from the deployment."
        )
        return

    # A top-document iframe (NOT components.html) carrying the v10 app
    # inline via srcdoc — same-origin, so it can hold the camera grant.
    # Built as ONE physical line; see _v10_srcdoc on why that matters.
    iframe_html = (
        f'<iframe srcdoc="{srcdoc}" '
        f'allow="camera; microphone; fullscreen" '
        f'title="Omytea live video" '
        f'style="width:100%;height:{int(height)}px;border:0;'
        f'border-radius:10px;background:#0a0c11;'
        f'box-shadow:0 10px 40px rgba(0,0,0,0.35);"></iframe>'
    )
    st.markdown(iframe_html, unsafe_allow_html=True)

    st.caption(T("live_video.embed_caption"))


# Component pixel height. Sized to sit inside the workspace output pane
# (the one-screen layout) — the iframe itself never scrolls.
_COMPONENT_HEIGHT = 392


def render_heatmap_camera_component(
    branches: list[dict[str, Any]],
    horizon_label: str = "",
    *,
    height: int = _COMPONENT_HEIGHT,
    key_suffix: str = "",
    show_camera: bool = True,
) -> None:
    """Render the embedded interactive heatmap + camera component.

    Parameters
    ----------
    branches:
        Output of :func:`branches_to_payload`. Empty list = idle uniform
        grid (no prediction has run).
    horizon_label:
        The user's ``time_horizon`` string, shown on the NOW → HORIZON
        axis. Falls back to "horizon" when blank.
    height:
        Iframe pixel height.
    key_suffix:
        Reserved for disambiguation if two components ever co-exist.
    """
    payload_json = json.dumps(branches, ensure_ascii=True)
    horizon_safe = _html.escape((horizon_label or "horizon").strip())

    # i18n strings are baked into the HTML at render time (the JS side has
    # no Streamlit access). All are escaped for safe embedding.
    strings = {
        "title": _html.escape(T("result.heatmap_title")),
        "reading": _html.escape(T("result.heatmap_reading")),
        "camera_btn": _html.escape(T("heatmap.camera_btn")),
        "video_btn": _html.escape(T("heatmap.video_btn")),
        "stop_btn": _html.escape(T("heatmap.stop_btn")),
        "preview_title": _html.escape(T("heatmap.preview_title")),
        "watching": _html.escape(T("heatmap.motion_watching")),
        "camera_off": _html.escape(T("heatmap.camera_off")),
        "no_motion": _html.escape(T("heatmap.no_motion")),
        "cell_hint": _html.escape(T("heatmap.cell_hint")),
        "now": _html.escape(T("heatmap.axis_now")),
        "horizon": horizon_safe,
        "iframe_cam_note": _html.escape(T("heatmap.iframe_camera_note")),
        "idle_note": _html.escape(T("heatmap.idle_note")),
        "live_note": _html.escape(T("heatmap.live_note")),
    }

    html_doc = _build_component_html(payload_json, strings)
    if not show_camera:
        # Output-only heatmap: hide the component's own camera / video
        # controls and the camera-preview column. Camera input belongs
        # to the composer's "Live video" toggle, never the output region.
        html_doc = html_doc.replace(
            "</head>",
            "<style>.controls,.cam-note,.preview"
            "{display:none!important;}"
            ".stage{display:block!important;}</style></head>",
            1,
        )
    components.html(html_doc, height=height, scrolling=False)


def _build_component_html(payload_json: str, s: dict[str, str]) -> str:
    """Assemble the full single-file HTML/JS/CSS component document.

    ``payload_json`` is a JSON array of branch dicts; ``s`` is the map of
    pre-escaped i18n strings.
    """
    # NOTE: this is one self-contained document — vanilla JS, zero deps,
    # no model download. The motion detector is an 80×45 canvas pixel
    # diff (the v10 design the founder approved). The {curly} slots below
    # are .format()-filled from `s` + payload; all JS braces are doubled.
    return _COMPONENT_TEMPLATE.format(payload=payload_json, **s)


# ----------------------------------------------------------------------
# The component document. JS literal braces are doubled for str.format.
# ----------------------------------------------------------------------
_COMPONENT_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
  :root {{
    color-scheme: dark;
    --canvas: #0a0c11; --surface: #11141b; --surface-2: #181c25;
    --hairline: #232834; --ink-0: #f0f2f5; --ink-1: #b9bfc8;
    --ink-2: #76808d; --ink-3: #4b525d;
    --accent: #8b8cff; --teal: #58c5b4; --red: #ff5e6e; --amber: #d8a657;
    --mono: ui-monospace, "SF Mono", Menlo, monospace;
    --sans: -apple-system, "Inter", system-ui, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--canvas); }}
  body {{
    color: var(--ink-0); font-family: var(--sans); font-size: 14px;
    line-height: 1.5; -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ padding: 2px; }}
  .sect-label {{
    color: var(--ink-2); font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.12em; font-weight: 600; margin: 0 0 8px;
  }}
  /* layout: stacks by default, side-by-side when video is active */
  .stage {{ display: block; }}
  .stage.live {{
    display: grid; grid-template-columns: 320px 1fr; gap: 16px;
    align-items: start;
  }}
  @media (max-width: 760px) {{
    .stage.live {{ grid-template-columns: 1fr; }}
  }}
  /* ---- camera preview column ---- */
  .preview {{
    display: none; background: var(--surface);
    border: 1px solid var(--hairline); border-radius: 10px;
    overflow: hidden; position: sticky; top: 4px;
  }}
  .stage.live .preview {{ display: block; }}
  .preview-hd {{
    display: flex; align-items: center; gap: 8px; padding: 9px 12px;
    border-bottom: 1px solid var(--hairline); font-size: 12px;
    color: var(--ink-1);
  }}
  .preview-hd .dot {{
    width: 6px; height: 6px; border-radius: 50%; background: var(--teal);
    box-shadow: 0 0 6px var(--teal);
  }}
  .preview-hd .close {{
    margin-left: auto; cursor: pointer; color: var(--ink-2);
    font-size: 16px; line-height: 1; border: 0; background: none;
  }}
  .preview-hd .close:hover {{ color: var(--ink-0); }}
  .video-box {{ position: relative; background: #000; aspect-ratio: 16/10; }}
  .video-box video, .video-box img {{
    width: 100%; height: 100%; object-fit: cover; display: block;
  }}
  .motion-marker {{
    position: absolute; top: 50%; width: 30px; height: 30px;
    margin: -15px 0 0 -15px; border: 2px solid var(--teal);
    border-radius: 50%; pointer-events: none; opacity: 0;
    transition: left 0.1s linear, opacity 0.15s ease;
    box-shadow: 0 0 14px rgba(88,197,180,0.7);
  }}
  .motion-marker.show {{ opacity: 1; }}
  .motion-marker .lbl {{
    position: absolute; top: -20px; left: 50%; transform: translateX(-50%);
    white-space: nowrap; font-size: 9px; color: var(--teal);
    font-family: var(--mono);
  }}
  .motion-status {{
    padding: 9px 12px; font-size: 11.5px; color: var(--ink-2);
    border-top: 1px solid var(--hairline);
  }}
  .motion-status.active {{ color: var(--teal); }}
  .bar-track {{
    display: block; margin-top: 6px; height: 3px; border-radius: 2px;
    background: var(--hairline); overflow: hidden;
  }}
  .bar-fill {{
    display: block; height: 100%; width: 0%; background: var(--teal);
    transition: width 0.1s linear;
  }}
  /* ---- controls ---- */
  .controls {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 12px; }}
  .ctl {{
    appearance: none; cursor: pointer; font-family: var(--sans);
    font-size: 12px; color: var(--ink-1); background: var(--surface-2);
    border: 1px solid var(--hairline); border-radius: 7px;
    padding: 7px 13px; transition: all 0.12s ease;
  }}
  .ctl:hover {{ border-color: var(--accent); color: var(--ink-0); }}
  .ctl.on {{
    border-color: var(--accent); color: var(--ink-0);
    background: rgba(139,140,255,0.14);
  }}
  .ctl.stop {{ display: none; }}
  .stage.live .ctl.stop {{ display: inline-block; }}
  .cam-note {{
    display: none; margin: 0 0 12px; padding: 9px 12px;
    background: rgba(216,166,87,0.08); border: 1px solid rgba(216,166,87,0.3);
    border-radius: 7px; color: var(--amber); font-size: 11.5px;
    line-height: 1.5;
  }}
  .cam-note.show {{ display: block; }}
  /* ---- forecast column ---- */
  /* idle / prediction: cap the whole column so the heatmap + its
     caption + legend stay a compact centred block; the live
     side-by-side layout uses the full column width. */
  .forecast {{ max-width: 680px; margin: 0 auto; }}
  .stage.live .forecast {{ max-width: none; margin: 0; }}
  /* ---- heatmap card ---- */
  /* The .forecast cap above bounds the rendered grid so each cell
     stays small + precise (Acceptance #63) — an unbounded column
     stretched the SVG across the full Console width and ballooned
     every cell. */
  .heat-card {{
    background: var(--surface); border: 1px solid var(--hairline);
    border-radius: 8px; padding: 10px 10px 6px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.35),
      0 1px 0 rgba(255,255,255,0.025) inset;
  }}
  .heat-card svg {{ width: 100%; display: block; }}
  .heatmap-cell {{ cursor: pointer; transition: opacity 0.18s ease; }}
  .heatmap-cell:hover {{ stroke: var(--ink-0); stroke-width: 1.4; }}
  .reading-hint {{
    color: var(--ink-3); font-size: 11px; margin: 8px 0 0;
  }}
  .caption {{
    color: var(--ink-2); font-size: 12px; line-height: 1.5;
    margin-top: 10px;
  }}
  .legend {{
    display: flex; align-items: center; gap: 14px; margin-top: 10px;
    color: var(--ink-2); font-size: 11.5px; flex-wrap: wrap;
  }}
  .legend .sw {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    vertical-align: middle; margin-right: 6px;
  }}
  .legend .grad {{
    display: inline-block; height: 10px; width: 92px; border-radius: 2px;
    border: 1px solid var(--hairline);
    background: linear-gradient(to right,
      rgba(139,140,255,0.06) 0%, rgba(139,140,255,0.45) 55%,
      rgba(139,140,255,0.98) 100%);
  }}
  /* ---- cell popover ---- */
  .heat-wrap {{ position: relative; }}
  .cell-popover {{
    position: absolute; width: 270px; background: var(--surface-2);
    border: 1px solid var(--hairline); border-radius: 9px; padding: 12px;
    box-shadow: 0 16px 44px rgba(0,0,0,0.55); opacity: 0;
    transform: translateY(4px); pointer-events: none;
    transition: opacity 0.13s ease, transform 0.13s ease; z-index: 20;
  }}
  .cell-popover.show {{
    opacity: 1; transform: translateY(0); pointer-events: auto;
  }}
  .cell-popover .hd {{
    display: flex; align-items: center; gap: 8px; margin-bottom: 7px;
  }}
  .cell-popover .badge {{
    font-family: var(--mono); font-size: 10px; color: var(--accent);
    background: rgba(139,140,255,0.14); border-radius: 4px;
    padding: 2px 7px;
  }}
  .cell-popover .close-x {{
    margin-left: auto; cursor: pointer; border: 0; background: none;
    color: var(--ink-2); font-size: 15px; line-height: 1;
  }}
  .cell-popover .close-x:hover {{ color: var(--ink-0); }}
  .cell-popover .num {{
    font-family: var(--mono); font-size: 22px; color: var(--ink-0);
    font-weight: 500; margin-bottom: 4px;
  }}
  .cell-popover .narrative {{
    color: var(--ink-1); font-size: 12.5px; line-height: 1.55;
  }}
  /* Mode notes — visibility is JS-driven per heatmap mode
     (idle / prediction / live), see updateModeNotes(). */
  .idle-note, .live-note {{
    text-align: center; color: var(--ink-2); font-size: 12.5px;
    line-height: 1.6; margin: 8px 0 2px; display: none;
  }}
  .idle-note.show, .live-note.show {{ display: block; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="sect-label">{title}</div>

  <div class="controls">
    <button class="ctl" id="btn-camera" type="button">{camera_btn}</button>
    <button class="ctl" id="btn-video" type="button">{video_btn}</button>
    <button class="ctl stop" id="btn-stop" type="button">{stop_btn}</button>
    <input type="file" id="file-input" accept="video/*"
           style="display:none;" />
  </div>
  <div class="cam-note" id="cam-note">{iframe_cam_note}</div>

  <div class="stage" id="stage">
    <!-- camera / video preview column -->
    <div class="preview" id="preview">
      <div class="preview-hd">
        <span class="dot"></span>
        <span id="preview-title">{preview_title}</span>
        <button class="close" id="preview-close" type="button"
                aria-label="close">&times;</button>
      </div>
      <div class="video-box">
        <video id="preview-video" autoplay muted playsinline></video>
        <div class="motion-marker" id="motion-marker">
          <span class="lbl" id="motion-marker-label">Person A</span>
        </div>
      </div>
      <div class="motion-status" id="motion-status">
        <span id="motion-status-text">{watching}</span>
        <span class="bar-track"><span class="bar-fill"
              id="motion-bar"></span></span>
      </div>
    </div>

    <!-- heatmap column -->
    <div class="forecast">
      <div class="heat-wrap">
        <div class="heat-card">
          <svg id="heatmap" viewBox="0 0 760 206"
               preserveAspectRatio="xMidYMid meet"
               aria-label="Probability heatmap">
            <g id="heat-axis"></g>
            <g id="heat-grid"></g>
          </svg>
        </div>
        <div class="cell-popover" id="cell-popover" role="dialog"
             aria-hidden="true">
          <div class="hd">
            <span class="badge" id="pop-badge">cell</span>
            <button class="close-x" id="pop-close" type="button"
                    aria-label="close">&times;</button>
          </div>
          <div class="num" id="pop-prob">--%</div>
          <div class="narrative" id="pop-narr"></div>
        </div>
      </div>
      <div class="reading-hint">{cell_hint}</div>
      <div class="idle-note" id="idle-note">{idle_note}</div>
      <div class="live-note" id="live-note">{live_note}</div>
      <div class="caption">{reading}</div>
      <div class="legend">
        <span><span class="sw" style="background:#58c5b4;"></span>
          best plausible</span>
        <span><span class="sw" style="background:#ff5e6e;"></span>
          worst plausible</span>
        <span style="display:inline-flex;align-items:center;gap:6px;">
          <span class="grad"></span>low &rarr; high probability mass</span>
      </div>
    </div>
  </div>
</div>

<!-- hidden canvas for the pixel-diff motion loop -->
<canvas id="motion-canvas" width="80" height="45"
        style="display:none;"></canvas>

<script>
(function () {{
  "use strict";
  var $ = function (id) {{ return document.getElementById(id); }};

  // ===== server-side branch distribution (may be empty = idle) =====
  var BRANCHES = {payload};

  var STR = {{
    cameraOff: "{camera_off}",
    watching: "{watching}",
    noMotion: "{no_motion}",
    now: "{now}",
    horizon: "{horizon}",
  }};

  // ===== zone model (matches v10 live_perception) =====
  var ZONE_INDEX = [-3, -2, -1, 0, 1, 2, 3];
  var ZONE_NAMES = ["far left", "mid left", "near left", "center",
                    "near right", "mid right", "far right"];

  function gaussianDensity(x, mu, sigma) {{
    var d = (x - mu) / sigma;
    return Math.exp(-0.5 * d * d) / (sigma * Math.sqrt(2 * Math.PI));
  }}
  function zoneNameOf(c) {{
    var i = Math.max(0, Math.min(6, Math.round(c + 3)));
    return ZONE_NAMES[i];
  }}

  // ===== motion-detection module (v10 pixel-diff) =====
  var motion = {{
    centroid: 0, intensity: 0, rawCentroid: 0,
    timer: null, canvas: null, ctx: null, prevFrame: null, active: false,
  }};
  var MOTION_W = 80, MOTION_H = 45;
  var MOTION_NOISE = 24;        // per-channel |delta| threshold
  var MOTION_MIN_MASS = 600;    // below this = no motion
  var MOTION_SCALE = 12000;     // mass / scale = intensity
  var MOTION_SMOOTH = 0.55;     // EMA alpha
  var MOTION_DECAY = 0.78;      // intensity decay when still
  var MOTION_TICK_MS = 100;     // 10 fps
  var RERENDER_C = 0.06;        // skip rebuild if |dCentroid| < this
  var RERENDER_I = 0.04;        // ...and |dIntensity| < this
  var lastPaintC = 0, lastPaintI = 0, lastPaintActive = false;

  function initMotion() {{
    if (motion.canvas) return;
    motion.canvas = $("motion-canvas");
    motion.ctx = motion.canvas.getContext("2d",
      {{ willReadFrequently: true }});
  }}
  function startMotionLoop() {{
    initMotion();
    stopMotionLoop();
    motion.active = true;
    motion.prevFrame = null;
    lastPaintActive = false;
    motion.timer = setInterval(processMotionFrame, MOTION_TICK_MS);
  }}
  function stopMotionLoop() {{
    if (motion.timer) {{ clearInterval(motion.timer); motion.timer = null; }}
    motion.active = false;
    motion.prevFrame = null;
    motion.centroid = 0; motion.intensity = 0; motion.rawCentroid = 0;
    $("motion-marker").classList.remove("show");
    $("motion-status-text").textContent = STR.cameraOff;
    $("motion-status").classList.remove("active");
    $("motion-bar").style.width = "0%";
  }}
  function motionEffective() {{
    return motion.active && motion.intensity >= 0.05;
  }}
  function motionStartZone() {{
    if (!motionEffective()) return 0;
    return Math.max(-3, Math.min(3, motion.centroid));
  }}

  function processMotionFrame() {{
    var v = $("preview-video");
    if (!v.srcObject &&
        !(v.src && !v.paused && !v.ended && v.readyState >= 2)) {{
      return;  // source not ready
    }}
    var srcW = v.videoWidth, srcH = v.videoHeight;
    if (!srcW || !srcH) return;
    try {{
      motion.ctx.drawImage(v, 0, 0, MOTION_W, MOTION_H);
    }} catch (e) {{ return; }}
    var curr = motion.ctx.getImageData(0, 0, MOTION_W, MOTION_H);

    if (motion.prevFrame) {{
      var colMass = new Array(MOTION_W);
      for (var k = 0; k < MOTION_W; k++) colMass[k] = 0;
      var totalMass = 0;
      var a = curr.data, b = motion.prevFrame.data;
      for (var y = 0; y < MOTION_H; y++) {{
        var rowOff = y * MOTION_W * 4;
        for (var x = 0; x < MOTION_W; x++) {{
          var i = rowOff + x * 4;
          var dr = Math.abs(a[i] - b[i]);
          var dg = Math.abs(a[i + 1] - b[i + 1]);
          var db = Math.abs(a[i + 2] - b[i + 2]);
          if (dr > MOTION_NOISE || dg > MOTION_NOISE ||
              db > MOTION_NOISE) {{
            var d = (dr + dg + db) / 3;
            colMass[x] += d;
            totalMass += d;
          }}
        }}
      }}
      if (totalMass > MOTION_MIN_MASS) {{
        var cx = 0;
        for (var x2 = 0; x2 < MOTION_W; x2++) cx += x2 * colMass[x2];
        cx /= totalMass;
        motion.rawCentroid = (cx / MOTION_W - 0.5) * 6;
        var rawI = Math.min(1, totalMass / MOTION_SCALE);
        motion.centroid = MOTION_SMOOTH * motion.rawCentroid +
          (1 - MOTION_SMOOTH) * motion.centroid;
        motion.intensity = MOTION_SMOOTH * rawI +
          (1 - MOTION_SMOOTH) * motion.intensity;
      }} else {{
        motion.intensity *= MOTION_DECAY;
        if (motion.intensity < 0.02) motion.intensity = 0;
      }}
    }}
    motion.prevFrame = curr;

    updateMotionMarker();
    updateMotionStatus();

    // lazy re-render: only rebuild the SVG when motion meaningfully moved
    var dC = Math.abs(motion.centroid - lastPaintC);
    var dI = Math.abs(motion.intensity - lastPaintI);
    var activeChanged = motionEffective() !== lastPaintActive;
    if (activeChanged || dC > RERENDER_C || dI > RERENDER_I) {{
      renderHeatmap();
      lastPaintC = motion.centroid;
      lastPaintI = motion.intensity;
      lastPaintActive = motionEffective();
    }}
  }}

  function updateMotionMarker() {{
    var marker = $("motion-marker");
    if (!motion.active || motion.intensity < 0.05) {{
      marker.classList.remove("show");
      return;
    }}
    marker.classList.add("show");
    var pct = ((motion.centroid + 3) / 6) * 100;
    marker.style.left = pct.toFixed(1) + "%";
    marker.style.opacity = (0.45 + 0.55 * motion.intensity).toFixed(2);
    $("motion-marker-label").textContent =
      "Person A · " + zoneNameOf(motion.centroid);
  }}
  function updateMotionStatus() {{
    var txt = $("motion-status-text");
    var bar = $("motion-bar");
    var wrap = $("motion-status");
    if (!motion.active) {{
      txt.textContent = STR.cameraOff;
      wrap.classList.remove("active");
      bar.style.width = "0%";
      return;
    }}
    if (motion.intensity < 0.05) {{
      txt.textContent = STR.noMotion;
      wrap.classList.remove("active");
      bar.style.width = (motion.intensity * 100).toFixed(0) + "%";
      return;
    }}
    txt.textContent = "Motion detected · Person A in the " +
      zoneNameOf(motion.centroid) + " zone · intensity " +
      motion.intensity.toFixed(2) + ".";
    wrap.classList.add("active");
    bar.style.width = (motion.intensity * 100).toFixed(0) + "%";
  }}

  // ===== layout toggle =====
  function setLive(on) {{
    $("stage").classList.toggle("live", on);
  }}

  // ===== heatmap geometry =====
  // Cell sizing tracks the v10 marketing demo's finer grid: a narrow
  // left gutter (96, not 200) so the grid is wide, many time columns
  // so each cell is small + precise, and a shorter canvas so the rows
  // do not balloon into oversized blocks. The grid stays centred so a
  // few-row prediction does not stretch each cell vertically.
  var SVG_W = 760, SVG_H = 206;
  var PADX_L = 96, PADX_R = 16, PADY_T = 12, PADY_B = 26;
  var GRID_W = SVG_W - PADX_L - PADX_R;
  var GRID_H = SVG_H - PADY_T - PADY_B;
  // hard cap on a single cell so a 5-row prediction grid never draws
  // giant blocks — surplus vertical space becomes a centred margin.
  var MAX_CELL_H = 30;

  // mode A — server prediction present: branch x time grid.
  // mode B — idle, no prediction: uniform branch x time grid.
  // mode C — video active: live_perception zone x second heatmap.
  function heatmapMode() {{
    if (motion.active) return "live";
    return BRANCHES.length > 0 ? "prediction" : "idle";
  }}

  // build the grid data for the current mode
  function buildGrid() {{
    var mode = heatmapMode();
    if (mode === "live") {{
      // live_perception: 7 zones x 31 seconds, diffusion from centroid
      var rows = ZONE_INDEX.length;     // 7
      var cols = 31;
      var startZone = motionStartZone();
      var grid = [];
      for (var r = 0; r < rows; r++) grid.push(new Array(cols));
      var gmax = 0;
      for (var c = 0; c < cols; c++) {{
        var t = c / (cols - 1);
        var mu = startZone;             // walking-forward anchor
        var sigma = Math.max(0.18, 1.6 * Math.sqrt(t));
        var dens = ZONE_INDEX.map(function (z) {{
          return gaussianDensity(z, mu, sigma);
        }});
        var tot = dens.reduce(function (p, q) {{ return p + q; }}, 0);
        for (var r2 = 0; r2 < rows; r2++) {{
          var p = dens[r2] / tot;
          grid[r2][c] = p;
          if (p > gmax) gmax = p;
        }}
      }}
      return {{
        rows: rows, cols: cols, grid: grid, gmax: gmax || 1,
        rowLabels: ZONE_NAMES.slice(),
        rowColors: ZONE_INDEX.map(function () {{ return "139,140,255"; }}),
        kind: "live",
      }};
    }}
    // prediction / idle: branch x time, sharpening uniform -> predicted.
    // Many fine time columns (24) — a compact, precise grid like the
    // v10 marketing demo's 31-step heatmap, not a few oversized blocks.
    var branches = BRANCHES.length > 0 ? BRANCHES : idleBranches();
    var n = branches.length;
    var ncols = 24;
    var uniform = 1 / n;
    var g = [];
    var gm = 0;
    for (var bi = 0; bi < n; bi++) {{
      var rowArr = [];
      var prob = branches[bi].probability;
      for (var cc = 0; cc < ncols; cc++) {{
        var tt = cc / (ncols - 1);
        var val = uniform * (1 - tt) + prob * tt;
        rowArr.push(val);
        if (val > gm) gm = val;
      }}
      g.push(rowArr);
    }}
    var colors = branches.map(function (b) {{
      if (b.branch_type === "wishful") return "88,197,180";
      if (b.branch_type === "worst") return "255,94,110";
      return "139,140,255";
    }});
    return {{
      rows: n, cols: ncols, grid: g, gmax: gm || 1,
      rowLabels: branches.map(function (b, ix) {{
        var lbl = (b.label || ("Branch " + (ix + 1))).trim();
        return lbl.length > 11 ? lbl.slice(0, 10) + "…" : lbl;
      }}),
      rowColors: colors,
      branches: branches,
      kind: BRANCHES.length > 0 ? "prediction" : "idle",
    }};
  }}

  function idleBranches() {{
    var out = [];
    var labels = ["Branch A", "Branch B", "Branch C",
                  "Branch D", "Branch E"];
    for (var i = 0; i < labels.length; i++) {{
      out.push({{ label: labels[i] + " — awaiting your decision",
                  probability: 0.2, branch_type: "realistic" }});
    }}
    return out;
  }}

  var GD = null;  // current grid data (cached for popover)

  function renderHeatmap() {{
    GD = buildGrid();
    var rows = GD.rows, cols = GD.cols;
    var cellW = GRID_W / cols;
    // cap cell height so a few-row prediction grid stays compact; the
    // surplus vertical space becomes a centred top/bottom margin.
    var cellH = Math.min(MAX_CELL_H, GRID_H / rows);
    var gridH = cellH * rows;
    var gy0 = PADY_T + (GRID_H - gridH) / 2;
    var axis = "";
    var grid = "";

    // row labels (left). Compact: smaller font for the narrow gutter.
    for (var r = 0; r < rows; r++) {{
      var y = gy0 + r * cellH + cellH / 2 + 3.4;
      var lab = GD.rowLabels[r]
        .replace(/&/g, "&amp;").replace(/</g, "&lt;");
      axis += '<text x="' + (PADX_L - 8) + '" y="' + y.toFixed(1) +
        '" text-anchor="end" font-family="var(--mono)" ' +
        'font-size="9.5" fill="#b9bfc8">' + lab + "</text>";
    }}
    // cells — fine grid: a hairline gap, crisp corners. The gap is a
    // fixed 0.5px so cells stay precise + tight even when small.
    var gap = 0.5;
    for (var c = 0; c < cols; c++) {{
      for (var r2 = 0; r2 < rows; r2++) {{
        var p = GD.grid[r2][c];
        var op = (0.05 + 0.93 * (p / GD.gmax)).toFixed(3);
        var rgb = GD.rowColors[r2];
        var glow = (c === cols - 1)
          ? ' filter="url(#heat-glow)"' : "";
        var cx = PADX_L + c * cellW;
        var cy = gy0 + r2 * cellH;
        grid += '<rect class="heatmap-cell" x="' + (cx + gap).toFixed(2) +
          '" y="' + (cy + gap).toFixed(2) + '" width="' +
          (cellW - 2 * gap).toFixed(2) + '" height="' +
          (cellH - 2 * gap).toFixed(2) + '" rx="1" fill="rgba(' +
          rgb + "," + op + ')" stroke="#0a0c11" stroke-width="0.35"' +
          glow + ' data-step="' + c + '" data-row="' + r2 +
          '" data-prob="' + p.toFixed(4) + '"></rect>';
      }}
    }}
    // horizon column highlight
    var hlx = PADX_L + (cols - 1) * cellW;
    grid += '<rect x="' + (hlx + 0.4).toFixed(1) + '" y="' +
      (gy0 - 2.5).toFixed(1) + '" width="' + (cellW - 0.8).toFixed(1) +
      '" height="' + (gridH + 5).toFixed(1) +
      '" rx="2" fill="none" stroke="rgba(139,140,255,0.55)" ' +
      'stroke-width="1.0"></rect>';
    // bottom NOW -> HORIZON axis
    var axisY = PADY_T + GRID_H + 14;
    axis += '<line x1="' + PADX_L + '" y1="' + (axisY - 8) +
      '" x2="' + (SVG_W - PADX_R) + '" y2="' + (axisY - 8) +
      '" stroke="#232834" stroke-width="0.7"></line>';
    axis += '<text x="' + PADX_L + '" y="' + (axisY + 4) +
      '" font-family="var(--mono)" font-size="9" fill="#76808d" ' +
      'letter-spacing="0.1em">' + STR.now.toUpperCase() + "</text>";
    axis += '<text x="' + (SVG_W - PADX_R) + '" y="' + (axisY + 4) +
      '" font-family="var(--mono)" font-size="9" fill="#8b8cff" ' +
      'letter-spacing="0.1em" text-anchor="end">' +
      STR.horizon.toUpperCase() + "</text>";

    $("heat-axis").innerHTML =
      '<defs><filter id="heat-glow" x="-40%" y="-40%" width="180%" ' +
      'height="180%"><feGaussianBlur stdDeviation="2.2" result="b"/>' +
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>' +
      "</feMerge></filter></defs>" + axis;
    $("heat-grid").innerHTML = grid;
    updateModeNotes();
    hideCellPopover();
  }}

  // The two contextual notes below the grid are mutually exclusive and
  // mode-driven: idle-note only when truly idle (no prediction, no
  // camera); live-note only when a video source is driving the math;
  // a resolved prediction with no camera shows neither (the caption
  // already explains the grid).
  function updateModeNotes() {{
    var mode = heatmapMode();
    $("idle-note").classList.toggle("show", mode === "idle");
    $("live-note").classList.toggle("show", mode === "live");
  }}

  // ===== cell popover =====
  function plainReading(step, row) {{
    var p = GD.grid[row][step];
    var pct = (p * 100).toFixed(1);
    if (GD.kind === "live") {{
      return "Roughly a <strong>" + pct + "%</strong> chance Person A " +
        "is in the <strong>" + GD.rowLabels[row] + "</strong> zone, " +
        "<strong>" + step + (step === 1 ? " second" : " seconds") +
        "</strong> from now.";
    }}
    var horizonTxt = STR.horizon;
    var when = step === GD.cols - 1
      ? "at your " + horizonTxt
      : "at horizon slice " + step + " of " + (GD.cols - 1);
    if (GD.kind === "idle") {{
      return "<strong>" + GD.rowLabels[row] + "</strong> — the grid " +
        "is uniform until a prediction runs. This cell would carry " +
        "<strong>" + pct + "%</strong> of the probability mass " +
        when + ".";
    }}
    return "<strong>" + GD.rowLabels[row] + "</strong> carries " +
      "<strong>" + pct + "%</strong> of the probability mass " + when +
      ". Read across this row to see the future's likelihood evolve.";
  }}

  function showCellPopover(target) {{
    var step = parseInt(target.getAttribute("data-step"), 10);
    var row = parseInt(target.getAttribute("data-row"), 10);
    var cellNo = row * GD.cols + step + 1;
    $("pop-badge").textContent = "cell #" + cellNo;
    $("pop-prob").textContent =
      (GD.grid[row][step] * 100).toFixed(1) + "%";
    $("pop-narr").innerHTML = plainReading(step, row);

    var pop = $("cell-popover");
    var cellRect = target.getBoundingClientRect();
    var wrapRect = target.closest(".heat-wrap").getBoundingClientRect();
    var popW = 270, popH = 130;
    var x = cellRect.left - wrapRect.left +
      cellRect.width / 2 - popW / 2;
    var y = cellRect.top - wrapRect.top - popH - 8;
    x = Math.max(6, Math.min(wrapRect.width - popW - 6, x));
    if (y < 6) y = cellRect.bottom - wrapRect.top + 8;
    pop.style.left = x + "px";
    pop.style.top = y + "px";
    pop.classList.add("show");
    pop.setAttribute("aria-hidden", "false");
  }}
  function hideCellPopover() {{
    var pop = $("cell-popover");
    pop.classList.remove("show");
    pop.setAttribute("aria-hidden", "true");
  }}

  // ===== camera / video wiring =====
  var mediaStream = null;

  function stopMedia() {{
    stopMotionLoop();
    if (mediaStream) {{
      mediaStream.getTracks().forEach(function (t) {{ t.stop(); }});
      mediaStream = null;
    }}
    var v = $("preview-video");
    v.srcObject = null;
    v.removeAttribute("src");
    setLive(false);
    $("btn-camera").classList.remove("on");
    $("btn-video").classList.remove("on");
    lastPaintActive = false;
    renderHeatmap();
  }}

  function startCamera() {{
    // getUserMedia inside the components.html iframe is normally blocked
    // by Permissions Policy (no allow="camera"). We attempt it honestly
    // and, if blocked, surface a clear message instead of a dead button.
    if (!navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia) {{
      $("cam-note").classList.add("show");
      return;
    }}
    navigator.mediaDevices.getUserMedia({{ video: true, audio: false }})
      .then(function (stream) {{
        $("cam-note").classList.remove("show");
        mediaStream = stream;
        var v = $("preview-video");
        v.srcObject = stream;
        $("preview-title").textContent = "Live camera feed";
        setLive(true);
        $("btn-camera").classList.add("on");
        $("btn-video").classList.remove("on");
        if (v.readyState >= 2) startMotionLoop();
        else v.addEventListener("loadeddata", startMotionLoop,
          {{ once: true }});
      }})
      .catch(function (err) {{
        // Permission denied OR Permissions-Policy block — both land
        // here. Honest surface: tell the user the real fallback.
        $("cam-note").classList.add("show");
      }});
  }}

  function handleVideoFile(file) {{
    if (!file) return;
    stopMedia();
    var url = URL.createObjectURL(file);
    var v = $("preview-video");
    v.src = url;
    v.play().catch(function () {{}});
    $("preview-title").textContent = "Uploaded video";
    setLive(true);
    $("btn-video").classList.add("on");
    $("btn-camera").classList.remove("on");
    v.addEventListener("loadeddata", startMotionLoop, {{ once: true }});
    v.addEventListener("play", startMotionLoop, {{ once: true }});
  }}

  // ===== event wiring =====
  $("btn-camera").addEventListener("click", startCamera);
  $("btn-video").addEventListener("click", function () {{
    $("file-input").click();
  }});
  $("btn-stop").addEventListener("click", stopMedia);
  $("preview-close").addEventListener("click", stopMedia);
  $("file-input").addEventListener("change", function (e) {{
    if (e.target.files && e.target.files[0]) {{
      handleVideoFile(e.target.files[0]);
    }}
  }});
  $("pop-close").addEventListener("click", hideCellPopover);

  $("heatmap").addEventListener("click", function (e) {{
    var t = e.target;
    if (t && t.classList &&
        t.classList.contains("heatmap-cell")) {{
      showCellPopover(t);
    }} else {{
      hideCellPopover();
    }}
  }});
  document.addEventListener("keydown", function (e) {{
    if (e.key === "Escape") hideCellPopover();
  }});

  // ===== test hook (used by AppTest / manual verification) =====
  window.__omyteaHeatmap = {{
    motion: motion,
    mode: heatmapMode,
    branchCount: function () {{ return BRANCHES.length; }},
    cellCount: function () {{
      return document.querySelectorAll(".heatmap-cell").length;
    }},
  }};

  // ===== first paint =====
  renderHeatmap();
}})();
</script>
</body>
</html>
"""
