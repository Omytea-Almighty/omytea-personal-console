# Omytea prediction test tool

An early experiment, separate from the Omytea product. Ask a question about your future and the tool maps the ways it could go, then keeps score as outcomes arrive. Results are demo or LLM estimates, never calibrated forecasts. Not financial, legal, or medical advice.

- **Try it in a browser:** [omytea-console.pages.dev](https://omytea-console.pages.dev)
- **This repository:** the Python version, which you run on your own machine
- **The Omytea product:** [omyteaai.com](https://omyteaai.com)

## What it does

| Mode | What it does |
|---|---|
| New prediction | Takes a decision in plain text and lays out possible futures with estimates, what drives them, and what evidence to collect next |
| Video query | Takes a short video and a question, tracks what is in the scene, and lays out possible futures |
| Measurement update | Takes what actually happened and scores the earlier prediction with Brier score and log-loss |
| Calibration history | Shows those scores across all your predictions |

**Time-honored lens (optional).** Shows BaZi, I Ching, tarot and astrology readings next to a prediction, using birth data you enter. The model's own output stays on screen beside any weighted view.

## How a prediction is made

1. An LLM backend you choose (local Ollama, Gemini, Groq, Anthropic, or mock) turns your question into a structured belief program (`compiler.py`).
2. [`omytea-quantum-substrate`](https://github.com/Omytea-Almighty/omytea-quantum-substrate) generates 3–5 branches with estimated probabilities and shows which futures are correlated.
3. Later, you report what happened and the tool scores the prediction.

Your predictions stay in a local SQLite file at `~/.omytea-personal-console/predictions.db`. If you choose a hosted LLM backend, your question is sent to that provider.

## Install and run

You need Python 3.11 or newer, about 6 GB of disk for local models, and 16 GB of RAM (8 GB is tight). macOS 12+, Ubuntu 22.04+ and Windows 11 with WSL2 are supported.

```bash
git clone https://github.com/Omytea-Almighty/omytea-personal-console.git
cd omytea-personal-console
bash scripts/install.sh
```

`install.sh` creates a `.venv`, installs `requirements.txt`, checks for [Ollama](https://ollama.com/download), and prints the next steps. To install by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Pull the local models:

```bash
ollama pull llava:7b              # vision model for Video query, about 4.5 GB
ollama pull qwen2.5:7b-instruct   # text model for New prediction, about 4.5 GB
```

Start it and open <http://localhost:8501>:

```bash
source .venv/bin/activate
streamlit run app.py
```

To look around without Ollama, use mock mode. It returns fixed stub predictions, so it is only for inspecting the interface:

```bash
OMYTEA_CONSOLE_MOCK=1 streamlit run app.py
```

Run the tests with `pytest tests/`.

### Troubleshooting

- **"OpenCV not installed":** run `pip install opencv-python-headless` inside the venv.
- **"Ollama vision backend not ready":** start the daemon with `ollama serve` and check that `ollama pull llava:7b` finished.
- **Vision model is slow:** the opening call warms the model and later calls are much faster. On CPU-only hardware, speed depends on your CPU.

### Uninstall

```bash
rm -rf .venv
ollama rm llava:7b qwen2.5:7b-instruct
```

Delete `~/.omytea-personal-console/predictions.db` to remove your saved predictions.

## License

Apache 2.0.

---

<!-- OMYTEA_ORG_SYNC_README_START -->
> **Organization source of truth:** [`Omytea-Almighty/omytea-personal-console`](https://github.com/Omytea-Almighty/omytea-personal-console). Humans and agents must read [`ORG-SYNC.md`](ORG-SYNC.md) before working. Managed commit/rewrite hooks queue reviewed commits; ordinary direct push is denied; registered linked worktrees are supported. Automation never stages or commits dirty work, changes visibility, or bypasses hooks.
> This repository is public: every intentional commit is a publication decision. Secret scanning is not a privacy, PII, licensing, research, or commercial-sensitivity review.
<!-- OMYTEA_ORG_SYNC_README_END -->
