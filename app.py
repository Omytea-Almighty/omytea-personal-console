"""Omytea Personal Future Console — Streamlit MVP.

Master plan §9 World Console minimum viable instantiation.

Run:
    streamlit run app.py

Mock mode (no API key needed):
    OMYTEA_CONSOLE_MOCK=1 streamlit run app.py
"""

from __future__ import annotations

import html as _html
import json
import os
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

# Iter #44 — bridge `st.secrets[turso]` → env vars BEFORE
# `import storage` (which reads OMYTEA_TURSO_URL at module-load
# time to decide whether to use the durable Turso libSQL backend
# or fall back to the ephemeral local SQLite). Without this
# bridge, a Streamlit Cloud deploy with `[turso]` configured in
# secrets.toml would still write to the ephemeral filesystem
# because the storage module already cached its backend choice
# at import time. See SETUP_TURSO.md for the founder setup.
try:
    if "turso" in st.secrets:
        _turso_cfg = st.secrets["turso"]
        if "url" in _turso_cfg:
            os.environ.setdefault(
                "OMYTEA_TURSO_URL", str(_turso_cfg["url"])
            )
        if "auth_token" in _turso_cfg:
            os.environ.setdefault(
                "OMYTEA_TURSO_AUTH_TOKEN",
                str(_turso_cfg["auth_token"]),
            )
except Exception:
    # secrets.toml missing or malformed — fall back to local
    # SQLite path. storage.py emits a stderr warning if the env
    # vars ARE set but libsql failed to import.
    pass

import _brand
# Iter #40 phase-1 — measurement-loop helpers were extracted from
# app.py into their own module to start unblocking the 6208-line
# monolith risk the founder flagged in round-3 audit. The original
# function bodies were deleted from app.py; this import keeps
# `_humanize_id` / `_dt_today_plus_months` / `_build_review_ics` /
# `_check_score_deeplink` callable from app.py (so existing
# `from app import _humanize_id` test patterns + internal call
# sites continue to work unchanged).
from _measurement_loop import (
    _build_review_ics,
    _check_score_deeplink,
    _dt_today_plus_months,
    _humanize_id,
)
from _heatmap_component import (
    branches_to_payload,
    render_heatmap_camera_component,
    render_live_video_v10,
)
import _i18n
from _i18n import T
import currency
import pricing
import storage
from compiler import compile_belief_program, compile_branch_drilldown
from console import (
    ConsoleResult,
    _parse_time_horizon_to_steps,
    availability_status,
    belief_program_to_console,
    build_branch_comparison_rows,
    build_coherence_chart_data,
    build_continuous_distribution,
    build_decision_timeline_mermaid,
    compute_calibration_delta,
    format_delta_p,
    normalize_evidence_list,
    storyform_narrative,
)
from scenarios import AVAILABLE_SCENARIOS
from scenarios.career_decision import (
    INPUT_FIELDS as CAREER_DECISION_FIELDS,
    SCENARIO_NAME as CAREER_DECISION_NAME,
    validate_input,
)

st.set_page_config(
    page_title="Omytea Console",
    layout="wide",
    # Founder audit 2026-05-26 P1: on mobile (~390px) the expanded
    # sidebar dominates the first paint — new users see the
    # navigation rail instead of the composer. Streamlit's "auto"
    # mode collapses on narrow viewports and expands on wide ones —
    # the correct first-paint behaviour. Desktop users still get
    # the rail; mobile users see the workspace first.
    initial_sidebar_state="auto",
)


# ============================================================
# Visual polish — CSS injection matching the v10 marketing
# design language (dark canvas, lavender accent #5e6ad2, teal
# success #58c5b4, Inter sans, refined hairlines and spacing).
# Kept additive: Streamlit's default widgets still work; we just
# soften the corners, tighten the contrast, and de-emoji the
# default chrome. CSS scoped to common Streamlit class names —
# may break on a future Streamlit upgrade and is intended to be
# easily revertible (delete this block).
# ============================================================
st.markdown(
    """
    <style>
    /* ========================================================
       Omytea Console — precise greyscale product UI
       Restyle-only. Reference: Linear (near-black canvas, a
       four-step surface ladder, hairline borders, NO shadows,
       NO gradients, NO glows). The lavender accent (#5e6ad2) is
       RARE — it appears only on the one primary CTA, focus
       rings, and links. Everything else is disciplined grey.
       Canvas #08090a · surface-1 #0f1011 · surface-2 #141516 ·
       surface-3 #18191a · hairline #23252a · hairline-strong
       #34343a · ink f7f8f8/d0d6e0/8a8f98/62666d.
       Premium = quiet, precise, flat. Easily revertible —
       delete this block.
       ======================================================== */

    /* ---- Typography — system sans, precise scale ---- */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, system-ui,
                     "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        letter-spacing: -0.005em;
        -webkit-font-smoothing: antialiased;
    }
    h1, h2, h3, h4 {
        font-family: -apple-system,BlinkMacSystemFont,system-ui,Roboto,Helvetica,Arial,sans-serif;
        letter-spacing: -0.018em;
        font-weight: 600;
        color: #f7f8f8;
    }
    /* Body copy — a precise grey, generous line-height. */
    p, li, label, .stMarkdown { color: #d0d6e0; line-height: 1.6; }

    /* Text links inside markdown. Streamlit auto-derives a bright
       link colour and pins it with `a,a:visited{...!important}`.
       Links are one of the few sanctioned uses of the accent — keep
       a restrained lavender with a thin low-opacity underline.
       !important + higher specificity is required to beat
       Streamlit's own !important link rule; text-decoration-line
       longhand survives Streamlit's text-decoration:none reset. */
    [data-testid="stMarkdownContainer"] a,
    [data-testid="stMarkdownContainer"] a:visited {
        color: #8a8f98 !important;
        text-decoration-line: underline !important;
        text-decoration-color: rgba(138,143,152,0.34) !important;
        text-decoration-thickness: 1px !important;
        text-underline-offset: 0.18em;
        transition: color 0.12s ease, text-decoration-color 0.12s ease;
    }
    [data-testid="stMarkdownContainer"] a:hover {
        color: #5e6ad2 !important;
        text-decoration-color: rgba(94,106,210,0.6) !important;
    }

    /* st.info alerts — Streamlit tints the info variant sky-blue.
       Re-tint to a NEUTRAL grey surface, not a coloured fill —
       these empty-state notices must read as quiet panels, not
       decoration. Scoped via :has() to the info variant only;
       success / warning / error keep their semantic colours. */
    [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {
        background-color: rgba(255,255,255,0.04) !important;
        border-color: #23252a !important;
    }
    [data-testid="stAlertContentInfo"] {
        color: #d0d6e0 !important;
    }

    /* ---- Canvas: a flat near-black. No atmospheric gradient —
       depth comes from the surface ladder + hairlines only. ---- */
    .stApp {
        background: #08090a;
    }
    /* Streamlit header — kept present so the sidebar collapse / expand
       control is always reachable; just made visually quiet. */
    [data-testid="stHeader"] {
        background: transparent !important;
        box-shadow: none !important;
    }
    .block-container { padding-top: 2.4rem; }

    /* ---- Sidebar: surface-1 lifted one step off the canvas, a
       crisp 1px right hairline. One flat plane, no glow. ---- */
    section[data-testid="stSidebar"] {
        background: #0f1011;
        border-right: 1px solid #23252a;
    }
    section[data-testid="stSidebar"] > div {
        background: transparent;
    }
    /* Iter 42d — mobile sidebar @media block EXTRACTED to its own
       dedicated _MOBILE_SIDEBAR_CSS constant + injected via a
       separate st.markdown call (see render_sidebar()). Cerebrum
       iter 22 learning: "layout-critical CSS buried in the
       737-line global <style> can silently never reach the
       CSSOM" — live-verified iter 43 that this @media block was
       NOT in document.styleSheets despite being declared here.
       The smaller, dedicated style block loads reliably. */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.6rem;
        padding-left: 1.15rem;
        padding-right: 1.15rem;
    }
    section[data-testid="stSidebar"] h1 {
        font-family: -apple-system,BlinkMacSystemFont,system-ui,Roboto,Helvetica,Arial,sans-serif;
        font-size: 17px !important;
        letter-spacing: -0.015em;
        font-weight: 600;
    }

    /* ---- Buttons — quiet by default. A flat surface fill, ONE
       fine hairline, 8px radius, a restrained GREY hover. No
       glow, no accent: secondary buttons are disciplined grey. ---- */
    .stButton > button, .stDownloadButton > button,
    .stLinkButton > a {
        border-radius: 8px;
        border: 1px solid #23252a;
        background: #141516;
        color: #d0d6e0;
        font-weight: 500;
        font-size: 13.5px;
        letter-spacing: -0.003em;
        padding: 9px 14px;
        box-shadow: none;
        transition: border-color 0.15s ease, background 0.15s ease,
                    color 0.15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover,
    .stLinkButton > a:hover {
        background: #18191a;
        border-color: #34343a;
        color: #f7f8f8;
        box-shadow: none;
    }
    .stButton > button:active, .stDownloadButton > button:active {
        background: #1c1d1e;
    }
    .stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
    .stLinkButton > a:focus-visible {
        outline: none;
        border-color: #5e6ad2;
        box-shadow: 0 0 0 2px rgba(94,106,210,0.5);
    }
    /* Primary — the ONE assertive control. A solid lavender plane,
       white label, 8px radius. No glow, no inset highlight — just
       a clean, confident accent fill. */
    .stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"],
    .stButton > button[kind="primaryFormSubmit"],
    .stFormSubmitButton > button {
        background: #5e6ad2;
        border: 1px solid #5e6ad2;
        color: #ffffff;
        font-weight: 600;
        font-size: 13px;
        border-radius: 6px;
        padding: 7px 12px;
        box-shadow: none;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[kind="primaryFormSubmit"]:hover,
    .stFormSubmitButton > button:hover {
        background: #828fff;
        border-color: #828fff;
        color: #ffffff;
        box-shadow: none;
    }
    .stButton > button[kind="primary"]:active,
    .stButton > button[kind="primaryFormSubmit"]:active,
    .stFormSubmitButton > button:active {
        background: #5e69d1;
        box-shadow: none;
    }
    .stFormSubmitButton > button:focus-visible,
    .stButton > button[kind="primary"]:focus-visible {
        box-shadow: 0 0 0 2px rgba(94,106,210,0.5);
    }

    /* ---- Sidebar buttons: quieter than the main column. History /
       nav rows read as a flat rail; hover is a subtle grey lift. ---- */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent;
        border: 1px solid transparent;
        box-shadow: none;
        text-align: left;
        justify-content: flex-start;
        color: #8a8f98;
        font-weight: 450;
        font-size: 13px;
        padding: 7px 11px;
        border-radius: 6px;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.05);
        border-color: transparent;
        color: #f7f8f8;
        box-shadow: none;
    }
    /* The "New prediction" button — the rail's primary action. The
       Linear / ChatGPT new-action pattern: NOT a loud accent fill — a
       quiet surface lift (lifted dark plane, a stronger hairline,
       bright ink). It reads as primary through elevation + a bright
       label, never through colour. Every other sidebar button stays a
       flat quiet row. NB: scope to [kind="primary"] — NOT
       :first-of-type, which would paint the whole nav rail. */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #1b1d22 !important;
        border: 1px solid #34343a !important;
        border-radius: 6px !important;
        color: #f7f8f8 !important;
        font-weight: 600;
        font-size: 13px;
        text-align: center;
        justify-content: center;
        padding: 7px 11px;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: #22242a !important;
        border-color: #3e3e44 !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:active {
        background: #18191d !important;
        box-shadow: none !important;
    }
    /* bug-035 follow-up: force-dark the "New prediction" button. The
       previous sidebar [kind="primary"] rule (above) lost to Streamlit's
       higher-specificity / inline primary-color injection. This rule
       scopes by the unique st-key class — adds an attribute selector of
       higher specificity — and stacks !important on EVERY colour-bearing
       property (including background-color separately from background)
       so any inline style or theme variable is overridden. */
    section[data-testid="stSidebar"] [class*="st-key-_nav_new_prediction"] button,
    section[data-testid="stSidebar"] [class*="st-key-_nav_new_prediction"] button[kind="primary"],
    section[data-testid="stSidebar"] div[class*="st-key-_nav_new_prediction"] button {
        background: #1b1d22 !important;
        background-color: #1b1d22 !important;
        border: 1px solid #34343a !important;
        border-color: #34343a !important;
        border-radius: 6px !important;
        color: #f7f8f8 !important;
        font-size: 13px !important;
        padding: 7px 11px !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] [class*="st-key-_nav_new_prediction"] button:hover,
    section[data-testid="stSidebar"] [class*="st-key-_nav_new_prediction"] button[kind="primary"]:hover {
        background: #22242a !important;
        background-color: #22242a !important;
        border-color: #3e3e44 !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] [class*="st-key-_nav_new_prediction"] button:active,
    section[data-testid="stSidebar"] [class*="st-key-_nav_new_prediction"] button[kind="primary"]:active {
        background: #15161a !important;
        background-color: #15161a !important;
        box-shadow: none !important;
    }

    /* ---- Account + footer bottom-pin: these rules, placed mid-way
       through this big <style>, silently never reached the CSSOM
       (bug-034 — confirmed live: footRulesInCSSOM=0). The working pin
       now ships as the dedicated _SIDEBAR_PIN_CSS <style> injected by
       render_sidebar(). ---- */

    /* ---- Text inputs / textareas / selects — a flat surface-1
       fill, ONE 1px hairline, 8px radius, comfortable padding, a
       clean accent focus ring. BaseWeb wraps the field in nested
       nodes; the outer wrapper carries the border, the inner nodes
       go transparent so there is exactly one visible line. ---- */
    .stTextInput div[data-baseweb="base-input"],
    .stTextArea div[data-baseweb="base-input"],
    div[data-baseweb="textarea"],
    .stNumberInput div[data-baseweb="base-input"],
    .stSelectbox div[data-baseweb="select"] > div,
    div[data-baseweb="select"] > div {
        background: #0f1011 !important;
        border: 1px solid #23252a !important;
        border-radius: 8px !important;
        color: #f7f8f8 !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    /* Inner BaseWeb nodes — keep them clear so the wrapper's
       single hairline is the only line the eye sees. */
    [data-testid="stTextArea"] textarea,
    [data-testid="stTextInput"] input,
    .stTextInput input, .stTextArea textarea,
    .stNumberInput input,
    div[data-baseweb="base-input"] input,
    div[data-baseweb="textarea"] textarea {
        background: transparent !important;
        border: none !important;
        color: #f7f8f8 !important;
        font-size: 14px !important;
        padding: 9px 12px !important;
        -webkit-text-fill-color: #f7f8f8;
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder,
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        /* Placeholders carry real guidance — a legible tertiary
           grey, clearly dimmer than typed input. */
        color: #62666d !important;
        -webkit-text-fill-color: #62666d;
    }
    /* Focus — a 2px accent ring, no glow. */
    .stTextInput div[data-baseweb="base-input"]:focus-within,
    .stTextArea div[data-baseweb="base-input"]:focus-within,
    div[data-baseweb="textarea"]:focus-within,
    .stNumberInput div[data-baseweb="base-input"]:focus-within,
    div[data-baseweb="select"]:focus-within > div {
        border-color: #5e6ad2 !important;
        box-shadow: 0 0 0 2px rgba(94,106,210,0.5) !important;
    }
    /* Hover — a quiet brightening of the hairline. */
    .stTextInput div[data-baseweb="base-input"]:hover,
    .stTextArea div[data-baseweb="base-input"]:hover,
    div[data-baseweb="textarea"]:hover,
    div[data-baseweb="select"]:hover > div {
        border-color: #34343a !important;
    }
    /* Suppress BaseWeb's own focus outline on the inner field. */
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stTextInput"] input:focus,
    div[data-baseweb="base-input"] input:focus,
    div[data-baseweb="textarea"] textarea:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    /* Selectbox + popover dropdown panels — a surface-3 card with
       a fine hairline. A modest shadow is acceptable on a true
       floating menu (depth, not decoration). */
    div[data-baseweb="popover"] [role="listbox"],
    div[data-baseweb="menu"] {
        background: #18191a !important;
        border: 1px solid #23252a !important;
        border-radius: 8px !important;
        box-shadow: 0 12px 34px rgba(0,0,0,0.6) !important;
    }
    li[role="option"], div[data-baseweb="menu"] li {
        font-size: 13.5px !important;
        color: #d0d6e0 !important;
    }
    li[role="option"]:hover, div[data-baseweb="menu"] li:hover {
        background: rgba(255,255,255,0.05) !important;
        color: #f7f8f8 !important;
    }
    li[role="option"][aria-selected="true"] {
        background: rgba(255,255,255,0.07) !important;
        color: #f7f8f8 !important;
    }

    /* ---- Labels above widgets — a quiet subtle grey, light
       weight, just enough presence. ---- */
    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stNumberInput label, .stRadio label, .stFileUploader label,
    .stCheckbox label, .stToggle label {
        color: #8a8f98 !important;
        font-size: 12.5px !important;
        font-weight: 500 !important;
        letter-spacing: 0.004em;
    }
    /* Toggle / checkbox inline labels read at body size — they
       are statements, not field captions. */
    .stToggle label p, .stCheckbox label p {
        color: #d0d6e0 !important;
        font-size: 13.5px !important;
    }

    /* ---- Expanders — card language: a flat surface-1 plane,
       ONE 1px hairline, 12px radius. The "More details" composer
       expander reads as a quiet card you can open. ---- */
    [data-testid="stExpander"] {
        border: 1px solid #23252a;
        border-radius: 12px;
        background: #0f1011;
        overflow: hidden;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        margin-bottom: 7px;
        border-radius: 8px;
        border-color: #23252a;
        background: #141516;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background: #141516;
        padding: 9px 12px;
        font-size: 12.5px;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
        background: #18191a;
    }
    section[data-testid="stSidebar"]
        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background: #141516;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] details > summary {
        background: #0f1011;
        border: none;
        border-radius: 0;
        padding: 11px 15px;
        color: #d0d6e0;
        font-weight: 500;
        font-size: 13px;
        transition: background 0.15s ease, color 0.15s ease;
    }
    [data-testid="stExpander"] summary:hover {
        background: #141516;
        color: #f7f8f8;
    }
    /* Expander chevron — a quiet subtle grey, brightens with the row. */
    [data-testid="stExpander"] summary svg { fill: #8a8f98; }
    [data-testid="stExpander"] summary:hover svg { fill: #d0d6e0; }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background: #0f1011;
        padding: 6px 15px 14px;
    }

    /* ---- Toggles — the live-video / 玄学-lens switches. Off:
       a surface-3 track with a fine hairline + a pale knob.
       On: a solid accent track, white knob — a genuine toggle,
       one of the few sanctioned accent surfaces. No glow. ---- */
    .stToggle [data-baseweb="checkbox"] [role="checkbox"],
    div[data-baseweb="toggle"] {
        background: #18191a !important;
        border: 1px solid #23252a !important;
    }
    .stToggle [data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"],
    div[data-baseweb="toggle"][aria-checked="true"],
    button[role="switch"][aria-checked="true"] {
        background: #5e6ad2 !important;
        border-color: #5e6ad2 !important;
        box-shadow: none !important;
    }
    /* The knob — a clean disc. */
    .stToggle [data-baseweb="checkbox"] [role="checkbox"] > div,
    div[data-baseweb="toggle"] > div {
        background: #d0d6e0 !important;
    }
    .stToggle [data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] > div,
    div[data-baseweb="toggle"][aria-checked="true"] > div {
        background: #ffffff !important;
    }
    /* Plain checkbox (owner-bias flag) — a hairline box, accent
       when checked. */
    .stCheckbox [data-baseweb="checkbox"] [role="checkbox"] {
        background: #0f1011 !important;
        border: 1px solid #23252a !important;
        border-radius: 4px !important;
    }
    .stCheckbox [data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] {
        background: #5e6ad2 !important;
        border-color: #5e6ad2 !important;
    }

    /* ---- Popover panel (the "+ Attach" control) — a surface-3
       card: a fine hairline, 12px radius. The trigger button
       inherits the secondary-button language above. ---- */
    div[data-baseweb="popover"] > div {
        background: #18191a !important;
        border: 1px solid #23252a !important;
        border-radius: 12px !important;
        box-shadow: 0 16px 40px rgba(0,0,0,0.6) !important;
    }
    [data-testid="stPopoverBody"] {
        background: #18191a !important;
        padding: 16px !important;
    }

    /* ---- File uploader dropzone — input-card look, a dashed
       hairline that brightens on hover. ---- */
    [data-testid="stFileUploaderDropzone"] {
        background: #0f1011 !important;
        border: 1px dashed #34343a !important;
        border-radius: 8px !important;
        transition: border-color 0.15s ease, background 0.15s ease;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #3e3e44 !important;
        background: #141516 !important;
    }

    /* ---- Sliders — the accent track is a sanctioned use; no glow. ---- */
    .stSlider [role="slider"] {
        background: #5e6ad2;
        box-shadow: none;
    }
    .stSlider [data-baseweb="slider"] div[data-testid] { background: #5e6ad2; }

    /* ---- Radio (Settings language picker) ---- */
    .stRadio div[role="radiogroup"] label {
        background: #0f1011;
        border: 1px solid #23252a;
        border-radius: 6px;
        padding: 3px 10px;
        transition: border-color 0.14s ease;
    }
    .stRadio div[role="radiogroup"] label:hover {
        border-color: #34343a;
    }

    /* ---- Dividers — a flat hairline, not a fading rule ---- */
    hr {
        border: none !important;
        height: 1px !important;
        background: #23252a !important;
        opacity: 1;
    }

    /* ---- Captions ---- */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #62666d !important;
        letter-spacing: 0.004em;
    }

    /* ---- Links — quiet grey, accent only on hover ---- */
    a, a:visited {
        color: #8a8f98 !important;
        text-decoration: none !important;
        transition: color 0.14s ease;
    }
    a:hover {
        color: #5e6ad2 !important;
        text-decoration: underline !important;
        text-underline-offset: 2px;
    }

    /* ---- Code / inline code — a neutral surface, not an
       accent-tinted block ---- */
    code {
        background: rgba(255,255,255,0.05) !important;
        color: #d0d6e0 !important;
        padding: 1px 5px !important;
        border-radius: 4px !important;
        font-size: 0.86em !important;
    }
    pre, [data-testid="stCodeBlock"] {
        background: #0f1011 !important;
        border: 1px solid #23252a !important;
        border-radius: 8px !important;
    }

    /* ---- Hide Streamlit dev chrome ---- (P1.1 / founder audit 2026-05-26)
       The default Streamlit Cloud chrome (top-right Share/star/pencil/Fork/
       GitHub icons + the floating bottom-right "Manage app" pill + the
       "Hosted with Streamlit" viewer badge) ships every visitor a
       developer-demo first impression. A normal user reads these as
       "this is open dev infrastructure, not a product." Suppress them
       so the workspace is the product surface. The sidebar collapse
       toggle (different testid) is intentionally NOT hidden — users
       still need a way to open/close the rail.
    */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    /* Top-right toolbar — Share / star / pencil / Fork / GitHub */
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stToolbarActions"] { display: none !important; }
    [data-testid="stActionButtonIcon"] { display: none !important; }
    /* The thin coloured ribbon Streamlit injects at the very top */
    [data-testid="stDecoration"] { display: none !important; }
    /* Bottom-right floating Streamlit Cloud "Manage app" pill */
    [data-testid="manage-app-button"] { display: none !important; }
    /* "Made with Streamlit" badge — the canonical hiding selector
       changed across versions; cover the main variants. */
    .viewerBadge_container__1QSob,
    .viewerBadge_link__1S137,
    a[href*="streamlit.io/cloud"],
    a[href*="share.streamlit.io"][title*="Made"] {
        display: none !important;
    }
    /* The status-running spinner top-right also reads as dev chrome. */
    [data-testid="stStatusWidget"] { display: none !important; }

    /* ---- Metrics: a large precise value; the container reads as
       a quiet card. ---- */
    [data-testid="stMetric"] {
        background: #0f1011;
        border: 1px solid #23252a;
        border-radius: 12px;
        padding: 14px 16px;
    }
    [data-testid="stMetricValue"] {
        font-family: -apple-system,BlinkMacSystemFont,system-ui,Roboto,Helvetica,Arial,sans-serif;
        font-size: 32px;
        font-weight: 600;
        color: #f7f8f8;
        letter-spacing: -0.02em;
    }
    [data-testid="stMetricLabel"] {
        color: #8a8f98;
        font-size: 11.5px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    /* ---- Bordered containers — the composer card + embedded
       panels. A flat surface-1 plane, ONE 1px hairline, 12px
       radius. No gradient, no shadow — depth via the surface
       ladder. ---- */
    [data-testid="stContainer"][data-border="true"],
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stContainer"]:has(> div[data-testid="stContainerBorder"]) {
        background: #0f1011;
        border: 1px solid #23252a !important;
        border-radius: 12px;
        box-shadow: none;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 1px solid #23252a;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8a8f98;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        color: #f7f8f8 !important;
    }
    .stTabs [data-baseweb="tab-highlight"] { background: #5e6ad2 !important; }

    /* ---- Alerts — calm, fine-bordered, not loud blocks. The
       neutral base is a quiet surface; semantic variants get a
       restrained hairline tint only (success / error / warning
       keep their meaning without shouting). ---- */
    [data-testid="stAlert"] {
        border-radius: 10px;
        border: 1px solid #23252a;
        background: rgba(255,255,255,0.04);
    }
    [data-testid="stAlert"] p { color: #d0d6e0 !important; }
    /* Success — a restrained green hairline. */
    [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]),
    div[data-baseweb="notification"][kind="positive"] {
        border-color: rgba(39,166,68,0.4);
        background: rgba(39,166,68,0.06);
    }
    /* Error — a restrained red hairline. */
    [data-testid="stAlert"]:has([data-testid="stAlertContentError"]),
    div[data-baseweb="notification"][kind="negative"] {
        border-color: rgba(220,76,90,0.4);
        background: rgba(220,76,90,0.06);
    }
    /* Warning — a restrained amber hairline. */
    [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]),
    div[data-baseweb="notification"][kind="warning"] {
        border-color: rgba(190,150,70,0.4);
        background: rgba(190,150,70,0.06);
    }

    /* ---- Tables / dataframes ---- */
    [data-testid="stTable"], .stDataFrame {
        border: 1px solid #23252a;
        border-radius: 8px;
    }

    /* ---- Scrollbar — thin, near-black ---- */
    ::-webkit-scrollbar { width: 9px; height: 9px; }
    ::-webkit-scrollbar-track { background: #08090a; }
    ::-webkit-scrollbar-thumb {
        background: #23252a;
        border-radius: 6px;
        border: 2px solid #08090a;
    }
    ::-webkit-scrollbar-thumb:hover { background: #34343a; }

    /* ========================================================
       Spacing rhythm + composer polish — premium through
       restraint. One consistent vertical cadence so the
       workspace breathes; the modality row aligned; widget
       labels on one quiet type scale.
       ======================================================== */

    /* A calm, even gap between stacked widgets — the workspace
       reads as a measured rhythm, not a cramped stack. Streamlit's
       default vertical block gap is tightened/standardised here. */
    section[data-testid="stMain"]
        div[data-testid="stVerticalBlock"] {
        gap: 0.85rem;
    }
    /* The composer pane stays a touch tighter than the page so its
       inputs group without crowding. */
    section[data-testid="stMain"]
        [data-testid="stExpander"]
        div[data-testid="stVerticalBlock"] {
        gap: 0.6rem;
    }

    /* Modality row (+Attach · Live video · 玄学 lens) — vertically
       centred so the popover trigger and the two toggles sit on one
       calm baseline instead of drifting. */
    section[data-testid="stMain"]
        div[data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    /* The popover trigger reads as a peer of the toggles — same
       quiet secondary-button language, comfortable height. */
    [data-testid="stPopover"] > div > button {
        width: 100%;
    }

    /* Form fields inside the composer — generous, even breathing
       room so the conditions never feel boxed-in. */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
    }
    [data-testid="stForm"]
        div[data-testid="stVerticalBlock"] {
        gap: 0.7rem;
    }

    /* Widget labels — one type scale across every input: a quiet
       --ink-2 grey, light, with a hair of space below so the label
       and its field read as a pair, not a collision. */
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label {
        margin-bottom: 4px !important;
        font-size: 12.5px !important;
        letter-spacing: 0.004em;
    }

    /* Headings — a clear, restrained type scale. */
    h1 { font-size: 30px !important; line-height: 1.2; }
    h2 { font-size: 22px !important; line-height: 1.25; }
    h3 { font-size: 17px !important; line-height: 1.3; }
    h4 { font-size: 14.5px !important; line-height: 1.35; }

    /* Caption hint lines sit close under their control. */
    section[data-testid="stMain"]
        [data-testid="stCaptionContainer"] {
        margin-top: 2px;
        line-height: 1.5;
    }

    /* Segmented control (the output-view switch) — a flat surface
       track, one hairline; the selected segment lifts onto a
       neutral grey surface (surface lift = selected, the Linear
       pattern). No accent fill, no loud pill. */
    [data-testid="stSegmentedControl"] [role="radiogroup"] {
        background: #0f1011;
        border: 1px solid #23252a;
        border-radius: 8px;
        padding: 2px;
        gap: 2px;
    }
    [data-testid="stSegmentedControl"] [role="radio"] {
        border: none !important;
        background: transparent !important;
        color: #8a8f98 !important;
        border-radius: 6px !important;
        font-size: 12.5px !important;
        font-weight: 500 !important;
    }
    [data-testid="stSegmentedControl"] [role="radio"]:hover {
        color: #d0d6e0 !important;
        background: rgba(255,255,255,0.04) !important;
    }
    [data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"] {
        background: rgba(255,255,255,0.07) !important;
        color: #f7f8f8 !important;
    }

    /* Spinner accent — the accent thread, not Streamlit red. */
    [data-testid="stSpinner"] svg { color: #5e6ad2 !important; }
    [data-testid="stSpinner"] i {
        border-top-color: #5e6ad2 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Iter 18 P1.1 — outer-page chrome hide via parent-frame JS hop.
# ============================================================
# Streamlit Cloud renders the app inside an iframe at /~/+/. The
# "Manage app" pill, the Streamlit-Cloud header, and a few other
# branding fixtures live in the OUTER document — so CSS injected
# into the Streamlit app's own document (via st.markdown above)
# cannot reach them; that's why P1.1 hid the inner chrome but the
# bottom-right "Manage app" pill remained.
#
# This components.html block creates a tiny same-origin grandchild
# iframe that hops up two levels to window.parent.parent.document
# and hides the outer-page chrome. All three frames share the
# *.streamlit.app origin so the access is permitted. Wrapped in
# try/catch and a MutationObserver so a late-mounting pill is also
# caught. height=0 so the helper iframe doesn't take any visual
# space.
#
# Honest scope: this only works on Streamlit Cloud's same-origin
# layout. If they ever move chrome cross-origin we degrade
# silently to whatever the iframe-level CSS already hides.
components.html(
    """
    <script>
    (function () {
      var SELECTORS = [
        '[data-testid="manage-app-button"]',
        '[data-testid="stAppDeployButton"]',
        'a[href*="share.streamlit.io"]',
        'a[href*="streamlit.io/cloud"]',
        'iframe[title="streamlit_app"] ~ div',
      ];
      function hideIn(doc) {
        if (!doc) return false;
        var hidAny = false;
        SELECTORS.forEach(function (s) {
          var nodes = doc.querySelectorAll(s);
          nodes.forEach(function (n) {
            n.style.setProperty("display", "none", "important");
            hidAny = true;
          });
        });
        return hidAny;
      }
      function tryHide() {
        try {
          // Two levels up: this iframe -> Streamlit app iframe ->
          // outer Streamlit-Cloud page.
          var outer = window.parent && window.parent.parent
            ? window.parent.parent.document : null;
          hideIn(outer);
          // Defensive: also try the immediate parent in case the
          // app is iframed only once on a future Cloud layout.
          var direct = window.parent ? window.parent.document : null;
          hideIn(direct);
        } catch (e) { /* cross-origin — degrade silently */ }
      }
      // Initial sweep on a couple of paint cycles (the pill is
      // lazy-mounted after first paint).
      tryHide();
      setTimeout(tryHide, 250);
      setTimeout(tryHide, 1500);
      // Long-tail: a MutationObserver on the outer document
      // catches re-mounts. Best-effort — silently skipped if the
      // origin check fails.
      try {
        var outer = window.parent && window.parent.parent
          ? window.parent.parent.document : null;
        if (outer && outer.body) {
          var mo = new MutationObserver(function () { tryHide(); });
          mo.observe(outer.body, { childList: true, subtree: true });
        }
      } catch (e) { /* silently skipped */ }
    })();
    </script>
    """,
    height=0,
)


# ============================================================
# Sidebar — system status + measurement-update entry
# ============================================================

# Route kinds returned by render_sidebar(). A route is a 2-tuple
# (kind, payload):
#   ("workspace", None)              — the default new-prediction composer
#   ("history", prediction_id:str)   — open a past prediction (viewer)
#   ("secondary", mode_key:str)      — a transitional secondary surface
#   ("settings", None)               — the routed Settings surface
ROUTE_WORKSPACE = "workspace"
ROUTE_HISTORY = "history"
ROUTE_SECONDARY = "secondary"
ROUTE_SETTINGS = "settings"

# Secondary surfaces — genuinely standalone pages with no home in the
# unified composer. The 玄学 lens, video query, and live webcam used to
# live here too, but they ARE the composer now (the lens toggle / the
# Attach control / the Live-video toggle), so routing to them as separate
# pages was a redundant SECOND entry point — they were removed from
# "More". What remains is what the composer has no slot for: scoring a
# past outcome, the calibration track record, and pricing.
SECONDARY_MODES_ALL = (
    "Measurement update",
    "Calibration history",
    "Pricing & pre-order",
)
SECONDARY_MODE_I18N = {
    "Measurement update": "mode.measurement_update",
    "Calibration history": "mode.calibration_history",
    "Pricing & pre-order": "mode.pricing",
}


# Iter #42 B2 — hide non-PMF surfaces during beta. Founder round-4
# audit: "Pricing/Live video/Attach toggles OFF by default during
# beta; session-state toggle for founder to flip back on". During
# beta we're trying to learn whether the predict→calendar→score
# loop has PMF — surfacing Pricing (a pre-order page that implies
# the product is mature enough to monetize) and the modality
# toggles (live video / file attach are research extensions, not
# the PMF candidate) muddies the read. The 玄学 lens stays visible
# because the founder explicitly ratified it as a product surface
# (2026-05-26 "玄学还是要的" + WORK_PLAN_V415 two-channel framing).
#
# Override: append `?dev=1` to the URL to re-enable all surfaces.
# That's how the founder demos the full product without shipping
# new code.
def _show_research_features() -> bool:
    """Whether the non-PMF surfaces (Pricing / Live video / Attach)
    are shown. Default False during beta; set True via `?dev=1` URL
    param OR by setting `_show_research_features` in session_state
    (founder-only escape hatch).
    """
    if bool(st.session_state.get("_show_research_features", False)):
        return True
    try:
        params = st.query_params
        if params and str(params.get("dev", "")).strip() in ("1", "true", "yes"):
            # Persist for the rest of the session so the founder
            # doesn't have to keep the URL param visible.
            st.session_state["_show_research_features"] = True
            return True
    except Exception:
        pass
    return False


def _secondary_modes() -> tuple[str, ...]:
    """SECONDARY_MODES filtered to what should be visible right now.
    During beta we drop "Pricing & pre-order" — selling a pre-order
    before PMF is the wrong signal to send a beta tester.
    """
    if _show_research_features():
        return SECONDARY_MODES_ALL
    return tuple(
        m for m in SECONDARY_MODES_ALL
        if m != "Pricing & pre-order"
    )


# Back-compat alias — older sites and tests reference the original
# constant name. Module-level evaluation: when modules import
# `from app import SECONDARY_MODES`, they get the full tuple (so a
# test that pre-dates the beta gate still sees all three modes).
# Runtime call sites use `_secondary_modes()` so dev-mode behavior
# is captured on every render.
SECONDARY_MODES = SECONDARY_MODES_ALL


def _render_back_bar() -> None:
    """A "← back to workspace" control at the top of every non-workspace
    surface.

    The workspace composer is the single home: every secondary page and
    the history viewer MUST always be closeable. Without this the user
    lands on e.g. Pricing with no way back except the differently-named
    "New prediction" button — the "opens but won't close" trap the
    founder flagged.
    """
    if st.button(
        T("nav.back_workspace"),
        key="_back_to_workspace",
        type="tertiary",
    ):
        st.session_state._route = (ROUTE_WORKSPACE, None)
        st.rerun()


def session_user_id() -> str:
    """Stable user handle the history rail + every save site key off.

    A signed-in account (Google OIDC via ``st.login``) owns its
    prediction history across sessions and devices — its email is the
    id. Signed out, a per-session anonymous handle (`tester-XXXX`) is
    used, matching the auto-suggested composer form handle.
    """
    # A signed-in account takes precedence; touching st.user when no
    # [auth] secrets exist raises, so guard it.
    try:
        if st.user.is_logged_in and st.user.email:
            return str(st.user.email)
    except Exception:
        pass
    if "_default_user_id" not in st.session_state:
        import random
        import string
        rand_tail = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4)
        )
        st.session_state._default_user_id = f"tester-{rand_tail}"
    return str(st.session_state._default_user_id)


def _history_item_label(rec: "storage.PredictionRecord") -> str:
    """One-line label for a history-rail row.

    Prefers a human-meaningful field from the saved input; falls back
    to the scenario name + short id so the row is never blank.
    """
    inp = rec.user_input or {}
    for candidate in ("current_role", "question", "decision", "title"):
        val = inp.get(candidate)
        if isinstance(val, str) and val.strip():
            text = val.strip()
            return text if len(text) <= 38 else text[:37] + "…"
    scen = (rec.scenario or "prediction").replace("_", " ")
    return f"{scen} · {rec.prediction_id[:6]}"


def _date_bucket(created_at: float) -> str:
    """ChatGPT-style date grouping for the history rail."""
    import datetime as _dt

    now = _dt.datetime.now()
    then = _dt.datetime.fromtimestamp(float(created_at))
    days = (now.date() - then.date()).days
    if days <= 0:
        return T("history.bucket.today")
    if days == 1:
        return T("history.bucket.yesterday")
    if days < 7:
        return T("history.bucket.prev7")
    if days < 30:
        return T("history.bucket.prev30")
    return then.strftime("%Y-%m")


# ----------------------------------------------------------------------
# Iter #51 — history-rail read cache (the single biggest per-click
# latency win). The rail re-queries Turso on EVERY rerun: 4 separate
# network round-trips (predictions / categories / labels / label-map) to
# us-east-1, each opening a fresh libSQL connection. Read-only reruns
# (every button click, toggle, expander) are the common case and do NOT
# change this data — only a save / category edit / label edit does. So we
# cache the reads (60s TTL backstop) and explicitly invalidate on those
# writes. Founder report: "clicking any button is very slow." This turns
# the typical click from 4 network round-trips into a cache hit.
@st.cache_data(ttl=60, show_spinner=False)
def _cached_user_predictions(uid: str) -> Any:
    return storage.list_user_predictions(uid)


@st.cache_data(ttl=60, show_spinner=False)
def _cached_categories(uid: str) -> Any:
    return storage.list_categories(uid)


@st.cache_data(ttl=60, show_spinner=False)
def _cached_user_labels(uid: str) -> Any:
    return storage.list_user_labels(uid)


@st.cache_data(ttl=60, show_spinner=False)
def _cached_label_map(pred_ids: tuple[str, ...]) -> Any:
    return storage.labels_for_predictions(list(pred_ids))


def _invalidate_history_cache() -> None:
    """Drop the cached history reads so the next rerun reflects a write
    immediately (a just-saved prediction must appear in the rail at once,
    not after the TTL)."""
    for _fn in (
        _cached_user_predictions,
        _cached_categories,
        _cached_user_labels,
        _cached_label_map,
    ):
        try:
            _fn.clear()
        except Exception:  # noqa: BLE001 — cache clear must never crash a write
            pass


def _render_history_rail(route: tuple[str, Any]) -> tuple[str, Any]:
    """The user-organized history tree (Stage 4).

    A flat date-grouped list when the user has created no categories;
    a category-grouped tree once they have. The user owns the taxonomy
    — there is a create-category control, rename / delete, per-
    prediction category assignment + labels (those last two live in
    the prediction viewer), and a group-by-category / filter-by-label
    rail. Returns the (possibly updated) route tuple.
    """
    uid = session_user_id()
    try:
        predictions = _cached_user_predictions(uid)
        categories = _cached_categories(uid)
        all_labels = _cached_user_labels(uid)
        label_map = _cached_label_map(
            tuple(p.prediction_id for p in predictions)
        )
    except Exception:  # noqa: BLE001 — a broken DB must not blank the app
        predictions, categories, all_labels, label_map = [], [], [], {}

    # ---- Manage-categories control ----
    with st.sidebar.expander(T("history.manage"), expanded=False):
        new_cat = st.text_input(
            T("history.new_category"),
            key="_new_category_name",
            placeholder=T("history.new_category.ph"),
        )
        if st.button(
            T("history.create_category"),
            key="_create_category_btn",
            use_container_width=True,
        ):
            if new_cat.strip():
                storage.create_category(uid, new_cat.strip())
                _invalidate_history_cache()
                st.session_state["_new_category_name"] = ""
                st.rerun()
        # rename / delete each existing category
        for cat in categories:
            cc1, cc2 = st.columns([4, 1])
            with cc1:
                renamed = st.text_input(
                    T("history.category_name"),
                    value=cat.name,
                    key=f"_catname_{cat.category_id}",
                    label_visibility="collapsed",
                )
            with cc2:
                if st.button(
                    "✕",
                    key=f"_catdel_{cat.category_id}",
                    help=T("history.delete_category"),
                ):
                    storage.delete_category(cat.category_id)
                    _invalidate_history_cache()
                    st.rerun()
            if renamed.strip() and renamed.strip() != cat.name:
                storage.rename_category(cat.category_id, renamed.strip())
                _invalidate_history_cache()
                st.rerun()

    # ---- Label filter ----
    active_label = st.session_state.get("_history_label_filter", "")
    if all_labels:
        filter_options = [""] + all_labels
        chosen_label = st.sidebar.selectbox(
            T("history.filter_by_label"),
            options=filter_options,
            format_func=lambda x: (
                T("history.all_labels") if x == "" else f"# {x}"
            ),
            index=(
                filter_options.index(active_label)
                if active_label in filter_options else 0
            ),
            key="_history_label_filter",
        )
        active_label = chosen_label

    # ---- Apply the label filter ----
    if active_label:
        predictions = [
            p for p in predictions
            if active_label in label_map.get(p.prediction_id, [])
        ]

    if not predictions:
        msg = (
            T("history.no_label_match") if active_label
            else T("nav.history.empty")
        )
        st.sidebar.markdown(
            f"<div style='color:#62666d;font-size:12px;line-height:1.5;"
            f"padding:4px 0 2px;'>{msg}</div>",
            unsafe_allow_html=True,
        )
        return route

    def _emit_item(rec: "storage.PredictionRecord") -> tuple[str, Any]:
        is_active = (
            route[0] == ROUTE_HISTORY and route[1] == rec.prediction_id
        )
        labels = label_map.get(rec.prediction_id, [])
        label_suffix = ("  · " + " ".join(f"#{x}" for x in labels[:2])
                        if labels else "")
        # `st.button` (not `st.sidebar.button`) so the row lands inside
        # whatever container context is active — here the keyed
        # `omy_hist_list` container whose tight gap controls row pitch.
        if st.button(
            _history_item_label(rec) + label_suffix,
            key=f"_hist_{rec.prediction_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            new_route = (ROUTE_HISTORY, rec.prediction_id)
            st.session_state._route = new_route
            return new_route
        return route

    # Iter #51 — the row list lives in its OWN keyed container so its
    # pitch is set by THIS container's gap, independent of the sidebar's
    # global 16px flex gap and of CSS load order (the per-row negative-
    # margin approach was unreliable on the deployed build). `_TYPOGRAPHY
    # _CSS` sets `st-key-omy_hist_list` inner stVerticalBlock gap → tight
    # Claude-style list. Headers go in via `st.markdown` (not
    # `st.sidebar.markdown`) so they share the container context.
    with st.sidebar.container(key="omy_hist_list"):
        if categories:
            # ---- Category-grouped tree ----
            cat_by_id = {c.category_id: c for c in categories}
            for cat in categories:
                members = [
                    p for p in predictions
                    if p.category_id == cat.category_id
                ]
                st.markdown(
                    f"<div style='color:#8a8f98;font-size:10.5px;"
                    f"letter-spacing:0.04em;margin:12px 0 2px;"
                    f"font-weight:600;'>{_esc_html(cat.name)} "
                    f"<span style='color:#62666d;font-weight:400;'>"
                    f"({len(members)})</span></div>",
                    unsafe_allow_html=True,
                )
                for rec in members:
                    route = _emit_item(rec)
            # uncategorized bucket
            loose = [
                p for p in predictions
                if not p.category_id or p.category_id not in cat_by_id
            ]
            if loose:
                st.markdown(
                    f"<div style='color:#62666d;font-size:10.5px;"
                    f"letter-spacing:0.04em;margin:12px 0 2px;'>"
                    f"{T('history.uncategorized')} "
                    f"<span style='color:#62666d;'>({len(loose)})</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                for rec in loose:
                    route = _emit_item(rec)
        else:
            # ---- Flat date-grouped list (no categories created yet) ----
            last_bucket = None
            for rec in predictions:
                bucket = _date_bucket(rec.created_at)
                if bucket != last_bucket:
                    st.markdown(
                        f"<div style='color:#62666d;font-size:10px;"
                        f"letter-spacing:0.04em;margin:10px 0 2px;'>"
                        f"{bucket}</div>",
                        unsafe_allow_html=True,
                    )
                    last_bucket = bucket
                route = _emit_item(rec)

    return route


def _esc_html(text: str) -> str:
    """Minimal HTML-escape for user-supplied category names rendered
    inside st.markdown(unsafe_allow_html=True)."""
    import html as _html
    return _html.escape(str(text))


def _account_state() -> tuple[str, Any]:
    """Resolve the sidebar account area's sign-in state.

    Returns one of:
      ``("in", user)``       — signed in; ``user`` is ``st.user``
      ``("out", None)``      — OIDC configured, signed out
      ``("disabled", None)`` — OIDC not wired yet (no ``[auth]`` secrets)

    ``st.user`` / ``st.login`` need an ``[auth]`` block in secrets;
    reading ``st.user.is_logged_in`` raises when it is absent, so the
    console degrades gracefully until the founder configures OIDC.
    """
    try:
        if bool(st.user.is_logged_in):
            return ("in", st.user)
        return ("out", None)
    except Exception:
        return ("disabled", None)


def _render_account_area() -> None:
    """Account control + Settings gear, pinned to the sidebar's
    bottom-left corner.

    A thin separator, then a row: the account control on the left (an
    account chip with a popover menu when signed in, a "Log in / Sign
    up" button when signed out) and a small gear button on the right
    that opens the routed Settings surface. This mirrors the
    account-corner pattern shared by Claude, ChatGPT, VS Code and Slack
    — the settings entry point lives beside the account, one click away,
    never hunted for. See docs/SETTINGS_REDESIGN.md.
    """
    state, user = _account_state()

    st.sidebar.markdown(
        "<div style='margin-top:20px;padding-top:14px;"
        "border-top:1px solid #23252a;'></div>",
        unsafe_allow_html=True,
    )

    # Signed-out hint sits full-width above the row so the login button
    # and the gear share one clean baseline.
    if state != "in":
        st.sidebar.caption(T("account.login_hint"))

    acct_col, gear_col = st.sidebar.columns([5, 1], gap="small")

    with acct_col:
        if state == "in":
            name = (
                (getattr(user, "name", None) or "").strip()
                or (getattr(user, "email", None) or "").strip()
                or "Account"
            )
            email = (getattr(user, "email", None) or "").strip()
            initial = (name[:1] or "·").upper()
            chip = name if len(name) <= 18 else name[:17] + "…"
            with st.popover(chip, use_container_width=True):
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;"
                    f"margin:2px 0 8px;'>"
                    f"<div style='width:36px;height:36px;border-radius:50%;"
                    f"flex:none;background:#18191a;border:1px solid #34343a;"
                    f"color:#d0d6e0;font-weight:600;font-size:15px;"
                    f"display:flex;align-items:center;justify-content:center;'>"
                    f"{_html.escape(initial)}</div>"
                    f"<div style='line-height:1.35;min-width:0;'>"
                    f"<div style='color:#f7f8f8;font-size:13.5px;"
                    f"font-weight:600;'>{_html.escape(name)}</div>"
                    f"<div style='color:#8a8f98;font-size:11.5px;'>"
                    f"{_html.escape(email)}</div></div></div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    T("account.logout"),
                    key="_acct_logout",
                    use_container_width=True,
                ):
                    st.logout()
        else:
            if st.button(
                T("account.login"),
                key="_acct_login",
                use_container_width=True,
            ):
                if state == "disabled":
                    st.warning(T("account.not_configured"))
                else:
                    st.login()

    with gear_col:
        # Iter #49 — every-button-works: the gear is the Settings entry,
        # but it stays visible (sidebar) once you're ON Settings. A plain
        # re-route to the same route would re-render the same page →
        # reads as a dead no-op (same class as the old "New prediction"
        # bug). So: highlight the gear as active when on Settings (mirrors
        # the "More" items), and on an already-here click give visible
        # feedback (toast + scroll-to-top) instead of a silent rerun.
        _on_settings = (
            st.session_state.get("_route", (ROUTE_WORKSPACE, None))[0]
            == ROUTE_SETTINGS
        )
        if st.button(
            "⚙",
            key="_acct_settings_gear",
            help=T("nav.settings"),
            use_container_width=True,
            type="primary" if _on_settings else "secondary",
        ):
            if _on_settings:
                st.toast(T("nav.settings_here"))
                _scroll_main_top()
            else:
                st.session_state._route = (ROUTE_SETTINGS, None)
                st.rerun()


# Pins the footer + account chip to the sidebar's bottom edge (Claude /
# ChatGPT style): a flex chain — sidebar content → user-content →
# wrapper → vertical block all stretch — then the footer
# element-container takes margin-top:auto. Injected as its OWN <style>
# by render_sidebar(): the same rules placed mid-way through the big
# global <style> silently never reached the CSSOM (bug-034). The ~96px
# default sidebar bottom padding is trimmed so the chip sits flush.
_SIDEBAR_PIN_CSS = (
    "<style>"
    'section[data-testid="stSidebar"] [data-testid="stSidebarContent"]'
    "{display:flex;flex-direction:column;}"
    'section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]'
    "{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;"
    "padding-bottom:16px!important;}"
    'section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]'
    " > div{flex:1 1 auto;min-height:0;display:flex;"
    "flex-direction:column;}"
    'section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]'
    ' > div > [data-testid="stVerticalBlock"]{flex:1 1 auto;}'
    'section[data-testid="stSidebar"] '
    '[data-testid="stElementContainer"]:has(.omy-foot-anchor)'
    "{margin-top:auto;}"
    "</style>"
)


# Iter #42d — mobile-sidebar CSS extracted from the global style
# block. Cerebrum iter 22 learning: when layout-critical CSS sits
# inside the 800+ line global <style>, it can silently fail to
# reach the CSSOM (live verified iter 43 — `document.styleSheets`
# scan found ZERO `stSidebar` transform rules despite the @media
# block being declared in app.py). The dedicated small-block
# pattern (see `_SIDEBAR_PIN_CSS` / `_SETTINGS_CSS` /
# `_WORKSPACE_CHROME_CSS`) loads reliably.
#
# Pairs with `_force_sidebar_open()` JS: on mobile, the JS sets
# `aria-expanded="false"` (the .click() route is broken — React
# silently drops synthetic events on Streamlit's collapse button).
# CSS then slides the off-screen via translateX(-100%). When user
# explicitly opens the drawer via Streamlit's hamburger, aria
# becomes "true" and the second rule re-shows it.
_MOBILE_SIDEBAR_CSS = (
    "<style>"
    "@media (max-width: 768px) {"
    'section[data-testid="stSidebar"]'
    "{transform:translateX(-100%) !important;"
    "transition:transform 0.28s ease !important;"
    "box-shadow:8px 0 24px rgba(0,0,0,0.4) !important;"
    "z-index:999990 !important;"
    "position:fixed !important;"
    "left:0 !important;top:0 !important;"
    "height:100vh !important;}"
    'section[data-testid="stSidebar"][aria-expanded="true"]'
    "{transform:translateX(0) !important;}"
    "section.main > div.block-container,"
    'div[data-testid="stMain"] > div.block-container'
    "{padding-left:1rem !important;padding-right:1rem !important;"
    "max-width:100% !important;margin-left:0 !important;}"
    "}"
    "</style>"
)


# Iter #51 — typography. Founder: "字体太大了 + 一行装不下别换第二行"
# (fonts too big; labels that don't fit must NOT wrap to a 2nd line).
# Claude/ChatGPT pattern: small dense fonts, and an overflowing label
# truncates to ONE line with an ellipsis — never two lines. Dedicated
# small <style> so the rules reliably reach the CSSOM (bug-034: layout
# CSS buried in the 800-line global block was silently dropped).
# Targets the two named offenders by Streamlit key-class: the sidebar
# history rows (st-key-_hist_) and the suggestion chips
# (st-key-_quick_chip_). `min-width:0` on the flex child + `width:100%`
# on the <p> are what make text-overflow:ellipsis actually fire inside
# Streamlit's flex button.
_TYPOGRAPHY_CSS = (
    "<style>"
    # --- History rail rows: one line, left-aligned, smaller, ellipsis
    # Borderless Claude-style list rows (founder: 历史记录边框太重) — no
    # box/hairline, transparent fill, subtle hover, quiet selected-fill
    # (NOT a bright accent button). Reads as a clean list, not cards.
    'section[data-testid="stSidebar"] [class*="st-key-_hist_"] button{'
    "text-align:left!important;justify-content:flex-start!important;"
    "padding:3px 9px!important;min-height:0!important;height:auto!important;"
    "line-height:1.3!important;"
    "background:transparent!important;border:1px solid transparent!important;"
    "box-shadow:none!important;border-radius:7px!important;}"
    'section[data-testid="stSidebar"] [class*="st-key-_hist_"] button:hover{'
    "background:rgba(255,255,255,0.055)!important;"
    "border-color:transparent!important;}"
    'section[data-testid="stSidebar"] [class*="st-key-_hist_"] '
    'button[kind="primary"]{background:rgba(255,255,255,0.09)!important;'
    "border-color:transparent!important;box-shadow:none!important;}"
    'section[data-testid="stSidebar"] [class*="st-key-_hist_"] '
    'button[kind="primary"]:hover{background:rgba(255,255,255,0.13)!important;}'
    'section[data-testid="stSidebar"] [class*="st-key-_hist_"] button '
    '[data-testid="stMarkdownContainer"]{width:100%!important;'
    "min-width:0!important;}"
    'section[data-testid="stSidebar"] [class*="st-key-_hist_"] button p{'
    "font-size:12.5px!important;line-height:1.35!important;color:#aeb4be!important;"
    "white-space:nowrap!important;overflow:hidden!important;"
    "text-overflow:ellipsis!important;display:block!important;"
    "width:100%!important;text-align:left!important;margin:0!important;}"
    'section[data-testid="stSidebar"] [class*="st-key-_hist_"] '
    'button[kind="primary"] p{color:#f2f4f8!important;}'
    # Tight row pitch (founder: 历史记录字间距太宽 — Claude's list is
    # dense). DETERMINISTIC approach: the history rows render inside a
    # dedicated keyed container `omy_hist_list`; set the gap on THAT
    # container's inner vertical block directly. Unlike the per-row
    # negative margin (which didn't reliably take on the deployed build),
    # a `gap` on the actual flex container is geometric and load-order-
    # independent. 4px = a tight Claude/ChatGPT list (date headers keep
    # their own top margins, so groups still breathe).
    'section[data-testid="stSidebar"] [class*="st-key-omy_hist_list"] '
    '[data-testid="stVerticalBlock"]{gap:4px!important;}'
    # Option B (founder: 还松, after container approach didn't visibly
    # take) — DECISIVE, geometry-guaranteed: set the gap on EVERY sidebar
    # vertical block. The history rows are flex children of one of these
    # blocks, so this selector cannot miss them (unlike the keyed-
    # container rule above, whose class may not have deployed). 5px = a
    # dense Claude-style sidebar; section headers keep their own margins
    # so groups still read. Scoped to the sidebar — main area untouched.
    'section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]'
    "{gap:5px!important;}"
    # --- Suggestion chips: one line, smaller, ellipsis
    '[class*="st-key-_quick_chip_"] button{overflow:hidden!important;}'
    '[class*="st-key-_quick_chip_"] button '
    '[data-testid="stMarkdownContainer"]{width:100%!important;'
    "min-width:0!important;}"
    '[class*="st-key-_quick_chip_"] button p{font-size:13px!important;'
    "white-space:nowrap!important;overflow:hidden!important;"
    "text-overflow:ellipsis!important;display:block!important;"
    "width:100%!important;margin:0!important;}"
    # --- Widget field labels (composer "What decision…" / "A little
    # about you" + Settings fields): Claude-dense, reliable testid
    # (the legacy `.stTextArea label` selector can miss modern DOM).
    '[data-testid="stWidgetLabel"] p{font-size:13px!important;}'
    "</style>"
)


def render_sidebar() -> tuple[str, Any]:
    """Sidebar — ChatGPT-shaped navigation: brand → New prediction →
    a date-grouped history of past predictions → a transitional "More"
    expander for the secondary surfaces → footer → account chip + a
    Settings gear. Settings is a routed two-pane surface now, not an
    expander — reached from the gear beside the account chip.

    Returns a route tuple consumed by ``main()``. See ROUTE_* constants.

    Intentionally clean: no developer chrome (substrate-available,
    mock-mode, Ollama-available, etc. are all suppressed). The substrate
    is detected silently at the use sites that need it.
    """
    if "ui_lang" not in st.session_state:
        st.session_state.ui_lang = _i18n.DEFAULT_LANG
    # user_locale is initialised here (not only inside the Settings
    # surface) so price displays resolve even before Settings is opened.
    if "user_locale" not in st.session_state:
        st.session_state.user_locale = currency.detect_locale()

    # Pin the footer + account chip to the sidebar's bottom edge.
    st.markdown(_SIDEBAR_PIN_CSS, unsafe_allow_html=True)
    # Iter 42d — mobile sidebar collapse, injected as a dedicated
    # small <style> so the rules actually reach the CSSOM (the
    # @media block had been buried in the giant global style and
    # was silently dropped — see iter 22 cerebrum learning).
    st.markdown(_MOBILE_SIDEBAR_CSS, unsafe_allow_html=True)
    # Iter 51 — single-line ellipsis + smaller fonts for history rows
    # and chips (founder: too big + must not wrap to a 2nd line).
    st.markdown(_TYPOGRAPHY_CSS, unsafe_allow_html=True)

    # ---- Brand wordmark ----
    # A precise wordmark with a small accent dot as the brand mark
    # (the accent on the brand mark is a sanctioned use). No
    # sparkle, no glow.
    st.sidebar.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;"
        f"margin:2px 0 3px;'>"
        f"<span style='width:7px;height:7px;border-radius:50%;"
        f"flex:none;background:#5e6ad2;'></span>"
        f"<span style='font-family:-apple-system,BlinkMacSystemFont,system-ui,Roboto,Helvetica,Arial,sans-serif;"
        f"font-size:22px;font-weight:600;letter-spacing:-0.018em;"
        f"color:#f7f8f8;'>"
        f"{_brand.BRAND_NAME_SHORT}</span>"
        f"</div>"
        f"<div style='color:#62666d;font-size:11.5px;letter-spacing:0.012em;"
        f"line-height:1.45;margin-bottom:16px;'>"
        f"{T('brand.tagline')}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # The active route is held in session_state so a history click on
    # one run survives into the next. Default = the workspace composer.
    route: tuple[str, Any] = st.session_state.get(
        "_route", (ROUTE_WORKSPACE, None)
    )

    # ---- New prediction button — always returns to the composer ----
    # Iter #47 bug-041 fix: a beta tester clicked "New prediction"
    # on the workspace and saw "no reaction" → concluded the app
    # was a dead UI. Root cause: when already on ROUTE_WORKSPACE,
    # re-setting the same route is a visual no-op. Now the button
    # ALSO (a) clears any current prediction so a returning user
    # sees the composer reset to a fresh state (a visible change),
    # and (b) clears the composer input fields + dismisses the
    # cold-start banner so the user lands on a clean, ready-to-type
    # form. This makes the most prominent CTA never silently
    # do nothing.
    if st.sidebar.button(
        T("nav.new_prediction"),
        use_container_width=True,
        type="primary",
        key="_nav_new_prediction",
    ):
        # Clear the last prediction → output region resets from a
        # result back to the idle composer-first cold start.
        st.session_state.pop("current_prediction", None)
        # Clear the composer input fields so "New prediction" reads
        # as "start fresh", not "nothing happened".
        for _k in list(st.session_state.keys()):
            if isinstance(_k, str) and _k.startswith("input_"):
                st.session_state.pop(_k, None)
        # Keep the beta banner dismissed if they already saw it —
        # don't re-nag. (We do NOT reset _beta_banner_dismissed.)
        # Iter #48 (founder principle: every button must do something
        # visible + sensible in EVERY state). On cold start the
        # composer is already fresh, so clearing alone changes
        # nothing the eye can see → the button felt dead. Set a
        # one-shot flag so the next render scrolls the decision input
        # into view + focuses it. Now "New prediction" ALWAYS lands
        # the user at the input ready to type, regardless of prior
        # state (fresh composer, a result showing, or a secondary
        # page).
        st.session_state["_focus_composer"] = True
        route = (ROUTE_WORKSPACE, None)
        st.session_state._route = route
        st.rerun()

    # ---- History rail — user-organized tree (categories + labels) ----
    st.sidebar.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;"
        f"margin:20px 0 6px;'>"
        f"<span style='color:#8a8f98;font-size:10.5px;letter-spacing:0.13em;"
        f"text-transform:uppercase;font-weight:600;'>"
        f"{T('nav.history')}</span>"
        f"<span style='flex:1;height:1px;background:#23252a;'></span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    route = _render_history_rail(route)

    # ---- "More" expander — transitional home for secondary surfaces ----
    # Iter #42 B2 — Pricing & pre-order is hidden during beta (the
    # `_secondary_modes()` filter drops it). Founder can re-enable
    # by appending `?dev=1` to the URL.
    with st.sidebar.expander(T("nav.more"), expanded=False):
        st.caption(T("nav.more.hint"))
        for mode_key in _secondary_modes():
            is_active = (
                route[0] == ROUTE_SECONDARY and route[1] == mode_key
            )
            if st.button(
                T(SECONDARY_MODE_I18N[mode_key]),
                key=f"_more_{mode_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                route = (ROUTE_SECONDARY, mode_key)
                st.session_state._route = route
                st.rerun()

    # ---- Footer + account, pinned flush to the sidebar's bottom edge.
    # The footer markdown is the bottom block's first element; its
    # element-container gets margin-top:auto via the .omy-foot-anchor
    # CSS rule, so the footer + account chip sit flush at the bottom
    # (Claude / ChatGPT style) instead of floating with dead space. ----
    st.sidebar.markdown(
        f"<div class='omy-foot-anchor' style='color:#62666d;"
        f"font-size:11px;line-height:1.5;margin-top:24px;"
        f"padding-top:16px;border-top:1px solid #23252a;'>"
        f"{T('brand.disclaimer')}"
        f"</div>"
        f"<div style='color:#8a8f98;font-size:11px;margin-top:12px;'>"
        f"{_brand.footer_html()}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- Account — Claude-style sign-in at the very bottom-left ----
    _render_account_area()

    st.session_state._route = route
    return route


# ============================================================
# Settings — routed two-pane surface (category rail + content)
# ============================================================

def _settings_section_header(title: str, desc: str) -> None:
    """Heading + one-line description for a Settings content section.

    Implements the redesign's per-setting anatomy (docs/SETTINGS_
    REDESIGN.md §3.4): every surface self-explains — a clear title and a
    short helper line, never a bare control. A hairline rule separates
    the header from the controls below. Styled by _SETTINGS_CSS.
    """
    st.markdown(
        f"<div class='omy-set-section'>"
        f"<div class='omy-set-section-t'>{title}</div>"
        f"<div class='omy-set-section-d'>{desc}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_settings_general() -> None:
    """General — display language + region/currency. Migrated verbatim
    from the old mid-sidebar Settings expander (roadmap R1)."""
    _settings_section_header(
        T("settings.cat.general"), T("settings.general.desc")
    )

    chosen_lang = st.radio(
        T("settings.language"),
        options=list(_i18n.SUPPORTED_LANGS),
        format_func=lambda k: _i18n.LANG_LABEL.get(k, k),
        horizontal=True,
        index=list(_i18n.SUPPORTED_LANGS).index(st.session_state.ui_lang),
        key="_lang_radio",
    )
    if chosen_lang != st.session_state.ui_lang:
        st.session_state.ui_lang = chosen_lang
        st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    locale_labels = {
        currency.LOCALE_US: "US · USD",
        currency.LOCALE_CN: "中国 · CNY",
        currency.LOCALE_EU: "EU · EUR",
        currency.LOCALE_GB: "UK · GBP",
        currency.LOCALE_JP: "日本 · JPY",
    }
    chosen = st.selectbox(
        T("settings.currency"),
        options=list(currency.SUPPORTED_LOCALES),
        format_func=lambda k: locale_labels.get(k, k),
        index=list(currency.SUPPORTED_LOCALES).index(
            st.session_state.user_locale
        ),
        help=T("settings.currency.help"),
    )
    st.session_state.user_locale = chosen


def _render_settings_about() -> None:
    """About — version, the not-a-deterministic-system disclaimer, and a
    plain statement of what the console is and is not."""
    _settings_section_header(
        T("settings.cat.about"),
        f"{_brand.BRAND_NAME_SHORT}  ·  v{_brand.BRAND_VERSION}",
    )
    st.markdown(
        f"<div style='background:#0f1011;border:1px solid #23252a;"
        f"border-radius:12px;padding:18px 20px;color:#d0d6e0;"
        f"font-size:13.5px;line-height:1.62;'>"
        f"{T('settings.about.what')}"
        f"</div>"
        f"<div style='color:#8a8f98;font-size:12px;line-height:1.6;"
        f"margin-top:14px;'>{T('brand.disclaimer')}</div>",
        unsafe_allow_html=True,
    )


def _resolve_user_backend():
    """If the user pinned a backend in Settings → Model & API (R3),
    instantiate it with their session-scoped credentials. Returns
    None when the user is on "default" (or there's no choice yet),
    so callers fall back to ``get_default_backend()``'s rotation.

    Iter #18: closes the previous "UI without wiring" gap — R3
    shipped a clean selectbox + password field but the actual
    backend dispatch path (`get_default_backend` / `compile_belief_
    program`) wasn't consulting it. Now `compile_belief_program`
    receives the resolved backend on every form submit.
    """
    choice = st.session_state.get("model_backend_choice", "default")
    if choice == "default" or not choice:
        return None
    try:
        if choice == "ollama":
            host = (
                st.session_state.get("model_ollama_url", "").strip()
                or "http://localhost:11434"
            )
            from llm_backends import get_backend
            return get_backend("ollama", host=host)
        if choice == "anthropic":
            key = st.session_state.get("model_api_key_anthropic", "").strip()
            if not key:
                return None
            from llm_backends import get_backend
            return get_backend("anthropic", api_key=key)
        if choice == "groq":
            key = st.session_state.get("model_api_key_groq", "").strip()
            if not key:
                return None
            from llm_backends import get_backend
            return get_backend("groq", api_key=key)
        if choice == "openai":
            key = st.session_state.get("model_api_key_openai", "").strip()
            if not key:
                return None
            from llm_backends import get_backend
            return get_backend("openai", api_key=key)
    except Exception:  # noqa: BLE001 — defensive: never block submission
        return None
    return None


def _render_settings_model() -> None:
    """Model & API (R3) — LLM backend selector + session-scoped API
    keys. The last "Planned" placeholder becomes real.

    Streamlit session_state is the storage; nothing here writes to
    disk. The backend dispatch read-side (`llm_backends.get_default_
    backend`) will consult `model_backend_choice` + `model_api_key_*`
    on a follow-up wiring pass; the choice + key are valid the moment
    the user submits the form, but the rotation default behaviour
    stays unchanged for backend modules that read env vars only.
    """
    _settings_section_header(
        T("settings.cat.model"), T("settings.model.desc")
    )

    _backends = ("default", "ollama", "anthropic", "groq", "openai")
    if st.session_state.get("model_backend_choice") not in _backends:
        st.session_state["model_backend_choice"] = "default"

    st.selectbox(
        T("settings.model.backend.label"),
        options=_backends,
        format_func=lambda b: T(f"settings.model.backend.{b}"),
        key="model_backend_choice",
        help=T("settings.model.backend.help"),
    )

    choice = st.session_state["model_backend_choice"]

    # Each backend has its own field: API key for cloud providers,
    # local URL for Ollama. Only the relevant field surfaces; the
    # others stay invisible (no irrelevant fields to read past).
    if choice == "anthropic":
        st.text_input(
            T("settings.model.api_key.label"),
            type="password",
            key="model_api_key_anthropic",
            placeholder="sk-ant-...",
            help=T("settings.model.api_key.help"),
        )
    elif choice == "groq":
        st.text_input(
            T("settings.model.api_key.label"),
            type="password",
            key="model_api_key_groq",
            placeholder="gsk_...",
            help=T("settings.model.api_key.help"),
        )
    elif choice == "openai":
        st.text_input(
            T("settings.model.api_key.label"),
            type="password",
            key="model_api_key_openai",
            placeholder="sk-...",
            help=T("settings.model.api_key.help"),
        )
    elif choice == "ollama":
        if "model_ollama_url" not in st.session_state:
            st.session_state["model_ollama_url"] = "http://localhost:11434"
        st.text_input(
            T("settings.model.ollama_url.label"),
            key="model_ollama_url",
            placeholder="http://localhost:11434",
            help=T("settings.model.ollama_url.help"),
        )

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    if choice == "default":
        st.caption(T("settings.model.status.default"))
    else:
        st.caption(T("settings.model.status.pinned"))


def _render_settings_planned(cat: str) -> None:
    """An honest preview panel for a category whose controls are still on
    the roadmap — the category name + a one-line description of what it
    will hold, plus a "Planned" badge. No fake controls (roadmap §5)."""
    meta: dict[str, tuple[str, str]] = {
        # Empty after R3 lands. Kept as a guard for future deferred
        # categories so we don't have to re-introduce the function.
    }
    tkey, dkey = meta.get(
        cat, ("settings.cat.general", "settings.general.desc")
    )
    _settings_section_header(T(tkey), T(dkey))
    st.markdown(
        f"<div style='background:#0f1011;border:1px solid #23252a;"
        f"border-radius:12px;padding:20px;'>"
        f"<span style='display:inline-block;"
        f"background:rgba(255,255,255,0.05);color:#8a8f98;font-size:10px;"
        f"font-weight:700;letter-spacing:0.09em;text-transform:uppercase;"
        f"padding:3px 9px;border-radius:5px;border:1px solid #23252a;'>"
        f"{T('settings.planned.badge')}</span>"
        f"<div style='color:#8a8f98;font-size:12.5px;line-height:1.62;"
        f"margin-top:12px;'>{T('settings.planned.note')}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_settings_personalization() -> None:
    """Personalization (R4) — display name, standing 'about you' context,
    readout tone, plus birth date / time / city for the Metaphysics-lens
    math.

    Per XUANXUE_REDESIGN.md L2: personal data (birth especially) is user
    info, not per-prediction. It belongs once, here, and the Metaphysics
    lens reads it from session_state — the composer no longer asks.

    All fields persist in ``st.session_state`` and stay browser-session-
    scoped. Nothing here is written to disk, logged, or sent off-device.
    """
    _settings_section_header(
        T("settings.cat.personalization"),
        T("settings.personalization.desc"),
    )

    _eyebrow = (
        "color:#f7f8f8;font-size:11px;font-weight:700;"
        "letter-spacing:0.09em;text-transform:uppercase;"
        "margin:4px 0 9px;"
    )

    # --- Section: PROFILE -------------------------------------------------
    st.markdown(
        f"<div style='{_eyebrow}'>"
        f"{T('settings.personalization.section.profile')}</div>",
        unsafe_allow_html=True,
    )
    st.text_input(
        T("settings.personalization.display_name"),
        key="personalization_display_name",
        max_chars=60,
        placeholder=T("settings.personalization.display_name.placeholder"),
        help=T("settings.personalization.display_name.help"),
    )
    st.text_area(
        T("settings.personalization.about_you"),
        key="personalization_about_you",
        max_chars=600,
        height=110,
        placeholder=T("settings.personalization.about_you.placeholder"),
        help=T("settings.personalization.about_you.help"),
    )

    st.markdown(
        "<div style='height:14px;'></div>", unsafe_allow_html=True
    )

    # --- Section: READOUT TONE -------------------------------------------
    st.markdown(
        f"<div style='{_eyebrow}'>"
        f"{T('settings.personalization.section.tone')}</div>",
        unsafe_allow_html=True,
    )
    _tone_options = ("plain", "calibrated", "warm")
    if st.session_state.get("personalization_tone") not in _tone_options:
        st.session_state["personalization_tone"] = "calibrated"
    st.selectbox(
        T("settings.personalization.tone"),
        options=_tone_options,
        format_func=lambda k: T(f"settings.personalization.tone.{k}"),
        key="personalization_tone",
        help=T("settings.personalization.tone.help"),
    )

    st.markdown(
        "<div style='height:14px;'></div>", unsafe_allow_html=True
    )

    # --- Section: BIRTH DATA ---------------------------------------------
    st.markdown(
        f"<div style='{_eyebrow}'>"
        f"{T('settings.personalization.section.birth')}</div>",
        unsafe_allow_html=True,
    )
    if "personalization_birth_enabled" not in st.session_state:
        st.session_state["personalization_birth_enabled"] = False
    st.toggle(
        T("settings.personalization.birth.toggle"),
        key="personalization_birth_enabled",
        help=T("settings.personalization.birth.toggle.help"),
    )

    if st.session_state.get("personalization_birth_enabled"):
        # Initialize sentinels once (Streamlit number_input requires a
        # concrete value to render — we use a neutral midpoint, not 1900,
        # so the field reads "needs your edit" rather than "wrong year").
        for _k, _default in (
            ("personalization_birth_year", 1990),
            ("personalization_birth_month", 1),
            ("personalization_birth_day", 1),
            ("personalization_birth_hour", 12),
        ):
            if _k not in st.session_state:
                st.session_state[_k] = _default

        bc1, bc2, bc3, bc4 = st.columns(4)
        with bc1:
            st.number_input(
                T("trad.birth.year"),
                min_value=1900,
                max_value=2100,
                step=1,
                key="personalization_birth_year",
            )
        with bc2:
            st.number_input(
                T("trad.birth.month"),
                min_value=1,
                max_value=12,
                step=1,
                key="personalization_birth_month",
            )
        with bc3:
            st.number_input(
                T("trad.birth.day"),
                min_value=1,
                max_value=31,
                step=1,
                key="personalization_birth_day",
            )
        with bc4:
            st.number_input(
                T("trad.birth.hour"),
                min_value=0,
                max_value=23,
                step=1,
                key="personalization_birth_hour",
            )

        st.text_input(
            T("settings.personalization.birth.city"),
            key="personalization_birth_city",
            max_chars=80,
            placeholder=T(
                "settings.personalization.birth.city.placeholder"
            ),
            help=T("settings.personalization.birth.city.help"),
        )

    st.markdown(
        "<div style='height:6px;'></div>", unsafe_allow_html=True
    )
    st.caption(T("settings.personalization.birth.privacy"))


def _render_settings_prediction() -> None:
    """Prediction defaults — the composer's starting values, set once and
    reused on every new prediction (roadmap R2).

    The default time horizon seeds the composer's time-horizon select on
    first render; the 玄学-lens default seeds the composer's lens toggle.
    Both stay editable per prediction — these only set the start point.
    Scenario is not a lever (one scenario ships) and branch count is
    fixed in the substrate, not a composer input — so neither is here.
    """
    _settings_section_header(
        T("settings.cat.prediction"), T("settings.prediction.desc")
    )

    # Keep the horizon options in lockstep with the composer's
    # time_horizon field so the default is always a valid choice.
    _scenario = next(iter(AVAILABLE_SCENARIOS))
    _hfield = next(
        (
            f
            for f in AVAILABLE_SCENARIOS[_scenario]["input_fields"]
            if f.key == "time_horizon"
        ),
        None,
    )
    horizons = tuple(getattr(_hfield, "options", ()) or ()) or (
        "3 months",
        "6 months",
        "12 months",
        "24 months",
    )
    fallback_h = "6 months" if "6 months" in horizons else horizons[0]
    if st.session_state.get("settings_default_horizon") not in horizons:
        st.session_state["settings_default_horizon"] = fallback_h
    st.selectbox(
        T("settings.prediction.horizon"),
        options=horizons,
        key="settings_default_horizon",
        help=T("settings.prediction.horizon.help"),
    )

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    if "settings_default_lens" not in st.session_state:
        st.session_state["settings_default_lens"] = False
    st.toggle(
        T("settings.prediction.lens"),
        key="settings_default_lens",
        help=T("settings.prediction.lens.help"),
    )


def _render_settings_data() -> None:
    """Data & privacy — export or clear your prediction history, plus an
    honest note on how (and how briefly) it is stored. Roadmap R5 — a
    real, wired surface: every control acts on storage, none decorative.
    """
    import csv as _csv
    import datetime as _dt
    import io as _io
    import json as _json
    from dataclasses import asdict as _asdict

    _settings_section_header(
        T("settings.cat.data"), T("settings.data.desc")
    )

    _label = (
        "color:#f7f8f8;font-size:13px;font-weight:600;margin:2px 0 3px;"
    )
    _help = (
        "color:#8a8f98;font-size:12px;line-height:1.5;margin-bottom:9px;"
    )

    cleared = st.session_state.pop("_data_cleared_n", None)
    if cleared is not None:
        st.success(T("settings.data.clear.done").format(n=cleared))

    uid = session_user_id()
    records = storage.list_user_predictions(uid)
    n = len(records)

    # ---- Export — CSV summary + full-fidelity JSON ----
    st.markdown(
        f"<div style='{_label}'>{T('settings.data.export.title')}</div>"
        f"<div style='{_help}'>{T('settings.data.export.help')}</div>",
        unsafe_allow_html=True,
    )
    if n == 0:
        st.caption(T("settings.data.empty"))
    else:
        json_blob = _json.dumps(
            [_asdict(r) for r in records],
            ensure_ascii=False, indent=2, default=str,
        )
        buf = _io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(
            ["prediction_id", "created_at", "scenario",
             "owner_flagged", "notes"]
        )
        for r in records:
            iso = _dt.datetime.fromtimestamp(
                r.created_at
            ).isoformat(timespec="seconds")
            writer.writerow(
                [r.prediction_id, iso, r.scenario,
                 r.is_owner_bias_flagged, r.notes]
            )
        exp_csv, exp_json = st.columns(2)
        with exp_csv:
            st.download_button(
                T("settings.data.export.csv"),
                data=buf.getvalue(),
                file_name="omytea_predictions.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with exp_json:
            st.download_button(
                T("settings.data.export.json"),
                data=json_blob,
                file_name="omytea_predictions.json",
                mime="application/json",
                use_container_width=True,
            )

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ---- Clear history — destructive, two-step confirmed ----
    st.markdown(
        f"<div style='{_label}'>{T('settings.data.clear.title')}</div>"
        f"<div style='{_help}'>{T('settings.data.clear.help')}</div>",
        unsafe_allow_html=True,
    )
    if st.session_state.get("_data_clear_armed"):
        st.warning(T("settings.data.clear.confirm").format(n=n))
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button(
                T("settings.data.clear.yes"),
                key="_data_clear_yes",
                type="primary",
                use_container_width=True,
            ):
                removed = storage.delete_user_predictions(uid)
                st.session_state._data_clear_armed = False
                st.session_state._data_cleared_n = removed
                st.session_state.pop("current_prediction", None)
                st.rerun()
        with no_col:
            if st.button(
                T("settings.data.clear.cancel"),
                key="_data_clear_cancel",
                use_container_width=True,
            ):
                st.session_state._data_clear_armed = False
                st.rerun()
    else:
        if st.button(
            T("settings.data.clear.btn"),
            key="_data_clear_btn",
            disabled=(n == 0),
        ):
            st.session_state._data_clear_armed = True
            st.rerun()

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ---- Honest storage note ----
    st.markdown(
        f"<div style='background:#0f1011;border:1px solid #23252a;"
        f"border-radius:12px;padding:14px 16px;color:#8a8f98;"
        f"font-size:12px;line-height:1.62;'>{T('settings.data.note')}</div>",
        unsafe_allow_html=True,
    )


_SETTINGS_CSS = (
    "<style>"
    ".omy-set-head{margin:4px 0 22px;}"
    ".omy-set-title{font-family:-apple-system,BlinkMacSystemFont,system-ui,Roboto,Helvetica,Arial,sans-serif;"
    "font-size:32px;font-weight:600;letter-spacing:-0.02em;"
    "color:#f7f8f8;line-height:1.12;}"
    ".omy-set-sub{color:#8a8f98;font-size:13px;line-height:1.55;"
    "margin-top:3px;}"
    ".omy-set-section{margin:2px 0 18px;padding-bottom:13px;"
    "border-bottom:1px solid #23252a;}"
    ".omy-set-section-t{font-family:-apple-system,BlinkMacSystemFont,system-ui,Roboto,Helvetica,Arial,sans-serif;"
    "font-size:22px;font-weight:600;color:#f7f8f8;"
    "letter-spacing:-0.01em;line-height:1.15;}"
    ".omy-set-section-d{color:#8a8f98;font-size:12.5px;"
    "line-height:1.5;margin-top:4px;}"
    '[data-testid="stColumn"]:has(.omy-pane-marker){'
    "border-left:1px solid #23252a;padding-left:26px!important;}"
    '[class*="st-key-_setcat_"] button{'
    "justify-content:flex-start!important;text-align:left!important;"
    "border:none!important;background:transparent!important;"
    "color:#8a8f98!important;font-weight:500!important;"
    "font-size:13.5px!important;padding:8px 12px!important;"
    "border-radius:6px!important;box-shadow:none!important;"
    "min-height:0!important;}"
    '[class*="st-key-_setcat_"] button:hover{'
    "background:rgba(255,255,255,0.05)!important;"
    "color:#d0d6e0!important;}"
    # Active category row — a subtle GREY surface lift + the accent
    # only as a thin 2px left bar (the brand mark of the active row,
    # not a coloured fill).
    '[class*="st-key-_setcat_"] button[kind="primary"]{'
    "background:rgba(255,255,255,0.06)!important;"
    "color:#f7f8f8!important;font-weight:600!important;"
    "box-shadow:inset 2px 0 0 0 #5e6ad2!important;}"
    '[class*="st-key-_setcat_"] button[kind="primary"]:hover{'
    "background:rgba(255,255,255,0.08)!important;"
    "color:#f7f8f8!important;}"
    "</style>"
)


def render_settings() -> None:
    """The Settings surface — a routed two-pane page: a left category
    rail + the selected category's controls, reached from the gear
    beside the account chip.

    Mirrors the settings shape shared by ChatGPT, Claude, macOS System
    Settings and the Google Account page: a left rail of grouped
    categories, the selected category's controls on the right. The page
    header is a modest left-aligned title (a configuration surface, not
    a centered marketing hero); the rail is a flat list with a
    soft-lavender active row; a hairline divides the two panes. See
    docs/SETTINGS_REDESIGN.md for the platform research + R1–R5 roadmap.
    """
    _render_back_bar()
    st.markdown(_SETTINGS_CSS, unsafe_allow_html=True)

    # Modest, left-aligned page header — not a centered marketing hero.
    st.markdown(
        f"<div class='omy-set-head'>"
        f"<div class='omy-set-title'>{T('nav.settings')}</div>"
        f"<div class='omy-set-sub'>{T('settings.subtitle')}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    categories = (
        ("general", T("settings.cat.general")),
        ("prediction", T("settings.cat.prediction")),
        ("model", T("settings.cat.model")),
        ("personalization", T("settings.cat.personalization")),
        ("data", T("settings.cat.data")),
        ("about", T("settings.cat.about")),
    )
    valid = {c[0] for c in categories}
    if st.session_state.get("_settings_cat") not in valid:
        st.session_state._settings_cat = "general"
    active = st.session_state._settings_cat

    rail, pane = st.columns([1, 2.8], gap="large")
    with rail:
        for key, label in categories:
            if st.button(
                label,
                key=f"_setcat_{key}",
                use_container_width=True,
                type="primary" if key == active else "secondary",
            ):
                st.session_state._settings_cat = key
                st.rerun()
    with pane:
        # Marker → the content column picks up the two-pane divider rule.
        st.markdown(
            "<div class='omy-pane-marker' style='display:none'></div>",
            unsafe_allow_html=True,
        )
        if active == "general":
            _render_settings_general()
        elif active == "prediction":
            _render_settings_prediction()
        elif active == "model":
            _render_settings_model()
        elif active == "personalization":
            _render_settings_personalization()
        elif active == "data":
            _render_settings_data()
        elif active == "about":
            _render_settings_about()
        else:
            _render_settings_planned(active)


# ============================================================
# Mode 1 — New prediction
# ============================================================

def _idle_heatmap_branches() -> list[Any]:
    """Five equal-probability placeholder branches — canonical idle shape.

    The chatbox layout keeps the quantum probability heatmap visible at
    the top of the workspace at ALL times — even before any prediction
    exists. The idle grid is a flat uniform distribution: five
    0.20-probability branches; a uniform prior IS the honest pre-evidence
    belief.

    OMY-V415 Acceptance #59: the heatmap is now the interactive v10
    HTML/JS component, which renders this same 5×0.20 uniform grid in JS
    when fed an empty branch list (``_render_workspace_output`` passes
    ``[]`` in the idle path). This Python helper is retained as the
    single canonical definition of that idle shape — exercised by the
    chatbox-layout test suite to pin the 5-branch / 0.20-each contract
    the JS ``idleBranches()`` mirror must stay consistent with.
    """
    from console import ConsoleHypothesis

    # Iter #7 → iter #11: idle row labels first went "Branch A/B/C...
    # —awaiting your decision" → "Your option 1...5". Live verify
    # showed the chart's narrow left gutter truncated to "Your
    # option…" (the digit was cut off). Shortened again to "Option
    # 1...5" — still self-explanatory + fits the gutter without
    # truncation.
    labels = [
        "Option 1",
        "Option 2",
        "Option 3",
        "Option 4",
        "Option 5",
    ]
    return [
        ConsoleHypothesis(
            label=lbl,
            narrative="",
            probability=0.20,
            key_uncertainty_driver="",
            depends_on_decision=None,
            branch_type="realistic",
        )
        for lbl in labels
    ]


# Fixed pixel heights for the two workspace panes. The page itself does
# NOT scroll — the output pane + composer pane are sized to fit one
# viewport (WeChat-style: the composer is always visible). Each is its
# own ``st.container(height=…)`` scroll box, so scrolling one never
# moves the other. The output pane is the larger one (the quantum
# heatmap is the centerpiece); the composer pane is smaller.
#
# Streamlit's header (~50px) is kept visible so the sidebar collapse /
# expand control stays reachable — the two panes give that space back
# rather than hiding the header.
_OUTPUT_PANE_HEIGHT = 410
_COMPOSER_PANE_HEIGHT = 275

# Composer fields shown directly; every other scenario field folds into
# the composer's "More details" expander so the composer stays compact.
_COMPOSER_CORE_FIELDS = (
    # Reordered (XUANXUE_REDESIGN iteration #1, "design-self-explains"):
    # the DECISION the user is weighing is the hero — first field they
    # see, first thing they fill. Context about THEM (current role,
    # motivation) comes after the decision so the page reads "tell me
    # what you're choosing between → tell me about you" rather than
    # "tell me about you → tell me about your decision".
    "decision_options",
    "current_role",
    "why_considering_change",
    "time_horizon",
)

# Injected once at the top of the workspace: reclaim Streamlit's tall
# default chrome padding so the output + composer panes fit one screen
# with no marketing hero pushing them down.
#
# The Streamlit header is kept PRESENT (not hidden) — hiding it also
# removes the sidebar collapse / expand control, which would strand a
# collapsed sidebar with no way to reopen it. Instead the header is made
# visually quiet (transparent, no shadow) and the ~50px it occupies is
# given back from the pane heights above.
_WORKSPACE_CHROME_CSS = (
    "<style>"
    "header[data-testid='stHeader']{background:transparent!important;"
    "box-shadow:none!important;}"
    ".block-container{padding-top:0.6rem!important;"
    "padding-bottom:0.3rem!important;}"
    # Iter #52 — genuinely SHRINK the cold-start preview heatmap (founder:
    # don't truncate it). The full chart renders inside the keyed
    # `omy_idle_preview` container; a CSS scale transform shrinks the
    # WHOLE component proportionally (grid + axis + legend all stay
    # visible, just smaller), and the wrapper is clipped to the scaled
    # height so there's no empty gap below before the input.
    '[class*="st-key-omy_idle_preview"]{height:250px!important;'
    "overflow:hidden!important;}"
    '[class*="st-key-omy_idle_preview"] iframe{'
    "transform:scale(0.62)!important;transform-origin:top center!important;}"
    # Iter #52 (founder) — distinct "input tray" so the user can tell the
    # composer is a SEPARATE, independently-scrollable zone (not part of
    # the output page above): subtle raised fill, full hairline border,
    # rounded corners, and a soft top shadow that reads as "docked".
    '[class*="st-key-omy_composer_pane"]{'
    "background:#15171c!important;border:1px solid #3a3d46!important;"
    "border-radius:16px!important;padding:14px 16px 6px!important;"
    "box-shadow:0 -12px 34px rgba(0,0,0,0.5)!important;"
    "margin-top:20px!important;}"
    # A faint accent strip on the tray's top edge + a small label make the
    # "this is the input zone, separate & scrollable" reading unmistakable.
    '[class*="st-key-omy_composer_pane"]::before{content:"";position:absolute;'
    "left:18px;right:18px;top:0;height:2px;border-radius:2px;"
    "background:linear-gradient(90deg,transparent,#6b8fff66,transparent);}"
    '[class*="st-key-omy_composer_pane"]{position:relative!important;}'
    # Float the "Advanced options" wrapper to the BOTTOM of the composer
    # flex column (after the input form) — the composer body is a flex
    # column, so a high `order` on this one item moves it last visually
    # while leaving the Python execution (and the lens/video vars) intact.
    # `order` must sit on the FLEX ITEM — the composer pane's direct child
    # that CONTAINS the wrap (an stLayoutWrapper/stElementContainer,
    # depending on Streamlit version), not the inner keyed wrapper. :has()
    # targets it robustly across versions.
    '[class*="st-key-omy_composer_pane"] > div:has([class*="st-key-omy_advanced_wrap"])'
    "{order:99!important;margin-top:8px!important;}"
    "</style>"
)


def _render_xuanxue_output_view() -> None:
    """The 玄学 output view — the Nye Clock lens, rendered in the OUTPUT
    region (OMY-V415 / M2 / Acceptance #60 — requirement D).

    Reached via the output-region view toggle when the 玄学 lens is on.
    It expands to COVER the quantum heatmap; the toggle switches back.
    Reuses ``_render_traditional_lens`` so the 玄学 surface stays in
    lockstep visually with the rest of the console.
    """
    current = st.session_state.get("current_prediction")
    branches = (
        list(current["result"].hypotheses) if current is not None else None
    )
    prediction_id = (
        current.get("prediction_id") if current is not None else None
    )
    _render_traditional_lens(
        branches,
        key_prefix=f"_output_xuanxue_{prediction_id or 'idle'}",
    )


def _xuanxue_lens_enabled() -> bool:
    """Whether the composer's 玄学-lens toggle is on.

    Streamlit reruns top→bottom and the output region renders BEFORE the
    composer, so the derived ``_xuanxue_lens_on`` flag (set inside the
    composer) is one rerun stale for the output region. The composer's
    toggle WIDGET key ``_composer_lens_toggle`` is persisted by
    Streamlit across reruns, so it is the authoritative current value —
    fall back to the derived flag only if the widget hasn't rendered
    yet (first run).
    """
    if "_composer_lens_toggle" in st.session_state:
        return bool(st.session_state["_composer_lens_toggle"])
    return bool(st.session_state.get("_xuanxue_lens_on", False))


def _live_video_enabled() -> bool:
    """Whether the composer's "Live video" toggle is on.

    Same top→bottom rerun ordering as :func:`_xuanxue_lens_enabled`: the
    output region renders BEFORE the composer, so it reads the composer
    toggle's persisted WIDGET key ``_composer_live_toggle`` directly —
    that key is the authoritative current value across reruns. When the
    toggle is on, the output surface becomes the embedded v10
    live-video app (OMY-V415 / M2 / Acceptance #65).
    """
    return bool(st.session_state.get("_composer_live_toggle", False))


def _render_output_view_toggle() -> str:
    """Output-region view switch — a one-click pill at the top of the
    output region (OMY-V415 / M2 / Acceptance #60 — requirement D).

    Shown ONLY when the 玄学 lens toggle is enabled. It switches the
    output region between the **quantum heatmap** (default — the
    scientific centerpiece) and the **玄学 Nye Clock** view. When the
    lens is off this returns ``"quantum"`` without drawing anything, so
    the output region is heatmap-only.
    """
    if not _xuanxue_lens_enabled():
        return "quantum"

    quantum_label = T("output.view.quantum")
    xuanxue_label = T("output.view.xuanxue")
    choice = st.segmented_control(
        T("output.view.label"),
        options=[quantum_label, xuanxue_label],
        default=quantum_label,
        key="_output_view_choice",
        help=T("output.view.hint"),
        label_visibility="collapsed",
    )
    return "xuanxue" if choice == xuanxue_label else "quantum"


def _step_label(title: str, sub: str = "") -> None:
    """A numbered step heading (①②③) that gives the workspace a legible
    top-to-bottom narrative.

    Founder feedback (2026-05-29): the page reads as a flat wall of
    panels — a first-time user (even the founder) can't tell what to do
    first or what produced what. The fix is NOT removing content; it's
    making the LOGIC visible: a clear "do this → then this" spine. This
    renders a small step title + a one-line plain-language hint.
    """
    sub_html = (
        f"<div style='color:#8a8f98;font-size:12px;line-height:1.45;"
        f"margin-top:2px;'>{_esc_html(sub)}</div>"
        if sub else ""
    )
    st.markdown(
        f"<div style='margin:2px 0 9px;'>"
        f"<div style='color:#e8eaed;font-size:14px;font-weight:600;"
        f"letter-spacing:-0.01em;'>{_esc_html(title)}</div>{sub_html}</div>",
        unsafe_allow_html=True,
    )


def _render_workspace_output() -> None:
    """Top region of the chatbox workspace — the persistent output.

    Always present. The quantum probability heatmap is the centerpiece
    and renders on every run: an idle flat grid before a prediction, the
    real branch distribution after. When a prediction exists in
    ``st.session_state.current_prediction`` the full result (branches,
    joint structure, drill-down, 玄学 lens) renders here too.

    OMY-V415 / M2 / Acceptance #60:
      • C — the whole output region is wrapped in a fixed-height
        ``st.container`` so it scrolls independently of the composer
        below; scrolling the composer never moves this output region.
      • D — when the 玄学 lens is on, a one-click view toggle at the
        top switches the region between the quantum heatmap (default)
        and the 玄学 Nye Clock view, which covers the quantum module.

    OMY-V415 / M2 / Acceptance #65:
      • When the composer's "Live video" toggle is on, the output
        surface BECOMES the v10 live-video app embedded whole
        (``render_live_video_v10`` — camera + motion loop + live
        heatmap + see-both-at-once, one integrated unit). The idle /
        prediction quantum heatmap is the non-video default; live video
        replaces it only while the toggle is on.

    Streamlit reruns top→bottom, so this output region — placed before
    the composer — reflects the last prediction the composer stored.
    """
    # Requirement C — own fixed-height scroll pane. The heatmap (the
    # centerpiece) stays visually stable while the user works in the
    # composer pane below.
    # Iter #52 (founder): on cold-start (no prediction / no live / no
    # lens) render this region COMPACT so the input composer beneath it
    # is visible without scrolling — the Claude-style "input always in
    # view at the bottom" pattern. A real prediction / live / lens view
    # keeps the full height (the heatmap is the centerpiece then).
    _ow_lens = bool(st.session_state.get("_xuanxue_lens_on")) or bool(
        st.session_state.get("_composer_lens_toggle")
    )
    _ow_compact = (
        st.session_state.get("current_prediction") is None
        and not _live_video_enabled()
        and not _ow_lens
    )
    _ow_pane_h = 300 if _ow_compact else _OUTPUT_PANE_HEIGHT
    with st.container(height=_ow_pane_h, border=False):
        # Acceptance #65 — live video on: the output surface becomes the
        # v10 app embedded whole. Checked before the 玄学 view toggle and
        # before the prediction/idle heatmap: an active live-video
        # session owns the output region.
        if _live_video_enabled():
            st.markdown(
                "<div style='display:flex;align-items:center;gap:9px;"
                "margin:6px 0 8px;'>"
                "<span style='width:5px;height:5px;border-radius:50%;"
                "background:#8a8f98;'>"
                "</span>"
                "<span style='color:#8a8f98;font-size:11px;"
                "letter-spacing:0.14em;text-transform:uppercase;"
                "font-weight:600;'>Live video</span>"
                "<span style='flex:1;height:1px;"
                "background:#23252a;'></span>"
                "</div>",
                unsafe_allow_html=True,
            )
            render_live_video_v10()
            return

        # Requirement D — view toggle (only drawn when the lens is on).
        view = _render_output_view_toggle()

        if view == "xuanxue":
            # The 玄学 Nye Clock view covers the quantum module.
            _render_xuanxue_output_view()
            return

        current = st.session_state.get("current_prediction")

        if current is None:
            # Idle state — heatmap only, calm "awaiting your decision"
            # grid.
            # Iter #3: removed the "PREDICTION SPACE" eyebrow above the
            # heatmap. It was an extra all-caps label adding nothing
            # the heatmap's own card-title doesn't already convey, and
            # the founder's "no text crutches" rule applies — the
            # heatmap card title + the grid itself name the surface.
            # Idle = empty branch list. The interactive component
            # renders its own uniform grid + idle caption (i18n
            # heatmap.idle_note), and a video dropped here will drive
            # the heatmap live even before any prediction has run.
            # Iter #52 — step-② heading frames this preview as "what
            # you'll GET after ①", so a first-timer reads the chart as
            # a result-to-come, not a mysterious standalone widget.
            _step_label(
                T("workspace.step2.title"), T("workspace.step2.sub_idle")
            )
            if _ow_compact:
                # Iter #52 (founder caught it): passing a smaller height
                # to the heatmap CLIPS it (truncates legend/axis), it does
                # NOT shrink the chart. To genuinely shrink it, render the
                # FULL chart and CSS-scale the whole component down (see
                # the `st-key-omy_idle_preview` transform in
                # _WORKSPACE_CHROME_CSS) — everything stays visible, just
                # proportionally smaller, so the bottom input is in view.
                with st.container(key="omy_idle_preview"):
                    _render_probability_heatmap([], horizon_label="")
            else:
                _render_probability_heatmap([], horizon_label="")
            return

        # A prediction exists — render the full result here at the top.
        _render_result(
            current["result"], current["form_data"], current["scenario"],
            current["user_id"], current["program"],
            prediction_id=current["prediction_id"],
        )


def _render_workspace_composer() -> None:
    """Bottom region of the chatbox workspace — the input composer.

    OMY-V415 / M2 / Acceptance #60 — requirement C: the composer is its
    own fixed-height ``st.container`` scroll pane (smaller than the
    output pane above), so scrolling the composer never moves the
    output region and vice versa — a two-pane / chatbox layout. The
    pane is intentionally the smaller of the two: the output heatmap is
    the centerpiece. The composer markup itself lives in
    ``_render_workspace_composer_body``.

    Iter #30 — when a prediction exists, fold the composer into an
    expander default-collapsed so the result page's attention stays
    on the story → evidence → revisit reminder. Founder round-2
    audit: "结果页不要在故事下面马上把表单又露出来. 生成后用户注意力
    应该停在结果、证据、回访提醒". The expander lets users tweak
    inputs and re-run when they want — just not by default.
    """
    # Iter #52 (founder): the input region needs a DISTINCT boundary from
    # the output above — otherwise a user can't tell it's a separate,
    # independently-scrollable zone. The `omy_composer_pane` key lets
    # _WORKSPACE_CHROME_CSS give it a docked "input tray" look (top
    # divider + subtle raised fill + rounded top).
    with st.container(
        height=_COMPOSER_PANE_HEIGHT, border=False, key="omy_composer_pane"
    ):
        if st.session_state.get("current_prediction") is not None:
            with st.expander(
                T("composer.edit_and_rerun"), expanded=False,
            ):
                _render_workspace_composer_body()
        else:
            _render_workspace_composer_body()


def _render_composer_field(field: Any) -> Any:
    """Render one composer input widget; return its value.

    Textareas are height-floored so the composer stays a compact,
    one-screen input bar. ``user_id`` is auto-suggested on first render
    so the handle never blocks submission.
    """
    field_key = f"input_{field.key}"
    if field.key == "user_id" and not st.session_state.get(field_key):
        # session_user_id() resolves to the signed-in email or the
        # anonymous tester-XXXX handle — and, unlike a raw
        # st.session_state._default_user_id read, it never AttributeErrors
        # when the user is logged in (that key is only set on the
        # signed-out path).
        st.session_state[field_key] = session_user_id()
    if (
        field.key == "time_horizon"
        and not st.session_state.get(field_key)
        and st.session_state.get("settings_default_horizon")
        in (getattr(field, "options", ()) or ())
    ):
        # Seed the composer's horizon select from the user's
        # Prediction-defaults setting on first render (roadmap R2). The
        # user can still change it per prediction; "Clear form" re-seeds.
        st.session_state[field_key] = st.session_state[
            "settings_default_horizon"
        ]
    placeholder = getattr(field, "placeholder", "") or ""
    if field.field_type == "textarea":
        return st.text_area(
            field.label, help=field.hint, key=field_key,
            placeholder=placeholder, height=68,
        )
    if field.field_type == "select":
        return st.selectbox(
            field.label, options=field.options,
            help=field.hint, key=field_key,
        )
    return st.text_input(
        field.label, help=field.hint, key=field_key,
        placeholder=placeholder,
    )


def _render_workspace_composer_body() -> None:
    """The input composer's markup — text conditions + a "+" attach
    (video / files) + a live-video toggle + a 玄学-lens toggle, all
    feeding one "Run prediction".

    When Generate is submitted the prediction is compiled, stored in
    ``st.session_state.current_prediction``, and ``st.rerun()`` is called
    so the top output region picks it up. Borrows only the "one composer
    + attach" affordance — this is NOT a turn-by-turn chatbox. Rendered
    inside the fixed-height scroll pane opened by
    ``_render_workspace_composer``.
    """
    # Auto-suggested user handle so the field never blocks submission.
    # Shares the session-stable id with the history rail, so a
    # prediction created here appears in the sidebar immediately.
    session_user_id()

    # Iter #41 — beta-research consent banner (founder round-4 P1
    # #5). Shown ONCE per session above the cold-start composer
    # so first-time visitors understand: (a) it's a beta gathering
    # calibration data, (b) prefer desktop for first try, (c) no
    # sensitive info, (d) save the prediction ID + add the calendar
    # reminder, (e) data lives on the demo server not the device.
    # Dismissed via session_state once the user clicks "Got it" so
    # returning users aren't nagged. Hidden once any prediction
    # exists (the user clearly engaged with the product already).
    if (
        st.session_state.get("current_prediction") is None
        and not st.session_state.get("_beta_banner_dismissed", False)
    ):
        with st.container(border=True):
            # Iter #51 — smaller, denser banner (founder: 字体太大). Render
            # as one HTML block at 13px/12px instead of default ~16px
            # markdown; keep the **bold** safety span by converting it
            # to <b>. The "Don't paste sensitive info" emphasis stays.
            import re as _re
            _b_body = _re.sub(
                r"\*\*(.+?)\*\*", r"<b>\1</b>", T("beta.banner_body")
            )
            st.markdown(
                "<div style='font-size:13px;font-weight:600;color:#e8eaed;"
                "margin:0 0 3px;'>"
                f"{_esc_html(T('beta.banner_title'))}</div>"
                "<div style='font-size:12px;line-height:1.55;color:#aab0ba;'>"
                f"{_b_body}</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "Got it — continue",
                key="_beta_banner_dismiss_btn",
                type="primary",
                use_container_width=False,
            ):
                st.session_state["_beta_banner_dismissed"] = True
                st.rerun()

    # ---- Quick-start suggestion chips (iteration #1 — design-self-
    # explains) ----
    # ChatGPT-/Claude.ai-style examples on a fresh load: 3 one-click
    # decision templates so a stumbled-in visitor knows by sight what
    # this product takes as input — no instruction text needed. Hidden
    # once any prediction exists so they never crowd a returning user.
    if (
        st.session_state.get("current_prediction") is None
        and not st.session_state.get("input_decision_options", "").strip()
    ):
        # Iter #52 — no step number / heading here (founder: 序号没必要).
        # The chips are self-explanatory examples and the decision
        # field's own label below names the input; a small top margin
        # gives the chip row breathing room without a redundant heading.
        st.markdown(
            "<div style='height:2px;'></div>", unsafe_allow_html=True
        )
        _chip_specs = (
            (
                "🎯 Take the offer or stay?",
                "decision",
                (
                    "Accept the senior engineer offer (relocate)\n"
                    "Stay in current role and negotiate a counter\n"
                    "Wait one more quarter for the planned promotion"
                ),
                (
                    "Early-career engineer, 4 years experience, currently "
                    "at a stable mid-size company; have an offer from a "
                    "fast-moving Series-B with 30% comp bump but relocation."
                ),
                (
                    "Comp + growth ceiling vs. uprooting life and team "
                    "I trust. Promotion is 'planned' but uncertain."
                ),
            ),
            (
                "🌏 Move home or stay abroad?",
                "move",
                (
                    "Return home now to be near family\n"
                    "Stay abroad two more years to lock in residency\n"
                    "Take a 6-month sabbatical and decide afterward"
                ),
                (
                    "Have been working abroad 5 years, parents aging, "
                    "current job is good but not life-defining; partner "
                    "is flexible either way."
                ),
                (
                    "Family proximity + cost of living vs. residency "
                    "status and the career arc I've built here."
                ),
            ),
            (
                "🔬 Industry or PhD?",
                "phd",
                (
                    "Take the research scientist role at an AI lab\n"
                    "Start a PhD in machine learning theory this fall\n"
                    "Defer one year and ship the open-source project"
                ),
                (
                    "Final-year Master's student in ML; admitted to a "
                    "strong PhD program; have a competing offer from a "
                    "well-funded AI research lab."
                ),
                (
                    "Long-horizon depth vs. near-term impact + income. "
                    "5-year career ROI is the real question."
                ),
            ),
        )
        cols = st.columns(len(_chip_specs))
        for col, (label, key_suffix, opts, role, why) in zip(
            cols, _chip_specs
        ):
            with col:
                if st.button(
                    label,
                    key=f"_quick_chip_{key_suffix}",
                    use_container_width=True,
                    type="secondary",
                    help="One-click prefill — edit anything, then Generate.",
                ):
                    st.session_state["input_decision_options"] = opts
                    st.session_state["input_current_role"] = role
                    st.session_state["input_why_considering_change"] = why
                    st.session_state["input_user_id"] = session_user_id()
                    # Iter #48 — immediate feedback + scroll. On the
                    # free-tier server the rerun that fills the form
                    # takes 10-15s to paint; without feedback a user
                    # thinks the chip "did nothing", clicks again, or
                    # worse hits "See my futures →" before the fields
                    # commit → "Missing required field: A little about
                    # you" (a confusing error for someone who clicked
                    # an example). A toast confirms the click landed,
                    # and `_focus_composer` scrolls the now-filled
                    # decision field into view so the user SEES the
                    # example loaded and naturally proceeds to Generate.
                    try:
                        st.toast(T("composer.chip_loaded"))
                    except Exception:
                        pass
                    st.session_state["_focus_composer"] = True
                    st.rerun()

    # ---- Modality bar: attach (+) · live video · Metaphysics lens ----
    # Iter #21 (founder audit 2026-05-26 P1): the 3 modality controls
    # used to sit visible in the composer flow, but a stumbled-in user
    # reads "Live video" and "+ Attach" as "this might want my camera /
    # uploads" — scary first-paint signals. They're advanced features.
    # Now folded inside a small `st.expander` labelled "Advanced
    # options"; the lens toggle is shown next to the expander label so
    # the easter-egg stays discoverable in one click, the rest hide.
    # When the user has already opened the expander once (or has
    # attached a video / enabled live video / enabled the lens), the
    # row stays open on subsequent reruns so we don't yank the
    # affordance away from a power user mid-session.
    _adv_open = bool(
        st.session_state.get("_composer_live_toggle")
        or st.session_state.get("_composer_lens_toggle")
        or st.session_state.get("_composer_video")
        or st.session_state.get("_composer_files")
        or st.session_state.get("_composer_advanced_seen")
    )
    # Iter #42 B2 — during beta, the Advanced expander shows ONLY
    # the 玄学 lens toggle (founder ratified — opt-in product
    # surface). Live video + Attach are research extensions and
    # are hidden behind `?dev=1`. The expander still exists so
    # the lens toggle stays one click away.
    _show_research = _show_research_features()
    # Iter #52 (founder: 继续优化) — "Advanced options" used to sit wedged
    # BETWEEN the example chips and the decision input, scrambling the
    # read order. Wrap it in a keyed container and float it to the BOTTOM
    # of the composer column via CSS `order` (see _WORKSPACE_CHROME_CSS) —
    # this moves it visually below the input WITHOUT touching the lens /
    # live-video / attach variable flow (the toggles still compute here,
    # in place; only the on-screen position changes). Order now reads:
    # chips → decision input → submit → Advanced options.
    with st.container(key="omy_advanced_wrap"), st.expander(
        "Advanced options", expanded=_adv_open
    ):
        st.session_state["_composer_advanced_seen"] = True
        if _show_research:
            mod_attach, mod_live, mod_lens, _mod_spacer = st.columns(
                [1.2, 1.2, 1.2, 2.4]
            )
            with mod_attach:
                with st.popover(
                    T("composer.attach"), use_container_width=True
                ):
                    st.caption(T("composer.attach.hint"))
                    attached_video = st.file_uploader(
                        T("composer.attach.video"),
                        type=["mp4", "mov", "webm", "avi", "mkv"],
                        accept_multiple_files=False,
                        key="_composer_video",
                    )
                    attached_files = st.file_uploader(
                        T("composer.attach.files"),
                        accept_multiple_files=True,
                        key="_composer_files",
                    )
                    if attached_video is not None:
                        st.success(T("composer.attach.video_ready"))
                    if attached_files:
                        st.success(
                            f"{len(attached_files)} "
                            f"{T('composer.attach.files_ready')}"
                        )
            with mod_live:
                live_on = st.toggle(
                    T("composer.live"),
                    key="_composer_live_toggle",
                    help=T("composer.live.hint"),
                )
            with mod_lens:
                lens_on = st.toggle(
                    T("composer.lens"),
                    key="_composer_lens_toggle",
                    value=st.session_state.get(
                        "_composer_lens_toggle",
                        bool(st.session_state.get(
                            "settings_default_lens", False)),
                    ),
                    help=T("composer.lens.hint"),
                )
        else:
            # Beta path — lens toggle only. Live/Attach hidden;
            # live_on stays False, attached_video/files stay None.
            mod_lens, _mod_spacer = st.columns([1.4, 4.6])
            with mod_lens:
                lens_on = st.toggle(
                    T("composer.lens"),
                    key="_composer_lens_toggle",
                    value=st.session_state.get(
                        "_composer_lens_toggle",
                        bool(st.session_state.get(
                            "settings_default_lens", False)),
                    ),
                    help=T("composer.lens.hint"),
                )
            # Defensive: if a leftover session_state has the live
            # toggle on from a prior `?dev=1` session, force it off
            # so the output region doesn't try to render the live
            # video pipeline.
            if st.session_state.get("_composer_live_toggle"):
                st.session_state["_composer_live_toggle"] = False
            attached_video = None
            attached_files = []
    # The lens toggle is consumed downstream by _render_result.
    st.session_state["_xuanxue_lens_on"] = bool(lens_on)

    attached_video = st.session_state.get("_composer_video")

    # The live-video toggle (live_on) drives the OUTPUT region only:
    # when on, _render_workspace_output renders the v10 see-both-at-once
    # panel (camera | quantum heatmap). The composer carries NO
    # live-video UI — all input here, all output in the region above.

    # ---- Attached-video modality: embed the video pipeline inline ----
    if attached_video is not None:
        with st.container(border=True):
            st.markdown(f"**{T('composer.attach.panel')}**")
            st.caption(T("composer.attach.panel_hint"))
            render_video_query(embedded=True)
        st.divider()

    # One scenario ships today (career_decision) — use it directly; no
    # picker clutters the slim composer.
    scenario = next(iter(AVAILABLE_SCENARIOS))

    # Fill / clear utility row — iter #6: hidden on the cold start
    # (no input AND no prediction yet) because the 3 suggestion chips
    # already cover the "one-click prefill" job there. Surfaced after
    # the user has typed anything OR a prediction exists, so a
    # returning visitor can still wipe / reseed the form.
    _has_any_input = any(
        bool(str(st.session_state.get(f"input_{f.key}", "")).strip())
        for f in AVAILABLE_SCENARIOS[scenario]["input_fields"]
    )
    _has_prediction = st.session_state.get("current_prediction") is not None
    if _has_any_input or _has_prediction:
        col_a, col_b = st.columns([3, 2])
        with col_a:
            if st.button(
                T("new.fill_sample"),
                help=(
                    "Prefill every field with realistic example values "
                    "so you can see the entire prediction flow in one "
                    "click."
                ),
                use_container_width=True,
                type="secondary",
            ):
                for field in AVAILABLE_SCENARIOS[scenario]["input_fields"]:
                    if field.example_value:
                        st.session_state[f"input_{field.key}"] = (
                            field.example_value
                        )
                handle_field_key = "input_user_id"
                if not st.session_state.get(handle_field_key):
                    st.session_state[handle_field_key] = session_user_id()
                st.rerun()
        with col_b:
            if st.button(
                T("new.clear_form"),
                help="Reset all fields to empty.",
                use_container_width=True,
            ):
                for field in AVAILABLE_SCENARIOS[scenario]["input_fields"]:
                    st.session_state.pop(f"input_{field.key}", None)
                st.rerun()

    # Form fields — the core fields are visible; secondary / optional
    # fields fold into a "More details" expander so the composer stays a
    # compact, always-visible input bar.
    # Iter #1-bugfix: previously the filter `[f for f in fields if
    # f.key in _COMPOSER_CORE_FIELDS]` preserved the INPUT_FIELDS
    # order, ignoring the explicit _COMPOSER_CORE_FIELDS order. That
    # meant the iter #1 reorder ("decision is the hero, first field")
    # never took effect. Now the render order is taken FROM
    # _COMPOSER_CORE_FIELDS — the authoritative UI-order list.
    form_data: dict[str, Any] = {}
    fields = AVAILABLE_SCENARIOS[scenario]["input_fields"]
    _fields_by_key = {f.key: f for f in fields}
    core = [
        _fields_by_key[k]
        for k in _COMPOSER_CORE_FIELDS
        if k in _fields_by_key
    ]
    extra = [f for f in fields if f.key not in _COMPOSER_CORE_FIELDS]

    with st.form(key=f"form_{scenario}"):
        for field in core:
            form_data[field.key] = _render_composer_field(field)

        with st.expander(T("composer.more_fields"), expanded=False):
            for field in extra:
                form_data[field.key] = _render_composer_field(field)
            # Opt-in self-test flag — keeps owner data separable in the
            # calibration aggregates.
            form_data["is_owner_bias_flagged"] = st.checkbox(
                T("new.owner_bias"),
                value=False,
                help=(
                    "Check this if you are the project founder or "
                    "running an internal self-test."
                ),
            )

        submit = st.form_submit_button(
            T("new.generate"),
            use_container_width=True,
            type="primary",
        )

    # v4.16 P2: persist the latest prediction in st.session_state so the
    # top output region (and post-submit interactions — drill-down
    # clicks, view-mode toggles, γ sliders) read a stable snapshot
    # across reruns.
    if submit:
        is_valid, err = validate_input(form_data)
        if not is_valid:
            st.error(err)
            return

        user_id = form_data.get("user_id", "").strip()
        if not user_id:
            st.error("Please provide a user handle.")
            return

        # Iter #18: if the user pinned a backend in Settings → Model
        # & API and supplied a key, use it; else None falls through
        # to the env-var-driven default rotation.
        _user_backend = _resolve_user_backend()
        with st.spinner(T("new.generating")):
            try:
                program = compile_belief_program(
                    form_data, scenario=scenario, backend=_user_backend,
                )
                result = belief_program_to_console(program)
            except Exception as exc:  # noqa: BLE001 — show error to user
                st.error(f"Compilation failed: {exc}")
                return

            # Persist + freeze the snapshot in session_state for re-render.
            # Iter #50: the Turso write stays INSIDE the spinner so the
            # whole heavy step reads as one legible "working…" wait,
            # rather than the spinner vanishing while the form sits
            # frozen during the network save (the slow-tail "looks dead"
            # window on the free-tier host).
            rec = storage.PredictionRecord(
                prediction_id=storage.new_prediction_id(),
                user_id=user_id,
                scenario=scenario,
                created_at=storage.now_unix(),
                user_input=form_data,
                belief_program=program.raw,
                wavefunction_snapshot={
                    "hypotheses": [h.to_dict() for h in result.hypotheses],
                },
                joint_offdiag={
                    "entries": [o.to_dict() for o in result.joint_offdiag],
                },
                is_owner_bias_flagged=bool(
                    form_data.get("is_owner_bias_flagged", False)
                ),
            )
            storage.save_prediction(rec)
            _invalidate_history_cache()
            st.session_state.current_prediction = {
                "prediction_id": rec.prediction_id,
                "result": result,
                "form_data": form_data,
                "scenario": scenario,
                "user_id": user_id,
                "program": program,
            }
        # Chatbox layout: rerun so the TOP output region resolves the
        # heatmap from idle uniform → the real distribution.
        st.rerun()


def render_new_prediction() -> None:
    """The workspace — output region on top, composer below, ONE screen.

    The page itself does not scroll: the output region and the composer
    are each a fixed-height ``st.container`` pane, sized so the two
    together fit the viewport — the composer is always visible
    (WeChat-style) and scrolling one pane never moves the other.

    Streamlit reruns top→bottom: the output region reads the last
    prediction from ``st.session_state`` (idle heatmap if none); the
    composer computes a prediction, stores it, and reruns so the top
    updates. NOT a turn-by-turn chatbox — it borrows only the
    "one composer + attach" affordance.
    """
    # Reclaim Streamlit's tall default chrome padding so the workspace
    # starts at the top of the viewport — no marketing hero, the two
    # panes fit one screen.
    st.markdown(_WORKSPACE_CHROME_CSS, unsafe_allow_html=True)

    # Iter #47 bug-041 fix — first-paint ordering. A beta tester
    # landed, saw the EXAMPLE-PREVIEW heatmap + the full beta banner,
    # never scrolled past them to the input form below, and concluded
    # the app "does nothing". Root cause: on cold start the output
    # region (a placeholder preview) was rendered ON TOP, burying the
    # actual composer.
    #
    # Fix: branch on whether a prediction exists.
    #   • No prediction yet (cold start) → lead with the COMPOSER so
    #     the decision input + suggestion chips are the first thing a
    #     visitor sees ("here's where you type"). The example-preview
    #     heatmap renders BELOW as a "this is what you'll get" teaser.
    #   • Prediction exists → lead with the OUTPUT (the real result
    #     heatmap + CTA row), composer below for re-runs. Matches the
    #     user's mental model: empty → input-first; filled → result-
    #     first.
    # Iter #52 (founder): input belongs at the BOTTOM — the universal
    # chat-tool convention (Claude / ChatGPT / WeChat: content area on
    # top, the input bar pinned below). So ALWAYS render output on top
    # and the composer beneath, cold-start included. (This supersedes
    # the iter #47 cold-start flip that put the composer on top to aid
    # discovery; the output's "type a decision below" hint + the always-
    # visible bottom composer pane solve discovery without breaking the
    # chat mental model.)
    _render_workspace_output()
    _render_workspace_composer()

    # Iter #48 — "New prediction" visible-feedback: if the user just
    # clicked it, scroll the decision input into view + focus it so
    # the click always produces an obvious, sensible result (land at
    # the input, ready to type). One-shot flag, consumed here.
    if st.session_state.pop("_focus_composer", False):
        _scroll_focus_composer()


# ============================================================
# Mode 7 — Traditional × Calibrated (Nye-clock instrument)
#
# Two entry points share the same render helper below:
#   1. PRIMARY: a subtle expander at the end of the result page
#      ("Or read the same prediction the old way") — the founder's
#      "精妙小彩蛋" requirement. Discovered AFTER the user has seen
#      the model result, so the dial reads as an *alternate take* on
#      something they already trust.
#   2. SECONDARY: the sidebar's Mode 7 page — a standalone playground
#      where new visitors can twirl the dial without committing to a
#      full prediction. Prefills sample 八字 + sample branches so the
#      dial is alive on first view.
# ============================================================

def _render_traditional_lens(
    branches_or_none: list[Any] | None,
    *,
    key_prefix: str,
    sample_birth: tuple[int, int, int, int] = (2000, 6, 15, 12),
    sample_branches: list[tuple[str, float, str]] | None = None,
) -> None:
    """Render the unified 玄学 lens — one celestial astrolabe + 易经/塔罗
    companion instruments, all four systems jointly driving one decision.

    Shared between the result-page expander and the standalone Mode 7
    page. ``key_prefix`` namespaces the widget keys and seeds the
    deterministic 易经 / 塔罗 cast (same prediction → same reading).

    No system selector and no click-through: 八字 + 占星 share a single
    celestial astrolabe (both are read off the sky), 易经 + 塔罗 sit
    below it as companion instruments, and every system's auspice is
    aggregated into one 玄学-consensus prior that drives the per-branch
    Bayesian reweight — the whole module decides together.
    """
    import html as _html

    import _metaphysics as _mp
    from _clock import render_celestial_svg, render_reading_svg

    # ---- Lens header (iter #2 — design-self-explains) ----
    # The L3 thesis paragraph + "易经 cast · 八字 four pillars · ..."
    # explainer was 4 lines of reading. Replaced with an eyebrow tag
    # alone — the five instruments rendered below ARE the explanation;
    # the user looks down and sees what the lens does. No paragraph
    # to read.
    st.markdown(
        f"<div style='max-width:760px;margin:6px auto 10px;'>"
        f"<div style='color:#8a8f98;font-size:10px;font-weight:700;"
        f"letter-spacing:0.14em;text-transform:uppercase;'>"
        f"{_html.escape(str(T('lens.header.eyebrow')))}"
        f"<span style='color:#34343a;margin:0 8px;'>·</span>"
        f"<span style='color:#5e6ad2;font-weight:600;letter-spacing:0.10em;'>"
        f"5 systems"
        f"</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- Birth data — read from Settings → Personalization (R4) ----
    # XUANXUE_REDESIGN.md L2: personal data is not per-prediction. The
    # composer no longer asks. When the user hasn't set birth data, the
    # lens falls back to ``sample_birth`` and shows a small "set in
    # Settings" affordance — modules that don't need birth (I Ching,
    # tarot, Nye Clock, sun-sign) still work; BaZi / ZiWei / ascendant
    # read as a sample reading.
    _p_birth_on = bool(
        st.session_state.get("personalization_birth_enabled", False)
    )
    if _p_birth_on:
        b_year = int(
            st.session_state.get(
                "personalization_birth_year", sample_birth[0]
            )
        )
        b_month = int(
            st.session_state.get(
                "personalization_birth_month", sample_birth[1]
            )
        )
        b_day = int(
            st.session_state.get(
                "personalization_birth_day", sample_birth[2]
            )
        )
        b_hour = int(
            st.session_state.get(
                "personalization_birth_hour", sample_birth[3]
            )
        )
    else:
        b_year, b_month, b_day, b_hour = sample_birth
        st.markdown(
            "<div style='display:flex;gap:8px;align-items:flex-start;"
            "background:#0f1011;border:1px solid #23252a;border-radius:8px;"
            "padding:9px 12px;margin:2px auto 12px;max-width:760px;'>"
            "<span style='color:#8a8f98;font-size:11px;font-weight:700;"
            "letter-spacing:0.06em;text-transform:uppercase;"
            "padding-top:2px;'>·</span>"
            f"<span style='color:#c9cdd4;font-size:12px;line-height:1.55;'>"
            f"{T('settings.personalization.birth.unset_hint')}</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ---- Outcome + combination controls ----
    cc1, cc2, cc3 = st.columns([2, 2, 1.4])
    with cc1:
        outcome = st.selectbox(
            T("trad.outcome.select"),
            options=list(_mp.OUTCOME_CATEGORIES),
            format_func=lambda k: T(f"trad.outcome.{k}"),
            index=0,
            key=f"{key_prefix}_outcome",
        )
    with cc2:
        mode_options = ("mixture", "bayesian", "off")
        mode = st.selectbox(
            T("trad.combine.label"),
            options=mode_options,
            format_func=lambda k: T(f"trad.combine.{k}"),
            index=0,
            key=f"{key_prefix}_mode",
        )
    with cc3:
        alpha = st.slider(
            T("trad.alpha.label"),
            min_value=0.0, max_value=1.0, value=0.30, step=0.05,
            key=f"{key_prefix}_alpha",
            help=T("trad.alpha.hint"),
        )

    # ---- Run every system; aggregate into one 玄学 consensus ----
    birth = _mp.BirthData(year=int(b_year), month=int(b_month),
                          day=int(b_day), hour=int(b_hour))
    readings = _mp.compute_all_readings(
        birth=birth, seed=key_prefix, outcome=str(outcome),
    )
    joint_prior, joint_auspice = _mp.aggregate_readings(readings)

    # ---- Choose the focal branch (real or sample) ----
    using_sample = False
    if branches_or_none:
        hyps = branches_or_none
        realistic = [h for h in hyps if h.branch_type
                     not in ("wishful", "worst")]
        focal = max(realistic or hyps, key=lambda h: h.probability)
        model_prob = float(focal.probability)
        branch_data: list[tuple[str, float, str]] = [
            (h.label, float(h.probability), str(h.branch_type))
            for h in hyps
        ]
    elif sample_branches:
        using_sample = True
        branch_data = list(sample_branches)
        non_anchor = [(l, p, t) for l, p, t in branch_data
                      if t not in ("wishful", "worst")]
        focal_tuple = max(non_anchor or branch_data, key=lambda x: x[1])
        model_prob = float(focal_tuple[1])
    else:
        branch_data = []
        model_prob = 0.0

    # ---- Combine the focal model probability × the 玄学 consensus ----
    combined = _mp.combine_with_model(model_prob, joint_prior, mode, alpha)
    if mode == "bayesian":
        # Renormalize the focal posterior against its complement for
        # display (the readout centre focuses on ONE outcome category).
        denom = combined + (1 - joint_prior) * (1 - model_prob)
        combined = combined / denom if denom > 1e-9 else combined

    # ---- Per-branch Bayesian reweight, driven by the JOINT auspice —
    # the four traditions' mean favourability pulls the branch ring. ----
    eff_alpha = 0.0 if mode == "off" else float(alpha)
    display_branches = _mp.apply_lens_to_branches(
        branch_data, joint_auspice, eff_alpha,
    )

    model_value = f"{model_prob * 100:.1f}%"
    combined_value = f"{combined * 100:.1f}%"
    alpha_tag = f"α={alpha:.2f}" if mode != "off" else "model only"

    # ---- The consensus arrow (L3) — proof the lens MODULATES the model ----
    # The single header block that ties everything below back to the
    # branches the heatmap shows. When the symbolic systems agree, name
    # the favoured branch; when they disagree, say so. Then the live
    # tri-metric (Model · Tradition · Combined) sits beneath, so the
    # founder's "what does this DO to my prediction" question is
    # answered before the user sees any individual instrument.
    _has_branches = bool(display_branches)
    if _has_branches:
        _fav_label, _fav_prob, _fav_type = max(
            display_branches, key=lambda x: x[1]
        )
        # Disagreement test: the joint auspice sits in a near-neutral
        # band [0.46, 0.54] → no clear favourite. Otherwise we name
        # the branch the lens lifted to the top of the distribution.
        _contested = 0.46 <= joint_auspice <= 0.54
    else:
        _fav_label, _fav_prob, _contested = "", 0.0, False

    if not _has_branches:
        # The lens is on but the user hasn't run a prediction yet — the
        # math is still meaningful (the symbolic auspice exists), but
        # there's no specific branch to lift / drop. Say so honestly
        # rather than claiming the systems "disagree" (they may not).
        _consensus_html = _html.escape(
            str(T("lens.consensus.no_prediction"))
        )
    elif _contested:
        _consensus_html = _html.escape(str(T("lens.consensus.contests")))
    else:
        _consensus_html = (
            str(T("lens.consensus.favours"))
            .replace(
                "{branch}",
                f"<span style='color:#f7f8f8;'>"
                f"{_html.escape(str(_fav_label))}</span>",
            )
            .replace("{pct}", f"{joint_prior * 100:.0f}%")
        )

    _consensus_line = (
        str(T("lens.consensus.line"))
        .replace("{model}", f"<b style='color:#f7f8f8;'>{model_value}</b>")
        .replace(
            "{tradition}",
            f"<b style='color:#f7f8f8;'>{joint_prior * 100:.1f}%</b>",
        )
        .replace(
            "{combined}",
            f"<b style='color:#5e6ad2;'>{combined_value}</b>",
        )
        .replace("{tag}", _html.escape(alpha_tag))
    )

    # Iter #2: drop the L3 "Model alone X% · Joint symbolic Y% ·
    # COMBINED Z%" numeric line. That same data renders at the BOTTOM
    # of the lens as a visual delta arrow (MODEL → ↑ → COMBINED), so
    # repeating it here was forced double-reading. Keep only the one
    # plain-language sentence about WHICH branch the systems favour.
    st.markdown(
        f"<div style='max-width:760px;margin:0 auto 16px;"
        f"background:#0f1011;border:1px solid #23252a;border-radius:10px;"
        f"padding:11px 16px;'>"
        f"<div style='color:#c9cdd4;font-size:13px;line-height:1.5;'>"
        f"{_consensus_html}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- Module-card helper (iter #2 — title-only, no paragraph) ----
    # The L3 version always rendered a 1-2 line description below each
    # module title. That's the founder's text-crutch — 5 modules × 2
    # lines = 10 lines of forced reading. Now: title alone (the
    # instrument itself shows what it is). `desc_key` kept in the
    # signature for call-site stability but no longer rendered as a
    # body paragraph — only as a title=tooltip the cursor reveals on
    # hover for users who want the explainer.
    def _mod_header(
        title_key: str, desc_key: str, *, max_w: int = 560
    ) -> None:
        _title = _html.escape(str(T(title_key)))
        _desc = _html.escape(str(T(desc_key)))
        st.markdown(
            f"<div style='max-width:{max_w}px;margin:18px auto 6px;' "
            f"title='{_desc}'>"
            f"<div style='color:#f7f8f8;font-size:13px;font-weight:600;"
            f"letter-spacing:-0.005em;'>{_title}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ---- The unified celestial astrolabe — 八字 ⊕ 占星 on one dial ----
    # XUANXUE_REDESIGN.md L5: the Nye Clock is the visual centerpiece,
    # not a small inset. Companion instruments (易经 / 塔罗) stay at
    # 560px below it; the Nye Clock card stretches to the workspace
    # column edge (760px) so the real-image still reads at the
    # resolution the founder captured it at.
    _mod_header(
        "lens.module.astrolabe.title",
        "lens.module.astrolabe.desc",
        max_w=760,
    )
    astrolabe_svg = render_celestial_svg(
        readings[_mp.SYSTEM_BAZI], readings[_mp.SYSTEM_ASTRO],
        display_branches,
        center_top_label=T("trad.metric.model_short"),
        center_top_value=model_value,
        center_bottom_label=T("trad.metric.combined_short"),
        center_bottom_value=combined_value,
        center_meta=f"八字 ⊕ 占星 · {alpha_tag}",
    )
    st.markdown(
        f"<div style='background:#0f1011;border:1px solid #23252a;"
        f"border-radius:14px;padding:14px 14px 10px;margin:8px auto 10px;"
        f"max-width:760px;'>"
        f"{astrolabe_svg}</div>",
        unsafe_allow_html=True,
    )

    # ---- BaZi Four Pillars text readout (L6) ----
    # XUANXUE_REDESIGN.md L6. The dial shows the four pillars
    # spatially but doesn't read them out. This compact 4-card row
    # surfaces 年柱 · 月柱 · 日柱 · 时柱 as plain text: stem +
    # branch + five-element tag for each. Element-tinted left
    # accent shows the five-element distribution at a glance.
    _bazi_reading = readings[_mp.SYSTEM_BAZI]
    _bazi: _mp.BaZiPattern | None = _bazi_reading.bazi
    if _bazi is not None:
        _mod_header(
            "lens.module.bazi_pillars.title",
            "lens.module.bazi_pillars.desc",
            max_w=760,
        )
        _pillars = (
            (T("trad.birth.year"),  _bazi.year_pillar),
            (T("trad.birth.month"), _bazi.month_pillar),
            (T("trad.birth.day"),   _bazi.day_pillar),
            (T("trad.birth.hour"),  _bazi.hour_pillar),
        )
        _pcards: list[str] = [
            '<div style="display:grid;'
            'grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));'
            'gap:8px;'
            'max-width:760px;margin:6px auto 10px;">'
        ]
        for _ptitle, (_st_idx, _br_idx) in _pillars:
            _stem = _mp.HEAVENLY_STEMS[_st_idx]
            _branch = _mp.EARTHLY_BRANCHES[_br_idx]
            # The pillar's element is the stem's element by convention
            # (the day-master derivation also uses the day stem). Tag
            # both stem & branch elements separately below.
            _stem_wuxing_idx = _mp.WUXING_OF_STEM[_st_idx]
            _branch_wuxing_idx = _mp.WUXING_OF_BRANCH[_br_idx]
            _stem_el_key = _mp.WUXING_KEYS[_stem_wuxing_idx]
            _branch_el_key = _mp.WUXING_KEYS[_branch_wuxing_idx]
            _stem_color = _mp.WUXING_COLOR[_stem_el_key]
            _stem_hanzi = _mp.WUXING_HANZI[_stem_wuxing_idx]
            _branch_hanzi = _mp.WUXING_HANZI[_branch_wuxing_idx]
            _pcards.append(
                f'<div style="background:#0f1011;'
                f'border:1px solid #23252a;border-left:2px solid '
                f'{_stem_color};border-radius:8px;padding:10px 12px;">'
                f'<div style="color:#8a8f98;font-size:9.5px;'
                f'font-weight:700;letter-spacing:0.11em;'
                f'text-transform:uppercase;margin-bottom:6px;">'
                f'{_html.escape(str(_ptitle))}</div>'
                f'<div style="display:flex;align-items:baseline;'
                f'gap:4px;font-family:-apple-system,system-ui,sans-serif;">'
                f'<span style="color:#f7f8f8;font-size:22px;'
                f'font-weight:600;letter-spacing:-0.01em;">'
                f'{_html.escape(_stem)}</span>'
                f'<span style="color:#c9cdd4;font-size:20px;'
                f'font-weight:500;">'
                f'{_html.escape(_branch)}</span></div>'
                f'<div style="color:#8a8f98;font-size:10px;'
                f'letter-spacing:0.04em;margin-top:5px;'
                f'display:flex;gap:4px;align-items:center;">'
                f'<span style="color:{_stem_color};">'
                f'{_html.escape(_stem_hanzi)}</span>'
                f'<span style="opacity:0.5;">·</span>'
                f'<span style="color:{_mp.WUXING_COLOR[_branch_el_key]};">'
                f'{_html.escape(_branch_hanzi)}</span>'
                f'</div>'
                f'</div>'
            )
        _pcards.append('</div>')
        st.markdown("".join(_pcards), unsafe_allow_html=True)

    # ---- 易经 + 塔罗 + 星盘 — companion instruments below the astrolabe ----
    # L9: the 占星 reading was previously invisible (folded only into
    # the joint auspice); now rendered as its own natal-wheel panel
    # alongside I Ching and Tarot. Glyphs are forced text-style via
    # the U+FE0E variation selector on each ZODIAC sign, so the
    # founder's "emoji 表情的星座星盘" complaint is fixed at the
    # glyph level too.
    # bug-037 / P0 (revert L7): SYSTEM_ZIWEI was added to the lens loop
    # by iter L7, but _metaphysics.SYSTEMS deliberately EXCLUDES ziwei
    # because the 12-palace chart needs a lunar-calendar engine the
    # module doesn't have yet (honest-fallback discipline, see comment
    # in _metaphysics.py:67). `compute_all_readings` only populates
    # readings[k] for k in SYSTEMS — so readings["ziwei"] never
    # existed, and every prediction's result page crashed with a
    # KeyError. L7 is reverted here; the `_render_ziwei` renderer in
    # _clock.py is kept untouched for the future re-enable. The lens
    # loop is also wrapped in a `readings.get` defensive check, so any
    # similar SYSTEMS-mismatch in future never crashes — it silently
    # skips the missing instrument.
    _mod_meta = (
        (_mp.SYSTEM_ICHING, "易经 I CHING",
         "lens.module.iching.title", "lens.module.iching.desc"),
        (_mp.SYSTEM_TAROT, "塔罗 TAROT",
         "lens.module.tarot.title", "lens.module.tarot.desc"),
        (_mp.SYSTEM_ASTRO, "本命星盘 NATAL",
         "lens.module.astro.title", "lens.module.astro.desc"),
    )
    for sysk, label, title_key, desc_key in _mod_meta:
        reading_for_sys = readings.get(sysk)
        if reading_for_sys is None:
            # Defensive: a system the lens listed but `readings` does
            # not contain. Skip rather than crash; this is the guard
            # bug-037 wanted to install permanently.
            continue
        _mod_header(title_key, desc_key)
        panel_svg = render_reading_svg(
            reading_for_sys, display_branches,
            center_top_label=T("trad.metric.model_short"),
            center_top_value=model_value,
            center_bottom_label=T("trad.metric.combined_short"),
            center_bottom_value=combined_value,
            center_meta=f"{label} · {alpha_tag}",
        )
        st.markdown(
            f"<div style='background:#0f1011;border:1px solid #23252a;"
            f"border-radius:12px;padding:16px 14px;margin:6px auto 10px;"
            f"max-width:560px;'>"
            f"{panel_svg}</div>",
            unsafe_allow_html=True,
        )

    if using_sample:
        st.caption(T("trad.using_sample"))

    # ---- Per-system consensus chips — each tradition's favourability,
    # so the user sees for themselves whether the four agree ----
    _mod_header("lens.module.chips.title", "lens.module.chips.desc")
    chips = ['<div style="display:flex;gap:8px;flex-wrap:wrap;'
             'justify-content:center;margin:6px auto 2px;max-width:560px;">']
    for sysk in _mp.SYSTEMS:
        ausp = readings[sysk].auspice
        # Favourability — a restrained semantic green / red, with a
        # neutral grey for the unremarkable middle. No accent as a
        # data-viz fill.
        col = ("#27a644" if ausp >= 0.56
               else "#dc4c5a" if ausp <= 0.44 else "#8a8f98")
        pct = ausp * 100.0
        chips.append(
            f'<div style="flex:1;min-width:112px;background:#0f1011;'
            f'border:1px solid #23252a;border-radius:8px;'
            f'padding:9px 11px 10px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;">'
            f'<span style="color:#8a8f98;font-size:8.5px;'
            f'letter-spacing:0.12em;text-transform:uppercase;">'
            f'{_html.escape(str(T(f"trad.system.{sysk}")))}</span>'
            f'<span style="color:{col};font-size:15px;font-weight:600;'
            f"font-family:-apple-system,BlinkMacSystemFont,system-ui,Roboto,Helvetica,Arial,sans-serif;\">"
            f'{pct:.0f}%</span></div>'
            f'<div style="margin-top:6px;height:4px;border-radius:2px;'
            f'background:#23252a;overflow:hidden;">'
            f'<div style="height:100%;width:{pct:.0f}%;background:{col};'
            f'border-radius:2px;"></div></div></div>'
        )
    chips.append('</div>')
    st.markdown("".join(chips), unsafe_allow_html=True)

    # ---- Joint tri-metric readout (iter #2 — title dropped) ----
    # The "How the lens modulates the model" title + description was
    # text duplication of what st.metric labels already show. The 3
    # st.metric pills (Model · Tradition · Combined) are self-labelled
    # and self-explanatory — no header card needed.
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(T("trad.metric.model"), f"{model_prob * 100:.1f}%")
    with m2:
        st.metric(T("trad.metric.tradition"), f"{joint_prior * 100:.1f}%")
    with m3:
        st.metric(T("trad.metric.combined"), f"{combined * 100:.1f}%")

    # ---- The takeaway delta (iter #2 — visual, not a sentence) ----
    # The L3 takeaway was a full sentence ("The lens lifts the focal
    # branch from 22.0% to 27.0% — a 5.0 pp upward modulation") —
    # forced reading. Replaced with a visual delta strip: MODEL → COMBINED
    # with a coloured arrow ↑ / ↓ / · and the pp magnitude as a tag.
    # No sentence — the symbols carry it.
    _delta = combined - model_prob
    _delta_abs = abs(_delta)
    if _delta_abs < 0.005:
        _arrow = "·"
        _arrow_color = "#8a8f98"
    elif _delta > 0:
        _arrow = "↑"
        _arrow_color = "#27a644"
    else:
        _arrow = "↓"
        _arrow_color = "#dc4c5a"
    _delta_tag = f"{_delta_abs * 100:.1f}pp"
    st.markdown(
        f"<div style='max-width:760px;margin:14px auto 4px;"
        f"background:#0f1011;border:1px solid #34343a;border-radius:10px;"
        f"padding:13px 18px;display:flex;align-items:center;"
        f"justify-content:center;gap:14px;flex-wrap:wrap;'>"
        # MODEL pill
        f"<div style='display:flex;flex-direction:column;align-items:flex-end;"
        f"gap:2px;'>"
        f"<span style='color:#8a8f98;font-size:9px;font-weight:700;"
        f"letter-spacing:0.14em;text-transform:uppercase;'>MODEL</span>"
        f"<span style='color:#c9cdd4;font-size:18px;font-weight:600;"
        f"letter-spacing:-0.01em;'>{model_prob * 100:.1f}%</span>"
        f"</div>"
        # arrow + delta tag
        f"<div style='display:flex;flex-direction:column;align-items:center;"
        f"gap:2px;'>"
        f"<span style='color:{_arrow_color};font-size:22px;font-weight:700;"
        f"line-height:1;'>{_arrow}</span>"
        f"<span style='color:{_arrow_color};font-size:10px;font-weight:600;"
        f"letter-spacing:0.06em;'>{_delta_tag}</span>"
        f"</div>"
        # COMBINED pill
        f"<div style='display:flex;flex-direction:column;align-items:flex-start;"
        f"gap:2px;'>"
        f"<span style='color:#5e6ad2;font-size:9px;font-weight:700;"
        f"letter-spacing:0.14em;text-transform:uppercase;'>COMBINED</span>"
        f"<span style='color:#f7f8f8;font-size:18px;font-weight:600;"
        f"letter-spacing:-0.01em;'>{combined * 100:.1f}%</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- L10: per-branch modulation visualization ----
    # The single-branch takeaway delta above shows what the lens did
    # to the FOCAL branch. L10 closes the redesign by showing the
    # lens's effect on EVERY branch — paired bars (grey = model,
    # lavender = combined) so the user sees which branches the lens
    # lifts and which it lowers. This is the visual link between
    # the lens and the workspace's heatmap that XUANXUE_REDESIGN.md
    # §5.7 specifies — the proof that the lens MODULATES the world
    # model rather than running in parallel.
    if branch_data and display_branches:
        _mod_header(
            "lens.module.delta.title",
            "lens.module.delta.desc",
            max_w=760,
        )
        # Pair model-prob ↔ combined-prob by label so reordering
        # (which apply_lens_to_branches doesn't do, but defensive
        # programming) doesn't misalign.
        _model_by_label = {l: p for l, p, _ in branch_data}
        _combined_by_label = {l: p for l, p, _ in display_branches}
        _max_p = max(
            [p for p in _model_by_label.values()]
            + [p for p in _combined_by_label.values()]
            + [0.01]
        )
        # Sort by combined-prob descending so the lens-favoured
        # branches sit at the top.
        _ordered = sorted(
            (
                (lbl, _model_by_label.get(lbl, 0.0), p, btype)
                for lbl, p, btype in display_branches
            ),
            key=lambda x: -x[2],
        )
        _rows: list[str] = [
            "<div style='max-width:760px;margin:6px auto 10px;"
            "display:flex;flex-direction:column;gap:6px;'>"
        ]
        for lbl, m_p, c_p, _btype in _ordered:
            _m_w = (m_p / _max_p) * 100.0
            _c_w = (c_p / _max_p) * 100.0
            _delta_p = c_p - m_p
            _delta_color = (
                "#27a644" if _delta_p > 0.005
                else "#dc4c5a" if _delta_p < -0.005
                else "#8a8f98"
            )
            _delta_sign = (
                "+" if _delta_p > 0.005
                else "−" if _delta_p < -0.005
                else "·"
            )
            _delta_tag = (
                f"{_delta_sign}{abs(_delta_p) * 100:.1f}pp"
                if abs(_delta_p) > 0.005
                else "·"
            )
            _rows.append(
                f"<div style='background:#0f1011;"
                f"border:1px solid #23252a;border-radius:8px;"
                f"padding:9px 12px 8px;'>"
                # label + delta tag row
                f"<div style='display:flex;align-items:center;"
                f"justify-content:space-between;margin-bottom:6px;'>"
                f"<span style='color:#f7f8f8;font-size:12px;"
                f"font-weight:500;letter-spacing:-0.005em;'>"
                f"{_html.escape(str(lbl))[:48]}</span>"
                f"<span style='color:{_delta_color};font-size:11px;"
                f"font-weight:700;letter-spacing:0.04em;"
                f"font-family:-apple-system,system-ui,sans-serif;'>"
                f"{_delta_tag}</span>"
                f"</div>"
                # model bar (grey)
                f"<div style='display:flex;align-items:center;gap:8px;"
                f"margin-bottom:3px;'>"
                f"<span style='color:#8a8f98;font-size:9px;"
                f"font-weight:700;letter-spacing:0.1em;width:54px;"
                f"text-align:right;'>MODEL</span>"
                f"<div style='flex:1;height:6px;border-radius:3px;"
                f"background:#181c25;overflow:hidden;'>"
                f"<div style='height:100%;width:{_m_w:.1f}%;"
                f"background:#c9cdd4;border-radius:3px;'></div></div>"
                f"<span style='color:#c9cdd4;font-size:11px;"
                f"font-weight:600;width:44px;'>"
                f"{m_p * 100:.1f}%</span></div>"
                # combined bar (lavender)
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span style='color:#5e6ad2;font-size:9px;"
                f"font-weight:700;letter-spacing:0.1em;width:54px;"
                f"text-align:right;'>COMBINED</span>"
                f"<div style='flex:1;height:6px;border-radius:3px;"
                f"background:#181c25;overflow:hidden;'>"
                f"<div style='height:100%;width:{_c_w:.1f}%;"
                f"background:#5e6ad2;border-radius:3px;'></div></div>"
                f"<span style='color:#f7f8f8;font-size:11px;"
                f"font-weight:600;width:44px;'>"
                f"{c_p * 100:.1f}%</span></div>"
                f"</div>"
            )
        _rows.append("</div>")
        st.markdown("".join(_rows), unsafe_allow_html=True)

    # ---- Always-visible disclaimer (integrity gate per spec §7) ----
    st.markdown(
        f"<div style='color:#8a8f98;font-size:11.5px;line-height:1.55;"
        f"max-width:760px;margin:16px auto 4px;letter-spacing:0.005em;'>"
        f"{T('trad.disclaimer')}</div>",
        unsafe_allow_html=True,
    )


_TRAD_SAMPLE_BRANCHES: list[tuple[str, float, str]] = [
    ("Take the offer",       0.32, "realistic"),
    ("Stay & negotiate",     0.27, "realistic"),
    ("Pivot to research",    0.18, "wishful"),
    ("Wait one quarter",     0.15, "realistic"),
    ("Withdraw entirely",    0.08, "worst"),
]


def render_traditional_view() -> None:
    """Mode 7 — standalone "古法 × 校准" page.

    Lightweight playground. New visitors who land here see a populated
    dial immediately (sample 八字 + sample branches), so the brand's
    cultural differentiator works in one click without forcing them
    to type a decision first. Users who *do* have a current prediction
    see the dial driven by that prediction's branches.
    """
    # Iter #16: quiet left-aligned page title; the lens instruments
    # below name what they are. Same de-marketing-hero pass as iter
    # #15 for the secondary pages.
    st.markdown(
        f"<div style='margin:8px 0 14px;'>"
        f"<h2 style='color:#f7f8f8;font-size:22px;font-weight:600;"
        f"letter-spacing:-0.012em;margin:0;'>"
        f"{T('trad.hero.title')}</h2>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Try to use the user's current prediction; fall back to sample.
    current = st.session_state.get("current_prediction")
    branches = None
    if current is not None and current.get("result") is not None:
        branches = list(current["result"].hypotheses)

    _render_traditional_lens(
        branches,
        key_prefix="_trad_standalone",
        sample_birth=(2000, 6, 15, 12),
        sample_branches=_TRAD_SAMPLE_BRANCHES,
    )


# Iter #40 phase-1 — `_dt_today_plus_months`, `_build_review_ics`,
# and `_humanize_id` moved to `_measurement_loop.py`. They're imported
# at the top of this module (search for `from _measurement_loop`).
# Phase 2/3 will continue the decomposition (rendering layer +
# routing); for now the rest of the measurement-loop UI surfaces
# (`_render_story_card`, `_render_score_due_banner`, etc.) stay here
# because they bind heavily to st.* primitives + module-scoped
# helpers, which a clean module boundary would force re-plumbing.


def _render_story_card(
    h: Any,
    kind_tag: str,
    recommended_evidence: list[dict[str, Any]] | None = None,
) -> None:
    """v4.16 P4 — narrative-first card. Narrative is the headline;
    probability + label + metadata sit in a smaller footer caption.
    Inverts the previous machine-table priority where label/probability
    led the visual hierarchy.

    Iter #21+22 P1.4 — "Why this probability?" reveal.
    Founder live-audit: "给每个概率加一句 '为什么是这个概率 / 哪些
    输入最影响它 / 置信度多高'". Iter 21 shipped the structural slot
    surfacing existing Hypothesis fields (key_uncertainty_driver,
    depends_on_decision). Iter 22 (Phase 2) wires REAL driver data —
    `recommended_evidence` already carries a `target_branch` field
    that lets us filter the existing evidence list per branch and
    show "Collect X → expected +Yp shift" entries. No fabrication;
    the data is already computed by the compile step.
    """
    with st.container(border=True):
        st.markdown(
            f"### {kind_tag} {storyform_narrative(h.narrative, h.branch_type)}"
        )
        # Iter #25 P1.4 Phase 3 — per-branch confidence signal.
        # Founder audit item 3 of the per-probability ask:
        # "置信度多高". Honest proxy: count recommended_evidence
        # items that target this specific branch. More levers we
        # can name → more calibrated the probability. Three tiers
        # are enough — finer-grained pretend-confidence would be
        # fabrication.
        n_for_branch = 0
        if recommended_evidence:
            n_for_branch = sum(
                1 for rec in recommended_evidence
                if rec.get("target_branch") == h.label
            )
        # Iter #26: route the confidence tier through i18n. The iter
        # 25 ship was English-only — these qualitative labels read
        # very differently across locales (the ZH "well-calibrated"
        # in particular needed a literal translation, not a
        # transliteration). Strings live in _i18n.py:result.confidence_*.
        if n_for_branch >= 2:
            confidence_tier = T("result.confidence_well_calibrated")
        elif n_for_branch == 1:
            confidence_tier = T("result.confidence_single_source")
        else:
            confidence_tier = T("result.confidence_soft_estimate")
        # Iter #30: humanized labels in the meta line. The raw branch
        # label / decision id / driver id were snake_case dev
        # internals; founder audit flagged them as un-user-friendly.
        # `branch` removed from meta (the internal label adds no user
        # value); decision dep + key uncertainty now read as prose.
        meta_parts = [
            f"**{h.probability * 100:.1f}%** probability",
            f"_{confidence_tier}_",
        ]
        if h.depends_on_decision:
            meta_parts.append(
                f"if you {_humanize_id(h.depends_on_decision).lower()}"
            )
        if h.key_uncertainty_driver:
            meta_parts.append(
                f"hinges on _{_humanize_id(h.key_uncertainty_driver)}_"
            )
        st.caption(" · ".join(meta_parts))

        # iter #21+22 P1.4: per-branch "Why this probability?" reveal.
        # Phase 1 (iter 21) surfaced existing Hypothesis fields.
        # Phase 2 (iter 22) filters `recommended_evidence` by its
        # `target_branch` so each branch's expander now contains the
        # REAL driver list — not just a "coming later" caption. The
        # data was already computed by compile_belief_program; we're
        # just routing it per branch.
        has_extras = bool(h.key_uncertainty_driver) or bool(
            h.depends_on_decision
        )
        # Filter evidence to those whose target_branch matches this
        # hypothesis. normalize_evidence_list sorts by ΔP descending
        # so the top driver leads.
        per_branch_evidence: list[dict[str, Any]] = []
        if recommended_evidence:
            normalized = normalize_evidence_list(recommended_evidence)
            per_branch_evidence = [
                rec for rec in normalized
                if rec.get("target_branch") == h.label
            ]
        has_drivers = bool(per_branch_evidence)
        # Iter #40 (founder round-3 #2): derive provenance label from
        # the available signals. Default ConsoleHypothesis carries
        # `probability_provenance="llm_estimate"`; the render layer
        # promotes it to "evidence_proxy" when ≥1 evidence item is
        # mapped to this branch (the same signal the confidence tier
        # reads). Future code path will set "historical_calibrated"
        # once enough measurement_updates exist; "user_adjusted" is
        # reserved for a future "nudge the probability" affordance.
        provenance_field = getattr(
            h, "probability_provenance", "llm_estimate",
        )
        if provenance_field == "llm_estimate" and n_for_branch >= 1:
            # Promote at render — backend hasn't set it yet but the
            # evidence-count signal warrants the upgraded tag.
            provenance_field = "evidence_proxy"
        provenance_i18n_key = {
            "llm_estimate": "result.provenance_llm_estimate",
            "evidence_proxy": "result.provenance_evidence_proxy",
            "historical_calibrated": (
                "result.provenance_historical_calibrated"
            ),
            "user_adjusted": "result.provenance_user_adjusted",
        }.get(provenance_field, "result.provenance_llm_estimate")
        with st.expander(T("result.why_probability_label"), expanded=False):
            # Provenance comes FIRST in the expander — answers "where
            # does this probability come from" before "what would
            # change it". The founder audit ask was specifically to
            # prevent the confidence tier being misread as
            # statistical confidence; provenance disambiguates that.
            st.markdown(
                f"**{T('result.provenance_source_label')}** "
                f"_{T(provenance_i18n_key)}_"
            )
            if h.key_uncertainty_driver:
                # Iter #30: prose-ify the key uncertainty so users
                # read "Team culture: actual vs. pitch" instead of
                # "team_culture_actual_vs_pitch".
                st.markdown(
                    f"**{T('result.why_hinges_on')}** "
                    f"_{_humanize_id(h.key_uncertainty_driver)}_"
                )
            if h.depends_on_decision:
                st.markdown(
                    f"**{T('result.why_depends_on')}** "
                    f"{_humanize_id(h.depends_on_decision)}"
                )
            if not has_extras and not has_drivers:
                st.caption(T("result.why_no_extras"))
            # Iter #22 P1.4 Phase 2: top drivers — real ΔP-style
            # evidence items mapped to this branch. The user can see
            # which evidence collection moves THIS branch the most,
            # per the founder's "哪些输入最影响它" ask.
            if has_drivers:
                st.markdown(f"**{T('result.why_top_drivers')}**")
                # Cap at 3 to avoid overwhelming the expander; the
                # full list is still available in the existing
                # "Recommended evidence to collect" section below.
                # Iter #30 — evidence labels humanized via _humanize_id
                # so they read as prose, not snake_case dev internals.
                for rec in per_branch_evidence[:3]:
                    raw_label = rec.get("evidence_label", "")
                    label = _humanize_id(raw_label) if raw_label else ""
                    dp = rec.get("expected_delta_p", 0.0)
                    rationale = rec.get("rationale", "")
                    pp = int(round(dp))
                    sign = "+" if pp >= 0 else ""
                    delta_str = f"{sign}{pp}pp" if pp != 0 else "≈0pp"
                    line = (
                        f"- **{label}** — _{delta_str} expected shift_"
                    )
                    if rationale:
                        line += f". {rationale}"
                    st.markdown(line)
            elif has_extras:
                # Has key_uncertainty_driver/decision but no per-branch
                # evidence — surface a softer line, not the cold
                # no-extras message that contradicts what we already
                # showed.
                st.caption(T("result.why_no_specific_drivers"))


def _render_story_view(
    wishful: list[Any],
    realistic: list[Any],
    worst: list[Any],
    decision_options: list[str],
    recommended_evidence: list[dict[str, Any]] | None = None,
) -> None:
    """v4.16 P4 — story-view layout: wishful (hope) → realistic
    (likely) → worst (caution). Each branch rendered as a
    narrative-first card via _render_story_card.

    Iter #22 P1.4 Phase 2 — `recommended_evidence` is threaded
    through so each story card's "Why this probability?" expander
    can show per-branch top drivers (filtered by `target_branch`).
    Default-None keeps every other call site compatible.
    """
    if wishful:
        st.subheader("🌟 Best plausible case")
        st.caption(
            "The hoped-for future. Low probability but emotionally vivid. "
            "Use this as the anchor for thinking about what evidence / "
            "actions would shift its probability upward."
        )
        for h in wishful:
            _render_story_card(h, "🌟", recommended_evidence)

    if realistic:
        st.subheader("📊 Most-likely futures")
        st.caption(
            f"{len(realistic)} realistic branches across decision options: "
            f"{', '.join(decision_options)}"
        )
        for h in sorted(realistic, key=lambda x: -x.probability):
            _render_story_card(h, "📊", recommended_evidence)

    if worst:
        st.subheader("⚠️ Worst plausible case")
        st.caption(
            "The future to actively avoid. Low probability but specific. "
            "Use this to identify what preventive actions you should "
            "take regardless of which decision you pick."
        )
        for h in worst:
            _render_story_card(h, "⚠️", recommended_evidence)


def _render_comparison_table(result: ConsoleResult) -> None:
    """v4.16 P4 — side-by-side comparison view for users who want the
    classic table-shaped overview."""
    st.subheader(T("result.view.comparison_title"))
    st.caption(
        "Same data as the story view, laid out for quick scanning. "
        "Useful when you need to compare two branches' "
        "probability / decision / key driver side-by-side."
    )
    rows = build_branch_comparison_rows(result)
    if not rows:
        st.info("No branches to compare.")
        return
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_decision_timeline(
    result: ConsoleResult,
    user_input: dict[str, Any],
) -> None:
    """v4.16 P4 — Mermaid flowchart showing decision → branch leaves
    along the user's time horizon. Streamlit can render a fenced
    ```mermaid block on supported versions; older versions fall back
    to a code display."""
    st.subheader(T("result.view.timeline_title"))
    horizon = str(user_input.get("time_horizon", "decision horizon"))
    st.caption(
        f"How each decision option fans out into branches over {horizon}. "
        "🌟 = best-case anchor · 📊 = realistic · ⚠️ = worst-case anchor."
    )
    diagram = build_decision_timeline_mermaid(
        result, time_horizon_label=horizon,
    )
    # Streamlit 1.34+ renders ```mermaid code blocks natively in
    # st.markdown. On older versions the user still sees the syntax
    # rendered as a fenced code block — readable, just not graphical.
    st.markdown(f"```mermaid\n{diagram}\n```")


def _render_continuous_distribution(
    result: ConsoleResult,
    user_input: dict[str, Any],
) -> None:
    """v4.16 P3 — continuous density-over-time view of the discrete
    branch distribution. Each branch contributes a Gaussian kernel
    centered at a heuristic 'characteristic time' (wishful early,
    realistic mid, worst late); the chart sums them into a single
    density curve."""
    horizon_label = str(user_input.get("time_horizon", "6 months"))
    horizon_months = float(_parse_time_horizon_to_steps(horizon_label))
    chart = build_continuous_distribution(
        result, time_horizon_months=horizon_months,
    )
    if chart is None or chart.get("n_points", 0) < 2:
        st.info(
            "No branches to plot a continuous distribution for."
        )
        return

    st.subheader(T("result.view.continuous_title"))
    st.caption(
        f"Each of {len(result.hypotheses)} branches contributes a "
        f"Gaussian kernel (σ ≈ {chart['sigma_months']:.1f} months) at "
        f"a heuristic characteristic time — wishful branches centered "
        f"around month {chart['horizon_months'] * 0.2:.1f}, realistic "
        f"around month {chart['horizon_months'] * 0.5:.1f}, worst "
        f"around month {chart['horizon_months'] * 0.7:.1f}. The "
        f"curve is the probability-weighted sum. Use this when the "
        f"discrete-branch table feels too engineering-shaped."
    )

    # Build chart data: a dict keyed by "Total density" + each branch
    # contribution. Streamlit's area_chart takes a dict of column
    # name → list of values and uses index for x-axis.
    chart_data: dict[str, list[float]] = {
        "Total density": chart["density"],
    }
    # Optional: include each branch's individual contribution to
    # the right of the legend so users can see where each kernel
    # peaks.
    for label, series in chart["per_branch_density"].items():
        chart_data[label] = series

    # Convert x-axis from index to "month N" labels via a pandas-free
    # workaround: just print the months alongside.
    st.area_chart(chart_data)
    st.caption(
        "x-axis = sample index 0…N along the time horizon; first "
        "sample is t=0 and last is t={:.0f} months.".format(
            chart["horizon_months"]
        )
    )

    # Per-branch characteristic-time summary table.
    summary_rows: list[dict[str, Any]] = []
    for label, mu in chart["characteristic_times"].items():
        hyp = next(
            (h for h in result.hypotheses if h.label == label), None,
        )
        if hyp is None:
            continue
        summary_rows.append({
            "Branch": label,
            "Type": hyp.branch_type,
            "Probability": f"{hyp.probability * 100:.1f}%",
            "Characteristic time": f"month {mu:.1f}",
        })
    if summary_rows:
        st.markdown("**Characteristic-time anchors**")
        st.dataframe(
            summary_rows, hide_index=True, use_container_width=True,
        )


def _render_drilldown_section(
    result: ConsoleResult,
    user_input: dict[str, Any],
    scenario: str,
    prediction_id: str,
) -> None:
    """v4.16 P2 — drill-down loop. Lets the user pick any branch and
    get an LLM-generated deep dive (3-paragraph narrative + concrete
    actions + conditional dependencies + sensitivity preview).

    Caches the LLM output in SQLite (branch_drilldowns table) keyed
    by (prediction_id, branch_label) so repeated clicks don't burn
    quota. Refresh button forces a re-call.
    """
    with st.expander("🔍 Drill down on one of these futures", expanded=False):
        st.caption(
            "Pick a branch you care about most — typically the wishful "
            "one if you want to plan toward it, or the worst-case if "
            "you want to plan around it — and the system will expand "
            "it into a 3-paragraph deeper narrative + concrete actions "
            "this week + dependencies that gate it + sensitivity preview."
        )

        # Sort hypotheses with the same reading order the story view uses.
        type_order = {"wishful": 0, "realistic": 1, "worst": 2}
        sorted_h = sorted(
            result.hypotheses,
            key=lambda h: (type_order.get(h.branch_type, 1), -h.probability),
        )
        labels = [h.label for h in sorted_h]
        label_to_hyp = {h.label: h for h in sorted_h}
        if not labels:
            st.info("No branches to drill into.")
            return

        chosen_label = st.selectbox(
            "Branch to drill into",
            options=labels,
            format_func=lambda lbl: (
                f"{_emoji_for_type(label_to_hyp[lbl].branch_type)} "
                f"{lbl} ({label_to_hyp[lbl].probability * 100:.0f}%)"
            ),
        )

        cached = storage.get_drilldown(prediction_id, chosen_label)
        cache_present = cached is not None

        col_a, col_b = st.columns([1, 1])
        with col_a:
            run = st.button(
                "Run drill-down" if not cache_present
                else "Show cached drill-down",
                use_container_width=True,
            )
        with col_b:
            refresh = st.button(
                "↻ Re-run (force refresh)",
                disabled=not cache_present,
                use_container_width=True,
                help=(
                    "Forces a fresh LLM call. Costs another API "
                    "request — only use if the cached output looks "
                    "wrong or outdated."
                ),
            )

        if refresh and cache_present:
            storage.delete_drilldown(prediction_id, chosen_label)
            cached = None
            cache_present = False

        chosen_hyp = label_to_hyp[chosen_label]

        if (run or refresh) and not cache_present:
            with st.spinner(
                f"Drilling into `{chosen_label}` via LLM…"
            ):
                try:
                    drilldown = compile_branch_drilldown(
                        branch_label=chosen_label,
                        branch_type=chosen_hyp.branch_type,
                        full_belief_program=_dump_program_for_drilldown(
                            chosen_hyp, result,
                        ),
                        user_input=user_input,
                        scenario=scenario,
                        # Iter #18: respect the user's pinned backend
                        # for drill-downs too (else fall to default).
                        backend=_resolve_user_backend(),
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Drill-down failed: {exc}")
                    return
            rec = storage.BranchDrilldown(
                drilldown_id=storage.new_drilldown_id(),
                prediction_id=prediction_id,
                branch_label=chosen_label,
                created_at=storage.now_unix(),
                drilldown_json=drilldown,
            )
            storage.save_drilldown(rec)
            cached = rec

        if cached is not None:
            _render_drilldown_body(cached, chosen_hyp)


def _emoji_for_type(branch_type: str) -> str:
    return {
        "wishful": "🌟",
        "worst": "⚠️",
        "realistic": "📊",
    }.get(branch_type, "•")


def _dump_program_for_drilldown(
    chosen_hyp: Any, result: ConsoleResult,
) -> dict[str, Any]:
    """Build a compact dict representation of the BeliefProgram for the
    drill-down LLM call — omits the wavefunction snapshots / Omytea
    runtime objects, only the user-facing data."""
    return {
        "scenario": result.scenario,
        "decision_options": list(result.decision_options),
        "chosen_branch": chosen_hyp.to_dict(),
        "all_branches": [h.to_dict() for h in result.hypotheses],
        "joint_offdiag": [o.to_dict() for o in result.joint_offdiag],
        "recommended_evidence": list(result.recommended_evidence),
    }


def _render_drilldown_body(
    cached: Any, chosen_hyp: Any,
) -> None:
    """Render the drill-down dict in a single nicely-organized block."""
    body = cached.drilldown_json
    st.markdown(
        f"### {_emoji_for_type(chosen_hyp.branch_type)} Drill-down: "
        f"`{cached.branch_label}` "
        f"({chosen_hyp.probability * 100:.1f}%)"
    )

    # Deeper narrative — 3 paragraphs.
    narrative = body.get("deeper_narrative") or []
    if narrative:
        st.subheader("Deeper narrative")
        for para in narrative:
            st.write(para)

    # Concrete actions this week.
    actions = body.get("concrete_actions_this_week") or []
    if actions:
        st.subheader("Concrete actions this week")
        for a in actions:
            with st.container(border=True):
                st.markdown(f"**{a.get('action', '')}**")
                effort = a.get("effort", "")
                if effort:
                    st.caption(f"Effort: {effort}")
                if a.get("expected_effect"):
                    st.caption(f"Expected effect: {a['expected_effect']}")

    # Conditional dependencies.
    deps = body.get("conditional_dependencies") or []
    if deps:
        st.subheader("Conditional dependencies")
        for d in deps:
            with st.container(border=True):
                st.markdown(f"**{d.get('condition', '')}**")
                cs = d.get("current_state", "")
                impact = d.get("impact_if_fails", "")
                if cs:
                    st.caption(f"Current state: {cs}")
                if impact:
                    st.caption(f"If this fails: {impact}")

    # Sensitivity preview.
    sens = body.get("sensitivity_preview") or []
    if sens:
        st.subheader("Sensitivity preview")
        st.caption(
            "What collecting each piece of evidence would do to this "
            "branch's probability specifically (in percentage points)."
        )
        for s in sens:
            with st.container(border=True):
                st.markdown(f"**{s.get('evidence_label', 'unknown')}**")
                up = s.get("if_positive_delta_p", 0)
                down = s.get("if_negative_delta_p", 0)
                cols = st.columns(2)
                with cols[0]:
                    st.metric(
                        "If signal supports",
                        f"+{int(round(float(up)))} pp",
                    )
                with cols[1]:
                    st.metric(
                        "If signal cuts against",
                        f"{int(round(float(down)))} pp",
                    )

    st.caption(
        f"Cached at {cached.created_at:.0f} (unix). Re-run with "
        f"the refresh button if context has changed materially."
    )


def _render_coherence_evolution(
    result: ConsoleResult,
    user_input: dict[str, Any],
) -> None:
    """Render the C1 'coherence over time' chart + summary table.

    Uses the user's `time_horizon` form field as the default evolution
    window and γ=0.05/month decoherence rate (the conservative default).
    Pure decay (no phase rotation) so the visual story is unambiguous:
    "this is how fast your correlations wash out into independent
    classical futures."
    """
    default_steps = _parse_time_horizon_to_steps(
        str(user_input.get("time_horizon", "6 months"))
    )

    chart = build_coherence_chart_data(
        result,
        time_horizon_months=default_steps,
        decoherence_rate_per_month=0.05,
        use_branch_energies=False,
    )
    if chart is None:
        return

    st.subheader("📉 Coherence decay over time")
    st.caption(
        "Off-diagonal magnitudes |ρ_ab| evolve under a Lindblad "
        "decoherence channel at γ=0.05/month (pure-decay; no phase "
        "rotation shown). When a pair's magnitude approaches zero, "
        "those two futures stop interfering and become independent — "
        "you've lost the window where they're 'coupled enough to "
        "reason about together.'"
    )

    # Line chart of all pairs over ticks. Streamlit's line_chart wants
    # a dict-of-lists (column → values) and infers x-axis from index.
    st.line_chart(chart["magnitude_series"])

    summary = chart["pairs_summary"]
    if summary:
        st.markdown(
            f"**Decay summary over {chart['n_steps']} months** "
            f"(γ={chart['decoherence_rate']:.2f}/month; analytic "
            f"reference ≈ {chart['expected_decay_ratio']:.2f}× of "
            f"initial)"
        )
        for row in summary:
            initial = row["initial"]
            final = row["final"]
            decay_pct = row["decay_pct"]
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 1, 4])
                with cols[0]:
                    st.markdown(
                        f"`{row['pair_a']}` ↔ `{row['pair_b']}`"
                    )
                with cols[1]:
                    st.metric("|ρ| now", f"{initial:.2f}")
                with cols[2]:
                    st.metric(
                        f"|ρ| @ {chart['n_steps']}mo",
                        f"{final:.2f}",
                    )
                with cols[3]:
                    st.metric(
                        "Δ decay",
                        f"−{decay_pct:.0f}%",
                    )
                with cols[4]:
                    if row["rationale"]:
                        st.caption(row["rationale"])

    st.caption(
        "Interpretation: a strong, slowly-decaying coherence means "
        "you can still treat those two futures as 'linked' when "
        "planning. A coherence that has already collapsed by your "
        "decision horizon means the two are practically independent "
        "outcomes — preventive action against one no longer biases "
        "the other."
    )

    st.divider()


def _render_probability_heatmap(
    hypotheses: list[Any],
    horizon_label: str = "",
    height: int | None = None,
) -> None:
    """Quantum probability-mass heatmap — interactive v10 component.

    [OMY-V415 / M2 / Acceptance #59] Ported from the v10 marketing demo
    ``marketing/console/Omytea Console v10 — see both at once.html``.

    This used to be a static server-rendered SVG with zero interaction.
    It is now an **embedded HTML/JS component** (delegated to
    ``_heatmap_component.render_heatmap_camera_component``) that:

      • renders the same probability-mass grid — each row a future
        branch, each column a slice of the scoring horizon, cell
        intensity = probability mass — sharpening uniform → calibrated
        across the NOW → HORIZON axis;
      • adds hover-highlight + click-to-open cell popovers (cell number
        + plain-English reading);
      • adds a **camera-drives-the-math** loop: a hidden 80×45 canvas
        pixel-diffs video frames ~10 fps → motion centroid + intensity
        → the heatmap updates live and continuously, no submit click,
        with the camera preview side-by-side with the heatmap.

    The function signature is unchanged so existing call sites (idle
    output region + ``_render_result``) keep working: ``hypotheses`` is
    the server-side prediction's branch distribution, projected to JSON
    and fed into the component; an empty list renders the idle uniform
    grid inside the component itself.

    Camera honesty: a live ``getUserMedia`` call is blocked inside the
    Streamlit component iframe (no ``allow="camera"``). The uploaded-
    video pixel-diff path works in any iframe and is the always-on live
    driver; the component surfaces an honest note if the user clicks the
    camera button and the browser blocks it. See ``_heatmap_component``
    module docstring for the full rationale.
    """
    payload = branches_to_payload(hypotheses or [])
    # Output-only: the default heatmap carries no camera/video input —
    # that modality lives in the composer's "Live video" toggle, so the
    # output region holds output only.
    _hkw = {} if height is None else {"height": height}
    render_heatmap_camera_component(
        payload, horizon_label=horizon_label, show_camera=False, **_hkw,
    )


def _render_result(
    result: ConsoleResult,
    user_input: dict[str, Any],
    scenario: str,
    user_id: str,
    program: Any,
    prediction_id: str | None = None,
) -> None:
    """Render the prediction result + persist snapshot.

    v4.16 P2: prediction_id is supplied by the caller now (storage
    happens in render_new_prediction so the drill-down loop has a
    stable id to key the cache on). When prediction_id is None we
    fall back to inline-persistence (legacy path for tests that
    construct results directly)."""
    # Iter #14 (design-self-explains): "RESOLVED PREDICTION" eyebrow
    # tag deleted — same class as iter #3's "PREDICTION SPACE" delete.
    # The heatmap rendering below ALREADY conveys "this is a resolved
    # prediction" (real branch distribution vs. the idle uniform
    # grid). An all-caps tag above it added nothing.

    if prediction_id is None:
        rec = storage.PredictionRecord(
            prediction_id=storage.new_prediction_id(),
            user_id=user_id,
            scenario=scenario,
            created_at=storage.now_unix(),
            user_input=user_input,
            belief_program=program.raw,
            wavefunction_snapshot={
                "hypotheses": [h.to_dict() for h in result.hypotheses],
            },
            joint_offdiag={
                "entries": [o.to_dict() for o in result.joint_offdiag],
            },
            is_owner_bias_flagged=bool(
                user_input.get("is_owner_bias_flagged", False)
            ),
        )
        storage.save_prediction(rec)
        prediction_id = rec.prediction_id

    # Iter #52 (founder: result page, same clear logic) — LEAD WITH THE
    # ANSWER. The raw prediction-ID (a UUID) used to be the very first
    # line — techy noise before the takeaway for a non-technical reader.
    # The plain "Most likely: …" takeaway now leads; the ID is demoted
    # below it (and is also one click away via the "Copy ID" CTA).

    # Iter #51 (revised) — PLAIN result lead-in for a NON-technical user.
    # Founder: most users can't parse ρ / "correlated links" /
    # "decoherence" — show the engine's VALUE in human words, not its
    # math. Default = a one-line takeaway anyone gets (most-likely path +
    # what it hinges on) + a plain note that real per-situation analysis
    # happened. The genuine technical depth (ρ diagonal, off-diagonal
    # correlations, decoherence) lives only in the optional, skippable
    # "How we worked this out" — invisible to a normal user, there for
    # the curious. Master Plan §9/§15 Rule#6 reconciled with design-for-
    # the-non-expert: the engine shows up as plain, specific value.
    _eng_n = len(result.hypotheses)
    _eng_m = len(result.joint_offdiag)
    _ranked = sorted(
        result.hypotheses,
        key=lambda _x: float(getattr(_x, "probability", 0.0) or 0.0),
        reverse=True,
    )
    if _ranked:
        _top = _ranked[0]
        _top_lab = _humanize_id(getattr(_top, "label", "") or "this path")
        _top_p = float(getattr(_top, "probability", 0.0) or 0.0)
        _top_p = 0.0 if _top_p < 0 else (1.0 if _top_p > 1 else _top_p)
        _top_drv = getattr(_top, "key_uncertainty_driver", "") or ""
        _hinge = (
            T("result.lead.hinges").format(driver=_humanize_id(_top_drv))
            if _top_drv else ""
        )
        _mapped = T("result.lead.mapped").format(n=_eng_n)
        # Iter #53 (founder: result page = same clear logic) — the answer
        # now reads as a BOUNDED hero card so a non-expert instantly sees
        # "this is my result" (the 界限分明 / distinct-boundary principle
        # applied to output, same as the cold-start composer pane). Quiet
        # uppercase eyebrow ("Most likely"), big path + odds, plain sub.
        _eyebrow = T("result.lead.most_likely").rstrip(":：").strip()
        st.markdown(
            "<div style='margin:2px 0 14px;padding:15px 18px 14px;"
            "background:linear-gradient(135deg,rgba(107,143,255,0.10),"
            "rgba(180,126,255,0.055));border:1px solid "
            "rgba(139,124,240,0.30);border-radius:14px;'>"
            "<div style='font-size:10.5px;letter-spacing:0.16em;"
            "text-transform:uppercase;color:#8a8f98;margin-bottom:6px;'>"
            f"{_esc_html(_eyebrow)}</div>"
            "<div style='font-size:18px;color:#f2f4f8;font-weight:600;"
            "line-height:1.28;'>"
            f"{_esc_html(_top_lab)}"
            "<span style='color:#a99cff;font-weight:700;'> · "
            f"{_top_p*100:.0f}%</span></div>"
            "<div style='margin:8px 0 0;font-size:13px;color:#aab0ba;"
            "line-height:1.5;'>"
            f"{_esc_html((_hinge + ' ' + _mapped).strip())}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    # Iter #53 — the raw prediction-ID UUID used to print HERE, right
    # under the answer ("`<uuid>` — your prediction ID"). For a
    # non-technical reader a 36-char hex string is pure intimidating
    # noise next to their answer. The ID is functional (you need it to
    # score later) so it is NOT deleted — it now lives in the labeled
    # "save / come back later" zone below the chart, with a plain-language
    # caption explaining what it's for.
    with st.expander(T("result.engine.expander"), expanded=False):
        st.caption(T("result.engine.belief_state"))
        for _h in _ranked:
            _p = float(getattr(_h, "probability", 0.0) or 0.0)
            _p = 0.0 if _p < 0 else (1.0 if _p > 1 else _p)
            _lab = _humanize_id(getattr(_h, "label", "") or "future")
            st.markdown(
                "<div style='margin:4px 0;'>"
                "<div style='display:flex;justify-content:space-between;"
                "font-size:12.5px;color:#d0d6e0;'>"
                f"<span>{_esc_html(_lab)}</span>"
                f"<span style='color:#8b7cf0;font-weight:600;'>"
                f"{_p*100:.0f}%</span></div>"
                "<div style='height:5px;border-radius:3px;background:#1c1d22;"
                "margin-top:3px;'>"
                f"<div style='height:5px;border-radius:3px;"
                f"width:{_p*100:.1f}%;background:linear-gradient("
                "90deg,#6b8fff,#b47eff);'></div>"
                "</div></div>",
                unsafe_allow_html=True,
            )
        st.caption(T("result.engine.compiled_note").format(n=_eng_n, m=_eng_m))
        st.caption(T("result.engine.tech_footnote"))

    # Iter #42 B1 — top-of-result CTA row. Founder round-4 audit:
    # "Add calendar / Copy ID / Score later" were buried at the
    # BOTTOM of the result page, below story + drill-down + technical
    # details + recommended evidence — so a user scoring later had
    # to scroll past everything to find the calendar download. The
    # 3 measurement-loop CTAs are surfaced HERE, right under the
    # prediction-ID caption, before the heatmap. The bottom .ics
    # block is slimmed to a reminder line only (no duplicate
    # download button). Build the .ics blob early so the top row
    # can offer it; we re-use the same blob for the bottom reminder
    # context line.
    _cta_horizon_str = str(user_input.get("time_horizon", "6 months"))
    _cta_horizon_months = _parse_time_horizon_to_steps(_cta_horizon_str)
    _cta_review_date = _dt_today_plus_months(_cta_horizon_months)
    _cta_review_human = _cta_review_date.strftime("%B %Y")
    _cta_ics_blob = _build_review_ics(
        prediction_id=prediction_id,
        decision_label=str(user_input.get("decision_options", ""))[:80],
        review_date=_cta_review_date,
    )
    # Iter #43 — JSON snapshot download. Direct mitigation for the
    # ephemeral-storage finding (storage.DEFAULT_DB_PATH lives on
    # Streamlit Cloud's wipeable filesystem; user predictions can
    # vanish on any redeploy). With this button the user owns their
    # own durable copy. The PMF-loop "predict → wait 3 months →
    # score" is no longer at the mercy of the demo server's
    # lifespan — even if the DB wipes, the user can email me their
    # `.json` to restore. Snapshot fields match the schema in
    # `storage.PredictionRecord` so a future restore-from-upload
    # path can rebuild the record verbatim.
    import json as _json
    import time as _time
    _cta_snapshot = {
        "schema": "omytea-prediction-snapshot/v1",
        "exported_at_unix": _time.time(),
        "prediction_id": prediction_id,
        "user_id": user_id,
        "scenario": scenario,
        "user_input": user_input,
        "wavefunction_snapshot": {
            "hypotheses": [h.to_dict() for h in result.hypotheses],
        },
        "joint_offdiag": {
            "entries": [o.to_dict() for o in result.joint_offdiag],
        },
        "console_version": _brand.BRAND_VERSION,
    }
    _cta_snapshot_blob = _json.dumps(
        _cta_snapshot, indent=2, ensure_ascii=False, default=str,
    ).encode("utf-8")

    # Iter #53 (founder: result page = same clear logic) — the save /
    # revisit CTAs used to render HERE, jammed between the answer and the
    # chart, led by a raw UUID code block. That interrupted the
    # answer→chart read for a non-expert. They are wrapped in a closure
    # now and emitted BELOW the chart (see the _emit_save_zone() call
    # after the heatmap divider) under a plain "save this / come back
    # later" label — mirroring the cold-start logic: output/answer on
    # top, actions demoted. Restructured to 3 equal action buttons +
    # the prediction ID on its own clearly-labeled full-width line
    # (no longer a cryptic truncated hex column).
    def _emit_save_zone() -> None:
        st.markdown(
            "<div style='margin:4px 0 1px;font-size:13px;color:#c7ccd4;"
            "font-weight:600;'>"
            f"{_esc_html(T('result.save.zone_title'))}</div>"
            "<div style='margin:0 0 11px;font-size:12px;color:#8a8f98;"
            "line-height:1.45;'>"
            f"{_esc_html(T('result.save.zone_sub'))}</div>",
            unsafe_allow_html=True,
        )
        _c_ics, _c_snap, _c_score = st.columns(3)
        with _c_ics:
            st.download_button(
                label=T("result.cta.add_calendar"),
                data=_cta_ics_blob,
                file_name=f"omytea-review-{prediction_id[:8]}.ics",
                mime="text/calendar",
                key=f"_top_ics_dl_{prediction_id}",
                use_container_width=True,
                help=T("result.cta.add_calendar.hint"),
            )
        with _c_snap:
            st.download_button(
                label=T("result.cta.save_snapshot"),
                data=_cta_snapshot_blob,
                file_name=f"omytea-prediction-{prediction_id[:8]}.json",
                mime="application/json",
                key=f"_top_snapshot_dl_{prediction_id}",
                use_container_width=True,
                help=T("result.cta.save_snapshot.hint"),
            )
        with _c_score:
            if st.button(
                T("result.cta.score_later"),
                key=f"_top_score_later_{prediction_id}",
                use_container_width=True,
                help=T("result.cta.score_later.hint"),
            ):
                # Set ?score=<id> URL param + rerun → main()'s
                # _check_score_deeplink() catches it and routes to
                # Measurement Update with this prediction pre-loaded.
                try:
                    st.query_params["score"] = prediction_id
                except Exception:
                    pass
                st.rerun()
        # The prediction ID on its own labeled line — full width (no
        # truncation), plain-language caption, st.code keeps the
        # hover-to-copy affordance.
        st.caption(T("result.save.id_label"))
        st.code(prediction_id, language=None)

    # v4.16 P1+P4: partition by branch_type for visually distinct anchor
    # display + offer Story (default) vs Comparison-table view.
    wishful = [h for h in result.hypotheses if h.branch_type == "wishful"]
    worst = [h for h in result.hypotheses if h.branch_type == "worst"]
    realistic = [h for h in result.hypotheses
                 if h.branch_type not in ("wishful", "worst")]

    # Probability heatmap visualization — restored from the v10 marketing
    # demo. SVG-only (no Plotly dependency), drawn inline so the bars
    # match the dark canvas + lavender accent of the v10 palette.
    _render_probability_heatmap(
        wishful + realistic + worst,
        horizon_label=str(user_input.get("time_horizon", "") or ""),
    )
    # Iter #53 — save / revisit actions live here now, right under the
    # chart: answer (hero card) → chart (visual proof) → "what you can do
    # with this". Still high on the page = discoverable, not buried below
    # story / drill-down / technical details.
    _emit_save_zone()
    st.divider()

    # Iter #14: view-mode radio's help text was 4 sentences explaining
    # each of the 4 view options — exactly the "use text to teach the
    # affordance instead of letting the affordance teach itself" rule.
    # The labels (Story / Comparison table / Timeline / Continuous)
    # already name what each is; users discover by clicking.
    # Iter #50 — every-button-works applied to locale-state: these 4 view
    # options were hardcoded English, so ZH/ES/FR users saw English labels
    # mid-result while the rest of the page was translated. Localize the
    # labels but branch off a STABLE key, never the localized string (a
    # locale switch must not break the dispatch). "(default)" dropped — the
    # radio already pre-selects index 0, so the suffix was redundant noise.
    _view_keys = ("story", "comparison", "timeline", "continuous")
    _view_labels = [
        T("result.view.story"),
        T("result.view.comparison"),
        T("result.view.timeline"),
        T("result.view.continuous"),
    ]
    _view_choice = st.radio(
        "View",
        options=_view_labels,
        horizontal=True,
        label_visibility="collapsed",
    )
    try:
        _view_key = _view_keys[_view_labels.index(_view_choice)]
    except ValueError:
        _view_key = "story"

    if _view_key == "comparison":
        _render_comparison_table(result)
    elif _view_key == "timeline":
        _render_decision_timeline(result, user_input)
    elif _view_key == "continuous":
        _render_continuous_distribution(result, user_input)
    else:
        # Iter #22 P1.4 Phase 2: thread recommended_evidence through so
        # each story card's "Why this probability?" expander can render
        # the per-branch top-driver list (filtered by target_branch).
        _render_story_view(
            wishful,
            realistic,
            worst,
            result.decision_options,
            recommended_evidence=list(result.recommended_evidence),
        )

    # v4.17 P1 — "Time-honored lens".
    # OMY-V415 / M2 / Acceptance #60 — requirement D: when the 玄学 lens
    # is ON, the 玄学 output lives in the OUTPUT REGION via the view
    # toggle at the top — it covers the quantum module there. So this
    # in-result surface no longer renders the full lens inline when the
    # lens is on (that would double-render it); it points to the toggle
    # instead. When the lens is OFF it stays a single subtle invite
    # chip — never imposing on visitors who don't want it.
    lens_on = bool(st.session_state.get("_xuanxue_lens_on", False))
    st.markdown(
        "<div style='margin:24px 0 -8px;text-align:center;'>"
        f"<span style='color:#8a8f98;font-size:11.5px;"
        f"letter-spacing:0.18em;text-transform:uppercase;'>"
        f"{T('trad.lens.invite_chip')}</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    if lens_on:
        # The lens is on — the 玄学 Nye Clock view is reachable in the
        # output region via the view toggle at its top. Don't render it
        # twice.
        st.caption(T("trad.lens.in_output_note"))
    else:
        # Lens off — keep the collapsed discovery expander (the "彩蛋").
        with st.expander(T("trad.lens.expander_label"), expanded=False):
            _render_traditional_lens(
                list(result.hypotheses),
                key_prefix=f"_trad_lens_{prediction_id or 'inline'}",
            )

    # v4.16 P2: drill-down loop. Wrapped in an expander so it doesn't
    # dominate the page; once opened it persists across reruns via
    # session_state so the user can iterate without losing context.
    st.divider()
    _render_drilldown_section(result, user_input, scenario, prediction_id)

    # Iter 18 P1.3 — quantum machinery (joint off-diagonal + Lindblad
    # coherence decay) was rendering directly on the result page,
    # exposing ρ_ab / γ=0.05/month / "Lindblad decoherence channel" to
    # first-time users. That copy is a trust hit on the casual path —
    # research-demo signal, not a calibrated-journal signal. Both
    # sections are now folded into ONE default-closed expander so the
    # primary result-page stays story + branches + evidence + revisit;
    # users who want the math open the expander explicitly.
    if result.joint_offdiag:
        st.divider()
        with st.expander(
            # Iter #51 — these 4 strings were hardcoded English, so zh/es/fr
            # users opening this section (the joint off-diagonal + Lindblad
            # coherence machinery — the physics-engine view) saw English.
            # Localized via result.tech.* keys; the math/labels below stay
            # symbolic (ρ-free here, just branch ids + signed coherence).
            T("result.tech.expander"),
            expanded=False,
        ):
            st.caption(T("result.tech.caption"))

            st.subheader(T("result.tech.joint_subheader"))
            st.caption(T("result.tech.joint_caption"))
            for o in result.joint_offdiag:
                sign = "+" if o.coherence_strength > 0 else ""
                color = "green" if o.coherence_strength > 0 else "red"
                with st.container(border=True):
                    cols = st.columns([2, 1, 2, 3])
                    with cols[0]:
                        st.markdown(f"`{o.branch_a}`")
                    with cols[1]:
                        st.markdown(
                            f":{color}[{sign}{o.coherence_strength:.2f}]"
                        )
                    with cols[2]:
                        st.markdown(f"`{o.branch_b}`")
                    with cols[3]:
                        st.caption(o.rationale)

            # C1 — Coherence evolution over time (Lindblad open-system
            # decay). Stays inside the same expander.
            if result.used_omytea_substrate:
                st.divider()
                _render_coherence_evolution(result, user_input)

    # v4.16 P5: recommended evidence in ΔP semantics (percentage-point shift)
    if result.recommended_evidence:
        # Iter #52 — localized (was hardcoded English; bug-051/052 class).
        st.subheader(T("result.evidence.subheader"))
        st.caption(T("result.evidence.caption"))
        for e in normalize_evidence_list(result.recommended_evidence):
            with st.container(border=True):
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"**{e['evidence_label']}**")
                    if e.get("rationale"):
                        st.caption(e["rationale"])
                    if e.get("target_branch"):
                        st.caption(
                            T("result.evidence.most_affects").format(
                                branch=e["target_branch"]
                            )
                        )
                with cols[1]:
                    st.metric(
                        T("result.evidence.expected_dp"),
                        format_delta_p(e["expected_delta_p"]),
                    )

    st.divider()
    # Bug 2026-05-19 (first friend user hit this): the `rec` PredictionRecord
    # is only created inside the `if prediction_id is None:` branch above;
    # when the caller passes a non-None prediction_id (the v4.16 P2 path
    # that render_new_prediction takes), that local is unbound here. Use
    # the `prediction_id` parameter instead — it's guaranteed populated in
    # both branches (either passed in by caller, or reassigned to the
    # freshly-created record's id by the inline-persistence fallback
    # above). See tests/test_render_result_unbound_regression.py.
    # Iter #23 → Iter #42 B1 — the .ics download + Copy ID + Score
    # later CTAs are now at the TOP of the result (right under the
    # prediction-ID caption) so they're discoverable BEFORE the user
    # scrolls through story/drill-down/technical details. The bottom
    # of the page keeps a calm reminder line for context — no
    # duplicate download button, just the "when to come back"
    # anchor.
    st.caption(
        T("result.review_anchor").format(
            horizon=_cta_horizon_str,
            review_date=_cta_review_human,
        )
    )


# ============================================================
# Mode 2 — Measurement update
# ============================================================

def _render_prediction_organizer(
    pred: "storage.PredictionRecord", user_id: str,
) -> None:
    """Stage 4 — let the user file this prediction into their own
    history tree: pick a category (folder) and add / remove free-form
    labels. The app imposes no taxonomy; the user owns it.
    """
    try:
        categories = storage.list_categories(user_id)
        current_labels = storage.list_labels(pred.prediction_id)
    except Exception:  # noqa: BLE001 — never block the viewer on a DB hiccup
        categories, current_labels = [], []

    with st.expander(T("organizer.title"), expanded=False):
        # ---- category assignment ----
        cat_ids: list[str | None] = [None] + [c.category_id for c in categories]
        cat_name = {c.category_id: c.name for c in categories}
        try:
            cur_idx = cat_ids.index(pred.category_id)
        except ValueError:
            cur_idx = 0
        chosen = st.selectbox(
            T("organizer.category"),
            options=cat_ids,
            index=cur_idx,
            format_func=lambda cid: (
                T("organizer.uncategorized") if cid is None
                else cat_name.get(cid, cid)
            ),
            key=f"_org_cat_{pred.prediction_id}",
        )
        if chosen != pred.category_id:
            storage.assign_prediction_category(pred.prediction_id, chosen)
            st.rerun()
        if not categories:
            st.caption(T("organizer.no_categories"))

        # ---- labels ----
        st.markdown(f"**{T('organizer.labels')}**")
        if current_labels:
            lab_cols = st.columns(min(len(current_labels), 4))
            for i, lab in enumerate(current_labels):
                with lab_cols[i % len(lab_cols)]:
                    if st.button(
                        f"# {lab}  ✕",
                        key=f"_org_rmlab_{pred.prediction_id}_{lab}",
                        help=T("organizer.remove_label"),
                        use_container_width=True,
                    ):
                        storage.remove_label(pred.prediction_id, lab)
                        _invalidate_history_cache()
                        st.rerun()
        else:
            st.caption(T("organizer.no_labels"))
        new_label = st.text_input(
            T("organizer.add_label"),
            key=f"_org_addlab_{pred.prediction_id}",
            placeholder=T("organizer.add_label.ph"),
        )
        if st.button(
            T("organizer.add_label_btn"),
            key=f"_org_addlab_btn_{pred.prediction_id}",
        ):
            if new_label.strip():
                storage.add_label(pred.prediction_id, new_label.strip())
                _invalidate_history_cache()
                st.rerun()


def render_measurement_update(
    preloaded_prediction_id: str | None = None,
) -> None:
    """Open a past prediction → score how it actually turned out.

    Two entry paths:
      * ``preloaded_prediction_id`` set — a history-rail click opened
        this prediction directly; the user handle is the current
        session id, no manual entry.
      * ``preloaded_prediction_id`` None — the standalone "Measurement
        update" secondary surface; the user types their handle and
        picks from a list.
    """
    _render_back_bar()
    # Iter #15 (design-self-explains): the 38px center-aligned
    # marketing hero "Tell it what actually happened." + 3-line
    # explainer paragraph violated the same rule the workspace's
    # iter #3 fixed — telling the user what the page does with
    # text before the form below explains it via interaction. Now a
    # quiet left-aligned page title; the form's own field labels +
    # the interaction telegraph the rest.
    st.markdown(
        f"<div style='margin:8px 0 14px;'>"
        f"<h2 style='color:#f7f8f8;font-size:22px;font-weight:600;"
        f"letter-spacing:-0.012em;margin:0;'>"
        f"{T('measurement.hero.title')}</h2>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if preloaded_prediction_id:
        # Iter #41 cross-device deep-link fix (founder round-4 P0
        # #2): the previous version called session_user_id() and
        # then filtered by id, which BROKE the .ics-calendar-→-
        # different-device flow because anonymous handles are random
        # per-session `tester-xxxx`. Now resolves directly by id via
        # get_prediction_by_id with no user filter, so opening from
        # ANY browser/device with the .ics link works.
        pred = storage.get_prediction_by_id(preloaded_prediction_id)
        if pred is None:
            st.warning(T("measurement.not_found"))
            return
        # Use the prediction's stored user_id (the original predictor)
        # for the measurement record, not the current session — so the
        # measurement is correctly attributed to the original prediction
        # owner, not the cross-device session.
        user_id = pred.user_id
        st.caption(
            f"{T('measurement.opened_from_history')} · "
            f"`{pred.prediction_id[:8]}` · {pred.scenario}"
        )
    else:
        # Iter #41 (founder round-4 P0 #3): standalone path now
        # supports prediction_id lookup directly — the .ics calendar
        # invite gives users a UUID; they should be able to paste it
        # in here even if they don't remember their handle.
        with st.expander(
            T("measurement.lookup_by_id_label"), expanded=True,
        ):
            pasted_pid = st.text_input(
                T("measurement.pid_input_label"),
                placeholder=T("measurement.pid_input_placeholder"),
                key="_measurement_lookup_pid",
            )

        # Iter #46 — restore-from-snapshot upload. Pairs with the
        # iter 43 `💾 Save snapshot` (.json) download on the result
        # page so the full snapshot↔restore loop is closed. If the
        # demo's data ever gets wiped (Turso outage / account
        # deletion / accidental redeploy that misses [turso]
        # secrets), beta testers can drop their .json back in here
        # and continue scoring — their prediction lives in their
        # device's filesystem as the durable record. The schema
        # field on the JSON is checked so future schema changes
        # can warn the user instead of crashing.
        restored_from_snapshot = False
        with st.expander(
            T("measurement.restore_label"), expanded=False,
        ):
            st.caption(T("measurement.restore_hint"))
            uploaded = st.file_uploader(
                T("measurement.restore_upload_label"),
                type=["json"],
                accept_multiple_files=False,
                key="_measurement_restore_uploader",
            )
            if uploaded is not None:
                try:
                    import json as _restore_json
                    raw = uploaded.read()
                    blob = _restore_json.loads(raw)
                    if not isinstance(blob, dict):
                        st.error(T("measurement.restore_invalid"))
                    elif blob.get("schema", "").split("/")[0] != (
                        "omytea-prediction-snapshot"
                    ):
                        st.error(T("measurement.restore_schema_mismatch"))
                    elif not blob.get("prediction_id"):
                        st.error(T("measurement.restore_invalid"))
                    else:
                        restored_pid = str(blob["prediction_id"])
                        # If the prediction already exists in the DB
                        # (Turso still has it), just route to it. If
                        # not, rebuild + save the PredictionRecord
                        # from the JSON and route.
                        existing = storage.get_prediction_by_id(
                            restored_pid,
                        )
                        if existing is not None:
                            pred = existing
                        else:
                            try:
                                rec = storage.PredictionRecord(
                                    prediction_id=restored_pid,
                                    user_id=str(blob.get("user_id", "")),
                                    scenario=str(blob.get("scenario", "")),
                                    created_at=float(
                                        blob.get(
                                            "exported_at_unix",
                                            storage.now_unix(),
                                        )
                                    ),
                                    user_input=dict(
                                        blob.get("user_input", {})
                                    ),
                                    belief_program={},
                                    wavefunction_snapshot=dict(
                                        blob.get(
                                            "wavefunction_snapshot",
                                            {"hypotheses": []},
                                        )
                                    ),
                                    joint_offdiag=dict(
                                        blob.get(
                                            "joint_offdiag",
                                            {"entries": []},
                                        )
                                    ),
                                )
                                storage.save_prediction(rec)
                                pred = rec
                            except Exception as _e:  # noqa: BLE001
                                st.error(
                                    f"{T('measurement.restore_failed')}: "
                                    f"{type(_e).__name__}"
                                )
                                pred = None
                        if pred is not None:
                            user_id = pred.user_id
                            preloaded_prediction_id = pred.prediction_id
                            predictions = [pred]
                            restored_from_snapshot = True
                            st.success(
                                f"{T('measurement.restore_success')} · "
                                f"`{pred.prediction_id[:8]}` · "
                                f"{pred.scenario}"
                            )
                except Exception as _e:  # noqa: BLE001
                    st.error(
                        f"{T('measurement.restore_invalid')}: "
                        f"{type(_e).__name__}"
                    )

        if pasted_pid and pasted_pid.strip():
            pred = storage.get_prediction_by_id(pasted_pid.strip())
            if pred is None:
                st.warning(T("measurement.not_found_by_id"))
                return
            user_id = pred.user_id
            st.caption(
                f"{T('measurement.found_by_id')} · "
                f"`{pred.prediction_id[:8]}` · {pred.scenario}"
            )
            # Branch to the same single-prediction render path as
            # the deep-link by reassigning preloaded_prediction_id
            # and short-circuiting the handle-then-list logic.
            preloaded_prediction_id = pred.prediction_id
            predictions = [pred]
            # Fall through to render path (handled at bottom).
            user_id_resolved = True
        elif restored_from_snapshot:
            user_id_resolved = True
        else:
            user_id_resolved = False

        if not user_id_resolved:
            user_id = st.text_input(
                T("measurement.handle_label"),
            )
            if not user_id:
                return

            predictions = storage.list_user_predictions(user_id)
            if not predictions:
                st.warning(f"No predictions found for user `{user_id}`.")
                return

        pred_labels = [
            f"{i + 1}. [{p.scenario}] {p.prediction_id[:8]}… "
            f"({p.user_input.get('current_role', '<no role>')[:40]}…)"
            for i, p in enumerate(predictions)
        ]
        sel_idx = st.selectbox(
            "Select the prediction to update",
            options=range(len(predictions)),
            format_func=lambda i: pred_labels[i],
        )
        pred = predictions[sel_idx]

    # ---- Stage 4: organize this prediction (category + labels) ----
    _render_prediction_organizer(pred, user_id)

    st.divider()
    st.subheader("Original prediction branches")
    # Iter #42 — snake_case residue cleanup (founder round-4 audit
    # P2). The Measurement Update flow was rendering the raw
    # snake_case label keys (e.g. `accept_offer`) — that's a
    # dev-internal signal leaking onto a user-facing surface. The
    # `_humanize_id()` helper already exists for this exact case
    # (used everywhere on the result page since iter 30); the
    # measurement-update branch list + outcome sliders just
    # hadn't been threaded through it. Slider KEYS still use the
    # raw label (that's what the `actual_outcome` dict + storage
    # layer key off — never touch the storage contract).
    for h in pred.wavefunction_snapshot.get("hypotheses", []):
        human_label = _humanize_id(h["label"])
        st.markdown(
            f"- **{human_label}** — {h['probability'] * 100:.1f}%: "
            f"{h['narrative']}"
        )

    st.divider()
    st.subheader("What actually happened?")
    st.caption(
        "For each branch, indicate how much it matched reality. 1.0 = "
        "fully materialized, 0.0 = didn't happen, intermediate values "
        "for partial matches. The values get auto-normalized."
    )

    actual_outcome: dict[str, float] = {}
    for h in pred.wavefunction_snapshot.get("hypotheses", []):
        v = st.slider(
            _humanize_id(h["label"]),
            min_value=0.0, max_value=1.0, value=0.0, step=0.1,
            help=h.get("narrative", ""),
            # Iter #42 — keep the slider's session-state key
            # stable across humanize toggles (the raw label is
            # the storage contract; the visible label is
            # cosmetic).
            key=f"_outcome_slider_{pred.prediction_id}_{h['label']}",
        )
        actual_outcome[h["label"]] = v

    # Iter #42 B3 — PMF default-value de-bias. Founder round-4
    # audit: "NPS default 5 / Sean Ellis 'Somewhat disappointed' /
    # effort 'needed_reminder' are all pre-biased — a user who
    # doesn't read the labels and clicks submit submits the
    # anchor, polluting our PMF readout. Change all three to
    # require an explicit pick."
    #
    # NPS: st.slider requires a concrete value (no None), so we
    # use st.number_input with value=None (Streamlit ≥1.27 — our
    # 1.56 pin honors this) so the field reads as "empty" until
    # the user picks. The submit gate below rejects None.
    nps = st.number_input(
        "How likely would you recommend this tool to a friend? (0-10 NPS)",
        min_value=0,
        max_value=10,
        value=None,
        step=1,
        placeholder="—",
        help=(
            "Pick a number from 0 (not at all likely) to 10 (extremely "
            "likely). Leave blank if you'd rather not say."
        ),
    )

    # v4.16 playbook-adopt: Sean Ellis disappointment test.
    # Anthropic founder's playbook §4 (MVP), canonical PMF indicator.
    # >40% "very disappointed" across active users = meaningful PMF.
    # Iter #42 B3: `index=None` so no option pre-checked; submit
    # gate below rejects unselected.
    st.divider()
    st.markdown("**Sean Ellis disappointment test** (PMF indicator)")
    sean_ellis_label_map = {
        "very_disappointed": "Very disappointed",
        "somewhat_disappointed": "Somewhat disappointed",
        "not_disappointed": "Not disappointed",
    }
    sean_ellis_response = st.radio(
        "If you could no longer use this prediction tool, how would you feel?",
        options=list(sean_ellis_label_map.keys()),
        format_func=lambda k: sean_ellis_label_map[k],
        index=None,  # no default — force explicit pick (B3 de-bias)
        help=(
            "Standard PMF instrument. We tally the share of users who "
            "say 'very disappointed' — when that share crosses 40% "
            "across real (non-owner) users, that's a meaningful signal "
            "of product-market fit."
        ),
    )

    # v4.16 playbook-adopt: effort test (push → pull retention transition).
    # Iter #42 B3 + B4: index=None (no default) + horizon copy
    # binds to THIS prediction's time_horizon, not a hardcoded
    # "6 weeks" that doesn't match the composer's "3 months"
    # default.
    pred_horizon = str(pred.user_input.get("time_horizon", "")).strip()
    effort_horizon_phrase = pred_horizon or "the measurement window"
    st.markdown(
        f"**Effort test** (retention quality over {effort_horizon_phrase})"
    )
    effort_label_map = {
        "self_returned": (
            "I came back to it on my own initiative "
            "(opened it without being reminded)"
        ),
        "needed_reminder": (
            "I came back only when reminded "
            "(the operator nudged me)"
        ),
        "did_not_return": "I did not return to the tool",
    }
    effort_test_response = st.radio(
        f"Over the past {effort_horizon_phrase}, "
        f"did you self-return to the tool?",
        options=list(effort_label_map.keys()),
        format_func=lambda k: effort_label_map[k],
        index=None,  # no default — force explicit pick (B3 de-bias)
        help=(
            "Pre-PMF retention requires founder energy pushing users; "
            "post-PMF, the product 'starts doing that work on its "
            "own' (per Anthropic founder's playbook §4)."
        ),
    )

    st.divider()
    notes = st.text_area("Notes (optional)")

    if st.button("Submit measurement update"):
        # Iter #41 P0 #4 — slider validation. Founder round-4 audit:
        # "测量提交可以产生无效数据. 每个实际结果 slider 默认 0.0;
        # 用户如果不理解直接提交, actual_outcome 总和为 0,
        # compute_calibration_delta 会返回 brier=1.0、log_loss=inf.
        # 这会污染 H3/H4 数据."
        # Reject submission when ALL sliders are 0 — that's the
        # garbage-in case. The total-mass-normalization message
        # explains the contract.
        total_outcome = sum(
            float(v) for v in actual_outcome.values() if v is not None
        )
        if total_outcome <= 0.0:
            st.error(T("measurement.outcome_validation_error"))
            return

        # Iter #42 B3 — require explicit PMF picks. Defaults are
        # gone (B3 de-bias); if a user submits without picking, we
        # block rather than save a None that the storage layer
        # later coerces to "" + the PMF aggregates silently drop.
        # NPS is allowed blank (genuinely optional per founder) —
        # we save None and the storage column tolerates NULL.
        if sean_ellis_response is None:
            st.error(T("measurement.sean_ellis_required"))
            return
        if effort_test_response is None:
            st.error(T("measurement.effort_required"))
            return

        # Compute calibration delta
        from console import ConsoleHypothesis

        branches = [
            ConsoleHypothesis(
                label=h["label"],
                narrative=h.get("narrative", ""),
                probability=float(h["probability"]),
                key_uncertainty_driver=h.get("key_uncertainty_driver", ""),
                depends_on_decision=h.get("depends_on_decision"),
            )
            for h in pred.wavefunction_snapshot.get("hypotheses", [])
        ]
        cal = compute_calibration_delta(branches, actual_outcome)

        upd = storage.MeasurementUpdate(
            update_id=storage.new_update_id(),
            prediction_id=pred.prediction_id,
            user_id=user_id,
            observed_at=storage.now_unix(),
            actual_outcome=actual_outcome,
            calibration_delta=cal,
            # B3: nps may be None (genuinely optional); the storage
            # column is INTEGER NULL so None is the correct value.
            user_satisfaction=(int(nps) if nps is not None else None),
            user_notes=notes,
            sean_ellis_response=sean_ellis_response,
            effort_test_response=effort_test_response,
        )
        storage.save_measurement(upd)

        st.success("Measurement saved.")
        st.json(cal)


# ============================================================
# Mode 3 — Calibration history
# ============================================================

def render_calibration_history() -> None:
    """Show aggregate calibration metrics with owner-bias breakdown."""
    _render_back_bar()
    # Iter #15: quiet left-aligned page title; the chart + metric
    # pills below self-explain the calibration view.
    st.markdown(
        f"<div style='margin:8px 0 14px;'>"
        f"<h2 style='color:#f7f8f8;font-size:22px;font-weight:600;"
        f"letter-spacing:-0.012em;margin:0;'>"
        f"{T('calibration.hero.title')}</h2>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Iter #42 — calibration-history default-handle fix (founder
    # round-4 audit P1: "empty default handle is confusing").
    # Previously the input defaulted to "" and an empty handle
    # was treated as "show GLOBAL stats". A user landing on this
    # page expected to see THEIR calibration record, not a
    # mystery aggregate across every demo visitor. The default
    # now prefills `session_user_id()` (the same handle that
    # composer uses) so the user sees their own data
    # immediately; clearing the field reveals the global stats
    # (with an explicit "across all demo users" caption so the
    # mode shift is visible).
    _default_handle = session_user_id()
    if "_calibration_handle_seeded" not in st.session_state:
        st.session_state["_calibration_handle"] = _default_handle
        st.session_state["_calibration_handle_seeded"] = True
    user_id = st.text_input(
        "User handle",
        key="_calibration_handle",
        help=(
            "Defaults to your session handle. Clear the field to "
            "see aggregate calibration across all demo users."
        ),
    )
    if not user_id:
        st.caption(
            "Showing aggregate calibration across **all** demo "
            "users (no handle entered)."
        )
    breakdown = storage.get_calibration_bias_breakdown(
        user_id=user_id if user_id else None,
    )

    aggregate = breakdown["all"]
    if not aggregate:
        # Iter #32 — empty state now describes the loop so users
        # who arrive here BEFORE having scored anything understand
        # why it's empty + what they can do (the founder thesis:
        # "校准记录可视化 / 当初哪些判断错了" only renders once they've
        # closed the loop at least once).
        st.info(
            "No measurement updates recorded yet. After a prediction's "
            "horizon date passes, score it on the **Measurement update** "
            "page to populate this view — that's where your calibration "
            "track record builds up."
        )
        return

    cols = st.columns(3)
    with cols[0]:
        st.metric("Measurements", f"{int(aggregate.get('n_measurements', 0))}")
    with cols[1]:
        if "mean_brier" in aggregate:
            st.metric("Mean Brier", f"{aggregate['mean_brier']:.4f}")
    with cols[2]:
        if "mean_log_loss" in aggregate:
            st.metric("Mean log-loss", f"{aggregate['mean_log_loss']:.4f}")

    st.caption(
        "Brier score reference: 0 = perfect calibration; 1 = perfectly "
        "wrong (uniform-prior baseline ≈ 0.5 for 5-way categorical)."
    )

    st.divider()
    st.subheader("Owner-bias breakdown")
    st.caption(
        "Some predictions are flagged as project-owner self-tests. The "
        "founder explicitly noted that owner data points may carry "
        "bias (NPS/utility scored higher than a neutral user would). "
        "This breakdown shows the same metrics computed with and "
        "without owner-flagged measurements."
    )

    excl = breakdown["exclude_owner"]
    own = breakdown["owner_only"]

    cmp_cols = st.columns(2)
    with cmp_cols[0]:
        st.markdown("**Real users only (owner excluded)**")
        if excl:
            st.metric("Measurements", f"{int(excl.get('n_measurements', 0))}")
            if "mean_brier" in excl:
                st.metric("Mean Brier", f"{excl['mean_brier']:.4f}")
            if "mean_log_loss" in excl:
                st.metric("Mean log-loss", f"{excl['mean_log_loss']:.4f}")
        else:
            st.info("No non-owner measurements yet.")
    with cmp_cols[1]:
        st.markdown("**Owner self-tests only**")
        if own:
            st.metric("Measurements", f"{int(own.get('n_measurements', 0))}")
            if "mean_brier" in own:
                st.metric("Mean Brier", f"{own['mean_brier']:.4f}")
            if "mean_log_loss" in own:
                st.metric("Mean log-loss", f"{own['mean_log_loss']:.4f}")
        else:
            st.info("No owner-flagged measurements yet.")

    # Highlight the delta when both sides have data.
    if excl and own and "mean_brier" in excl and "mean_brier" in own:
        delta = own["mean_brier"] - excl["mean_brier"]
        sign = "+" if delta >= 0 else ""
        st.caption(
            f"Δ (owner − non-owner) Brier = {sign}{delta:.4f}. "
            "Negative delta means owner self-test scored 'better calibrated' "
            "than the neutral sample — interpret as ownership bias."
        )

    # Iter #33 — measurement-loop part 3: Brier-over-time trend chart.
    # The founder thesis is that the user wants to see "am I getting
    # more calibrated over time?" — a single-glance answer. Brier
    # score is the canonical measure (0 = perfect, 1 = perfectly
    # wrong). A simple line chart ordered by observed_at, with one
    # point per measurement, surfaces the trend directly. Only renders
    # when there are at least 2 measurements (one point isn't a
    # trend). The diff cards below this chart provide the per-record
    # detail.
    trend_records = storage.list_recent_measurements_with_predictions(
        user_id=user_id if user_id else None,
        limit=100,
    )
    brier_points = [
        (rec["observed_at"], rec["brier"])
        for rec in trend_records
        if rec.get("brier") is not None
    ]
    if len(brier_points) >= 2:
        st.divider()
        st.subheader("Calibration trend")
        st.caption(
            "Brier score per measurement, oldest → newest. **Down "
            "and to the right** means you're getting more calibrated "
            "over time. 0 is perfect; 0.5 is uniform-prior baseline; "
            "1 is perfectly wrong."
        )
        # Sort oldest → newest so the chart reads left-to-right.
        import datetime as _dt
        brier_points.sort(key=lambda p: p[0])
        chart_data = {
            "Brier score": [pt[1] for pt in brier_points],
        }
        st.line_chart(chart_data, height=200)
        # Quick directional read — first 1/3 vs last 1/3 of points,
        # only when there are enough points to be honest about it.
        if len(brier_points) >= 6:
            third = len(brier_points) // 3
            early = sum(p[1] for p in brier_points[:third]) / third
            late = sum(p[1] for p in brier_points[-third:]) / third
            delta = late - early
            if delta < -0.02:
                trend_word = "improving"
            elif delta > 0.02:
                trend_word = "regressing"
            else:
                trend_word = "flat"
            st.caption(
                f"Direction over your scored history: **{trend_word}** "
                f"(early third Brier ≈ {early:.3f} → recent third ≈ "
                f"{late:.3f}; delta {delta:+.3f}, negative is good)."
            )

    # Iter #32 — measurement-loop part 2: per-prediction diff cards.
    # Founder thesis: the user's most-wanted view is "what I predicted
    # vs. what happened" per individual prediction, not just
    # aggregates. This section renders the most recent N measurements
    # as cards showing: decision excerpt → top predicted branch &
    # probability → which branch actually happened & the probability
    # the user gave it in advance → calibration metrics. The single
    # most decision-relevant number per card is "you gave the outcome
    # that actually happened X% in advance" — that's the calibration
    # the user is most curious about.
    st.divider()
    st.subheader("Per-prediction track record")
    st.caption(
        "Your most recent scored predictions. Each card shows the "
        "probability you assigned to the future that actually "
        "happened — the single number you most want to see."
    )
    records = storage.list_recent_measurements_with_predictions(
        user_id=user_id if user_id else None,
        limit=20,
    )
    if not records:
        st.info(
            "No per-prediction records yet. The aggregate above counts "
            "all measurements across users; individual records show up "
            "here only when you scored predictions under this user "
            "handle."
        )
    else:
        # Format helper for the "you gave the outcome X% in advance"
        # headline number. Honest fallback ("not scored against a
        # specific branch") when the measurement form didn't capture
        # which branch materialized.
        import datetime as _dt
        for rec in records:
            top_label = _humanize_id(rec["predicted_top_label"]) or "—"
            top_pct = f"{rec['predicted_top_prob'] * 100:.0f}%"
            actual = rec["actual_label"]
            actual_human = _humanize_id(actual) if actual else ""
            advance_pct = (
                f"{rec['prob_for_actual'] * 100:.0f}%"
                if rec["prob_for_actual"] > 0
                else "—"
            )
            try:
                pred_date = _dt.datetime.fromtimestamp(
                    rec["predicted_at"]
                ).strftime("%b %Y")
            except Exception:
                pred_date = ""
            try:
                obs_date = _dt.datetime.fromtimestamp(
                    rec["observed_at"]
                ).strftime("%b %Y")
            except Exception:
                obs_date = ""
            with st.container(border=True):
                # Decision excerpt as the card headline; falls back
                # to scenario name if no decision_options captured.
                heading = (
                    rec["decision_label"]
                    or f"({rec['scenario']} prediction)"
                )
                st.markdown(f"### {heading}")
                # Predicted-vs-actual line — the founder-asked
                # "what I got right / wrong" surface.
                if actual_human:
                    line = (
                        f"**Predicted most likely**: _{top_label}_ ({top_pct})  \n"
                        f"**Actually happened**: _{actual_human}_  \n"
                        f"**You gave it {advance_pct} in advance**"
                    )
                else:
                    # Older / softer measurements without an explicit
                    # branch — honest fallback rather than fabricating.
                    line = (
                        f"**Predicted most likely**: _{top_label}_ ({top_pct})  \n"
                        "_(this measurement didn't capture which branch "
                        "materialized — only aggregate calibration metrics "
                        "are recorded.)_"
                    )
                st.markdown(line)
                meta_bits: list[str] = []
                if pred_date:
                    meta_bits.append(f"predicted {pred_date}")
                if obs_date:
                    meta_bits.append(f"scored {obs_date}")
                if rec["brier"] is not None:
                    meta_bits.append(f"Brier {float(rec['brier']):.3f}")
                if rec["log_loss"] is not None:
                    meta_bits.append(
                        f"log-loss {float(rec['log_loss']):.3f}"
                    )
                if rec["user_notes"]:
                    meta_bits.append(
                        f"note: {str(rec['user_notes'])[:60]}"
                    )
                if meta_bits:
                    st.caption(" · ".join(meta_bits))


# ============================================================
# Main
# ============================================================

def render_pricing_and_preorder() -> None:
    """v4.16 P6 — pricing tier comparison + pre-order interest
    capture. Pre-revenue PMF research; no payment processor wired."""
    _render_back_bar()
    # Iter #15: quiet left-aligned page title; the 3 pricing tier
    # cards below tell their own story.
    st.markdown(
        f"<div style='margin:8px 0 14px;'>"
        f"<h2 style='color:#f7f8f8;font-size:22px;font-weight:600;"
        f"letter-spacing:-0.012em;margin:0;'>"
        f"{T('pricing.hero.title')}</h2>"
        f"</div>",
        unsafe_allow_html=True,
    )

    locale = st.session_state.get("user_locale", currency.DEFAULT_LOCALE)
    # Show the human-readable currency, never the raw locale code — a
    # bare "en_US" is a technical token a user should not see.
    _cur = currency.CURRENCY_BY_LOCALE.get(
        locale, currency.CURRENCY_BY_LOCALE[currency.DEFAULT_LOCALE]
    )
    if _cur.code == "USD":
        st.caption(
            "Prices shown in **US Dollars** — the canonical billing currency."
        )
    else:
        st.caption(
            f"Prices shown in **{_cur.name_en} ({_cur.code})** — an "
            f"approximate conversion; canonical billing is USD."
        )

    # --- Tier comparison cards ---
    st.subheader("Tier comparison")
    cols = st.columns(len(pricing.PRICING_TIERS))
    for idx, tier in enumerate(pricing.PRICING_TIERS):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"### {tier.display_name}")
                st.markdown(
                    f"**{pricing.format_tier_price(tier, locale=locale)}**"
                )
                st.caption(tier.one_line_pitch)
                if tier.bullet_features:
                    st.markdown("**Includes:**")
                    for feat in tier.bullet_features:
                        st.markdown(f"- {feat}")
                if tier.target_persona:
                    st.caption(f"*For:* {tier.target_persona}")
                if not tier.available_now:
                    st.warning("⏳ Not available for purchase yet")

    st.divider()

    # --- Pre-order interest capture ---
    st.subheader("Express pre-order interest")
    st.caption(
        "Tell us which tier interests you and how much you'd actually "
        "pay (USD). This is honest PMF research; we don't take payment "
        "or commit you to anything."
    )

    user_id = st.text_input(
        "Your handle (same one you used for predictions)",
        key="preorder_user_id",
    )
    tier_id = st.selectbox(
        "Which tier?",
        options=pricing.list_tier_ids(),
        format_func=lambda tid: pricing.get_tier(tid).display_name,
    )
    chosen_tier = pricing.get_tier(tier_id)

    # USD anchor selector + free-form override.
    anchor_choices = list(currency.PAY_WILLINGNESS_USD_ANCHORS) + [None]
    anchor = st.selectbox(
        "What would you pay (USD anchor)?",
        options=anchor_choices,
        format_func=lambda x: (
            "Custom (enter below)" if x is None
            else currency.format_price(x, locale=locale, approx=True)
        ),
    )
    custom_amount = 0.0
    if anchor is None:
        custom_amount = st.number_input(
            "Custom willing-to-pay (USD)",
            min_value=0.0, max_value=10000.0, value=0.0, step=1.0,
        )
    notes = st.text_area(
        "Notes (optional)",
        help=(
            "Why this number? What would make you pay more? What "
            "would make you walk away? Concrete the better."
        ),
    )

    if st.button("Submit pre-order interest", type="primary"):
        if not user_id.strip():
            st.error("Please provide your handle.")
            return
        willing = float(anchor) if anchor is not None else float(custom_amount)
        rec = storage.PreorderInterest(
            interest_id=storage.new_interest_id(),
            user_id=user_id.strip(),
            tier_id=tier_id,
            expressed_at=storage.now_unix(),
            willing_to_pay_usd=willing,
            locale=locale,
            notes=notes,
        )
        storage.save_preorder_interest(rec)
        st.success(
            f"Recorded: {currency.format_price(willing, locale)} "
            f"for {chosen_tier.display_name}. Thanks — this directly "
            f"feeds the v4.17 billing-integration prioritization."
        )

    st.divider()
    # --- Aggregate summary per tier ---
    st.subheader("Current pre-order signal")
    st.caption(
        "Aggregate willingness-to-pay across all submissions per tier. "
        "Helps the founder spot which tier has actual demand vs which "
        "is theoretical."
    )
    for tier in pricing.PRICING_TIERS:
        summary = storage.preorder_interest_summary(tier.tier_id)
        if not summary:
            st.markdown(
                f"**{tier.display_name}** — no pre-orders captured yet."
            )
            continue
        n = int(summary["n"])
        mean = summary["mean_usd"]
        median = summary["median_usd"]
        max_v = summary["max_usd"]
        st.markdown(
            f"**{tier.display_name}** — "
            f"{n} pre-order(s); mean "
            f"{currency.format_price(mean, locale)} · "
            f"median {currency.format_price(median, locale)} · "
            f"max {currency.format_price(max_v, locale)}."
        )


def render_video_query(embedded: bool = False) -> None:
    """Video Query: upload a video file, ask a question, get
    probabilistic predictions about the scene.

    Pipeline:
    1. User uploads mp4/mov/webm
    2. video_ingest samples N frames + runs perception (substrate's
       MotionFallbackDetector + IoUTracker)
    3. Sampled JPEG frames + tracked-entity summaries are sent to
       OllamaVisionBackend via compile_scene_query
    4. The resulting BeliefProgram is converted to the same
       ConsoleResult the New-prediction mode uses, so all
       existing visualization paths (story view / comparison
       table / decision timeline / continuous distribution /
       coherence decay / evidence ΔP) just work.

    ``embedded`` — when True, the standalone hero is suppressed so the
    flow can be hosted inside the unified composer's "+" attach panel.
    Master plan §9 first-cut consumer surface for the video path.
    """
    if not embedded:
        # Iter #16: quiet page title; the upload affordance below
        # tells the user what to do.
        st.markdown(
            f"<div style='margin:8px 0 14px;'>"
            f"<h2 style='color:#f7f8f8;font-size:22px;font-weight:600;"
            f"letter-spacing:-0.012em;margin:0;'>"
            f"{T('video.hero.title')}</h2>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Silently probe the vision backend. If it's not ready, the
    # honest-fallback in compile_scene_query handles the timeout +
    # surfaces a clean banner in the result render. No developer-style
    # "⚠ Ollama vision backend not ready..." block here.
    try:
        from llm_backends import OllamaVisionBackend
        _vb_available = OllamaVisionBackend().is_available()
    except Exception:
        _vb_available = False

    uploaded = st.file_uploader(
        "Video file",
        type=["mp4", "mov", "webm", "avi", "mkv"],
        accept_multiple_files=False,
        help=(
            "Smaller files = faster processing. Recommended: <30 "
            "seconds, <50 MB. The first run may be slow as the "
            "vision model warms up."
        ),
    )

    user_query = st.text_area(
        "Your question about the scene",
        value="What might happen next? What are the most likely outcomes?",
        height=80,
        help=(
            "Ask anything about the future of the scene. Examples: "
            "'If the person on the left keeps walking, where will "
            "they be in 30 seconds?'  /  'What's the most likely "
            "next action?'  /  'What could go wrong here?'"
        ),
    )

    user_id = st.text_input(
        "Your handle (for measurement-update tracking)",
        help=(
            "Any string. Used to look up the prediction later via "
            "the Measurement update tab. No PII, no registration."
        ),
    )

    n_sample_frames = st.slider(
        "Number of sampled keyframes",
        min_value=2, max_value=12, value=3,
        help=(
            "More frames = better entity tracking but slower "
            "vision-LLM call. 3 is a fast default for CPU-only "
            "inference. Bump to 5-8 if your machine has a GPU."
        ),
    )

    submit = st.button("🚀 Analyze video", type="primary")

    if not submit:
        return

    if uploaded is None:
        st.error("Please upload a video file first.")
        return
    if not user_query.strip():
        st.error("Please enter a question about the scene.")
        return
    if not user_id.strip():
        st.error("Please provide a handle (any string).")
        return

    # Step 1: ingest video → sampled frames + tracked entities
    with st.spinner(
        "Step 1/3 — Sampling frames + running substrate perception…"
    ):
        from video_ingest import ingest_video_file

        file_bytes = uploaded.read()
        ingest_result = ingest_video_file(
            file_bytes=file_bytes,
            n_sample_frames=n_sample_frames,
        )

    if not ingest_result.available:
        st.error(
            f"Video ingestion failed: {ingest_result.reason}\n\n"
            f"If this says 'opencv-python or numpy not installed', "
            f"run: `pip install opencv-python-headless`. If it says "
            f"'mock mode enabled', unset `OMYTEA_CONSOLE_MOCK` in "
            f"your shell."
        )
        return

    st.success(
        f"✓ Sampled {ingest_result.sampled_count} frames · "
        f"{len(ingest_result.tracked_entities)} entities tracked · "
        f"detector: `{ingest_result.detector_used}` · "
        f"video duration: {ingest_result.duration_seconds:.1f}s @ "
        f"{ingest_result.fps:.0f}fps"
    )

    # Show a thumbnail strip of sampled frames so the user sees what
    # the model is looking at. Each frame gets detection bounding
    # box + trajectory polyline overlays for entities tracked on
    # or before that frame.
    if ingest_result.sampled_frames:
        st.markdown("**Sampled keyframes with detection overlays**")
        from visualization import render_frame_with_overlays
        entity_dicts_for_overlay = [
            {
                "object_id": e.object_id,
                "label": e.label,
                "trajectory": list(e.trajectory),
                "confidence": e.confidence,
            }
            for e in ingest_result.tracked_entities
        ]
        cols = st.columns(min(len(ingest_result.sampled_frames), 6))
        for i, sf in enumerate(ingest_result.sampled_frames):
            overlay_bytes = render_frame_with_overlays(
                image_bytes=sf.image_bytes,
                frame_idx=sf.frame_idx,
                tracked_entities=entity_dicts_for_overlay,
                frame_width=sf.width,
                frame_height=sf.height,
            )
            with cols[i % len(cols)]:
                st.image(
                    overlay_bytes,
                    caption=(
                        f"t={sf.timestamp_seconds:.1f}s "
                        f"(frame {sf.frame_idx})"
                    ),
                    use_container_width=True,
                )

    # Entity summary table
    if ingest_result.tracked_entities:
        st.markdown("**Tracked entities (top by track-length × confidence)**")
        entity_rows = []
        for e in ingest_result.tracked_entities:
            entity_rows.append({
                "Entity ID": e.object_id,
                "Label": e.label,
                "First frame": e.first_frame_idx,
                "Last frame": e.last_frame_idx,
                "Trajectory length": len(e.trajectory),
                "Confidence": f"{e.confidence:.2f}",
            })
        st.dataframe(
            entity_rows, hide_index=True, use_container_width=True,
        )

    # Step 2: scene-compile via vision LLM
    with st.spinner(
        f"Step 2/3 — Asking local vision LLM to read the scene ({n_sample_frames} frames)…"
    ):
        from compiler import compile_scene_query

        entity_summaries = [
            {
                "object_id": e.object_id,
                "label": e.label,
                "trajectory": list(e.trajectory),
                "confidence": e.confidence,
            }
            for e in ingest_result.tracked_entities
        ]
        try:
            program = compile_scene_query(
                user_query=user_query.strip(),
                sampled_frame_jpegs=[
                    sf.image_bytes for sf in ingest_result.sampled_frames
                ],
                tracked_entities_summary=entity_summaries,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Scene compilation failed: {exc}")
            return

    # Step 3: convert to ConsoleResult + persist + render via existing UI
    with st.spinner("Step 3/3 — Building belief state + applying quantum operator…"):
        from console import belief_program_to_console
        result = belief_program_to_console(program)

    # Surface fallback warning if the vision LLM timed out / failed.
    fallback_reason = program.raw.get("_fallback_reason", "")
    if fallback_reason:
        st.warning(
            f"⚠ Vision LLM fallback engaged. {fallback_reason}\n\n"
            f"The branches below come from a deterministic stub and "
            f"are NOT grounded in the specific video content. The "
            f"entity-tracking + quantum-operator evolution still "
            f"uses the real per-frame detections."
        )
    else:
        st.success("✓ Scene analysis complete.")

    st.divider()

    # Persist as a prediction (so it shows up in Measurement update later)
    rec = storage.PredictionRecord(
        prediction_id=storage.new_prediction_id(),
        user_id=user_id.strip(),
        scenario="video_scene_query",
        created_at=storage.now_unix(),
        user_input={
            "user_query": user_query.strip(),
            "n_sample_frames": n_sample_frames,
            "video_duration_seconds": ingest_result.duration_seconds,
            "n_entities": len(ingest_result.tracked_entities),
            "detector": ingest_result.detector_used,
            "is_owner_bias_flagged": False,
        },
        belief_program=program.raw,
        wavefunction_snapshot={
            "hypotheses": [h.to_dict() for h in result.hypotheses],
        },
        joint_offdiag={
            "entries": [o.to_dict() for o in result.joint_offdiag],
        },
        is_owner_bias_flagged=False,
    )
    storage.save_prediction(rec)
    st.caption(
        f"Prediction ID (save this for later measurement-update): "
        f"`{rec.prediction_id}`"
    )

    st.divider()
    # Render the per-entity quantum-state evolution alongside the
    # scene-level branches. This is the operator-algebra-level
    # quantum operator on a tracked-entity JointWaveFunction,
    # distinct from the scene-level branch coherence shown below.
    if ingest_result.tracked_entities:
        _render_entity_quantum_evolution(
            entity_summaries=entity_summaries,
            ingest_result=ingest_result,
        )
    st.divider()
    # Reuse the existing result-rendering machinery from
    # _render_result, including story view / comparison / timeline /
    # continuous-distribution / coherence-decay / evidence ΔP.
    user_input_proxy = {
        "time_horizon": "6 months",  # placeholder; the C1 UI uses this
        "user_query": user_query.strip(),
    }
    _render_result(
        result, user_input_proxy, "video_scene_query",
        rec.user_id, program,
        prediction_id=rec.prediction_id,
    )


def _render_entity_quantum_evolution(
    entity_summaries: list[dict[str, Any]],
    ingest_result: Any,
) -> None:
    """Build per-entity hypothesis bundles → JointWaveFunction → run
    LindbladOperator → visualize the off-diagonal coherence decay
    between entity-trajectory futures.

    This is the operator-algebra-level quantum operator applied to
    the actual tracked entities from the video, separate from the
    BeliefProgram branches the vision LLM emits.
    """
    import video_state

    st.subheader("⚛ Entity-trajectory quantum evolution")
    st.caption(
        "For each tracked entity, the system synthesizes three "
        "future-position hypotheses (continue / accelerate / "
        "decelerate). These are combined into a JointWaveFunction "
        "across up to 3 entities, then evolved under a Lindblad "
        "open-system operator over a short horizon. The decaying "
        "off-diagonal magnitudes below show how correlations "
        "between entity-trajectory futures wash out into "
        "independent classical outcomes."
    )

    bundles = video_state.build_entity_hypothesis_bundles(
        entity_summaries, max_entities=3,
    )

    if not bundles:
        st.info("No trackable entities to evolve.")
        return

    # Bundle preview table
    bundle_rows = []
    for b in bundles:
        bundle_rows.append({
            "Entity": f"{b.entity_id} ({b.label})",
            "Last x (norm)": f"{b.last_observed_cx:.2f}",
            "Last y (norm)": f"{b.last_observed_cy:.2f}",
            "Velocity x": f"{b.velocity_x:+.3f}",
            "Velocity y": f"{b.velocity_y:+.3f}",
            "Continue prior": f"{b.hypothesis_weights[0]:.0%}",
            "Accelerate prior": f"{b.hypothesis_weights[1]:.0%}",
            "Decelerate prior": f"{b.hypothesis_weights[2]:.0%}",
        })
    st.dataframe(
        bundle_rows, hide_index=True, use_container_width=True,
    )

    jwf = video_state.build_joint_wavefunction(bundles)
    if jwf is None:
        st.info(
            "Joint evolution unavailable in this environment — the "
            "frame stream and entity tracking still ran above."
        )
        return

    n_joint = len(jwf.hypotheses)
    n_offdiag_pairs = len(jwf.off_diagonal_couplings) // 2

    cols = st.columns(3)
    with cols[0]:
        st.metric("Joint hypotheses", n_joint)
    with cols[1]:
        st.metric("Off-diagonal pairs", n_offdiag_pairs)
    with cols[2]:
        st.metric("Entities evolved", len(bundles))

    if n_offdiag_pairs == 0:
        st.info(
            "No off-diagonal coherences generated (need ≥2 entities "
            "with informative trajectories). Skipping evolution."
        )
        return

    horizon_steps = st.slider(
        "Evolution horizon (Lindblad ticks)",
        min_value=2, max_value=12, value=6,
        help=(
            "Each tick = one unit of decoherence time. More ticks "
            "show fuller decay; fewer ticks = faster compute."
        ),
    )
    decoherence_rate = st.slider(
        "Decoherence rate γ (per tick)",
        min_value=0.02, max_value=0.30, value=0.08, step=0.02,
        help=(
            "Higher γ = faster coherence collapse. Lower γ = "
            "futures stay correlated longer."
        ),
    )

    evo = video_state.evolve_entity_joint(
        jwf,
        time_horizon_steps=horizon_steps,
        decoherence_rate=decoherence_rate,
    )

    if evo.get("skipped"):
        st.error(
            f"Evolution skipped: {evo.get('reason', 'unknown')}"
        )
        return

    # Per-pair magnitude over time → line chart
    snapshots = evo["snapshots"]
    if not snapshots:
        st.info("No evolution snapshots to display.")
        return

    # Build series: one line per off-diagonal pair (deduped by sorted i,j)
    seen_pairs: set[tuple[int, int]] = set()
    pair_series: dict[str, list[float]] = {}
    for snap in snapshots:
        for entry in snap["entries"]:
            i, j = entry["row"], entry["col"]
            key = (min(i, j), max(i, j))
            if key not in seen_pairs:
                # Find or initialize this pair's series across all
                # snapshots seen so far + this one
                seen_pairs.add(key)
                pair_series[f"(j{key[0]}, j{key[1]})"] = []

    # Now fill series consistently across all snapshots
    for snap in snapshots:
        pair_mags: dict[tuple[int, int], float] = {}
        for entry in snap["entries"]:
            i, j = entry["row"], entry["col"]
            key = (min(i, j), max(i, j))
            pair_mags[key] = max(
                pair_mags.get(key, 0.0), entry["magnitude"]
            )
        for key in seen_pairs:
            label = f"(j{key[0]}, j{key[1]})"
            pair_series[label].append(pair_mags.get(key, 0.0))

    st.line_chart(pair_series)
    st.caption(
        f"Off-diagonal magnitude |⟨joint_i | ρ | joint_j⟩| over "
        f"{horizon_steps} Lindblad ticks at γ={decoherence_rate:.2f}. "
        f"Each line = one joint-hypothesis pair. Lines converging to "
        f"zero = those two correlated futures have lost their "
        f"coherence and are now effectively independent classical "
        f"outcomes."
    )


# ============================================================
# Mode 6 — Live webcam (Tier 2)
# ============================================================


def render_live_webcam(embedded: bool = False) -> None:
    """Live webcam streaming with continuous quantum-state evolution.

    Pipeline:
    1. streamlit-webrtc opens a local WebRTC peer in the browser →
       camera frames stream into a callback running on a background
       thread (managed by aiortc).
    2. Each frame goes through ``WebcamSession.on_frame`` →
       substrate detector → IoUTracker → rolling trajectory dict.
    3. Every ``rebuild_every_n_frames`` frames, the joint
       wavefunction is rebuilt and evolved under the Lindblad
       operator. The snapshot of the joint state is cached in the
       session so the Streamlit main thread can read it without
       racing.
    4. A "Capture for prediction" button freezes the latest snapshot
       and asks the vision LLM about the current scene, returning
       a full ConsoleResult — same rendering as the video path.

    ``embedded`` — when True, the standalone hero is suppressed so the
    flow can be hosted inside the unified composer's live-video toggle.
    Master plan §9 World Console direction — direct live perception
    rather than file upload. §2.9 negative scope — no biometric ID,
    no demographic features, no multi-camera fusion (single stream
    only).
    """
    if not embedded:
        # Iter #17: last remaining marketing-hero — webcam page.
        # Same quiet h2 pattern; subtitle dropped.
        st.markdown(
            f"<div style='margin:8px 0 14px;'>"
            f"<h2 style='color:#f7f8f8;font-size:22px;font-weight:600;"
            f"letter-spacing:-0.012em;margin:0;'>"
            f"{T('webcam.title')}</h2>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Probe streamlit-webrtc availability up front. We deliberately do
    # NOT surface raw substrate-import errors to the user — they look
    # like crash traces and confuse non-technical testers. Instead the
    # render path either (a) shows the camera with full substrate
    # processing if available, or (b) shows the camera with a clean
    # single-line "Frames-only mode" note if substrate perception
    # isn't reachable (e.g., on the slim PyPI substrate that lacks
    # omytea.perception). No traceback, no "unset OMYTEA_CONSOLE_MOCK"
    # technobabble.
    import webcam_stream
    webrtc_mod, webrtc_err = webcam_stream._try_streamlit_webrtc()

    if webrtc_mod is None:
        # Browser-side webrtc package itself missing — this only happens
        # for local installs that opted out of streamlit-webrtc. Show a
        # short, friendly explanation, not the raw pip command.
        st.info(
            "The live-webcam stream stack isn't installed in this "
            "environment. The Video query tab (above in the sidebar) "
            "accepts uploaded video files and runs the same perception + "
            "quantum pipeline."
        )
        return

    # Check substrate-perception availability quietly. If unavailable,
    # the rolling-window quantum-rebuild stage will skip — but the
    # camera + frame counter still works, which is the visible
    # showpiece. We only surface this in a tiny gray caption far below.
    sub_types, _sub_err = webcam_stream._try_import_substrate()
    substrate_full = sub_types is not None

    # Session-state object — persists across reruns and is the same
    # Python object the webrtc frame callback writes to.
    if "webcam_session" not in st.session_state:
        st.session_state.webcam_session = webcam_stream.WebcamSession()
    session: webcam_stream.WebcamSession = st.session_state.webcam_session

    # Tunable settings
    with st.expander("Tuning (advanced)", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            new_rebuild = st.slider(
                "Rebuild every N frames",
                min_value=2, max_value=30,
                value=session.rebuild_every_n_frames,
                help=(
                    "How often the joint wavefunction is rebuilt + "
                    "evolved. Smaller = more reactive, more CPU."
                ),
            )
            session.rebuild_every_n_frames = new_rebuild
        with col_b:
            new_max_traj = st.slider(
                "Rolling-window size",
                min_value=10, max_value=120,
                value=session.max_trajectory_len,
                help="Max trajectory points kept per entity.",
            )
            session.max_trajectory_len = new_max_traj
        with col_c:
            new_decoh = st.slider(
                "Decoherence rate γ",
                min_value=0.02, max_value=0.30,
                value=session.decoherence_rate, step=0.02,
            )
            session.decoherence_rate = new_decoh

    # WebRTC streamer
    from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

    rtc_config = RTCConfiguration({
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}],
    })

    def video_frame_callback(frame: Any) -> Any:
        """Background-thread callback. Converts av.VideoFrame → BGR
        ndarray and pushes into the WebcamSession. Returns the frame
        unchanged so the user still sees their video preview."""
        try:
            import numpy as np  # noqa: F401  # required by av's to_ndarray
            img = frame.to_ndarray(format="bgr24")
            h, w = img.shape[:2]
            session.on_frame(
                image_data=img, frame_width=w, frame_height=h,
                stream_id="streamlit_webrtc",
            )
        except Exception:
            # Honest-fail: never crash the WebRTC track loop —
            # the user would lose the video preview.
            pass
        return frame

    ctx = webrtc_streamer(
        key="omytea-live-webcam",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=rtc_config,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    # Live state panel (re-reads the snapshot every rerun)
    st.subheader("Live state")
    refresh_col, reset_col = st.columns([1, 1])
    with refresh_col:
        if st.button("🔄 Refresh state", use_container_width=True):
            st.rerun()
    with reset_col:
        if st.button("🧹 Reset session", use_container_width=True):
            session.reset()
            st.rerun()

    snap = session.snapshot()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T("live.frames_processed"), snap.frames_processed)
    m2.metric(T("live.fps"), f"{snap.fps_observed:.1f}")
    m3.metric(T("live.entities"), snap.n_entities)
    m4.metric(T("live.joint_hyps"), snap.n_joint_hypotheses)

    if snap.entities_summary:
        st.markdown("**Tracked entities**")
        rows = [
            {
                "Entity": f"{e['object_id']} ({e['label']})",
                "Points": e["n_points"],
                "Last x": f"{e['last_cx']:.2f}",
                "Last y": f"{e['last_cy']:.2f}",
                "Vx": f"{e['velocity_x']:+.3f}",
                "Vy": f"{e['velocity_y']:+.3f}",
                "Confidence": f"{e['confidence']:.2f}",
            }
            for e in snap.entities_summary
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.caption(
            "No entities tracked yet. Start the webcam above and move "
            "something within the frame."
        )

    # Coherence-decay chart (last rebuild's snapshots)
    if snap.coherence_snapshots:
        # Build per-pair series like Mode 5 does, but from the live snapshot
        seen_pairs: set[tuple[int, int]] = set()
        pair_series: dict[str, list[float]] = {}
        for s_ in snap.coherence_snapshots:
            for entry in s_.get("entries", []):
                key = (min(entry["row"], entry["col"]),
                       max(entry["row"], entry["col"]))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    pair_series[f"(j{key[0]}, j{key[1]})"] = []
        for s_ in snap.coherence_snapshots:
            pair_mags: dict[tuple[int, int], float] = {}
            for entry in s_.get("entries", []):
                key = (min(entry["row"], entry["col"]),
                       max(entry["row"], entry["col"]))
                pair_mags[key] = max(
                    pair_mags.get(key, 0.0), entry["magnitude"]
                )
            for key in seen_pairs:
                lbl = f"(j{key[0]}, j{key[1]})"
                pair_series[lbl].append(pair_mags.get(key, 0.0))

        if pair_series:
            st.markdown("**Off-diagonal coherence decay (last rebuild)**")
            st.line_chart(pair_series)
            st.caption(
                f"Rebuilt at frame {snap.last_rebuild_at_frame}. "
                f"Each line = one joint-hypothesis pair magnitude over "
                f"Lindblad ticks. Lines decaying to 0 = correlated "
                f"futures losing coherence."
            )
    else:
        st.caption(
            "No joint quantum state yet. Coherence chart will appear "
            "after the first rebuild (every "
            f"{session.rebuild_every_n_frames} frames by default)."
        )

    # ----------------------------------------------------------------
    # Tier 3 — Capture & predict: freeze current state, ask vision LLM
    # ----------------------------------------------------------------

    st.divider()
    st.subheader("🎯 Ask vision LLM about the current scene")
    st.write(
        "Freeze the last few webcam frames + current entity tracks "
        "and run them through the same scene-understanding pipeline "
        "Mode 5 uses. Returns calibrated future branches you can "
        "score later in the Measurement update tab."
    )

    cap_query = st.text_area(
        "Your question about the current scene",
        value="What is most likely about to happen?",
        height=70,
        key="webcam_capture_query",
        help=(
            "Ask anything probabilistic about what's happening or "
            "about to happen. 'What's most likely?' works; "
            "'exactly when will X happen?' does not."
        ),
    )
    cap_user_id = st.text_input(
        "Your handle (for measurement-update tracking)",
        key="webcam_capture_user_id",
        help=(
            "Any string. Used to look up the prediction later via "
            "the Measurement update tab."
        ),
    )
    cap_n_frames = st.slider(
        "How many recent frames to include",
        min_value=1, max_value=session.frame_buffer_size, value=min(3, session.frame_buffer_size),
        help=(
            "More frames = more visual context for the vision LLM "
            "(better tracking) but slower inference. 2-3 is usually "
            "enough."
        ),
    )

    if st.button("📸 Capture & predict", type="primary", use_container_width=True):
        capture = session.snapshot_for_prediction(n_frames=cap_n_frames)
        if not capture["available"]:
            st.warning(
                f"Cannot capture yet: {capture['reason']}"
            )
        elif not cap_query.strip():
            st.error("Please type a question first.")
        elif not cap_user_id.strip():
            st.error("Please enter a handle (any string is fine).")
        else:
            with st.spinner("Asking vision LLM about the current scene…"):
                from compiler import compile_scene_query
                program = compile_scene_query(
                    user_query=cap_query.strip(),
                    sampled_frame_jpegs=capture["frames"],
                    tracked_entities_summary=capture["entities_summary"],
                )
            result = belief_program_to_console(program)

            # Persist via storage so the Measurement update tab can
            # surface this prediction later. Reuses the standard
            # PredictionRecord shape from Mode 5.
            prediction_id = storage.new_prediction_id()
            try:
                storage.save_prediction(storage.PredictionRecord(
                    prediction_id=prediction_id,
                    user_id=cap_user_id.strip(),
                    scenario="webcam_live_scene_query",
                    created_at=storage.now_unix(),
                    user_input={
                        "query": cap_query.strip(),
                        "n_frames_captured": len(capture["frames"]),
                        "n_entities_at_capture": len(
                            capture["entities_summary"]
                        ),
                    },
                    belief_program=program.raw,
                    wavefunction_snapshot={
                        "hypotheses": [
                            h.to_dict() for h in result.hypotheses
                        ],
                    },
                    joint_offdiag={
                        "entries": [
                            o.to_dict() for o in result.joint_offdiag
                        ],
                    },
                    is_owner_bias_flagged=False,
                ))
            except Exception as exc:
                # Storage failure is not fatal — the user still sees
                # the prediction on screen.
                st.warning(
                    f"Saved-prediction storage failed (prediction "
                    f"still shown below): {exc}"
                )

            # Reuse the Mode 5 / new-prediction result renderer so
            # the visualization stays consistent across modes.
            _render_result(
                result=result,
                user_input={
                    "query": cap_query.strip(),
                    "source": "live_webcam_capture",
                },
                scenario="webcam_live_scene_query",
                user_id=cap_user_id.strip(),
                program=program,
                prediction_id=prediction_id,
            )

    # Footer — accurate to the deployment context. Camera frames stream
    # to wherever the Streamlit server is running (local desktop in
    # self-hosted mode, cloud container in the hosted demo). In both
    # cases frames are processed in memory only and never persisted.
    # Show a one-line caption — no warnings, no traceback chrome.
    if substrate_full:
        st.caption(
            "Camera frames stream to the perception layer in memory "
            "only; nothing about the stream is persisted."
        )
    else:
        st.caption(
            "Frames-only preview — full perception + quantum stages "
            "are enabled when the host has the parent Omytea package "
            "available."
        )


def _scroll_focus_composer() -> None:
    """Iter #48 — scroll the composer's decision input into view +
    focus it, so the "New prediction" button always produces a
    visible, sensible result (land at the input, ready to type) in
    EVERY state — not a silent no-op on an already-fresh composer.

    Injects a tiny client-side script (same window.parent pattern as
    `_force_sidebar_open`). Targets the decision textarea by its
    Streamlit key-class (`st-key-input_decision_options`) with a
    generic stTextArea fallback. Re-fires on a short schedule because
    the element mounts a beat after the rerun. Worst case (element
    absent / cross-origin) is a silent no-op.
    """
    components.html(
        """
        <script>
        (function () {
          function focusComposer() {
            try {
              var d = window.parent && window.parent.document;
              if (!d) return;
              var el = d.querySelector(
                '[class*="st-key-input_decision_options"] textarea')
                || d.querySelector('[class*="st-key-input_decision_options"] input')
                || d.querySelector('[data-testid="stTextArea"] textarea');
              if (!el) return;
              el.scrollIntoView({behavior: 'smooth', block: 'center'});
              // Focus after the scroll settles so the caret lands
              // in-view (and, on desktop, the user can type at once).
              setTimeout(function () { try { el.focus(); } catch (e) {} }, 350);
            } catch (e) {}
          }
          setTimeout(focusComposer, 200);
          setTimeout(focusComposer, 650);
          setTimeout(focusComposer, 1300);
        })();
        </script>
        """,
        height=0,
    )


def _scroll_main_top() -> None:
    """Iter #49 — scroll the main content area to the top.

    Visible feedback for a nav control clicked while the user is
    already on its target page: a silent re-route to the same route
    looks dead (the "New prediction" / Settings-gear no-op class the
    founder flagged — every button must do something sensible + visible
    in every state). Same `window.parent` injection idiom as
    `_scroll_focus_composer`; worst case (no parent / cross-origin) is a
    silent no-op.
    """
    components.html(
        """
        <script>
        (function () {
          function toTop() {
            try {
              var d = window.parent && window.parent.document;
              if (!d) return;
              var el = d.querySelector('section[data-testid="stMain"]')
                || d.querySelector('[data-testid="stAppViewContainer"] section.main')
                || d.querySelector('section.main');
              if (el) el.scrollTo({top: 0, behavior: 'smooth'});
              try { window.parent.scrollTo({top: 0, behavior: 'smooth'}); } catch (e) {}
            } catch (e) {}
          }
          setTimeout(toTop, 60);
          setTimeout(toTop, 300);
        })();
        </script>
        """,
        height=0,
    )


def _force_sidebar_open() -> None:
    """Iter #42c real-real fix — viewport-aware sidebar nudge.

    **Why this exists at all**: Streamlit Community Cloud can paint
    the app with the sidebar collapsed on DESKTOP (a width race in
    the embedding iframe) even though ``initial_sidebar_state`` is
    "expanded". The sidebar IS the navigation — on a 1440px monitor
    it must not start hidden.

    **History — iter 41 "fix" was broken in production**: the iter
    41 attempt called `collapseBtn.click()` on mobile to retract the
    drawer. Live verification iter 43 reproduced the bug: at 610px
    viewport, after multiple `click()` and pointerdown/pointerup/
    click `dispatchEvent` sequences, React's collapse handler was
    NOT invoked — `aria-expanded` stayed "true" and the sidebar kept
    covering half the workspace. Synthetic clicks on Streamlit's
    React buttons are silently dropped (likely because Streamlit
    uses Pointer Events internally and the synthetic MouseEvent
    isn't trusted). Bug-039 reopened, bug-040 logged for the
    failed-fix.

    **The real fix (iter 42c)**: drive the sidebar state via the
    DOM attribute directly, NOT via clicking React's button.
    `aria-expanded` is the attribute that the @media CSS rule keys
    off (see lines ~198-217: `[aria-expanded="false"]` →
    `translateX(-100%)` slides off-screen; default rule + the
    sibling `[aria-expanded="true"]` show it). Setting the attribute
    bypasses React entirely; CSS does the visual update. Verified
    live: `setAttribute('aria-expanded', 'false')` → transform
    becomes `matrix(1,0,0,1,-300,0)` → workspace gets full viewport
    width within ~200ms.

    Behavior matrix:
      - **Desktop (>=768px)**: if sidebar `aria-expanded="false"`,
        set it to "true" + the @media rule doesn't apply so it
        naturally shows. Preserves the original desktop intent.
      - **Mobile (<768px)**: if sidebar `aria-expanded="true"`,
        set it to "false". The CSS @media rule then slides it off-
        screen with the smooth transition. User can still re-open
        via Streamlit's hamburger.

    Caveat: Streamlit might reset aria on its own next rerun. The
    re-fire schedule (150/700/1600/3000 ms) re-asserts the attribute
    if Streamlit overwrites it. Worst case (no parent / no sidebar /
    cross-origin): silent no-op.
    """
    components.html(
        """
        <script>
        (function () {
          function nudgeSb() {
            try {
              var d = window.parent && window.parent.document;
              if (!d) return;
              var sb = d.querySelector('section[data-testid="stSidebar"]');
              if (!sb) return;
              var aria = sb.getAttribute('aria-expanded');
              // Read viewport width from the OUTER document (not
              // our 0-height helper iframe).
              var w = (window.parent && window.parent.innerWidth) || 9999;
              if (w < 768) {
                // Mobile: set aria-expanded="false" directly.
                // The @media CSS rule does the visual collapse.
                // React-button .click() does NOT work here (iter
                // 41 bug); setAttribute on the DOM does.
                if (aria !== 'false') {
                  sb.setAttribute('aria-expanded', 'false');
                }
              } else {
                // Desktop: ensure expanded. Same DOM-attribute
                // strategy for symmetry — though the desktop
                // race condition is rarer, the same fix works.
                if (aria !== 'true') {
                  sb.setAttribute('aria-expanded', 'true');
                }
              }
            } catch (e) {}
          }
          setTimeout(nudgeSb, 150);
          setTimeout(nudgeSb, 700);
          setTimeout(nudgeSb, 1600);
          setTimeout(nudgeSb, 3000);
        })();
        </script>
        """,
        height=0,
    )


# Iter #40 phase-1 — `_check_score_deeplink` moved to
# `_measurement_loop.py`; imported at module top.


def _render_score_due_banner() -> None:
    """Iter #34 — active complement to the passive .ics calendar
    reminder (iter 23).

    When the user lands in the app for ANY reason, check if any of
    their past predictions have passed their horizon date without
    being scored. If so, surface a top banner inviting them to score
    the freshest one immediately. The button uses the same
    pre-loaded-prediction mechanism iter 31's deep-link uses, so it
    drops them into Measurement Update with the prediction ready.

    Honest scoping: only renders if the user actually has an
    overdue prediction; silent otherwise.
    """
    try:
        uid = session_user_id()
    except Exception:
        return
    if not uid:
        return
    try:
        overdue = storage.list_overdue_predictions(uid)
    except Exception:
        return
    if not overdue:
        return
    # Show only the freshest overdue (one banner is non-intrusive;
    # ten would be noise). User can drill into the full list via the
    # Calibration History page once they score the first one.
    top = overdue[0]
    decision = top.get("decision_label") or "(your prediction)"
    # How long ago did the user predict?
    import datetime as _dt
    try:
        days_ago = max(1, int((time.time() - top["predicted_at"]) / 86400))
    except Exception:
        days_ago = 0
    if days_ago >= 60:
        when = f"~{days_ago // 30} months ago"
    elif days_ago >= 14:
        when = f"~{days_ago // 7} weeks ago"
    else:
        when = f"{days_ago} days ago"
    cols = st.columns([5, 1])
    with cols[0]:
        st.info(
            f"📅 **Time to score**: {decision} — predicted {when}. "
            "How did this future actually play out?",
            icon=None,
        )
    with cols[1]:
        if st.button(
            "Score now →",
            key=f"_score_due_btn_{top['prediction_id']}",
            type="primary",
            use_container_width=True,
            help=(
                "Open the Measurement Update flow pre-loaded with this "
                "prediction. This is where the calibration loop closes."
            ),
        ):
            # Re-use iter 31's pre-load mechanism by routing via
            # query_params so the next rerun hits the deep-link branch
            # of main(). Cleanest path that doesn't require touching
            # the sidebar route plumbing.
            try:
                st.query_params["score"] = top["prediction_id"]
            except Exception:
                # Older Streamlit fallback — store in session_state and
                # let _check_score_deeplink read either source.
                st.session_state["_score_deeplink_pid"] = top["prediction_id"]
            st.rerun()


def main() -> None:
    _force_sidebar_open()

    # Iter #31 — measurement-loop deep-link check BEFORE the normal
    # route dispatch. If the user landed via the .ics calendar
    # reminder's deep-link (`?score=<prediction_id>`), drop them
    # straight into Measurement Update with that prediction
    # pre-loaded — the closed loop the founder identified as the
    # primary PMF lever.
    score_pid = _check_score_deeplink()
    if score_pid:
        render_measurement_update(preloaded_prediction_id=score_pid)
        return

    kind, payload = render_sidebar()

    # Iter #34 — active "Time to score" banner. Renders only when the
    # user has predictions past their horizon date without a
    # measurement, and only on the main workspace route (don't dilute
    # the banner by showing it on every page).
    if kind == ROUTE_WORKSPACE:
        _render_score_due_banner()

    if kind == ROUTE_HISTORY:
        # A history-rail click → open that prediction in the
        # measurement-update viewer, pre-loaded by id.
        render_measurement_update(preloaded_prediction_id=str(payload))
    elif kind == ROUTE_SECONDARY:
        # The 玄学 lens / video query / live webcam are NOT routed here —
        # they ARE the composer now. Only genuinely-standalone surfaces.
        if payload == "Measurement update":
            render_measurement_update()
        elif payload == "Calibration history":
            render_calibration_history()
        elif payload == "Pricing & pre-order":
            # Iter #42 B2 — guard: if the user deep-linked to
            # Pricing while beta-hide is active (e.g. an old
            # bookmark), bounce them back to workspace so they
            # don't see a pre-order page during PMF discovery.
            if not _show_research_features():
                st.session_state._route = (ROUTE_WORKSPACE, None)
                st.rerun()
            render_pricing_and_preorder()
        else:
            render_new_prediction()
    elif kind == ROUTE_SETTINGS:
        # The routed Settings surface — opened from the gear beside the
        # account chip (see docs/SETTINGS_REDESIGN.md).
        render_settings()
    else:
        # ROUTE_WORKSPACE — the default new-prediction composer.
        render_new_prediction()

    # Single, consistent footer rendered after the mode body so users
    # always see the version + GitHub + privacy links.
    st.divider()
    st.caption(_brand.footer_markdown())


if __name__ == "__main__":
    main()
