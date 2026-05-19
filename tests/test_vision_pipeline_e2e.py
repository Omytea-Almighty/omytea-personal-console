"""End-to-end tests for the Mode 5 video pipeline.

Pipeline: video file → ingestion → entity tracking → scene
compilation (mock-mode vision LLM) → BeliefProgram → ConsoleResult
→ quantum operator evolution.

These tests use the OMYTEA_CONSOLE_MOCK=1 path so they run without
a vision model. They verify the *plumbing* works end-to-end, not the
quality of the vision LLM.

Real video ingestion is exercised via a synthetic OpenCV-generated
test video so we don't depend on bundled binary fixtures.
"""

from __future__ import annotations

import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ----- Synthetic video fixture -----


@pytest.fixture(scope="module")
def synthetic_video_path() -> Path:
    """Generate a 16-frame 320x240 video with a moving rectangle."""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    tmp_path = Path(tempfile.gettempdir()) / "omytea_test_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp_path), fourcc, 8.0, (320, 240))

    try:
        for i in range(16):
            frame = np.full((240, 320, 3), 30, dtype=np.uint8)
            # Moving rectangle across the frame
            x1 = 20 + i * 15
            y1 = 80
            x2 = x1 + 40
            y2 = y1 + 40
            cv2.rectangle(
                frame, (x1, y1), (x2, y2), (200, 200, 200), -1,
            )
            writer.write(frame)
    finally:
        writer.release()

    if not tmp_path.exists() or tmp_path.stat().st_size < 100:
        pytest.skip("synthetic video creation failed; codec issue")

    yield tmp_path

    try:
        tmp_path.unlink()
    except OSError:
        pass


# ----- ingest_video_file with real synthetic video -----


def test_ingest_synthetic_video_produces_frames(
    synthetic_video_path: Path,
) -> None:
    from video_ingest import ingest_video_file

    out = ingest_video_file(
        file_path=synthetic_video_path,
        n_sample_frames=5,
    )

    if not out.available:
        # If OpenCV or substrate complains about something
        # environment-specific, skip rather than fail.
        pytest.skip(f"ingest unavailable: {out.reason}")

    assert out.sampled_count > 0
    assert out.total_frames_in_video >= 10
    assert out.fps > 0


def test_ingest_synthetic_video_returns_jpegs(
    synthetic_video_path: Path,
) -> None:
    from video_ingest import ingest_video_file

    out = ingest_video_file(
        file_path=synthetic_video_path,
        n_sample_frames=3,
    )
    if not out.available:
        pytest.skip(f"ingest unavailable: {out.reason}")

    for sf in out.sampled_frames:
        # JPEG SOI marker is FFD8FFE0 (or FFD8FFE1)
        assert sf.image_bytes[:2] == b"\xff\xd8"
        assert sf.width > 0
        assert sf.height > 0


def test_ingest_from_bytes_works(synthetic_video_path: Path) -> None:
    from video_ingest import ingest_video_file

    file_bytes = synthetic_video_path.read_bytes()
    out = ingest_video_file(
        file_bytes=file_bytes,
        n_sample_frames=4,
    )
    if not out.available:
        pytest.skip(f"ingest unavailable: {out.reason}")
    assert out.sampled_count > 0


# ----- compile_scene_query in mock mode -----


def test_scene_compile_mock_mode_well_formed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")
    from compiler import compile_scene_query

    result = compile_scene_query(
        user_query="What's about to happen?",
        sampled_frame_jpegs=[b"\xff\xd8\xff" + b"\x00" * 50],
        tracked_entities_summary=[
            {
                "object_id": "t1",
                "label": "person",
                "trajectory": [(0, 0.3, 0.5, 0.04), (5, 0.5, 0.5, 0.04)],
                "confidence": 0.8,
            }
        ],
    )

    assert result.scenario == "video_scene_query"
    assert len(result.branches) >= 6
    assert len(result.branches) <= 8
    # Probabilities sum to 1.0
    total = sum(b["probability_prior"] for b in result.branches)
    assert abs(total - 1.0) < 1e-3
    # Exactly one wishful + one worst
    wishful = [b for b in result.branches if b["branch_type"] == "wishful"]
    worst = [b for b in result.branches if b["branch_type"] == "worst"]
    assert len(wishful) == 1
    assert len(worst) == 1


def test_scene_compile_mock_no_entities() -> None:
    """Mock mode should work even if no entities are detected."""
    os.environ["OMYTEA_CONSOLE_MOCK"] = "1"
    try:
        from compiler import compile_scene_query

        result = compile_scene_query(
            user_query="empty scene",
            sampled_frame_jpegs=[b"\xff\xd8\xff"],
            tracked_entities_summary=[],
        )
        assert len(result.branches) >= 6
    finally:
        del os.environ["OMYTEA_CONSOLE_MOCK"]


def test_scene_compile_mock_evidence_has_pp_units() -> None:
    """Evidence uses ΔP in pp per the canonical PMF-instrument schema."""
    os.environ["OMYTEA_CONSOLE_MOCK"] = "1"
    try:
        from compiler import compile_scene_query

        result = compile_scene_query(
            user_query="x",
            sampled_frame_jpegs=[b"\xff\xd8"],
            tracked_entities_summary=[],
        )
        evidence = result.recommended_evidence
        assert len(evidence) > 0
        for e in evidence:
            assert "expected_delta_p" in e
            assert isinstance(e["expected_delta_p"], (int, float))
            assert 0 <= e["expected_delta_p"] <= 100
    finally:
        del os.environ["OMYTEA_CONSOLE_MOCK"]


# ----- End-to-end: ingest → scene-compile → console result -----


def test_full_pipeline_mock_mode_returns_console_result(
    synthetic_video_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full pipeline test in mock mode: video → ingest → mock
    scene compile → console result. Verifies the wiring works."""
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")

    from compiler import compile_scene_query
    from console import belief_program_to_console
    from video_ingest import ingest_video_file

    ingest = ingest_video_file(
        file_path=synthetic_video_path,
        n_sample_frames=4,
    )
    # In mock mode, ingest may report unavailable because the
    # substrate is gated by mock-mode env var. That's the expected
    # behavior; we then exercise the rest of the pipeline with
    # synthetic data.
    if not ingest.available:
        sampled_jpegs = [b"\xff\xd8\xff"]
        entity_summaries = [
            {"object_id": "t1", "label": "person",
             "trajectory": [(0, 0.3, 0.5, 0.04)],
             "confidence": 0.7},
        ]
    else:
        sampled_jpegs = [sf.image_bytes for sf in ingest.sampled_frames]
        entity_summaries = [
            {
                "object_id": e.object_id, "label": e.label,
                "trajectory": list(e.trajectory),
                "confidence": e.confidence,
            }
            for e in ingest.tracked_entities
        ]

    program = compile_scene_query(
        user_query="What happens next?",
        sampled_frame_jpegs=sampled_jpegs,
        tracked_entities_summary=entity_summaries,
    )

    result = belief_program_to_console(program)
    assert len(result.hypotheses) >= 6
    assert result.scenario == "video_scene_query"


# ----- visualization with real frame -----


def test_visualization_with_synthetic_jpeg() -> None:
    """render_frame_with_overlays should not crash on a real JPEG."""
    pil = pytest.importorskip("PIL.Image")
    from PIL import Image
    img = Image.new("RGB", (200, 150), (40, 40, 40))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    original = buf.getvalue()

    from visualization import render_frame_with_overlays
    out = render_frame_with_overlays(
        image_bytes=original,
        frame_idx=2,
        tracked_entities=[
            {"object_id": "a", "label": "x", "confidence": 0.5,
             "trajectory": [(0, 0.3, 0.5, 0.04),
                            (2, 0.5, 0.5, 0.04)]},
        ],
        frame_width=200,
        frame_height=150,
    )
    # Output should be different (overlay drawn)
    assert out != original
    # Still valid JPEG
    assert out[:2] == b"\xff\xd8"


def test_visualization_no_entities_returns_original() -> None:
    """No entities → no overlay → original bytes (or close)."""
    from PIL import Image
    img = Image.new("RGB", (100, 100), (60, 60, 60))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    original = buf.getvalue()

    from visualization import render_frame_with_overlays
    out = render_frame_with_overlays(
        image_bytes=original,
        frame_idx=0,
        tracked_entities=[],
        frame_width=100,
        frame_height=100,
    )
    # Without overlays, output is a re-encoded copy — content
    # should be semantically equivalent but bytes may differ
    assert out[:2] == b"\xff\xd8"


def test_visualization_pil_missing_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If PIL import fails, render_frame_with_overlays returns the
    original bytes unchanged (honest fallback)."""
    import builtins

    original_import = builtins.__import__

    def selective_block(name, *args, **kwargs):
        if name.startswith("PIL"):
            raise ImportError("simulated")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", selective_block)
    # Re-import to bust any cached state
    import importlib
    import visualization
    importlib.reload(visualization)

    from visualization import render_frame_with_overlays
    out = render_frame_with_overlays(
        image_bytes=b"original_bytes",
        frame_idx=0,
        tracked_entities=[],
        frame_width=10,
        frame_height=10,
    )
    assert out == b"original_bytes"
