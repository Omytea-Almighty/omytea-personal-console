"""Operator Library protocols — PLAN.md "Operator Library", WORK_PLAN_V04 §5 #7.

BeliefState / JointBeliefState are concrete bridge types from PLAN.md's hierarchy:
per-entity categorical belief is :class:`omytea.quantum.WaveFunction`; joint grids are
:class:`omytea.joint_belief.JointWaveFunction`. These are distinct from density-matrix
API payloads elsewhere — do not alias them verbally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeAlias, runtime_checkable

from omytea.joint_belief import JointWaveFunction
from omytea.models import Observation
from omytea.quantum import Velocity, WaveFunction

BeliefState: TypeAlias = WaveFunction
JointBeliefState: TypeAlias = JointWaveFunction


def _default_operator_rng() -> object:
    """Deterministic stream for stochastic resample + roughening defaults.

    v0.6 M7: each fresh :class:`OperatorContext` gets an independent
    ``default_rng(0)`` — identical starting state so replay audits match
    when the caller constructs a new context per run. Callers that need
    one RNG advanced across multiple evolves should pass ``ctx.rng``
    explicitly.
    """
    import numpy as np

    return np.random.default_rng(0)


@dataclass(frozen=True, slots=True)
class OperatorContext:
    """Per-call context for :meth:`Operator.evolve` / :meth:`Operator.observe`.

    ``roughening_sigma``: optional σ for Gaussian perturbation of each child's
    action (and matching Boltzmann weight) before stochastic resampling.
    ``None`` disables. Ignored when ``resample_scheme`` is ``\"topk\"``.
    See ``docs/research/ROUGHENING_DESIGN.md``.

    v0.6 M7 defaults: ``systematic`` resampling + σ = ``0.02`` roughening
    (locked in §4 / §4.1) and a seed-0 :class:`numpy.random.Generator`.
    Opt back into legacy behavior with ``resample_scheme="topk"`` (and
    typically ``roughening_sigma=None``).
    """

    scenario_name: str = ""
    tick: int = 0
    max_branches: int = 8
    resample_scheme: str = "systematic"
    rng: object | None = field(default_factory=_default_operator_rng)
    roughening_sigma: float | None = 0.02
    velocity_for_observe: Velocity | None = None
    # v1.4 HW.6 — action vector passed to action-conditioned operators.
    # Per Cui & Ma 2026 eq 19, the controlled-dissipative Hamiltonian
    # form ż = (J − R_ψ)∇H + G_ψ·a + ε_ψ accepts an action a_t at
    # every tick. Operators that don't consume it ignore it;
    # HamiltonianOperator with control_kind != "none" uses it.
    action: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        """v1.4 audit V14-M4 — action element-type validator.

        The `action: tuple[float, ...] | None` hint claims floats, but
        Python won't enforce element type at runtime. A caller passing
        `action=(1, 2)` (ints) or `("0.5", "0.7")` (strings) would
        only surface at `float(a[j])` deep inside the leapfrog substep
        loop. Validate at construction so the error reports the
        caller's frame, not an internal one.
        """
        if self.action is None:
            return
        if not isinstance(self.action, tuple):
            raise TypeError(
                f"OperatorContext.action must be a tuple (immutable), "
                f"got {type(self.action).__name__}. Audit V14-M4."
            )
        import numbers as _numbers
        for i, x in enumerate(self.action):
            if not isinstance(x, _numbers.Real) or isinstance(x, bool):
                raise TypeError(
                    f"OperatorContext.action[{i}] must be a real number "
                    f"(int or float), got {type(x).__name__}={x!r}. "
                    f"Audit V14-M4."
                )


@runtime_checkable
class Operator(Protocol):
    """Pluggable world dynamics on categorical belief states.

    ``evolve`` = predict forward without fresh observations (Dreamer-style prior).
    ``observe`` = incorporate a new observation (posterior / ingest).

    v0.4 ships :class:`omytea.dynamics.kinematic.KinematicOperator` only; other domains
    are roadmap per PLAN.md.
    """

    name: str
    domain: str

    def evolve(self, rho: BeliefState, dt: float, ctx: OperatorContext) -> BeliefState:
        """Forward simulate by ``dt`` seconds from current categorical belief."""
        ...

    def observe(
        self,
        rho: BeliefState | None,
        observation: Observation,
        ctx: OperatorContext,
    ) -> BeliefState:
        """Incorporate ``observation`` into belief (Bayes / ingest path).

        ``rho`` may be ``None`` when ingesting the first observation for an entity.
        """
        ...

    def coupling(
        self,
        rho_ab: JointBeliefState,
        type_a: str,
        type_b: str,
    ) -> float | None:
        """Optional joint coupling log-potential hook between domains (v0.4: unused)."""
        ...


__all__ = [
    "BeliefState",
    "JointBeliefState",
    "Operator",
    "OperatorContext",
]
