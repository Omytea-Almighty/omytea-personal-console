"""Stage 5 — polish: i18n completeness + stale-copy cleanup
(OMY-V415 / M2 / Acceptance #56).

Stage 5 of the console redesign is polish: every redesign string must
exist in all four UI languages, and the stale Mode-7 hero copy ("pick
the system" — there is no system selector anymore, 八字/占星/易经/塔罗
share one Nye Clock lens) must be gone.

_i18n.py has no Streamlit dependency, so TRANSLATIONS is imported and
checked directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _i18n  # noqa: E402


# --------------------------------------------------------------------
# Every translation key is complete across all four languages
# --------------------------------------------------------------------

def test_every_key_has_all_four_languages() -> None:
    """No key may be missing EN / 中 / ES / FR — a missing language
    silently falls back to the key string, which ships untranslated UI.
    """
    missing: list[str] = []
    for key, entry in _i18n.TRANSLATIONS.items():
        for lang in _i18n.SUPPORTED_LANGS:
            if lang not in entry or not str(entry[lang]).strip():
                missing.append(f"{key}::{lang}")
    assert not missing, f"incomplete translations: {missing}"


def test_no_translation_value_is_the_bare_key() -> None:
    """A value equal to its own key is an un-filled placeholder."""
    offenders = [
        key for key, entry in _i18n.TRANSLATIONS.items()
        if any(str(entry.get(lang, "")) == key
               for lang in _i18n.SUPPORTED_LANGS)
    ]
    assert not offenders, f"placeholder values: {offenders}"


# --------------------------------------------------------------------
# Stale Mode-7 copy is gone
# --------------------------------------------------------------------

def test_trad_hero_subtitle_drops_pick_the_system() -> None:
    """The redesign removed the per-system selector — 八字 / 占星 / 易经
    / 塔罗 are aggregated onto one Nye Clock lens. The old copy "pick
    the system" must no longer appear."""
    sub = _i18n.TRANSLATIONS["trad.hero.subtitle"]
    for lang in _i18n.SUPPORTED_LANGS:
        text = str(sub[lang]).lower()
        assert "pick the system" not in text
        assert "选体系" not in str(sub[lang])


def test_trad_hero_subtitle_mentions_nye_clock() -> None:
    """The new copy frames the lens as the Nye Clock solar system."""
    sub = _i18n.TRANSLATIONS["trad.hero.subtitle"]
    # at least the EN string names the Nye Clock
    assert "nye clock" in str(sub[_i18n.LANG_EN]).lower()


# --------------------------------------------------------------------
# All redesign i18n keys are present (Stages 1-4 surfaces)
# --------------------------------------------------------------------

@pytest.mark.parametrize(
    "key",
    [
        # Stage 1 — history-rail shell
        "nav.new_prediction",
        "nav.history",
        "nav.history.empty",
        "nav.more",
        "nav.settings",
        "history.bucket.today",
        "history.bucket.yesterday",
        "measurement.opened_from_history",
        # Stage 2 — unified composer
        "composer.section",
        "composer.attach",
        "composer.live",
        "composer.lens",
        "composer.scenario",
        # Stage 4 — history tree
        "history.manage",
        "history.new_category",
        "history.create_category",
        "history.filter_by_label",
        "history.uncategorized",
        "organizer.title",
        "organizer.category",
        "organizer.labels",
        "organizer.add_label",
        # Stage 5 — refreshed howto
        "new.howto.body",
    ],
)
def test_redesign_key_present(key: str) -> None:
    assert key in _i18n.TRANSLATIONS, f"missing redesign i18n key: {key}"
    entry = _i18n.TRANSLATIONS[key]
    for lang in _i18n.SUPPORTED_LANGS:
        assert lang in entry and str(entry[lang]).strip()


def test_howto_body_reflects_history_rail() -> None:
    """The refreshed how-it-works copy points at the History rail, not
    the retired 'Measurement update tab'."""
    body = _i18n.TRANSLATIONS["new.howto.body"]
    en = str(body[_i18n.LANG_EN])
    assert "History" in en
    assert "Measurement update tab" not in en


def test_translation_function_falls_back_to_english() -> None:
    """T() falls back EN when a language is absent — but with the
    completeness test above, fallback should never actually trigger."""
    # a real key resolves in every language
    for lang in _i18n.SUPPORTED_LANGS:
        val = _i18n.T("nav.history", lang=lang)
        assert val and val != "nav.history"
    # an unknown key returns itself (last-resort signal)
    assert _i18n.T("totally.unknown.key.xyz") == "totally.unknown.key.xyz"
