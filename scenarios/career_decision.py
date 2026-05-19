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
    """Description of one form field shown in the Streamlit UI."""

    key: str
    label: str
    field_type: str  # "text" | "textarea" | "select" | "number"
    hint: str = ""
    required: bool = True
    options: tuple[str, ...] = ()  # for "select"


INPUT_FIELDS: list[InputField] = [
    InputField(
        key="current_role",
        label="Current role and company (industry / function / level)",
        field_type="textarea",
        hint="E.g., 'Senior ML engineer at a Series-B AI startup, 3rd year, "
        "leading a 4-person team building retrieval pipeline.'",
    ),
    InputField(
        key="decision_options",
        label="Decision options you're considering (one per line)",
        field_type="textarea",
        hint="E.g.,\n- Accept offer at Company B (50% raise, FAANG, IC role)\n"
        "- Counter-offer with current employer\n"
        "- Stay current, push for promotion in 6 months",
    ),
    InputField(
        key="why_considering_change",
        label="What's driving you to consider a change? (be honest)",
        field_type="textarea",
        hint="Compensation / growth / team dynamics / personal life "
        "alignment / burnout / opportunity / external pull. The more "
        "honest, the better the analysis.",
    ),
    InputField(
        key="time_horizon",
        label="Time horizon for the prediction",
        field_type="select",
        options=("3 months", "6 months", "12 months", "24 months"),
        hint="When you'd like to come back and report what actually happened.",
    ),
    InputField(
        key="constraints",
        label="Constraints (financial / family / immigration / health)",
        field_type="textarea",
        required=False,
        hint="Anything that materially constrains the choice — financial "
        "runway, family location, visa status, health conditions. "
        "Optional but improves calibration.",
    ),
    InputField(
        key="key_unknowns",
        label="What you don't know yet but feel matters",
        field_type="textarea",
        required=False,
        hint="E.g., team culture at new place, your real reason for being "
        "unhappy at current job, whether the market will turn. These "
        "become candidate 'evidence to collect' in the output.",
    ),
    InputField(
        key="user_id",
        label="Your handle (for measurement-update tracking)",
        field_type="text",
        hint="Pick any string. Used to look up this prediction 6 weeks "
        "later when you come back to report what actually happened. "
        "No registration / no PII collected.",
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
