# Changelog

All notable changes to the Omytea Personal Future Console.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/) for
the public-facing version string (`_brand.BRAND_VERSION`).

## [Unreleased]

### Planned for Tier 3 follow-on cycles
- Trained Omytea perception model (YOLO fine-tune) — requires GPU + labelled dataset
- Per-class accuracy benchmark (depends on trained model)
- Streamlit Cloud deploy with persistent storage (SQLite → Postgres via env var)
- iOS / Android via the Streamlit Cloud deploy (Path β)
- Animated future-flow visualization

## [0.3.2] — 2026-05-19

### Added
- `omytea-console-onefile.spec` — PyInstaller variant that produces a single binary instead of the one-folder bundle. Trade-off: slower first launch (~3-8s vs. ~1-2s), single artifact to ship.
- `scripts/build_native.sh` extended with `--onefile` / `--folder` flags.
- `docs/papers/OMYTEA_VIDEO_CONSOLE_DRAFT.md` — arXiv paper draft skeleton (v0.1). Abstract + 9 section outlines + honest "what we are *not* measuring yet" subsection. CC BY 4.0.

### Tests
- +4 native_bundle tests for one-folder vs onefile spec invariants + build-script flag coverage.

### Public repo
- Tag [v0.3.2](https://github.com/Adonyth/omytea-personal-console/releases/tag/v0.3.2) · commit `394129a`.

## [0.3.1] — 2026-05-19

### Added
- Mode 6 **Capture & predict** panel. Freezes the latest webcam frames + live entity tracks and runs them through the same `compile_scene_query → ConsoleResult` pipeline that Mode 5 uses. Persisted via `storage` so the Measurement update tab can pick up the prediction later.
- `WebcamSession` ring-buffered JPEG frame cache (default 3 frames at 70-quality) + `snapshot_for_prediction()` method.
- `eval/` package — pipeline-invariant evaluation metrics that compute regardless of which perception model is in use:
  - `tracker_id_switches`, `coherence_monotonic_decay`, `joint_cardinality_matches_cartesian`, `pmf_normalization_error`, `end_to_end_latency_seconds`
- `python -m eval.run_eval` CLI (pretty + `--json`).
- `eval/README.md` — what each metric means + add-a-clip / add-a-metric recipes.

### Tests
- +9 webcam capture-and-predict + frame buffer.
- +21 eval-harness metrics + CLI smoke.

### Public repo
- Tag [v0.3.1](https://github.com/Adonyth/omytea-personal-console/releases/tag/v0.3.1) · commit `fa1f9e1`.

## [0.3.0] — 2026-05-19

### Added
- **Mode 6 — Live webcam** via streamlit-webrtc. Frames go through the substrate's `MotionFallbackDetector` + `IoUTracker` on a background thread; every 8 frames (tunable) the joint wavefunction rebuilds and is evolved under the Lindblad operator. The off-diagonal coherence-decay chart updates live. Nothing leaves your machine.
- **PyInstaller native bundle** — `omytea-console.spec` + `scripts/build_native.sh` + `bootstrap_native.py` launcher. Builds a self-contained folder that launches Streamlit bound to 127.0.0.1 and opens the browser.
- **`_brand.py`** — single source of truth for the version string, tagline, repo URL, per-mode emoji palette. Wired into sidebar + page footer so links stay in lockstep with the release tag.

### Tests
- +20 webcam_stream.
- +7 native_bundle.
- +8 brand.

### Public repo
- Tag [v0.3.0](https://github.com/Adonyth/omytea-personal-console/releases/tag/v0.3.0) · commit `cb3d643`.

## [0.2.0] — 2026-05-18

### Added
- **Mode 5 — Video query**. Upload a short video (mp4/mov/webm); the system samples keyframes, runs local perception (substrate's tracked-entity detector), asks the local vision LLM (LLaVA via Ollama) to read the scene, and emits calibrated future-scenario branches.
- **`OllamaVisionBackend`** — image+text via Ollama's `/api/chat`. Default model `llava:7b`; configurable via `OLLAMA_VISION_MODEL`.
- **`video_ingest.py`** — wraps substrate perception (`MotionFallbackDetector` + `IoUTracker`) for uploaded video files.
- **`video_state.py`** — per-entity hypothesis bundles → JointWaveFunction → Lindblad evolution over off-diagonal coherences.
- **`visualization.py`** — bounding-box + trajectory overlays via PIL.
- **`samples/walking_demo.mp4`** — 5-second synthetic bundled fixture for first-run tour.
- **`scripts/install.sh`** — one-shot installer with Ollama probe + next-step guidance.
- **`docs/USER_WALKTHROUGH.md`** — step-by-step first-time guide.

### Public repo
- Initial Apache 2.0 release on `Adonyth/omytea-personal-console`.
- Tag [v0.2.0](https://github.com/Adonyth/omytea-personal-console/releases/tag/v0.2.0) · commit `5156e19`.
- Custom domain `console.omyteaai.com` wired via GitHub Pages + Cloudflare.

## Releases & how to upgrade

| Version | Date | Highlight |
|---|---|---|
| 0.3.2 | 2026-05-19 | Single-binary distribution + paper draft skeleton |
| 0.3.1 | 2026-05-19 | Mode 6 capture-and-predict + eval harness |
| 0.3.0 | 2026-05-19 | Mode 6 live webcam + PyInstaller bundle + branding |
| 0.2.0 | 2026-05-18 | Mode 5 video query + local vision LLM + quantum operator |

Upgrade: `git pull && pip install -r requirements.txt --upgrade`. No DB migrations across these versions.
