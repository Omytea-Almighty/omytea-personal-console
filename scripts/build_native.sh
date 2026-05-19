#!/usr/bin/env bash
# Build a native bundle of the Omytea Personal Future Console via
# PyInstaller. Defaults to one-folder; pass --onefile for a single
# self-contained executable.
#
# Output (one-folder, default):
#     dist/omytea-console/                       # the bundle folder
#     dist/omytea-console/omytea-console         # the launch binary
#
# Output (--onefile):
#     dist/omytea-console            (macOS / Linux)
#     dist/omytea-console.exe        (Windows)
#
# Usage:
#     bash scripts/build_native.sh            # one-folder
#     bash scripts/build_native.sh --onefile  # single binary
#
# Trade-offs:
#   one-folder → ~1-2s startup, multiple files to distribute
#   --onefile  → ~3-8s startup, a single file to download

set -euo pipefail

MODE="folder"
SPEC_FILE="omytea-console.spec"
for arg in "$@"; do
    case "${arg}" in
        --onefile)
            MODE="onefile"
            SPEC_FILE="omytea-console-onefile.spec"
            ;;
        --folder)
            MODE="folder"
            SPEC_FILE="omytea-console.spec"
            ;;
        *)
            echo "Unknown arg: ${arg}"
            echo "Usage: bash scripts/build_native.sh [--onefile|--folder]"
            exit 2
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_DIR}"

echo "=================================================="
echo "  Omytea Console — native bundle builder (${MODE})"
echo "=================================================="
echo ""

# Step 1: venv check
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ -d "${REPO_DIR}/.venv" ]]; then
        echo "→ Activating .venv ..."
        # shellcheck disable=SC1091
        source "${REPO_DIR}/.venv/bin/activate"
    else
        echo "⚠ No virtualenv detected. Run scripts/install.sh first,"
        echo "  or activate your own venv before invoking this script."
        echo "  Continuing with system Python (not recommended) ..."
    fi
fi

# Step 2: pyinstaller install
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "→ Installing PyInstaller ..."
    pip install 'pyinstaller>=6.0,<7.0' --quiet
fi

# Step 3: clean previous build
if [[ -d "${REPO_DIR}/build" ]]; then
    echo "→ Cleaning previous build/ dir ..."
    rm -rf "${REPO_DIR}/build"
fi
if [[ -d "${REPO_DIR}/dist/omytea-console" ]]; then
    echo "→ Cleaning previous dist/omytea-console/ dir ..."
    rm -rf "${REPO_DIR}/dist/omytea-console"
fi
if [[ -f "${REPO_DIR}/dist/omytea-console" ]]; then
    echo "→ Cleaning previous dist/omytea-console single binary ..."
    rm -f "${REPO_DIR}/dist/omytea-console"
fi
if [[ -f "${REPO_DIR}/dist/omytea-console.exe" ]]; then
    rm -f "${REPO_DIR}/dist/omytea-console.exe"
fi

# Step 4: build
echo "→ Running PyInstaller with ${SPEC_FILE} (this can take 1-5 minutes) ..."
pyinstaller --noconfirm "${SPEC_FILE}"

# Step 5: report
if [[ "${MODE}" == "folder" ]]; then
    BUNDLE_DIR="${REPO_DIR}/dist/omytea-console"
    if [[ -d "${BUNDLE_DIR}" ]]; then
        BUNDLE_SIZE=$(du -sh "${BUNDLE_DIR}" | cut -f1)
        echo ""
        echo "=================================================="
        echo "  Build complete (one-folder mode)."
        echo "=================================================="
        echo "  Bundle:  ${BUNDLE_DIR}"
        echo "  Size:    ${BUNDLE_SIZE}"
        echo ""
        echo "Launch the bundle:"
        echo "    ${BUNDLE_DIR}/omytea-console"
        echo ""
        echo "A browser tab opens at http://127.0.0.1:8501."
        echo ""
        echo "Distribute by zipping or tarring the entire folder:"
        echo "    tar czf omytea-console-\$(uname -s)-\$(uname -m).tar.gz -C dist omytea-console"
        echo ""
    else
        echo "✗ Build failed — dist/omytea-console/ does not exist."
        exit 1
    fi
else
    # onefile
    SINGLE_FILE="${REPO_DIR}/dist/omytea-console"
    if [[ -f "${SINGLE_FILE}" ]]; then
        FILE_SIZE=$(du -h "${SINGLE_FILE}" | cut -f1)
        echo ""
        echo "=================================================="
        echo "  Build complete (single-binary mode)."
        echo "=================================================="
        echo "  Binary:  ${SINGLE_FILE}"
        echo "  Size:    ${FILE_SIZE}"
        echo ""
        echo "Launch the binary:"
        echo "    ${SINGLE_FILE}"
        echo ""
        echo "A browser tab opens at http://127.0.0.1:8501."
        echo ""
        echo "Distribute as-is — no folder, no extraction needed."
        echo "    cp ${SINGLE_FILE} ~/Downloads/   # ready to share"
        echo ""
        echo "Note: first launch takes 3-8s as the bootloader unpacks."
        echo ""
    else
        echo "✗ Build failed — dist/omytea-console single binary does not exist."
        exit 1
    fi
fi
