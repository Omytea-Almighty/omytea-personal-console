# Omytea Personal Future Console — MVP

<!-- OMYTEA_ORG_SYNC_README_START -->
> **Organization source of truth:** [`Omytea-Almighty/omytea-personal-console`](https://github.com/Omytea-Almighty/omytea-personal-console). Humans and agents must read [`ORG-SYNC.md`](ORG-SYNC.md) before working. Managed commit/rewrite hooks queue reviewed commits; ordinary direct push is denied; registered linked worktrees are supported. Automation never stages or commits dirty work, changes visibility, or bypasses hooks.
> This repository is public: every intentional commit is a publication decision. Secret scanning is not a privacy, PII, licensing, research, or commercial-sensitivity review.
<!-- OMYTEA_ORG_SYNC_README_END -->

**🚀 Live demo: [omytea-personal-console.streamlit.app](https://omytea-personal-console.streamlit.app/?embed=true)** — open the URL, no install required. Mock mode + non-vision modes work fully in-browser. For real video/webcam prediction, follow the install steps below to run locally with Ollama. *(The `?embed=true` parameter is the canonical public URL — it suppresses Streamlit Cloud's outer chrome for a clean first-paint; the bare URL also works.)*

**A probability-calibrated decision-support tool for personal futures, with local video understanding.**

Built on Omytea's quantum-enhanced world-model substrate. Type a decision **or** upload a short video; get multiple future scenarios with calibrated probabilities, watch the quantum-operator coherence between those scenarios decay over time, and see how new evidence shifts the predictions.

> **Not a deterministic prediction system. Not "fortune-telling." A measurement-update-aware probabilistic decision-support tool with a local-first runtime (no external API required).**

## Quick start — 3 commands

```bash
# 1. Install (creates venv, installs deps, checks Ollama)
bash scripts/install.sh

# 2. Pull a local vision LLM (≈4.5 GB; one-time)
ollama pull llava:7b
ollama pull qwen2.5:7b-instruct

# 3. Run
source .venv/bin/activate && streamlit run app.py
```

Then open http://localhost:8501 → switch to **Video query** mode → upload an mp4 and ask a question.

For the full step-by-step + troubleshooting, see [§ Install and run](#install-and-run) below.

### Tier 2 — Live webcam + native bundle (v0.3.0)

The Console now ships **Mode 6 "Live webcam"** for continuous streaming and a PyInstaller spec for native distribution. Both are opt-in so the Tier 1 install stays light.

**Mode 6 — Live webcam.** Install the optional WebRTC stack, then pick `Live webcam` in the sidebar:

```bash
pip install 'streamlit-webrtc>=0.47,<1.0' 'av>=10.0,<13.0'
streamlit run app.py
```

Camera frames stream into the substrate's detector + IoUTracker on a background thread. Every 8 frames (tunable) the joint wavefunction rebuilds and is evolved under the Lindblad operator — the live coherence-decay chart updates each rerender. Nothing leaves your machine.

**Native bundle.** Pre-built binaries are attached to each release on GitHub. No Python install needed:

| Platform | Variant | Download |
|---|---|---|
| macOS arm64 | one-folder | [omytea-console-Darwin-arm64.tar.gz](https://github.com/Omytea-Almighty/omytea-personal-console/releases/latest) |
| macOS arm64 | single binary | [omytea-console-onefile-Darwin-arm64.gz](https://github.com/Omytea-Almighty/omytea-personal-console/releases/latest) |
| Linux x86_64 | one-folder | [omytea-console-Linux-x86_64.tar.gz](https://github.com/Omytea-Almighty/omytea-personal-console/releases/latest) |
| Docker | multi-arch image | `docker build -t omytea-console:0.3 . && docker run -p 8501:8501 omytea-console:0.3` |

```bash
# Pick a platform, then:
tar xzf omytea-console-*.tar.gz
./omytea-console/omytea-console
# Browser opens at http://127.0.0.1:8501.
```

To build a bundle from source for your own platform:

```bash
bash scripts/build_native.sh             # one-folder (default)
bash scripts/build_native.sh --onefile   # single binary (slower startup)
# → dist/omytea-console/  or  dist/omytea-console
```

The bundle still expects Ollama for the vision LLM (multi-GB models aren't worth embedding); the Console runs in mock mode if Ollama isn't present.

---

## Install and run

### Prerequisites

- macOS 12+, Linux (Ubuntu 22.04+ tested), or Windows 11 (WSL2)
- Python 3.11 or newer
- ~6 GB free disk space (mostly for the local LLMs)
- 16 GB RAM recommended (8 GB works for `llava:7b` text-only mode but is tight)
- [Ollama](https://ollama.com/download) installed — the install script will check + prompt

### Step 1 — Clone and bootstrap

```bash
git clone https://github.com/Omytea-Almighty/omytea-personal-console.git
cd omytea-personal-console
bash scripts/install.sh
```

What `install.sh` does:
- Creates `.venv` (Python virtualenv) if absent
- Installs `requirements.txt` (Streamlit, Pydantic, OpenCV-headless, LLM SDKs, etc.)
- Checks whether Ollama is on `$PATH` and reachable on `localhost:11434`
- Prints next-step instructions (model pulls + launch command)

If you prefer manual install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2 — Install Ollama and pull local models

Install Ollama from <https://ollama.com/download> (one-click installer for macOS / Linux / Windows).

Then pull the models the Console uses:

```bash
# Vision model for Video Query mode (~4.5 GB)
ollama pull llava:7b

# Text model for the New Prediction mode (~4.5 GB)
ollama pull qwen2.5:7b-instruct
```

Both models are open-weight (LLaVA: Apache 2.0; Qwen: Apache 2.0). No account required.

If you don't want to install Ollama yet, you can still run the console in **mock mode** to inspect the UI:

```bash
OMYTEA_CONSOLE_MOCK=1 streamlit run app.py
```

Mock mode returns deterministic stub predictions — useful for development but not for real decision support.

### Step 3 — Launch the Console

```bash
source .venv/bin/activate
streamlit run app.py
```

Open <http://localhost:8501> in your browser. The sidebar has 5 modes:

| Mode | What it does |
|---|---|
| **New prediction** | Text-input career / lifestyle decision → branches + drilldown + coherence chart |
| **Video query** | Upload a video file → entity tracking + scene-LLM analysis + branches + per-entity quantum-state evolution |
| Measurement update | 6-week-later report on a prior prediction → calibration delta + Sean Ellis + effort test |
| Calibration history | Aggregate Brier / log-loss across all predictions with owner-bias breakdown |
| Pricing & pre-order | (Pre-revenue PMF research) tier comparison + willingness-to-pay capture |

### Step 4 — Try the Video query mode

1. Sidebar → "Video query"
2. Upload a short video (mp4 / mov / webm). Recommended: <30 seconds, <50 MB.
3. Type a question: "What might happen next?" / "If the person on the left keeps walking, where will they be in 30 seconds?" / "What could go wrong here?"
4. Pick the number of sampled keyframes (default 5; more = better tracking + slower)
5. Click **🚀 Analyze video**
6. Wait ~30–90 seconds (depending on your hardware — first call may be slower as Ollama warms up the model)
7. Browse the result: sampled keyframes with detection overlays + tracked entities + entity-trajectory quantum evolution chart + 6-8 future branches + ΔP evidence list

### Troubleshooting

- **"OpenCV not installed"** → run `pip install opencv-python-headless` inside the venv
- **"Ollama vision backend not ready"** → start the Ollama daemon (`ollama serve` if it isn't running automatically) and verify `ollama pull llava:7b` finished
- **Vision LLM very slow** → first call always warms the model. Subsequent calls are 5–10× faster. If still slow after warm-up: your hardware is CPU-only and inference is bound by your CPU speed. Try `llava:7b` (faster) instead of `llava:13b` (more accurate).
- **"substrate not importable"** → Omytea quantum substrate needs to be installable. If you cloned this repo, the substrate is vendored in `omytea/`. If you got a release zip, the substrate package should be alongside. If neither, set `OMYTEA_CONSOLE_MOCK=1` to use the offline stub.

### Uninstall

```bash
rm -rf .venv
# Optional: remove local models
ollama rm llava:7b qwen2.5:7b-instruct
```

Your local SQLite of predictions lives at `~/.omytea-personal-console/predictions.db` — delete it manually if you want a clean slate.

---

## What this is (and isn't)

### Is

- A streamlit web app that:
  1. Takes a structured decision input from the user (e.g., "I have a job offer at company A. Should I accept it?")
  2. Compiles the input via a configurable LLM backend (Gemini / Groq / Anthropic / mock) into an Omytea `BeliefProgram` using the natural-language → DSL compiler in `compiler.py`
  3. Uses Omytea's `WaveFunction` + `BranchingPredictor` to generate 3-5 future hypothesis branches with calibrated probabilities
  4. Displays joint hypothesis off-diagonal (which futures are correlated)
  5. Identifies key uncertainty drivers + suggests what evidence to collect
  6. **6 weeks later**: user comes back, reports actual outcome → system updates calibration histogram

- A **falsification platform** for Omytea's hypotheses H3 (off-diagonal information value) and H4 (product user appeal). See `docs/RISKS_AND_FALSIFICATION_PLAN.md`.

### Isn't

- A production app. This is an MVP for 10-user self-test, not commercial release.
- Fortune-telling, tarot, astrology, 算命, oracle. The brand framing is strictly **probability + calibration + evidence**.
- A medical / legal / financial advice system. Scope is strictly **career / lifestyle / personal-development**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Streamlit UI (app.py)                                          │
│  └─ Form-based decision input + result visualization            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  compiler.py — NL → BeliefProgram                               │
│  └─ Claude API (Anthropic SDK)                                  │
│     Master plan §7 OmyteaCompiler-LLM (minimal version)         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  console.py — Core scenario logic                               │
│  ├─ omytea.quantum.WaveFunction (branch hypotheses)             │
│  ├─ omytea.joint_belief.JointWaveFunction (off-diagonals)       │
│  ├─ omytea.quantum.BranchingPredictor (future evolution)        │
│  └─ scenarios/<scenario>.py (career_decision, etc.)             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  storage.py — SQLite persistence                                │
│  ├─ user_predictions (id, user, timestamp, BeliefProgram,       │
│  │                     WaveFunction snapshot, scenario)         │
│  └─ measurement_updates (id, prediction_id, timestamp,          │
│                          actual_outcome, calibration_delta)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick start

### Prerequisites

- Python 3.11+
- Omytea installed (`pip install -e ../` from parent WMDB repo)
- Anthropic API key (set `ANTHROPIC_API_KEY` env var)

### Install

```bash
cd omytea-personal-console
pip install -r requirements.txt
```

### Run

```bash
# Real API mode (default)
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py

# Mock mode (offline, no API calls)
export OMYTEA_CONSOLE_MOCK=1
streamlit run app.py
```

Open browser to `http://localhost:8501`.

### Smoke test

```bash
pytest tests/
```

---

## Scenario 1: Career Decision Support

The MVP ships with one scenario: **`career_decision`**.

### User input

- Current job / location / role / salary / industry
- Decision options (e.g., "Accept offer A", "Counter-offer B", "Stay")
- Relevant context (family situation, health, learning goals, financial runway)

### Output

For each decision option, the system shows:

1. **3-5 future hypothesis branches** (e.g., "Stay 6 months then leave anyway", "Thrive at new job", "Burnout within 3 months", "Counter-offer accepted, original problems remain")
2. **Probability** for each branch (e.g., 22% / 35% / 18% / 25%)
3. **One-sentence narrative** description per branch
4. **Key uncertainty driver** per branch
5. **Joint hypothesis off-diagonal**: which outcomes are correlated (e.g., "burnout" + "relocation" + "relationship strain" share coherence)
6. **Pearl rung-2 sensitivity**: what changes if the user does X (interventional preview)
7. **Recommended evidence to collect**: what new info would most reduce uncertainty

### Measurement update loop

6 weeks later, the user comes back and reports what actually happened. The system:

- Stores `actual_outcome` keyed to the original prediction
- Computes Brier score / calibration delta vs the original distribution
- Updates a **calibration histogram** (cumulative across all user predictions)
- Improves future predictions via posterior re-fit

---

## File layout

```
omytea-personal-console/
├── README.md                      # This file
├── requirements.txt               # Python deps
├── app.py                         # Streamlit main app
├── compiler.py                    # NL → BeliefProgram via Claude API
├── console.py                     # Core Omytea integration
├── storage.py                     # SQLite persistence
├── scenarios/
│   ├── __init__.py
│   └── career_decision.py         # Scenario 1 implementation
└── tests/
    ├── __init__.py
    └── test_smoke.py              # Basic smoke tests (no API required)
```

---

## What gets measured

This MVP is the empirical platform for two of Omytea's pre-registered hypotheses (see `docs/RISKS_AND_FALSIFICATION_PLAN.md`):

### H3: Off-diagonal information value

For each prediction, we store both:
- **Product-form joint**: assuming independence between marginal hypotheses
- **Off-diagonal joint**: using `JointWaveFunction.to_density_matrix()` off-diagonal coherence

After 6 weeks, when the user reports actual outcome on joint events, we compute Brier score for both variants. If the off-diagonal variant is consistently better → H3 supported. If not → H3 falsified, off-diagonal display removed from product.

### H4: Product user appeal

10-user self-test target:
- NPS ≥ 30
- Perceived utility ≥ 5/7
- 50%+ willing to pay ≥ $5/month (USD — US market is the canonical
  billing currency; see `currency.py` for non-USD display rates)
- Qualitative differentiator from astrology / fortune-telling /
  talking to friends

---

## Brand framing rules (strict)

These rules govern all UI copy and external communication. Violations should be caught in PR review.

✅ **Use**: "probability scenarios", "decision support", "evidence-driven futures", "calibrated forecasts", "measurement update", "hypothesis branches"

❌ **Don't use**: "fortune", "oracle", "tarot", "horoscope", "predict your future", "destiny", "what will happen to you", 算命, 命理, 占卜, 玄学

---

## License

Apache 2.0 — companion to the broader `omytea-quantum-substrate` package.

---

## Master plan alignment

| Master plan § | This MVP instantiates |
|---|---|
| §1 Quantum-enhanced WM for streaming reality | Personal-future scenario = streaming reality terminal-user use case |
| §5 Quantum Information Core | Uses `WaveFunction` + `JointWaveFunction` + density-matrix Born projection |
| §6 Operator algebra | `BranchingPredictor` + scenario-specific operators (career-decision physics) |
| §7 LLM as Compiler | `compiler.py` Claude API = OmyteaCompiler-LLM minimum version |
| §9 Public Product — World Console | This MVP = §9 minimum viable instantiation |
| §3 Claim Level | L2 (Prototype) when shipped; L3 (Empirical) after 6-week self-tests measured |

See `docs/V4_15_FOCUS_PROPOSAL.md` §2.2 for full milestone context.
