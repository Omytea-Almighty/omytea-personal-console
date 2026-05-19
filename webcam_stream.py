"""Continuous-stream perception + quantum-state evolution for the
Mode 6 "Live webcam" mode.

This module is the Tier 2 sibling of ``video_ingest.py`` + ``video_state.py``.
Whereas the Tier 1 video-file path runs once over an uploaded file and
returns a one-shot ``VideoIngestResult`` + a one-shot quantum-evolution
result, this module exposes a long-lived ``WebcamSession`` object that:

  1. Holds a single substrate ``IoUTracker`` across many frames so the
     entity IDs stay stable
  2. Per incoming frame: runs the substrate detector → tracker → appends
     to a rolling-window trajectory dict
  3. Periodically (every ``rebuild_every_n_frames`` frames) rebuilds the
     ``EntityHypothesisBundle`` set, the ``JointWaveFunction``, and runs
     ``LindbladOperator`` over the joint off-diagonal coherence
  4. Exposes a thread-safe ``snapshot()`` for the Streamlit UI render
     loop to read the current state without racing with the frame
     callback

Substrate components used (lazy-loaded; ``OMYTEA_CONSOLE_MOCK=1`` opts
out everywhere):
  - ``omytea.perception.IoUTracker``
  - ``omytea.perception.RawDetection``
  - ``omytea.camera_ingest.MotionFallbackDetector``
  - ``omytea.models.FrameEnvelope`` / ``BoundingBox``
  - ``omytea.quantum`` + ``omytea.joint_belief`` + ``omytea.dynamics.lindblad``
    (via ``video_state.build_joint_wavefunction`` and
    ``video_state.evolve_entity_joint``)

streamlit-webrtc dependency: this module does NOT import
``streamlit_webrtc`` directly. The UI (``app.py``) imports
``streamlit_webrtc`` and wires its frame callback to call
``WebcamSession.on_frame()``. This keeps the module testable without
the heavy aiortc/av dependency chain.

Master plan compatibility:
  - §9 World Console live-camera direction
  - §2.9 negative scope — no biometric ID, no demographic attributes,
    no multi-camera reconciliation (single stream only)
  - §15 Rule #11 — provider-neutral (works fully offline; no LLM call
    per frame, only the user's natural-language query at the end
    triggers a single vision-LLM call)
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

try:
    from video_state import (
        EntityHypothesisBundle,
        build_entity_hypothesis_bundles,
        build_joint_wavefunction,
        evolve_entity_joint,
    )
except ImportError:  # circular-safe fallback (won't trigger in real use)
    EntityHypothesisBundle = None  # type: ignore
    build_entity_hypothesis_bundles = None  # type: ignore
    build_joint_wavefunction = None  # type: ignore
    evolve_entity_joint = None  # type: ignore


# Default tuning per master plan v0.4 scope (N≤3 joint entities).
_DEFAULT_MAX_TRAJECTORY_LEN = 30   # rolling window per entity
_DEFAULT_REBUILD_EVERY_N = 8       # rebuild joint state every 8 frames
_DEFAULT_MAX_ENTITIES = 3          # joint-state cap
_DEFAULT_DETECT_EVERY_N = 1        # how often to run the detector
_DEFAULT_DECOHERENCE_RATE = 0.08
_DEFAULT_HORIZON_STEPS = 5
_DEFAULT_FRAME_BUFFER_SIZE = 3     # last-N frame JPEGs kept for capture-and-predict
_DEFAULT_FRAME_BUFFER_JPEG_QUALITY = 70  # capture-and-predict snapshot quality


@dataclass
class LiveEntity:
    """One entity tracked in the live stream. Mirrors
    ``video_ingest.TrackedEntity`` shape but mutable so we can grow
    the trajectory in place."""

    object_id: str
    label: str
    first_frame_idx: int
    last_frame_idx: int
    # Each entry: (frame_idx, cx_norm, cy_norm, area_norm)
    trajectory: list[tuple[int, float, float, float]] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class WebcamSnapshot:
    """Read-only snapshot of the current live session state.

    The UI calls ``WebcamSession.snapshot()`` to get one of these.
    All fields are plain Python types (no substrate references) so
    the snapshot can outlive the substrate objects safely.
    """

    available: bool
    reason: str
    frames_processed: int
    fps_observed: float
    n_entities: int
    n_joint_hypotheses: int
    n_off_diagonal_pairs: int
    # For each live entity, a UI-friendly row.
    entities_summary: list[dict[str, Any]] = field(default_factory=list)
    # Off-diagonal magnitude per pair over the last evolve() call.
    coherence_snapshots: list[dict[str, Any]] = field(default_factory=list)
    last_rebuild_at_frame: int = -1
    last_rebuild_wallclock: float = 0.0
    detector_name: str = ""
    buffered_frames: int = 0  # # of recent frames available for capture-and-predict


def _try_import_substrate() -> tuple[dict[str, Any] | None, str | None]:
    """Lazy-load the substrate types used per frame.

    Mirrors ``video_ingest._try_import_substrate`` so both modules use
    the same fallback rules. Kept here as a separate function to avoid
    cross-module coupling on internals."""
    if os.environ.get("OMYTEA_CONSOLE_MOCK") == "1":
        return None, "mock_mode_enabled"
    try:
        from omytea.perception import IoUTracker, RawDetection
        from omytea.camera_ingest import MotionFallbackDetector
        from omytea.models import BoundingBox, FrameEnvelope
    except ImportError as exc:
        return None, f"omytea substrate not importable: {exc}"
    return {
        "IoUTracker": IoUTracker,
        "RawDetection": RawDetection,
        "MotionFallbackDetector": MotionFallbackDetector,
        "BoundingBox": BoundingBox,
        "FrameEnvelope": FrameEnvelope,
    }, None


def _try_streamlit_webrtc() -> tuple[Any | None, str | None]:
    """Probe whether streamlit-webrtc is importable. Used by the UI to
    decide whether to surface Mode 6 or show an install hint.

    Returns ``(module, None)`` on success or ``(None, reason)`` on
    failure. This is the single source of truth for the "is the
    webcam feature available?" check.
    """
    try:
        import streamlit_webrtc  # type: ignore
    except ImportError as exc:
        return None, (
            f"streamlit-webrtc not installed ({exc}). "
            "Install with: pip install 'streamlit-webrtc>=0.47,<1.0'"
        )
    return streamlit_webrtc, None


class WebcamSession:
    """Long-lived per-Streamlit-session state for the live webcam mode.

    Threading note: streamlit-webrtc runs its frame callback on a
    separate thread (via aiortc's media-track loop). The UI rerender
    happens on the main Streamlit thread. We therefore use a lock to
    guard mutations of ``self._entities`` and ``self._joint_snapshot``
    so the UI never sees a partially-rebuilt joint state.
    """

    def __init__(
        self,
        *,
        max_trajectory_len: int = _DEFAULT_MAX_TRAJECTORY_LEN,
        rebuild_every_n_frames: int = _DEFAULT_REBUILD_EVERY_N,
        max_entities: int = _DEFAULT_MAX_ENTITIES,
        detect_every_n_frames: int = _DEFAULT_DETECT_EVERY_N,
        decoherence_rate: float = _DEFAULT_DECOHERENCE_RATE,
        horizon_steps: int = _DEFAULT_HORIZON_STEPS,
        frame_buffer_size: int = _DEFAULT_FRAME_BUFFER_SIZE,
        frame_buffer_jpeg_quality: int = _DEFAULT_FRAME_BUFFER_JPEG_QUALITY,
    ) -> None:
        self.max_trajectory_len = max_trajectory_len
        self.rebuild_every_n_frames = rebuild_every_n_frames
        self.max_entities = max_entities
        self.detect_every_n_frames = detect_every_n_frames
        self.decoherence_rate = decoherence_rate
        self.horizon_steps = horizon_steps
        # Frame buffer for the Mode 6 "Capture & predict" feature:
        # we keep the last N raw frame JPEGs so the vision LLM can be
        # called on whatever the user is currently seeing. Kept small
        # (default 3) to bound memory — at 70-quality VGA, ~30-80 KB
        # per frame, so worst case ~250 KB.
        self.frame_buffer_size = max(1, frame_buffer_size)
        self.frame_buffer_jpeg_quality = max(
            10, min(95, frame_buffer_jpeg_quality)
        )

        self._lock = threading.Lock()
        self._frames_processed = 0
        self._frame_idx = 0
        self._first_seen_wallclock = 0.0
        self._last_seen_wallclock = 0.0
        self._entities: dict[str, LiveEntity] = {}
        self._joint_snapshot: dict[str, Any] = {
            "n_joint_hypotheses": 0,
            "n_off_diagonal_pairs": 0,
            "snapshots": [],
            "skipped": True,
            "reason": "no_frames_yet",
        }
        self._last_rebuild_at_frame = -1
        self._last_rebuild_wallclock = 0.0

        # Frame buffer for capture-and-predict. Each entry is a tuple
        # (frame_idx, timestamp_unix, width, height, jpeg_bytes).
        self._frame_buffer: list[tuple[int, float, int, int, bytes]] = []

        # Substrate handles (lazy-loaded on first frame).
        self._substrate_loaded = False
        self._substrate_reason: str | None = None
        self._detector: Any = None
        self._tracker: Any = None
        self._FrameEnvelope: Any = None

    # --------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------

    def _ensure_substrate(self) -> bool:
        """Lazy-init the detector + tracker. Returns True on success.

        Honest-fallback: if substrate or OpenCV is missing, we set
        ``_substrate_reason`` so the UI can surface why live mode is
        degraded — but we never raise.
        """
        if self._substrate_loaded:
            return self._tracker is not None

        types, err = _try_import_substrate()
        if types is None:
            self._substrate_reason = err or "substrate unavailable"
            self._substrate_loaded = True
            return False

        Detector = types["MotionFallbackDetector"]
        Tracker = types["IoUTracker"]
        self._FrameEnvelope = types["FrameEnvelope"]

        try:
            self._detector = Detector(min_area=80.0, thresh=20)
        except TypeError:
            self._detector = Detector()
        try:
            self._tracker = Tracker()
        except Exception as exc:
            self._substrate_reason = f"tracker init failed: {exc}"
            self._substrate_loaded = True
            return False

        self._substrate_loaded = True
        return True

    def reset(self) -> None:
        """Clear all rolling state (frame count, trajectories, joint
        snapshot). Tracker + detector are also re-initialized on the
        next ``on_frame`` so entity IDs restart fresh."""
        with self._lock:
            self._frames_processed = 0
            self._frame_idx = 0
            self._first_seen_wallclock = 0.0
            self._last_seen_wallclock = 0.0
            self._entities.clear()
            self._joint_snapshot = {
                "n_joint_hypotheses": 0,
                "n_off_diagonal_pairs": 0,
                "snapshots": [],
                "skipped": True,
                "reason": "after_reset",
            }
            self._last_rebuild_at_frame = -1
            self._last_rebuild_wallclock = 0.0
            self._frame_buffer.clear()
            self._substrate_loaded = False
            self._detector = None
            self._tracker = None

    # --------------------------------------------------------------
    # Per-frame entry point
    # --------------------------------------------------------------

    def on_frame(
        self,
        image_data: Any,
        *,
        frame_width: int,
        frame_height: int,
        stream_id: str = "webcam",
    ) -> None:
        """Process one incoming frame.

        Args:
          image_data: numpy BGR array (whatever the substrate detector
            expects). For OpenCV decode path this is just
            ``cv2.imdecode(..)``. streamlit-webrtc gives a
            ``av.VideoFrame`` which the caller must convert via
            ``frame.to_ndarray(format='bgr24')`` before calling this.
          frame_width, frame_height: dims in pixels (for normalization).
          stream_id: a stable identifier for the source — used by the
            substrate envelope. Pass per-tab/session to avoid cross-
            session ID collisions in the substrate's internal state.

        Side effects:
          - Increments frame counter
          - Runs detector + tracker
          - Updates ``self._entities`` rolling trajectories
          - Every ``rebuild_every_n_frames``, rebuilds the joint
            wavefunction + evolves it via Lindblad

        Returns: None. Use ``snapshot()`` to read the current state.
        """
        if not self._ensure_substrate():
            # Substrate not available — record the frame as seen so
            # the UI can still show "frames received but no perception".
            # Still try to buffer the frame so capture-and-predict
            # works even in degraded-perception mode.
            jpeg = _maybe_encode_jpeg(
                image_data, self.frame_buffer_jpeg_quality,
            )
            with self._lock:
                now = time.time()
                if self._first_seen_wallclock == 0.0:
                    self._first_seen_wallclock = now
                self._last_seen_wallclock = now
                self._frames_processed += 1
                self._frame_idx += 1
                if jpeg is not None:
                    self._frame_buffer.append(
                        (self._frame_idx, now, frame_width, frame_height, jpeg)
                    )
                    if len(self._frame_buffer) > self.frame_buffer_size:
                        self._frame_buffer = self._frame_buffer[
                            -self.frame_buffer_size:
                        ]
            return

        # Detect + track (this part can be heavy; outside the lock).
        do_detect = (
            self._frames_processed % max(self.detect_every_n_frames, 1) == 0
        )
        tracked = ()
        if do_detect:
            tracked = self._detect_and_track(
                image_data=image_data,
                frame_width=frame_width,
                frame_height=frame_height,
                stream_id=stream_id,
            )

        # Encode the frame for the capture-and-predict buffer outside
        # the lock — JPEG encoding is the heaviest non-substrate step.
        buffered_jpeg = _maybe_encode_jpeg(
            image_data, self.frame_buffer_jpeg_quality,
        )

        # Update rolling state + maybe rebuild joint, inside the lock.
        with self._lock:
            now = time.time()
            if self._first_seen_wallclock == 0.0:
                self._first_seen_wallclock = now
            self._last_seen_wallclock = now
            self._frame_idx += 1
            self._frames_processed += 1
            if buffered_jpeg is not None:
                self._frame_buffer.append(
                    (self._frame_idx, now, frame_width, frame_height,
                     buffered_jpeg)
                )
                if len(self._frame_buffer) > self.frame_buffer_size:
                    self._frame_buffer = self._frame_buffer[
                        -self.frame_buffer_size:
                    ]

            for det in tracked:
                oid = getattr(det, "object_id", None)
                if oid is None:
                    continue
                cx, cy, area, conf, label = _extract_centroid(
                    det, frame_width, frame_height,
                )
                if cx is None:
                    continue
                ent = self._entities.get(oid)
                if ent is None:
                    ent = LiveEntity(
                        object_id=str(oid),
                        label=label,
                        first_frame_idx=self._frame_idx,
                        last_frame_idx=self._frame_idx,
                        trajectory=[],
                        confidence=conf,
                    )
                    self._entities[str(oid)] = ent
                ent.last_frame_idx = self._frame_idx
                ent.label = label
                ent.confidence = (ent.confidence * 0.7) + (conf * 0.3)
                ent.trajectory.append(
                    (self._frame_idx, float(cx), float(cy), float(area))
                )
                # Trim the trajectory to the rolling window.
                if len(ent.trajectory) > self.max_trajectory_len:
                    ent.trajectory = ent.trajectory[-self.max_trajectory_len:]

            # Garbage-collect entities not seen in the last
            # max_trajectory_len frames — they've aged out of the
            # rolling window.
            stale_cutoff = self._frame_idx - self.max_trajectory_len
            stale_ids = [
                oid for oid, ent in self._entities.items()
                if ent.last_frame_idx < stale_cutoff
            ]
            for oid in stale_ids:
                self._entities.pop(oid, None)

            # Rebuild joint state periodically.
            should_rebuild = (
                self._frames_processed > 0
                and self._frames_processed % max(self.rebuild_every_n_frames, 1) == 0
                and len(self._entities) > 0
            )
            if should_rebuild:
                self._rebuild_joint_locked()

    # --------------------------------------------------------------
    # Detect+track helper (outside the lock — substrate work)
    # --------------------------------------------------------------

    def _detect_and_track(
        self,
        *,
        image_data: Any,
        frame_width: int,
        frame_height: int,
        stream_id: str,
    ) -> tuple[Any, ...]:
        """Run detector + tracker once. Returns the tracked detections
        (an iterable of objects with ``object_id``, ``bbox``, ``label``,
        ``confidence``). Empty tuple on any substrate error."""
        if self._detector is None or self._tracker is None:
            return ()
        from datetime import datetime, timezone

        try:
            envelope = self._FrameEnvelope(
                stream_id=stream_id,
                frame_id=f"frame_{self._frame_idx}",
                timestamp=datetime.now(tz=timezone.utc),
                width=frame_width,
                height=frame_height,
            )
        except TypeError:
            try:
                envelope = self._FrameEnvelope(
                    frame_id=f"frame_{self._frame_idx}",
                    timestamp=datetime.now(tz=timezone.utc),
                    width=frame_width,
                    height=frame_height,
                )
            except Exception:
                return ()
        except Exception:
            return ()

        try:
            raw_dets = self._detector.detect(envelope, image_data=image_data)
        except Exception:
            raw_dets = []

        for method_name in ("assign", "track"):
            method = getattr(self._tracker, method_name, None)
            if method is None:
                continue
            try:
                return tuple(method(envelope, raw_dets))
            except Exception:
                continue
        # Last-resort synthesis so the trajectory pipeline isn't empty.
        return tuple(
            type("DT", (), {
                "object_id": f"raw_{self._frame_idx}_{i}",
                "bbox": d.bbox,
                "label": getattr(d, "label", "detection"),
                "confidence": getattr(d, "confidence", 0.5),
            })()
            for i, d in enumerate(raw_dets)
        )

    # --------------------------------------------------------------
    # Joint-state rebuild (caller holds self._lock)
    # --------------------------------------------------------------

    def _rebuild_joint_locked(self) -> None:
        """Convert current ``self._entities`` to hypothesis bundles,
        build the JointWaveFunction, evolve via Lindblad, and stash
        the result into ``self._joint_snapshot``.

        Caller must hold ``self._lock``."""
        if build_entity_hypothesis_bundles is None:
            self._joint_snapshot = {
                "skipped": True,
                "reason": "video_state module not importable",
                "n_joint_hypotheses": 0,
                "n_off_diagonal_pairs": 0,
                "snapshots": [],
            }
            return

        # Convert LiveEntity → the dict shape that video_state expects.
        # Sort by track quality (length × confidence) descending so the
        # top-3 cap inside build_entity_hypothesis_bundles picks the
        # strongest entities.
        sorted_entities = sorted(
            self._entities.values(),
            key=lambda e: -(len(e.trajectory) * e.confidence),
        )
        ent_dicts = [
            {
                "object_id": e.object_id,
                "label": e.label,
                "trajectory": list(e.trajectory),
                "confidence": e.confidence,
            }
            for e in sorted_entities[: self.max_entities]
        ]

        try:
            bundles = build_entity_hypothesis_bundles(
                ent_dicts, max_entities=self.max_entities,
            )
        except Exception as exc:
            self._joint_snapshot = {
                "skipped": True,
                "reason": f"bundles build failed: {exc}",
                "n_joint_hypotheses": 0,
                "n_off_diagonal_pairs": 0,
                "snapshots": [],
            }
            return

        if not bundles:
            self._joint_snapshot = {
                "skipped": True,
                "reason": "no_bundles",
                "n_joint_hypotheses": 0,
                "n_off_diagonal_pairs": 0,
                "snapshots": [],
            }
            self._last_rebuild_at_frame = self._frame_idx
            self._last_rebuild_wallclock = time.time()
            return

        try:
            jwf = build_joint_wavefunction(bundles)
        except Exception as exc:
            self._joint_snapshot = {
                "skipped": True,
                "reason": f"jwf build failed: {exc}",
                "n_joint_hypotheses": 0,
                "n_off_diagonal_pairs": 0,
                "snapshots": [],
            }
            self._last_rebuild_at_frame = self._frame_idx
            self._last_rebuild_wallclock = time.time()
            return

        try:
            evo = evolve_entity_joint(
                jwf,
                time_horizon_steps=self.horizon_steps,
                decoherence_rate=self.decoherence_rate,
            )
        except Exception as exc:
            evo = {
                "skipped": True,
                "reason": f"lindblad evolve failed: {exc}",
                "n_joint_hypotheses": (
                    len(jwf.hypotheses) if jwf is not None else 0
                ),
                "n_off_diagonal_pairs": 0,
                "snapshots": [],
            }

        self._joint_snapshot = evo
        self._last_rebuild_at_frame = self._frame_idx
        self._last_rebuild_wallclock = time.time()

    # --------------------------------------------------------------
    # Snapshot
    # --------------------------------------------------------------

    def snapshot(self) -> WebcamSnapshot:
        """Return a thread-safe immutable snapshot of the current
        session state. The UI calls this on every rerender."""
        with self._lock:
            elapsed = max(
                self._last_seen_wallclock - self._first_seen_wallclock, 1e-6
            )
            fps_observed = (
                float(self._frames_processed) / elapsed
                if self._frames_processed > 0 and elapsed > 0
                else 0.0
            )

            entities_summary: list[dict[str, Any]] = []
            for ent in sorted(
                self._entities.values(),
                key=lambda e: -(len(e.trajectory) * e.confidence),
            )[: self.max_entities]:
                # Velocity over the last few points
                vx, vy = _velocity_estimate(ent.trajectory)
                last = ent.trajectory[-1] if ent.trajectory else (0, 0.0, 0.0, 0.0)
                entities_summary.append({
                    "object_id": ent.object_id,
                    "label": ent.label,
                    "first_frame_idx": ent.first_frame_idx,
                    "last_frame_idx": ent.last_frame_idx,
                    "n_points": len(ent.trajectory),
                    "last_cx": float(last[1]),
                    "last_cy": float(last[2]),
                    "velocity_x": float(vx),
                    "velocity_y": float(vy),
                    "confidence": float(ent.confidence),
                })

            snapshots = list(self._joint_snapshot.get("snapshots", []))

            reason = (
                self._substrate_reason
                if self._substrate_reason
                else ""
            )
            available = self._tracker is not None and not self._substrate_reason

            return WebcamSnapshot(
                available=bool(available),
                reason=reason,
                frames_processed=self._frames_processed,
                fps_observed=fps_observed,
                n_entities=len(self._entities),
                n_joint_hypotheses=int(
                    self._joint_snapshot.get("n_joint_hypotheses", 0) or 0
                ),
                n_off_diagonal_pairs=int(
                    self._joint_snapshot.get("n_off_diagonal_pairs", 0) or 0
                ),
                entities_summary=entities_summary,
                coherence_snapshots=snapshots,
                last_rebuild_at_frame=self._last_rebuild_at_frame,
                last_rebuild_wallclock=self._last_rebuild_wallclock,
                detector_name=(
                    type(self._detector).__name__ if self._detector else ""
                ),
                buffered_frames=len(self._frame_buffer),
            )

    # --------------------------------------------------------------
    # Capture-and-predict — Tier 3 Mode 6 polish
    # --------------------------------------------------------------

    def snapshot_for_prediction(
        self, n_frames: int = 3,
    ) -> dict[str, Any]:
        """Freeze the latest N frames + entity summaries so the vision
        LLM can be called against the current scene.

        Returns a dict with:
          - 'frames': list of JPEG-encoded bytes (oldest → newest)
          - 'frame_meta': list of (frame_idx, timestamp_unix, width, height)
          - 'entities_summary': same shape as Mode 5 expects
            (object_id, label, trajectory, confidence)
          - 'available': bool — False if no frames buffered yet
          - 'reason': human-readable when ``available`` is False

        This is the bridge the Mode 6 UI uses to forward the live
        state into ``compile_scene_query`` (same path as Mode 5)."""
        with self._lock:
            if not self._frame_buffer:
                return {
                    "available": False,
                    "reason": (
                        "no_frames_buffered — start the webcam, wait "
                        "for at least one frame, then capture again."
                    ),
                    "frames": [],
                    "frame_meta": [],
                    "entities_summary": [],
                }
            tail = self._frame_buffer[-max(1, n_frames):]
            frames = [t[4] for t in tail]
            meta = [(t[0], t[1], t[2], t[3]) for t in tail]
            # Mode 5 expects: object_id, label, trajectory, confidence.
            ents = sorted(
                self._entities.values(),
                key=lambda e: -(len(e.trajectory) * e.confidence),
            )[: self.max_entities]
            ent_dicts = [
                {
                    "object_id": e.object_id,
                    "label": e.label,
                    "trajectory": list(e.trajectory),
                    "confidence": e.confidence,
                }
                for e in ents
            ]
            return {
                "available": True,
                "reason": "",
                "frames": frames,
                "frame_meta": meta,
                "entities_summary": ent_dicts,
            }


# --------------------------------------------------------------
# Free helpers (no class state — easier to test in isolation)
# --------------------------------------------------------------


def _extract_centroid(
    det: Any, frame_width: int, frame_height: int,
) -> tuple[float | None, float | None, float, float, str]:
    """Pull (cx_norm, cy_norm, area_norm, conf, label) from a tracked
    detection. Returns (None, None, 0, 0, '') on schema mismatch so the
    caller can skip without raising.

    Schema tolerance: substrate has two bbox shapes — (x,y,w,h) on
    newer versions and (x1,y1,x2,y2) on older ones. We accept both.
    """
    box = getattr(det, "bbox", None) or getattr(det, "bounding_box", None)
    if box is None:
        return None, None, 0.0, 0.0, ""

    if hasattr(box, "width") and hasattr(box, "height"):
        bx = float(getattr(box, "x", 0.0))
        by = float(getattr(box, "y", 0.0))
        bw = float(box.width)
        bh = float(box.height)
        cx = (bx + bw / 2.0) / max(frame_width, 1)
        cy = (by + bh / 2.0) / max(frame_height, 1)
        area = max(0.0, bw * bh) / max(frame_width * frame_height, 1)
    else:
        x1 = float(getattr(box, "x1", 0))
        y1 = float(getattr(box, "y1", 0))
        x2 = float(getattr(box, "x2", 0))
        y2 = float(getattr(box, "y2", 0))
        cx = ((x1 + x2) / 2.0) / max(frame_width, 1)
        cy = ((y1 + y2) / 2.0) / max(frame_height, 1)
        area = max(0.0, (x2 - x1) * (y2 - y1)) / max(
            frame_width * frame_height, 1
        )

    conf = float(getattr(det, "confidence", 0.5))
    label = str(getattr(det, "label", "detection"))
    return cx, cy, area, conf, label


def _maybe_encode_jpeg(image_data: Any, quality: int) -> bytes | None:
    """Encode a BGR ndarray (or already-bytes payload) to JPEG.

    Returns None if encoding fails (e.g. ``image_data`` is None,
    OpenCV isn't installed, or the array shape is unsupported).
    Used by the WebcamSession frame buffer for the capture-and-
    predict feature; failure is non-fatal — the live mode continues.

    If ``image_data`` is already ``bytes``, we trust the caller and
    return it as-is. Useful for tests that drive on_frame() with a
    pre-encoded payload.
    """
    if image_data is None:
        return None
    if isinstance(image_data, (bytes, bytearray)):
        return bytes(image_data)
    try:
        import cv2  # type: ignore
    except ImportError:
        return None
    try:
        ok, buf = cv2.imencode(
            ".jpg", image_data, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)],
        )
    except Exception:
        return None
    if not ok:
        return None
    try:
        return buf.tobytes()
    except Exception:
        return None


def _velocity_estimate(
    trajectory: list[tuple[int, float, float, float]],
) -> tuple[float, float]:
    """Per-frame normalized velocity from the last <=8 trajectory points.

    Uses the first/last of a tail-window rather than full-trajectory so
    we react to recent motion changes rather than averaging over old
    history."""
    if len(trajectory) < 2:
        return 0.0, 0.0
    tail = trajectory[-8:] if len(trajectory) >= 2 else trajectory
    first = tail[0]
    last = tail[-1]
    df = max(last[0] - first[0], 1)
    return (last[1] - first[1]) / df, (last[2] - first[2]) / df


__all__ = [
    "LiveEntity",
    "WebcamSnapshot",
    "WebcamSession",
    "_try_streamlit_webrtc",
    "_try_import_substrate",
    "_maybe_encode_jpeg",
]
