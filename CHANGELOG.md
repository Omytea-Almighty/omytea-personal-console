# Changelog

All notable changes to the Omytea Personal Future Console.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/) for
the public-facing version string (`_brand.BRAND_VERSION`).

## [Unreleased]

### Planned for v4.16 (founder direction post-H4 self-test)
- Wishful best-case branch + worst-case anchor presentation polish
- Branch drill-down UI
- Continuous probability distribution visualization (vs current discrete-branch view)
- USD pricing finalization
- Local/cloud data-boundary documentation in product UI

### Still gated on external resources (Tier 3 follow-on)
- Trained Omytea perception model (YOLO fine-tune) — requires GPU + labelled dataset
- Per-class accuracy benchmark — depends on trained model
- Streamlit Cloud persistent storage (SQLite → Postgres via env var) — `scripts/snapshot_predictions.py` is the lightweight unblocker; full Postgres swap remains a v4.16 sub-item
- iOS / Android via the Streamlit Cloud deploy (Path β) — mobile-browser works today via the live URL

## [0.4.0] — 2026-05-19

### Changed
- **Omytea quantum substrate is now an independent PyPI package.** `requirements.txt` installs `omytea-quantum-substrate>=0.1.1,<1.0` instead of carrying a vendored copy. The substrate lives at <https://github.com/Adonyth/omytea-quantum-substrate> and is published at <https://pypi.org/project/omytea-quantum-substrate/>.
- `scripts/prepare_public_release.py`: substrate vendor step is now **off by default** (legacy `--vendor-omytea` flag still available for pre-v0.4 workflow). Public dist tree no longer carries an `omytea/` subdirectory.

### Why
This closes WORK_PLAN_V415 M3. The substrate gets:
- Independent PyPI version + Zenodo DOI for paper citation
- A clear cite-able identity separate from the Console product
- Its own CI / release cadence (Trusted Publishing OIDC on tag push)
- Lower barrier for downstream users who want just the math, not the Streamlit app

### Migration

- **Users**: pull v0.4.0 source and `pip install -r requirements.txt` — pip fetches `omytea-quantum-substrate` from PyPI automatically. No code changes needed; import paths (`from omytea.quantum import ...`) are unchanged.
- **Devs in the WMDB monorepo**: editable install of WMDB no longer shadows PyPI substrate because requirements.txt now uses the PyPI name. Use a fresh venv when switching between vendored and PyPI modes.

## [0.3.4] — 2026-05-19

### Added
- `SECURITY.md` — supported versions + responsible-disclosure email + explicit threat model (loopback-only, no third-party transmission by default).
- `.github/ISSUE_TEMPLATE/bug_report.md` + `feature_request.md` — bug + feature templates with the project's scope-fit gates inline.
- `Makefile` — `make help` / `make test` / `make eval` / `make bundle` / `make docker` / `make snapshot` / `make real-e2e` / `make clean` / `make release-tarball`.
- Streamlit Cloud deploy live at <https://omytea-personal-console.streamlit.app> (matrix-build artefact pulled via OAuth from `share.streamlit.io`).
- `docs/papers/OMYTEA_VIDEO_CONSOLE_DRAFT.md` §6 populated with measured E2E timing on `samples/walking_demo.mp4` × llava:7b CPU-only (both 4-frame and 2-frame configurations hit 600s honest-fallback ceiling).
- `_brand.BRAND_LIVE_DEMO_URL` constant pointing at the Streamlit Cloud URL.

### Changed
- README headline now leads with the live-demo URL so anyone landing on the repo can try the app with zero install.
- Sidebar footer and main-pane footer both pull from `_brand.footer_markdown()` so the version + GitHub + privacy links stay in lockstep.

### Tests
- 491 passed (source) / 467 passed + 3 skipped (public-dist).

### Public repo
- Tag [v0.3.4](https://github.com/Adonyth/omytea-personal-console/releases/tag/v0.3.4) · commit `22df5dd`.

## [0.3.3] — 2026-05-19

### Added
- **Pre-built native binaries attached to the GitHub release**: `omytea-console-Darwin-arm64.tar.gz` (one-folder, 129 MB), `omytea-console-onefile-Darwin-arm64.gz` (single binary, 129 MB), `omytea-console-Linux-x86_64.tar.gz` (one-folder, 178 MB), `omytea-console-docker-arm64.tar.gz` (Docker image as `docker load`-able tarball, 275 MB). End users can now run the Console without any Python install.
- `Dockerfile` + `.dockerignore` — multi-stage Python 3.12 image with Streamlit + healthcheck + non-root runtime user.
- `scripts/snapshot_predictions.py` — dumps the SQLite predictions DB to portable JSON. Unblocks `DEPLOYMENT_GUIDE.md` §5 (ephemeral-filesystem persistence problem on Streamlit Cloud free tier).
- `.github/workflows/ci.yml` — pytest matrix (Python 3.11 / 3.12 / 3.13 on Ubuntu) + macOS + Linux PyInstaller bundle smoke build + paper-draft compliance lint with smarter context-aware entanglement-claim check.
- `CHANGELOG.md` (this file) — Keep-a-Changelog format covering every release.
- `CONTRIBUTING.md` — what fits / what doesn't / how to run / PR checklist.
- `scripts/real_e2e.py` — CLI for capturing real-LLM timings into `docs/papers/real_e2e_runs/<timestamp>.json` artefacts.

### Fixed
- `bootstrap_native.py` now correctly binds to `127.0.0.1` only (previous version bound to `0.0.0.0` — a local-network-exposure risk for desktop software). Env-var + `config.set_option` belt-and-suspenders for cross-version Streamlit behaviour.
- PyInstaller specs now `copy_metadata('streamlit')` so the bundle no longer dies at startup with `PackageNotFoundError`.

### Public repo
- Tag [v0.3.3](https://github.com/Adonyth/omytea-personal-console/releases/tag/v0.3.3) · commit `4b53539` (+ Linux bundle added post-tag).

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
