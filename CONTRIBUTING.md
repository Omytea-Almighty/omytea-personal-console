# Contributing to Omytea Personal Future Console

Thanks for considering a contribution. This is an open-source project under Apache 2.0; we welcome bug reports, fixes, and feature work that aligns with the project's design constraints.

## Quick links

- **Live demo**: https://omytea-personal-console.streamlit.app
- **Public repo**: https://github.com/Omytea-Almighty/omytea-personal-console
- **Privacy policy**: [PRIVACY_POLICY.md](PRIVACY_POLICY.md)
- **Release notes**: [CHANGELOG.md](CHANGELOG.md)
- **Architectural / strategic anchor**: see master plan in upstream Omytea repo

## Ground rules

Things that fit the project:
- Bug fixes — please include a reproducing test
- New scenarios in `scenarios/` (decision-support domains)
- Visualization improvements (Streamlit components, charts, accessibility)
- Performance work on the perception or quantum-evolution paths
- Documentation improvements (README, walkthrough, paper draft)
- New evaluation metrics in `eval/`
- Multi-vendor LLM backends (provider-neutral by default — see §15 Rule #11)

Things that **don't** fit, and pull requests will be politely declined:
- "Fortune-telling" / "oracle" / "算命" framing in any user-visible copy
- Required external API integrations (the system must work fully offline via Ollama)
- Biometric features (face recognition, demographic attribution, re-identification)
- Multi-camera identity reconciliation (out of scope per master plan v0.4)
- Single-vendor LLM lock-in (every backend must be optional)
- Pixel-level human imagination / deepfake-class generation
- Automated trading, money movement, or legal-advice-without-human-in-loop

## Setup

```bash
git clone https://github.com/Omytea-Almighty/omytea-personal-console.git
cd omytea-personal-console
bash scripts/install.sh
ollama pull llava:7b qwen2.5:7b-instruct   # optional, for real vision LLM
```

For development:

```bash
source .venv/bin/activate
pip install pytest pytest-cov

# Run the full test suite (mock mode — no LLM / no network)
OMYTEA_CONSOLE_MOCK=1 python -m pytest -q

# Run the evaluation harness
OMYTEA_CONSOLE_MOCK=1 python -m eval.run_eval

# Run a real end-to-end test with live Ollama
python scripts/real_e2e.py
```

## Pull request checklist

Before opening a PR:

- [ ] All existing tests still pass (`OMYTEA_CONSOLE_MOCK=1 python -m pytest`)
- [ ] New behavior is covered by tests (target: 1+ unit test per public function added)
- [ ] No new required external dependencies (Ollama and the LLM-backend HTTP libs are the established baseline)
- [ ] Privacy posture preserved — no telemetry added without an explicit opt-out
- [ ] User-visible copy uses "probability" / "calibrated" / "correlated futures" framing, never "fortune" / "oracle"
- [ ] If you touched the brand surface (sidebar, headers, footers), update `_brand.py` rather than hardcoding strings
- [ ] If you touched the eval/ harness, document the new metric in `eval/README.md`

## Bug reports

Open a GitHub Issue with:
- What you did (command, click sequence)
- What you expected to happen
- What actually happened (full stack trace if any)
- Console version (`python -c "import _brand; print(_brand.BRAND_VERSION)"`)
- OS + Python version
- If vision-LLM related: which Ollama model + `ollama --version`

## Code style

- Python: PEP 8 compliant. No formatter enforcement, but please don't add code that would obviously fail a flake8 / ruff lint pass.
- Tests: pytest functions; one assertion per concept; descriptive names.
- Comments: explain *why*, not *what*; document non-obvious design choices inline.

## License

By contributing you agree your contribution is offered under the Apache License 2.0, the same license the project ships under. See [LICENSE](LICENSE) for the full text.

## Code of conduct

Be kind. Disagree about ideas, not about people. If you see behavior that crosses the line, email lewxam0102+omytea-console@gmail.com.
