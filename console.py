"""Core Omytea integration — BeliefProgram → WaveFunction → joint hypothesis.

Bridges between the compiler.py output and Omytea's quantum substrate:
- BeliefProgram branches → WaveFunction sparse categorical state
- joint_offdiag → JointWaveFunction off-diagonal entries
- Pearl rung-2 sensitivity → action_arm markers (associational vs
  interventional belief states)

Falls back to a pure-dict representation when Omytea isn't importable
(OMYTEA_CONSOLE_MOCK=1 mode), so the demo runs offline.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any

from compiler import CompiledBeliefProgram


def _load_omytea_types() -> tuple[dict[str, Any] | None, str | None]:
    """Load Omytea substrate types at call time.

    Mock/non-mock mode is controlled by an environment variable that tests
    intentionally switch per test. Import-time caching would make the result
    order-dependent, so this function checks the current environment every
    time a prediction is converted.
    """
    if os.environ.get("OMYTEA_CONSOLE_MOCK") == "1":
        return None, None

    try:
        from datetime import datetime, timezone  # type: ignore
        from omytea.quantum import WaveFunction, StateHypothesis  # type: ignore
        from omytea.joint_belief import (  # type: ignore
            JointBranchHypothesis,
            JointWaveFunction,
            OffDiagonalEntry,
        )
        from omytea.models import Position  # type: ignore
    except ImportError as exc:
        return None, str(exc)

    return {
        "datetime": datetime,
        "timezone": timezone,
        "WaveFunction": WaveFunction,
        "StateHypothesis": StateHypothesis,
        "JointBranchHypothesis": JointBranchHypothesis,
        "JointWaveFunction": JointWaveFunction,
        "OffDiagonalEntry": OffDiagonalEntry,
        "Position": Position,
    }, None


@dataclass(frozen=True, slots=True)
class ConsoleHypothesis:
    """Pure-dict representation of a single branch hypothesis.

    Mirrors the structure of `omytea.quantum.StateHypothesis` but stays
    importable without Omytea installed. Acts as the user-facing record.

    ``branch_type`` partitions branches into "wishful" (best-case
    plausible anchor; user emotional engagement hook), "worst" (worst-case
    plausible anchor; preventive-action hook), and "realistic" (the
    middle distribution). Exactly one wishful + one worst per prediction;
    the rest realistic. Anchor branches were added to address the gap
    between "balanced realistic distribution" (mathematically clean but
    emotionally flat) and the engagement needed for repeat use.
    """

    label: str
    narrative: str
    probability: float  # diagonal ρ_kk
    key_uncertainty_driver: str
    depends_on_decision: str | None  # Pearl rung-2 action_arm marker
    branch_type: str = "realistic"  # "wishful" | "worst" | "realistic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "narrative": self.narrative,
            "probability": self.probability,
            "key_uncertainty_driver": self.key_uncertainty_driver,
            "depends_on_decision": self.depends_on_decision,
            "branch_type": self.branch_type,
        }


@dataclass(frozen=True, slots=True)
class ConsoleOffDiagonal:
    """Joint hypothesis correlation between two branches.

    Maps to `omytea.joint_belief.OffDiagonalEntry`. Carries the
    interpretable "coherence_strength" (signed in [-1, 1]); positive =
    co-occur, negative = anti-correlated.
    """

    branch_a: str
    branch_b: str
    coherence_strength: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_a": self.branch_a,
            "branch_b": self.branch_b,
            "coherence_strength": self.coherence_strength,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class ConsoleResult:
    """Top-level result of compiling user input into a hypothesis space."""

    scenario: str
    decision_options: list[str]
    hypotheses: list[ConsoleHypothesis]
    joint_offdiag: list[ConsoleOffDiagonal]
    recommended_evidence: list[dict[str, Any]]
    omytea_wavefunction: Any = None  # populated when Omytea is importable
    omytea_joint_wavefunction: Any = None
    used_omytea_substrate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "decision_options": self.decision_options,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "joint_offdiag": [o.to_dict() for o in self.joint_offdiag],
            "recommended_evidence": list(self.recommended_evidence),
            "used_omytea_substrate": self.used_omytea_substrate,
        }


def belief_program_to_console(
    program: CompiledBeliefProgram,
) -> ConsoleResult:
    """Convert a CompiledBeliefProgram into a ConsoleResult.

    When Omytea is importable, also constructs WaveFunction +
    JointWaveFunction objects (for downstream operator-pipeline use).
    Otherwise returns the pure-dict view only.
    """
    hypotheses = [
        ConsoleHypothesis(
            label=str(b["label"]),
            narrative=str(b.get("narrative", "")),
            probability=float(b.get("probability_prior", 0.0)),
            key_uncertainty_driver=str(b.get("key_uncertainty_driver", "")),
            depends_on_decision=b.get("depends_on_decision"),
            branch_type=str(b.get("branch_type", "realistic")),
        )
        for b in program.branches
    ]

    joint = [
        ConsoleOffDiagonal(
            branch_a=str(j["branch_a"]),
            branch_b=str(j["branch_b"]),
            coherence_strength=float(j.get("coherence_strength", 0.0)),
            rationale=str(j.get("rationale", "")),
        )
        for j in program.joint_offdiag
    ]

    omytea_wf = None
    omytea_jwf = None
    used_omytea = False

    omytea_types, _import_error = _load_omytea_types()
    if omytea_types is not None:
        try:
            datetime = omytea_types["datetime"]
            timezone = omytea_types["timezone"]
            WaveFunction = omytea_types["WaveFunction"]
            StateHypothesis = omytea_types["StateHypothesis"]
            JointBranchHypothesis = omytea_types["JointBranchHypothesis"]
            JointWaveFunction = omytea_types["JointWaveFunction"]
            OffDiagonalEntry = omytea_types["OffDiagonalEntry"]
            Position = omytea_types["Position"]

            # Conforms to Omytea's real type signatures from
            # src/omytea/quantum.py + joint_belief.py + models.py.
            # StateHypothesis takes (object_id, label, stream_id,
            # timestamp, position, weight, ...); OffDiagonalEntry takes
            # integer row/col (not label strings) and requires explicit
            # Hermitian pairs.

            now = datetime.now(tz=timezone.utc)
            stream_id = f"personal_future_{program.scenario}"
            entity_id = "user_future_self"

            # Build StateHypothesis per branch. weight= carries the probability
            # (StateHypothesis.probability is a @property reading .weight).
            # Position is required but irrelevant for a non-spatial scenario;
            # we use a degenerate Position(0,0) per StateHypothesis with
            # branch_label encoding the scenario label.
            hyps: list = []
            for h in hypotheses:
                hyps.append(
                    StateHypothesis(
                        object_id=entity_id,
                        label=h.label,
                        stream_id=stream_id,
                        timestamp=now,
                        position=Position(x=0.0, y=0.0, space="abstract"),
                        weight=h.probability,
                        branch_label=h.label,
                        # Store narrative + uncertainty driver in attributes for
                        # downstream inspection (per StateHypothesis schema).
                        attributes={
                            "narrative": h.narrative,
                            "key_uncertainty_driver": h.key_uncertainty_driver,
                            "depends_on_decision": h.depends_on_decision or "",
                            "branch_type": h.branch_type,
                        },
                    )
                )

            # Pearl rung-2 action_arm: if all branches share the same
            # depends_on_decision, lift it; else leave None (associational).
            arms = {h.depends_on_decision for h in hypotheses if h.depends_on_decision}
            omytea_wf = WaveFunction(
                object_id=entity_id,
                label="user_future_self",
                stream_id=stream_id,
                timestamp=now,
                hypotheses=tuple(hyps),
                # If branches all share decision arm, mark it; else None.
                action_arm=(next(iter(arms)) if len(arms) == 1 else None),
            )

            # JointWaveFunction with single-entity self-joint to carry
            # the off_diagonal_couplings between branch indices. We model
            # off-diagonals as the coherence between *futures of the same
            # entity* (the user) representing scenario coherence.
            # Build joint hypotheses (one per branch, ref to itself).
            joint_hyps: list = []
            for h_obj in hyps:
                joint_hyps.append(
                    JointBranchHypothesis(
                        branch_refs={entity_id: h_obj.hypothesis_id},
                        weight=h_obj.weight,
                    )
                )

            # Map branch_label → integer index for off_diagonal_couplings.
            label_to_idx = {h.label: i for i, h in enumerate(hypotheses)}
            offdiag_entries: list = []
            for o in joint:
                if o.branch_a not in label_to_idx or o.branch_b not in label_to_idx:
                    # LLM returned a coupling for a branch label that doesn't
                    # exist; honest-skip rather than crash.
                    continue
                row_idx = label_to_idx[o.branch_a]
                col_idx = label_to_idx[o.branch_b]
                if row_idx == col_idx:
                    continue  # off-diagonal requires row != col
                amp = complex(o.coherence_strength, 0.0)
                # Hermitian pair: append both (row, col, a) AND (col, row, a*)
                # per OffDiagonalEntry docstring requirement.
                offdiag_entries.append(
                    OffDiagonalEntry(row=row_idx, col=col_idx, amplitude=amp)
                )
                offdiag_entries.append(
                    OffDiagonalEntry(row=col_idx, col=row_idx, amplitude=amp.conjugate())
                )

            omytea_jwf = JointWaveFunction(
                entity_ids=(entity_id,),
                hypotheses=tuple(joint_hyps),
                off_diagonal_couplings=tuple(offdiag_entries),
            )
            used_omytea = True
        except Exception as exc:  # noqa: BLE001 — defensive in MVP
            # Honest-fallback: if Omytea import succeeds but construction
            # fails (e.g. schema drift between this package and the
            # vendored Omytea version), keep the pure-dict result and
            # continue rather than crashing the user-facing UI.
            print(
                f"[omytea-personal-console] WARNING: Omytea construction "
                f"failed: {exc}. Falling back to pure-dict result."
            )
            import traceback
            traceback.print_exc()

    return ConsoleResult(
        scenario=program.scenario,
        decision_options=program.decision_options,
        hypotheses=hypotheses,
        joint_offdiag=joint,
        recommended_evidence=program.recommended_evidence,
        omytea_wavefunction=omytea_wf,
        omytea_joint_wavefunction=omytea_jwf,
        used_omytea_substrate=used_omytea,
    )


def compute_calibration_delta(
    prediction_branches: list[ConsoleHypothesis],
    actual_outcome: dict[str, float],
) -> dict[str, float]:
    """Compute Brier score + log-loss between a prediction and the
    actual observed outcome.

    Args:
        prediction_branches: the original branch list with probabilities.
        actual_outcome: dict mapping branch_label → 1.0 (if that branch
            materialized) or 0.0 (didn't). Multiple branches may have
            positive support (e.g., 0.7 to A, 0.3 to B if reality
            partially matched both).

    Returns:
        Dict with 'brier' (lower=better) and 'log_loss' (lower=better).
    """
    # Normalize actual_outcome to sum to 1.0
    total = sum(actual_outcome.values())
    if total <= 0:
        return {"brier": 1.0, "log_loss": float("inf")}
    actual_normalized = {k: v / total for k, v in actual_outcome.items()}

    brier = 0.0
    log_loss = 0.0
    for h in prediction_branches:
        p = h.probability
        y = actual_normalized.get(h.label, 0.0)
        brier += (p - y) ** 2
        if y > 0:
            log_loss -= y * math.log(max(p, 1e-9))

    return {"brier": round(brier, 6), "log_loss": round(log_loss, 6)}


def availability_status() -> dict[str, Any]:
    """Diagnostic — show whether Omytea is importable + mock-mode state."""
    omytea_types, import_error = _load_omytea_types()
    return {
        "omytea_available": omytea_types is not None,
        "omytea_import_error": import_error,
        "mock_mode": os.environ.get("OMYTEA_CONSOLE_MOCK") == "1",
    }


# ============================================================
# C1 — Substrate runtime: Lindblad evolution over time horizon
# ============================================================
#
# Until C1, console.py only CONSTRUCTED WaveFunction + JointWaveFunction
# but never EVOLVED them. The off-diagonal coherence numbers shown to
# the user were static — taken as-is from the LLM compiler output.
#
# C1 wires up LindbladOperator (substrate v3.3) to actually evolve
# off-diagonal coherences over the user's time_horizon. The user can
# then see how branch correlations decay as we approach the decision
# horizon — concrete demonstration of the quantum-substrate's value vs
# pure LLM output.
#
# Interpretation for personal-future-decision scenarios:
#   - Branch energies E_k = -log(p_k) (information-theoretic surprisal)
#   - Decoherence rate γ_kl = base rate, default 0.05/month, tunable
#   - dt = 1 step = 1 month
#   - Diagonal probabilities ρ_kk: unchanged by Lindblad (per protocol;
#     domain operators evolve those, Lindblad only touches off-diag)
#
# What this gives the UI:
#   "Your branches are 0.55 correlated NOW. In 6 months, that decays to
#    0.30 — meaning evidence will increasingly distinguish them."
#
# HamiltonianOperator NOT used here: our scenarios use degenerate
# Position(0,0, space='abstract') — symplectic leapfrog over (q,p) is
# a no-op. The Hamiltonian backbone applies to physics scenarios
# (pedestrian flow, curved path, etc.); irrelevant for personal-decision.


def _parse_time_horizon_to_steps(time_horizon: str) -> int:
    """Convert form-input time_horizon ("3 months" / "6 months" /
    "12 months" / "24 months") to integer N steps where dt = 1 month."""
    if not time_horizon:
        return 6  # default
    t = time_horizon.lower().strip()
    # Match in descending order to catch "12" before "1", "24" before "2"
    for n in (24, 12, 6, 3):
        if str(n) in t:
            return n
    # Fallback: extract first integer if non-standard input
    import re
    m = re.search(r"\d+", t)
    if m:
        return max(1, min(36, int(m.group())))
    return 6


def evolve_offdiagonal_coherence(
    result: ConsoleResult,
    time_horizon_months: int = 6,
    decoherence_rate_per_month: float = 0.05,
    use_branch_energies: bool = True,
) -> dict[str, Any]:
    """C1 substrate runtime: evolve the JointWaveFunction's off-diagonal
    coherences via Lindblad over `time_horizon_months` steps.

    Args:
      result: ConsoleResult with a populated `omytea_joint_wavefunction`
        (i.e., real Omytea substrate was constructed in
        `belief_program_to_console`).
      time_horizon_months: how many monthly ticks to evolve over.
      decoherence_rate_per_month: γ — uniform decoherence rate across
        all branch pairs. 0.05/month ≈ 30% coherence decay per 6 months.
      use_branch_energies: if True, branch energies E_k = -log(p_k)
        drive unitary rotation of off-diagonals (information-theoretic
        surprisal). If False, only decay (no rotation).

    Returns:
      Dict with keys:
        - "skipped": bool — True if no substrate or no off-diagonals
        - "evolved": list of {tick, off_diagonal_entries} snapshots at
          tick=0, 1, 2, ..., time_horizon_months
        - "evolved_wavefunction_final": the final-state JointWaveFunction
        - "decoherence_rate": echoed
        - "n_steps": echoed
        - "use_branch_energies": echoed

    Honest-fallback: if result wasn't built on real Omytea substrate,
    returns {"skipped": True, ...} — UI degrades gracefully.
    """
    if not result.used_omytea_substrate or result.omytea_joint_wavefunction is None:
        return {
            "skipped": True,
            "reason": "no_substrate",
            "decoherence_rate": decoherence_rate_per_month,
        }

    jwf = result.omytea_joint_wavefunction
    if not jwf.off_diagonal_couplings:
        return {
            "skipped": True,
            "reason": "no_off_diagonals",
            "decoherence_rate": decoherence_rate_per_month,
        }

    # Load LindbladOperator at call time (avoid module-import-time
    # coupling — Do-Not-Repeat for the import-pollution bug pattern).
    try:
        from omytea.dynamics.lindblad import LindbladOperator  # type: ignore
        from omytea.dynamics.protocol import OperatorContext  # type: ignore
    except ImportError:
        return {
            "skipped": True,
            "reason": "omytea_dynamics_not_importable",
            "decoherence_rate": decoherence_rate_per_month,
        }

    # Build branch_energies from the result's hypotheses.
    # E_k = -log(p_k); higher probability → lower "energy" (more stable).
    # NB: Lindblad._joint_energy looks up by hypothesis_id (UUID),
    # NOT by branch label. The UUIDs are auto-generated when
    # belief_program_to_console constructs each StateHypothesis. So we
    # must key the energies dict by the UUID coming off the
    # constructed WaveFunction, not by the ConsoleHypothesis.label
    # string.
    energies: dict[str, float] | None = None
    if use_branch_energies and result.omytea_wavefunction is not None:
        wf = result.omytea_wavefunction
        energies = {
            h.hypothesis_id: -math.log(max(h.weight, 1e-9))
            for h in wf.hypotheses
        }

    lindblad = LindbladOperator(
        decoherence_rate=decoherence_rate_per_month,
        branch_energies=energies,
    )
    ctx = OperatorContext(scenario_name=result.scenario, tick=0)
    idx_to_label = [h.label for h in result.hypotheses]

    def _capture_snapshot(jwf_state: Any, tick: int) -> dict[str, Any]:
        """Serialize current off-diagonal state for one tick."""
        entries = []
        for entry in jwf_state.off_diagonal_couplings:
            row_label = (idx_to_label[entry.row]
                         if 0 <= entry.row < len(idx_to_label)
                         else f"idx{entry.row}")
            col_label = (idx_to_label[entry.col]
                         if 0 <= entry.col < len(idx_to_label)
                         else f"idx{entry.col}")
            entries.append({
                "row_label": row_label,
                "col_label": col_label,
                "amplitude_real": entry.amplitude.real,
                "amplitude_imag": entry.amplitude.imag,
                "amplitude_magnitude": abs(entry.amplitude),
            })
        return {"tick": tick, "off_diagonal_entries": entries}

    # Tick 0 = initial state, no evolution
    snapshots: list[dict[str, Any]] = [_capture_snapshot(jwf, 0)]

    # Tick 1..N: evolve one month at a time
    current = jwf
    for t in range(1, time_horizon_months + 1):
        current = lindblad.evolve(current, dt=1.0, ctx=ctx)
        snapshots.append(_capture_snapshot(current, t))

    return {
        "skipped": False,
        "evolved": snapshots,
        "evolved_wavefunction_final": current,
        "decoherence_rate": decoherence_rate_per_month,
        "n_steps": time_horizon_months,
        "use_branch_energies": use_branch_energies,
    }


def evolve_from_time_horizon_string(
    result: ConsoleResult,
    time_horizon_str: str,
    decoherence_rate_per_month: float = 0.05,
) -> dict[str, Any]:
    """Convenience: parse the form's time_horizon string + evolve."""
    n_steps = _parse_time_horizon_to_steps(time_horizon_str)
    return evolve_offdiagonal_coherence(
        result, n_steps, decoherence_rate_per_month,
    )


def normalize_evidence_record(raw: dict[str, Any]) -> dict[str, Any]:
    """v4.16 P5 — normalize a recommended-evidence dict to the new
    Option-C ΔP schema regardless of source.

    Output schema:
      - "evidence_label": str
      - "expected_delta_p": float — percentage points in [0, 100]
      - "target_branch": str | None
      - "rationale": str

    Reads from:
      - Modern: ``raw["expected_delta_p"]`` directly (already pp).
      - Legacy: ``raw["sensitivity"]`` (0-1 float) → multiplied by 100
        to convert to pp.

    Any extra fields on the record (e.g. older "key_uncertainty") are
    dropped — call-sites that need them should read ``raw`` directly.
    """
    label = str(raw.get("evidence_label", "unknown"))
    target = raw.get("target_branch")
    if target is not None:
        target = str(target)
    rationale = str(raw.get("rationale", ""))

    # Prefer new schema; fall back to legacy.
    if "expected_delta_p" in raw and raw["expected_delta_p"] is not None:
        delta_p = float(raw["expected_delta_p"])
    elif "sensitivity" in raw and raw["sensitivity"] is not None:
        delta_p = float(raw["sensitivity"]) * 100.0
    else:
        delta_p = 0.0

    # Clamp to [0, 100] — anything outside is malformed and would
    # render nonsensically.
    delta_p = max(0.0, min(100.0, delta_p))

    return {
        "evidence_label": label,
        "expected_delta_p": delta_p,
        "target_branch": target,
        "rationale": rationale,
    }


def normalize_evidence_list(
    raw_list: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize every record + sort by descending ΔP."""
    normalized = [normalize_evidence_record(r) for r in raw_list]
    normalized.sort(key=lambda r: -r["expected_delta_p"])
    return normalized


# ============================================================
# v4.16 P4 — Human-narrative presentation helpers
# ============================================================


_STORYFORM_PREFIX_BY_TYPE: dict[str, str] = {
    "wishful": "If everything aligns, ",
    "worst": "If things go the worst plausible way, ",
    "realistic": "In this future, ",
}


def storyform_narrative(narrative: str, branch_type: str = "realistic") -> str:
    """v4.16 P4 — coerce an LLM narrative sentence into a second-person
    story-form opener so the user reads it as "a future you might
    live in" rather than "a row in a table".

    The transformation is intentionally light-touch:

    1. Strip leading whitespace.
    2. If the narrative already starts with an explicit "In this
       future" / "If everything" / "If things go" cue (case-insensitive
       prefix match against the canonical openers), leave it alone —
       the LLM did the work.
    3. Otherwise prepend the branch-type-appropriate opener and
       lowercase the next character so the result reads as one
       sentence ("In this future, accept the offer and ...").

    The opener for realistic ("In this future, ") matches the
    V4_16 spec quote exactly. Wishful + worst openers add an
    emotional cue ("if everything aligns" / "if things go the worst
    plausible way") that matches the section headers in app.py.

    Returns the empty string unchanged for empty input (caller
    decides whether to skip rendering).
    """
    s = (narrative or "").lstrip()
    if not s:
        return ""

    bt = branch_type if branch_type in _STORYFORM_PREFIX_BY_TYPE else "realistic"
    opener = _STORYFORM_PREFIX_BY_TYPE[bt]

    # If the first sentence already starts with one of the canonical
    # cues, leave it alone (LLM may have written it that way; double-
    # prefixing reads awkwardly).
    s_lower = s.lower()
    for known_opener in _STORYFORM_PREFIX_BY_TYPE.values():
        if s_lower.startswith(known_opener.lower()):
            return s

    # Also catch lighter cues that mean "story already started".
    for cue in ("in this", "if everything", "if things go",
                "imagine", "picture this"):
        if s_lower.startswith(cue):
            return s

    # Prepend opener; lowercase the first character of the existing
    # narrative so it merges into one grammatical sentence — unless
    # that first character is an acronym (e.g. "EIN") in which case
    # leave casing alone.
    first = s[0]
    rest = s[1:]
    if first.isupper() and len(s) > 1 and s[1].isupper():
        # ALL-CAPS or acronym start; don't munge case.
        merged_tail = s
    else:
        merged_tail = first.lower() + rest
    return opener + merged_tail


def build_branch_comparison_rows(
    result: ConsoleResult,
) -> list[dict[str, Any]]:
    """v4.16 P4 — flatten ConsoleResult into a table-ready list of
    dicts the UI can render via ``st.dataframe`` for the
    side-by-side comparison view.

    Each row has: branch_type (sortable: wishful → realistic → worst),
    label, probability_pct (display string), decision, key_driver,
    narrative_preview (truncated).

    Sort order: wishful first, realistic by descending probability
    second, worst last — matches the card layout's emotional reading
    order (hope → reality → caution).
    """
    type_order = {"wishful": 0, "realistic": 1, "worst": 2}
    rows: list[dict[str, Any]] = []
    for h in result.hypotheses:
        narrative = h.narrative or ""
        preview = (
            narrative if len(narrative) <= 120
            else narrative[:119].rstrip() + "…"
        )
        rows.append({
            "_sort_key": (
                type_order.get(h.branch_type, 1),
                -h.probability,
            ),
            "Type": h.branch_type,
            "Branch": h.label,
            "Probability": f"{h.probability * 100:.1f}%",
            "Decision": h.depends_on_decision or "—",
            "Key driver": h.key_uncertainty_driver,
            "Narrative (preview)": preview,
        })
    rows.sort(key=lambda r: r["_sort_key"])
    for r in rows:
        r.pop("_sort_key", None)
    return rows


def _branch_characteristic_time(
    hyp: ConsoleHypothesis, horizon_months: float,
) -> float:
    """v4.16 P3 — heuristic 'when in the time-horizon does this branch
    play out' anchor point.

    Wishful branches → 0.2 × horizon (best-case is "things click fast").
    Realistic branches → 0.5 × horizon (mid-horizon, the canonical
    decision-outcome time).
    Worst branches → 0.7 × horizon (worst-case takes longer to
    crystallize and harder to course-correct).

    This is a *rule-based* anchor for v4.16. v4.17+ can replace it with
    an LLM-extracted "characteristic_time_months" field per branch
    (sketch left in compiler SYSTEM_PROMPT comment).
    """
    bt = hyp.branch_type
    if bt == "wishful":
        return 0.20 * horizon_months
    if bt == "worst":
        return 0.70 * horizon_months
    return 0.50 * horizon_months


def build_continuous_distribution(
    result: ConsoleResult,
    time_horizon_months: float,
    n_points: int = 100,
    sigma_fraction: float = 0.15,
) -> dict[str, Any] | None:
    """v4.16 P3 — turn the discrete-branch ConsoleResult into a
    continuous density over the user's time horizon.

    Algorithm:
      1. For each branch, derive a characteristic time
         (via _branch_characteristic_time) and a Gaussian kernel of
         width σ = ``sigma_fraction × horizon``.
      2. Density(t) = Σ over branches of (p_branch × N(t; μ_branch, σ)).
      3. Sampled at ``n_points`` evenly spaced from 0 → horizon.

    Returns:
      None if there are no hypotheses (caller should hide the chart).
      Dict with:
        - "x_months": list[float] — sample points along the time axis
        - "density": list[float] — total density at each sample point
        - "per_branch_density": dict[branch_label → list[float]] —
            each branch's Gaussian contribution (so the UI can overlay
            shaded per-branch areas if it wants)
        - "characteristic_times": dict[branch_label → float] — μ used
        - "sigma_months": float — σ used
        - "horizon_months": float — echoed
        - "n_points": int — echoed

    Edge case: horizon ≤ 0 still produces a degenerate dict with a
    single sample at t=0; the UI is expected to skip rendering when
    n_points ≤ 1.
    """
    if not result.hypotheses:
        return None
    if n_points < 2 or time_horizon_months <= 0:
        return {
            "x_months": [0.0],
            "density": [0.0],
            "per_branch_density": {h.label: [0.0] for h in result.hypotheses},
            "characteristic_times": {
                h.label: 0.0 for h in result.hypotheses
            },
            "sigma_months": 0.0,
            "horizon_months": float(time_horizon_months),
            "n_points": 1,
        }

    sigma = max(0.05, sigma_fraction * time_horizon_months)
    step = time_horizon_months / (n_points - 1)
    x = [i * step for i in range(n_points)]

    per_branch: dict[str, list[float]] = {}
    char_times: dict[str, float] = {}
    inv_two_sigma_sq = 1.0 / (2.0 * sigma * sigma)
    norm = 1.0 / (sigma * math.sqrt(2.0 * math.pi))

    for h in result.hypotheses:
        mu = _branch_characteristic_time(h, time_horizon_months)
        char_times[h.label] = mu
        contrib = [
            h.probability * norm * math.exp(
                -((xi - mu) ** 2) * inv_two_sigma_sq
            )
            for xi in x
        ]
        per_branch[h.label] = contrib

    density = [
        sum(per_branch[lbl][i] for lbl in per_branch)
        for i in range(n_points)
    ]

    return {
        "x_months": x,
        "density": density,
        "per_branch_density": per_branch,
        "characteristic_times": char_times,
        "sigma_months": sigma,
        "horizon_months": float(time_horizon_months),
        "n_points": n_points,
    }


def build_decision_timeline_mermaid(
    result: ConsoleResult,
    time_horizon_label: str = "decision horizon",
) -> str:
    """v4.16 P4 — synthesize a tiny Mermaid timeline diagram showing
    each decision option as a track + its dependent branches as nodes
    along the user's time horizon.

    The output is the body of a ``mermaid`` flowchart — Streamlit can
    render it via the ``mermaid`` library or display as a code block
    if the lib isn't installed. The diagram is deliberately compact
    (one decision → 1-3 branch terminals) so it adds visual structure
    without forcing the user to read a complex graph.
    """
    lines: list[str] = [
        "flowchart LR",
        f"    Now([Now]) --> Horizon[{time_horizon_label}]",
    ]
    seen_options: set[str] = set()
    for opt in result.decision_options:
        opt_safe = opt.replace(" ", "_")
        if opt_safe in seen_options:
            continue
        seen_options.add(opt_safe)
        # Add an "option" node and connect from Horizon.
        lines.append(f"    Horizon --> Opt_{opt_safe}([Decide: {opt}])")
        # For each hypothesis dependent on this option, add a leaf.
        for h in result.hypotheses:
            if h.depends_on_decision != opt:
                continue
            leaf_id = (f"L_{h.label}".replace(" ", "_")
                       [:40])  # short, deterministic
            kind_tag = (
                "🌟" if h.branch_type == "wishful"
                else "⚠️" if h.branch_type == "worst"
                else "📊"
            )
            label_text = (
                f"{kind_tag} {h.label} ({h.probability * 100:.0f}%)"
            )
            lines.append(f"    Opt_{opt_safe} --> {leaf_id}[\"{label_text}\"]")
    # Standalone hypotheses (no depends_on_decision) — connect to Horizon.
    for h in result.hypotheses:
        if h.depends_on_decision:
            continue
        leaf_id = (f"L_{h.label}".replace(" ", "_")[:40])
        kind_tag = (
            "🌟" if h.branch_type == "wishful"
            else "⚠️" if h.branch_type == "worst"
            else "📊"
        )
        label_text = f"{kind_tag} {h.label} ({h.probability * 100:.0f}%)"
        lines.append(f"    Horizon --> {leaf_id}[\"{label_text}\"]")
    return "\n".join(lines)


def format_delta_p(expected_delta_p: float) -> str:
    """Render ΔP in the canonical Option-C surface form: '±N pp'
    rounded to the nearest whole percentage point.

    Examples:
      18.0  → "±18 pp"
      0.0   →  "±0 pp"
      99.9  → "±100 pp"
    """
    pp_int = int(round(expected_delta_p))
    return f"±{pp_int} pp"


def _short_label(label: str, max_len: int = 18) -> str:
    """Truncate a branch label for compact chart legends. Keeps a trailing
    ellipsis when truncation occurred."""
    if len(label) <= max_len:
        return label
    return label[: max_len - 1] + "…"


def build_coherence_chart_data(
    result: ConsoleResult,
    time_horizon_months: int = 6,
    decoherence_rate_per_month: float = 0.05,
    use_branch_energies: bool = False,
) -> dict[str, Any] | None:
    """C1 UI helper — shape Lindblad evolution into chart-ready dicts.

    Wraps `evolve_offdiagonal_coherence` and:
      - deduplicates Hermitian pairs (we kept both (a,b) and (b,a) when
        constructing the JointWaveFunction; the chart only needs one)
      - truncates branch labels for compact legends
      - extracts initial / final magnitudes per pair for a summary table
      - bolts the human-readable rationale (from result.joint_offdiag)
        back onto the series so the UI can show "why this pair matters"

    Returns:
      None — if no substrate (caller's UI should render an "n/a" notice).
      dict with keys:
        "tick_labels": ["t=0", "t=1mo", ..., f"t={N}mo"]
        "magnitude_series": {legend_key: [|ρ_ab|(t=0), ..., |ρ_ab|(t=N)]}
        "pairs_summary": list of {pair_a, pair_b, initial, final, decay_pct,
          rationale}
        "n_steps": int
        "decoherence_rate": float
        "use_branch_energies": bool
        "expected_decay_ratio": exp(-γ·N) — analytic decay reference
    """
    evo = evolve_offdiagonal_coherence(
        result,
        time_horizon_months=time_horizon_months,
        decoherence_rate_per_month=decoherence_rate_per_month,
        use_branch_energies=use_branch_energies,
    )
    if evo.get("skipped"):
        return None

    snapshots: list[dict[str, Any]] = evo["evolved"]
    if not snapshots:
        return None

    # Map (a, b) → rationale (from the user-facing off-diagonal records).
    rationale_by_pair: dict[tuple[str, str], str] = {}
    for o in result.joint_offdiag:
        rationale_by_pair[(o.branch_a, o.branch_b)] = o.rationale
        rationale_by_pair[(o.branch_b, o.branch_a)] = o.rationale

    # Collect pairs from tick 0; dedupe by sorted-tuple identity so the
    # Hermitian conjugate of each pair only shows once on the chart.
    initial_entries = snapshots[0]["off_diagonal_entries"]
    seen: set[tuple[str, str]] = set()
    unique_pairs: list[tuple[str, str]] = []
    for entry in initial_entries:
        a = entry["row_label"]
        b = entry["col_label"]
        if a == b:
            continue
        key = tuple(sorted([a, b]))
        if key in seen:
            continue
        seen.add(key)
        unique_pairs.append((a, b))

    # Pull |ρ_ab|(t) for each unique pair across all ticks.
    magnitude_series: dict[str, list[float]] = {}
    pairs_summary: list[dict[str, Any]] = []
    for a, b in unique_pairs:
        magnitudes: list[float] = []
        for snap in snapshots:
            mag = next(
                (e["amplitude_magnitude"]
                 for e in snap["off_diagonal_entries"]
                 if e["row_label"] == a and e["col_label"] == b),
                0.0,
            )
            magnitudes.append(mag)
        legend = f"|({_short_label(a)}, {_short_label(b)})|"
        magnitude_series[legend] = magnitudes
        initial_mag = magnitudes[0]
        final_mag = magnitudes[-1]
        decay_pct = (
            (initial_mag - final_mag) / initial_mag * 100.0
            if initial_mag > 1e-9
            else 0.0
        )
        pairs_summary.append({
            "pair_a": a,
            "pair_b": b,
            "initial": initial_mag,
            "final": final_mag,
            "decay_pct": decay_pct,
            "rationale": rationale_by_pair.get((a, b), ""),
        })

    # Sort pairs_summary by initial magnitude descending so the strongest
    # correlation surfaces first.
    pairs_summary.sort(key=lambda p: -p["initial"])

    tick_labels = [f"t={t}mo" if t > 0 else "t=0"
                   for t in range(time_horizon_months + 1)]

    expected_decay_ratio = math.exp(
        -decoherence_rate_per_month * time_horizon_months
    )

    return {
        "tick_labels": tick_labels,
        "magnitude_series": magnitude_series,
        "pairs_summary": pairs_summary,
        "n_steps": time_horizon_months,
        "decoherence_rate": decoherence_rate_per_month,
        "use_branch_energies": use_branch_energies,
        "expected_decay_ratio": expected_decay_ratio,
    }
