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

# CSS + JS injected into the embedded v10 copy. The console output
# region holds OUTPUT ONLY, and the surviving camera + heatmap surface
# is polished to sit beside the console's own quantum-heatmap as one
# consistent, premium surface. Hidden: v10's onboarding chrome
# (scenario picker, topbar, upload, now-banner), its input controls
# (the "Use my camera" .input-row + the "What would change this
# picture?" .cf-card), and its verbose explanatory copy (the
# .honesty-note essay under the camera + the .caveat under the answer).
# The heatmap header is kept to one line (it wrapped in the narrow
# side-by-side column) and the camera | heatmap grid is forced on
# (v10's own grid needs >=1100px). With no in-iframe start button the
# injected script auto-starts the camera on load — flipping the
# composer's "Live video" toggle is the single start control.
_V10_EMBED_SCOPE = """
<style id="omytea-embed-scope">
/* hide v10's onboarding chrome, input controls + verbose copy — the
   console composer owns input, the output region is output-only */
.topbar,.menu-btn,#scenario-card,#input-file,#input-scenario,
.now-banner,.hero-head,.more-row,footer.footer,
.input-row,.cf-card,.honesty-note,.file-info,
.answer-text .caveat{display:none!important;}
/* full-bleed — the console output pane is the frame */
html,body{background:#0a0c11!important;}
main{max-width:none!important;margin:0!important;
 padding:18px 20px!important;}
body:not(.camera-active) main{max-width:740px!important;
 margin:0 auto!important;}
/* camera | heatmap side-by-side + a full-width one-line read */
body.camera-active main{display:grid!important;
 grid-template-columns:minmax(250px,40%) 1fr!important;
 gap:16px 20px!important;align-items:start!important;}
body.camera-active #preview-card{grid-area:1/1/2/2!important;}
body.camera-active .heat-card{grid-area:1/2/2/3!important;}
body.camera-active .answer-text{grid-area:2/1/3/3!important;}
@media (max-width:560px){
 body.camera-active main{grid-template-columns:1fr!important;}
 body.camera-active #preview-card,body.camera-active .heat-card,
 body.camera-active .answer-text{grid-area:auto!important;}}
/* shared card chrome — both cards read as one refined surface,
   matching the console's own quantum-heatmap card */
#preview-card,.heat-card{position:static!important;margin:0!important;
 border-radius:8px!important;
 border:1px solid var(--hairline)!important;
 box-shadow:0 10px 40px rgba(0,0,0,0.35),
  0 1px 0 rgba(255,255,255,0.03) inset!important;}
#preview-card{overflow:hidden!important;padding:14px!important;}
.preview-card .video-wrap{border-radius:7px!important;
 overflow:hidden!important;}
.preview-card .label{margin-bottom:10px!important;}
.heat-card{padding:15px 17px 11px!important;}
/* the header wrapped to two lines in the narrow side-by-side column —
   keep the title on one line, drop v10's verbose reading hint */
.heat-card .head{align-items:center!important;gap:10px!important;
 margin-bottom:10px!important;}
.heat-card .head .title{white-space:nowrap!important;
 font-size:11px!important;letter-spacing:0.13em!important;}
.heat-card .head .reading-hint{display:none!important;}
/* soften the heatmap cells — rounded corners read more refined */
.heatmap-cell{rx:2px!important;ry:2px!important;}
/* the one-line plain-English read — centred, quiet, premium */
.answer-text{text-align:center!important;max-width:none!important;
 margin:2px 8px 0!important;padding:0!important;
 font-size:12.5px!important;line-height:1.6!important;
 color:var(--ink-1)!important;}
</style>
<script id="omytea-embed-autostart">
/* The console composer owns all input — v10's own "Use my camera"
   card and counterfactual box are hidden above. With no in-iframe
   start button, the camera starts automatically on load: this iframe
   exists only because the user flipped the composer's "Live video"
   toggle. We click v10's own (now-hidden) camera trigger so v10's
   real startCamera path runs unchanged. */
(function () {
  var started = false;
  function go() {
    if (started) return;
    var btn = document.getElementById('input-camera');
    if (!btn) return;
    started = true;
    btn.click();
  }
  if (document.readyState === 'complete') {
    setTimeout(go, 250);
  } else {
    window.addEventListener('load', function () { setTimeout(go, 250); });
  }
})();
</script>
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
        # snake_case hypothesis ids (e.g. "thrive_at_new_role") render as
        # unreadable stubs — humanise them into "Thrive at new role".
        if label and "_" in label and " " not in label:
            label = label.replace("_", " ")
            label = label[:1].upper() + label[1:]
        btype = str(getattr(h, "branch_type", "realistic"))
        if btype not in ("wishful", "worst", "realistic"):
            btype = "realistic"
        payload.append(
            {"label": label, "probability": prob, "branch_type": btype}
        )
    return payload


def _heatmap_narrative(
    branches: list[dict[str, Any]], horizon_label: str
) -> str:
    """Build the one-line plain-English reading shown below the heatmap.

    Ports v10's ``ans-narrative`` answer sentence: it names the
    most-likely branch and its calibrated share of the probability mass
    at the horizon. An empty branch list (idle) returns the static idle
    reading instead. The sentence is generated from the data so it
    stays a real calibrated read, never a fixed string.
    """
    if not branches:
        return T("heatmap.narrative_idle")
    horizon = (horizon_label or "horizon").strip() or "horizon"
    # Most-likely branch = the largest calibrated probability.
    top = max(
        branches,
        key=lambda b: float(b.get("probability", 0.0) or 0.0),
    )
    total = sum(float(b.get("probability", 0.0) or 0.0) for b in branches)
    raw = float(top.get("probability", 0.0) or 0.0)
    # Normalize so the quoted share reads as a true share of the mass.
    share = (raw / total) if total > 0 else (1.0 / max(1, len(branches)))
    pct = max(0, min(100, round(share * 100)))
    label = str(top.get("label", "") or "").strip() or "this branch"
    return T("heatmap.narrative_prediction").format(
        branch=label, pct=pct, horizon=horizon
    )


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
    horizon_raw = (horizon_label or "horizon").strip()
    horizon_safe = _html.escape(horizon_raw)

    # The plain-English reading sentence below the chart (v10's
    # ``ans-narrative``) is data-derived: it names the most-likely branch
    # and its calibrated share. Idle / live get their own static reading.
    reading_narrative = _heatmap_narrative(branches, horizon_raw)

    # i18n strings are baked into the HTML at render time (the JS side has
    # no Streamlit access). All are escaped for safe embedding.
    strings = {
        "title": _html.escape(T("result.heatmap_title")),
        "reading": _html.escape(T("result.heatmap_reading")),
        "head_title": _html.escape(T("heatmap.head_title")),
        "head_hint": _html.escape(T("heatmap.head_hint")),
        # iter #19 P1.2: idle-mode badge. Shown only when no
        # prediction has run — labels the placeholder as an example so
        # casual users do not read it as a real generated result.
        "preview_badge": _html.escape(T("heatmap.preview_badge")),
        "legend_label": _html.escape(T("heatmap.legend_label")),
        "legend_rare": _html.escape(T("heatmap.legend_rare")),
        "legend_likely": _html.escape(T("heatmap.legend_likely")),
        "y_axis_caption": _html.escape(T("heatmap.y_axis_caption")),
        "narrative": _html.escape(reading_narrative),
        "narrative_idle": _html.escape(T("heatmap.narrative_idle")),
        "narrative_live": _html.escape(T("heatmap.narrative_live")),
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


# Default fillers for the heatmap-card head / legend / narrative slots.
# ``render_heatmap_camera_component`` always supplies these from i18n;
# the defaults only matter for callers that pass a minimal strings map
# (e.g. structural tests), so every {slot} stays filled regardless.
_TEMPLATE_SLOT_DEFAULTS = {
    "head_title": "Probability of each outcome",
    "head_hint": "click a cell for detail",
    "legend_label": "Likelihood:",
    "legend_rare": "rare",
    "legend_likely": "most likely",
    "y_axis_caption": "outcome branch",
    "narrative": "",
    "narrative_idle": "",
    "narrative_live": "",
    "preview_badge": "Example preview",
}


def _build_component_html(payload_json: str, s: dict[str, str]) -> str:
    """Assemble the full single-file HTML/JS/CSS component document.

    ``payload_json`` is a JSON array of branch dicts; ``s`` is the map of
    pre-escaped i18n strings.
    """
    # NOTE: this is one self-contained document — vanilla JS, zero deps,
    # no model download. The motion detector is an 80×45 canvas pixel
    # diff (the v10 design the founder approved). The {curly} slots below
    # are .format()-filled from `s` + payload; all JS braces are doubled.
    # Any heatmap-card slot the caller omitted is back-filled so the
    # template always formats cleanly.
    fields = dict(_TEMPLATE_SLOT_DEFAULTS)
    fields.update(s)
    return _COMPONENT_TEMPLATE.format(payload=payload_json, **fields)


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
    --accent: #5e6ad2; --teal: #58c5b4; --red: #ff5e6e; --amber: #d8a657;
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
  /* Section heading — promoted from a third stacked all-caps eyebrow
     to a proper mixed-case title, so the page hierarchy reads
     eyebrow -> title -> card-label instead of three caps labels
     stuttering down the column. */
  .sect-label {{
    color: var(--ink-0); font-size: 16px; font-weight: 600;
    letter-spacing: -0.01em; margin: 1px 0 11px;
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
  /* ---- heatmap card (ported from v10's .heat-card) ---- */
  /* The .forecast cap above bounds the rendered grid so each cell
     stays small + precise (Acceptance #63) — an unbounded column
     stretched the SVG across the full Console width and ballooned
     every cell. */
  .heat-card {{
    background: var(--surface); border: 1px solid var(--hairline);
    /* radius matched to the Console's other cards (12px); the shadow
       tightened from a 40px-blur slab to a precise, quiet lift —
       floaty soft shadows read cheap, tight ones read crafted. */
    border-radius: 12px; padding: 14px 16px 10px;
    box-shadow: 0 3px 14px rgba(0,0,0,0.22),
      0 1px 0 rgba(255,255,255,0.03) inset;
  }}
  /* card head — title + reading hint, v10's .heat-card .head */
  .heat-head {{
    display: flex; align-items: baseline; gap: 12px; margin: 0 0 11px;
  }}
  .heat-head .heat-title {{
    color: var(--ink-2); font-size: 11.5px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.12em;
  }}
  .heat-head .heat-hint {{
    color: var(--ink-3); font-size: 11.5px; margin-left: auto;
  }}
  /* iter #19 P1.2 — preview badge.
     The placeholder heatmap on the cold-start screen looks
     uncomfortably like a real generated result. The user feedback was
     direct: "首屏上方的 heatmap 在还没输入前就出现，容易让人误以为
     已经生成了什么". The fix is twofold — (a) a small uppercase
     "EXAMPLE PREVIEW" badge in the heat-head, immediately readable as
     "this is illustrative, not a real prediction"; (b) a subtle
     opacity reduction on the cells when idle, so the placeholder
     reads softer than a real result without losing its shape. Both
     activate ONLY when body[data-mode="idle"], set by the JS in
     updateModeNotes(). Live and prediction modes are untouched. */
  .heat-head .preview-badge {{
    display: none;
    align-items: center;
    color: var(--accent);
    background: rgba(94,106,210,0.10);
    border: 1px solid rgba(94,106,210,0.32);
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    margin-left: 8px;
  }}
  body[data-mode="idle"] .heat-head .preview-badge {{
    display: inline-flex;
  }}
  body[data-mode="idle"] .heatmap-cell {{
    opacity: 0.62;
  }}
  body[data-mode="idle"] .heat-card {{
    /* drop the card-level lift a notch in idle — the placeholder
       should sit slightly recessed from a real result. */
    box-shadow: 0 2px 8px rgba(0,0,0,0.18),
      0 1px 0 rgba(255,255,255,0.02) inset;
  }}
  .heat-card svg {{ width: 100%; display: block; }}
  /* density-shaded cells — bright = high probability mass */
  .heatmap-cell {{ cursor: pointer; transition: opacity 0.3s ease; }}
  .heatmap-cell:hover {{ stroke: var(--ink-0); stroke-width: 1.5; }}
  .reading-hint {{
    color: var(--ink-3); font-size: 11px; margin: 8px 0 0;
  }}
  /* one-line plain-English reading below the chart (v10 ans-narrative) */
  .heat-narrative {{
    color: var(--ink-1); font-size: 13px; line-height: 1.55;
    margin: 11px 2px 2px;
  }}
  .caption {{
    color: var(--ink-2); font-size: 12px; line-height: 1.5;
    margin-top: 8px;
  }}
  /* horizontal Likelihood gradient-bar legend (v10's .heat-legend) */
  .legend {{
    display: flex; align-items: center; gap: 14px; margin-top: 9px;
    color: var(--ink-2); font-size: 12px; flex-wrap: wrap;
  }}
  .legend .sw {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    vertical-align: middle; margin-right: 6px;
  }}
  .legend .like {{
    display: inline-flex; align-items: center; gap: 7px;
  }}
  .legend .like .like-label {{ color: var(--ink-1); }}
  .legend .grad {{
    display: inline-block; height: 10px; width: 120px; border-radius: 2px;
    border: 1px solid var(--hairline);
    background: linear-gradient(to right,
      rgba(139,140,255,0.05) 0%, rgba(139,140,255,0.30) 40%,
      rgba(139,140,255,0.60) 70%, rgba(139,140,255,0.95) 100%);
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
  /* Mode notes share the left edge of the narrative + cell-hint above
     them — a consistent left rag reads as intentional; the previous
     centered idle-note broke the column's alignment rhythm. */
  .idle-note, .live-note {{
    text-align: left; color: var(--ink-2); font-size: 12.5px;
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
          <div class="heat-head">
            <span class="heat-title">{head_title}</span>
            <!-- iter #19 P1.2: preview badge — only shown when the
                 heatmap is in idle mode (no prediction submitted). The
                 label makes the cold-start state visually unambiguous:
                 this is an example of what the chart shows, not a
                 generated result. The CSS rule below shows/hides via
                 body[data-mode="idle"]; the JS sets that attribute in
                 updateModeNotes(). -->
            <span class="preview-badge">{preview_badge}</span>
            <span class="heat-hint">{head_hint}</span>
          </div>
          <svg id="heatmap" viewBox="0 0 760 206"
               preserveAspectRatio="xMidYMid meet"
               aria-label="Probability heatmap">
            <g id="heat-axis"></g>
            <g id="heat-grid"></g>
          </svg>
          <!-- horizontal Likelihood gradient-bar legend (v10) -->
          <div class="legend">
            <span class="like">
              <span class="like-label">{legend_label}</span>
              {legend_rare}<span class="grad"></span>{legend_likely}
            </span>
            <span><span class="sw" style="background:#58c5b4;"></span>
              best plausible</span>
            <span><span class="sw" style="background:#ff5e6e;"></span>
              worst plausible</span>
          </div>
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
      <!-- one-line plain-English reading, swapped by mode (v10) -->
      <p class="heat-narrative" id="heat-narrative">{narrative}</p>
      <div class="reading-hint">{cell_hint}</div>
      <div class="idle-note" id="idle-note">{idle_note}</div>
      <div class="live-note" id="live-note">{live_note}</div>
      <div class="caption">{reading}</div>
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
    yAxisCaption: "{y_axis_caption}",
    narrativePrediction: "{narrative}",
    narrativeIdle: "{narrative_idle}",
    narrativeLive: "{narrative_live}",
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
  // Left gutter widened 96 -> 124 (iter #17) so branch anchor labels
  // can actually be read — the previous 96px gutter forced labels to
  // truncate at ~11 chars, rendering "Thrive at n..." / "Burnout wit..."
  // The redundant rotated "outcome branch" caption that used to share
  // this gutter was removed too; the section title above already names
  // what the rows are, so the caption was duplicate ink.
  // Iter #54 (founder: result-chart legibility) — left gutter widened
  // 124 -> 156 so the prose future-names render in full in a friendlier
  // sans font; a non-expert was seeing "Compounding failu…" and could
  // not tell what each row's future was.
  var PADX_L = 156, PADX_R = 16, PADY_T = 12, PADY_B = 26;
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
      // live mode labels every zone row; rowLabelAt mirrors that so the
      // renderer can use one label-placement path for all modes.
      var liveLabelAt = {{}};
      for (var lz = 0; lz < rows; lz++) liveLabelAt[lz] = ZONE_NAMES[lz];
      return {{
        rows: rows, cols: cols, grid: grid, gmax: gmax || 1,
        rowLabels: ZONE_NAMES.slice(),
        rowLabelAt: liveLabelAt,
        rowColors: ZONE_INDEX.map(function () {{ return "139,140,255"; }}),
        centerRow: Math.floor((rows - 1) / 2),
        kind: "live",
      }};
    }}
    // prediction / idle: a DENSITY-SHADED probability-distribution viz,
    // ported from v10's heatmap. The branches are ordered worst ->
    // realistic -> wishful, then placed as anchor rows on a FINE row
    // grid (~7 rows per branch). The cloud DIFFUSES like v10's heatmap:
    // a tight bright core at NOW that fans outward, column by column,
    // into the calibrated spread at the HORIZON — each bump landing on
    // its branch anchor weighted by that branch's probability. It reads
    // as a probability cloud — a concentrated core widening into a
    // broad spread — not a flat colored matrix. Rendered in ONE colour
    // (v10-style); shape comes from opacity alone. 24 fine columns.
    var branches = orderedBranches(
      BRANCHES.length > 0 ? BRANCHES : idleBranches()
    );
    var n = branches.length;
    var ncols = 24;
    // calibrated horizon distribution, renormalized to sum to 1.
    var calib = branches.map(function (b) {{
      return Math.max(0, b.probability || 0);
    }});
    var calibSum = calib.reduce(function (p, q) {{ return p + q; }}, 0);
    calib = calib.map(function (v) {{
      return calibSum > 0 ? v / calibSum : (1 / n);
    }});
    // fine row grid: each branch is an anchor band, spaced ROW_STRIDE
    // apart, with a PAD-row margin top + bottom so the cloud can fan
    // past the outer branches instead of being clipped at the edge.
    // (MAX_CELL_H still keeps the rendered grid compact.)
    var ROW_STRIDE = 7;
    var PAD = 4;
    var fineRows = n * ROW_STRIDE + PAD * 2;
    // anchor row index for branch bi (centre of its band).
    function anchorOf(bi) {{
      return Math.round(PAD + bi * ROW_STRIDE + (ROW_STRIDE - 1) / 2);
    }}
    var anchors = [];
    for (var ai = 0; ai < n; ai++) anchors.push(anchorOf(ai));
    var center = (fineRows - 1) / 2;
    // modal branch = the one carrying the most calibrated mass.
    var modeBi = 0, modeP = -1;
    for (var mi = 0; mi < n; mi++) {{
      if (calib[mi] > modeP) {{ modeP = calib[mi]; modeBi = mi; }}
    }}
    var g = [];
    for (var ri = 0; ri < fineRows; ri++) g.push(new Array(ncols));
    var gm = 0;
    var colMax = new Array(ncols);
    // v10's heatmap is a DIFFUSING cloud — a tight bright core at NOW
    // that fans outward into a broad spread at the HORIZON. Centroid of
    // the calibrated distribution = where that core sits: at NOW every
    // branch bump collapses onto this one point; column by column the
    // bumps slide back to their own anchors and the cloud fans open.
    var centroid = 0;
    for (var ck = 0; ck < n; ck++) centroid += calib[ck] * anchors[ck];
    // sigma grows with sqrt(t) — v10's exact `sigma30 * sqrt(t)`
    // diffusion law — so the cloud widens visibly from NOW to HORIZON.
    var sigmaMin = ROW_STRIDE * 0.34;
    var sigmaMax = ROW_STRIDE * 0.52;
    for (var cc = 0; cc < ncols; cc++) {{
      var tt = ncols > 1 ? cc / (ncols - 1) : 1;
      var grow = Math.sqrt(tt);
      var sigma = sigmaMin + (sigmaMax - sigmaMin) * grow;
      // collapse = 1 at NOW (every bump on the centroid, one tight
      // core) -> 0 at the HORIZON (each bump on its calibrated anchor).
      var collapse = 1 - grow;
      var col = new Array(fineRows);
      var colSum = 0;
      for (var rr = 0; rr < fineRows; rr++) {{
        var d = 0;
        for (var bk = 0; bk < n; bk++) {{
          var eff = anchors[bk] * (1 - collapse) + centroid * collapse;
          d += calib[bk] * gaussianDensity(rr, eff, sigma);
        }}
        col[rr] = d;
        colSum += d;
      }}
      var cMax = 0;
      for (var rw = 0; rw < fineRows; rw++) {{
        // each time-column is normalized to a real distribution (sums
        // to 1); the pow-gamma opacity shading does the rest.
        var val = colSum > 0 ? col[rw] / colSum : (1 / fineRows);
        g[rw][cc] = val;
        if (val > cMax) cMax = val;
        if (val > gm) gm = val;
      }}
      colMax[cc] = cMax;
    }}
    // one colour for the whole cloud (v10 renders the grid single-hue;
    // shape reads from opacity). branch_type is surfaced by the legend
    // dots + the tinted anchor label, not by recolouring the cells.
    var colors = [];
    for (var ci = 0; ci < fineRows; ci++) colors.push("139,140,255");
    // labels live only on branch anchor rows (v10's rowLabelAt).
    // Iter #17: cap raised 12 -> 18 to actually let users read their
    // futures — the widened 124px gutter + the removal of the rotated
    // axis caption fits the new cap with margin. 18 chars covers the
    // career scenario labels in full ("Thrive at new role", "Burnout
    // within 6mo", "Counter offer ok", "Stay and thrive") instead of
    // truncating mid-word.
    var shortLabels = [];
    var rowLabelAt = {{}};
    var rowLabelColor = {{}};
    for (var li = 0; li < n; li++) {{
      var lbl = (branches[li].label || ("Branch " + (li + 1))).trim();
      // Iter #54 — cap raised 18 -> 30 and made WORD-AWARE so the future
      // names read in full / break on a space, never mid-word. The wider
      // sans gutter fits ~30 chars; the full name stays in the popover.
      var CAP = 30;
      if (lbl.length > CAP) {{
        var cut = lbl.slice(0, CAP);
        var sp = cut.lastIndexOf(" ");
        lbl = (sp > 16 ? cut.slice(0, sp) : cut) + "…";
      }}
      shortLabels.push(lbl);
      rowLabelAt[anchors[li]] = lbl;
      rowLabelColor[anchors[li]] =
        branches[li].branch_type === "wishful" ? "#58c5b4"
        : branches[li].branch_type === "worst" ? "#ff5e6e"
        : "#b9bfc8";
    }}
    // every fine row maps to its nearest branch label (popover read).
    var fullRowLabels = [];
    for (var fr = 0; fr < fineRows; fr++) {{
      var nearBi = 0, nearD = Infinity;
      for (var nb = 0; nb < n; nb++) {{
        var dd = Math.abs(anchors[nb] - fr);
        if (dd < nearD) {{ nearD = dd; nearBi = nb; }}
      }}
      fullRowLabels.push(shortLabels[nearBi]);
    }}
    return {{
      rows: fineRows, cols: ncols, grid: g, gmax: gm || 1,
      colMax: colMax,
      rowColors: colors,
      rowLabels: fullRowLabels,
      rowLabelAt: rowLabelAt,
      rowLabelColor: rowLabelColor,
      anchors: anchors,
      branches: branches,
      modeRow: anchors[modeBi],
      // dashed reference line at the MEDIAN branch's anchor — the
      // central band the cloud's mass is read against.
      centerRow: anchors[Math.floor((n - 1) / 2)],
      kind: BRANCHES.length > 0 ? "prediction" : "idle",
    }};
  }}

  // Order branches into a read-as-a-distribution sequence: worst at the
  // bottom, realistic in the middle, wishful at the top — and within a
  // band by ascending probability. This makes the rendered rows an
  // ordered distribution (like v10's value-ordered y-axis) rather than
  // an arbitrary list.
  function orderedBranches(list) {{
    var rank = {{ worst: 0, realistic: 1, wishful: 2 }};
    return list.slice().sort(function (a, b) {{
      var ra = rank[a.branch_type];
      var rb = rank[b.branch_type];
      if (ra === undefined) ra = 1;
      if (rb === undefined) rb = 1;
      if (ra !== rb) return ra - rb;
      return (a.probability || 0) - (b.probability || 0);
    }});
  }}

  function idleBranches() {{
    // Iter #7 → iter #11: "Branch A...E" → "Your option 1...5" →
    // "Option 1...5". The middle form got truncated by the chart's
    // narrow left gutter ("Your option…"); final form is short enough
    // to fit + still names the contract (each form option = one row).
    var out = [];
    var labels = ["Option 1", "Option 2", "Option 3",
                  "Option 4", "Option 5"];
    for (var i = 0; i < labels.length; i++) {{
      out.push({{ label: labels[i],
                  probability: 0.2, branch_type: "realistic" }});
    }}
    return out;
  }}

  var GD = null;  // current grid data (cached for popover)

  // x-axis tick labels — a mono-font "now … horizon" scale. The middle
  // ticks read like v10's "day 0 … d30": a short unit derived from the
  // horizon string, with NOW and the horizon word at the ends.
  function xTickLabels(cols, kind) {{
    var fracs = [0, 0.25, 0.5, 0.75, 1];
    if (kind === "live") {{
      // live_perception is seconds — mirror v10's "now / 8s / 15s …".
      return fracs.map(function (f) {{
        var s = Math.round(f * (cols - 1));
        return s === 0 ? STR.now : s + "s";
      }});
    }}
    // prediction / idle — derive a compact unit from the horizon word.
    var hz = (STR.horizon || "").toLowerCase();
    var unit = "";
    if (/day|天|jour|día|dia/.test(hz)) unit = "d";
    else if (/week|周|semaine|semana/.test(hz)) unit = "w";
    else if (/month|月|mois|mes/.test(hz)) unit = "mo";
    else if (/year|年|an|año/.test(hz)) unit = "y";
    var mNum = (hz.match(/\d+/) || [])[0];
    var span = mNum ? parseInt(mNum, 10) : (cols - 1);
    var labels = fracs.map(function (f, ix) {{
      if (ix === 0) return STR.now;
      if (ix === fracs.length - 1) return STR.horizon;
      var v = Math.round(f * span);
      return unit ? (unit + v) : ("t" + v);
    }});
    // a short horizon rounds two fracs to the same tick (e.g. mo2 /
    // mo2) — blank the colliding middle tick so the axis never repeats.
    for (var li = 1; li < labels.length - 1; li++) {{
      if (labels[li] === labels[li - 1]) labels[li] = "";
    }}
    return labels;
  }}

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

    // iter #17: the rotated y-axis caption ("outcome branch") used to
    // sit in the far-left gutter; we removed it because the section
    // title above the chart ("LIKELIHOOD BY BRANCH · OVER TIME")
    // already names what the rows are — the caption was duplicate ink
    // and was the reason the gutter was kept narrow (96px) and the
    // anchor labels were truncated to 11 chars. The gutter is now 124px
    // and the cap is 18 chars; the labels stay tinted by branch_type
    // and read in full.

    // row labels (left) — mono-font, only on rows in rowLabelAt (the
    // branch anchors); each tinted by branch_type (v10's rowLabelAt).
    var labelAt = GD.rowLabelAt || {{}};
    var labelColor = GD.rowLabelColor || {{}};
    for (var r = 0; r < rows; r++) {{
      if (!Object.prototype.hasOwnProperty.call(labelAt, r)) continue;
      var y = gy0 + r * cellH + cellH / 2 + 3.4;
      var lab = String(labelAt[r])
        .replace(/&/g, "&amp;").replace(/</g, "&lt;");
      // Iter #54 — row labels are prose future-names, not data codes, so
      // they render in the proportional sans font (friendlier + fits more
      // chars than mono in the same gutter). Axis ticks below stay mono.
      axis += '<text x="' + (PADX_L - 8) + '" y="' + y.toFixed(1) +
        '" text-anchor="end" font-family="var(--sans)" ' +
        'font-size="10" font-weight="500" fill="' +
        (labelColor[r] || "#b9bfc8") +
        '">' + lab + "</text>";
    }}
    // cells — DENSITY-SHADED: opacity is a gamma-corrected ratio of the
    // cell's mass to the grid max (v10 uses pow(p/max, 0.65)). The
    // gamma lifts mid-mass cells so the bright probability cloud reads
    // as a smooth concentrated shape, not a hard binary grid. On a fine
    // grid the gap shrinks so the cloud reads as continuous density.
    var gap = cellH < 12 ? 0.18 : 0.5;
    var rx = cellH < 12 ? 0.4 : 1;
    for (var c = 0; c < cols; c++) {{
      for (var r2 = 0; r2 < rows; r2++) {{
        var p = GD.grid[r2][c];
        // opacity is a gamma-corrected ratio of the cell's mass to a
        // NOW-vs-column blended max (v10 shades with pow(p/max, 0.65)).
        // The 50/50 blend keeps v10's gentle fade — the tight NOW core
        // stays brightest — without letting the spread-thin HORIZON
        // cloud wash out to near-black. No floor + no glow => the dark
        // valleys stay genuinely dark, so the cloud reads high-contrast.
        var cmx = (GD.colMax && GD.colMax[c]) || GD.gmax;
        var effMax = 0.5 * GD.gmax + 0.5 * cmx;
        var ratio = effMax > 0 ? Math.min(1, p / effMax) : 0;
        var op = Math.pow(ratio, 0.66).toFixed(3);
        var rgb = GD.rowColors[r2];
        var cx = PADX_L + c * cellW;
        var cy = gy0 + r2 * cellH;
        grid += '<rect class="heatmap-cell" x="' + (cx + gap).toFixed(2) +
          '" y="' + (cy + gap).toFixed(2) + '" width="' +
          (cellW - 2 * gap).toFixed(2) + '" height="' +
          (cellH - 2 * gap).toFixed(2) + '" rx="' + rx + '" fill="rgba(' +
          rgb + "," + op + ')" stroke="#0a0c11" stroke-width="0.3"' +
          ' data-step="' + c + '" data-row="' + r2 +
          '" data-prob="' + p.toFixed(4) + '"></rect>';
      }}
    }}
    // dashed centerline — marks the central reference band (v10's
    // .heat-zero-line), the band the probability mass is read against.
    var midRow = (typeof GD.centerRow === "number")
      ? GD.centerRow : Math.floor((rows - 1) / 2);
    var midY = gy0 + midRow * cellH + cellH / 2;
    grid += '<line x1="' + PADX_L + '" y1="' + midY.toFixed(1) +
      '" x2="' + (PADX_L + cols * cellW).toFixed(1) + '" y2="' +
      midY.toFixed(1) + '" stroke="#76808d" stroke-width="1" ' +
      'stroke-dasharray="3 3" opacity="0.65"></line>';
    // bottom NOW -> HORIZON axis — mono-font tick labels along the way.
    var axisY = PADY_T + GRID_H + 14;
    axis += '<line x1="' + PADX_L + '" y1="' + (axisY - 8) +
      '" x2="' + (SVG_W - PADX_R) + '" y2="' + (axisY - 8) +
      '" stroke="#232834" stroke-width="0.7"></line>';
    var ticks = xTickLabels(cols, GD.kind);
    var tickFracs = [0, 0.25, 0.5, 0.75, 1];
    for (var ti = 0; ti < ticks.length; ti++) {{
      var f = tickFracs[ti];
      var tx = PADX_L + f * GRID_W;
      var anchor = ti === 0 ? "start"
        : (ti === ticks.length - 1 ? "end" : "middle");
      var isEnd = ti === 0 || ti === ticks.length - 1;
      var fill = ti === ticks.length - 1 ? "#5e6ad2" : "#76808d";
      var lab2 = (ticks[ti] || "")
        .replace(/&/g, "&amp;").replace(/</g, "&lt;");
      axis += '<text x="' + tx.toFixed(1) + '" y="' + (axisY + 4) +
        '" font-family="var(--mono)" font-size="9" fill="' + fill +
        '" letter-spacing="' + (isEnd ? "0.1em" : "0.02em") +
        '" text-anchor="' + anchor + '">' +
        (isEnd ? lab2.toUpperCase() : lab2) + "</text>";
    }}

    $("heat-axis").innerHTML = axis;
    $("heat-grid").innerHTML = grid;
    updateModeNotes();
    hideCellPopover();
  }}

  // The two contextual notes below the grid are mutually exclusive and
  // mode-driven: idle-note only when truly idle (no prediction, no
  // camera); live-note only when a video source is driving the math;
  // a resolved prediction with no camera shows neither (the caption
  // already explains the grid). The one-line reading narrative also
  // swaps per mode — v10's data-derived answer sentence.
  function updateModeNotes() {{
    var mode = heatmapMode();
    // iter #19 P1.2: surface the mode on <body> so CSS can target it.
    // The preview-badge + desaturate styles key off body[data-mode=...]
    // so they activate only on the cold-start idle state.
    document.body.dataset.mode = mode;
    $("idle-note").classList.toggle("show", mode === "idle");
    $("live-note").classList.toggle("show", mode === "live");
    var narr = $("heat-narrative");
    if (narr) {{
      if (mode === "live") narr.textContent = STR.narrativeLive;
      else if (mode === "idle") narr.textContent = STR.narrativeIdle;
      else narr.textContent = STR.narrativePrediction;
    }}
  }}

  // ===== cell popover =====
  // For the prediction / idle cloud the grid is FINE-rowed: a single
  // cell is one slice of the probability cloud, so the popover reports
  // the BAND mass — the total density over the branch's band at that
  // time-column — which is the number the user actually cares about.
  function bandMassAt(row, step) {{
    if (!GD.anchors || GD.anchors.length === 0) {{
      return GD.grid[row][step];
    }}
    // which branch band does this fine row belong to?
    var nearBi = 0, nearD = Infinity;
    for (var bi = 0; bi < GD.anchors.length; bi++) {{
      var d = Math.abs(GD.anchors[bi] - row);
      if (d < nearD) {{ nearD = d; nearBi = bi; }}
    }}
    // band = the rows closest to this branch's anchor; sum their mass.
    var sum = 0;
    for (var rr = 0; rr < GD.rows; rr++) {{
      var owner = 0, od = Infinity;
      for (var bk = 0; bk < GD.anchors.length; bk++) {{
        var dd = Math.abs(GD.anchors[bk] - rr);
        if (dd < od) {{ od = dd; owner = bk; }}
      }}
      if (owner === nearBi) sum += GD.grid[rr][step];
    }}
    return sum;
  }}

  function plainReading(step, row) {{
    if (GD.kind === "live") {{
      var pl = (GD.grid[row][step] * 100).toFixed(1);
      return "Roughly a <strong>" + pl + "%</strong> chance Person A " +
        "is in the <strong>" + GD.rowLabels[row] + "</strong> zone, " +
        "<strong>" + step + (step === 1 ? " second" : " seconds") +
        "</strong> from now.";
    }}
    var pct = (bandMassAt(row, step) * 100).toFixed(1);
    var horizonTxt = STR.horizon;
    var when = step === GD.cols - 1
      ? "at your " + horizonTxt
      : "at horizon slice " + step + " of " + (GD.cols - 1);
    if (GD.kind === "idle") {{
      return "<strong>" + GD.rowLabels[row] + "</strong> — the grid " +
        "is uniform until a prediction runs. This branch would carry " +
        "<strong>" + pct + "%</strong> of the probability mass " +
        when + ".";
    }}
    return "<strong>" + GD.rowLabels[row] + "</strong> carries " +
      "<strong>" + pct + "%</strong> of the probability mass " + when +
      ". The bright band is where the future's mass concentrates.";
  }}

  function showCellPopover(target) {{
    var step = parseInt(target.getAttribute("data-step"), 10);
    var row = parseInt(target.getAttribute("data-row"), 10);
    var cellNo = row * GD.cols + step + 1;
    $("pop-badge").textContent = "cell #" + cellNo;
    // headline number: band mass for the prediction/idle cloud, the
    // raw cell for the live zone grid (matches plainReading).
    var headP = GD.kind === "live"
      ? GD.grid[row][step] : bandMassAt(row, step);
    $("pop-prob").textContent = (headP * 100).toFixed(1) + "%";
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
