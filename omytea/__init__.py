"""Omytea quantum substrate — vendored snapshot.

This is a minimum subset of the Omytea library, snapshotted under
Apache License 2.0 for use by the Personal Future Console package.
The full Omytea library is maintained upstream; refer to the
upstream repo for the complete API.

This vendored snapshot exposes only the types the Personal Future
Console actually depends on:
  - WaveFunction, StateHypothesis, Velocity (from .quantum)
  - JointBranchHypothesis, JointWaveFunction, OffDiagonalEntry
    (from .joint_belief)
  - Position (from .models)
  - DensityMatrix (from .density)
"""

from omytea.models import Position
from omytea.density import DensityMatrix
from omytea.quantum import StateHypothesis, Velocity, WaveFunction
from omytea.joint_belief import (
    JointBranchHypothesis,
    JointWaveFunction,
    OffDiagonalEntry,
)

__all__ = [
    "Position",
    "DensityMatrix",
    "StateHypothesis",
    "Velocity",
    "WaveFunction",
    "JointBranchHypothesis",
    "JointWaveFunction",
    "OffDiagonalEntry",
]
