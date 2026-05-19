"""Joint belief state for v0.4 multi-entity correlated futures.

Per ``PLAN.md`` "State Representation Hierarchy" and ``WORK_PLAN_V04.md`` §3.1:

- ``JointBranchHypothesis`` is one cell in the joint hypothesis grid: a mapping
  from entity_id → its hypothesis_id (referencing the per-entity
  ``WaveFunction``) plus a scalar weight.
- ``JointWaveFunction`` stores joint mass in the branch tensor-product basis:
  diagonal entries are classical branch weights; optional v0.5+
  ``off_diagonal_couplings`` hold explicit Hermitian off-diagonal ρ entries
  (correlated futures / coherence between branches). Default empty couplings
  preserve v0.4 classical-correlation-only behavior.
- ``JointCoupling`` is a real-valued log-potential; ``DistanceCoupling`` is the
  v0.4 ship default (single global κ, hand-coded per scenario, pairwise on
  predicted positions). Other coupling types and per-type-pair κ are explicitly
  out of scope for v0.4 — see ``WORK_PLAN_V04.md`` §3.2.

Pruning order is locked in M1 (``WORK_PLAN_V04.md`` §3.1): when joint
enumeration would exceed ``max_joint_branches``, prune in **ascending weight**
order; ties break **lexicographically** by the tuple of branch ids in
``entity_ids`` order. Determinism is required — no reliance on dict insertion
order or float-equality ambiguity.

Architecture inspired in part by MiroFish's ontology-pattern (AGPL-3.0;
``docs/research/MIROFISH_NOTES.md``); no code copied. The Operator Library
framing in ``PLAN.md`` makes this module a strict v0.4 deliverable: the
operator-protocol surface itself lands at v0.4 M5 (acceptance criterion 7).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from typing import Mapping, Optional, Protocol, Sequence, runtime_checkable

from omytea.density import DensityMatrix
from omytea.quantum import StateHypothesis, WaveFunction


def _complex_close(a: complex, b: complex, *, tol: float = 1e-12) -> bool:
    return abs(a.real - b.real) <= tol and abs(a.imag - b.imag) <= tol


# ---------------------------------------------------------------------------
# Joint hypothesis cell
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class JointBranchHypothesis:
    """One cell in the joint hypothesis grid.

    ``branch_refs`` maps each ``entity_id`` to its ``hypothesis_id`` (a reference
    into that entity's marginal :class:`omytea.quantum.WaveFunction`). ``weight``
    is non-negative; after the parent ``JointWaveFunction`` is normalized,
    ``weight`` equals the joint probability of that branch combination.
    """

    branch_refs: Mapping[str, str]  # entity_id → hypothesis_id
    weight: float

    @property
    def probability(self) -> float:
        return max(0.0, self.weight)

    def with_weight(self, weight: float) -> "JointBranchHypothesis":
        return JointBranchHypothesis(
            branch_refs=self.branch_refs,
            weight=max(0.0, weight),
        )

    def __post_init__(self) -> None:
        # Frozen dataclass: assign through object.__setattr__ since branch_refs
        # may have been passed as a non-Mapping; coerce to dict for stable
        # ordering and hashable keys.
        if not isinstance(self.branch_refs, dict):
            object.__setattr__(self, "branch_refs", dict(self.branch_refs))


# ---------------------------------------------------------------------------
# Coupling protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class JointCoupling(Protocol):
    """Real-valued log-potential between marginal branches in a joint.

    ``joint_weight ∝ product_of_marginal_probs × exp(log_potential)``.

    Implementations should be deterministic and total: given the same
    ``branch_refs`` + ``marginals``, return the same number; never raise.
    """

    def log_potential(
        self,
        branch_refs: Mapping[str, str],
        marginals: Mapping[str, WaveFunction],
    ) -> float: ...


@dataclass(frozen=True, slots=True)
class DistanceCoupling:
    """v0.4 default coupling: pairwise squared-distance log-potential.

    ``log_potential = −κ · Σ_{i<j} ‖x_i − x_j‖₂²`` over all entity pairs in the
    joint. Positions are read from the selected branch's :class:`StateHypothesis`
    in each entity's marginal.

    - ``κ > 0`` encourages proximity (negative log-potential pulled smaller for
      faraway pairs, joint weight reduced when entities far apart).
    - ``κ < 0`` encourages avoidance.
    - ``κ = 0`` is the **marginal-recovery sanity invariant** of
      ``WORK_PLAN_V04.md`` §5 criterion 2: the joint must reduce exactly to the
      product of marginals within ε.

    Per ``WORK_PLAN_V04.md`` §3.2, v0.4 ships exactly **one** coupling type
    (``DistanceCoupling``) and a single global ``kappa`` value. Per-type-pair
    κ, learned κ, and synchronized-discrete coupling are explicitly out of
    scope for v0.4 and tracked as v0.5+ items.
    """

    kappa: float

    def log_potential(
        self,
        branch_refs: Mapping[str, str],
        marginals: Mapping[str, WaveFunction],
    ) -> float:
        if self.kappa == 0.0:
            return 0.0
        positions = []
        for entity_id, hypothesis_id in branch_refs.items():
            wave = marginals.get(entity_id)
            if wave is None:
                # Missing marginal — caller should fail fast upstream.
                # Returning 0 keeps coupling=0 invariant from leaking on
                # incomplete inputs; the caller validates earlier.
                return 0.0
            hyp = next(
                (h for h in wave.hypotheses if h.hypothesis_id == hypothesis_id),
                None,
            )
            if hyp is None:
                return 0.0
            positions.append(hyp.position)
        if len(positions) < 2:
            return 0.0
        total = 0.0
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                a, b = positions[i], positions[j]
                dx = a.x - b.x
                dy = a.y - b.y
                dz = (a.z or 0.0) - (b.z or 0.0)
                total += dx * dx + dy * dy + dz * dz
        return -self.kappa * total


@dataclass(frozen=True, slots=True)
class RelationCoupling:
    """Skeleton relation-based log-potential (v0.5 Wave 5d).

    Stand-in until a typed :class:`~omytea.dynamics.social.Network` backs
    edge lookup. Emits ``strength`` whenever at least two entities appear
    in ``branch_refs`` (edge presence is not yet modeled).
    """

    relation_type: str
    strength: float = 1.0

    def log_potential(
        self,
        branch_refs: Mapping[str, str],
        _marginals: Mapping[str, WaveFunction],
    ) -> float:
        if len(branch_refs) < 2:
            return 0.0
        return float(self.strength)


@dataclass(frozen=True, slots=True)
class TypedJointCoupling:
    """Route entity pairs to per-(type_a, type_b) :class:`JointCoupling` instances.

    Lookup is symmetric: ``(t_a, t_b)`` matches ``(t_b, t_a)``. Missing
    type-pair entries contribute 0 (same as :class:`DistanceCoupling`
    with ``kappa=0`` for that pair).
    """

    couplings_by_pair: Mapping[tuple[str, str], JointCoupling]
    entity_types: Mapping[str, str]

    def _lookup(self, type_a: str, type_b: str) -> JointCoupling | None:
        if (type_a, type_b) in self.couplings_by_pair:
            return self.couplings_by_pair[(type_a, type_b)]
        if (type_b, type_a) in self.couplings_by_pair:
            return self.couplings_by_pair[(type_b, type_a)]
        return None

    def log_potential(
        self,
        branch_refs: Mapping[str, str],
        marginals: Mapping[str, WaveFunction],
    ) -> float:
        total = 0.0
        ids = list(branch_refs.keys())
        for i, id_a in enumerate(ids):
            for id_b in ids[i + 1 :]:
                type_a = self.entity_types.get(id_a, "unknown")
                type_b = self.entity_types.get(id_b, "unknown")
                coupling = self._lookup(type_a, type_b)
                if coupling is None:
                    continue
                sub_refs = {id_a: branch_refs[id_a], id_b: branch_refs[id_b]}
                wa = marginals.get(id_a)
                wb = marginals.get(id_b)
                if wa is None or wb is None:
                    continue
                sub_marginals = {id_a: wa, id_b: wb}
                total += coupling.log_potential(sub_refs, sub_marginals)
        return total


# ---------------------------------------------------------------------------
# Off-diagonal joint ρ (v0.5+) — sparse Hermitian pairs in branch basis
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OffDiagonalEntry:
    """One off-diagonal element ρ_{row,col} (row ≠ col) in the branch basis.

    Hermitian storage is **explicit**: both ``(row, col, a)`` and
    ``(col, row, conj(a))`` must appear in
    :attr:`JointWaveFunction.off_diagonal_couplings`.
    """

    row: int
    col: int
    amplitude: complex


# ---------------------------------------------------------------------------
# Density matrix view (sparse-diagonal, v0.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class JointDiagonalRho:
    """Sparse diagonal of joint ρ in the branch tensor-product basis (v0.4).

    Not the full ``N×N`` complex density matrix — see
    :class:`omytea.density.DensityMatrix` for the quantum-engine representation.

    v0.4 invariant: only diagonal entries (classical correlation). True
    entanglement (off-diagonals) is v0.5+.
    """

    basis_labels: tuple[str, ...]  # one label per basis vector, "entity_id::hypothesis_id"
    diagonal: tuple[float, ...]  # populated; off-diag implicitly zero in v0.4

    @property
    def dim(self) -> int:
        return len(self.basis_labels)

    def trace(self) -> float:
        return float(sum(self.diagonal))

    def is_hermitian(self, atol: float = 1e-9) -> bool:
        del atol
        return True

    def is_positive_semidefinite(self, atol: float = 1e-9) -> bool:
        return all(d >= -atol for d in self.diagonal)

    def as_full_matrix(self) -> list[list[float]]:
        """Full real diagonal matrix (zeros off-diagonal)."""
        n = self.dim
        m = [[0.0] * n for _ in range(n)]
        for i, d in enumerate(self.diagonal):
            m[i][i] = float(d)
        return m


# ---------------------------------------------------------------------------
# JointWaveFunction
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class JointWaveFunction:
    """Joint ``ρ_{AB}`` in the branch tensor-product basis (sparse storage).

    ``entity_ids`` is the ordered tuple of entity ids participating in the
    joint. Order matters because the lex tie-break in :meth:`pruned` reads
    branch ids in that order, and because :meth:`basis_labels` follows it.

    ``hypotheses`` lists populated joint cells; each cell's weight is the
    **diagonal** ρ_{ii} in that basis. Optional
    :attr:`off_diagonal_couplings` hold explicit Hermitian off-diagonal
    pairs (v0.5+); default empty preserves v0.4 classical-correlation-only
    behavior.

    After :meth:`normalized`, ``sum(weight) == 1`` (within float tolerance).
    """

    entity_ids: tuple[str, ...]
    hypotheses: tuple[JointBranchHypothesis, ...]
    off_diagonal_couplings: tuple[OffDiagonalEntry, ...] = ()

    def __post_init__(self) -> None:
        n = len(self.hypotheses)
        if self.off_diagonal_couplings and n == 0:
            raise ValueError("off_diagonal_couplings require non-empty hypotheses")
        by_pos: dict[tuple[int, int], complex] = {}
        for e in self.off_diagonal_couplings:
            if e.row == e.col:
                raise ValueError(
                    f"off-diagonal entry must have row != col; got ({e.row}, {e.col})"
                )
            if not (0 <= e.row < n and 0 <= e.col < n):
                raise ValueError(
                    f"off-diagonal indices out of range for n={n}: ({e.row}, {e.col})"
                )
            key = (e.row, e.col)
            if key in by_pos and not _complex_close(by_pos[key], e.amplitude):
                raise ValueError(f"conflicting amplitudes for position {key}")
            by_pos[key] = e.amplitude
        for (r, c), a in by_pos.items():
            partner = by_pos.get((c, r))
            if partner is None:
                raise ValueError(
                    f"missing Hermitian partner for off-diagonal ({r}, {c}); "
                    f"expected ({c}, {r}, conj({a}))"
                )
            if not _complex_close(partner, a.conjugate()):
                raise ValueError(
                    f"Hermitian mismatch: ρ[{r},{c}]={a!r} but ρ[{c},{r}]={partner!r} "
                    f"(expected {a.conjugate()!r})"
                )

    # ----- constructors ---------------------------------------------------

    @classmethod
    def from_marginals(
        cls,
        marginals: Mapping[str, WaveFunction],
        coupling: Optional[JointCoupling] = None,
        max_joint_branches: int = 64,
        entity_id_order: Optional[Sequence[str]] = None,
        use_tensor_network: Optional[bool] = None,
    ) -> "JointWaveFunction":
        """Build a joint from per-entity marginals plus an optional coupling.

        With ``coupling=None`` (or with a coupling whose ``log_potential`` is
        identically zero, e.g. ``DistanceCoupling(kappa=0.0)``), the joint
        reduces exactly to the product of marginals. This is the marginal-
        recovery invariant from ``WORK_PLAN_V04.md`` §5 criterion 2.

        **v3.5 S2 — tensor-network high-N path (Strategy B default)**:
        When the entity count is high (``N >= 4``) or the implied state
        space is large (default threshold: ``Π_k d_k > 256`` cells), this
        method **auto-routes** through
        ``omytea.wm_db.tensor_network.joint_from_marginals_via_tensor_network``
        — heap-based lazy top-K instead of d^N enumeration — **even when
        ``coupling`` is non-None**. Strategy B keeps this default so
        high-N + coupling callers get a bounded-cost path without silent
        falling back to exponential memory.

        **Semantics / breaking note (must read before upgrading)**:
        For ``coupling is not None``, the heap path can be **only
        approximately exact** for strong potentials (see
        ``joint_from_marginals_via_tensor_network`` docstring: successor
        generation may miss cells where ``log_potential`` dominates marginal
        mass). The helper sets ``HighNJointResult.top_k_exact=False`` whenever
        ``coupling`` is provided. For **bit-identical** agreement with the
        legacy softmax + prune path (full d^N, same tie-break as
        ``WORK_PLAN_V04`` §3.1), pass ``use_tensor_network=False`` — that is
        the supported escape hatch for audits and golden tests.

        ``use_tensor_network`` override:
          - ``True``: force the TN heap path (any N).
          - ``False``: force the legacy d^N enumeration path (exact w.r.t.
            the legacy implementation; use for strong coupling or golden
            comparisons).
          - ``None`` (default): auto-detect via ``N >= 4`` or ``Π_k d_k > 256``.

        The TN heap path is **exact** for product state (``coupling=None``)
        when ``top_k`` equals the full grid size. When the TN path is used,
        the returned ``JointWaveFunction`` has at most ``max_joint_branches``
        hypotheses (``top_k=max_joint_branches`` on the helper).

        Args:
            marginals: mapping ``entity_id`` → :class:`WaveFunction`.
            coupling: optional :class:`JointCoupling`.
            max_joint_branches: hard cap on the number of joint cells.
                For the legacy enumeration path: cells are sorted +
                pruned to this count. For the TN path: heap top-K stops
                at this count.
            entity_id_order: optional explicit ordering for ``entity_ids``.
            use_tensor_network: see class docstring; ``None`` auto-detects
                (Strategy B: may still route through TN when ``coupling`` is
                set — use ``False`` for legacy exact path).

        Raises:
            ValueError: empty marginals or non-positive max_joint_branches.
        """
        if not marginals:
            raise ValueError("marginals must contain at least one entity")
        if max_joint_branches <= 0:
            raise ValueError("max_joint_branches must be positive")

        # v3.5 S2 Strategy B: auto-detect TN path for N >= 4 or Π_k d_k > 256.
        # Applies even when coupling is set (bounded cost). For exact legacy
        # softmax+prune behavior (strong coupling / goldens), pass
        # use_tensor_network=False.
        if use_tensor_network is None:
            state_space_size = 1
            for eid in marginals:
                state_space_size *= len(marginals[eid].hypotheses)
                if state_space_size > 256:
                    break  # short-circuit; no need to keep multiplying
            use_tn = len(marginals) >= 4 or state_space_size > 256
        else:
            use_tn = bool(use_tensor_network)
        if use_tn:
            # Lazy import to avoid quimb dep cost for low-N callers.
            from omytea.wm_db.tensor_network import (
                joint_from_marginals_via_tensor_network,
            )
            tn_result = joint_from_marginals_via_tensor_network(
                marginals=marginals,
                top_k=max_joint_branches,
                entity_id_order=entity_id_order,
                # MPS χ verification only when no coupling (the helper
                # auto-skips when coupling is provided, but for the
                # product-state path we explicitly disable to avoid
                # quimb import cost in the joint-construction hot path).
                verify_mps_chi=False,
                coupling=coupling,
            )
            return tn_result.joint.normalized()

        if entity_id_order is None:
            entity_ids = tuple(marginals.keys())
        else:
            entity_ids = tuple(entity_id_order)
            missing = set(entity_ids) - set(marginals.keys())
            if missing:
                raise ValueError(
                    f"entity_id_order references entities not in marginals: {sorted(missing)}"
                )

        hyp_lists = [tuple(marginals[eid].hypotheses) for eid in entity_ids]
        if any(len(hl) == 0 for hl in hyp_lists):
            # An entity with no hypotheses produces an empty product. Return
            # an empty joint rather than blowing up, so downstream code can
            # fail fast on its own terms.
            return cls(entity_ids=entity_ids, hypotheses=(), off_diagonal_couplings=())

        # Build per-cell log-weights first, then logsumexp-normalize for
        # numerical stability under extreme coupling parameters. Without
        # this, large positive log-potentials produce exp(...) = +inf and
        # the subsequent normalization either yields NaN or collapses to a
        # degenerate uniform mass-zero fallback. Tested by
        # ``tests/test_joint_belief.py::test_extreme_*_kappa_*``.
        cells: list[tuple[Mapping[str, str], float]] = []  # (branch_refs, log_weight)
        for combo in product(*hyp_lists):
            branch_refs = {
                entity_ids[i]: combo[i].hypothesis_id for i in range(len(entity_ids))
            }
            # log of product of marginal probabilities. Treat zero-probability
            # cells (a marginal hypothesis with weight=0) as -inf log-weight;
            # they are dropped during normalization.
            log_base = 0.0
            zero_seen = False
            for h in combo:
                if h.probability <= 0.0:
                    zero_seen = True
                    break
                log_base += math.log(h.probability)
            if zero_seen:
                cells.append((branch_refs, float("-inf")))
                continue
            log_pot = (
                coupling.log_potential(branch_refs, marginals) if coupling is not None else 0.0
            )
            cells.append((branch_refs, log_base + log_pot))

        # Numerically stable softmax: subtract max log-weight, exp, normalize.
        finite_logs = [lw for _, lw in cells if math.isfinite(lw)]
        if not finite_logs:
            # All cells are -inf or +inf; degenerate. Fall back to uniform
            # over the cells (mass-zero fallback path also handled by
            # ``normalized()``, but doing it here avoids producing NaN cells).
            uniform = 1.0 / max(1, len(cells))
            joint_hyps: list[JointBranchHypothesis] = [
                JointBranchHypothesis(branch_refs=refs, weight=uniform)
                for refs, _ in cells
            ]
        else:
            log_max = max(finite_logs)
            unnorm: list[float] = []
            for _, lw in cells:
                if math.isfinite(lw):
                    # exp(lw - log_max) is in [0, 1]; never overflows.
                    unnorm.append(math.exp(lw - log_max))
                elif lw == float("inf"):
                    # +inf log-weight (pathological) — let normalize() handle
                    # by treating as a very large finite value so it dominates.
                    unnorm.append(float("inf"))
                else:
                    # -inf log-weight: zero-probability cell.
                    unnorm.append(0.0)
            # If any cell is +inf, only those cells share the mass equally.
            if any(math.isinf(w) for w in unnorm):
                inf_count = sum(1 for w in unnorm if math.isinf(w))
                joint_hyps = []
                for (refs, _), w in zip(cells, unnorm):
                    weight = (1.0 / inf_count) if math.isinf(w) else 0.0
                    joint_hyps.append(JointBranchHypothesis(branch_refs=refs, weight=weight))
            else:
                total = sum(unnorm)
                if total <= 0.0:
                    uniform = 1.0 / max(1, len(cells))
                    joint_hyps = [
                        JointBranchHypothesis(branch_refs=refs, weight=uniform)
                        for refs, _ in cells
                    ]
                else:
                    joint_hyps = [
                        JointBranchHypothesis(branch_refs=refs, weight=w / total)
                        for (refs, _), w in zip(cells, unnorm)
                    ]

        joint = cls(
            entity_ids=entity_ids,
            hypotheses=tuple(joint_hyps),
            off_diagonal_couplings=(),
        )
        return joint.normalized().pruned(max_joint_branches)

    # ----- properties ----------------------------------------------------

    @property
    def probability_mass(self) -> float:
        return sum(h.probability for h in self.hypotheses)

    @property
    def n_entities(self) -> int:
        return len(self.entity_ids)

    @property
    def n_branches(self) -> int:
        return len(self.hypotheses)

    @property
    def basis_labels(self) -> tuple[str, ...]:
        """Branch-basis labels in hypothesis order (``entity::hyp`` tokens)."""
        return tuple(
            "|".join(f"{eid}::{h.branch_refs[eid]}" for eid in self.entity_ids)
            for h in self.hypotheses
        )

    # ----- algebra -------------------------------------------------------

    def normalized(self) -> "JointWaveFunction":
        if not self.hypotheses:
            return self
        mass = self.probability_mass
        if mass <= 0:
            uniform = 1.0 / len(self.hypotheses)
            new_hyps = tuple(h.with_weight(uniform) for h in self.hypotheses)
            return JointWaveFunction(
                entity_ids=self.entity_ids,
                hypotheses=new_hyps,
                off_diagonal_couplings=(),
            )
        scale = 1.0 / mass
        new_hyps = tuple(h.with_weight(h.probability * scale) for h in self.hypotheses)
        new_off = tuple(
            OffDiagonalEntry(e.row, e.col, e.amplitude * scale) for e in self.off_diagonal_couplings
        )
        return JointWaveFunction(
            entity_ids=self.entity_ids,
            hypotheses=new_hyps,
            off_diagonal_couplings=new_off,
        )

    def pruned(self, max_joint_branches: int) -> "JointWaveFunction":
        """Prune to at most ``max_joint_branches`` cells, then renormalize.

        Order locked in ``WORK_PLAN_V04.md`` §3.1:

        1. Cells with **lower probability** are pruned first (ascending
           weight removed first).
        2. **Tie-break: lexicographic** by the tuple of branch ids in
           ``self.entity_ids`` order. Among equal-weight cells, the one
           with the **lex-smaller** branch_refs key tuple is **kept**; the
           lex-larger one is removed first.

        Implementation: sort by ``(-weight, lex_key)`` and take the head.
        Determinism: no reliance on dict insertion order or float-equality
        accidents — keys are looked up explicitly via ``self.entity_ids``.
        """
        if max_joint_branches <= 0:
            raise ValueError("max_joint_branches must be positive")
        if len(self.hypotheses) <= max_joint_branches:
            return self

        def lex_key(h: JointBranchHypothesis) -> tuple[str, ...]:
            return tuple(h.branch_refs[eid] for eid in self.entity_ids)

        sorted_hyps = sorted(
            self.hypotheses,
            key=lambda h: (-h.probability, lex_key(h)),
        )
        kept = tuple(sorted_hyps[:max_joint_branches])
        old_to_new: dict[int, int] = {}
        for new_i, hyp in enumerate(kept):
            old_i = self.hypotheses.index(hyp)
            old_to_new[old_i] = new_i
        new_couplings: list[OffDiagonalEntry] = []
        for e in self.off_diagonal_couplings:
            nr = old_to_new.get(e.row)
            nc = old_to_new.get(e.col)
            if nr is None or nc is None:
                continue
            new_couplings.append(OffDiagonalEntry(nr, nc, e.amplitude))
        return JointWaveFunction(
            entity_ids=self.entity_ids,
            hypotheses=kept,
            off_diagonal_couplings=tuple(new_couplings),
        ).normalized()

    # ----- marginalization ----------------------------------------------

    def marginal(self, entity_id: str) -> dict[str, float]:
        """Return ``P(branch | entity_id)`` by summing joint weights over all
        other entities' branches.

        This is the function the marginal-recovery test (acceptance criterion
        2) calls: when coupling is zero, the joint marginal must equal the
        per-entity marginal that was fed into :meth:`from_marginals`, within
        ε = 1e-6.
        """
        if entity_id not in self.entity_ids:
            raise ValueError(
                f"entity {entity_id!r} not in this joint; entities are {self.entity_ids}"
            )
        out: dict[str, float] = {}
        for h in self.hypotheses:
            ref = h.branch_refs[entity_id]
            out[ref] = out.get(ref, 0.0) + h.probability
        return out

    # ----- v0.4 M3 scoring helpers --------------------------------------

    def probability_in_region(
        self,
        region: "RectRegion",
        marginals: Mapping[str, "WaveFunction"],
    ) -> float:
        """v0.4 M3: P(all entities in ``region``) under this joint.

        Sums joint cell probabilities where every entity's selected branch
        has its position inside the region. Used by ``WORK_PLAN_V04.md`` §5
        criterion 4(a) — the Bernoulli interpretability metric ("all in
        region R at horizon").

        Args:
            region: a :class:`omytea.models.RectRegion` to test against.
            marginals: per-entity :class:`WaveFunction` mapping. Must include
                every entity in ``self.entity_ids``; otherwise the affected
                cells contribute 0.
        """
        total = 0.0
        for h in self.hypotheses:
            all_inside = True
            for entity_id in self.entity_ids:
                hypothesis_id = h.branch_refs.get(entity_id)
                if hypothesis_id is None:
                    all_inside = False
                    break
                wave = marginals.get(entity_id)
                if wave is None:
                    all_inside = False
                    break
                hyp = next(
                    (sh for sh in wave.hypotheses if sh.hypothesis_id == hypothesis_id),
                    None,
                )
                if hyp is None or not region.contains(hyp.position):
                    all_inside = False
                    break
            if all_inside:
                total += h.probability
        return total

    def pair_distance_distribution(
        self,
        entity_a: str,
        entity_b: str,
        marginals: Mapping[str, "WaveFunction"],
    ) -> tuple[list[float], list[float]]:
        """v0.4 M3: empirical (samples, weights) for ‖x_A − x_B‖₂ under this joint.

        Returns the predictive distribution of pair-separation distance
        between ``entity_a`` and ``entity_b`` as parallel lists. Cells
        whose marginal hypotheses can't be resolved are dropped (empty
        result is a programmer error upstream — caller should verify
        the entities are in ``self.entity_ids``).

        Used by ``WORK_PLAN_V04.md`` §5 criterion 4(b) — the continuous-CRPS
        statistical metric on horizon-time pair separation. Feed the result
        directly into :func:`omytea.scoring.crps_empirical_weighted`.
        """
        if entity_a not in self.entity_ids or entity_b not in self.entity_ids:
            raise ValueError(
                f"entity_a={entity_a!r} and entity_b={entity_b!r} must both "
                f"be in this joint's entity_ids {self.entity_ids}"
            )
        wave_a = marginals.get(entity_a)
        wave_b = marginals.get(entity_b)
        if wave_a is None or wave_b is None:
            raise ValueError(
                "marginals must include WaveFunctions for both entity_a and entity_b"
            )
        # Index hypotheses by id for O(1) lookup.
        index_a = {h.hypothesis_id: h for h in wave_a.hypotheses}
        index_b = {h.hypothesis_id: h for h in wave_b.hypotheses}
        samples: list[float] = []
        weights: list[float] = []
        for cell in self.hypotheses:
            id_a = cell.branch_refs.get(entity_a)
            id_b = cell.branch_refs.get(entity_b)
            if id_a is None or id_b is None:
                continue
            hyp_a = index_a.get(id_a)
            hyp_b = index_b.get(id_b)
            if hyp_a is None or hyp_b is None:
                continue
            dx = hyp_a.position.x - hyp_b.position.x
            dy = hyp_a.position.y - hyp_b.position.y
            dz = (hyp_a.position.z or 0.0) - (hyp_b.position.z or 0.0)
            samples.append(math.sqrt(dx * dx + dy * dy + dz * dz))
            weights.append(cell.probability)
        return samples, weights

    # ----- density-matrix bridge (PLAN.md primary representation) -------

    def to_joint_diagonal_rho(self) -> JointDiagonalRho:
        """v0.4-style sparse diagonal view (ignores off-diagonal couplings)."""
        return JointDiagonalRho(basis_labels=self.basis_labels, diagonal=tuple(h.probability for h in self.hypotheses))

    def to_density_matrix(self) -> DensityMatrix:
        """Full complex ``N×N`` ρ in the branch tensor-product basis."""
        n = len(self.hypotheses)
        if n == 0:
            raise ValueError("to_density_matrix requires at least one joint hypothesis")
        rows: list[list[complex]] = [[0.0j] * n for _ in range(n)]
        for i, h in enumerate(self.hypotheses):
            rows[i][i] = complex(float(h.probability), 0.0)
        for e in self.off_diagonal_couplings:
            rows[e.row][e.col] = e.amplitude
        return DensityMatrix.from_complex_matrix(rows, check=True)

    @classmethod
    def from_density_matrix(
        cls,
        rho: DensityMatrix,
        *,
        hypotheses: tuple[JointBranchHypothesis, ...],
        entity_id_order: tuple[str, ...],
        diagonal_threshold: float = 1e-12,
        off_diagonal_threshold: float = 1e-12,
    ) -> "JointWaveFunction":
        """Reconstruct a joint from a full density matrix and caller-supplied cells.

        Diagonal reals above ``diagonal_threshold`` become hypothesis weights;
        off-diagonal entries above ``off_diagonal_threshold`` in magnitude
        become explicit Hermitian :class:`OffDiagonalEntry` pairs.
        """
        n = rho.dim
        if len(hypotheses) != n:
            raise ValueError(
                f"hypotheses length ({len(hypotheses)}) must equal rho.dim ({n})"
            )
        new_hyps: list[JointBranchHypothesis] = []
        for i, h in enumerate(hypotheses):
            w = float(rho.data[i][i].real)
            if abs(w) < diagonal_threshold:
                w = 0.0
            new_hyps.append(h.with_weight(w))
        couplings: list[OffDiagonalEntry] = []
        for i in range(n):
            for j in range(i + 1, n):
                a = rho.data[i][j]
                if abs(a) > off_diagonal_threshold:
                    couplings.append(OffDiagonalEntry(i, j, a))
                    couplings.append(OffDiagonalEntry(j, i, a.conjugate()))
        return cls(
            entity_ids=entity_id_order,
            hypotheses=tuple(new_hyps),
            off_diagonal_couplings=tuple(couplings),
        ).normalized()

    def add_off_diagonal_pair(self, row: int, col: int, amplitude: complex) -> "JointWaveFunction":
        """Return a copy with Hermitian pair ``(row,col)`` and ``(col,row)`` inserted."""
        if row == col:
            raise ValueError("add_off_diagonal_pair requires row != col")
        n = len(self.hypotheses)
        if not (0 <= row < n and 0 <= col < n):
            raise ValueError(f"indices out of range for n={n}: ({row}, {col})")
        extra = (
            OffDiagonalEntry(row, col, amplitude),
            OffDiagonalEntry(col, row, amplitude.conjugate()),
        )
        return JointWaveFunction(
            entity_ids=self.entity_ids,
            hypotheses=self.hypotheses,
            off_diagonal_couplings=self.off_diagonal_couplings + extra,
        )


__all__ = [
    "JointBranchHypothesis",
    "JointCoupling",
    "DistanceCoupling",
    "RelationCoupling",
    "TypedJointCoupling",
    "JointDiagonalRho",
    "JointWaveFunction",
    "OffDiagonalEntry",
]
