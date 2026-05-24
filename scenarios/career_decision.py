"""Career decision scenario — v4.15 MVP scenario #1.

Defines the form-field schema + scenario metadata. The actual
compilation happens in compiler.py via the Claude API; this module
only describes what the UI should collect.
"""

from __future__ import annotations

from dataclasses import dataclass


SCENARIO_NAME = "career_decision"
DESCRIPTION = (
    "Probabilistic decision support for career-related decisions: "
    "evaluating job offers, considering role transitions, weighing "
    "stay-vs-leave at current position. Produces 3-5 future scenarios "
    "with calibrated probabilities + key uncertainty drivers + "
    "recommended evidence to collect."
)


@dataclass(frozen=True, slots=True)
class InputField:
    """Description of one form field shown in the Streamlit UI.

    `placeholder` shows greyed-out example text inside an empty input.
    `example_value` is the realistic prefill the "Try with example
    data" button writes — lets a brand-new visitor see the prediction
    flow in one click with zero typing.
    """

    key: str
    label: str
    field_type: str  # "text" | "textarea" | "select" | "number"
    hint: str = ""
    required: bool = True
    options: tuple[str, ...] = ()  # for "select"
    placeholder: str = ""
    example_value: str = ""


INPUT_FIELDS: list[InputField] = [
    # ⚠️ Field render ORDER is governed by `_COMPOSER_CORE_FIELDS` in
    # app.py, not by this list. ``decision_options`` renders FIRST in the
    # composer (XUANXUE_REDESIGN iteration #1: "the decision is the
    # hero"). Order here is preserved historical for compiler stability;
    # do not rely on it for UI order.
    InputField(
        key="current_role",
        label="A little about you",
        field_type="textarea",
        hint=(
            "Job, study, freelance, in-transition — anything. One or two "
            "sentences is enough."
        ),
        placeholder=(
            "e.g., final-year CS Master's student in the US, ML focus, "
            "looking for full-time roles"
        ),
        example_value=(
            "Final-year US-based CS Master's student focused on ML; "
            "previously worked 2 years as an algorithms engineer at an "
            "AI startup; currently job-hunting while also maintaining a "
            "small open-source side project."
        ),
    ),
    InputField(
        key="decision_options",
        label="What decision are you weighing?",
        field_type="textarea",
        hint=(
            "List 3-5 concrete choices, one per line — comparing offers, "
            "stay-vs-leave, returning home vs. abroad, industry vs. PhD, "
            "join-existing vs. start-something."
        ),
        placeholder=(
            "Take the ML engineer offer at Anthropic\n"
            "Join a Series-A startup back home as tech lead\n"
            "Go solo on the open-source project for 6 months and reassess"
        ),
        example_value=(
            "- Accept the ML engineer offer at Anthropic (Bay Area)\n"
            "- Join a Series-A startup back home as tech lead\n"
            "- Continue solo on the open-source project for 6 months and "
            "reassess"
        ),
    ),
    InputField(
        key="why_considering_change",
        label="What's actually driving you? (the more honest, the more accurate)",
        field_type="textarea",
        hint=(
            "Pay / growth / team dynamics / life balance / creative pull / "
            "family proximity / visa / external opportunity — the real driver, "
            "not the polished one."
        ),
        placeholder=(
            "e.g., Bay-area cost of living plus wanting to be closer to "
            "family, weighed against worry about long-hours culture and "
            "career ceiling back home"
        ),
        example_value=(
            "Bay-area cost of living + missing family pull me toward "
            "returning home. But I worry about long-hours culture and "
            "the career ceiling there. Going solo on the open-source "
            "project gives me autonomy but creates real cash-flow "
            "pressure and risks missing the current AI window."
        ),
    ),
    InputField(
        key="time_horizon",
        label="When will you come back to score this?",
        field_type="select",
        options=("3 months", "6 months", "12 months", "24 months"),
        hint=(
            "At that point return to the Measurement update tab and "
            "score each branch by how much it actually materialized. "
            "The system uses your scores to compute calibration "
            "(Brier / log-loss) on your forecast."
        ),
    ),
    InputField(
        key="constraints",
        label="Hard constraints (optional)",
        field_type="textarea",
        required=False,
        hint=(
            "Money floor, family location, visa, health, legal — anything "
            "that materially fences the choice. Optional but more "
            "specificity improves output quality."
        ),
        placeholder=(
            "e.g., F-1 OPT has 24 months left; monthly rent + loans = "
            "$4500; family hopes I return within 2 years but isn't "
            "demanding it"
        ),
        example_value=(
            "F-1 OPT has 24 months left; monthly rent + loans about "
            "$4500; family hopes I return within 2 years but isn't "
            "demanding it."
        ),
    ),
    InputField(
        key="key_unknowns",
        label="Things you know you don't know — but that matter (optional)",
        field_type="textarea",
        required=False,
        hint=(
            "e.g., team culture at a specific company, policy direction "
            "in a region, whether a 12-month AI window will close. These "
            "become the system's 'evidence worth collecting' list in the "
            "output."
        ),
        placeholder=(
            "e.g., real working hours at Anthropic ML team; 12-month "
            "survival probability of the Series-A startup; whether my "
            "side project can reach $3k/month sustainable revenue"
        ),
        example_value=(
            "Real working hours at the Anthropic ML team; 12-month "
            "survival probability of the Series-A startup; whether my "
            "side project can reach $3k/month sustainable revenue in 12 "
            "months."
        ),
    ),
    InputField(
        key="user_id",
        label="Pick a handle",
        field_type="text",
        hint=(
            "Any string. Used to look up this prediction later when you "
            "come back to score what actually happened. No registration, "
            "no PII collected."
        ),
        placeholder="e.g., tester-alice",
        example_value="demo-tester",
    ),
]


def validate_input(form_data: dict) -> tuple[bool, str]:
    """Check that all required fields are filled.

    Returns (is_valid, error_message). Empty error_message when valid.
    """
    for field in INPUT_FIELDS:
        if field.required:
            v = form_data.get(field.key, "").strip()
            if not v:
                return False, f"Missing required field: {field.label}"
    return True, ""
