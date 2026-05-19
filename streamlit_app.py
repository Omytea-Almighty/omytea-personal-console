"""Streamlit Cloud entrypoint for Omytea Personal Future Console.

Streamlit Cloud auto-discovers ``streamlit_app.py`` at the repo / subdir
root and uses it as the main entry. This thin module just re-exports
``app.main()`` so the local-dev ``streamlit run app.py`` flow keeps
working unchanged.

Distribution paths:
- Manual hand-off (a small set of high-trust early testers via an
  out-of-band round-trip — see scripts/process_friend_self_test.py).
- Public Streamlit Cloud deploy via this entry — see
  DEPLOYMENT_GUIDE.md for deploy steps.

Operational notes:
- When deployed publicly, LLM provider API keys come from Streamlit
  Cloud secrets; the multi-provider rotation in ``llm_backends/``
  picks a free-tier provider first (Gemini / Groq), so the public
  surface does not require a paid Anthropic key.
- Privacy: this deployment exposes the form UI to anyone with the
  URL. Per PRIVACY_POLICY.md, users consent on first prediction
  submission; data is persisted to the local SQLite store
  (see DEPLOYMENT_GUIDE.md §5 for the SQLite sync/download strategy).
"""

from __future__ import annotations

# Re-export the main entrypoint
from app import main

if __name__ == "__main__":
    main()
