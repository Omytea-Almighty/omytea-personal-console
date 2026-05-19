"""Tests for the Tier 2 live-webcam streaming module.

These exercise ``webcam_stream.py``'s rolling-window perception →
joint quantum-state-rebuild pipeline without requiring streamlit-
webrtc (we drive ``on_frame`` directly with synthetic detections via
monkey-patched substrate handles).

Master plan §15 Rule #11 — these tests run fully offline; no LLM is
called; no network access needed.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import webcam_stream
from webcam_stream import (
    LiveEntity,
    WebcamSession,
    WebcamSnapshot,
    _extract_centroid,
    _try_import_substrate,
    _try_streamlit_webrtc,
    _velocity_estimate,
)


# --------------------------------------------------------------
# 1. Free-helper unit tests
# --------------------------------------------------------------


def test_extract_centroid_xywh_form() -> None:
    """Newer substrate BoundingBox: (x, y, width, height) — top-left."""
    box = SimpleNamespace(x=10.0, y=20.0, width=40.0, height=80.0)
    det = SimpleNamespace(bbox=box, confidence=0.7, label="person")
    cx, cy, area, conf, label = _extract_centroid(det, 100, 200)
    assert cx == pytest.approx((10 + 20) / 100)  # (10 + 40/2) / 100 = 30/100
    assert cy == pytest.approx((20 + 40) / 200)  # (20 + 80/2) / 200 = 60/200
    assert area == pytest.approx((40 * 80) / (100 * 200))
    assert conf == pytest.approx(0.7)
    assert label == "person"


def test_extract_centroid_x1y1x2y2_form() -> None:
    """Older substrate BoundingBox: (x1, y1, x2, y2) — corners."""
    box = SimpleNamespace(x1=10.0, y1=20.0, x2=50.0, y2=100.0)
    det = SimpleNamespace(bounding_box=box, confidence=0.4, label="blob")
    cx, cy, area, conf, label = _extract_centroid(det, 200, 400)
    assert cx == pytest.approx(30.0 / 200)
    assert cy == pytest.approx(60.0 / 400)
    assert area == pytest.approx((40 * 80) / (200 * 400))


def test_extract_centroid_no_bbox_returns_nones() -> None:
    det = SimpleNamespace(confidence=0.9, label="x")
    cx, cy, area, conf, label = _extract_centroid(det, 100, 100)
    assert cx is None
    assert cy is None


def test_velocity_estimate_short_trajectory() -> None:
    assert _velocity_estimate([]) == (0.0, 0.0)
    assert _velocity_estimate([(0, 0.5, 0.5, 0.04)]) == (0.0, 0.0)


def test_velocity_estimate_linear_motion() -> None:
    # 4 frames apart, moved 0.4 in x: vx = 0.4/4 = 0.1 per frame
    traj = [
        (0, 0.1, 0.5, 0.04),
        (2, 0.3, 0.5, 0.04),
        (4, 0.5, 0.5, 0.04),
    ]
    vx, vy = _velocity_estimate(traj)
    assert vx == pytest.approx(0.1, abs=1e-6)
    assert vy == pytest.approx(0.0, abs=1e-6)


def test_velocity_estimate_uses_tail_window() -> None:
    """If the trajectory has 20 points but motion is uniform, velocity
    should be the same as the per-step rate regardless of window."""
    traj = [(i, i * 0.01, 0.5, 0.04) for i in range(20)]
    vx, vy = _velocity_estimate(traj)
    assert vx == pytest.approx(0.01, abs=1e-6)
    assert vy == pytest.approx(0.0, abs=1e-6)


# --------------------------------------------------------------
# 2. streamlit-webrtc probe
# --------------------------------------------------------------


def test_try_streamlit_webrtc_returns_a_tuple() -> None:
    """Even when streamlit-webrtc isn't installed, the probe returns
    a (None, reason) tuple — never raises."""
    mod, err = _try_streamlit_webrtc()
    # Either the module is installed or we get a graceful reason.
    assert (mod is not None and err is None) or (
        mod is None and isinstance(err, str) and "streamlit-webrtc" in err
    )


# --------------------------------------------------------------
# 3. WebcamSession construction defaults
# --------------------------------------------------------------


def test_session_defaults() -> None:
    s = WebcamSession()
    assert s.max_trajectory_len == 30
    assert s.rebuild_every_n_frames == 8
    assert s.max_entities == 3
    assert s.detect_every_n_frames == 1
    snap = s.snapshot()
    assert snap.frames_processed == 0
    assert snap.n_entities == 0


def test_session_custom_params() -> None:
    s = WebcamSession(
        max_trajectory_len=12,
        rebuild_every_n_frames=4,
        max_entities=2,
        detect_every_n_frames=2,
        decoherence_rate=0.15,
        horizon_steps=10,
    )
    assert s.max_trajectory_len == 12
    assert s.rebuild_every_n_frames == 4
    assert s.max_entities == 2
    assert s.decoherence_rate == 0.15


# --------------------------------------------------------------
# 4. WebcamSession.on_frame in mock mode — substrate is unavailable,
#    so frames count but no entities are built.
# --------------------------------------------------------------


def test_on_frame_mock_mode_counts_but_no_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")
    s = WebcamSession()
    s.on_frame(image_data=None, frame_width=320, frame_height=240)
    s.on_frame(image_data=None, frame_width=320, frame_height=240)
    snap = s.snapshot()
    assert snap.frames_processed == 2
    assert snap.n_entities == 0
    assert snap.available is False
    assert "mock_mode" in snap.reason or "substrate" in snap.reason.lower()


def test_reset_clears_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")
    s = WebcamSession()
    s.on_frame(image_data=None, frame_width=320, frame_height=240)
    s.on_frame(image_data=None, frame_width=320, frame_height=240)
    assert s.snapshot().frames_processed == 2
    s.reset()
    assert s.snapshot().frames_processed == 0


# --------------------------------------------------------------
# 5. With a stub substrate, frames produce tracked entities.
# --------------------------------------------------------------


class _StubBBox:
    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        self.x = x
        self.y = y
        self.width = w
        self.height = h


class _StubDet:
    def __init__(
        self, oid: str, x: float, y: float, w: float = 30.0, h: float = 40.0,
        conf: float = 0.6, label: str = "motion_blob",
    ) -> None:
        self.object_id = oid
        self.bbox = _StubBBox(x, y, w, h)
        self.confidence = conf
        self.label = label


def _install_stub_substrate(
    session: WebcamSession,
    detections_per_frame: list[list[_StubDet]],
) -> None:
    """Bypass the lazy substrate load and inject a deterministic
    stub detector + tracker. This lets us test the session's rolling
    state without the real substrate."""
    # Mark substrate as loaded so _ensure_substrate short-circuits
    session._substrate_loaded = True

    class StubDetector:
        def __init__(self) -> None:
            self._idx = 0

        def detect(self, envelope: object, image_data: object) -> list[_StubDet]:
            dets = detections_per_frame[
                min(self._idx, len(detections_per_frame) - 1)
            ]
            self._idx += 1
            return dets

    class StubTracker:
        def assign(
            self, envelope: object, raw_dets: list[_StubDet],
        ) -> list[_StubDet]:
            # Pass-through — the stub _StubDet already has object_id.
            return raw_dets

    class StubFrameEnvelope:
        def __init__(self, **kwargs: object) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    session._detector = StubDetector()
    session._tracker = StubTracker()
    session._FrameEnvelope = StubFrameEnvelope


def test_on_frame_with_stub_substrate_builds_entity() -> None:
    s = WebcamSession(rebuild_every_n_frames=100)  # skip rebuild
    _install_stub_substrate(s, [
        [_StubDet("t1", x=10, y=10, w=20, h=30)],
        [_StubDet("t1", x=15, y=12, w=20, h=30)],
        [_StubDet("t1", x=20, y=14, w=20, h=30)],
    ])
    for _ in range(3):
        s.on_frame(image_data=None, frame_width=320, frame_height=240)
    snap = s.snapshot()
    assert snap.frames_processed == 3
    assert snap.n_entities == 1
    assert snap.entities_summary[0]["object_id"] == "t1"
    assert snap.entities_summary[0]["n_points"] == 3
    # Velocity should be positive in x (entity moved right)
    assert snap.entities_summary[0]["velocity_x"] > 0


def test_rolling_window_trim() -> None:
    """Trajectories longer than max_trajectory_len should be trimmed
    to the most recent N points."""
    s = WebcamSession(
        max_trajectory_len=5, rebuild_every_n_frames=100,
    )
    detections = [
        [_StubDet("t1", x=10 + i, y=10, w=20, h=30)]
        for i in range(20)
    ]
    _install_stub_substrate(s, detections)
    for _ in range(20):
        s.on_frame(image_data=None, frame_width=320, frame_height=240)
    snap = s.snapshot()
    assert snap.entities_summary[0]["n_points"] == 5


def test_stale_entity_gc() -> None:
    """Entities not seen in the last max_trajectory_len frames should
    be garbage-collected from the rolling state."""
    s = WebcamSession(
        max_trajectory_len=4, rebuild_every_n_frames=100,
    )
    # First 3 frames: entity t1. Then 8 frames: entity t2 only.
    # By the end, t1 hasn't been seen in 8 frames, > max_trajectory_len=4.
    detections = (
        [[_StubDet("t1", x=10, y=10)]] * 3
        + [[_StubDet("t2", x=50, y=50)]] * 8
    )
    _install_stub_substrate(s, detections)
    for _ in range(11):
        s.on_frame(image_data=None, frame_width=320, frame_height=240)
    snap = s.snapshot()
    ids = {e["object_id"] for e in snap.entities_summary}
    assert "t1" not in ids
    assert "t2" in ids


def test_max_entities_cap_in_snapshot() -> None:
    """When more entities are tracked than max_entities, snapshot
    returns only the top-N by track quality."""
    s = WebcamSession(max_entities=2, rebuild_every_n_frames=100)
    # Five concurrent entities with decreasing track lengths
    detections = []
    for f in range(10):
        per_frame = [_StubDet(f"t{k}", x=10 + k * 30, y=10 + k * 20) for k in range(5)]
        # Only the first 2 entities appear in every frame; the rest fade.
        if f >= 3:
            per_frame = per_frame[:2]
        detections.append(per_frame)
    _install_stub_substrate(s, detections)
    for _ in range(10):
        s.on_frame(image_data=None, frame_width=320, frame_height=240)
    snap = s.snapshot()
    assert len(snap.entities_summary) <= 2


def test_joint_rebuild_triggered_on_interval() -> None:
    """When rebuild_every_n_frames frames have passed, the joint
    snapshot's last_rebuild_at_frame should advance."""
    s = WebcamSession(rebuild_every_n_frames=2)
    detections = [
        [_StubDet("t1", x=10 + i, y=10, w=20, h=30)]
        for i in range(6)
    ]
    _install_stub_substrate(s, detections)

    # Without a real substrate, the rebuild attempt will mark
    # last_rebuild_at_frame even though the joint snapshot itself may
    # be "skipped" (no substrate → no jwf). That's the contract.
    for _ in range(6):
        s.on_frame(image_data=None, frame_width=320, frame_height=240)
    snap = s.snapshot()
    # last_rebuild_at_frame should be set after the first multiple-of-2
    # frame regardless of substrate availability.
    assert snap.last_rebuild_at_frame >= 0


# --------------------------------------------------------------
# 6. Snapshot dataclass invariants
# --------------------------------------------------------------


def test_snapshot_dataclass_is_pure_python() -> None:
    """A WebcamSnapshot must not hold substrate references — so that
    the UI can outlive the substrate."""
    snap = WebcamSnapshot(
        available=True, reason="", frames_processed=10,
        fps_observed=30.0, n_entities=2, n_joint_hypotheses=9,
        n_off_diagonal_pairs=3,
    )
    assert snap.available is True
    assert snap.entities_summary == []
    assert snap.coherence_snapshots == []


# --------------------------------------------------------------
# 7. Thread safety smoke test
# --------------------------------------------------------------


def test_concurrent_on_frame_and_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that calling snapshot() while on_frame() is in flight
    doesn't crash (the lock should serialize access)."""
    import threading

    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")
    s = WebcamSession()

    def push() -> None:
        for _ in range(50):
            s.on_frame(image_data=None, frame_width=320, frame_height=240)

    def read() -> None:
        for _ in range(50):
            s.snapshot()

    threads = [threading.Thread(target=push) for _ in range(3)]
    threads += [threading.Thread(target=read) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    snap = s.snapshot()
    assert snap.frames_processed == 150


# --------------------------------------------------------------
# 8. Honest-fail invariants — module never raises
# --------------------------------------------------------------


def test_on_frame_with_no_substrate_doesnt_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")
    s = WebcamSession()
    # Pass arbitrary garbage as image_data — substrate gate triggers first.
    s.on_frame(image_data="not_a_real_image", frame_width=320, frame_height=240)
    snap = s.snapshot()
    assert snap.frames_processed == 1


def test_substrate_probe_returns_tuple() -> None:
    types, err = _try_import_substrate()
    assert (types is None) == (err is not None)
