"""LindbladOperator — open-system off-diagonal coherence dynamics.

[OMY-V32 / M S.1 / Acceptance #1] v3.3 full implementation, replacing the
v0.7 identity-on-diagonal skeleton.

DESIGN (folds Lindblad master equation into Omytea categorical-state-lock):

The Lindblad master equation for an open quantum system is:

    dρ/dt = -i [H, ρ] + Σ_n (L_n ρ L_n† - ½ {L_n† L_n, ρ})

where H is the system Hamiltonian (closed-system, unitary part) and L_n are
jump operators (open-system, dissipative part).

For Omytea's discrete categorical-state-lock world states (ADR-003 §4.2):
- The state lives in the branch basis B = {|b_k⟩}
- Diagonal entries ρ_kk = Pr(branch k) are evolved by domain operators
  (Hamiltonian, Educational, Psychological, etc.) — NOT by Lindblad
- Off-diagonal entries ρ_kl (k ≠ l) are coherence terms; Lindblad evolves these

This gives Lindblad a SPECIFIC ROLE in the operator pipeline:
"how do branch coherences evolve under unitary + dissipative dynamics"

For diagonal-in-branch-basis Hamiltonian H = diag(E_1, ..., E_N):
    [H, ρ]_kl = (E_k - E_l) ρ_kl

For dephasing-style jump operators L_n = diag(λ_{n,1}, ..., λ_{n,N}):
    Σ_n (L_n ρ L_n† - ½ {L_n† L_n, ρ})_kl
        = ρ_kl Σ_n [λ_{n,k} λ_{n,l}* - ½(|λ_{n,k}|² + |λ_{n,l}|²)]
        = -ρ_kl Σ_n ½|λ_{n,k} - λ_{n,l}|²    (for real λ_{n,k}, by completing square)
        = -ρ_kl γ_kl    (defining decoherence rate γ_kl ≥ 0)

So the off-diagonal evolution under diagonal Hamiltonian + dephasing jumps:

    dρ_kl/dt = -i(E_k - E_l) ρ_kl - γ_kl ρ_kl
    ρ_kl(t+dt) ≈ ρ_kl(t) · exp(-i(E_k - E_l) dt - γ_kl dt)

This is EXACT in the continuous-time limit (no Trotter error since the
two terms commute on each off-diagonal entry independently). For finite
dt, we use exact exponential (numerically stable, preserves Hermiticity).

Reference: Breuer-Petruccione 2002 §3.4 "The standard Markov master
equation in Lindblad form"; Lindblad 1976; Gorini-Kossakowski-Sudarshan
1976. Inspirations folded into Omytea's existing operator + WaveFunction
+ JointWaveFunction type system. Per ADR-020 §3.2 product feature.

LIMITATIONS (honest-fallback per ADR-006 §3.6):
- Only diagonal Hamiltonian + diagonal (dephasing) jump operators supported.
  Real Lindblad allows arbitrary H + arbitrary L_n; we restrict to the
  practically-relevant case where H/L_n are diagonal in our branch basis.
- Default behavior (no `decoherence_rate_matrix` passed) is the UNIFORM
  single-rate projection-dephasing case `L_k = √γ · |k⟩⟨k|` for
  k = 0..N-1, all with the same `decoherence_rate` γ. Every off-diagonal
  entry (k,l) k≠l decays at the SAME rate γ.
- **v3.4 S2 lifts F-37-H-1**: pass `decoherence_rate_matrix={(k,l): γ_kl}`
  to use per-pair rates. Helper `jump_operators_to_rate_matrix(...)`
  computes the matrix from a list of diagonal jump operators via
  γ_{kl} = ½ Σ_n |λ_{n,k} - λ_{n,l}|² (Breuer-Petruccione 2002 §3.4.5).
  The reference impl in `lindblad_reference.py` is still uniform-only;
  for QuTiP cross-validation of per-pair rates, build matching c_ops
  list there.
- Diagonal probabilities ρ_kk unchanged by this operator (by design — they
  belong to other operators in the pipeline).
- WaveFunction (single-entity, diagonal-only by construction) is unchanged
  through this operator (no off-diagonals to evolve).
- The Hermitian-pair structure of OffDiagonalEntry is preserved
  (if (k,l) has amplitude a, then (l,k) has amplitude a*; both decay/rotate
  consistently).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Mapping

from omytea.dynamics.protocol import BeliefState, JointBeliefState, OperatorContext
from omytea.joint_belief import JointWaveFunction, OffDiagonalEntry
from omytea.models import Observation
from omytea.quantum import Velocity, WaveFunction


@dataclass(frozen=True, slots=True)
class LindbladOperator:
    """Open-system coherence dynamics: unitary rotation + decoherence damping.

    For each off-diagonal entry (row, col, amplitude):
        amplitude(t+dt) = amplitude(t) · exp(-i (E_row - E_col) dt) · exp(-γ dt)

    Args:
        decoherence_rate: γ in the formula above. Default 0.1/unit-dt
            (gives ~10% decay per unit time). Set to 0 for pure unitary
            (closed-system) evolution.
        branch_energies: optional dict[branch_label → energy E_k]. If None,
            all branches have E_k = 0 (no unitary rotation; pure decay).
            Energies are in units where ℏ=1 (i.e., dt and E_k have the
            same units).

    Backward compat: existing callers passing only `decoherence_rate` get
    the same exponential-decay behavior as the v0.7 skeleton (modulo the
    skeleton's linear-decay approximation `(1 - γ·dt)`; v3.3 uses the
    exact exponential `exp(-γ·dt)` for numerical stability).
    """

    name: str = "lindblad"
    domain: str = "quantum"
    decoherence_rate: float = 0.1
    branch_energies: Mapping[str, float] | None = field(default=None)
    strict_energy_keys: bool = False
    """V37 audit F-37-M-1: when True, raise KeyError if any branch label
    referenced by a JointBranchHypothesis is not in `branch_energies`.
    Default False preserves prior behavior (missing keys default to 0
    energy contribution — useful when only some entities have energies)."""
    decoherence_rate_matrix: Mapping[tuple[int, int], float] | None = field(default=None)
    """v3.4 S2 — per-pair γ_{kl} dephasing rate matrix.

    When None (default): uniform projection-dephasing at rate
    `decoherence_rate` for ALL off-diagonal pairs (v3.3 behavior).
    When set: each off-diagonal entry (k, l) decays at γ_{kl} =
    decoherence_rate_matrix[(min(k,l), max(k,l))] (Hermitian-symmetric:
    rate for (k,l) == rate for (l,k); only the canonical (min, max) key
    is looked up). Missing pairs default to 0 (no dephasing on that pair).

    Use this for the general L_n = diag(λ_{n,k}) jump operators case
    where γ_{kl} = ½ Σ_n |λ_{n,k} - λ_{n,l}|² varies per pair.
    See `jump_operators_to_rate_matrix` helper for computing from a
    list of diagonal jump operators."""

    def __post_init__(self) -> None:
        if self.decoherence_rate < 0:
            raise ValueError(
                f"decoherence_rate must be ≥ 0, got {self.decoherence_rate}"
            )
        if self.decoherence_rate_matrix is not None:
            # Validate: all values must be ≥ 0 (decoherence rates are positive)
            for key, gamma in self.decoherence_rate_matrix.items():
                if gamma < 0:
                    raise ValueError(
                        f"decoherence_rate_matrix[{key}] = {gamma} < 0; "
                        f"all per-pair γ_{{kl}} rates must be non-negative"
                    )
                # Canonical form: caller should pass (min, max) keys
                k, l = key
                if k > l:
                    raise ValueError(
                        f"decoherence_rate_matrix keys must be in canonical "
                        f"(min, max) order; got ({k}, {l}) where k > l. "
                        f"Hermitian symmetry: γ_{{kl}} = γ_{{lk}}; pass only "
                        f"the (min, max) form."
                    )
                # Per V38 audit F-38-M-6: diagonal entries (k, k) are not
                # off-diagonal pairs; reject as a caller bug.
                if k == l:
                    raise ValueError(
                        f"decoherence_rate_matrix keys are off-diagonal "
                        f"pairs; got diagonal ({k}, {l}). Diagonal "
                        f"probabilities are unchanged by Lindblad dephasing; "
                        f"this rate would have no effect."
                    )

    def evolve(
        self,
        rho: BeliefState | JointWaveFunction,
        dt: float,
        ctx: OperatorContext,
    ) -> BeliefState | JointWaveFunction:
        del ctx
        if dt < 0:
            raise ValueError("dt must be non-negative")
        if isinstance(rho, WaveFunction):
            # WaveFunction is single-entity, diagonal-only by construction —
            # no off-diagonals to evolve. Diagonal probabilities are owned
            # by other operators in the pipeline (Educational, Psychological,
            # Hamiltonian, etc.).
            return rho
        if isinstance(rho, JointWaveFunction):
            return self._evolve_joint(rho, dt)
        return rho

    def _evolve_joint(
        self,
        joint: JointWaveFunction,
        dt: float,
    ) -> JointWaveFunction:
        """Apply Lindblad master equation to off-diagonal coherences."""
        if not joint.off_diagonal_couplings:
            return joint
        if dt == 0:
            return joint

        # v3.4 S2: per-pair γ_kl decay if matrix provided, else uniform rate.
        rate_matrix = self.decoherence_rate_matrix
        uniform_decay = math.exp(-self.decoherence_rate * dt) if rate_matrix is None else None

        # Build energy lookup (label → E_k) or None for no-Hamiltonian path
        energies = self.branch_energies

        new_couplings = []
        for e in joint.off_diagonal_couplings:
            # row / col are INTEGER indices into joint.hypotheses tuple.
            # Energy of hypothesis k = sum over entities of E[branch_refs[entity_id]]
            # (additive Hamiltonian across entities; per-entity branch label
            # determines its energy contribution).
            if energies is not None:
                e_row = self._joint_energy(joint, e.row, energies, self.strict_energy_keys)
                e_col = self._joint_energy(joint, e.col, energies, self.strict_energy_keys)
                dE = e_row - e_col
                if dE != 0.0:
                    phase = complex(math.cos(-dE * dt), math.sin(-dE * dt))
                    rotated = e.amplitude * phase
                else:
                    rotated = e.amplitude
            else:
                rotated = e.amplitude
            # Per-pair γ_{kl} lookup (canonical (min, max) key) — v3.4 S2.
            if rate_matrix is not None:
                pair_key = (min(e.row, e.col), max(e.row, e.col))
                gamma_kl = float(rate_matrix.get(pair_key, 0.0))
                decay = math.exp(-gamma_kl * dt)
            else:
                decay = uniform_decay
            new_amp = rotated * decay
            new_couplings.append(
                OffDiagonalEntry(row=e.row, col=e.col, amplitude=new_amp)
            )

        return replace(joint, off_diagonal_couplings=tuple(new_couplings))


    @staticmethod
    def _joint_energy(
        joint: JointWaveFunction,
        hypothesis_index: int,
        energies: Mapping[str, float],
        strict: bool = False,
    ) -> float:
        """Total energy E(joint hypothesis k) = sum over entities of
        E[branch_refs[entity_id]].

        `branch_refs[entity_id]` gives the per-entity hypothesis_id (e.g., a
        branch label like "moving_left"); `energies` maps these labels to
        scalar energy values. Hamiltonian is additive across entities (no
        inter-entity coupling in this minimum-viable impl — that's v3.4 scope).

        Per V37 audit F-37-M-1:
        - default (strict=False): missing keys → 0 energy (back-compat;
          useful when only some entities have specified energies)
        - strict=True: raise KeyError on missing keys (catches typos)
        """
        hyp = joint.hypotheses[hypothesis_index]
        total = 0.0
        for _entity_id, hyp_id in hyp.branch_refs.items():
            key = str(hyp_id)
            if key in energies:
                total += float(energies[key])
            elif strict:
                raise KeyError(
                    f"branch_energies missing key {key!r} (referenced by "
                    f"hypothesis {hypothesis_index}); set strict_energy_keys"
                    f"=False to allow missing keys to default to 0."
                )
        return total

    def observe(
        self,
        rho: BeliefState | None,
        observation: Observation,
        ctx: OperatorContext,
    ) -> BeliefState:
        """Open-system measurement channel.

        For the dephasing-only case (current implementation), observation
        collapses to the measured branch with no off-diagonal mass leaking
        through. Returns a new WaveFunction at the observed position/velocity.
        """
        del rho
        vel: Velocity = (
            ctx.velocity_for_observe
            if ctx.velocity_for_observe is not None
            else (0.0, 0.0, 0.0)
        )
        return WaveFunction.from_observation(observation, velocity=vel)

    def coupling(
        self,
        rho_ab: JointBeliefState,
        type_a: str,
        type_b: str,
    ) -> float | None:
        """No inter-entity Lindblad coupling in v3.3 (Hamiltonian is additive).

        Future v3.4+ scope: support cross-entity dephasing operators
        (entanglement-decay rates that depend on entity-pair).
        """
        del rho_ab, type_a, type_b
        return None


# --------------------------------------------------------------------------
# v3.4 S2 — helper to derive per-pair γ_{kl} from a list of diagonal jump ops
# L_n = diag(λ_{n,k}). The Lindblad dissipator math gives:
#   γ_{kl} = ½ Σ_n |λ_{n,k} - λ_{n,l}|²
# which generalizes the uniform L_k = √γ|k⟩⟨k| case (γ_{kl} = γ for all k≠l)
# to arbitrary diagonal jumps. Breuer-Petruccione 2002 §3.4.5.
# --------------------------------------------------------------------------


from collections.abc import Sequence as _Sequence


def jump_operators_to_rate_matrix(
    jump_operators: _Sequence[Mapping[int, complex]],
    n_hypotheses: int,
) -> dict[tuple[int, int], float]:
    """Compute the per-pair γ_{kl} dephasing rate matrix from a list of
    diagonal jump operators L_n.

    Each `jump_operators[n]` is a dict {hypothesis_index → λ_{n,k}}
    giving the diagonal of one jump operator L_n in the hypothesis basis.

    γ_{kl} = ½ Σ_n |λ_{n,k} - λ_{n,l}|²
        (Breuer-Petruccione 2002 §3.4.5)

    For the uniform projection case L_k = √γ|k⟩⟨k| (one jump per basis
    state, λ_{n,k} = √γ·δ_{nk}), this recovers γ_{kl} = γ uniformly for
    all k≠l — matching the v3.3 default.

    Args:
        jump_operators: sequence of dicts, each giving the diagonal of
            one L_n. Missing keys default to 0.
        n_hypotheses: total number of basis states (= len(joint.hypotheses))

    Returns:
        dict {(k, l): γ_{kl}} for k < l (canonical (min, max) keys for
        Hermitian symmetry). Per V38 audit F-38-H-4: pairs with γ_{kl} = 0
        are OMITTED (LindbladOperator._evolve_joint treats missing pairs
        as 0 anyway; explicit-zero vs missing distinction was dead-coded).
    """
    # Per V38 audit F-38-M-2: guard n_hypotheses < 2 (no off-diagonal pairs
    # exist; calling with n=0 or n=1 is a caller bug — return empty silently
    # would hide it). Raise informative ValueError instead.
    if n_hypotheses < 2:
        raise ValueError(
            f"n_hypotheses must be ≥ 2 to have at least one off-diagonal "
            f"pair (k, l) with k < l; got {n_hypotheses}. "
            f"For single-state systems use the empty rate matrix {{}}."
        )
    matrix: dict[tuple[int, int], float] = {}
    for k in range(n_hypotheses):
        for l in range(k + 1, n_hypotheses):
            gamma_kl = 0.0
            for L in jump_operators:
                lambda_k = complex(L.get(k, 0.0))
                lambda_l = complex(L.get(l, 0.0))
                gamma_kl += 0.5 * abs(lambda_k - lambda_l) ** 2
            if gamma_kl > 0.0:
                matrix[(k, l)] = gamma_kl
    return matrix


__all__ = ["LindbladOperator", "jump_operators_to_rate_matrix"]
