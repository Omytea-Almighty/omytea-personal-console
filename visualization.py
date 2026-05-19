"""Visualization helpers for the Personal Future Console video mode.

Renders detected-entity overlays on sampled frames + trajectory
polylines + future-position projections. Pure PIL — does not depend
on OpenCV beyond what's already required for video_ingest.

Honest-fallback: when PIL/numpy is unavailable, falls back to
returning the original image bytes (degrades to no-overlay view).
"""

from __future__ import annotations

from io import BytesIO
from typing import Any


# Color palette for up to 10 entity tracks. Picked for accessibility
# (avoids red-green confusion + visible against most backgrounds).
_PALETTE = [
    (66, 165, 245),   # blue
    (255, 167, 38),   # orange
    (102, 187, 106),  # green
    (171, 71, 188),   # purple
    (255, 235, 59),   # yellow
    (255, 112, 67),   # red-orange
    (38, 198, 218),   # cyan
    (236, 64, 122),   # pink
    (141, 110, 99),   # brown
    (120, 144, 156),  # blue-grey
]


def _color_for_entity(entity_idx: int) -> tuple[int, int, int]:
    """Stable color assignment per entity index."""
    return _PALETTE[entity_idx % len(_PALETTE)]


def render_frame_with_overlays(
    image_bytes: bytes,
    frame_idx: int,
    tracked_entities: list[dict[str, Any]],
    frame_width: int,
    frame_height: int,
) -> bytes:
    """Draw detection bounding boxes + trajectory polylines on the
    image and return new JPEG bytes.

    Args:
      image_bytes: original JPEG bytes of the sampled frame.
      frame_idx: index of this frame within the original video.
      tracked_entities: list of entity dicts with 'object_id',
        'label', 'trajectory' (list of (frame_idx, cx_norm, cy_norm,
        area_norm)), 'confidence'.
      frame_width, frame_height: original frame dimensions (used to
        de-normalize trajectory coordinates back to pixels).

    Returns:
      JPEG bytes of the image with overlays drawn. On failure
      (PIL unavailable, image decode error, etc.) returns the
      original bytes unchanged.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return image_bytes

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return image_bytes

    draw = ImageDraw.Draw(img)

    # Try to load a basic font for entity labels. PIL has a default
    # bitmap font available without any system font files.
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    iw, ih = img.size
    # Use the actual decoded image size if it differs from the
    # caller-supplied frame_width/frame_height (compression may have
    # adjusted).
    use_w = iw if iw > 0 else frame_width
    use_h = ih if ih > 0 else frame_height

    for entity_idx, ent in enumerate(tracked_entities):
        color = _color_for_entity(entity_idx)
        traj = ent.get("trajectory", [])
        if not traj:
            continue

        # Find the trajectory entry that matches this frame, if any
        on_this_frame = next(
            (t for t in traj if t[0] == frame_idx), None,
        )

        # Draw the polyline from start of trajectory up through this
        # frame (if this frame is in the trajectory) or up to the
        # nearest preceding observation (if not).
        polyline_points: list[tuple[float, float]] = []
        for t in traj:
            if t[0] > frame_idx:
                break
            cx, cy = t[1], t[2]
            polyline_points.append((cx * use_w, cy * use_h))
        if len(polyline_points) >= 2:
            draw.line(polyline_points, fill=color, width=2)

        # Draw bounding box if this entity is detected on this frame.
        if on_this_frame is not None:
            cx, cy, area = on_this_frame[1], on_this_frame[2], on_this_frame[3]
            # Recover an approximate bbox: side ≈ sqrt(area_norm) of
            # the smaller dimension. This loses bbox aspect-ratio
            # info (the area_norm field doesn't preserve it) but
            # gives a reasonable visual cue.
            side_norm = area ** 0.5
            half_w = max(side_norm * use_w * 0.5, 8)
            half_h = max(side_norm * use_h * 0.5, 8)
            x1 = max(cx * use_w - half_w, 0)
            y1 = max(cy * use_h - half_h, 0)
            x2 = min(cx * use_w + half_w, use_w - 1)
            y2 = min(cy * use_h + half_h, use_h - 1)
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=2)

            # Label: small text in the upper-left of the bbox.
            label = ent.get("object_id", "?")[:14]
            confidence = ent.get("confidence", 0.0)
            text = f"{label} {confidence:.0%}"
            if font is not None:
                draw.text(
                    (x1 + 2, max(y1 - 12, 0)),
                    text,
                    fill=color,
                    font=font,
                )

    out = BytesIO()
    try:
        img.save(out, format="JPEG", quality=80)
        return out.getvalue()
    except Exception:
        return image_bytes


__all__ = ["render_frame_with_overlays"]
