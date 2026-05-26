"""Iter #25 + 26 — regression tests for the per-branch confidence tier
logic in `_render_story_card`.

The actual tier-selection is a pure-logic block inside the rendering
function — branch count of recommended_evidence items targeting this
branch's label decides which i18n key (well_calibrated /
single_source / soft_estimate) gets shown in the meta line.

These tests exercise that tier selection in isolation (without
running Streamlit) by extracting the conditional inline:
the live-verified contract from iter 27's screenshot is what
this test locks.
"""

from __future__ import annotations


def _select_confidence_tier_key(
    branch_label: str,
    recommended_evidence: list[dict],
) -> str:
    """Mirror the conditional from _render_story_card iter 25+26.

    This is the same selection logic that lives in app.py at the
    iter 25 patch site; mirrored here to test independent of
    Streamlit's render machinery. If iter 25 ever refactors the
    selection out into a named function, this helper should
    delegate to it and the assertions move accordingly.
    """
    n_for_branch = 0
    if recommended_evidence:
        n_for_branch = sum(
            1 for rec in recommended_evidence
            if rec.get("target_branch") == branch_label
        )
    if n_for_branch >= 2:
        return "result.confidence_well_calibrated"
    if n_for_branch == 1:
        return "result.confidence_single_source"
    return "result.confidence_soft_estimate"


def test_zero_evidence_for_branch_yields_soft_estimate() -> None:
    """A branch with no recommended_evidence items targeting it
    falls into the "soft estimate" bucket — its probability comes
    from the base scenario distribution, no specific lever named.

    Live-verified iter 27 on the everything_aligns_at_new_role
    branch (6% wishful, "soft estimate" rendered correctly).
    """
    key = _select_confidence_tier_key(
        branch_label="everything_aligns_at_new_role",
        recommended_evidence=[
            # Other branches' evidence; none target this one.
            {
                "evidence_label": "review_offer_team",
                "expected_delta_p": 8.0,
                "target_branch": "stay_and_thrive_after_renegotiation",
                "rationale": "",
            },
        ],
    )
    assert key == "result.confidence_soft_estimate"


def test_zero_evidence_globally_yields_soft_estimate() -> None:
    """When recommended_evidence is None or empty, every branch
    falls into "soft estimate" — there's no signal to bucket on."""
    for evidence in (None, [], [{"target_branch": "other"}]):
        key = _select_confidence_tier_key(
            branch_label="my_branch",
            recommended_evidence=evidence,
        )
        assert key == "result.confidence_soft_estimate"


def test_one_evidence_for_branch_yields_single_source() -> None:
    """Exactly one evidence item targeting this branch → single-source.
    Indicates one identified lever, but only one — confidence is
    qualitative-medium."""
    key = _select_confidence_tier_key(
        branch_label="thrive_at_new_role",
        recommended_evidence=[
            {
                "evidence_label": "check_team_glassdoor",
                "expected_delta_p": 12.0,
                "target_branch": "thrive_at_new_role",
                "rationale": "",
            },
            {
                "evidence_label": "review_comp_band",
                "expected_delta_p": 5.0,
                "target_branch": "another_branch",
                "rationale": "",
            },
        ],
    )
    assert key == "result.confidence_single_source"


def test_two_or_more_evidence_yields_well_calibrated() -> None:
    """≥2 evidence items targeting this branch → well-calibrated.
    Multiple identified levers means we can name several ways the
    probability could move."""
    key = _select_confidence_tier_key(
        branch_label="stay_and_thrive",
        recommended_evidence=[
            {
                "evidence_label": "ev1",
                "target_branch": "stay_and_thrive",
            },
            {
                "evidence_label": "ev2",
                "target_branch": "stay_and_thrive",
            },
            {
                "evidence_label": "ev3",
                "target_branch": "stay_and_thrive",
            },
        ],
    )
    assert key == "result.confidence_well_calibrated"


def test_tier_keys_resolve_through_i18n() -> None:
    """The three i18n keys must resolve to non-empty strings in EN.
    This catches accidental key drift between app.py call sites and
    _i18n.py entries. Live-verified iter 27: the EN string "soft
    estimate" rendered correctly in italic meta-line."""
    from _i18n import T

    for key in (
        "result.confidence_well_calibrated",
        "result.confidence_single_source",
        "result.confidence_soft_estimate",
    ):
        value = T(key)
        assert value, f"i18n key {key} resolved to empty"
        # Sanity: a missing key would fall back to the literal key
        # string per _i18n's T() contract. Make sure we got a real
        # translation, not the key itself.
        assert value != key, f"i18n key {key} returned itself"


def test_tier_keys_have_all_four_locales() -> None:
    """The iter 26 i18n shipped × 4 locales. Lock the contract so a
    future refactor can't drop a locale silently."""
    from _i18n import TRANSLATIONS, LANG_EN, LANG_ZH, LANG_ES, LANG_FR

    for key in (
        "result.confidence_well_calibrated",
        "result.confidence_single_source",
        "result.confidence_soft_estimate",
    ):
        entry = TRANSLATIONS.get(key, {})
        for lang in (LANG_EN, LANG_ZH, LANG_ES, LANG_FR):
            assert lang in entry, (
                f"i18n key {key} missing locale {lang}"
            )
            assert entry[lang], (
                f"i18n key {key} has empty value for locale {lang}"
            )
