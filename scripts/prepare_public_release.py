"""Public-release prep — assemble a fresh-clone standalone copy of the
Personal Future Console with the Omytea quantum substrate vendored in.

Why fresh-clone instead of ``git subtree split``: a real subtree split
preserves history, which means every internal commit message (with
its references to internal milestones, plan documents, etc.) ends up
in the public repo. We want the public repo to be a snapshot release,
not a history sync.

What this script does:

1. Pick an output directory (default: ``<repo>/dist/omytea-personal-
   console-public/``). Wipe it if it exists.
2. Copy the entire omytea-personal-console source tree, excluding
   internal artifacts (``__pycache__``, ``.venv``, ``.pytest_cache``,
   ``*.pyc``, ``runs/``, ``tests/runs/``).
3. Vendor a minimal subset of the parent Omytea quantum substrate
   into ``omytea/`` inside the dist (so ``from omytea.quantum import
   ...`` keeps working unchanged).
4. Drop in a top-level Apache-2.0 ``LICENSE`` and a ``NOTICE`` that
   credits the vendored substrate.
5. Print a summary + the suggested next steps for publishing.

This script never touches a remote — publishing is a separate
operator step (``git init && git remote add ... && git push``).

Usage:
    python scripts/prepare_public_release.py [--output PATH] [--source-omytea PATH] [--verify]

Flags:
    --output PATH         Override default dist directory.
    --source-omytea PATH  Path to the parent omytea/src tree
                          containing the vendor source files.
    --verify              After copying, run pytest in the dist
                          directory to confirm it's standalone.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


# Vendor set — files copied into <dist>/omytea/ so console.py's
# `from omytea.quantum import ...` etc. keeps working.
#
# NOTE: ``__init__.py`` is NOT copied from the parent — the parent's
# init imports a huge set of subsystems (analytics / perception /
# scoring / persistence / ...) that the personal console doesn't need.
# We synthesize a slim package init via ``_write_vendor_init()``.
OMYTEA_VENDOR_FILES: tuple[str, ...] = (
    "models.py",
    "density.py",
    "quantum.py",
    "joint_belief.py",
)

OMYTEA_VENDOR_DYNAMICS: tuple[str, ...] = (
    "protocol.py",
    "lindblad.py",
)


# Synthesized package init — exposes only the API surface the
# personal console actually imports. The slim shape also keeps the
# public package surface small, which is the right policy for an
# Apache-2.0 vendored snapshot.
_VENDOR_OMYTEA_INIT = '''"""Omytea quantum substrate — vendored snapshot.

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
'''

_VENDOR_DYNAMICS_INIT = '''"""Omytea dynamics — vendored snapshot.

Exposes the Lindblad open-system operator + OperatorContext / BeliefState
protocol types that the Personal Future Console uses to evolve the
joint-hypothesis off-diagonal coherence over time.
"""

from omytea.dynamics.protocol import (
    BeliefState,
    JointBeliefState,
    OperatorContext,
)
from omytea.dynamics.lindblad import LindbladOperator

__all__ = [
    "BeliefState",
    "JointBeliefState",
    "OperatorContext",
    "LindbladOperator",
]
'''

# Source-tree directories / files we never want in the public dist.
EXCLUDE_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
    "runs",              # local self-test data — never publish
    "dist",              # don't recurse into prior output
    "distribution_kit",  # internal operator workflow (email templates,
                         # PII-bearing privacy notice for the manual
                         # round-trip path); the public deploy carries
                         # its own PRIVACY_POLICY.md at the root.
})


# Individual top-level files to drop from the public dist. These are
# internal-audience documents (operator workflow, dev-process guides)
# that aren't part of the user-facing surface and may reference
# internal-only context.
EXCLUDE_FILES: frozenset[str] = frozenset({
    "SELF_TEST_GUIDE.md",  # operator workflow w/ cycle / admin refs
})


APACHE_2_0_LICENSE = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use the files in this directory except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

NOTICE_TEMPLATE = """Omytea Personal Future Console
Copyright {year} Omytea LLC

This product includes software developed by Omytea LLC and contributors.

Vendored components
-------------------
The `omytea/` package in this directory is a snapshot of the Omytea
quantum substrate (parts of `omytea.quantum`, `omytea.joint_belief`,
`omytea.models`, `omytea.density`, `omytea.dynamics.*`). The original
sources live in the upstream Omytea repository; the snapshot here is
included under Apache License 2.0 to keep the personal-console
package self-contained.
"""


def _safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _copy_filtered_tree(src: Path, dst: Path) -> int:
    """Copy ``src`` to ``dst`` skipping anything in EXCLUDE_NAMES.

    Returns the number of files copied.

    The exclude check looks only at path components *relative to* the
    source root — so a source path that happens to live under a
    folder named "dist" or "runs" (e.g. when the prep script is run
    from inside a previously-assembled dist tree) is not falsely
    filtered.
    """
    count = 0
    for entry in src.rglob("*"):
        if entry.is_dir():
            continue
        if entry.suffix == ".pyc":
            continue
        rel = entry.relative_to(src)
        if any(part in EXCLUDE_NAMES for part in rel.parts):
            continue
        if entry.name in EXCLUDE_FILES:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry, target)
        count += 1
    return count


def _vendor_omytea(parent_omytea_src: Path, dst: Path) -> int:
    """Copy the Omytea vendor subset into ``dst/omytea/`` + synthesize
    slim ``__init__.py`` shims.

    Returns the total number of files written (copies + synthesized).
    """
    target = dst / "omytea"
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for filename in OMYTEA_VENDOR_FILES:
        src_file = parent_omytea_src / filename
        if not src_file.exists():
            raise FileNotFoundError(
                f"Expected vendor source {src_file} not found. Provide "
                f"--source-omytea pointing at a tree that contains it."
            )
        shutil.copy2(src_file, target / filename)
        count += 1

    # Write slim package __init__ (replaces the bloated upstream one
    # that imports analytics / perception / scoring / persistence).
    (target / "__init__.py").write_text(
        _VENDOR_OMYTEA_INIT, encoding="utf-8",
    )
    count += 1

    dynamics_target = target / "dynamics"
    dynamics_target.mkdir(parents=True, exist_ok=True)
    for filename in OMYTEA_VENDOR_DYNAMICS:
        src_file = parent_omytea_src / "dynamics" / filename
        if not src_file.exists():
            raise FileNotFoundError(
                f"Expected vendor source {src_file} not found."
            )
        shutil.copy2(src_file, dynamics_target / filename)
        count += 1

    # Slim dynamics __init__.
    (dynamics_target / "__init__.py").write_text(
        _VENDOR_DYNAMICS_INIT, encoding="utf-8",
    )
    count += 1

    return count


def _write_license_and_notice(dst: Path, year: int) -> None:
    (dst / "LICENSE").write_text(APACHE_2_0_LICENSE, encoding="utf-8")
    (dst / "NOTICE").write_text(
        NOTICE_TEMPLATE.format(year=year), encoding="utf-8",
    )


def _verify_dist(dst: Path) -> int:
    """Run `python -m pytest -q` inside the dist directory. Returns
    the exit code of pytest."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=dst,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "--output",
        type=Path,
        default=here / "dist" / "omytea-personal-console-public",
        help="Where to assemble the dist tree (default: <repo>/dist/...)",
    )
    parser.add_argument(
        "--source-omytea",
        type=Path,
        default=here.parent / "src" / "omytea",
        help="Path to the parent omytea/src tree to vendor.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run pytest in the dist after assembly.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Copyright year in NOTICE.",
    )
    args = parser.parse_args(argv)

    src = here
    dst: Path = args.output.resolve()
    parent_omytea_src: Path = args.source_omytea.resolve()

    if not parent_omytea_src.exists():
        print(
            f"ERROR: omytea source tree not found at {parent_omytea_src}. "
            f"Pass --source-omytea to override.",
            file=sys.stderr,
        )
        return 2

    print(f"  source:  {src}")
    print(f"  dst:     {dst}")
    print(f"  omytea:  {parent_omytea_src}")

    _safe_rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    n_files = _copy_filtered_tree(src, dst)
    print(f"  copied {n_files} project files")

    n_vendor = _vendor_omytea(parent_omytea_src, dst)
    print(f"  vendored {n_vendor} omytea files")

    _write_license_and_notice(dst, year=args.year)
    print("  wrote LICENSE + NOTICE")

    if args.verify:
        print("\nRunning pytest in dist (this may take a few seconds)...")
        rc = _verify_dist(dst)
        if rc != 0:
            print(
                f"\nERROR: pytest in dist returned non-zero ({rc}).",
                file=sys.stderr,
            )
            return rc
        print("Verification passed.")

    print("\n=== Public release dist ready ===")
    print(f"Next steps (operator-driven; this script does NOT push):")
    print(f"  cd {dst}")
    print(f"  git init")
    print(f"  git add -A")
    print(f"  git commit -m 'Initial public release of "
          f"omytea-personal-console'")
    print(f"  git remote add origin "
          f"git@github.com:<org>/omytea-personal-console.git")
    print(f"  git push -u origin main")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
