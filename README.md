# Omytea Personal Future Console — MVP

**A probability-calibrated decision-support tool for personal futures.**

Built on Omytea's quantum-enhanced world-model substrate. Input your situation, get multiple future scenarios with calibrated probabilities, see how new evidence updates those probabilities over time.

> **Not a deterministic prediction system. Not "fortune-telling." A measurement-update-aware probabilistic decision-support tool.**

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
