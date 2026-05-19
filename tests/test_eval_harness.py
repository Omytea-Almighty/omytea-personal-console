"""Tests for the pipeline-invariant eval harness (Tier 3 scaffolding).

These cover the metrics + synthetic-truth generator. The full
``run_eval`` CLI is exercised by a smoke test at the end that uses
the standard `_build_default_clips()` set.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


# --------------------------------------------------------------
# 1. SyntheticEntity / SyntheticClip
# --------------------------------------------------------------


def test_two_entity_crossing_basic_shape() -> None:
    clip = build_two_entity_crossing_clip(n_frames=10, rasterize=False)
    assert clip.n_frames == 10
    assert len(clip.entities) == 2
    assert clip.entities[0].entity_id == "A"
    assert clip.entities[1].entity_id == "B"
    # Each entity should have exactly n_frames trajectory entries
    assert len(clip.entities[0].per_frame_bbox) == 10
    assert len(clip.entities[1].per_frame_bbox) == 10


def test_two_entity_clip_a_moves_rightward() -> None:
    clip = build_two_entity_crossing_clip(n_frames=10, rasterize=False)
    a = clip.entities[0]
    first_x = a.per_frame_bbox[0][1]
    last_x = a.per_frame_bbox[-1][1]
    assert last_x > first_x, "A should move left → right"


def test_two_entity_clip_b_moves_leftward() -> None:
    clip = build_two_entity_crossing_clip(n_frames=10, rasterize=False)
    b = clip.entities[1]
    first_x = b.per_frame_bbox[0][1]
    last_x = b.per_frame_bbox[-1][1]
    assert last_x < first_x, "B should move right → left"


def test_rasterize_optional_when_opencv_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When OpenCV isn't installed, rasterize gracefully degrades."""
    import builtins
    original_import = builtins.__import__

    def block_cv2(name: str, *args: object, **kwargs: object) -> object:
        if name == "cv2":
            raise ImportError("simulated missing cv2")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_cv2)
    # Re-import the module so the new import block takes effect
    import importlib

    import eval.synthetic_truth as st_mod
    importlib.reload(st_mod)
    clip = st_mod.build_two_entity_crossing_clip(
        n_frames=4, rasterize=True,
    )
    assert clip.rasterized_jpegs == ()


# --------------------------------------------------------------
# 2. tracker_id_switches
# --------------------------------------------------------------


def test_tracker_id_switches_zero_for_perfect_tracking() -> None:
    """If truth and tracker IDs align perfectly each frame, switches=0."""
    truth = [
        [("A", 0.1, 0.5), ("B", 0.9, 0.5)],
        [("A", 0.2, 0.5), ("B", 0.8, 0.5)],
        [("A", 0.3, 0.5), ("B", 0.7, 0.5)],
    ]
    tracked = [
        [("track_A", 0.1, 0.5), ("track_B", 0.9, 0.5)],
        [("track_A", 0.2, 0.5), ("track_B", 0.8, 0.5)],
        [("track_A", 0.3, 0.5), ("track_B", 0.7, 0.5)],
    ]
    assert tracker_id_switches(tracked, truth) == 0


def test_tracker_id_switches_counts_flip() -> None:
    """One mid-stream ID flip should count as 1 switch per truth entity."""
    truth = [
        [("A", 0.1, 0.5)],
        [("A", 0.2, 0.5)],
        [("A", 0.3, 0.5)],
    ]
    tracked = [
        [("track_1", 0.1, 0.5)],
        [("track_2", 0.2, 0.5)],
        [("track_2", 0.3, 0.5)],
    ]
    assert tracker_id_switches(tracked, truth) == 1


def test_tracker_id_switches_empty_inputs() -> None:
    assert tracker_id_switches([], []) == 0


# --------------------------------------------------------------
# 3. coherence_monotonic_decay
# --------------------------------------------------------------


def test_coherence_monotonic_decay_pure_decay_is_one() -> None:
    """Strictly decreasing pair magnitudes → fraction = 1.0."""
    snapshots = [
        {"entries": [{"row": 0, "col": 1, "magnitude": 0.10}]},
        {"entries": [{"row": 0, "col": 1, "magnitude": 0.08}]},
        {"entries": [{"row": 0, "col": 1, "magnitude": 0.05}]},
    ]
    assert coherence_monotonic_decay(snapshots) == 1.0


def test_coherence_monotonic_decay_partial_increase() -> None:
    """One increase in a 4-tick series → 2/3 monotonic transitions."""
    snapshots = [
        {"entries": [{"row": 0, "col": 1, "magnitude": 0.10}]},
        {"entries": [{"row": 0, "col": 1, "magnitude": 0.08}]},
        {"entries": [{"row": 0, "col": 1, "magnitude": 0.12}]},  # increase!
        {"entries": [{"row": 0, "col": 1, "magnitude": 0.09}]},
    ]
    frac = coherence_monotonic_decay(snapshots)
    assert frac == pytest.approx(2 / 3, abs=1e-6)


def test_coherence_monotonic_decay_empty() -> None:
    assert coherence_monotonic_decay([]) == 1.0
    assert coherence_monotonic_decay([{"entries": []}]) == 1.0


# --------------------------------------------------------------
# 4. joint_cardinality_matches_cartesian
# --------------------------------------------------------------


def test_joint_cardinality_2_entities_3_each() -> None:
    assert joint_cardinality_matches_cartesian(9, [3, 3]) is True


def test_joint_cardinality_3_entities_3_each() -> None:
    assert joint_cardinality_matches_cartesian(27, [3, 3, 3]) is True


def test_joint_cardinality_mismatch_returns_false() -> None:
    assert joint_cardinality_matches_cartesian(8, [3, 3]) is False


def test_joint_cardinality_zero_entities() -> None:
    assert joint_cardinality_matches_cartesian(0, []) is True
    assert joint_cardinality_matches_cartesian(1, []) is False


# --------------------------------------------------------------
# 5. pmf_normalization_error
# --------------------------------------------------------------


def test_pmf_normalization_perfect() -> None:
    branches = [
        {"probability_prior": 0.4},
        {"probability_prior": 0.35},
        {"probability_prior": 0.25},
    ]
    assert pmf_normalization_error(branches) == pytest.approx(0.0, abs=1e-9)


def test_pmf_normalization_offby() -> None:
    branches = [
        {"probability_prior": 0.5},
        {"probability_prior": 0.4},
    ]
    assert pmf_normalization_error(branches) == pytest.approx(0.1, abs=1e-9)


def test_pmf_normalization_empty_is_full_error() -> None:
    assert pmf_normalization_error([]) == 1.0


# --------------------------------------------------------------
# 6. end_to_end_latency_seconds
# --------------------------------------------------------------


def test_latency_for_simple_callable() -> None:
    t = end_to_end_latency_seconds(lambda: sum(range(100)))
    assert 0 <= t < 1.0


def test_latency_for_raising_callable_is_inf() -> None:
    def boom() -> None:
        raise RuntimeError("oh no")
    assert end_to_end_latency_seconds(boom) == float("inf")


# --------------------------------------------------------------
# 7. run_eval CLI smoke test
# --------------------------------------------------------------


def test_run_eval_main_executes_without_error() -> None:
    """The CLI runner should print rows and exit 0 even with the
    substrate unavailable — failures are surfaced as 'pipeline_error'
    fields on the per-clip row, not raises."""
    from eval.run_eval import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main([])
    assert code == 0
    out = buf.getvalue()
    assert "eval harness" in out
    assert "two_entity_crossing" in out


def test_run_eval_json_mode_outputs_one_object_per_line() -> None:
    """JSON mode should emit valid JSON per line."""
    import json
    from eval.run_eval import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["--json"])
    assert code == 0
    lines = [l for l in buf.getvalue().strip().splitlines() if l]
    assert len(lines) >= 1
    for line in lines:
        json.loads(line)  # must parse
