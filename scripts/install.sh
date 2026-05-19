#!/usr/bin/env bash
# Omytea Personal Future Console — install helper for end users.
#
# What this does:
#   1. Verifies Python >= 3.11
#   2. Creates a .venv if absent
#   3. Installs requirements.txt
#   4. Probes Ollama (presence + reachability)
#   5. Prints next-step model-pull + launch instructions
#
# What this does NOT do:
#   - Pull LLM models (you do this manually: `ollama pull llava:7b`)
#   - Start the Streamlit server (you do this manually: `streamlit run app.py`)
#   - Modify your shell config / install Ollama
#
# Reasoning: each of the not-done steps takes meaningful time / disk /
# network bandwidth, and several are interactive. The script's job is
# to set up the venv + tell you what to do next.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_DIR}"

echo "=================================================="
echo "  Omytea Personal Future Console — install helper"
echo "=================================================="
echo ""
echo "Working in: ${REPO_DIR}"
echo ""

# -- Step 1: Python version check --
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "✗ ${PYTHON_BIN} not found in PATH."
    echo "  Install Python 3.11+ from https://www.python.org/downloads/"
    echo "  or 'brew install python@3.11' on macOS / 'apt install python3.11' on Ubuntu."
    exit 1
fi

PYTHON_VERSION=$("${PYTHON_BIN}" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)
if [[ "${PYTHON_MAJOR}" -lt 3 || ("${PYTHON_MAJOR}" -eq 3 && "${PYTHON_MINOR}" -lt 11) ]]; then
    echo "✗ Python ${PYTHON_VERSION} too old. Need 3.11+."
    echo "  Try 'brew install python@3.11' (macOS) or 'apt install python3.11' (Ubuntu)."
    exit 1
fi
echo "✓ Python ${PYTHON_VERSION} OK"

# -- Step 2: venv --
VENV_DIR="${REPO_DIR}/.venv"
if [[ -d "${VENV_DIR}" ]]; then
    echo "✓ .venv already exists at ${VENV_DIR}"
else
    echo "→ Creating .venv ..."
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    echo "✓ .venv created"
fi

# Activate (subshell)
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# -- Step 3: pip install --
echo "→ Installing requirements (this can take a minute) ..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✓ Python dependencies installed"

# -- Step 4: Ollama probe --
echo ""
echo "→ Probing local Ollama daemon ..."
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_HEALTHY=0
if command -v ollama >/dev/null 2>&1; then
    if curl -s -o /dev/null -w "%{http_code}" "${OLLAMA_HOST}/api/tags" 2>/dev/null | grep -q "200"; then
        OLLAMA_HEALTHY=1
    fi
fi

if [[ "${OLLAMA_HEALTHY}" -eq 1 ]]; then
    echo "✓ Ollama reachable at ${OLLAMA_HOST}"
    # List installed models for the user
    INSTALLED_MODELS=$(curl -s "${OLLAMA_HOST}/api/tags" | python3 -c 'import sys,json; print("\n".join("  - " + m["name"] for m in json.load(sys.stdin).get("models", [])))' 2>/dev/null || echo "")
    if [[ -n "${INSTALLED_MODELS}" ]]; then
        echo "  Installed models:"
        echo "${INSTALLED_MODELS}"
    fi
else
    echo "⚠ Ollama not reachable at ${OLLAMA_HOST}."
    echo "  If you haven't installed Ollama: https://ollama.com/download"
    echo "  If you have but the daemon isn't running: 'ollama serve' or restart your machine."
    echo ""
    echo "  (You can still run the Console in mock mode without Ollama —"
    echo "   set OMYTEA_CONSOLE_MOCK=1 before 'streamlit run app.py'.)"
fi

# -- Step 5: Next steps --
echo ""
echo "=================================================="
echo "  Setup complete. Next steps:"
echo "=================================================="
echo ""
echo "  # 1. Pull a local vision model (~4.5 GB)"
echo "  ollama pull llava:7b"
echo ""
echo "  # 2. Pull a local text model (~4.5 GB)"
echo "  ollama pull qwen2.5:7b-instruct"
echo ""
echo "  # 3. Activate the venv and launch"
echo "  source .venv/bin/activate"
echo "  streamlit run app.py"
echo ""
echo "  # then open http://localhost:8501 in your browser"
echo ""
echo "For the full guide: see README.md § Install and run"
echo ""
