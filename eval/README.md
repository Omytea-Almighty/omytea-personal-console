# Personal Future Console — Eval Harness

Scaffolding for quantitative evaluation of the perception → joint-wavefunction → Lindblad-evolution pipeline.

**What this is for**: the pipeline has invariants that *must* hold regardless of which perception model is plugged in (motion fallback, YOLO, future trained Omytea model). The harness measures those invariants so we can ship perception-model changes with a clear before/after delta.

**What this is NOT**: an accuracy benchmark against real-world video. Real-world accuracy needs a trained perception model + labelled dataset, both of which are Tier 3 follow-on work per `DELIVERABLE_PLAN.md`. The accuracy harness will land alongside the trained model.

## Run

```bash
# Pretty-printed table
python -m eval.run_eval

# JSON-per-clip (pipe to jq if you want)
python -m eval.run_eval --json
```

Output one row per bundled synthetic clip with these columns:

| Metric | Meaning | Good |
|---|---|---|
| `tracker_id_switches` | Times the matched tracker-ID flipped frame-to-frame for a truth entity | 0 = perfect |
| `coherence_monotonic_decay` | Fraction of per-pair magnitude transitions that decreased | 1.0 = ideal Lindblad |
| `joint_cardinality_matches_cartesian` | `\|JointWaveFunction\|` equals product of per-entity hypothesis counts | `True` |
| `pmf_normalization_error` | `\|Σ branch.probability − 1.0\|` | ≤ 1e-3 |
| `end_to_end_latency_seconds` | Wall-clock for one ingest → compile → evolve loop | — |

## Add a new clip

Add a `build_*_clip()` factory to `synthetic_truth.py`. It returns a `SyntheticClip` with ground-truth per-frame bounding boxes. Add the factory to `_build_default_clips()` in `run_eval.py` and the new clip joins the harness automatically.

## Add a new metric

Add a pure function to `metrics.py` (no module-level imports of the substrate — keep it lean). Document the "what good looks like" expectation. Update `_run_one_clip()` in `run_eval.py` to compute + emit the new metric, and add a test under `tests/test_eval_harness.py`.

## When the trained perception model arrives

Replace the synthetic-tracker substitute in `_run_one_clip()` (the block where `tracked_per_frame` is set from `truth_per_frame`) with the real tracker's per-frame output. The harness will then report real `tracker_id_switches` instead of the trivial 0-by-construction value.
