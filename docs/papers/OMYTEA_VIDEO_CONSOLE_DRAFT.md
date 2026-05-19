# Omytea Video World Console: Quantum-Operator Evolution over Streaming Belief States

**Draft v0.1 (skeleton) — 2026-05-19**

**Status**: skeleton outline + section stubs. Experimental sections are placeholders; numbers populate when a trained perception model lands (DELIVERABLE_PLAN.md Tier 3 follow-on). This document deliberately ships *now* so the design rationale, related-work positioning, and evaluation methodology are pinned before they accumulate unstated assumptions.

**Authors (placeholder)**: Chen Jiaxuan + collaborators TBD.

**Target venue**: arXiv preprint first; conference submission depends on experimental maturity.

**License**: CC BY 4.0 (same as Cui-Ma 2026, our nearest companion paper).

---

## Abstract (target 200 words)

We present the Omytea Personal Future Console, an open-source system that pairs streaming video perception with a quantum-information-motivated joint belief state and an open-system (Lindblad-form) evolution operator to surface calibrated probability distributions over short-horizon scene futures. The system runs end-to-end on a single laptop without any required external API call: detection and tracking through the substrate's perception layer, scene-level interpretation through a locally-served vision-language model (LLaVA-class), and probability-calibrated branch generation grounded in a per-entity hypothesis bundle. Off-diagonal couplings in the joint wavefunction encode classical correlation between entity trajectories; Lindblad dissipation models how those correlations decohere as the prediction horizon extends. The Console persists predictions and accepts retroactive measurement updates from the user, allowing per-user Brier-score / log-loss calibration tracking. We describe the system architecture, the pipeline-invariant evaluation metrics we use to monitor pipeline regressions in the absence of a labelled benchmark, and the design constraints (local-first, multi-vendor, no biometric features) inherited from the larger Omytea framework. Experimental evaluation against trained perception models and a labelled scene-prediction benchmark is left to a follow-up paper as the necessary infrastructure stabilizes.

---

## 1. Introduction

> *Stub — to expand.* 
>
> Outline:
> - Motivation: many personal decisions hinge on short-horizon physical predictions (will this dish boil over, will both pedestrians safely cross, will the kid catch the ball). Existing tooling forces a choice between (a) consumer-grade video Q&A LLMs that hallucinate without surfacing probability, and (b) research-grade world models that don't reach end users.
> - Gap: a desktop-runnable, open-source system that gives *calibrated probability* predictions and lets the user keep score over time.
> - This paper: the Omytea Personal Future Console — system, methodology, and the evaluation infrastructure we built to keep it honest.
> - Contributions (3-4 bullets):
>   - End-to-end open-source pipeline from raw video → joint quantum belief state → calibrated futures, runnable on consumer hardware.
>   - Application of the open-system Lindblad evolution operator (familiar from quantum information) as a *classical* tool to model decoherence of joint-future correlations.
>   - Measurement-update tooling that records ground-truth resolutions and computes per-user calibration metrics over time.
>   - Pipeline-invariant evaluation harness (described in §5) that monitors pipeline regressions without requiring a labelled accuracy dataset.

---

## 2. Related Work

> *Stub — to expand.*
>
> Subsections (with key citations to fill in):
>
> **2.1 Video world models for prediction.** V-JEPA (Bardes et al., 2024); GigaWorld (Yuan et al., 2025); MWM (Sutton-style model-based RL); compare scope (Omytea targets short-horizon, single-stream, decision-support, not video generation).
>
> **2.2 Quantum-information formalism applied to classical inference.** Lindblad master equation as it appears in open quantum systems (Lindblad 1976; Gorini-Kossakowski-Sudarshan-Lindblad). Density-matrix formalism for non-coherent probability bookkeeping. Note: this paper uses Lindblad as a *classical* dissipation model on a joint distribution; we do not claim literal quantum advantage. (Cui-Ma 2026, *World Models with Quantum-Information Substrates*; ADR-009.)
>
> **2.3 Calibrated prediction.** Brier score (Brier 1950), log loss, conformal prediction (Vovk, Gammerman, Shafer 2005). Adaptive Gibbs-Candès (2021). The Console's measurement-update loop is operationally similar to a per-user conformal calibration set.
>
> **2.4 Vision-language scene understanding.** LLaVA (Liu et al., 2024), Qwen2-VL, MiniCPM-V; Ollama as a serving substrate. Omytea uses these as drop-in modules behind a stable BeliefProgram schema — no claim about which is "best".
>
> **2.5 Open-source consumer-runnable systems.** Stable Diffusion → LLaMA → Whisper / OpenAI's reference-implementation tradition. The Console belongs in this lineage: a research-grade system delivered as a Streamlit-and-Ollama bundle for desktop install.

---

## 3. System Architecture

### 3.1 Overview diagram

> *Figure 1.* End-to-end pipeline: video source → substrate detector + IoUTracker → per-entity trajectory store → vision-LLM scene interpretation → BeliefProgram → JointWaveFunction → Lindblad-evolved off-diagonal coherences → user-facing branches with priors, evidence, and calibration tracking.

### 3.2 Perception layer

A pluggable detector (default: motion fallback; optional: YOLO; future: a trained Omytea model) feeds into the substrate's `IoUTracker`, producing stable per-entity IDs across frames. The tracker output is a sequence of `(object_id, label, bbox)` records per frame; these are normalized into resolution-independent trajectories and stored in a rolling window per entity.

### 3.3 Belief state representation

Per `PLAN.md` vocabulary:

| Symbol | Role |
|---|---|
| `WaveFunction` | per-entity sparse branch grid; 3 future-position hypotheses (continue / accelerate / decelerate). |
| `JointWaveFunction` | entity-tuple sparse branch grid; Cartesian product of N ≤ 3 entities × 3 hypotheses; |J| ≤ 27. |
| `OffDiagonalEntry` | sparse off-diagonal element of `ρ_{joint}`; encodes correlation between two joint hypotheses. |
| `LindbladOperator` | open-system evolution operator that dissipates off-diagonal coherence at rate γ. |

### 3.4 Vision-LLM scene interpreter

A vision-language model (default: LLaVA-7b via local Ollama) receives the sampled keyframes plus the per-entity tracking summary and emits a `BeliefProgram`: 6–8 future-scene branches with prior probabilities, exactly one "wishful" and one "worst" branch, plus a recommended-evidence list with ΔP-in-percentage-points entries. The schema is enforced via `extract_json_from_text` shim; on parse failure the system falls back to a deterministic mock stub with `_fallback_reason` surfaced to the UI.

### 3.5 Lindblad evolution

The joint wavefunction's off-diagonal couplings (set heuristically: positive between matching "continue" entity-hypotheses, negative between opposing accelerate/decelerate pairs) are evolved over a short horizon under a Lindblad operator with rate γ ∈ [0.02, 0.30] (UI-tunable). Magnitudes decay monotonically over horizon ticks (verified by the `coherence_monotonic_decay` invariant in §5).

### 3.6 Measurement-update loop

The Console persists every prediction with its `prediction_id`. After a horizon-relevant amount of time passes, the user opens the Measurement update tab, looks up the prediction, and scores each branch in [0.0, 1.0] reflecting how much that branch's described future actually materialized. The Console computes Brier and log-loss deltas vs. the priors and updates aggregate calibration stats.

---

## 4. Implementation

> *Stub — to expand.*
>
> - Streamlit frontend (six modes: New prediction, Video query, Live webcam, Measurement update, Calibration history, Pricing & pre-order).
> - PyInstaller native bundle (one-folder default; single-binary variant available).
> - Storage: SQLite with versioned schema; `predictions`, `measurement_updates`, `branch_drilldowns`, `entitlements`, `preorder_interest`, `calibration_aggregate` tables.
> - Multi-vendor LLM rotation: Ollama (default; local) → Gemini → Groq → Cloudflare → OpenAI → Anthropic → MockBackend; provider-neutral by Omytea master-plan Rule #11.
> - License posture: Apache 2.0; vendored substrate snapshot (slim subset) included in the public release.

---

## 5. Evaluation methodology

### 5.1 Pipeline-invariant metrics

Before trained accuracy numbers are meaningful, the pipeline itself needs invariant checks. These metrics compute correctly regardless of which perception model is in use and detect regressions in the substrate:

| Metric | Expected | Detects |
|---|---|---|
| `tracker_id_switches` | 0 on a clean synthetic trajectory | Tracker assignment regressions. |
| `coherence_monotonic_decay` | 1.0 under Lindblad evolution | Dissipation operator regressions. |
| `joint_cardinality_matches_cartesian` | True for N ≤ 3 entities | Joint-state-build bugs. |
| `pmf_normalization_error` | ≤ 1e-3 across compiled branches | Compiler / prior assignment bugs. |
| `end_to_end_latency_seconds` | Hardware-dependent baseline | Performance regressions. |

Implementation: `eval/` package; CLI `python -m eval.run_eval`. Bundled with synthetic `two_entity_crossing` clips as the baseline fixture.

### 5.2 Calibration metrics from real users

The measurement-update tooling collects per-user prediction outcomes. We track:

- **Brier score**: per-branch squared error vs. the user's resolution score.
- **Log loss**: per-branch −log p applied at the user's resolution.
- **Reliability diagram**: bucketed predicted probability vs. observed frequency. Calibrated systems lie on the diagonal.

These are reported in the Calibration history tab and persisted for longitudinal analysis.

### 5.3 What we are *not* measuring (yet)

> Honest limitations section — important.

- **Per-class accuracy.** Requires a labelled dataset of (video, scene-future-truth) pairs. None exists; the trained perception model and its accompanying labelled-eval dataset are deferred to a follow-up paper.
- **End-to-end accuracy vs. competing systems.** Same gating dependency.
- **Multi-entity (N > 3) joint state.** Out of scope per master plan v0.4; combinatorial blow-up makes it expensive without further substrate work.

---

## 6. Preliminary results

### 6.1 Pipeline-invariant metrics (synthetic fixtures)

The bundled synthetic fixtures (`eval.synthetic_truth.build_two_entity_crossing_clip`) — two linear-motion entities crossing on a horizontal band — produce these `python -m eval.run_eval` numbers (single-machine, hermetic, reproducible):

| Clip | Resolution | Truth entities | `tracker_id_switches` | `joint_cardinality_matches_cartesian` | `coherence_monotonic_decay` |
|---|---|---|---|---|---|
| `two_entity_crossing` (12 frames) | 320×240 | 2 | 0 | True | 1.0 |
| `two_entity_crossing` (20 frames) | 480×320 | 2 | 0 | True | 1.0 |

`tracker_id_switches = 0` because the synthetic-truth substitute in `eval/run_eval.py` currently uses identity matching against ground truth (real-perception output substitutes in when the trained model lands). `joint_cardinality_matches_cartesian = True` confirms `|JointWaveFunction| = 3^N_entities` (9 hypotheses for 2 entities), the invariant the substrate guarantees. `coherence_monotonic_decay = 1.0` confirms every off-diagonal magnitude transition under Lindblad evolution decreases (or stays equal) — i.e. the dissipation operator behaves as designed.

### 6.2 End-to-end timing on real video

We ran the full pipeline against `samples/walking_demo.mp4` (80 KB, 5-second, 10 fps, 50 frames) on an Apple M-series laptop (16 GB RAM, no GPU; Ollama CPU-only inference) using `scripts/real_e2e.py`. Two configurations:

**Configuration A — 4 sampled frames, llava:7b (cold start):**

| Step | Wall-clock | Notes |
|---|---|---|
| Substrate ingest + tracking | 0.32 s | `MotionFallbackDetector` + `IoUTracker`; 6 tracked entities found |
| Vision-LLM scene compile | 600 s (timeout) | llava:7b CPU-only inference exceeded the 600 s honest-fallback ceiling → fallback stub returned |
| BeliefProgram → ConsoleResult | < 0.01 s | pure-Python schema conversion |
| Lindblad evolution | < 0.01 s | 27-cell joint state, 6-tick horizon |

The vision-LLM timeout demonstrates the **honest-fallback design pattern** (§3.5): rather than hang indefinitely, the system surfaces a fallback stub of 7 branches plus an explicit `_fallback_reason` field, and the UI shows a banner with the failure cause and remediation hints. The rest of the pipeline runs to completion regardless.

**Configuration B — 2 sampled frames, llava:7b (warm model):** populated by the v0.2 of this draft once the rerun completes.

### 6.3 What the timing implies for product design

- Substrate perception is the cheap step on CPU-only hardware: the 0.32 s ingest budget supports near-realtime per-frame processing for streaming use (Mode 6 live webcam) without GPU.
- Vision-LLM inference is the cost driver. llava:7b CPU-only is a poor fit for short interactive sessions; on Apple-M GPU or a discrete GPU, real benchmark numbers populate quickly. The fallback design ensures users always see *some* prediction even when the LLM call is unreliable.
- For the live mode, the design choice to call the vision LLM only on user `📸 Capture & predict` (not per-frame) is validated: per-frame LLM calls would be infeasible on consumer CPUs.

### 6.4 Open data

Raw per-run JSON artifacts are written to `docs/papers/real_e2e_runs/` so each invocation is archivable + parseable for paper-revision-time aggregation. The eval-harness CLI emits `--json` for the same purpose.

### 6.5 Limitations

These numbers do not constitute a benchmark against any competing system. They establish (a) pipeline correctness on a controlled fixture, and (b) the cost profile of the current default backend. Per §5.3, real accuracy numbers wait on a trained perception model and a labelled scene-prediction dataset; v0.2 of this draft will incorporate both.

---

## 7. Discussion

> *Stub — to expand.*
>
> - **What the quantum-information formalism buys us.** A unified bookkeeping for joint distributions + their correlations + the dissipation model. Lindblad gives a principled tunable for "how fast does correlation between entity-future trajectories wash out as the horizon extends?" — a question that's awkward in pure classical-probability vocabulary.
> - **What it doesn't buy us.** No claim of quantum advantage. No claim of literal entanglement. The off-diagonal magnitudes carry classical-correlation information; they are not amplitudes of a true quantum state.
> - **Brand framing.** Per master plan §2.9 negative scope, this is not "fortune-telling" or "oracle" tooling; it is decision support that explicitly forecasts uncertainty and asks users to score themselves over time.
> - **Open questions.** Calibration drift over long horizons; per-user prior learning; multi-camera reconciliation; trained-perception-model selection criteria.

---

## 8. Related Omytea documents and code

- `OMYTEA_MASTER_PLAN.md` §9 — World Console design.
- `OMYTEA_MASTER_PLAN.md` §15.5 — PMF instrument discipline.
- `WORK_PLAN_V415.md` — current cycle's empirical milestones.
- `DELIVERABLE_PLAN.md` — what Tier 1 / Tier 2 / Tier 3 / Tier 4 mean for this paper.
- Repository: <https://github.com/Adonyth/omytea-personal-console>.
- Domain: <https://console.omyteaai.com>.

---

## 9. Acknowledgements

> *Stub.* Vision LLM ecosystem (LLaVA, Ollama). Streamlit. PyInstaller. The Omytea team.

---

## References

> *Stub — full BibTeX to populate when the experimental sections fill in.* Provisional anchors:
>
> - Lindblad, G. (1976). On the generators of quantum dynamical semigroups. *Commun. Math. Phys.* 48(2), 119–130.
> - Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review* 78(1), 1–3.
> - Vovk, V., Gammerman, A., & Shafer, G. (2005). *Algorithmic Learning in a Random World.*
> - Bardes, A., et al. (2024). V-JEPA: latent video prediction for visual representation learning. arXiv:2404.08471.
> - Liu, H., et al. (2024). Improved baselines with visual instruction tuning. arXiv:2310.03744.
> - Cui, Y., & Ma, S. (2026). *World Models with Quantum-Information Substrates: A Lindblad-Form Formulation.* (Companion paper.)

---

## Notes for follow-up

- v0.2 of this draft: populate experimental sections after trained-perception-model release.
- v0.3 of this draft: incorporate calibration history aggregated across the first 100 user predictions.
- Submission target: arXiv first; CV / robotics venue for a tightened conference version once benchmark numbers stabilize.
- Strict-CI gating per master plan §15: no claim populated in v1.0 (camera-ready) without backing pipeline run + published metric.
