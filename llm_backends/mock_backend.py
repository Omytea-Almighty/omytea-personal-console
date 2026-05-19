"""MockBackend — offline / CI / development backend.

Returns a deterministic stub BeliefProgram for the career_decision
scenario. Includes wishful + worst anchor branches per the v4.16
anchor design. Used when OMYTEA_CONSOLE_MOCK=1 or as the
zero-dependency fallback when no LLM provider is configured.

Sanitization note: this file is part of the public deployable
surface. Keep references generic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .base import (
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    LLMResponse,
    validate_belief_program_schema,
)


_MOCK_BELIEF_PROGRAM = {
    "scenario": "career_decision",
    "decision_options": ["accept_offer", "counter_offer", "stay_current"],
    "branches": [
        {
            "label": "everything_aligns_at_new_role",
            "branch_type": "wishful",
            "narrative": (
                "Accept the offer, team culture is exceptional, project is "
                "energizing, manager actively invests in your growth. Within "
                "4 months you're shipping work you're proud of, the comp "
                "uplift improves life logistics, and you wake up most "
                "mornings looking forward to the day. This is the future "
                "you'd pick if you could."
            ),
            "probability_prior": 0.06,
            "key_uncertainty_driver": "team_culture_actual_vs_pitch",
            "depends_on_decision": "accept_offer",
        },
        {
            "label": "thrive_at_new_role",
            "branch_type": "realistic",
            "narrative": (
                "Accept the offer and the role mostly suits you; growth + "
                "impact within 6 months, normal team friction but workable."
            ),
            "probability_prior": 0.26,
            "key_uncertainty_driver": "team_culture_fit",
            "depends_on_decision": "accept_offer",
        },
        {
            "label": "burnout_within_3mo",
            "branch_type": "realistic",
            "narrative": (
                "Accept the offer but workload and team dynamics lead to "
                "burnout symptoms within 3 months."
            ),
            "probability_prior": 0.12,
            "key_uncertainty_driver": "workload_intensity",
            "depends_on_decision": "accept_offer",
        },
        {
            "label": "leave_anyway_in_6mo",
            "branch_type": "realistic",
            "narrative": (
                "Stay at current job, but underlying dissatisfaction persists; "
                "you leave within 6 months for a different opportunity."
            ),
            "probability_prior": 0.20,
            "key_uncertainty_driver": "current_role_growth_trajectory",
            "depends_on_decision": "stay_current",
        },
        {
            "label": "counter_offer_accepted_root_unsolved",
            "branch_type": "realistic",
            "narrative": (
                "Successful counter-offer, but the original sources of "
                "dissatisfaction (manager / scope / pace) remain."
            ),
            "probability_prior": 0.16,
            "key_uncertainty_driver": "root_cause_of_dissatisfaction",
            "depends_on_decision": "counter_offer",
        },
        {
            "label": "stay_and_thrive_after_renegotiation",
            "branch_type": "realistic",
            "narrative": (
                "Counter-offer or current-role renegotiation succeeds and "
                "underlying issues actually improve."
            ),
            "probability_prior": 0.16,
            "key_uncertainty_driver": "manager_willingness_to_change_role_design",
            "depends_on_decision": "stay_current",
        },
        {
            "label": "compounding_failure_cycle",
            "branch_type": "worst",
            "narrative": (
                "Whatever you pick goes wrong in a way that compounds: new "
                "role doesn't materialize as pitched AND your relationship "
                "with current employer sours from the counter-offer "
                "conversation, leaving you with worse options than today. "
                "Career trajectory stalls 12-18 months. This is the future "
                "to actively avoid."
            ),
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
            "rationale": (
                "Both indicate underlying overcommitment pattern not tied "
                "to specific job."
            ),
        },
        {
            "branch_a": "thrive_at_new_role",
            "branch_b": "stay_and_thrive_after_renegotiation",
            "coherence_strength": -0.45,
            "rationale": "Mutually exclusive paths.",
        },
        {
            "branch_a": "counter_offer_accepted_root_unsolved",
            "branch_b": "leave_anyway_in_6mo",
            "coherence_strength": 0.40,
            "rationale": (
                "Counter-offer without addressing root cause typically "
                "resolves into eventual departure."
            ),
        },
    ],
    "recommended_evidence": [
        {
            "evidence_label": "diagnostic_call_with_potential_manager",
            "expected_delta_p": 18.0,
            "target_branch": "thrive_at_new_role",
            "rationale": (
                "A 45-min call exposing real management style + team "
                "dynamics moves probability mass between the wishful + "
                "burnout branches sharply."
            ),
        },
        {
            "evidence_label": "honest_conversation_with_current_manager_on_role_design",
            "expected_delta_p": 14.0,
            "target_branch": "stay_and_thrive_after_renegotiation",
            "rationale": (
                "Tests whether root-cause unsolved branch versus genuine "
                "improvement is the more likely path on staying."
            ),
        },
        {
            "evidence_label": "review_offer_team_glassdoor_or_blind",
            "expected_delta_p": 8.0,
            "target_branch": None,
            "rationale": (
                "Broadly informs but limited signal-to-noise; modest "
                "mass redistribution across new-role branches."
            ),
        },
    ],
}


@dataclass(frozen=True, slots=True)
class MockBackend(LLMBackend):
    """Deterministic stub that returns a canned BeliefProgram.

    Used for CI / offline development / when no other provider is
    configured. Always succeeds (no API calls; cannot fail).
    """

    provider_name: str = "mock"
    default_model: str = "stub-v1"

    def compile(self, request: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        # Validate the canned response itself (catches schema drift if we
        # update _MOCK_BELIEF_PROGRAM later)
        validate_belief_program_schema(_MOCK_BELIEF_PROGRAM)
        return LLMResponse(
            program_json=dict(_MOCK_BELIEF_PROGRAM),  # defensive copy
            provider=self.provider_name,
            model=self.default_model,
            latency_seconds=time.perf_counter() - t0,
            prompt_tokens=0,
            completion_tokens=0,
            raw_response="<mock>",
        )

    def is_available(self) -> bool:
        return True
