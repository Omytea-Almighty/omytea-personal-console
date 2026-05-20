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
legibly. Reference: `~/Downloads/academic-cv-site/nye-clock-backdrop.html`.

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
