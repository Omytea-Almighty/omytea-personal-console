"""Probability-weighted belief state and branching prediction.

Historical note on naming
-------------------------

This module is named ``quantum`` for legacy reasons: an earlier draft of
Omytea used complex amplitudes and phase angles to dress probabilistic
state in quantum-mechanics grammar. That decoration was removed in the
v0.1 refactor because the phases never combined (no interference, no
unitary evolution) and were therefore engineering dead weight.

What remains is a clean, classical probabilistic data structure:

- ``StateHypothesis`` is one possible state with a non-negative
  ``weight``.
- ``WaveFunction`` is a normalized, probability-weighted mixture over
  hypotheses for a single entity. The name "WaveFunction" is preserved
  because it is pervasive in the codebase and in collaborator-facing
  docs, but inside this module it is just a normalized mixture.
- ``BranchingPredictor`` evolves a mixture forward in time by
  enumerating dynamics options and weighting their offspring branches
  by ``prior * exp(-action / temperature)``.

A genuine open-system / Lindblad-style dynamics (density operators,
unitary part + dissipative part) is documented as a v1.0+ research
direction in ``docs/future_directions/lindblad_dynamics.md`` and is
explicitly *not* implemented here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from omytea.models import Observation, Position, RectRegion

Velocity = tuple[float, float, float]


def clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, value))


def move_position(position: Position, velocity: Velocity, seconds: float) -> Position:
    return Position(
        x=position.x + velocity[0] * seconds,
        y=position.y + velocity[1] * seconds,
        z=(position.z or 0.0) + velocity[2] * seconds if position.z is not None else None,
        space=position.space,
    )


@dataclass(frozen=True, slots=True)
class StateHypothesis:
    """One probability-weighted possible state for an entity.

    ``weight`` is a non-negative real. After the parent ``WaveFunction``
    is normalized, ``weight`` equals the hypothesis's probability mass,
    and ``probability`` returns it directly.
    """

    object_id: str
    label: str
    stream_id: str
    timestamp: datetime
    position: Position
    velocity: Velocity = (0.0, 0.0, 0.0)
    weight: float = 1.0
    action: float = 0.0
    branch_label: str = "observed"
    hypothesis_id: str = field(default_factory=lambda: str(uuid4()))
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def probability(self) -> float:
        return max(0.0, self.weight)

    def with_weight(self, weight: float) -> "StateHypothesis":
        return StateHypothesis(
            object_id=self.object_id,
            label=self.label,
            stream_id=self.stream_id,
            timestamp=self.timestamp,
            position=self.position,
            velocity=self.velocity,
            weight=max(0.0, weight),
            action=self.action,
            branch_label=self.branch_label,
            hypothesis_id=self.hypothesis_id,
            attributes=self.attributes,
        )


@dataclass(frozen=True, slots=True)
class WaveFunction:
    """Probability-weighted belief state for one entity.

    "WaveFunction" is preserved as the user-facing name because the
    project's docs and dashboard use it. Mechanically this is a
    normalized mixture: ``sum(probability) == 1`` after ``normalized()``.
    There is no phase, no interference, no unitary evolution.

    v0.5 Wave 5c — Pearl-rung-2 schema extension: ``action_arm`` is the
    intervention label this belief was computed *under* (e.g. ``"do(T=A)"``
    vs ``"do(T=B)"``). When ``None`` (default, backward-compat), the wave
    is associational — predicted from history without an explicit
    intervention. When set by ``CausalOperator``, the wave's content is
    interventional and **must not** be averaged with associational waves
    of the same entity without preserving this distinction (per Pearl's
    rung-1 vs rung-2 contract).
    """

    object_id: str
    label: str
    stream_id: str
    timestamp: datetime
    hypotheses: tuple[StateHypothesis, ...]
    action_arm: str | None = None
    """v0.5 Wave 5c: intervention label, or ``None`` for associational
    waves. See ``docs/research/CAUSAL_INFERENCE_NOTES.md`` §H. Defaulted
    so v0.4 callers don't need updates."""

    @classmethod
    def from_observation(cls, observation: Observation, velocity: Velocity = (0.0, 0.0, 0.0)) -> "WaveFunction":
        confidence = clamp_probability(observation.confidence)
        observed = StateHypothesis(
            object_id=observation.object_id,
            label=observation.label,
            stream_id=observation.stream_id,
            timestamp=observation.timestamp,
            position=observation.position,
            velocity=velocity,
            weight=confidence,
            branch_label="measured",
            attributes=observation.attributes,
        )

        hypotheses = [observed]
        residual = max(0.0, 1.0 - confidence)
        if residual > 0:
            uncertainty = float(observation.attributes.get("position_uncertainty", 16.0))
            side_probability = residual / 2.0
            for label, dx in (
                ("uncertainty-left", -uncertainty),
                ("uncertainty-right", uncertainty),
            ):
                hypotheses.append(
                    StateHypothesis(
                        object_id=observation.object_id,
                        label=observation.label,
                        stream_id=observation.stream_id,
                        timestamp=observation.timestamp,
                        position=Position(
                            x=observation.position.x + dx,
                            y=observation.position.y,
                            z=observation.position.z,
                            space=observation.position.space,
                        ),
                        velocity=velocity,
                        weight=side_probability,
                        action=0.25,
                        branch_label=label,
                        attributes={**observation.attributes, "latent": True},
                    )
                )

        return cls(
            object_id=observation.object_id,
            label=observation.label,
            stream_id=observation.stream_id,
            timestamp=observation.timestamp,
            hypotheses=tuple(hypotheses),
        ).normalized()

    @property
    def probability_mass(self) -> float:
        return sum(hypothesis.probability for hypothesis in self.hypotheses)

    def normalized(self) -> "WaveFunction":
        if not self.hypotheses:
            return self

        mass = self.probability_mass
        if mass <= 0:
            uniform = 1.0 / len(self.hypotheses)
            normalized = tuple(hypothesis.with_weight(uniform) for hypothesis in self.hypotheses)
        else:
            scale = 1.0 / mass
            normalized = tuple(hypothesis.with_weight(hypothesis.probability * scale) for hypothesis in self.hypotheses)

        return WaveFunction(
            object_id=self.object_id,
            label=self.label,
            stream_id=self.stream_id,
            timestamp=self.timestamp,
            hypotheses=normalized,
            action_arm=self.action_arm,
        )

    def prune(self, max_hypotheses: int) -> "WaveFunction":
        if max_hypotheses <= 0:
            raise ValueError("max_hypotheses must be positive")
        kept = tuple(sorted(self.hypotheses, key=lambda item: item.probability, reverse=True)[:max_hypotheses])
        return WaveFunction(
            object_id=self.object_id,
            label=self.label,
            stream_id=self.stream_id,
            timestamp=self.timestamp,
            hypotheses=kept,
            action_arm=self.action_arm,
        ).normalized()

    @property
    def ess(self) -> float:
        """v0.5 M1: effective sample size = ``1 / Σ w_i²``.

        Standard SMC degeneracy diagnostic (Liu & Chen 1998). Equals
        ``len(hypotheses)`` when weights are uniform; equals 1 when one
        weight dominates. Rule of thumb: trigger resampling when
        ``ess / len(hypotheses) < 0.5``.

        Reference: ``docs/research/SMC_PARTICLE_FILTERS_NOTES.md``.

        Raises:
            ValueError: if no hypotheses.
        """
        if not self.hypotheses:
            raise ValueError("ess undefined for an empty WaveFunction")
        return float(1.0 / sum(h.probability * h.probability for h in self.hypotheses))

    def resample(
        self,
        max_hypotheses: int,
        scheme: str = "topk",
        rng: object | None = None,
    ) -> "WaveFunction":
        """v0.5 M1: opt-in stochastic resampling alternatives to ``prune``.

        Default ``scheme="topk"`` is identical to ``prune(max_hypotheses)``.
        :class:`BranchingPredictor.evolve` defaults to ``"systematic"`` +
        roughening (v0.6 M7); this method's default stays ``topk`` for
        direct ``WaveFunction.resample`` call sites.

        Stochastic schemes (``"systematic"``, ``"stratified"``,
        ``"residual"``, ``"multinomial"``) sample ``max_hypotheses``
        indices according to the per-hypothesis probabilities, then
        rebuild the wave with each surviving hypothesis carrying weight
        ``1/M`` (uniformly), preserving total probability mass exactly.
        This is the correct SMC restart: post-resample particles are
        identically weighted by construction.

        Args:
            max_hypotheses: number of hypotheses to keep after resample.
            scheme: ``"topk"`` (default, deterministic), ``"systematic"``
                (recommended SMC default per Chopin & Papaspiliopoulos
                2020), ``"stratified"``, ``"residual"``, or
                ``"multinomial"``.
            rng: ``numpy.random.Generator``. Required for stochastic
                schemes; ignored for ``"topk"``. Pass
                ``np.random.default_rng(seed)`` for reproducibility.

        Raises:
            ValueError: if ``max_hypotheses <= 0``, no hypotheses, or
                an unknown scheme. Stochastic schemes additionally raise
                if ``rng`` is None.
        """
        if max_hypotheses <= 0:
            raise ValueError("max_hypotheses must be positive")
        if not self.hypotheses:
            raise ValueError("cannot resample an empty WaveFunction")
        if scheme == "topk":
            return self.prune(max_hypotheses)

        # Stochastic schemes: import lazily so the topk path stays
        # numpy-free and the core wavefunction module retains its
        # current import surface.
        import numpy as np

        if rng is None:
            raise ValueError(
                f"resample(scheme={scheme!r}) requires an np.random.Generator; "
                "pass np.random.default_rng(seed) for reproducibility"
            )
        from omytea.sampling import (
            multinomial_resample,
            residual_resample,
            stratified_resample,
            systematic_resample,
        )
        schemes = {
            "systematic": systematic_resample,
            "stratified": stratified_resample,
            "residual": residual_resample,
            "multinomial": multinomial_resample,
        }
        if scheme not in schemes:
            raise ValueError(
                f"unknown resampling scheme {scheme!r}; choose from "
                f"{['topk', *sorted(schemes)]}"
            )
        # Normalize first; resampling only operates on normalized weights.
        wave = self.normalized()
        weights = np.asarray([h.probability for h in wave.hypotheses], dtype=np.float64)
        indices = schemes[scheme](weights, M=max_hypotheses, rng=rng)
        # Rebuild with uniform weights: this is the canonical SMC
        # post-resample state (every surviving particle weight = 1/M).
        uniform_weight = 1.0 / max_hypotheses
        kept = tuple(wave.hypotheses[i].with_weight(uniform_weight) for i in indices)
        return WaveFunction(
            object_id=self.object_id,
            label=self.label,
            stream_id=self.stream_id,
            timestamp=self.timestamp,
            hypotheses=kept,
            action_arm=self.action_arm,
        )

    def most_likely(self) -> StateHypothesis | None:
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda item: item.probability)

    def probability_in(self, region: RectRegion) -> float:
        return sum(hypothesis.probability for hypothesis in self.hypotheses if region.contains(hypothesis.position))

    def expectation_position(self) -> Position | None:
        if not self.hypotheses:
            return None
        mass = self.probability_mass
        if mass <= 0:
            return None

        space = self.hypotheses[0].position.space
        if any(hypothesis.position.space != space for hypothesis in self.hypotheses):
            raise ValueError("cannot compute expectation across mixed coordinate spaces")

        x = sum(hypothesis.position.x * hypothesis.probability for hypothesis in self.hypotheses) / mass
        y = sum(hypothesis.position.y * hypothesis.probability for hypothesis in self.hypotheses) / mass
        z_values = [hypothesis.position.z for hypothesis in self.hypotheses]
        z = None
        if any(value is not None for value in z_values):
            z = sum((hypothesis.position.z or 0.0) * hypothesis.probability for hypothesis in self.hypotheses) / mass
        return Position(x=x, y=y, z=z, space=space)

    def collapse_to_region(self, region: RectRegion) -> "WaveFunction":
        kept = tuple(hypothesis for hypothesis in self.hypotheses if region.contains(hypothesis.position))
        return WaveFunction(
            object_id=self.object_id,
            label=self.label,
            stream_id=self.stream_id,
            timestamp=self.timestamp,
            hypotheses=kept,
            action_arm=self.action_arm,
        ).normalized()


@dataclass(frozen=True, slots=True)
class DynamicsOption:
    """One possible local evolution rule for a branch.

    ``action_bias`` adds a constant to the action functional, biasing
    branches toward or away from this option independent of state.
    """

    name: str
    prior: float
    velocity_scale: float
    action_bias: float
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActionContribution:
    """One term contributing to the generalized action."""

    domain: str
    name: str
    value: float
    weight: float = 1.0

    @property
    def weighted_value(self) -> float:
        return self.value * self.weight


@dataclass(frozen=True, slots=True)
class DomainActionTerm:
    """Action term sourced from hypothesis or branch attributes."""

    domain: str
    name: str
    weight: float = 1.0
    source_attribute: str | None = None
    option_attribute: str | None = None
    constant: float = 0.0

    def evaluate(self, source: StateHypothesis, option: DynamicsOption, horizon_seconds: float) -> ActionContribution:
        del horizon_seconds
        value = self.constant
        if self.source_attribute:
            value += numeric_attribute(source.attributes, self.source_attribute)
        if self.option_attribute:
            value += numeric_attribute(option.attributes, self.option_attribute)
        return ActionContribution(domain=self.domain, name=self.name, value=value, weight=self.weight)


@dataclass(frozen=True, slots=True)
class ActionFunctional:
    """Scores a possible path with physics and optional domain terms."""

    motion_weight: float = 0.01
    acceleration_weight: float = 0.2
    temperature: float = 1.0
    domain_terms: tuple[DomainActionTerm, ...] = ()

    def evaluate(self, source: StateHypothesis, option: DynamicsOption, horizon_seconds: float) -> float:
        return sum(contribution.weighted_value for contribution in self.explain(source, option, horizon_seconds))

    def explain(
        self,
        source: StateHypothesis,
        option: DynamicsOption,
        horizon_seconds: float,
    ) -> tuple[ActionContribution, ...]:
        old_speed = math.sqrt(source.velocity[0] ** 2 + source.velocity[1] ** 2 + source.velocity[2] ** 2)
        new_velocity = scale_velocity(source.velocity, option.velocity_scale)
        new_speed = math.sqrt(new_velocity[0] ** 2 + new_velocity[1] ** 2 + new_velocity[2] ** 2)
        acceleration = abs(new_speed - old_speed) / max(horizon_seconds, 1e-9)
        path_length = new_speed * horizon_seconds
        contributions = [
            ActionContribution(domain="prior", name="branch_bias", value=option.action_bias),
            ActionContribution(domain="physics", name="path_length", value=path_length, weight=self.motion_weight),
            ActionContribution(
                domain="physics",
                name="acceleration_change",
                value=acceleration,
                weight=self.acceleration_weight,
            ),
        ]
        contributions.extend(term.evaluate(source, option, horizon_seconds) for term in self.domain_terms)
        return tuple(contributions)

    def likelihood(self, action: float) -> float:
        return math.exp(-action / max(self.temperature, 1e-9))


class BranchingPredictor:
    """Evolves a wave function into probability-weighted future branches.

    Each parent hypothesis spawns one child per ``DynamicsOption``. Child
    weight is ``parent.probability * option.prior * likelihood(action)``,
    where ``likelihood = exp(-action / T)``. The result is renormalized
    and pruned to ``max_branches``.
    """

    def __init__(
        self,
        options: tuple[DynamicsOption, ...] | None = None,
        action_functional: ActionFunctional | None = None,
    ) -> None:
        self.options = options or (
            DynamicsOption(name="continue", prior=0.50, velocity_scale=1.0, action_bias=0.10),
            DynamicsOption(name="slow", prior=0.25, velocity_scale=0.35, action_bias=0.22),
            DynamicsOption(name="pause", prior=0.18, velocity_scale=0.0, action_bias=0.35),
            DynamicsOption(name="accelerate", prior=0.07, velocity_scale=1.35, action_bias=0.55),
        )
        self.action_functional = action_functional or ActionFunctional()

    def evolve(
        self,
        wave: WaveFunction,
        horizon_seconds: float,
        max_branches: int = 8,
        resample_scheme: str = "systematic",
        rng: object | None = None,
        roughening_sigma: float | None = 0.02,
    ) -> WaveFunction:
        """Evolve a wave function forward by ``horizon_seconds``.

        Each parent hypothesis spawns one child per ``DynamicsOption``;
        children are reweighted, normalized, and then **reduced back to
        ``max_branches``** via ``resample_scheme``.

        Args:
            wave: input belief.
            horizon_seconds: prediction horizon (≥ 0).
            max_branches: cap on output hypothesis count.
            resample_scheme: ``"systematic"`` (v0.6 M7 default) or another
                stochastic scheme (``"stratified"``, ``"residual"``,
                ``"multinomial"``), or ``"topk"`` for legacy deterministic
                pruning. See ``docs/research/SMC_PARTICLE_FILTERS_NOTES.md``.
            rng: ``np.random.Generator``. Required for non-topk schemes
                unless omitted, in which case ``default_rng(0)`` is used
                (deterministic product default). Ignored for ``"topk"``.
            roughening_sigma: optional σ for process noise on each child's
                ``action`` (and matching weight update) before resampling.
                Only applied when ``resample_scheme != "topk"`` and σ > 0.
                Default ``0.02`` matches ``docs/research/ROUGHENING_DESIGN.md``
                §4. Set to ``None`` to disable.
        """
        if horizon_seconds < 0:
            raise ValueError("horizon_seconds must be non-negative")

        if resample_scheme != "topk" and rng is None:
            import numpy as np

            rng = np.random.default_rng(0)

        source_wave = wave.normalized()
        predicted_at = wave.timestamp + timedelta(seconds=horizon_seconds)
        branches: list[StateHypothesis] = []

        for source in source_wave.hypotheses:
            for option in self.options:
                velocity = scale_velocity(source.velocity, option.velocity_scale)
                action_contributions = self.action_functional.explain(source, option, horizon_seconds)
                action = sum(contribution.weighted_value for contribution in action_contributions)
                weight = max(0.0, source.probability * option.prior * self.action_functional.likelihood(action))
                # v0.5 Wave 2: propagate lineage_root_id through generations
                # so OperatorHealth.lineage_diversity tracks seed-ancestor
                # collapse, not just immediate-parent collapse. Inherit
                # parent's root if set, else parent's hypothesis_id (parent
                # was itself a seed). See _lineage_key in pipeline.py.
                lineage_root = source.attributes.get("lineage_root_id", source.hypothesis_id)
                branches.append(
                    StateHypothesis(
                        object_id=source.object_id,
                        label=source.label,
                        stream_id=source.stream_id,
                        timestamp=predicted_at,
                        position=move_position(source.position, velocity, horizon_seconds),
                        velocity=velocity,
                        weight=weight,
                        action=action,
                        branch_label=option.name,
                        attributes={
                            **source.attributes,
                            **option.attributes,
                            "parent_hypothesis_id": source.hypothesis_id,
                            "lineage_root_id": lineage_root,
                            "horizon_seconds": horizon_seconds,
                            "action_contributions": tuple(
                                {
                                    "domain": contribution.domain,
                                    "name": contribution.name,
                                    "value": contribution.value,
                                    "weight": contribution.weight,
                                    "weighted_value": contribution.weighted_value,
                                }
                                for contribution in action_contributions
                            ),
                        },
                    )
                )

        if resample_scheme != "topk" and roughening_sigma is not None:
            sigma = float(roughening_sigma)
            if sigma < 0:
                raise ValueError(f"roughening_sigma must be >= 0; got {sigma}")
            if sigma > 0:
                if rng is None:
                    raise ValueError(
                        "roughening_sigma > 0 requires rng (use np.random.default_rng(seed))"
                    )
                import numpy as np

                if not isinstance(rng, np.random.Generator):
                    raise ValueError(
                        "roughening requires rng to be an np.random.Generator "
                        "(same as stochastic resample schemes)"
                    )
                epsilons = rng.standard_normal(len(branches)) * sigma
                temp = max(self.action_functional.temperature, 1e-9)
                perturbed: list[StateHypothesis] = []
                for i, h in enumerate(branches):
                    eps = float(epsilons[i])
                    new_w = max(0.0, h.weight * math.exp(-eps / temp))
                    perturbed.append(
                        replace(
                            h,
                            action=h.action + eps,
                            weight=new_w,
                        )
                    )
                branches = perturbed

        evolved = WaveFunction(
            object_id=wave.object_id,
            label=wave.label,
            stream_id=wave.stream_id,
            timestamp=predicted_at,
            hypotheses=tuple(branches),
        ).normalized()
        return evolved.resample(max_branches, scheme=resample_scheme, rng=rng)


def scale_velocity(velocity: Velocity, scale: float) -> Velocity:
    return (velocity[0] * scale, velocity[1] * scale, velocity[2] * scale)


def numeric_attribute(attributes: dict[str, Any], key: str) -> float:
    value = attributes.get(key, 0.0)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
