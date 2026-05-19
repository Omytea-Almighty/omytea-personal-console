"""Synthetic-truth generator for the eval harness.

A SyntheticClip is a tiny dataset of (frame_idx, entity_id,
ground-truth-bbox) tuples plus optional rasterized frames. The
rasterization is OpenCV-rendered so we can feed it back into the
substrate's perception pipeline and see how the predicted
trajectories compare to the known truth.

These fixtures are deliberately small (10-30 frames, ≤3 entities)
to keep eval runs fast.

Design constraint: deterministic. Given the same generator args, the
output is byte-identical so eval results don't drift across runs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SyntheticEntity:
    """One ground-truth entity with a known per-frame trajectory.

    Attributes:
      entity_id: stable identifier for the entity (string).
      label: ground-truth class label (e.g. 'person', 'car').
      per_frame_bbox: tuple of (frame_idx, x_pixel, y_pixel,
        width_pixel, height_pixel) — all in pixels, top-left origin.
    """

    entity_id: str
    label: str
    per_frame_bbox: tuple[tuple[int, int, int, int, int], ...]


@dataclass(frozen=True, slots=True)
class SyntheticClip:
    """A complete synthetic video clip with known ground truth.

    Attributes:
      n_frames: number of frames in the clip.
      width, height: per-frame resolution (pixels).
      fps: frames per second.
      entities: tuple of SyntheticEntity ground-truth annotations.
      rasterized_jpegs: list of JPEG-encoded frames if ``rasterize``
        was True at construction. Empty tuple otherwise.
      label: a short human-readable name for this clip.
    """

    n_frames: int
    width: int
    height: int
    fps: float
    entities: tuple[SyntheticEntity, ...]
    rasterized_jpegs: tuple[bytes, ...] = field(default_factory=tuple)
    label: str = "synthetic"


def _rasterize_clip(
    n_frames: int,
    width: int,
    height: int,
    entities: tuple[SyntheticEntity, ...],
    bg_color: int = 30,
    jpeg_quality: int = 70,
) -> tuple[bytes, ...]:
    """Render each frame as a JPEG-encoded image with the ground-truth
    bounding boxes drawn as filled rectangles.

    Returns an empty tuple if OpenCV / numpy aren't installed — the
    eval harness then falls back to using just the truth annotations
    and skips perception-pipeline runs.
    """
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return ()

    frames: list[bytes] = []
    for f in range(n_frames):
        img = np.full((height, width, 3), bg_color, dtype=np.uint8)
        for ent_idx, ent in enumerate(entities):
            # Pick the bbox closest to this frame (use the last
            # known box at-or-before this frame_idx).
            current = None
            for bbox in ent.per_frame_bbox:
                if bbox[0] <= f:
                    current = bbox
                else:
                    break
            if current is None:
                continue
            _fi, x, y, w, h = current
            x2 = min(width, x + w)
            y2 = min(height, y + h)
            color = (
                40 + ent_idx * 60 % 215,
                160 + ent_idx * 30 % 95,
                200 - ent_idx * 40 % 100,
            )
            cv2.rectangle(img, (x, y), (x2, y2), color, -1)
        ok, buf = cv2.imencode(
            ".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
        )
        if ok:
            frames.append(buf.tobytes())
    return tuple(frames)


def build_two_entity_crossing_clip(
    n_frames: int = 16,
    width: int = 320,
    height: int = 240,
    fps: float = 8.0,
    rasterize: bool = True,
) -> SyntheticClip:
    """Two entities crossing horizontally in opposite directions.

    Good baseline because:
      - Two entities → exercises joint-state pipeline.
      - Crossing trajectories → tests tracker robustness around the
        occlusion-like center moment.
      - Constant velocity → tracker should produce clean velocity
        estimates.

    The motion is deterministic linear; entity A starts on the left
    and moves right, entity B starts on the right and moves left.
    Both at the same vertical band.
    """
    box_w, box_h = 40, 40
    y_band = height // 2 - box_h // 2

    def _linear_left_to_right(start_x: int, end_x: int) -> tuple[
        tuple[int, int, int, int, int], ...
    ]:
        # Linearly interpolate start_x → end_x across n_frames.
        out = []
        for f in range(n_frames):
            t = f / max(n_frames - 1, 1)
            x = int(round(start_x + (end_x - start_x) * t))
            out.append((f, x, y_band, box_w, box_h))
        return tuple(out)

    entity_a = SyntheticEntity(
        entity_id="A",
        label="left_to_right",
        per_frame_bbox=_linear_left_to_right(20, width - 20 - box_w),
    )
    entity_b = SyntheticEntity(
        entity_id="B",
        label="right_to_left",
        per_frame_bbox=_linear_left_to_right(
            width - 20 - box_w, 20,
        ),
    )

    entities = (entity_a, entity_b)
    jpegs: tuple[bytes, ...] = ()
    if rasterize:
        jpegs = _rasterize_clip(n_frames, width, height, entities)

    return SyntheticClip(
        n_frames=n_frames,
        width=width,
        height=height,
        fps=fps,
        entities=entities,
        rasterized_jpegs=jpegs,
        label="two_entity_crossing",
    )


__all__ = [
    "SyntheticEntity",
    "SyntheticClip",
    "build_two_entity_crossing_clip",
]
