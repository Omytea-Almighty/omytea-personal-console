# Console Redesign — ChatGPT-form world-model tool

**Status**: PLANNED. Design locked by the founder 2026-05-19. Stage 1 is the
next focused build. This document is the executable spec — no re-investigation
needed to start.

## Vision

Omytea Console becomes a ChatGPT / Claude-shaped **world-model prediction
tool**:

- **Left sidebar = navigation only** — a history of past predictions
  (flat, date-grouped list; tree / projects is a later increment).
- **Right main = ONE unified prediction workspace.** No mode-switching.
- A prediction is assembled from several input modalities *in one place*:
  text conditions + live video + uploaded video / files (a "+" attach
  button, chat-style) + an optional 玄学 lens.
- **NOT a chatbox** — only the "one composer + attach" affordance is
  borrowed; no turn-by-turn chat. The tool is explicitly for
  non-single-text-prompt, multi-modal world-model input — to let users
  *experience a world model*.
- Packaging may look like a 占卜 / cosmic-divination UI (the Nye Clock
  宇宙风格), but the substance is **world-model + quantum scientific
  prediction**; 玄学 is one optional lens, never the headline.

## Locked decisions

- **History**: a flat, date-grouped list ships first (Stage 1,
  ChatGPT-style), then grows into a **user-organized tree** (Stage 4) —
  the user creates their own categories and adds their own labels, like
  Notion / file managers / tagged note apps. No fixed taxonomy is
  imposed by the app.
- **Frontend**: stay in Streamlit. The information architecture (history
  rail + single workspace, no modes) is achievable; interaction fluidity
  will not match a native React SPA — accepted.

## Mode → modality mapping

The current 7 sidebar modes dissolve:

| Current mode | Becomes |
|---|---|
| New prediction | the default workspace composer |
| Video query | an input modality — "attach a video" |
| Live webcam | an input modality — a "live video" toggle |
| Measurement update | "open a past prediction → score it later" — it **is** the past-prediction viewer |
| Calibration history | the sidebar history rail itself |
| Pricing & pre-order | a small sidebar footer link, not a mode |
| Traditional × Calibrated (玄学) | an optional lens toggle inside the workspace |

## Stages

### Stage 1 — the shell (next focused build)

Rewrite the two shell functions; keep all 7 `render_*` bodies intact.

- `render_sidebar()` (`app.py:184`): brand → "✦ New prediction" button →
  **History list** (`storage.list_user_predictions`, date-grouped,
  clickable) → a "More" expander transitionally housing the secondary
  surfaces (Video / Live / 玄学 / Measurement / Pricing) → a Settings
  expander (language + currency, moved out of the main flow) → footer.
  Returns a route tuple.
- `main()` (`app.py:2790`): route → new workspace / a history prediction
  (via `render_measurement_update` for that id) / a secondary surface.
- **Open sub-questions to resolve at build time:**
  1. *User / session identity* — `list_user_predictions(user_id)` needs a
     `user_id`; confirm what id `render_new_prediction` saves under
     (anonymous? per-session?). The history rail lists that id's records.
  2. *History-item click* → route to `render_measurement_update`
     pre-loaded with the `prediction_id` (likely a small signature or
     `st.session_state` tweak).

### Stage 2 — the unified composer

Merge the "More" surfaces into one composer: text conditions + a "+" file
attach (`st.popover` / `st.file_uploader`) + a live-video toggle + a 玄学
toggle + one "Run prediction". Video query → attach a video; Live webcam
→ a toggle.

### Stage 3 — cosmic visual + Nye Clock solar system

Replace the dense 玄学 astrolabe (founder verdict: "不知所云") with a
faithful recreation of the **Nye Clock solar-system view** — Sun-Earth-Moon
orbital, deep-space 宇宙风格 — static SVG, no GPU. Extend the cosmic
aesthetic to the whole shell. Map 八字 / 占星 data onto the solar system
legibly.

> **Reference CORRECTED 2026-05-19**: the canonical final Nye Clock is
> **`~/Downloads/UCSB/Adonyth/tw_.html`** — the project's own sync
> scripts name it the sole source file ("以 tw_.html 为唯一源文件"); the
> mac app (Nye Clock v1.0.0) and the web deploy are both copies of it.
> Stage 3's `_render_nye_solar_system` was mistakenly built from
> `academic-cv-site/nye-clock-backdrop.html` — a separate, older
> CV-site *backdrop embed*, the WRONG version. It must be rebuilt
> faithfully from `tw_.html`; that rebuild is folded into #60 D below.

### Stage 4 — user-organized history tree (categories + labels)

The flat date-grouped rail (Stage 1) grows into a tree the **user owns**
— like Notion's sidebar, file managers, or tagged note apps. The app
imposes no fixed taxonomy; the user builds their own.

- **User-defined categories** — create / rename / delete your own
  categories (folders / projects); the history rail becomes a tree of
  them.
- **Custom labels** — add your own labels / tags to a prediction and
  classify by them; a prediction may carry several.
- The rail can group by category or filter by label.
- **Storage** — `PredictionRecord` carries no category / label field
  today; add storage support (new columns, or a small `categories` +
  `prediction_labels` table) with migration via the existing
  `_ensure_schema`.
- **UI** — a create-category control, rename / delete, assign a
  prediction to a category, add / remove labels on a prediction, and
  group-by-category / filter-by-label in the rail.

### Stage 5 — polish

i18n, copy (including the stale Mode-7 hero "pick the system" line),
tests, live verification.

---

# PART II — Consolidated design + the v10 heatmap/camera port

Added 2026-05-19 after the founder flagged that the heatmap+camera had
regressed below the v10 marketing demo. Founder instruction: **hold
EVERY design thread at once — fixing the v10 heatmap must not regress
anything else** ("不要顾了这个丢那个"). This Part II is the single
canonical reference; the invariants checklist below is load-bearing.

## Shipped baseline (do not lose any of it)
- Redesign Stages 1–5 (#52–#56): ChatGPT-form IA.
- #57 美化: deep-space cosmic CSS theme.
- #58 chatbox layout: output region on top (quantum heatmap always-on
  centerpiece, idle = uniform), input composer below.

## The new work — port the v10 heatmap + camera
Source: `marketing/console/Omytea Console v10 — see both at once.html`
(read it; the heatmap + camera + motion-loop JS/CSS is the spec).

The current heatmap is a static server-rendered SVG — zero interaction,
and the live camera does NOT drive it (exactly the v8 "functionally
hollow" failure that v9's "camera drives the math" fixed). Fix: the
heatmap+camera output block becomes an **embedded HTML/JS component**
(`st.components.v1.html`) porting v10's real code. It is LIGHTWEIGHT —
vanilla-JS pixel-diff on an 80×45 canvas, "zero model download"; NOT the
GPU-heavy WebGL the founder vetoed for the Nye Clock.

Must reproduce, from v10:
- **Camera drives the math** — a hidden canvas grabs a frame ~10 fps,
  pixel-diffs vs the previous frame → motion centroid + intensity → the
  heatmap updates LIVE and continuously, with NO submit click. A motion
  overlay marker on the video; a motion status badge.
- **See both at once** — when the camera (or an uploaded video) is
  active, the camera preview and the heatmap sit SIDE BY SIDE in one
  frame (preview sticky); single-column fallback on narrow viewports.
- **Interactive, precise cells** — each heatmap cell: hover highlight;
  click → a cell-popover with that cell's number + plain-English
  reading. Precise, legible cell sizing. Branch × time grid, NOW→HORIZON.
- **Smooth loop** — ~100 ms tick, EMA smoothing, lazy re-render (skip
  rebuild on tiny deltas) so it feels live, not laggy.
- The component still accepts the server-side prediction (branch
  distribution) when a prediction has run; idle = uniform.

## DESIGN INVARIANTS — must NOT regress ("不要顾此失彼" checklist)
Every item is already shipped and must still hold after the port:
1. **IA** — sidebar = history rail + "✦ New prediction" + "Manage
   categories"; main = one unified workspace; NO mode-switching radio.
2. **Chatbox layout** — output region top, input composer below.
3. **History tree** — user-created categories + custom labels; storage
   v6 schema intact.
4. **玄学 lens** — the optional lens toggle still works: Nye Clock solar
   system (八字⊕占星) + 易经 + 塔罗 companion panels + 4-system joint
   consensus gauges. Astronomically-exact 八字 节气 preserved.
5. **Multi-modal input** — text conditions + "+" file attach +
   live-video toggle + 玄学 toggle, all in the one composer.
6. **Cosmic aesthetic** — the #57 deep-space theme; whole console
   cohesive; restraint (limited palette, hierarchy, negative space, one
   focal glow — never decoration).
7. **Quantum heatmap = permanent output centerpiece** — upgraded to the
   interactive v10 component, still always-on (idle = uniform).
8. **Honest posture** — world model + quantum is the substance; 玄学 is
   opt-in; no fabricated data surfaced as real.
9. **i18n** — EN / 中 / ES / FR all still resolve.
10. **All tests green** (627+); app boots clean (AppTest 0
    exceptions / 0 error elements).
11. **Independent scroll** — the output region and the input region
    scroll independently; scrolling one never moves the other (see C).
12. **玄学 in the output region** — when the lens is on, the Nye Clock
    玄学 view is reachable in the output region via a one-click toggle
    that covers the quantum heatmap (see D).

Build verification must confirm ALL 12 — not just that the heatmap works.

## Output / input layout — two more founder requirements (2026-05-19)

These extend the v10 work. The v10 heatmap/camera component (Acceptance
#59, in progress) is the building block; **C + D are the next pass
(Acceptance #60)** — the final output/input assembly around that block.
Implement both in a NATURAL way (use Streamlit's own primitives).

**C — independent scroll panes.** The workspace is two independently
scrolling regions: the **output region** (top — the quantum heatmap /
camera / results) and the **input region** (bottom — the composer).
Scrolling one must NOT move the other — like a chatbox, or a two-pane
IDE. The load-bearing reason: during live-video input the output
region's quantum image must stay visually STABLE — it must never jump
or scroll away while the user works in the input region. Natural
Streamlit implementation: each region is its own fixed-height
scrollable container (`st.container(height=…)`); the output pane is the
larger one (the heatmap is the centerpiece), the input pane smaller.
The two panes do not scroll each other.

**D — 玄学 output lives in the output region.** When the 玄学 lens
toggle is on, the 玄学 output — the Nye Clock solar-system UI (八字⊕占星
+ 易经 + 塔罗 + joint consensus) — appears in the OUTPUT region, not
buried elsewhere. The output region then has two views: the **quantum
heatmap** (default — the scientific centerpiece) and the **玄学 Nye
Clock** view. A small one-click toggle (a pill / segmented control at
the top of the output region, shown only when the 玄学 lens is enabled)
switches between them — the 玄学 module expands to cover the quantum
module, and back. Quantum stays the default; 玄学 is the opt-in
alternate view. Both live in the same independently-scrolling output
pane from C.

**The 玄学 Nye Clock view must be (re)built from the canonical final
Nye Clock — `~/Downloads/UCSB/Adonyth/tw_.html`** — NOT the old
`nye-clock-backdrop.html`. The current `_render_nye_solar_system`
(redesign Stage 3) used the wrong backdrop and is superseded: #60 D
rebuilds the 玄学 output view faithfully from `tw_.html` (the founder's
final 3-D Nye Clock). Read `tw_.html` to recover its actual look.
