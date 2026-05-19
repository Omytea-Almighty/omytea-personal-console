"""Scenario manifests for the Personal Future Console MVP.

Each scenario module exposes:
- INPUT_FIELDS: list of form-input descriptors (label / type / hint)
- SCENARIO_NAME: str matching the compiler scenario tag
- description: brief explanation shown in the UI

The MVP ships only ``career_decision``. Additional manifests
(relationship / health / finance / startup) can be added as separate
modules and registered in ``AVAILABLE_SCENARIOS``.
"""

from scenarios.career_decision import (
    SCENARIO_NAME as CAREER_DECISION_NAME,
    INPUT_FIELDS as CAREER_DECISION_FIELDS,
    DESCRIPTION as CAREER_DECISION_DESCRIPTION,
)

AVAILABLE_SCENARIOS = {
    CAREER_DECISION_NAME: {
        "name": CAREER_DECISION_NAME,
        "description": CAREER_DECISION_DESCRIPTION,
        "input_fields": CAREER_DECISION_FIELDS,
    },
}
