"""Pipeline-invariant evaluation metrics.

These metrics compute correctly *regardless* of which perception
model is in use. They're the right infrastructure to land before a
trained perception model arrives:

  - ``tracker_id_switches`` — counts how many times a ground-truth
    entity gets a *different* tracker-assigned ID frame-to-frame.
    Lower is better (0 = perfect tracking).
  - ``coherence_monotonic_decay`` — fraction of per-pair tick-to-tick
    off-diagonal magnitude transitions that are monotonically
    decreasing (or staying equal). For a dissipative Lindblad
    operator we expect 1.0 (always decaying).
  - ``joint_cardinality_matches_cartesian`` — boolean: does the
    JointWaveFunction cardinality match the expected Cartesian
    product of per-entity hypothesis counts?
  - ``pmf_normalization_error`` — |Σ branch.probability − 1.0|.
  - ``end_to_end_latency_seconds`` — wall-clock for the
    ingest → compile → evolve loop.

Each metric is a pure function of its inputs. Tests live in
``tests/test_eval_harness.py``.
"""

from __future__ import annotations

import math
import time
from typing import Any


def tracker_id_switches(
    tracked_per_frame: list[list[tuple[str, float, float]]],
    truth_per_frame: list[list[tuple[str, float, float]]],
    distance_threshold_norm: float = 0.15,
) -> int:
    """Count how many times a truth entity's matched tracker ID
    switches frame-to-frame.

    For each truth entity at each frame, we find the nearest tracked
    detection (by normalized centroid distance). If a truth entity's
    matched ID changes from frame N to frame N+1, that counts as 1
    switch. Unmatched frames are skipped.

    Args:
      tracked_per_frame: list (frames) of list (detections) of
        (tracker_assigned_id, cx_norm, cy_norm).
      truth_per_frame: same shape but with ground-truth entity_ids.
      distance_threshold_norm: max normalized distance for a match;
        beyond this, the truth entity is considered unmatched.

    Returns:
      Integer count of ID switches across all truth entities + frames.
    """
    if not truth_per_frame or not tracked_per_frame:
        return 0

    n = min(len(truth_per_frame), len(tracked_per_frame))
    # Build truth_id → list of (frame_idx, matched_tracker_id_or_None).
    matches: dict[str, list[str | None]] = {}

    for frame_idx in range(n):
        truth_dets = truth_per_frame[frame_idx]
        tracked_dets = tracked_per_frame[frame_idx]
        for truth_id, tx, ty in truth_dets:
            best_id: str | None = None
            best_dist = distance_threshold_norm
            for trk_id, kx, ky in tracked_dets:
                d = math.hypot(tx - kx, ty - ky)
                if d < best_dist:
                    best_dist = d
                    best_id = trk_id
            matches.setdefault(truth_id, []).append(best_id)

    switches = 0
    for truth_id, chain in matches.items():
        prev: str | None = None
        for tid in chain:
            if tid is None:
                continue
            if prev is not None and tid != prev:
                switches += 1
            prev = tid
    return switches


def coherence_monotonic_decay(
    snapshots: list[dict[str, Any]],
) -> float:
    """Fraction of per-pair tick-to-tick magnitude transitions that
    are monotonic-decay (new ≤ old).

    Args:
      snapshots: list of dicts with key 'entries', each entry having
        'row', 'col', 'magnitude'. Same shape ``video_state.evolve_
        entity_joint`` returns.

    Returns:
      Float in [0, 1]. 1.0 = always decaying (ideal Lindblad).
      Returns 1.0 trivially when there are no transitions to score.
    """
    if not snapshots or len(snapshots) < 2:
        return 1.0

    # Build per-pair magnitude series across snapshots.
    pair_series: dict[tuple[int, int], list[float]] = {}
    for snap in snapshots:
        for entry in snap.get("entries", []):
            key = (min(entry["row"], entry["col"]),
                   max(entry["row"], entry["col"]))
            pair_series.setdefault(key, []).append(float(entry["magnitude"]))

    total = 0
    monotonic = 0
    for key, series in pair_series.items():
        for i in range(1, len(series)):
            total += 1
            if series[i] <= series[i - 1] + 1e-9:
                monotonic += 1
    if total == 0:
        return 1.0
    return monotonic / total


def joint_cardinality_matches_cartesian(
    actual_joint_count: int,
    per_entity_hypothesis_counts: list[int],
) -> bool:
    """Check |JointWF| == product of per-entity |hypotheses|.

    A pure-Cartesian-product joint state has this property; our
    pipeline should preserve it (off-diagonal couplings don't add
    new hypotheses, just correlations between existing ones).
    """
    if not per_entity_hypothesis_counts:
        return actual_joint_count == 0
    expected = 1
    for k in per_entity_hypothesis_counts:
        expected *= max(k, 0)
    return actual_joint_count == expected


def pmf_normalization_error(
    branches: list[dict[str, Any]],
    probability_key: str = "probability_prior",
) -> float:
    """|Σ probability − 1.0| across all branches.

    Substrate guarantees the compiled program normalizes to 1; this
    metric is the regression-watch line.
    """
    if not branches:
        return 1.0
    total = sum(float(b.get(probability_key, 0.0)) for b in branches)
    return abs(total - 1.0)


def end_to_end_latency_seconds(callable_fn: Any) -> float:
    """Wall-clock for one invocation of ``callable_fn``.

    Returns infinity if the callable raises (so a regression that
    breaks the pipeline doesn't show as a 'fast' metric)."""
    t0 = time.perf_counter()
    try:
        callable_fn()
    except Exception:
        return float("inf")
    return time.perf_counter() - t0


__all__ = [
    "tracker_id_switches",
    "coherence_monotonic_decay",
    "joint_cardinality_matches_cartesian",
    "pmf_normalization_error",
    "end_to_end_latency_seconds",
]
