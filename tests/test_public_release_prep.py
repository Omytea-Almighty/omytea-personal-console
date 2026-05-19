"""Tests for the public-release prep script.

Mostly exercise the pure-function helpers (filter / vendor / license)
against a temporary directory layout. No GitHub or network access.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import prepare_public_release as prep  # noqa: E402


@pytest.fixture
def tmp_layout(tmp_path: Path) -> dict[str, Path]:
    """Build a tiny source + parent-omytea layout under tmp_path."""
    src = tmp_path / "src_repo"
    omytea_src = tmp_path / "omytea_src"
    out = tmp_path / "dist"

    (src / "subdir").mkdir(parents=True)
    (src / "app.py").write_text("print('hi')")
    (src / "subdir" / "module.py").write_text("x = 1")
    (src / "README.md").write_text("# project")
    # Things that should be excluded:
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "stale.pyc").write_text("garbage")
    (src / "runs").mkdir()
    (src / "runs" / "private.txt").write_text("internal")
    (src / "tests").mkdir()
    (src / "tests" / "test_x.py").write_text("def test_x(): pass")
    (src / "dist").mkdir()
    (src / "dist" / "old_output.txt").write_text("stale")

    # Set up the vendor source tree.
    omytea_src.mkdir(parents=True)
    for name in prep.OMYTEA_VENDOR_FILES:
        (omytea_src / name).write_text(f"# vendor file {name}")
    (omytea_src / "dynamics").mkdir()
    for name in prep.OMYTEA_VENDOR_DYNAMICS:
        (omytea_src / "dynamics" / name).write_text(f"# vendor dyn {name}")

    return {"src": src, "omytea_src": omytea_src, "out": out}


# ----- _copy_filtered_tree -----


def test_copy_filtered_tree_copies_normal_files(tmp_layout) -> None:
    n = prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert n >= 3  # app.py + module.py + README.md + test_x.py
    assert (tmp_layout["out"] / "app.py").exists()
    assert (tmp_layout["out"] / "subdir" / "module.py").exists()
    assert (tmp_layout["out"] / "README.md").exists()


def test_copy_filtered_tree_skips_pycache(tmp_layout) -> None:
    prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert not (tmp_layout["out"] / "__pycache__").exists()


def test_copy_filtered_tree_skips_runs(tmp_layout) -> None:
    prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert not (tmp_layout["out"] / "runs").exists()


def test_copy_filtered_tree_skips_prior_dist(tmp_layout) -> None:
    prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert not (tmp_layout["out"] / "dist").exists()


def test_copy_filtered_tree_skips_pyc_files(tmp_layout) -> None:
    # Add a stray .pyc outside __pycache__.
    (tmp_layout["src"] / "stale.pyc").write_text("garbage")
    prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert not (tmp_layout["out"] / "stale.pyc").exists()


def test_copy_filtered_tree_includes_tests(tmp_layout) -> None:
    """Tests are part of the public package (Apache 2.0 release).
    Verify they DO get copied."""
    prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert (tmp_layout["out"] / "tests" / "test_x.py").exists()


# ----- _vendor_omytea -----


def test_vendor_omytea_copies_all_files(tmp_layout) -> None:
    n = prep._vendor_omytea(tmp_layout["omytea_src"], tmp_layout["out"])
    # OMYTEA_VENDOR_FILES + dynamics + synthesized __init__ × 2.
    assert n == (
        len(prep.OMYTEA_VENDOR_FILES)
        + len(prep.OMYTEA_VENDOR_DYNAMICS)
        + 2  # synthesized __init__.py for the package + dynamics
    )
    target = tmp_layout["out"] / "omytea"
    for name in prep.OMYTEA_VENDOR_FILES:
        assert (target / name).exists()
    for name in prep.OMYTEA_VENDOR_DYNAMICS:
        assert (target / "dynamics" / name).exists()
    # Synthesized inits should exist + reference vendored submodules.
    pkg_init = (target / "__init__.py").read_text()
    assert "from omytea.quantum import" in pkg_init
    assert "from omytea.joint_belief import" in pkg_init
    dyn_init = (target / "dynamics" / "__init__.py").read_text()
    assert "from omytea.dynamics.lindblad import LindbladOperator" in dyn_init


def test_vendor_omytea_raises_when_source_missing(
    tmp_layout, tmp_path: Path,
) -> None:
    bad_src = tmp_path / "nonexistent"
    bad_src.mkdir()  # exists but is empty
    with pytest.raises(FileNotFoundError, match="vendor source"):
        prep._vendor_omytea(bad_src, tmp_layout["out"])


# ----- _write_license_and_notice -----


def test_writes_apache_license_marker(tmp_layout) -> None:
    tmp_layout["out"].mkdir(parents=True, exist_ok=True)
    prep._write_license_and_notice(tmp_layout["out"], year=2026)
    license_text = (tmp_layout["out"] / "LICENSE").read_text()
    assert "Apache License" in license_text
    assert "Version 2.0" in license_text


def test_writes_notice_with_year(tmp_layout) -> None:
    tmp_layout["out"].mkdir(parents=True, exist_ok=True)
    prep._write_license_and_notice(tmp_layout["out"], year=2027)
    notice = (tmp_layout["out"] / "NOTICE").read_text()
    assert "2027" in notice
    assert "Omytea LLC" in notice
    assert "Vendored components" in notice


# ----- _safe_rmtree -----


def test_safe_rmtree_nonexistent_is_noop(tmp_path: Path) -> None:
    """Calling on a missing path should not raise."""
    prep._safe_rmtree(tmp_path / "does-not-exist")


def test_safe_rmtree_removes_existing(tmp_path: Path) -> None:
    target = tmp_path / "removeme"
    target.mkdir()
    (target / "file.txt").write_text("x")
    prep._safe_rmtree(target)
    assert not target.exists()


# ----- Vendor manifest sanity -----


def test_vendor_manifest_no_duplicates() -> None:
    assert len(set(prep.OMYTEA_VENDOR_FILES)) == len(prep.OMYTEA_VENDOR_FILES)
    assert len(set(prep.OMYTEA_VENDOR_DYNAMICS)) == len(
        prep.OMYTEA_VENDOR_DYNAMICS
    )


def test_vendor_manifest_includes_required_modules() -> None:
    """The personal-console code path imports these modules; the
    vendor set MUST cover them or the public release won't build.
    __init__.py is intentionally NOT in the copy-list (we synthesize
    a slim version) — it's checked separately in
    test_vendor_omytea_copies_all_files."""
    required = {
        "quantum.py", "joint_belief.py", "models.py", "density.py",
    }
    assert required.issubset(set(prep.OMYTEA_VENDOR_FILES))
    required_dyn = {"protocol.py", "lindblad.py"}
    assert required_dyn.issubset(set(prep.OMYTEA_VENDOR_DYNAMICS))


def test_exclude_names_includes_known_internal_dirs() -> None:
    for name in (
        "__pycache__", "runs", ".venv", "dist", "distribution_kit",
    ):
        assert name in prep.EXCLUDE_NAMES


def test_exclude_files_drops_internal_top_level_md() -> None:
    """SELF_TEST_GUIDE.md is an operator-workflow doc — must be in
    EXCLUDE_FILES so the public dist doesn't carry it."""
    assert "SELF_TEST_GUIDE.md" in prep.EXCLUDE_FILES


def test_excluded_top_level_files_not_copied(tmp_layout) -> None:
    """End-to-end: a file in EXCLUDE_FILES at the source root is
    skipped by the copier."""
    (tmp_layout["src"] / "SELF_TEST_GUIDE.md").write_text("internal")
    prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert not (tmp_layout["out"] / "SELF_TEST_GUIDE.md").exists()


def test_excluded_directory_distribution_kit_skipped(tmp_layout) -> None:
    (tmp_layout["src"] / "distribution_kit").mkdir()
    (tmp_layout["src"] / "distribution_kit" / "EMAIL.md").write_text("x")
    prep._copy_filtered_tree(tmp_layout["src"], tmp_layout["out"])
    assert not (tmp_layout["out"] / "distribution_kit").exists()


# ----- main() end-to-end smoke (no --verify) -----


def test_main_assembles_dist(tmp_layout, capsys, monkeypatch) -> None:
    out = tmp_layout["out"]
    rc = prep.main([
        "--output", str(out),
        "--source-omytea", str(tmp_layout["omytea_src"]),
    ])
    assert rc == 0
    # The dist tree should have app.py + LICENSE + NOTICE + omytea/*
    assert (out / "app.py").exists()
    assert (out / "LICENSE").exists()
    assert (out / "NOTICE").exists()
    assert (out / "omytea" / "quantum.py").exists()
    assert (out / "omytea" / "dynamics" / "lindblad.py").exists()
    captured = capsys.readouterr()
    assert "Public release dist ready" in captured.out


def test_main_returns_nonzero_when_source_missing(
    tmp_layout, capsys,
) -> None:
    rc = prep.main([
        "--output", str(tmp_layout["out"]),
        "--source-omytea", "/definitely/does/not/exist",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "omytea source tree not found" in captured.err


def test_main_wipes_existing_output(tmp_layout) -> None:
    out = tmp_layout["out"]
    out.mkdir(parents=True)
    (out / "stale_file.txt").write_text("garbage from a previous run")
    rc = prep.main([
        "--output", str(out),
        "--source-omytea", str(tmp_layout["omytea_src"]),
    ])
    assert rc == 0
    assert not (out / "stale_file.txt").exists()
