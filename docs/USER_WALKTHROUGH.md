# User Walkthrough — Omytea Personal Future Console

A step-by-step guide for first-time users. Assumes you've completed the [README install steps](../README.md#install-and-run).

## What you'll do in this walkthrough

In ~15 minutes you will:
1. Launch the Console
2. Try the **Video query** mode with the bundled sample video
3. Read the prediction branches + quantum coherence chart
4. Save the prediction ID for a future measurement update

By the end you'll understand the full data path: video → entity tracking → vision LLM → BeliefProgram branches → quantum-operator evolution → calibrated future scenarios.

## Sample video included

The repository ships with `samples/walking_demo.mp4` — a 5-second synthetic clip of two figures walking past each other on a horizontal ground line. It's tiny (~70 KB) and deliberately simple, so the first run can complete in under a minute even on modest hardware.

## Step 1 — Launch

```bash
cd omytea-personal-console
source .venv/bin/activate
streamlit run app.py
```

A browser tab opens at `http://localhost:8501`.

**Sidebar should show**:
- **Mode** radio: New prediction / Video query / Measurement update / Calibration history / Pricing & pre-order
- **System status** panel: green checkmarks if Omytea substrate + Ollama are reachable
- **Currency / Locale** selector: defaults to en_US

## Step 2 — Switch to Video query

Click "Video query" in the sidebar. You'll see a new title "🎥 Video query".

There's a "System status (local vision LLM check)" expander — open it. If green, you have a vision model ready. If yellow/red, your Ollama daemon isn't running or `ollama pull llava:7b` hasn't completed.

## Step 3 — Upload the sample video and ask a question

1. **Video file**: drag `samples/walking_demo.mp4` into the upload area, or click and select.
2. **Your question about the scene**: leave the default ("What might happen next? What are the most likely outcomes?") or type your own. Examples:
    - "If both people keep walking, will they meet?"
    - "What's the most likely thing that happens in the next 10 seconds?"
    - "Could something unexpected happen here?"
3. **Your handle**: any string, e.g., `walkthrough_001`. This lets you find this prediction later in the Measurement update tab.
4. **Number of sampled keyframes**: leave at the default of 5.
5. Click **🚀 Analyze video** (the blue button).

## Step 4 — Watch the pipeline run

You'll see three progress spinners:
1. **Step 1/3 — Sampling frames + running substrate perception** (1–2 seconds)
2. **Step 2/3 — Asking local vision LLM to read the scene** (10–60 seconds; first call is slower)
3. **Step 3/3 — Building belief state + applying quantum operator** (<1 second)

When complete, you'll see:

### Sampled keyframes with detection overlays
Five thumbnails of the video at evenly-spaced timestamps. Each has colored bounding boxes around detected entities + polyline trajectories showing how those entities moved up to that frame.

### Tracked entities table
Each row is one entity tracked by the substrate's IoU tracker, with:
- Entity ID (substrate-assigned)
- Label (`motion_blob` for the default detector; `person` / `car` / etc. if you have YOLO installed)
- First frame / last frame it was observed
- Trajectory length (how many sampled frames it appeared in)
- Average confidence

### Entity-trajectory quantum evolution
This is the quantum operator in action. For each tracked entity, the system synthesizes three future-position hypotheses (continue / accelerate / decelerate), builds a JointWaveFunction across up to 3 entities, then applies a Lindblad open-system operator to evolve the off-diagonal coherences over a short horizon.

You'll see:
- **Bundle preview table**: one row per entity with its observed velocity + the prior weights it assigned to its 3 hypotheses
- **Joint hypotheses count**: typically 3 (1 entity) or 9 (2 entities) or 27 (3 entities)
- **Off-diagonal pairs count**: the number of correlated futures the substrate identified
- **Evolution horizon slider** + **decoherence rate γ slider**: play with these to see how the coherence-decay line chart responds
- **Coherence-decay chart**: each line is one off-diagonal pair's magnitude over Lindblad ticks. Lines decaying to zero = those correlated futures have lost coherence and are now effectively independent classical outcomes.

### Story view of predicted scene futures
Below the quantum evolution, the standard prediction-result view appears: 6–8 future branches with probabilities, including 1 wishful (best-case) + 1 worst-case + 4–6 realistic. Each branch has a narrative paragraph grounded in what the vision LLM saw.

### Recommended evidence (ΔP)
A list of observations that would meaningfully shift probabilities, with their expected ΔP in percentage points.

### Prediction ID
At the top of the result, a `prediction_id` is shown (looks like `e09b...`). **Save this** — you'll use it later to report what actually happened in the Measurement update tab.

## Step 5 — Try with your own video

Once the bundled demo works, try a video from your own life:
- A short clip of your kitchen (predict "what's most likely the next state of these dishes?")
- A skate-park clip ("if the skater keeps this line, will they make the trick?")
- A meeting recording's intro ("based on the room layout, who's likely to dominate the discussion?")

The Console is most useful when:
- The video is short (< 30 seconds)
- There are 1–3 clearly tracked entities (more is OK but only the top 3 by track-quality are evolved by the quantum operator)
- Your question is *probabilistic*, not deterministic ("what's most likely?" works; "exactly what time will X happen?" does not)

## Step 6 — Come back in 6 weeks for measurement update

The Console is designed for a *6-week measurement loop*:
1. You make a prediction today
2. Time passes, real events unfold
3. You return to the Measurement update tab with your prediction ID
4. You score each branch by how much it actually materialized (0.0 – 1.0)
5. You answer the Sean Ellis disappointment question + the effort test
6. The Console computes your calibration delta (Brier score / log-loss vs your prior)
7. Aggregate calibration history surfaces in the third sidebar tab

This loop is what makes the Console a *learning* tool rather than a one-shot novelty. The honest goal isn't to be right; it's to be *calibrated* — your stated 70% probabilities should resolve at roughly 70% over time.

## What the Console doesn't do (negative scope)

- No exact-time / exact-distance / exact-amount predictions
- No medical / legal / financial / immigration advice
- No "fortune-telling" / "destiny" / "oracle" / "算命" framing
- No required external API — Ollama default keeps everything on your machine
- No closed-source weights — all default models (LLaVA, Qwen) are open-weight Apache 2.0
- No surveillance / discriminatory ranking / weapon-related applications

If you want to use the Console in a domain that bumps against any of these, the project owner retains case-by-case override authority for specific use cases. Override decisions are documented after explicit ratification.

## Questions, bugs, feedback

Issues: <https://github.com/Adonyth/omytea-personal-console/issues>
Privacy: see `PRIVACY_POLICY.md`
For technical / architectural questions: see `docs/OMYTEA_MASTER_PLAN.md` (start with §9 World Console).
