# 玄学 Lens — Product-level Redesign

Status: planning doc. Drives the loop iterations that follow.

## 1. The founder's critique (verbatim, the source of this rebuild)

The lens currently *looks like* a feature but is in fact scaffolding —
a frame built around modules that don't really function:

- It IS an easter egg, that is fine, but the UX is unfriendly.
- The visible content is just listed: a static Nye Clock; what looks
  like a single unprofessional 六爻 hexagram (real 六爻 has both a
  primary and a derived hexagram); three sketchy-looking tarot cards;
  a "constellation chart" rendered with emoji as if it were a draft.
- Nothing explains what these are, why they appear, or what they do.
  Nothing is designed to make their purpose obvious at a glance.
- The birth-time input isn't labelled as "date of birth" and has no
  context. It is personal info — it belongs in Settings (e.g.
  Personalization or Measurement update), not in the per-prediction
  composer.
- 六爻 only shows one hexagram. Real 六爻 always has changing lines →
  a primary + a derived hexagram.
- Nye Clock is embedded too small inside its frame — even within the
  small frame it isn't fully visible. And no one will understand what
  a "Nye Clock" is doing here without an explainer.
- 八字 / 四柱 and the zodiac chart are NOT integrated into the UI at
  all — they don't render against a real chart, no four pillars.
- 紫薇 doesn't show how the database is used. It's there, but it's
  inert.
- Every module is decorative — no interpretation, no help for the
  decision, no readout of "what this means for your prediction."
- The whole lens is **not integrated with the real (lens-off) world
  model prediction**. With the lens on, the divinations should still
  be *helping* the world model — modulating, augmenting — not just
  sitting in parallel.
- The English version still shows "玄学 lens" with the Chinese
  characters 玄学 intact. Non-Chinese users cannot read it.

## 2. Diagnosis

The lens shipped as "scaffold first, fill later," and the fill never
happened. The skeleton is real (toggle wiring, the consensus-prior
math already mixes a 玄学-consensus into the per-branch favourability
— see `_metaphysics.py` / `_render_traditional_lens`), but every
surface a user actually sees is a placeholder. The product debt:

1. **Identity** — no module labels what it is or why it is there.
2. **Inputs** — personal data is asked per-prediction; it should be
   asked once and remembered.
3. **Outputs** — nothing tells the user what the modules' outputs
   mean for *this* decision.
4. **Visual grammar** — each tradition has a real visual grammar
   (hexagram lines, tarot card art, 12-palace 紫薇 chart, planetary
   chart). The current modules ignore all of it.
5. **Integration** — the symbolic consensus exists in code but isn't
   shown to converge with the probabilistic output. The lens looks
   like a separate parallel feature rather than an augmentation.
6. **i18n** — Chinese characters in the English UI.

## 3. Principles for the redesign

- **Every module is a real feature or it doesn't ship.** If a module
  can't be made real and useful in the lens, remove it.
- **Lens-on composes with lens-off, never replaces.** With the lens
  on, the prediction is *augmented*, not swapped. The augmentation
  must be visible and explained.
- **Personal data lives in Settings → Personalization.** Birth date /
  time / city are user info, not per-prediction. The composer never
  asks again once they're set.
- **Every output gets a plain-language explainer.** What it is, what
  its number means for this decision, in two lines.
- **Each module honours its tradition's visual grammar.** No emoji
  fallbacks. No tiny embeds. If a real visual is too expensive,
  render a credible, designed alternative — not a draft.
- **Bilingual labelling.** "玄学" stays in the Chinese locale; the
  English UI gets a real English umbrella term (currently picked:
  *"Metaphysics lens"*).

## 4. Information architecture

| Concept | Lives in |
|---|---|
| Birth date / time / city | **Settings → Personalization** (R4) |
| Standing "about you" context | Settings → Personalization (R4) |
| Default scenario / horizon / branch count | Settings → Prediction defaults (R2 — shipped) |
| Per-prediction decision input | Composer |
| Lens-off prediction view | Workspace output (default) |
| Lens-on overlay | Same workspace output, augmented in place |
| Per-divination explainer | Inline, beside / under each module |
| "What this means for your decision" | A consensus readout at the bottom of the lens region, visually linked to the probability heatmap |

## 5. The redesigned lens — surfaces

After the lens toggle is on, the workspace output region opens a lens
view with these blocks, in this order:

### 5.1 Header + consensus readout (top)
A small explainer + the **consensus arrow**: "Across five symbolic
systems, branch X is the favoured / contested branch." Tied visually
to the same branches the heatmap shows. This is the proof that the
lens does something to the prediction, not just sits beside it.

### 5.2 Nye Clock — centerpiece
Promote from a tiny embed to a real centerpiece (full-width or close
to it). Add a one-line explainer: *"The celestial clock — sun / earth
/ moon positions at the moment of this prediction, used as the timing
prior."* Tie the live numbers (model %, 玄学-consensus %) into the
clock's readout strip.

### 5.3 I Ching / 六爻
Cast a hexagram from a deterministic hash of (current time, decision
phrasing). **Show both** the primary hexagram and, when changing
lines exist, the derived hexagram. Each hexagram drawn as six real
lines (solid / broken), labelled with its 卦名 and a two-line
interpretation specific to this decision.

### 5.4 八字 / Four pillars
Use the birth data from Settings → Personalization. Render the four
pillars (年柱 / 月柱 / 日柱 / 时柱) with their stems + branches +
5-element tags. Add a one-line favourability score — how the natal
chart leans for this kind of decision.

### 5.5 紫薇 (Zi Wei)
Use the birth data; draw a small 12-palace chart with the major
stars in their palaces. Highlight the 命宫 (life palace) and the
currently active 大限 (major limit). Two-line interpretation for the
decision at hand.

### 5.6 Tarot
Three-card draw — past / present / future. Drop the sketchy
placeholders; use either a public-domain Rider-Waite-style image set
or a clean SVG redraw. Each card with upright/reversed + meaning tied
to the decision.

### 5.7 Zodiac / 星座
Drop the emoji. Render a real chart: at minimum the sun sign for the
decision moment; with birth data set, also the moon sign and
ascendant against a small sky wheel.

### 5.8 Degradation
If birth data isn't set in Personalization, modules that need it
(BaZi, ZiWei, ascendant) show a clean "Set your birth date in
Settings → Personalization" prompt — never an empty placeholder. The
rest (I Ching, Nye Clock, tarot, sun-sign zodiac) still work without
it.

## 6. Roadmap (loop iterations)

Each iteration ships one slice independently, verified live.

- **L1 — i18n & label.** Replace `"玄学 lens"` in the English locale
  with **"Metaphysics lens"**; update the help text. Lightweight,
  ship immediately. (R4-precondition unblocker for non-Chinese users.)
- **L2 — Settings → Personalization (R4) with birth data.** This is
  the long-pending R4 slice. Personalization now holds: display name,
  standing "about you" context, readout tone, **birth date / time /
  city** for divination math. Composer stops asking for birth.
- **L3 — Lens shell + per-module explainers + the consensus readout.**
  Redesign the lens output region: header, per-module cards each with
  a one-line explainer, the consensus readout at the bottom, visually
  linked to the heatmap. Wire to Settings birth data; degrade
  gracefully without it.
- **L4 — I Ching / 六爻**, real cast (primary + derived hexagram),
  proper line drawing, per-decision interpretation.
- **L5 — Nye Clock**, full-width centerpiece, explainer, live readout
  tie-in.
- **L6 — 八字 / Four pillars**, rendered from birth data.
- **L7 — 紫薇**, 12-palace chart from birth data.
- **L8 — Tarot**, real card visuals + per-decision meaning.
- **L9 — Zodiac**, real sky chart (no emoji).
- **L10 — Consensus tie-in**, the single readout + the visual link to
  the heatmap, polished.

## 7. Open questions

- **Tarot card art licensing.** Rider-Waite is mostly public domain
  (1909, US). Any modern redrawn deck needs license verification.
- **"Real" math vs. "honestly playful."** Are we using real
  divination libraries (true I Ching coin cast, real BaZi math from
  open-source libs) or deterministic-but-symbolic shortcuts?
  Recommendation: real-ish math where libraries exist (六爻 via coin
  hash, BaZi via element math); honestly note in the explainer that
  the app does not sell fortune-telling — it overlays symbolic priors
  as one heuristic among many.
- **Storage of birth data.** Personalization birth data sits in
  `st.session_state` (per-session) for now; a future sign-in-bound
  storage layer (alongside prediction history) will make it durable.

## 8. Non-goals

- We are NOT building a divination service. We are augmenting a
  probability-calibrated decision-support tool with a symbolic prior
  overlay — clearly labelled as an experimental lens, not a fortune
  reading.
- We are NOT shipping anything that promises to predict the future.
  The lens output language stays calibrated (a "modulation," a
  "prior," a "leaning") — never "this will happen."
