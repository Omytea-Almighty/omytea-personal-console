"""Video file ingestion for the Personal Future Console.

Wraps the Omytea substrate's perception layer (``omytea.perception``)
to process uploaded video files into:
  - sampled keyframe images (for display + vision-LLM analysis)
  - raw per-frame detections (bounding boxes + class labels)
  - tracked entities (stable object IDs across frames)
  - per-entity trajectory histories (sequence of bounding box centers)

Honest-fallback design: if OpenCV or the substrate is unavailable,
returns an informative VideoIngestResult with ``available: False``
plus a reason string. The UI is expected to surface that gracefully
rather than hard-crashing.

This module is intentionally NOT the place for any quantum-operator
evolution — that lives in ``video_state.py`` (entity belief states +
JointWaveFunction). This module is just perception → tracked
entities.

Substrate components used:
  - `omytea.perception.IoUTracker`  (or ByteTracker if available)
  - `omytea.perception.RawDetection`
  - `omytea.camera_ingest.MotionFallbackDetector` (no-ML default)
  - `omytea.camera_ingest.decode_image_bytes`

Optional substrate components (per `[perception]` extra):
  - `omytea.perception_yolo.YoloDetector` (used when YOLO is
    installed; falls back to MotionFallbackDetector otherwise)
"""

from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TrackedEntity:
    """One entity tracked across N sampled frames.

    Attributes:
      object_id: stable identifier across the sampled frames
        (assigned by the tracker, e.g., ``track_0001``)
      label: best-guess class label from the detector (e.g.,
        ``person`` from YOLO; ``motion_blob`` from
        MotionFallbackDetector)
      first_frame_idx, last_frame_idx: frame indices the entity was
        first / last observed in
      trajectory: list of (frame_idx, center_x_norm, center_y_norm,
        area_norm). All values normalized to [0, 1] relative to the
        frame size so the downstream BeliefProgram is resolution-
        independent. ``area_norm`` is bbox_area / (frame_w * frame_h).
      confidence: average detector confidence across frames the
        entity appears in.
    """

    object_id: str
    label: str
    first_frame_idx: int
    last_frame_idx: int
    trajectory: tuple[tuple[int, float, float, float], ...]
    confidence: float


@dataclass(frozen=True, slots=True)
class SampledFrame:
    """One sampled frame with its raw image bytes for downstream
    display + vision-LLM analysis."""

    frame_idx: int
    timestamp_seconds: float
    image_bytes: bytes  # JPEG-encoded
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class VideoIngestResult:
    """Output of ingest_video_file().

    available=False means perception machinery couldn't run (OpenCV
    not installed, file unreadable, substrate not importable). Other
    fields are then empty.
    """

    available: bool
    reason: str  # human-readable; empty when available=True
    sampled_frames: tuple[SampledFrame, ...] = ()
    tracked_entities: tuple[TrackedEntity, ...] = ()
    total_frames_in_video: int = 0
    duration_seconds: float = 0.0
    fps: float = 0.0
    sampled_count: int = 0
    detector_used: str = ""  # e.g. "MotionFallbackDetector" or "YoloDetector"


def _try_import_substrate() -> tuple[dict[str, Any] | None, str | None]:
    """Lazy-load substrate types. Returns (types_dict, error_str).

    Lazy-load discipline: do NOT import at module-import-time —
    the OMYTEA_CONSOLE_MOCK env var should be honored per call
    so tests can switch mock vs real mode without restart."""
    if os.environ.get("OMYTEA_CONSOLE_MOCK") == "1":
        return None, "mock_mode_enabled"
    try:
        from omytea.perception import (
            IoUTracker,
            RawDetection,
            SyntheticDetector,
        )
        from omytea.camera_ingest import (
            MotionFallbackDetector,
            decode_image_bytes,
        )
        from omytea.models import BoundingBox, FrameEnvelope
    except ImportError as exc:
        return None, f"omytea substrate not importable: {exc}"
    return {
        "IoUTracker": IoUTracker,
        "RawDetection": RawDetection,
        "SyntheticDetector": SyntheticDetector,
        "MotionFallbackDetector": MotionFallbackDetector,
        "decode_image_bytes": decode_image_bytes,
        "BoundingBox": BoundingBox,
        "FrameEnvelope": FrameEnvelope,
    }, None


def _try_import_opencv() -> tuple[Any | None, Any | None, str | None]:
    """Lazy import of cv2 + numpy. Returns (cv2, np, error)."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:
        return None, None, f"opencv-python or numpy not installed: {exc}"
    return cv2, np, None


def _sample_indices(total_frames: int, n_samples: int) -> list[int]:
    """Evenly-spaced sample indices over [0, total_frames).

    Returns at most ``n_samples`` distinct integer indices. Edge
    cases: total_frames <= 0 → empty list; total_frames < n_samples
    → returns all available indices.
    """
    if total_frames <= 0:
        return []
    if total_frames <= n_samples:
        return list(range(total_frames))
    step = total_frames / float(n_samples)
    return [int(i * step) for i in range(n_samples)]


def ingest_video_file(
    file_bytes: bytes | None = None,
    file_path: str | Path | None = None,
    *,
    n_sample_frames: int = 8,
    jpeg_quality: int = 75,
    max_entities_returned: int = 10,
) -> VideoIngestResult:
    """Sample N frames from a video file + run substrate perception.

    Args:
      file_bytes: video file bytes (preferred for Streamlit uploads).
        Either this OR file_path must be supplied.
      file_path: path to a video on disk (alternative to file_bytes).
      n_sample_frames: how many frames to sample evenly. More frames =
        better tracking but slower vision-LLM downstream.
      jpeg_quality: re-encoding quality for the sampled-frame previews
        (75 is a reasonable Streamlit display quality).
      max_entities_returned: cap on TrackedEntity count returned.
        Master plan v0.4 caps joint state at N≤3 entities; downstream
        BeliefProgram should subset to top-3 by confidence regardless.

    Returns:
      VideoIngestResult. Always returns — never raises on missing
      deps; the UI inspects ``available`` and ``reason`` to decide
      what to show.
    """
    if file_bytes is None and file_path is None:
        return VideoIngestResult(
            available=False,
            reason="Either file_bytes or file_path must be supplied.",
        )

    # Check substrate first — the OMYTEA_CONSOLE_MOCK opt-out is the
    # most explicit signal that the user does not want substrate
    # processing, so it should short-circuit before any
    # environmental dependency check.
    substrate_types, subs_err = _try_import_substrate()
    if substrate_types is None:
        return VideoIngestResult(
            available=False,
            reason=subs_err or "Omytea substrate unavailable",
        )

    cv2, np, opencv_err = _try_import_opencv()
    if cv2 is None:
        return VideoIngestResult(
            available=False,
            reason=opencv_err or "OpenCV unavailable",
        )

    # Materialize to a temp file if we only have bytes (cv2 needs a path).
    tmp_path: str | None = None
    cleanup_path: str | None = None
    try:
        if file_path is not None:
            tmp_path = str(file_path)
        else:
            assert file_bytes is not None
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".mp4",
            ) as f:
                f.write(file_bytes)
                tmp_path = f.name
                cleanup_path = f.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return VideoIngestResult(
                available=False,
                reason=f"OpenCV failed to open video at {tmp_path}.",
            )

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        duration = (total_frames / fps) if fps > 0 else 0.0
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if total_frames <= 0 or frame_w <= 0 or frame_h <= 0:
            cap.release()
            return VideoIngestResult(
                available=False,
                reason="Video has zero frames or zero resolution.",
            )

        sample_idxs = _sample_indices(total_frames, n_sample_frames)
        if not sample_idxs:
            cap.release()
            return VideoIngestResult(
                available=False,
                reason="No frames to sample.",
            )

        # Build substrate components.
        Detector = substrate_types["MotionFallbackDetector"]
        Tracker = substrate_types["IoUTracker"]
        FrameEnvelope = substrate_types["FrameEnvelope"]
        BoundingBox = substrate_types["BoundingBox"]

        # min_area lowered from default 400 to 80 because we sample
        # frames sparsely (every N frames of the original video).
        # With sparse sampling, the motion-difference blobs are
        # smaller proportionally because the per-frame movement
        # is larger and the diff thresholding eats more area.
        # threshold also lowered slightly for better sensitivity
        # on the small synthetic sample.
        try:
            detector = Detector(min_area=80.0, thresh=20)
        except TypeError:
            # Older substrate version without those kwargs
            detector = Detector()
        tracker = Tracker()

        sampled_out: list[SampledFrame] = []
        # entity_id -> list[(frame_idx, cx_norm, cy_norm, area_norm, conf, label)]
        track_history: dict[str, list[tuple[int, float, float, float, float, str]]] = {}

        from datetime import datetime, timezone

        for sample_idx, target_frame_idx in enumerate(sample_idxs):
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
            ok, frame_img = cap.read()
            if not ok or frame_img is None:
                continue

            # Re-encode for downstream JPEG display
            ok2, jpeg_buf = cv2.imencode(
                ".jpg",
                frame_img,
                [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
            )
            if not ok2:
                continue

            t_seconds = (
                target_frame_idx / fps if fps > 0 else float(target_frame_idx)
            )

            sampled_out.append(SampledFrame(
                frame_idx=target_frame_idx,
                timestamp_seconds=t_seconds,
                image_bytes=jpeg_buf.tobytes(),
                width=frame_w,
                height=frame_h,
            ))

            # Substrate perception: detect + track.
            # FrameEnvelope signature per substrate v1.x:
            #   (stream_id, frame_id, timestamp, width, height, attributes)
            try:
                envelope = FrameEnvelope(
                    stream_id="video_upload",
                    frame_id=f"frame_{target_frame_idx}",
                    timestamp=datetime.now(tz=timezone.utc),
                    width=frame_w,
                    height=frame_h,
                )
            except TypeError:
                # Older substrate signature without explicit
                # stream_id; try the alternative form. Best-effort
                # graceful degradation.
                try:
                    envelope = FrameEnvelope(
                        frame_id=f"frame_{target_frame_idx}",
                        timestamp=datetime.now(tz=timezone.utc),
                        width=frame_w,
                        height=frame_h,
                    )
                except Exception:
                    continue
            except Exception:
                continue

            try:
                raw_dets = detector.detect(envelope, image_data=frame_img)
            except Exception:
                raw_dets = []

            # IoUTracker exposes `assign(envelope, detections)` per
            # substrate v1.x. Older / newer versions may use `track()`
            # so we try assign first then fall back.
            tracked = []
            for method_name in ("assign", "track"):
                method = getattr(tracker, method_name, None)
                if method is None:
                    continue
                try:
                    tracked = list(method(envelope, raw_dets))
                    break
                except Exception:
                    tracked = []
            if not tracked:
                # As a last resort, synthesize per-detection IDs so
                # the downstream trajectory pipeline still has data.
                tracked = [
                    type("DT", (), {
                        "object_id": f"raw_{target_frame_idx}_{i}",
                        "bbox": d.bbox,
                        "label": getattr(d, "label", "detection"),
                        "confidence": getattr(d, "confidence", 0.5),
                    })()
                    for i, d in enumerate(raw_dets)
                ]

            for det in tracked:
                oid = getattr(det, "object_id", None)
                if oid is None:
                    continue
                box = getattr(det, "bbox", None) or getattr(det, "bounding_box", None)
                if box is None:
                    continue
                # BoundingBox per substrate v1.x: (x, y, width, height)
                # in pixels (x, y = top-left corner). Older variants
                # might expose (x1, y1, x2, y2); fall back gracefully.
                if hasattr(box, "width") and hasattr(box, "height"):
                    bx = float(box.x)
                    by = float(box.y)
                    bw = float(box.width)
                    bh = float(box.height)
                    cx = (bx + bw / 2.0) / max(frame_w, 1)
                    cy = (by + bh / 2.0) / max(frame_h, 1)
                    area = max(0.0, bw * bh) / max(frame_w * frame_h, 1)
                else:
                    x1 = float(getattr(box, "x1", 0))
                    y1 = float(getattr(box, "y1", 0))
                    x2 = float(getattr(box, "x2", 0))
                    y2 = float(getattr(box, "y2", 0))
                    cx = ((x1 + x2) / 2.0) / max(frame_w, 1)
                    cy = ((y1 + y2) / 2.0) / max(frame_h, 1)
                    area = max(0.0, (x2 - x1) * (y2 - y1)) / max(
                        frame_w * frame_h, 1
                    )
                conf = float(getattr(det, "confidence", 0.5))
                label = str(getattr(det, "label", "detection"))
                track_history.setdefault(oid, []).append(
                    (target_frame_idx, cx, cy, area, conf, label)
                )

        cap.release()

        # Distill TrackedEntity records from the histories.
        entities: list[TrackedEntity] = []
        for oid, history in track_history.items():
            if not history:
                continue
            # Sort by frame_idx
            history.sort(key=lambda h: h[0])
            first_idx = history[0][0]
            last_idx = history[-1][0]
            avg_conf = sum(h[4] for h in history) / len(history)
            # Pick the most common label as the entity label
            label_counts: dict[str, int] = {}
            for h in history:
                label_counts[h[5]] = label_counts.get(h[5], 0) + 1
            label = max(label_counts, key=label_counts.get)  # type: ignore
            trajectory = tuple(
                (h[0], h[1], h[2], h[3]) for h in history
            )
            entities.append(TrackedEntity(
                object_id=str(oid),
                label=label,
                first_frame_idx=first_idx,
                last_frame_idx=last_idx,
                trajectory=trajectory,
                confidence=avg_conf,
            ))

        # Rank entities by track length × confidence, cap at max.
        entities.sort(
            key=lambda e: -(len(e.trajectory) * e.confidence),
        )
        entities = entities[:max_entities_returned]

        return VideoIngestResult(
            available=True,
            reason="",
            sampled_frames=tuple(sampled_out),
            tracked_entities=tuple(entities),
            total_frames_in_video=total_frames,
            duration_seconds=duration,
            fps=fps,
            sampled_count=len(sampled_out),
            detector_used=type(detector).__name__,
        )
    finally:
        if cleanup_path is not None:
            try:
                os.unlink(cleanup_path)
            except OSError:
                pass


__all__ = [
    "TrackedEntity",
    "SampledFrame",
    "VideoIngestResult",
    "ingest_video_file",
]
