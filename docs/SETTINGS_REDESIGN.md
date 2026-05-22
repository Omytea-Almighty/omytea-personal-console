# Settings & Account UX — Research, Architecture & Roadmap

Status: planning doc. Drives the loop iterations that follow.

## 1. Why this exists

The console's "Settings" is today a mid-sidebar expander holding only two
controls — Language and Currency. That is not a settings *system*; it is a
leftover. The founder's directive: study how mature products structure the
account + settings area, distil the shared patterns (they are shared because
they encode human habit), and rebuild the console's settings into a real,
product-aware system.

## 2. Platform research — how the leaders do it

**Account control.** Claude, ChatGPT, VS Code, Discord, Slack, Linear all
anchor the account/identity control to the **bottom-left of the sidebar** —
the last element in the rail, always in the same corner, showing avatar +
name. (The console's account-pin commit already lands our account chip
there.)

**Settings entry point.** Settings is always reached *from the account
corner*, never hunted for elsewhere: ChatGPT and Claude open it from a menu
on the bottom-left profile; Discord, VS Code and Slack put a **gear icon
directly beside the account/user area**. We adopt the gear-beside-account
form — one click, no menu.

**Settings surface.** ChatGPT and Claude use a **modal** with a left rail of
categories + a content pane; macOS System Settings and the Google Account
page use a **full page** with the same left-rail shape. The constant is a
**two-pane layout** — categories left, the selected category's controls
right.

**Category structure (the shared vocabulary).** Across ChatGPT, Claude,
Apple, Google and WeChat the top-level buckets recur: General (language /
appearance / region), Personalization (custom instructions / memory / tone),
Data & Privacy (export / delete / history), Account, Notifications,
Connected apps / Integrations / API, About. UX research consensus: **4–6
top-level categories**, labelled to users' mental models, always grouped —
never one flat list.

**Per-setting anatomy.** Each setting is a **row**: a clear label, a
one-line description, one control (toggle / select / input). Destructive
actions are visually separated and confirmed.

## 3. Design principles (distilled)

1. **Predictable location** — settings live in the account corner; never hunted.
2. **Grouped and shallow** — 4–6 categories, each shallow; no mega-list.
3. **Label to the mental model** — "Language", not "i18n".
4. **Every control self-explains** — label + short helper text.
5. **Sensible defaults** — the user only touches what they care about.
6. **Separate the dangerous** — clear / delete / export sit apart, confirmed.
7. **Settings are product surface** — the best settings expose the product's
   real levers, not generic chrome.

## 4. The console's settings, redesigned

### Entry point
- Remove the mid-sidebar "Settings" expander.
- At the sidebar's bottom, beside the account chip, add a **small gear icon
  button**. Account chip + gear sit together, bottom-anchored.
- The gear opens a **Settings view** — a routed full-width surface
  consistent with the existing Measurement-update / Calibration-history
  secondary pages — with a **left rail of categories** + a back-bar.

### Category architecture (6, product-aware)

| Category | What it holds |
|---|---|
| **General** | Display language; region & currency; timezone; number / date format. |
| **Prediction defaults** | Default time horizon (the composer's 3 / 6 / 12 / 24-month select); 玄学 lens on-by-default. |
| **Model & API** | Active LLM backend (Mock / Gemini / Groq / Anthropic / OpenAI); user-supplied API keys (password field, session-scoped, never committed); model choice. |
| **Personalization** | Display name / handle; a standing "about you" decision context the model reuses (so the user never retypes "F-1 student, ML focus"); readout tone (concise / detailed). |
| **Data & privacy** | Export prediction history (CSV / JSON); clear history; the honest note that Streamlit Cloud storage is ephemeral. |
| **About** | Version, links, the not-a-deterministic-system disclaimer, what the tool is / is not. |

### Why these (product-aware reasoning)
The console's job is *probability-calibrated prediction*. Its real levers —
the scenario, the horizon, the branch count, the model, the standing
context — are exactly what a returning user wants to set once and reuse.
"Prediction defaults" + "Personalization" + "Model & API" turn one-off
composer inputs into persistent preferences. That is the difference between
"a form" and "a tool you configure."

## 5. Implementation roadmap (loop iterations)

- **R1 — Relocate.** ✅ Drop the Settings expander; add the gear beside the
  account; add a `ROUTE_SETTINGS` view with a category rail + back-bar;
  migrate Language + Currency into **General**. Pure relocation, no
  behaviour change. Ship + verify.
- **R2 — Prediction defaults.** ✅ Default time horizon + 玄学 lens
  on-by-default, persisted to session, wired into the composer's initial
  values. Scenario is not a real lever (one scenario ships) and branch
  count is fixed in the substrate, not a composer input — both dropped
  from R2's honest scope.
- **R3 — Model & API.** Backend selector + API-key fields (session-scoped,
  password input) wired to the existing multi-backend layer.
- **R4 — Personalization.** Handle + standing "about you" context + readout
  tone.
- **R5 — Data & privacy + About.** History export / clear; the about panel.

Each iteration ships independently and is verified live. A setting either
wires to real behaviour or is scaffolded honestly — no fake controls.

## 6. Open questions

- **Theme.** The console is a deliberately dark "cosmic" design. A light
  mode is a large, separate effort — keep dark-locked for now; revisit after
  the roadmap.
- **Modal vs routed view.** Routed view chosen for Streamlit robustness
  (modals constrain height); revisit if a modal reads better once built.
- **Persistence.** Session-scoped for now; durable per-user settings need
  the same external store that durable prediction history needs (Streamlit
  Cloud's filesystem is ephemeral).
