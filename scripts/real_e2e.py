"""Real end-to-end run of the Console pipeline against a live local
Ollama vision-LLM. Unlike the test suite (which uses mock mode), this
script:

  1. Ingests samples/walking_demo.mp4 through the real substrate
     perception layer (OpenCV → motion-fallback detector → IoUTracker).
  2. Calls compile_scene_query with the live OllamaVisionBackend
     (model defaults to ``llava:7b``; set OLLAMA_VISION_MODEL to
     override).
  3. Converts the resulting BeliefProgram to a ConsoleResult and runs
     the Lindblad operator over the joint wavefunction.
  4. Prints per-step wall-clock + a JSON summary of the result so we
     have concrete numbers to fill the arXiv paper draft.

Output: a JSON object printed to stdout + a human-readable timing
table. The JSON is the canonical artifact (parseable, archivable).

Why a one-off script: pytest tests should stay reproducible and fast.
Real-network/Ollama tests don't fit that contract, so this lives as
a CLI script the user runs deliberately when capturing benchmark
numbers.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Repo root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _hr(s: str) -> None:
    print(flush=True)
    print("=" * 72, flush=True)
    print(f"  {s}", flush=True)
    print("=" * 72, flush=True)


# Make every print() flush — vision LLM steps take minutes; we want
# observable progress when this is invoked as a background process.
import functools
print = functools.partial(print, flush=True)  # type: ignore[assignment]


def main() -> int:
    _hr("Omytea Personal Future Console — real end-to-end run")

    sample = ROOT / "samples" / "walking_demo.mp4"
    if not sample.exists():
        print(f"✗ Sample video not found at {sample}")
        return 2
    n_frames = int(os.environ.get("OMYTEA_REAL_E2E_FRAMES", "2"))
    print(f"Sample: {sample}  ({sample.stat().st_size / 1024:.1f} KB)")
    print(f"n_sample_frames:    {n_frames}")
    print(f"OMYTEA_CONSOLE_MOCK = {os.environ.get('OMYTEA_CONSOLE_MOCK', '<unset>')}")
    print(f"OLLAMA_VISION_MODEL = "
          f"{os.environ.get('OLLAMA_VISION_MODEL', 'llava:7b (default)')}")

    out: dict[str, object] = {
        "sample_file": str(sample),
        "sample_size_kb": round(sample.stat().st_size / 1024, 1),
        "n_sample_frames": n_frames,
    }

    # ----- Step 1: ingest -----
    _hr("Step 1: video ingestion (substrate perception)")
    t0 = time.perf_counter()
    from video_ingest import ingest_video_file
    ingest = ingest_video_file(file_path=sample, n_sample_frames=n_frames)
    t_ingest = time.perf_counter() - t0
    print(f"  available:       {ingest.available}")
    print(f"  reason:          {ingest.reason or '(ok)'}")
    print(f"  sampled frames:  {ingest.sampled_count}")
    print(f"  total frames:    {ingest.total_frames_in_video}")
    print(f"  duration:        {ingest.duration_seconds:.2f}s "
          f"@ {ingest.fps:.1f} fps")
    print(f"  tracked entities: {len(ingest.tracked_entities)}")
    print(f"  detector used:   {ingest.detector_used}")
    print(f"  elapsed:         {t_ingest:.3f}s")

    out["step1_ingest"] = {
        "elapsed_seconds": round(t_ingest, 3),
        "available": ingest.available,
        "reason": ingest.reason,
        "sampled_frames": ingest.sampled_count,
        "total_frames": ingest.total_frames_in_video,
        "duration_seconds": round(ingest.duration_seconds, 2),
        "fps": round(ingest.fps, 1),
        "n_tracked_entities": len(ingest.tracked_entities),
        "detector_used": ingest.detector_used,
    }

    if not ingest.available:
        print("\n✗ Cannot proceed — substrate ingestion failed.")
        print(json.dumps(out, indent=2))
        return 3

    # ----- Step 2: compile scene query with live Ollama -----
    _hr("Step 2: vision-LLM scene compilation (LIVE Ollama)")
    t0 = time.perf_counter()
    from compiler import compile_scene_query
    sampled_jpegs = [sf.image_bytes for sf in ingest.sampled_frames]
    entity_summaries = [
        {
            "object_id": e.object_id, "label": e.label,
            "trajectory": list(e.trajectory),
            "confidence": e.confidence,
        }
        for e in ingest.tracked_entities
    ]
    user_query = (
        "Two people are walking past each other. What is the most "
        "likely thing that happens next?"
    )
    program = compile_scene_query(
        user_query=user_query,
        sampled_frame_jpegs=sampled_jpegs,
        tracked_entities_summary=entity_summaries,
    )
    t_compile = time.perf_counter() - t0
    fallback_reason = (
        getattr(program, "_fallback_reason", None)
        or program.raw.get("_fallback_reason", None)
    )
    n_branches = len(program.raw.get("branches", []))
    print(f"  branches emitted:   {n_branches}")
    print(f"  scenario:           {program.raw.get('scenario', '(?)')}")
    if fallback_reason:
        print(f"  ⚠ FALLBACK active:  {fallback_reason}")
    print(f"  elapsed:            {t_compile:.3f}s")

    out["step2_compile"] = {
        "elapsed_seconds": round(t_compile, 3),
        "n_branches": n_branches,
        "scenario": program.raw.get("scenario", ""),
        "fallback_reason": fallback_reason or "",
        "user_query": user_query,
    }

    # ----- Step 3: belief → console result -----
    _hr("Step 3: BeliefProgram → ConsoleResult")
    t0 = time.perf_counter()
    from console import belief_program_to_console
    result = belief_program_to_console(program)
    t_console = time.perf_counter() - t0
    print(f"  n_hypotheses:        {len(result.hypotheses)}")
    print(f"  scenario:            {result.scenario}")
    print(f"  substrate present:   {result.used_omytea_substrate}")
    print(f"  elapsed:             {t_console:.3f}s")

    # Print branches summary. ConsoleHypothesis attrs (per console.py):
    # label, narrative, probability, key_uncertainty_driver,
    # depends_on_decision, branch_type.
    print("\n  Branches:")
    for i, h in enumerate(result.hypotheses[:8]):
        narrative = (getattr(h, "narrative", "") or "")[:60]
        prob = float(getattr(h, "probability", 0.0))
        btype = getattr(h, "branch_type", "?") or "?"
        label = getattr(h, "label", "")
        print(f"    {i+1}. [{btype:>10s}]  p={prob:.2%}  {label}  {narrative}")

    out["step3_console"] = {
        "elapsed_seconds": round(t_console, 3),
        "n_hypotheses": len(result.hypotheses),
        "scenario": result.scenario,
        "used_omytea_substrate": result.used_omytea_substrate,
        "branches": [
            {
                "rank": i + 1,
                "branch_type": getattr(h, "branch_type", ""),
                "label": getattr(h, "label", ""),
                "probability": float(getattr(h, "probability", 0.0)),
                "narrative": (getattr(h, "narrative", "") or "")[:120],
            }
            for i, h in enumerate(result.hypotheses)
        ],
    }

    # ----- Step 4: quantum operator evolution -----
    _hr("Step 4: Lindblad evolution over entity joint wavefunction")
    t0 = time.perf_counter()
    import video_state
    bundles = video_state.build_entity_hypothesis_bundles(
        entity_summaries, max_entities=3,
    )
    jwf = video_state.build_joint_wavefunction(bundles)
    if jwf is None:
        print("  ⚠ Could not build JointWaveFunction (substrate not available?)")
        out["step4_quantum"] = {
            "elapsed_seconds": round(time.perf_counter() - t0, 3),
            "skipped": True,
            "reason": "no_jwf",
        }
    else:
        evo = video_state.evolve_entity_joint(
            jwf, time_horizon_steps=6, decoherence_rate=0.08,
        )
        t_quantum = time.perf_counter() - t0
        print(f"  n_joint_hypotheses: {len(jwf.hypotheses)}")
        print(f"  n_off_diagonal:     {len(jwf.off_diagonal_couplings) // 2}")
        print(f"  evolve skipped:     {evo.get('skipped', False)}")
        if evo.get("skipped"):
            print(f"  reason:             {evo.get('reason', '')}")
        else:
            n_ticks = len(evo.get('snapshots', []))
            print(f"  ticks computed:     {n_ticks}")
            # First/last snapshot magnitudes to show decay
            if n_ticks >= 2:
                first = evo['snapshots'][0]['entries']
                last = evo['snapshots'][-1]['entries']
                if first and last:
                    first_max = max(e['magnitude'] for e in first)
                    last_max = max(e['magnitude'] for e in last)
                    decay = (first_max - last_max) / max(first_max, 1e-9)
                    print(f"  off-diag max@t=0:   {first_max:.4f}")
                    print(f"  off-diag max@end:   {last_max:.4f}")
                    print(f"  decay fraction:     {decay:.1%}")
        print(f"  elapsed:            {t_quantum:.3f}s")

        out["step4_quantum"] = {
            "elapsed_seconds": round(t_quantum, 3),
            "n_joint_hypotheses": len(jwf.hypotheses),
            "n_off_diagonal_pairs":
                len(jwf.off_diagonal_couplings) // 2,
            "skipped": evo.get("skipped", False),
            "n_ticks": len(evo.get("snapshots", [])),
        }

    # Defensive: write artifact early in case downstream steps fail
    _early_artifact_dir = ROOT / "docs" / "papers" / "real_e2e_runs"
    _early_artifact_dir.mkdir(parents=True, exist_ok=True)
    _early_artifact_path = (
        _early_artifact_dir / f"real_e2e_partial_{int(time.time())}.json"
    )
    _early_artifact_path.write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )

    # ----- Totals -----
    total = sum(
        (
            out.get("step1_ingest", {}).get("elapsed_seconds", 0),
            out.get("step2_compile", {}).get("elapsed_seconds", 0),
            out.get("step3_console", {}).get("elapsed_seconds", 0),
            out.get("step4_quantum", {}).get("elapsed_seconds", 0),
        )
    )
    out["total_elapsed_seconds"] = round(total, 3)

    _hr("Totals")
    print(f"  Total wall-clock:   {total:.2f}s")
    print(f"  Step 1 (ingest):    "
          f"{out['step1_ingest']['elapsed_seconds']}s")
    print(f"  Step 2 (vision LLM): "
          f"{out['step2_compile']['elapsed_seconds']}s")
    print(f"  Step 3 (console):    "
          f"{out['step3_console']['elapsed_seconds']}s")
    print(f"  Step 4 (quantum):    "
          f"{out.get('step4_quantum', {}).get('elapsed_seconds', '?')}s")

    # Write the JSON artifact
    artifact_dir = ROOT / "docs" / "papers" / "real_e2e_runs"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = (
        artifact_dir / f"real_e2e_{int(time.time())}.json"
    )
    artifact_path.write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(f"\nArtifact written: {artifact_path}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
