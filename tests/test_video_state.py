"""Tests for video_state.py — entity hypothesis bundles + joint
wavefunction construction + Lindblad evolution.

Uses real substrate when available; falls back gracefully when not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _ensure_non_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Substrate tests need real Omytea — clear mock env."""
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)


omytea_importable = True
try:
    import omytea.quantum  # noqa: F401
    import omytea.joint_belief  # noqa: F401
    import omytea.dynamics.lindblad  # noqa: F401
except ImportError:
    omytea_importable = False


from video_state import (  # noqa: E402
    EntityHypothesisBundle,
    _estimate_velocity_per_frame,
    build_entity_hypothesis_bundles,
    build_joint_wavefunction,
    evolve_entity_joint,
)


# ----- _estimate_velocity_per_frame -----


def test_velocity_zero_for_singleton_trajectory() -> None:
    assert _estimate_velocity_per_frame([(0, 0.5, 0.5, 0.1)]) == (0.0, 0.0)


def test_velocity_zero_for_empty_trajectory() -> None:
    assert _estimate_velocity_per_frame([]) == (0.0, 0.0)


def test_velocity_positive_x() -> None:
    traj = [(0, 0.2, 0.5, 0.1), (10, 0.8, 0.5, 0.1)]
    vx, vy = _estimate_velocity_per_frame(traj)
    assert vx == pytest.approx(0.06)  # (0.8-0.2)/10
    assert vy == pytest.approx(0.0)


def test_velocity_positive_y() -> None:
    traj = [(0, 0.5, 0.2, 0.1), (5, 0.5, 0.7, 0.1)]
    vx, vy = _estimate_velocity_per_frame(traj)
    assert vx == pytest.approx(0.0)
    assert vy == pytest.approx(0.1)


def test_velocity_handles_same_frame_indices() -> None:
    """If both observations are at frame 0 (degenerate), df is
    clamped to 1 to avoid div-by-zero."""
    traj = [(0, 0.2, 0.2, 0.1), (0, 0.3, 0.3, 0.1)]
    vx, vy = _estimate_velocity_per_frame(traj)
    assert vx == pytest.approx(0.1)  # (0.3-0.2)/1
    assert vy == pytest.approx(0.1)


# ----- build_entity_hypothesis_bundles -----


def test_bundle_skips_empty_trajectory() -> None:
    entities = [{"object_id": "e1", "label": "x", "trajectory": []}]
    assert build_entity_hypothesis_bundles(entities) == []


def test_bundle_one_entity_produces_3_hypotheses() -> None:
    entities = [{
        "object_id": "e1",
        "label": "person",
        "trajectory": [(0, 0.3, 0.5, 0.1), (5, 0.5, 0.5, 0.1)],
        "confidence": 0.9,
    }]
    bundles = build_entity_hypothesis_bundles(entities)
    assert len(bundles) == 1
    b = bundles[0]
    assert b.entity_id == "e1"
    assert b.label == "person"
    assert len(b.hypothesis_ids) == 3
    assert len(b.hypothesis_weights) == 3
    assert sum(b.hypothesis_weights) == pytest.approx(1.0)


def test_bundle_caps_at_max_entities() -> None:
    entities = [
        {"object_id": f"e{i}", "label": "x",
         "trajectory": [(0, 0.5, 0.5, 0.1), (1, 0.5, 0.5, 0.1)],
         "confidence": 0.8}
        for i in range(10)
    ]
    bundles = build_entity_hypothesis_bundles(entities, max_entities=3)
    assert len(bundles) == 3


def test_bundle_stationary_entity_weights_decelerate() -> None:
    """Near-zero velocity → weight redistributed toward decelerate."""
    entities = [{
        "object_id": "e1", "label": "x",
        "trajectory": [(0, 0.5, 0.5, 0.1), (5, 0.5, 0.5, 0.1)],
        "confidence": 0.8,
    }]
    bundles = build_entity_hypothesis_bundles(entities)
    # weights = (continue, accelerate, decelerate)
    assert bundles[0].hypothesis_weights[2] >= 0.3


def test_bundle_fast_entity_weights_continue() -> None:
    """Fast velocity → weight redistributed toward continue + accelerate."""
    entities = [{
        "object_id": "e1", "label": "x",
        "trajectory": [(0, 0.2, 0.5, 0.1), (5, 0.6, 0.5, 0.1)],
        "confidence": 0.8,
    }]
    bundles = build_entity_hypothesis_bundles(entities)
    # speed = (0.4/5) = 0.08 > 0.05 threshold
    assert bundles[0].hypothesis_weights[0] >= 0.5  # continue
    assert bundles[0].hypothesis_weights[1] >= 0.25  # accelerate


def test_bundle_hypothesis_ids_include_entity_id() -> None:
    entities = [{
        "object_id": "track_42",
        "label": "x",
        "trajectory": [(0, 0.5, 0.5, 0.1), (1, 0.5, 0.5, 0.1)],
        "confidence": 0.7,
    }]
    bundles = build_entity_hypothesis_bundles(entities)
    assert "track_42" in bundles[0].hypothesis_ids[0]
    assert "continue" in bundles[0].hypothesis_ids[0]
    assert "accelerate" in bundles[0].hypothesis_ids[1]
    assert "decelerate" in bundles[0].hypothesis_ids[2]


# ----- build_joint_wavefunction + evolve_entity_joint -----


pytestmark_substrate = pytest.mark.skipif(
    not omytea_importable,
    reason="omytea + omytea.dynamics not installed; substrate tests skip.",
)


@pytestmark_substrate
def test_jwf_empty_bundles_returns_none() -> None:
    assert build_joint_wavefunction([]) is None


@pytestmark_substrate
def test_jwf_single_entity_3_hypotheses() -> None:
    entities = [{
        "object_id": "e1", "label": "person",
        "trajectory": [(0, 0.3, 0.5, 0.1), (5, 0.5, 0.5, 0.1)],
        "confidence": 0.9,
    }]
    bundles = build_entity_hypothesis_bundles(entities)
    jwf = build_joint_wavefunction(bundles)
    # 1 entity × 3 hypotheses = 3 joint cells
    assert jwf is not None
    assert len(jwf.hypotheses) == 3


@pytestmark_substrate
def test_jwf_two_entities_9_joint_cells() -> None:
    entities = [
        {"object_id": "e1", "label": "p1",
         "trajectory": [(0, 0.3, 0.5, 0.1), (5, 0.5, 0.5, 0.1)],
         "confidence": 0.9},
        {"object_id": "e2", "label": "p2",
         "trajectory": [(0, 0.6, 0.5, 0.1), (5, 0.8, 0.5, 0.1)],
         "confidence": 0.85},
    ]
    bundles = build_entity_hypothesis_bundles(entities)
    jwf = build_joint_wavefunction(bundles)
    assert jwf is not None
    # 2 entities × 3 hypotheses = 9 joint cells
    assert len(jwf.hypotheses) == 9


@pytestmark_substrate
def test_jwf_offdiagonals_exist_for_multi_entity() -> None:
    """For ≥2 entities, off-diagonal couplings should be generated
    based on 'continue + continue' overlaps and 'accel-decel' anti-
    overlaps."""
    entities = [
        {"object_id": "e1", "label": "p1",
         "trajectory": [(0, 0.3, 0.5, 0.1), (5, 0.5, 0.5, 0.1)],
         "confidence": 0.9},
        {"object_id": "e2", "label": "p2",
         "trajectory": [(0, 0.6, 0.5, 0.1), (5, 0.8, 0.5, 0.1)],
         "confidence": 0.85},
    ]
    bundles = build_entity_hypothesis_bundles(entities)
    jwf = build_joint_wavefunction(bundles)
    assert jwf is not None
    # Off-diagonals come in Hermitian pairs (both (i,j) and (j,i))
    assert len(jwf.off_diagonal_couplings) > 0
    assert len(jwf.off_diagonal_couplings) % 2 == 0


@pytestmark_substrate
def test_evolve_returns_skipped_for_none_jwf() -> None:
    out = evolve_entity_joint(None)
    assert out["skipped"] is True


@pytestmark_substrate
def test_evolve_produces_snapshots() -> None:
    entities = [
        {"object_id": "e1", "label": "p1",
         "trajectory": [(0, 0.3, 0.5, 0.1), (5, 0.5, 0.5, 0.1)],
         "confidence": 0.9},
        {"object_id": "e2", "label": "p2",
         "trajectory": [(0, 0.6, 0.5, 0.1), (5, 0.8, 0.5, 0.1)],
         "confidence": 0.85},
    ]
    bundles = build_entity_hypothesis_bundles(entities)
    jwf = build_joint_wavefunction(bundles)
    out = evolve_entity_joint(jwf, time_horizon_steps=4)
    assert out["skipped"] is False
    assert len(out["snapshots"]) == 5  # tick 0..4
    # Off-diagonal magnitudes should decay over time (decoherence)
    initial_mags = [e["magnitude"] for e in out["snapshots"][0]["entries"]]
    final_mags = [e["magnitude"] for e in out["snapshots"][-1]["entries"]]
    # At least one entry should show decay
    for i, m0 in enumerate(initial_mags):
        if m0 > 0.05:
            assert final_mags[i] < m0 + 1e-9
