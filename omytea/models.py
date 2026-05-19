from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Position:
    """A coordinate in image, map, or world space."""

    x: float
    y: float
    z: float | None = None
    space: str = "image"

    def distance_to(self, other: "Position") -> float:
        if self.space != other.space:
            raise ValueError(f"cannot compare positions in {self.space!r} and {other.space!r}")
        dz = (self.z or 0.0) - (other.z or 0.0)
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + dz**2) ** 0.5


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Image-space rectangle using top-left origin."""

    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> Position:
        return Position(self.x + self.width / 2, self.y + self.height / 2, space="image")

    def intersects(self, region: "RectRegion") -> bool:
        return not (
            self.x + self.width < region.min_x
            or self.x > region.max_x
            or self.y + self.height < region.min_y
            or self.y > region.max_y
        )


@dataclass(frozen=True, slots=True)
class RectRegion:
    """Axis-aligned spatial query region."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float
    space: str = "image"

    def contains(self, position: Position) -> bool:
        if position.space != self.space:
            return False
        return self.min_x <= position.x <= self.max_x and self.min_y <= position.y <= self.max_y


@dataclass(frozen=True, slots=True)
class FrameEnvelope:
    """Metadata for one processed frame or micro-batch."""

    stream_id: str
    frame_id: str
    timestamp: datetime
    width: int | None = None
    height: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Observation:
    """A model-produced claim about an object at a point in time."""

    stream_id: str
    timestamp: datetime
    object_id: str
    label: str
    position: Position
    confidence: float
    bbox: BoundingBox | None = None
    frame_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


class EventType(str, Enum):
    OBSERVED = "observed"
    EXPIRED = "expired"
    MERGED = "merged"
    CORRECTED = "corrected"


@dataclass(frozen=True, slots=True)
class WorldEvent:
    """Immutable fact entering the world model."""

    event_type: EventType
    observation: Observation | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def observed(cls, observation: Observation) -> "WorldEvent":
        return cls(event_type=EventType.OBSERVED, observation=observation)


@dataclass(frozen=True, slots=True)
class WorldObject:
    """Materialized object state derived from observations."""

    object_id: str
    label: str
    stream_id: str
    position: Position
    confidence: float
    last_seen_at: datetime
    first_seen_at: datetime
    bbox: BoundingBox | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Query:
    """Spatial-temporal world-state query."""

    labels: set[str] | None = None
    stream_ids: set[str] | None = None
    region: RectRegion | None = None
    at: datetime | None = None
    since: datetime | None = None
    until: datetime | None = None
    min_confidence: float = 0.0
    active_within_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class Prediction:
    """Predicted future state for one object."""

    object_id: str
    label: str
    stream_id: str
    predicted_at: datetime
    horizon_seconds: float
    position: Position
    confidence: float
    velocity: tuple[float, float, float]
    source_observations: int
