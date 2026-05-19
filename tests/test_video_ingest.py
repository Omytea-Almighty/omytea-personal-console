"""Tests for video_ingest.py — video file → tracked entities.

These tests verify graceful behavior:
- No file → informative error
- OpenCV missing → available=False with reason
- Mock mode → available=False with reason
- Helper functions (_sample_indices) round-trip correctly
- Dataclass defaults + immutability

Real perception tests require OpenCV + a small sample video; those
are integration-test territory and skipped here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from video_ingest import (  # noqa: E402
    SampledFrame,
    TrackedEntity,
    VideoIngestResult,
    _sample_indices,
    ingest_video_file,
)


# ----- _sample_indices -----


def test_sample_indices_empty_when_zero_frames() -> None:
    assert _sample_indices(0, 8) == []


def test_sample_indices_negative_when_negative_total() -> None:
    assert _sample_indices(-5, 8) == []


def test_sample_indices_returns_all_when_total_le_samples() -> None:
    assert _sample_indices(5, 8) == [0, 1, 2, 3, 4]
    assert _sample_indices(8, 8) == list(range(8))


def test_sample_indices_returns_n_when_total_gt_samples() -> None:
    out = _sample_indices(100, 5)
    assert len(out) == 5
    assert out[0] == 0
    assert out[-1] < 100


def test_sample_indices_evenly_spaced() -> None:
    out = _sample_indices(100, 5)
    # Step is 100/5 = 20, so indices ~= 0, 20, 40, 60, 80
    gaps = [out[i + 1] - out[i] for i in range(len(out) - 1)]
    for g in gaps:
        assert 15 <= g <= 25, f"gap {g} not roughly 20"


def test_sample_indices_distinct() -> None:
    out = _sample_indices(1000, 50)
    assert len(out) == len(set(out)), "indices must be distinct"


# ----- ingest_video_file guards -----


def test_ingest_no_input_returns_unavailable() -> None:
    out = ingest_video_file()
    assert out.available is False
    assert "must be supplied" in out.reason


def test_ingest_mock_mode_returns_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")
    out = ingest_video_file(file_bytes=b"\x00" * 100)
    # In mock mode, even with bytes provided, substrate isn't loaded
    # so we return unavailable with a clear reason.
    assert out.available is False
    assert "mock" in out.reason.lower() or "substrate" in out.reason.lower()


def test_ingest_bad_video_bytes_returns_unavailable() -> None:
    """Garbage bytes → OpenCV fails to open → unavailable + reason."""
    out = ingest_video_file(file_bytes=b"not_a_video_at_all")
    # Either OpenCV missing OR OpenCV fails to open the file.
    assert out.available is False
    assert len(out.reason) > 0


# ----- VideoIngestResult dataclass -----


def test_result_defaults_when_unavailable() -> None:
    r = VideoIngestResult(available=False, reason="test")
    assert r.sampled_frames == ()
    assert r.tracked_entities == ()
    assert r.total_frames_in_video == 0
    assert r.duration_seconds == 0.0
    assert r.fps == 0.0
    assert r.sampled_count == 0
    assert r.detector_used == ""


def test_result_immutable() -> None:
    r = VideoIngestResult(available=False, reason="x")
    with pytest.raises((AttributeError, Exception)):
        r.available = True  # type: ignore[misc]


# ----- TrackedEntity + SampledFrame dataclasses -----


def test_tracked_entity_construction() -> None:
    e = TrackedEntity(
        object_id="t_1",
        label="person",
        first_frame_idx=0,
        last_frame_idx=10,
        trajectory=((0, 0.5, 0.5, 0.1), (10, 0.6, 0.5, 0.1)),
        confidence=0.85,
    )
    assert e.object_id == "t_1"
    assert len(e.trajectory) == 2


def test_sampled_frame_construction() -> None:
    f = SampledFrame(
        frame_idx=0,
        timestamp_seconds=0.0,
        image_bytes=b"\x89PNG",
        width=640,
        height=480,
    )
    assert f.frame_idx == 0
    assert f.width == 640


# ----- Public exports -----


def test_module_exports() -> None:
    import video_ingest
    expected = {
        "TrackedEntity",
        "SampledFrame",
        "VideoIngestResult",
        "ingest_video_file",
    }
    assert expected.issubset(set(video_ingest.__all__))
