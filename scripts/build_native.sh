#!/usr/bin/env bash
# Build a native one-folder bundle of the Omytea Personal Future
# Console via PyInstaller.
#
# Output:
#     dist/omytea-console/                       # the bundle folder
#     dist/omytea-console/omytea-console         # the launch binary
#
# Usage:
#     bash scripts/build_native.sh
#
# Then ship dist/omytea-console/ as a tar.gz / zip / DMG.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_DIR}"

echo "=================================================="
echo "  Omytea Console — native bundle builder"
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

# Step 4: build
echo "→ Running PyInstaller (this can take 1-5 minutes) ..."
pyinstaller --noconfirm omytea-console.spec

# Step 5: report
BUNDLE_DIR="${REPO_DIR}/dist/omytea-console"
if [[ -d "${BUNDLE_DIR}" ]]; then
    BUNDLE_SIZE=$(du -sh "${BUNDLE_DIR}" | cut -f1)
    echo ""
    echo "=================================================="
    echo "  Build complete."
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
