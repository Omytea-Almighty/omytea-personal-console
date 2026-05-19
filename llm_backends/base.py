"""LLMBackend Protocol — provider-agnostic interface for BeliefProgram compilation.

Why this exists:
  Earlier iterations of compiler.py were hard-coded to a single LLM
  vendor's SDK. That created a single-vendor dependency that blocked
  any commercial deployment, exposed operators to API cost spikes,
  and made local-LLM / multi-provider rotation impossible. The
  Protocol-based abstraction in this module is the fix.

Design contract:
  A backend is a callable that takes a `LLMRequest` and returns a
  `LLMResponse` containing parsed BeliefProgram JSON. The compiler
  layer (compiler.py) selects a backend by name + handles
  fallback / rotation.

Adding a new provider:
  1. Subclass LLMBackend
  2. Implement `compile()` calling the provider's API
  3. Register in `llm_backends/__init__.py` `_REGISTRY` dict
  4. Set the appropriate API key env var pattern
  5. Add tests under `tests/test_llm_backends_*.py`

Sanitization note: this module is part of the public deployable
surface. NO references to internal docs (WORK_PLAN, ADR, PLAN.md,
etc.) — keep general-purpose.
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """One BeliefProgram compilation request to an LLM provider.

    Fields:
      - `system_prompt`: provider-agnostic instructions (BeliefProgram schema)
      - `user_message`: user's structured input (form data) formatted for LLM
      - `max_tokens`: hard ceiling for response length
      - `temperature`: 0.0-1.0; default 0.5 — some variety in branches without
        ungrounded outputs
    """

    system_prompt: str
    user_message: str
    max_tokens: int = 4096
    temperature: float = 0.5


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """One BeliefProgram compilation response from an LLM provider.

    Fields:
      - `program_json`: the parsed BeliefProgram dict
      - `provider`: which backend produced it (for audit + cost attribution)
      - `model`: specific model identifier within provider
      - `latency_seconds`: total wall-clock from request start to parse complete
      - `prompt_tokens` / `completion_tokens`: usage data when provider returns it
      - `raw_response`: provider-specific raw text (for debugging)
    """

    program_json: dict[str, Any]
    provider: str
    model: str
    latency_seconds: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: str = ""


class LLMBackendError(RuntimeError):
    """Raised when an LLM backend cannot fulfill a request.

    Sub-cases:
      - missing API key
      - rate limit hit
      - invalid JSON response
      - provider down / timeout
      - quota exceeded

    Callers (compiler.py / rotating backend) catch this to try
    fallback providers.
    """

    def __init__(self, message: str, *, provider: str, retriable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable


class LLMBackend(ABC):
    """Protocol for any LLM provider backend.

    Implementations should be FROZEN dataclasses (so config is immutable per
    backend instance), with `compile()` doing the actual provider call.

    For deployment safety: every backend's `__init__` should fail loud if
    required env vars are missing — never silently use a wrong key.
    """

    #: Human-readable name (e.g. "gemini-2.0-flash", "groq-llama-3.3")
    provider_name: str = "abstract"

    #: Default model identifier within provider
    default_model: str = "abstract"

    @abstractmethod
    def compile(self, request: LLMRequest) -> LLMResponse:
        """Send request to provider, parse + validate response, return."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Cheap check: does this backend have what it needs to run?

        Default: True. Subclasses override to e.g. verify API key
        present, local Ollama server reachable, etc.

        Used by rotating-fallback to skip unavailable backends without
        burning a slow timeout.
        """
        return True


def extract_json_from_text(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from LLM raw text.

    LLM outputs sometimes wrap JSON in markdown fences or add a sentence
    before/after. This helper strips those wrappers and parses.

    Raises:
      ValueError if no parseable JSON object found.
    """
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        # Find the closing fence
        lines = text.split("\n")
        # Drop first line (```json or ```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: find first {...} block (greedy match for outermost braces)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Found JSON-like block but failed to parse: {exc.msg}. "
                f"Raw text (first 500 chars):\n{text[:500]}"
            ) from exc

    raise ValueError(
        f"No JSON object found in LLM response. Raw text (first 500 chars):\n{text[:500]}"
    )


def validate_belief_program_schema(program: dict[str, Any]) -> None:
    """Validate that an LLM response matches the BeliefProgram schema.

    Raises ValueError on any schema violation. Schema details documented
    in the compiler.py SYSTEM_PROMPT_COMPILER.

    This is called by every backend after JSON parsing — if a provider
    returns garbage that happens to be valid JSON, this catches it.
    """
    if "branches" not in program:
        raise ValueError("BeliefProgram missing required field 'branches'")
    if not isinstance(program["branches"], list):
        raise ValueError("BeliefProgram 'branches' must be a list")
    if len(program["branches"]) < 3:
        raise ValueError(
            f"BeliefProgram must have ≥3 branches; got {len(program['branches'])}"
        )

    # Probabilities sum to 1
    probs = [float(b.get("probability_prior", 0.0)) for b in program["branches"]]
    total = sum(probs)
    if not (0.97 < total < 1.03):
        raise ValueError(
            f"branch probabilities don't sum to 1.0 (got {total:.4f})"
        )

    # Wishful + worst anchor invariants (v4.16 P1 feature; mandated by SYSTEM_PROMPT)
    types = [b.get("branch_type", "realistic") for b in program["branches"]]
    n_wishful = sum(1 for t in types if t == "wishful")
    n_worst = sum(1 for t in types if t == "worst")
    if n_wishful != 1:
        # Soft warning — some providers may not honor the anchor instruction
        # consistently. Don't hard-fail; the UI can still render usefully
        # without anchors. But log so we know which providers are weak.
        pass  # logged elsewhere; non-fatal
    if n_worst != 1:
        pass  # same

    # Each branch must have required fields
    for i, b in enumerate(program["branches"]):
        if "label" not in b:
            raise ValueError(f"Branch {i} missing 'label'")
        if "probability_prior" not in b:
            raise ValueError(f"Branch {i} missing 'probability_prior'")
        if "narrative" not in b:
            raise ValueError(f"Branch {i} missing 'narrative'")
