# Changelog

All notable changes to the Omytea Personal Future Console.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/) for
the public-facing version string (`_brand.BRAND_VERSION`).

## [Unreleased]

### v0.4.2-dev arc — 2026-05-26 founder audit + measurement-loop bridge (iter 17–27)

Eleven autonomous iterations against the 2026-05-26 founder live-audit + the
product-thesis directive ("calibrated decision journal, not one-shot AI
future generator"). All six P0/P1 items shipped, plus the calibration-loop
bridge to the user's external calendar. End-to-end verified live on the
deploy (iter 27 walked the chip → submit → result-page → expander → .ics
flow; no bugs found).

- **Audit-item ships**
  - **P0.1**: Delete `console.omyteaai.com` CNAME (TLS-cert-mismatch dead
    domain) from both monorepo and mirror; GitHub repo `homepage_url`
    updated via `gh repo edit` from the dead `omyteaai.com` to the embed
    URL. (iter 18, 20)
  - **P0.2**: Force-collapse mobile sidebar on `max-width: 768px`;
    Streamlit's `initial_sidebar_state="auto"` doesn't reliably collapse
    on phone widths. (iter 18)
  - **P1.1**: Surface `?embed=true` as the canonical public URL. Defeats
    Streamlit Cloud's outer "Manage app" pill that an earlier inner-iframe
    JS hop could not reach (sandboxed-iframe origin issue). Live-verified
    `[data-testid="manage-app-button"]` returns NO_PILL on the embed URL.
    (iter 18, 20)
  - **P1.2**: Cold-start heatmap reads as preview, not result. Adds
    "EXAMPLE PREVIEW" badge in heat-head + drops cell opacity to 0.62 +
    softens card shadow; both gated by `body[data-mode="idle"]`. Real
    predictions render at full opacity, no badge. (iter 19)
  - **P1.3**: Fold quantum machinery (`ρ_ab` off-diagonal + Lindblad
    coherence-decay chart with γ=0.05/month copy) into a default-closed
    `Technical details · joint structure & coherence decay` expander. The
    primary result-page path stays story → branches → evidence → revisit.
    (iter 18)
  - **P1.4 trio — "Why this probability?" per-branch reveal**. The
    largest remaining ask, shipped in three phases:
    - Phase 1: structural expander surfacing `key_uncertainty_driver` +
      `depends_on_decision` + honest fallback caption when neither is set.
      (iter 21)
    - Phase 2: real driver list filtered from `recommended_evidence` by
      `target_branch == branch.label`, rendering up to 3 top items as
      "**{evidence_label}** — _+Npp expected shift_". (iter 22)
    - Phase 3: per-branch confidence tier in the meta line via honest
      qualitative proxy (≥2 evidence → "well-calibrated", 1 →
      "single-source", 0 → "soft estimate"), routed through i18n × 4
      locales. (iter 25, 26)
- **Heatmap legibility**: Branch labels now read in full where space
  allows — widened left gutter `PADX_L: 96 → 124`, raised truncation cap
  `12 → 18` characters, removed the redundant rotated "outcome branch"
  axis caption (the section title above already names what rows are).
  (iter 17)
- **Measurement-update bridge — .ics calendar export**. Direct delivery
  on the founder product thesis that the value isn't a one-shot
  prediction but the user coming back to score it. Adds a "📥 Add
  reminder to my calendar (.ics)" button next to the existing "Come back
  in N months" reminder. RFC 5545 VCALENDAR/VEVENT, UID derives from
  prediction_id (re-downloading updates the existing event, no
  duplicates), DESCRIPTION + URL deep-link back to `BRAND_PUBLIC_URL`.
  Result page now also shows the computed review month ("around August
  2026") rather than just the relative interval. (iter 23)
- **Tooling / infrastructure**
  - GitNexus index refreshed: 26,982 nodes / 45,837 edges / 578 clusters
    / 300 flows. Cerebrum learning logged: the post-commit "stale" warning
    fires after every commit by design; refresh cadence is
    once-per-major-arc, not per-iter. (iter 24)
  - 15 new regression tests across two files: `test_iter23_review_ics.py`
    (9 RFC-5545 contract tests for the calendar bridge) and
    `test_iter25_confidence_tier.py` (6 tier-selection + i18n
    contract tests). Plus `datetime.utcnow()` →
    `datetime.now(timezone.utc)` deprecation fix surfaced during the
    new tests. Suite count 692 → 707. (iter 24, 27)
- **Live-verification** (iter 27 walked the actual user flow): all
  ships above are confirmed working on the live demo with screenshots.

### v0.4.2-dev arc cont. — measurement-loop closed end-to-end (iter 31–37)

Seven autonomous iterations following the founder's round-2 audit
+ explicit product direction: "把 prediction ID → 日历提醒 → 3 个月
后回访 → 校准自己当初判断 做成最强主线 (PMF 候选, 不再是 UI 抛光)".
Closes the calibration loop end-to-end across two entry paths
(passive .ics calendar reminder + active in-app "Time to score"
banner), with both per-record diff truth and aggregate trend
visualization. The PMF-candidate arc the founder identified as
the value driver.

**The complete loop** (predict → reminder → return → score → see truth):

- **iter 31 — `?score=<id>` URL deep-link**. `_check_score_deeplink()`
  reads `st.query_params`, normalizes list/single-value Streamlit
  quirks, consumes the param on first read so reruns don't loop.
  `main()` short-circuits to `render_measurement_update(preloaded_…)`
  when the param is present. The `.ics` URL field now carries
  `?embed=true&score=<id>` so calendar-app "Open URL" actions
  drop the user directly into Measurement Update pre-loaded —
  zero friction between calendar tap and "I can score this now."

- **iter 32 — Per-prediction diff cards on Calibration History**.
  New `storage.list_recent_measurements_with_predictions()` JOINs
  `measurement_updates` ⋈ `predictions` and reconstructs the
  per-record story: top predicted branch + probability, actual
  outcome branch (best-effort from common
  `actual_outcome_json` keys), and crucially `prob_for_actual`
  — the probability the user gave at prediction time to the
  branch that **actually happened**. Single most decision-relevant
  number per record. Renders as cards under the existing aggregate
  metrics: "Predicted most likely: _X_ (60%); Actually happened: _Y_;
  **You gave it 15% in advance**." Empty-state copy upgraded to
  explain the loop instead of just "no measurements yet."

- **iter 33 — Brier-over-time trend chart**. Single-glance "are
  you getting more calibrated?" answer. `st.line_chart` of Brier
  per measurement, oldest→newest, with a directional summary at
  ≥6 measurements: compares early-third vs recent-third mean
  Brier and labels as "improving" / "regressing" / "flat" with
  the actual delta number. Honest threshold `|Δ| > 0.02` so
  noise doesn't trigger false claims.

- **iter 34 — Active "Time to score" landing banner**. Complement
  to the passive `.ics` reminder: when the user opens the app
  (for any reason — including a new prediction) and has predictions
  past their horizon date without a measurement, a top banner
  surfaces "📅 Time to score: <decision> — predicted N months ago.
  [Score now →]". Click writes `?score=<id>` + `st.rerun()` →
  same iter 31 path → user lands in Measurement Update pre-loaded.
  Two entry paths, one mechanism. New
  `storage.list_overdue_predictions()` does the LEFT JOIN ⊥ filter
  + parses human horizon strings ("3 months" / "1 year" /
  "6 weeks") via regex, defaults to 3 months when unparseable.

- **iter 35 — storage bugfix (`db_connect` / `user_input_json`)**.
  Iter 32 + 34's helpers referenced `_connect(db_path)` (no such
  function) and column `input_json` (real: `user_input_json`).
  `py_compile` and `import` passed clean — only a real DB query
  triggers `NameError`, so the Calibration History page + the
  "Time to score" banner would have crashed on first user hit.
  **Caught by 9 new regression tests** in
  `test_iter32_measurement_loop_storage.py`. Bug never reached
  production traffic. bug-038 logged.

- **iter 36 — live verification of iter 35 fix**. Navigated to
  Calibration History via the sidebar → page renders cleanly
  with the new empty-state copy + no traceback. Streamlit Cloud
  auto-hot-reload picked up the storage.py change without
  needing a manual reboot. Cerebrum-worthy learning: when
  Streamlit Cloud's kebab is uncooperative, fall back to
  "trust the auto-reload + verify by exercising the affected
  page."

- **iter 37 — `_check_score_deeplink()` contract locked**. 7
  regression tests in `test_iter31_score_deeplink.py` covering
  absent param, present id, consume-on-first-read, list-form
  values, empty-string, whitespace strip, UUID round-trip. Same
  risk class as iter 35: a future refactor could silently break
  the measurement-loop's most critical hop with no compile-time
  signal. The contract is now pinned.

**Test count**: 717 → 724 across the cont. arc (+7 in iter 37);
combined with iter 35's +9 the measurement-loop arc added 16
regression tests, all green. Total suite 724/724 with iter 35
bug-038 caught + fixed before production traffic.

**GitNexus index** refreshed at end-of-arc (iter 37): 27,112
nodes / 46,094 edges / 583 clusters / 300 flows.

**Cerebrum learnings** logged:
- Streamlit's flaky kebab UI: fall back to `?embed=true` page
  navigation + Streamlit's auto-reload.
- Storage helpers MUST have `tmp_path`-fixture round-trip tests
  before shipping — pure compile/import doesn't catch wrong DB
  API references.
- Per-helper contract tests for measurement-loop entry points
  prevent the iter 35 / iter 37 class of silent break.

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
