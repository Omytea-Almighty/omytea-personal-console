"""NL → BeliefProgram compiler.

OmyteaCompiler-LLM (minimum version) — provider-agnostic.

The compiler takes structured user input (form data) + a scenario manifest,
and returns a BeliefProgram dict that downstream Omytea operators can
consume. Compilation is delegated to a pluggable LLM backend (see
`llm_backends/` package). Default server-side behavior selects from a
priority chain of free-tier providers (Gemini Flash, Groq Llama, etc.)
to avoid single-vendor lock-in.

Mock mode (set OMYTEA_CONSOLE_MOCK=1) returns a deterministic stub for
offline testing.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from llm_backends import (
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    get_default_backend,
)


SYSTEM_PROMPT_BRANCH_DRILLDOWN = """You are the Omytea Branch Drill-Down LLM.

Given (a) a single branch the user has chosen to explore deeper and
(b) the full BeliefProgram context (other branches, decision options,
recommended evidence), emit a strict JSON drill-down with this shape:

{
  "branch_label": "<echoed back>",
  "deeper_narrative": [
    "<paragraph 1 — what this future feels like in week 1 to month 1>",
    "<paragraph 2 — what it looks like at the time-horizon midpoint>",
    "<paragraph 3 — what life looks like in steady state past the horizon>"
  ],
  "concrete_actions_this_week": [
    {
      "action": "<imperative, specific, doable in <7 days>",
      "expected_effect": "<one sentence on how this shifts probability toward / away from this branch>",
      "effort": "low" | "medium" | "high"
    },
    ...  // 3-5 actions
  ],
  "conditional_dependencies": [
    {
      "condition": "<what must go right>",
      "current_state": "<short read on whether it looks likely now>",
      "impact_if_fails": "<short read on the alternate branch we'd shift toward>"
    },
    ...  // 2-4 dependencies
  ],
  "sensitivity_preview": [
    {
      "evidence_label": "<from the original recommended_evidence list>",
      "if_positive_delta_p": <float pp — shift toward this branch if signal>,
      "if_negative_delta_p": <float pp — shift away if anti-signal>
    },
    ...  // 1-3 entries
  ]
}

Strict requirements:
- The chosen branch may be wishful / realistic / worst — match the tone:
  for wishful, focus on "what to do this week to make this more likely";
  for worst, focus on "what to do this week to prevent this";
  for realistic, balance both.
- Concrete actions MUST be doable inside one week. No vague advice
  ("network more"); make it specific ("schedule a 30-min call with
  X to ask about Y by Friday").
- Use only branches + evidence labels that already appear in the
  provided BeliefProgram — do NOT invent new branches or evidence.
- Use neutral, evidence-oriented language. Never use: "fortune",
  "destiny", "will happen", "predict", "horoscope", "oracle", "tarot".
- Output ONLY the JSON object, no prose before or after.
"""


SYSTEM_PROMPT_COMPILER = """You are the Omytea Compiler — a natural-language to BeliefProgram translator.

Your task: given a structured user decision input and a scenario manifest,
emit a strict JSON BeliefProgram with the following shape:

{
  "scenario": "<scenario_name>",
  "decision_options": ["option_a", "option_b", ...],
  "branches": [
    {
      "label": "<short branch label>",
      "branch_type": "wishful" | "worst" | "realistic",
      "narrative": "<one-or-two-sentence description, emotionally vivid + specific to user>",
      "probability_prior": <float in [0,1]>,
      "key_uncertainty_driver": "<one phrase>",
      "depends_on_decision": "<option_label or null>"
    },
    ...  // 6-8 branches total
  ],
  "joint_offdiag": [
    {
      "branch_a": "<label_a>",
      "branch_b": "<label_b>",
      "coherence_strength": <float in [-1, 1]>,
      "rationale": "<one sentence>"
    },
    ...  // pairs of branches whose outcomes are correlated
  ],
  "recommended_evidence": [
    {
      "evidence_label": "<what to find out>",
      "expected_delta_p": <float in [0, 100] — percentage points>,
      "target_branch": "<branch_label or null>",
      "rationale": "<one sentence: WHY collecting this would shift probabilities>"
    },
    ...
  ]
}

Strict requirements:
- Total branches: 6-8.
- MUST include EXACTLY ONE branch with `branch_type: "wishful"` — the
  best-case-plausible scenario for the user. This branch should be
  EMOTIONALLY VIVID and SPECIFIC to the user's actual situation (not
  generic "everything works"). It captures the "hoped-for future" the
  user can anchor on. Probability typically 3-10% (low but non-zero).
- MUST include EXACTLY ONE branch with `branch_type: "worst"` — the
  worst-plausible-case scenario. Plausibly catastrophic without being
  doomer; references specific failure modes from the user's context.
  Probability typically 3-10%.
- The other 4-6 branches have `branch_type: "realistic"` and span the
  middle of the probability distribution (each typically 5-35%).
- All probability_prior values across all branches MUST sum to 1.0 ± 1e-3.
- coherence_strength: positive = correlated (likely co-occur), negative
  = anti-correlated.
- The wishful branch is what makes the user want to drill down + engage;
  the worst branch is what makes them want to take preventive action.
  Both must feel personal, not template.
- Never emit numeric "predictions" of dates / amounts. Only branches +
  probabilities + key uncertainty drivers.
- Use neutral, evidence-oriented language. NEVER use: "fortune",
  "destiny", "will happen", "predict", "horoscope", "oracle", "tarot",
  or related terms.
- `expected_delta_p`: ABSOLUTE expected change, in percentage points,
  of the most-likely branch's probability if this evidence is collected.
  Range [0, 100] but typically 5-30. Use percentage points (e.g. 12)
  NOT 0-1 fractions (NOT 0.12). This is what makes the number directly
  interpretable as "collecting this would shift the most-likely
  branch by ±12 percentage points".
- `target_branch`: the label of the branch most affected by this evidence
  (or null if the evidence redistributes mass broadly).
- `rationale`: one sentence explaining the mechanism — what specifically
  about this evidence shifts probability where.
- Sort recommended_evidence by descending expected_delta_p.
- Output ONLY the JSON object, no prose before or after.

The output will be parsed by the Omytea WaveFunction constructor."""


@dataclass(frozen=True, slots=True)
class CompiledBeliefProgram:
    """Strongly-typed wrapper over the JSON the LLM returns."""

    raw: dict[str, Any]

    @property
    def scenario(self) -> str:
        return str(self.raw.get("scenario", "unknown"))

    @property
    def branches(self) -> list[dict[str, Any]]:
        return list(self.raw.get("branches", []))

    @property
    def joint_offdiag(self) -> list[dict[str, Any]]:
        return list(self.raw.get("joint_offdiag", []))

    @property
    def recommended_evidence(self) -> list[dict[str, Any]]:
        return list(self.raw.get("recommended_evidence", []))

    @property
    def decision_options(self) -> list[str]:
        return list(self.raw.get("decision_options", []))


def _mock_compile(user_input: dict[str, Any], scenario: str) -> dict[str, Any]:
    """Deterministic stub for offline testing. Returns realistic-looking
    BeliefProgram for the career_decision scenario, NOW WITH wishful +
    worst anchor branches per v4.16 P1.
    """
    return {
        "scenario": scenario,
        "decision_options": ["accept_offer", "counter_offer", "stay_current"],
        "branches": [
            {
                "label": "everything_aligns_at_new_role",
                "branch_type": "wishful",
                "narrative": "Accept the offer, team culture is exceptional, project is energizing, manager actively invests in your growth. Within 4 months you're shipping work you're proud of, the comp uplift improves life logistics, and you wake up most mornings looking forward to the day. This is the future you'd pick if you could.",
                "probability_prior": 0.06,
                "key_uncertainty_driver": "team_culture_actual_vs_pitch",
                "depends_on_decision": "accept_offer",
            },
            {
                "label": "thrive_at_new_role",
                "branch_type": "realistic",
                "narrative": "Accept the offer and the role mostly suits you; growth + impact within 6 months, normal team friction but workable.",
                "probability_prior": 0.26,
                "key_uncertainty_driver": "team_culture_fit",
                "depends_on_decision": "accept_offer",
            },
            {
                "label": "burnout_within_3mo",
                "branch_type": "realistic",
                "narrative": "Accept the offer but workload and team dynamics lead to burnout symptoms within 3 months.",
                "probability_prior": 0.12,
                "key_uncertainty_driver": "workload_intensity",
                "depends_on_decision": "accept_offer",
            },
            {
                "label": "leave_anyway_in_6mo",
                "branch_type": "realistic",
                "narrative": "Stay at current job, but underlying dissatisfaction persists; you leave within 6 months for a different opportunity.",
                "probability_prior": 0.20,
                "key_uncertainty_driver": "current_role_growth_trajectory",
                "depends_on_decision": "stay_current",
            },
            {
                "label": "counter_offer_accepted_root_unsolved",
                "branch_type": "realistic",
                "narrative": "Successful counter-offer, but the original sources of dissatisfaction (manager / scope / pace) remain.",
                "probability_prior": 0.16,
                "key_uncertainty_driver": "root_cause_of_dissatisfaction",
                "depends_on_decision": "counter_offer",
            },
            {
                "label": "stay_and_thrive_after_renegotiation",
                "branch_type": "realistic",
                "narrative": "Counter-offer or current-role renegotiation succeeds and underlying issues actually improve.",
                "probability_prior": 0.16,
                "key_uncertainty_driver": "manager_willingness_to_change_role_design",
                "depends_on_decision": "stay_current",
            },
            {
                "label": "compounding_failure_cycle",
                "branch_type": "worst",
                "narrative": "Whatever you pick goes wrong in a way that compounds: new role doesn't materialize as pitched AND your relationship with current employer sours from the counter-offer conversation, leaving you with worse options than today. Career trajectory stalls 12-18 months. This is the future to actively avoid.",
                "probability_prior": 0.04,
                "key_uncertainty_driver": "burning_bridges_during_negotiation",
                "depends_on_decision": None,
            },
        ],
        "joint_offdiag": [
            {
                "branch_a": "burnout_within_3mo",
                "branch_b": "leave_anyway_in_6mo",
                "coherence_strength": 0.55,
                "rationale": "Both indicate underlying overcommitment pattern not tied to specific job.",
            },
            {
                "branch_a": "thrive_at_new_role",
                "branch_b": "stay_and_thrive_after_renegotiation",
                "coherence_strength": -0.45,
                "rationale": "Mutually exclusive paths; high prior on one indicates low prior on the other.",
            },
            {
                "branch_a": "counter_offer_accepted_root_unsolved",
                "branch_b": "leave_anyway_in_6mo",
                "coherence_strength": 0.40,
                "rationale": "Counter-offer without addressing root cause typically resolves into eventual departure.",
            },
        ],
        "recommended_evidence": [
            {
                "evidence_label": "diagnostic_call_with_potential_manager",
                "expected_delta_p": 18.0,
                "target_branch": "thrive_at_new_role",
                "rationale": "A 45-min call exposing real management style + team dynamics moves probability mass between the wishful + burnout branches sharply.",
            },
            {
                "evidence_label": "honest_conversation_with_current_manager_on_role_design",
                "expected_delta_p": 14.0,
                "target_branch": "stay_and_thrive_after_renegotiation",
                "rationale": "Tests whether root-cause unsolved branch versus genuine improvement is the more likely path on staying.",
            },
            {
                "evidence_label": "review_offer_team_glassdoor_or_blind",
                "expected_delta_p": 8.0,
                "target_branch": None,
                "rationale": "Broadly informs but limited signal-to-noise; modest mass redistribution across new-role branches.",
            },
        ],
    }


def compile_belief_program(
    user_input: dict[str, Any],
    scenario: str = "career_decision",
    max_tokens: int = 4096,
    backend: LLMBackend | None = None,
) -> CompiledBeliefProgram:
    """Compile user input → BeliefProgram via configured LLM backend (or mock).

    Args:
        user_input: dict of form-data fields from the Streamlit UI.
        scenario: scenario manifest name (e.g., "career_decision").
        max_tokens: hard cap on response size.
        backend: explicit backend to use; if None, picks from default
            priority chain (Gemini Flash → Groq Llama → Anthropic if
            user-key set → mock). Env var OMYTEA_LLM_BACKEND can override.

    Returns:
        CompiledBeliefProgram with .scenario / .branches / .joint_offdiag / etc.

    Raises:
        RuntimeError if all backends in the rotation fail.
    """
    if os.environ.get("OMYTEA_CONSOLE_MOCK") == "1":
        return CompiledBeliefProgram(raw=_mock_compile(user_input, scenario))

    if backend is None:
        backend = get_default_backend()

    user_message = (
        f"Scenario: {scenario}\n\n"
        f"User input (form data):\n```json\n"
        f"{json.dumps(user_input, ensure_ascii=False, indent=2)}\n```\n\n"
        f"Compile the above into a BeliefProgram following the JSON schema "
        f"in your instructions. Output ONLY the JSON object."
    )

    request = LLMRequest(
        system_prompt=SYSTEM_PROMPT_COMPILER,
        user_message=user_message,
        max_tokens=max_tokens,
    )

    try:
        response = backend.compile(request)
    except LLMBackendError as exc:
        raise RuntimeError(
            f"BeliefProgram compilation failed ({exc.provider}): {exc}. "
            f"If you have no API keys configured, set OMYTEA_CONSOLE_MOCK=1 "
            f"to use the offline mock backend."
        ) from exc

    return CompiledBeliefProgram(raw=response.program_json)


# ============================================================
# v4.16 P2 — Branch drill-down LLM call
# ============================================================


def _mock_branch_drilldown(
    branch_label: str,
    branch_type: str,
) -> dict[str, Any]:
    """Deterministic mock drill-down. Used for OMYTEA_CONSOLE_MOCK=1
    and as the canned fallback when no LLM backend is configured."""
    tone_intro = {
        "wishful": "If everything aligns toward this future,",
        "worst": "If the trajectory bends toward this worst case,",
        "realistic": "In this realistic future,",
    }.get(branch_type, "In this future,")

    return {
        "branch_label": branch_label,
        "deeper_narrative": [
            f"{tone_intro} the first 2-4 weeks bring concrete signals — "
            "specific conversations, calendar shifts, and small wins or "
            "warning signs you can name. You notice them because you're "
            "looking for them.",
            f"By the middle of your time horizon, the pattern has compounded. "
            "Routines have shifted. Your relationships with the relevant "
            "people (manager, peers, family) have visibly evolved one way "
            "or the other.",
            f"At horizon end and beyond, this future is no longer one of "
            "many possibilities — it has become the lived reality. The "
            "key question is whether you can look back and recognize the "
            "decision points where it became inevitable.",
        ],
        "concrete_actions_this_week": [
            {
                "action": (
                    "Schedule a 30-min call with one person whose perspective "
                    "would most de-risk this branch (a current team member "
                    "from the new role, an honest mentor, or someone who "
                    "made the same choice 2 years ago)."
                ),
                "expected_effect": (
                    "Shifts probability of this branch up if their feedback "
                    "is positive; sharply down if they raise red flags."
                ),
                "effort": "low",
            },
            {
                "action": (
                    "Write down 3 things you'd need to be true for this "
                    "branch to play out, then check current evidence for "
                    "each (yes / no / unsure)."
                ),
                "expected_effect": (
                    "Surfaces which dependencies are actually load-bearing "
                    "vs which you'd assumed without checking."
                ),
                "effort": "low",
            },
            {
                "action": (
                    "Identify one specific reversible action this week that, "
                    "if taken, increases the probability of this branch by "
                    "≥ 5 percentage points without burning bridges."
                ),
                "expected_effect": (
                    "Converts abstract preference into a testable bet — and "
                    "tests your true commitment to this future."
                ),
                "effort": "medium",
            },
        ],
        "conditional_dependencies": [
            {
                "condition": (
                    "The most-likely failure mode named in the original "
                    "branch's key_uncertainty_driver doesn't materialize."
                ),
                "current_state": (
                    "Unknown — this is exactly the diagnostic you should "
                    "run with the call recommended above."
                ),
                "impact_if_fails": (
                    "Probability mass shifts toward the adjacent realistic "
                    "branch or the worst-case anchor, depending on the "
                    "failure mode."
                ),
            },
            {
                "condition": (
                    "The decision option this branch depends on (if any) "
                    "is actually executable on your timeline."
                ),
                "current_state": (
                    "Read off the form input + your admin / commitments "
                    "calendar."
                ),
                "impact_if_fails": (
                    "Branch probability drops toward zero; the remaining "
                    "mass redistributes across decision-independent branches."
                ),
            },
        ],
        "sensitivity_preview": [
            {
                "evidence_label": "diagnostic_call_with_potential_manager",
                "if_positive_delta_p": 12.0,
                "if_negative_delta_p": -18.0,
            },
            {
                "evidence_label": "honest_conversation_with_current_manager_on_role_design",
                "if_positive_delta_p": 8.0,
                "if_negative_delta_p": -10.0,
            },
        ],
    }


def compile_branch_drilldown(
    branch_label: str,
    branch_type: str,
    full_belief_program: dict[str, Any],
    user_input: dict[str, Any],
    scenario: str = "career_decision",
    max_tokens: int = 3072,
    backend: LLMBackend | None = None,
) -> dict[str, Any]:
    """v4.16 P2 — drill down on a single branch the user is most
    interested in.

    Args:
      branch_label: which branch in the BeliefProgram to expand.
      branch_type: "wishful" | "worst" | "realistic" — tunes tone.
      full_belief_program: the complete BeliefProgram dict (other
        branches, decisions, recommended evidence) — the LLM uses
        this for context but should NOT invent new branches.
      user_input: original form data — gives context about the
        user's situation.
      scenario: scenario name.
      max_tokens: hard cap.
      backend: explicit backend override; defaults to
        ``get_default_backend()``.

    Returns:
      Dict matching the SYSTEM_PROMPT_BRANCH_DRILLDOWN output shape.

    Raises:
      RuntimeError if all backends fail.

    Mock mode (OMYTEA_CONSOLE_MOCK=1) returns a deterministic stub.
    """
    if os.environ.get("OMYTEA_CONSOLE_MOCK") == "1":
        return _mock_branch_drilldown(branch_label, branch_type)

    if backend is None:
        backend = get_default_backend()

    user_message = (
        f"Scenario: {scenario}\n\n"
        f"Branch to drill into: {branch_label} (type: {branch_type})\n\n"
        f"Full BeliefProgram context:\n```json\n"
        f"{json.dumps(full_belief_program, ensure_ascii=False, indent=2)}\n"
        f"```\n\n"
        f"User input (form data):\n```json\n"
        f"{json.dumps(user_input, ensure_ascii=False, indent=2)}\n```\n\n"
        f"Produce the drill-down JSON following the schema in your "
        f"instructions. Output ONLY the JSON object."
    )

    request = LLMRequest(
        system_prompt=SYSTEM_PROMPT_BRANCH_DRILLDOWN,
        user_message=user_message,
        max_tokens=max_tokens,
    )

    try:
        response = backend.compile(request)
    except LLMBackendError as exc:
        raise RuntimeError(
            f"Branch drill-down failed ({exc.provider}): {exc}. "
            f"Set OMYTEA_CONSOLE_MOCK=1 to use the offline mock."
        ) from exc

    return response.program_json
