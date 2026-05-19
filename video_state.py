"""Build per-entity quantum belief state from tracked-entity trajectories.

Bridges the video-perception layer (entity tracks across sampled
frames) to the Omytea quantum substrate (`StateHypothesis` per
entity, `JointWaveFunction` over the multi-entity tuple,
`LindbladOperator` to evolve the joint off-diagonal coherence).

The design follows the Omytea substrate's quantum-information
discipline: ρ as primary state, WaveFunction as sparse view,
LindbladOperator on JointWaveFunction for time evolution.

For each tracked entity, we synthesize 3 position-hypotheses:
  - "continue" — the entity keeps its observed motion vector
  - "accelerate" — the motion vector grows
  - "decelerate_or_stop" — the motion vector shrinks toward zero

For >1 entity, the JointWaveFunction expresses correlated futures
(e.g., entity A continuing + entity B continuing has higher prior
than entity A continuing + entity B reversing if they appear
coupled in the scene).

Master plan v0.4 caps joint state at N≤3 entities — this module
enforces that cap to avoid combinatorial blow-up.

Honest-fallback: returns None when substrate isn't importable.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EntityHypothesisBundle:
    """The 3 position-hypotheses synthesized for one tracked entity."""

    entity_id: str
    label: str
    last_observed_cx: float  # normalized [0,1]
    last_observed_cy: float
    velocity_x: float  # per-frame normalized velocity
    velocity_y: float
    hypothesis_ids: tuple[str, str, str]  # (continue, accelerate, decelerate)
    hypothesis_weights: tuple[float, float, float]  # priors, sum to 1.0


def _load_omytea_substrate() -> tuple[dict[str, Any] | None, str | None]:
    """Lazy-load substrate types at call time (per cerebrum DNR)."""
    if os.environ.get("OMYTEA_CONSOLE_MOCK") == "1":
        return None, "mock_mode_enabled"
    try:
        from datetime import datetime, timezone
        from omytea.quantum import StateHypothesis, WaveFunction
        from omytea.joint_belief import (
            JointBranchHypothesis,
            JointWaveFunction,
            OffDiagonalEntry,
        )
        from omytea.models import Position
        from omytea.dynamics.lindblad import LindbladOperator
        from omytea.dynamics.protocol import OperatorContext
    except ImportError as exc:
        return None, f"omytea substrate not importable: {exc}"
    return {
        "datetime": datetime,
        "timezone": timezone,
        "StateHypothesis": StateHypothesis,
        "WaveFunction": WaveFunction,
        "JointBranchHypothesis": JointBranchHypothesis,
        "JointWaveFunction": JointWaveFunction,
        "OffDiagonalEntry": OffDiagonalEntry,
        "Position": Position,
        "LindbladOperator": LindbladOperator,
        "OperatorContext": OperatorContext,
    }, None


def _estimate_velocity_per_frame(
    trajectory: list[tuple[int, float, float, float]],
) -> tuple[float, float]:
    """Linear-regression-free velocity estimate from first/last
    observations. Returns (dx_per_frame, dy_per_frame) in normalized
    units. Returns (0,0) for trajectories of length <2."""
    if len(trajectory) < 2:
        return 0.0, 0.0
    first = trajectory[0]
    last = trajectory[-1]
    df = max(last[0] - first[0], 1)
    dx = (last[1] - first[1]) / df
    dy = (last[2] - first[2]) / df
    return dx, dy


def build_entity_hypothesis_bundles(
    tracked_entities: list[dict[str, Any]],
    max_entities: int = 3,
) -> list[EntityHypothesisBundle]:
    """Synthesize 3 future-position hypotheses per entity.

    Args:
      tracked_entities: list of dicts with at least 'object_id',
        'label', 'trajectory' (list of (frame_idx, cx, cy, area)).
        From video_ingest.TrackedEntity.__dict__ effectively.
      max_entities: cap to keep joint-hypothesis count tractable
        (the substrate's v0.4 joint-state design recommends N≤3
        entities to avoid combinatorial blowup).

    Returns:
      List of EntityHypothesisBundle (one per entity, capped at
      max_entities).
    """
    bundles: list[EntityHypothesisBundle] = []
    for ent in tracked_entities[:max_entities]:
        traj = ent.get("trajectory", [])
        if not traj:
            continue
        last = traj[-1]
        last_cx = float(last[1])
        last_cy = float(last[2])
        vx, vy = _estimate_velocity_per_frame(traj)

        eid = str(ent.get("object_id", "?"))
        label = str(ent.get("label", "entity"))

        # Three hypothesis IDs — also stable across calls
        hyp_ids = (
            f"{eid}__continue",
            f"{eid}__accelerate",
            f"{eid}__decelerate",
        )

        # Default priors: 60% continue, 25% accelerate, 15% decelerate.
        # If observed velocity is near-zero, redistribute toward
        # "decelerate_or_stop" since the entity is barely moving.
        speed = math.sqrt(vx * vx + vy * vy)
        if speed < 1e-4:
            weights = (0.50, 0.10, 0.40)  # mostly stationary
        elif speed > 0.05:  # >5% of frame per frame = fast
            weights = (0.55, 0.35, 0.10)  # likely to keep moving
        else:
            weights = (0.60, 0.25, 0.15)

        bundles.append(EntityHypothesisBundle(
            entity_id=eid,
            label=label,
            last_observed_cx=last_cx,
            last_observed_cy=last_cy,
            velocity_x=vx,
            velocity_y=vy,
            hypothesis_ids=hyp_ids,
            hypothesis_weights=weights,
        ))
    return bundles


def build_joint_wavefunction(
    bundles: list[EntityHypothesisBundle],
) -> Any | None:
    """Construct an Omytea JointWaveFunction from entity hypothesis
    bundles.

    For each (entity, hypothesis) pair, create a StateHypothesis with
    a synthesized future position derived from the entity's
    last-observed position + velocity. The JointWaveFunction takes
    the Cartesian product across entities (but since the joint-state
    design caps at N≤3 entities × 3 hypotheses each, the tensor
    product is at most 27 joint hypotheses — manageable).

    Off-diagonal couplings: by default, "continue + continue" pairs
    across entities get a small positive coherence (entities likely
    to maintain their respective trajectories together); "accelerate
    + decelerate" pairs get small negative coherence (correlated
    opposites less likely).

    Returns:
      A JointWaveFunction (Omytea substrate type) when substrate is
      available + at least one bundle has hypotheses; None otherwise.
    """
    if not bundles:
        return None

    omytea, err = _load_omytea_substrate()
    if omytea is None:
        return None

    StateHypothesis = omytea["StateHypothesis"]
    Position = omytea["Position"]
    WaveFunction = omytea["WaveFunction"]
    JointBranchHypothesis = omytea["JointBranchHypothesis"]
    JointWaveFunction = omytea["JointWaveFunction"]
    OffDiagonalEntry = omytea["OffDiagonalEntry"]
    datetime = omytea["datetime"]
    timezone = omytea["timezone"]
    now = datetime.now(tz=timezone.utc)

    # For each entity, build a WaveFunction with 3 hypotheses
    # representing future-position futures.
    per_entity_wfs: list[Any] = []
    per_entity_hyp_ids: list[tuple[str, ...]] = []
    # Side-channel map: substrate-assigned hypothesis_id (UUID) →
    # human-readable label (which contains "continue" / "accelerate"
    # / "decelerate"). Used by the off-diagonal heuristic.
    uuid_to_label: dict[str, str] = {}
    for b in bundles:
        # Position projection: continue = position + velocity*T_horizon;
        # accelerate = position + 2*velocity*T_horizon;
        # decelerate = position + 0.3*velocity*T_horizon.
        # Using T_horizon=10 frames for the projection.
        T = 10.0
        positions_norm = [
            (b.last_observed_cx + b.velocity_x * T,
             b.last_observed_cy + b.velocity_y * T),
            (b.last_observed_cx + b.velocity_x * T * 2.0,
             b.last_observed_cy + b.velocity_y * T * 2.0),
            (b.last_observed_cx + b.velocity_x * T * 0.3,
             b.last_observed_cy + b.velocity_y * T * 0.3),
        ]

        hyps = []
        for h_idx, (hyp_id, weight) in enumerate(
            zip(b.hypothesis_ids, b.hypothesis_weights)
        ):
            cx, cy = positions_norm[h_idx]
            try:
                hyps.append(StateHypothesis(
                    object_id=b.entity_id,
                    label=hyp_id,
                    stream_id=f"video_entity_{b.entity_id}",
                    timestamp=now,
                    position=Position(
                        x=float(cx), y=float(cy), space="image_norm",
                    ),
                    weight=float(weight),
                    branch_label=hyp_id,
                    attributes={
                        "entity_label": b.label,
                        "future_vector_x": b.velocity_x,
                        "future_vector_y": b.velocity_y,
                        "hypothesis_index": h_idx,
                    },
                ))
            except Exception:
                # Schema drift across substrate versions; skip
                # gracefully rather than crashing the demo.
                continue

        if not hyps:
            continue

        try:
            wf = WaveFunction(
                object_id=b.entity_id,
                label=b.label,
                stream_id=f"video_entity_{b.entity_id}",
                timestamp=now,
                hypotheses=tuple(hyps),
                action_arm=None,
            )
        except Exception:
            continue

        per_entity_wfs.append(wf)
        # Track BOTH the substrate-side hypothesis_id (UUID, used in
        # branch_refs for substrate lookups) AND the human-readable
        # label (used for our continue/accelerate/decelerate
        # heuristic off-diagonal logic).
        per_entity_hyp_ids.append(tuple(h.hypothesis_id for h in hyps))
        for h in hyps:
            uuid_to_label[h.hypothesis_id] = h.label

    if not per_entity_wfs:
        return None

    # Build joint hypotheses as the Cartesian product across entities.
    # For 3 entities × 3 hypotheses = 27 joint cells; manageable.
    joint_hyps: list[Any] = []

    def _cartesian(idx_sets: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
        if not idx_sets:
            return [()]
        out: list[tuple[str, ...]] = [()]
        for s in idx_sets:
            out = [prefix + (item,) for prefix in out for item in s]
        return out

    entity_ids = tuple(b.entity_id for b in bundles[:len(per_entity_wfs)])
    weights_per_entity = [
        b.hypothesis_weights for b in bundles[:len(per_entity_wfs)]
    ]

    for combo in _cartesian(per_entity_hyp_ids):
        # Joint weight = product of per-entity weights (independence
        # assumption — off-diagonal couplings will introduce
        # correlation later).
        branch_refs = {
            entity_ids[i]: combo[i] for i in range(len(combo))
        }
        joint_weight = 1.0
        for i, hyp_id in enumerate(combo):
            # Find weight by looking up hyp_id in hypothesis_ids
            try:
                h_idx = per_entity_hyp_ids[i].index(hyp_id)
                joint_weight *= weights_per_entity[i][h_idx]
            except (ValueError, IndexError):
                joint_weight *= 1.0 / max(len(per_entity_hyp_ids[i]), 1)
        try:
            joint_hyps.append(JointBranchHypothesis(
                branch_refs=branch_refs,
                weight=joint_weight,
            ))
        except Exception:
            continue

    if not joint_hyps:
        return None

    # Off-diagonal couplings: small heuristic correlations.
    # For each pair of joint hypotheses, if both are "continue +
    # continue" for two entities, +0.1; if one is "accelerate" while
    # the partner is "decelerate", -0.1. Cap total off-diagonal
    # entries to avoid blow-up.
    offdiag_entries: list[Any] = []
    n_joint = len(joint_hyps)
    max_pairs = 12  # keep it manageable
    pair_count = 0

    for i in range(n_joint):
        if pair_count >= max_pairs:
            break
        for j in range(i + 1, n_joint):
            if pair_count >= max_pairs:
                break
            refs_i = joint_hyps[i].branch_refs
            refs_j = joint_hyps[j].branch_refs

            # refs_i/refs_j map entity_id → hypothesis_id (UUID); we
            # use the side-channel uuid_to_label map to recover the
            # human-readable category for the heuristic.
            def _label_for(uuid_str: str) -> str:
                return uuid_to_label.get(uuid_str, "")

            # Count "continue" overlaps and "accel-decel" anti-overlaps
            cont_overlap = 0
            ad_anti = 0
            for ent in refs_i:
                li = _label_for(refs_i[ent])
                lj = _label_for(refs_j.get(ent, ""))
                if "continue" in li and "continue" in lj:
                    cont_overlap += 1
                if (
                    ("accelerate" in li and "decelerate" in lj)
                    or ("decelerate" in li and "accelerate" in lj)
                ):
                    ad_anti += 1

            amp = 0.0
            # Positive coupling when any entity shares the "continue"
            # assignment across both joint cells — entities tend to
            # maintain their respective trajectories together.
            if cont_overlap >= 1:
                amp = 0.10
            # Anti-correlation overrides only when an accelerate↔
            # decelerate flip happens AND there's no shared
            # "continue" cell (in which case both patterns coexist
            # weakly and we let the positive coupling win).
            if ad_anti >= 1 and cont_overlap == 0:
                amp = -0.10

            if abs(amp) < 1e-9:
                continue

            try:
                offdiag_entries.append(
                    OffDiagonalEntry(row=i, col=j, amplitude=complex(amp, 0.0))
                )
                offdiag_entries.append(
                    OffDiagonalEntry(
                        row=j, col=i,
                        amplitude=complex(amp, 0.0).conjugate(),
                    )
                )
                pair_count += 1
            except Exception:
                continue

    try:
        jwf = JointWaveFunction(
            entity_ids=entity_ids,
            hypotheses=tuple(joint_hyps),
            off_diagonal_couplings=tuple(offdiag_entries),
        )
        return jwf
    except Exception:
        return None


def evolve_entity_joint(
    jwf: Any,
    time_horizon_steps: int = 6,
    decoherence_rate: float = 0.08,
) -> dict[str, Any]:
    """Apply LindbladOperator to the entity joint wavefunction over
    `time_horizon_steps` ticks.

    Returns dict with:
      - n_joint_hypotheses
      - off_diagonal_decay_series: per-pair (i,j) magnitude over ticks
      - skipped: bool + reason if anything went wrong
    """
    if jwf is None:
        return {"skipped": True, "reason": "no_jwf"}

    omytea, err = _load_omytea_substrate()
    if omytea is None:
        return {"skipped": True, "reason": err or "no_substrate"}

    LindbladOperator = omytea["LindbladOperator"]
    OperatorContext = omytea["OperatorContext"]

    if not jwf.off_diagonal_couplings:
        return {"skipped": True, "reason": "no_off_diagonals"}

    lindblad = LindbladOperator(decoherence_rate=decoherence_rate)
    ctx = OperatorContext(scenario_name="video_entity_joint", tick=0)

    snapshots: list[dict[str, Any]] = []
    current = jwf
    for t in range(time_horizon_steps + 1):
        entries = []
        for entry in current.off_diagonal_couplings:
            entries.append({
                "row": entry.row,
                "col": entry.col,
                "magnitude": abs(entry.amplitude),
            })
        snapshots.append({"tick": t, "entries": entries})

        if t < time_horizon_steps:
            try:
                current = lindblad.evolve(current, dt=1.0, ctx=ctx)
            except Exception as exc:
                return {
                    "skipped": True,
                    "reason": f"lindblad_evolve_failed: {exc}",
                    "partial_snapshots": snapshots,
                }

    return {
        "skipped": False,
        "n_joint_hypotheses": len(jwf.hypotheses),
        "n_off_diagonal_pairs": len(jwf.off_diagonal_couplings) // 2,
        "snapshots": snapshots,
        "time_horizon_steps": time_horizon_steps,
        "decoherence_rate": decoherence_rate,
    }


__all__ = [
    "EntityHypothesisBundle",
    "build_entity_hypothesis_bundles",
    "build_joint_wavefunction",
    "evolve_entity_joint",
]
