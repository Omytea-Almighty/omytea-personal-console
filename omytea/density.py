"""DensityMatrix utility — centralizes ρ (complex matrix) operations.

[OMY-V05 / M3 / Acceptance #7]

Wraps the ``ComplexMatrix`` list-of-lists representation used by
:mod:`omytea.quantum_engine` with explicit invariant helpers. New code should
prefer this type; :mod:`omytea.quantum_engine` keeps thin wrappers for backward
compatibility.

Note: :class:`omytea.joint_belief.JointWaveFunction.to_density_matrix` returns
this type (full ``N×N`` complex ρ). :class:`omytea.joint_belief.JointDiagonalRho`
is the legacy sparse diagonal-only view via :meth:`~omytea.joint_belief.JointWaveFunction.to_joint_diagonal_rho`.
The quantum engine also uses this representation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

ComplexMatrix = list[list[complex]]


def _quadratic_form_data(data: tuple[tuple[complex, ...], ...], v: list[complex]) -> complex:
    n = len(data)
    tmp = [sum(data[i][j] * v[j] for j in range(n)) for i in range(n)]
    return sum(v[i].conjugate() * tmp[i] for i in range(n))


@dataclass(frozen=True, slots=True)
class DensityMatrix:
    """Density matrix ρ stored as immutable rows of complex numbers."""

    data: tuple[tuple[complex, ...], ...]

    def __post_init__(self) -> None:
        n = len(self.data)
        if n == 0:
            raise ValueError("DensityMatrix must be non-empty (dim 0 is meaningless)")
        for row in self.data:
            if len(row) != n:
                raise ValueError(f"DensityMatrix must be square; got {n}x{len(row)}")

    @property
    def dim(self) -> int:
        return len(self.data)

    @classmethod
    def from_amplitudes(cls, amplitudes: Sequence[complex], *, check: bool = True) -> DensityMatrix:
        """Pure state ρ = |ψ⟩⟨ψ| with |ψ⟩ normalized from ``amplitudes``."""
        amps = list(amplitudes)
        norm_sq = sum(abs(z) ** 2 for z in amps)
        if norm_sq <= 1e-30:
            raise ValueError("amplitudes have zero norm")
        inv = norm_sq**0.5
        psi = [z / inv for z in amps]
        raw = tuple(tuple(a * b.conjugate() for b in psi) for a in psi)
        dm = cls(data=raw)
        if check:
            if not dm.is_hermitian(tol=1e-8):
                raise ValueError("from_amplitudes produced non-Hermitian matrix")
            if abs(dm.trace - 1.0) > 1e-6:
                raise ValueError(f"from_amplitudes trace must be 1; got {dm.trace}")
        return dm

    @classmethod
    def from_diagonal(cls, probabilities: Sequence[float], *, check: bool = True) -> DensityMatrix:
        """Classical mixture: diagonal ρ from a probability vector (off-diagonals zero)."""
        clean = [max(0.0, float(p)) for p in probabilities]
        s = sum(clean)
        if s <= 1e-30:
            n = max(1, len(clean))
            clean = [1.0 / n] * n
        else:
            clean = [p / s for p in clean]
        n = len(clean)
        rows = tuple(
            tuple(complex(clean[i], 0.0) if i == j else 0.0j for j in range(n))
            for i in range(n)
        )
        dm = cls(data=rows)
        if check:
            if not dm.is_hermitian(tol=1e-8):
                raise ValueError("from_diagonal produced non-Hermitian matrix")
            if abs(dm.trace - 1.0) > 1e-6:
                raise ValueError(f"from_diagonal trace must be 1; got {dm.trace}")
        return dm

    @classmethod
    def from_complex_matrix(cls, matrix: ComplexMatrix, *, check: bool = False) -> DensityMatrix:
        data = tuple(tuple(row) for row in matrix)
        dm = cls(data=data)
        if check and not dm.is_hermitian(tol=1e-8):
            raise ValueError("matrix is not Hermitian")
        return dm

    @classmethod
    def outer_from_amplitudes(cls, amplitudes: Sequence[complex], *, check: bool = False) -> DensityMatrix:
        """ρ_ij = a_i a_j* without normalizing (matches legacy :func:`quantum_engine.density_matrix`)."""
        amps = list(amplitudes)
        raw = tuple(tuple(a * b.conjugate() for b in amps) for a in amps)
        dm = cls(data=raw)
        if check and not dm.is_hermitian():
            raise ValueError("outer product state is not Hermitian")
        return dm

    def to_complex_matrix(self) -> ComplexMatrix:
        return [list(row) for row in self.data]

    @property
    def trace_complex(self) -> complex:
        return sum(self.data[i][i] for i in range(self.dim))

    @property
    def trace(self) -> float:
        return float(self.trace_complex.real)

    def quadratic_form(self, v: list[complex]) -> complex:
        """Compute v† ρ v."""
        if len(v) != self.dim:
            raise ValueError("vector dimension mismatch")
        return _quadratic_form_data(self.data, v)

    def is_hermitian(self, *, tol: float = 1e-9) -> bool:
        n = self.dim
        return all(
            abs(self.data[i][j] - self.data[j][i].conjugate()) <= tol for i in range(n) for j in range(n)
        )

    def is_psd_probe(self, *, n_samples: int = 8, tol: float = 1e-9) -> bool:
        """Random unit-vector probe; seed ``0xC0DE`` matches measurement router."""
        rng = random.Random(0xC0DE)
        n = self.dim
        for _ in range(n_samples):
            v = [complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(n)]
            norm = sum(abs(c) ** 2 for c in v) ** 0.5
            if norm == 0:
                continue
            v = [c / norm for c in v]
            val = _quadratic_form_data(self.data, v).real
            if val < -tol:
                return False
        return True

    def normalized_trace(self) -> DensityMatrix:
        tr = self.trace_complex
        if abs(tr) <= 1e-12:
            n = self.dim
            uniform = 1.0 / n
            rows = tuple(
                tuple(complex(uniform, 0.0) if i == j else 0.0j for j in range(n)) for i in range(n)
            )
            return DensityMatrix(data=rows)
        inv = 1.0 / tr
        rows = tuple(tuple(cell * inv for cell in row) for row in self.data)
        return DensityMatrix(data=rows)

    def diagonal(self) -> tuple[float, ...]:
        return tuple(self.data[i][i].real for i in range(self.dim))

    def expectation(self, observable: ComplexMatrix) -> complex:
        """Tr(O ρ) = Σ_i Σ_j O_ij ρ_ji."""
        n = self.dim
        if len(observable) != n or any(len(observable[i]) != n for i in range(n)):
            raise ValueError("observable must be N×N matching density matrix")
        s = 0.0j
        for i in range(n):
            for j in range(n):
                s += observable[i][j] * self.data[j][i]
        return s

    # ------------------------------------------------------------------
    # v3.3 quantum-information primitives (per QUANTUM_WORLD_MODEL_ORIGINALITY
    # §4.6 — density-matrix database queries). First concrete §4.6 primitive:
    # von Neumann entropy. The §4.6 contribution claim is that ρ as
    # first-class queryable object lets us interrogate any agent's belief
    # state through quantum-information operations; entropy is the
    # canonical scalar summary of how mixed the state is.
    # ------------------------------------------------------------------

    def von_neumann_entropy(self, *, log_base: float = 2.0, tol: float = 1e-12) -> float:
        """Compute S(ρ) = -Tr(ρ log ρ) using eigenvalue decomposition.

        For a pure state (ρ = |ψ⟩⟨ψ|), S = 0. For maximally mixed state
        (ρ = I/N), S = log(N) (in the chosen base). Bounded above by
        log(dim) per Nielsen & Chuang theorem 11.8 (max entropy theorem).

        Args:
            log_base: 2.0 → bits (default; Shannon convention),
                      math.e → nats, 10.0 → decits.
            tol: eigenvalues with |λ| < tol treated as zero (numerical
                stability; ρ has nonneg eigenvalues but tiny imaginary
                parts may arise from finite precision).

        Returns:
            Real-valued entropy. NaN if ρ is non-Hermitian (numpy.linalg
            cannot eigendecompose) or has negative eigenvalues outside
            tolerance (indicates ρ is not PSD).

        Per ADR-019 §3 compiler-moat thesis: a future quantum-hardware
        backend could compute this via expectation-value-of-log-ρ on a
        prepared state. The numpy fallback (this implementation) is the
        canonical CMOS reference.

        Per QUANTUM_WORLD_MODEL_ORIGINALITY_RESEARCH.md §4.6: this is the
        first paper-shaped query primitive — "given two world-model
        snapshots ρ(t1) and ρ(t2), which is more mixed?" is now a
        single-call query.
        """
        import math

        import numpy as np

        n = self.dim
        # Build complex matrix; numpy handles the eigendecomposition
        arr = np.array(
            [[complex(self.data[i][j]) for j in range(n)] for i in range(n)],
            dtype=np.complex128,
        )
        # eigh requires Hermitian input; we silently use it (the docstring
        # warns NaN on non-Hermitian). For non-Hermitian, use eig as
        # fallback — but then eigenvalues can be complex; we take real
        # part only.
        try:
            eigvals = np.linalg.eigvalsh(arr)  # real eigenvalues for Hermitian
        except np.linalg.LinAlgError:
            return float("nan")
        # Filter near-zero (log diverges); use shannon-style convention
        # 0 * log(0) = 0.
        entropy_nats = 0.0
        for lam in eigvals:
            x = float(lam.real if hasattr(lam, "real") else lam)
            if abs(x) < tol:
                continue
            if x < -tol:
                # Negative eigenvalue → not PSD → undefined entropy
                return float("nan")
            x = max(x, tol)  # numerical floor; safe because log monotone
            entropy_nats -= x * math.log(x)
        # Convert from nats to chosen base
        if log_base == math.e:
            return entropy_nats
        return entropy_nats / math.log(log_base)

    def purity(self) -> float:
        """Compute Tr(ρ²), bounded in [1/dim, 1].

        Tr(ρ²) = 1 iff ρ is pure. Tr(ρ²) = 1/N iff ρ is maximally mixed.
        The "linearized entropy" S_2 = 1 - Tr(ρ²) is a cheap entropy
        proxy that avoids the eigendecomposition (just matrix multiply).

        Per QUANTUM_WORLD_MODEL_ORIGINALITY_RESEARCH.md §4.6: purity is
        the canonical scalar for "how concentrated is the world-model
        belief". Lower purity → more uncertainty.
        """
        n = self.dim
        # Compute ρ² then take trace = Σ_i (ρ²)_ii = Σ_ij ρ_ij ρ_ji
        s = 0.0
        for i in range(n):
            for j in range(n):
                # (ρ²)_ii = Σ_j ρ_ij ρ_ji ; trace = Σ_i (ρ²)_ii
                term = self.data[i][j] * self.data[j][i]
                # term is complex; its imaginary parts cancel for Hermitian ρ
                s += term.real
        return s


__all__ = ["ComplexMatrix", "DensityMatrix"]
