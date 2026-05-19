"""Quantitative evaluation harness for the Personal Future Console.

This package is the Tier 3 scaffolding hook from
``DELIVERABLE_PLAN.md``. It exists so that *when* a trained perception
model (YOLO fine-tune, custom architecture, etc.) lands, the test +
benchmark surfaces are already in place — no scrambling to invent a
fair-comparison harness under deadline pressure.

What ships now (no trained model required):

  - ``synthetic_truth`` — programmatic generator for tiny synthetic
    video sequences with known ground-truth entity trajectories.
  - ``metrics`` — pipeline-invariant metrics that compute correctly
    regardless of which detector / perception model is in use:
       * ``tracker_id_switches`` — count of times a ground-truth
         entity's tracker-assigned ID flips frame-to-frame.
       * ``coherence_monotonic_decay`` — fraction of per-pair
         off-diagonal magnitudes that decreased (or stayed equal)
         from one Lindblad tick to the next. Should be ≥ 1.0 for a
         dissipative open-system operator.
       * ``joint_cardinality_matches_cartesian`` — boolean: does
         |JointWaveFunction.hypotheses| equal N_entities ^ k_hyps?
       * ``pmf_normalization_error`` — |Σ probability − 1.0| for
         the compiled branches.
       * ``end_to_end_latency_seconds`` — wall-clock for the
         ingest → compile → evolve loop on one synthetic clip.

  - ``run_eval`` — CLI runner that prints a one-row-per-dataset
    metric table. Can be wired into CI on a follow-up commit.

Why pipeline-invariants and not accuracy metrics yet?

Accuracy needs (a) labelled real-world video and (b) a trained
perception model. Neither is in scope this cycle (DELIVERABLE_PLAN
Tier 3 explicitly defers the trained model to a follow-up). The
invariants below are the right *infrastructure* to add now — they
keep the pipeline honest as the substrate evolves, and they slot
straight into a model comparison harness once a model lands.
"""

from eval.metrics import (
    coherence_monotonic_decay,
    end_to_end_latency_seconds,
    joint_cardinality_matches_cartesian,
    pmf_normalization_error,
    tracker_id_switches,
)
from eval.synthetic_truth import (
    SyntheticClip,
    SyntheticEntity,
    build_two_entity_crossing_clip,
)

__all__ = [
    "SyntheticClip",
    "SyntheticEntity",
    "build_two_entity_crossing_clip",
    "tracker_id_switches",
    "coherence_monotonic_decay",
    "joint_cardinality_matches_cartesian",
    "pmf_normalization_error",
    "end_to_end_latency_seconds",
]
