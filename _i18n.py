"""Internationalization for the Console UI.

Four languages — the ones the founder identified as common in North
America: English, Chinese (Simplified), Spanish, French.

Design discipline:
  - Single source of truth for every visible UI string is the EN value
  - Translations are co-located so a translator can read column by column
  - Fall back to EN when a key is missing in the chosen language
  - `T()` is a free function that reads the current language from
    Streamlit's session_state so it works inside any render_* function
    without passing state around

When adding a new visible string:
  1. Add the EN value to TRANSLATIONS[<key>][LANG_EN]
  2. Add 中 / ES / FR translations for the same key
  3. Use `T("<key>")` at the call site

Translations were drafted by a bilingual speaker who knows the
Omytea product vocabulary. They should be reviewed before a public-
press launch but are acceptable for a first-tester audience.
"""

from __future__ import annotations

from typing import Final

# Language codes are kept short — they become URL query params + cookies
# at some point, so we want stable two-character handles.
LANG_EN: Final = "en"
LANG_ZH: Final = "zh"
LANG_ES: Final = "es"
LANG_FR: Final = "fr"

SUPPORTED_LANGS: Final = (LANG_EN, LANG_ZH, LANG_ES, LANG_FR)

# Short display labels for the language switcher chip. Native-script
# label for each so the switcher reads correctly regardless of which
# language is currently active.
LANG_LABEL: Final[dict[str, str]] = {
    LANG_EN: "EN",
    LANG_ZH: "中",
    LANG_ES: "ES",
    LANG_FR: "FR",
}

DEFAULT_LANG: Final = LANG_EN


# ===========================================================================
# Translation table. Keys are stable identifiers; do not reuse them across
# meanings. When in doubt, add a new key rather than overloading an old one.
# ===========================================================================

TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    # -----  Brand / chrome  -----
    "brand.tagline": {
        LANG_EN: "Probability-calibrated decision support",
        LANG_ZH: "概率校准的决策辅助",
        LANG_ES: "Apoyo a decisiones con probabilidad calibrada",
        LANG_FR: "Aide à la décision à probabilité calibrée",
    },
    "brand.disclaimer": {
        LANG_EN: (
            "Not a deterministic prediction system. Outputs are calibrated "
            "future scenarios with measurement-update feedback. Not "
            "medical, legal, or financial advice."
        ),
        LANG_ZH: (
            "本系统不预测确定性结果，输出的是带校准反馈的未来情景概率分布。"
            "不构成医疗、法律或金融建议。"
        ),
        LANG_ES: (
            "No es un sistema de predicción determinista. Las salidas son "
            "escenarios futuros calibrados con retroalimentación de "
            "medición. No es asesoramiento médico, legal o financiero."
        ),
        LANG_FR: (
            "Pas un système de prédiction déterministe. Les résultats sont "
            "des scénarios futurs calibrés avec retour de mesure. Ne "
            "constitue pas un avis médical, juridique ou financier."
        ),
    },
    # -----  Sidebar mode labels  -----
    "mode.new_prediction": {
        LANG_EN: "New prediction",
        LANG_ZH: "新预测",
        LANG_ES: "Nueva predicción",
        LANG_FR: "Nouvelle prédiction",
    },
    "mode.video_query": {
        LANG_EN: "Video query",
        LANG_ZH: "视频问询",
        LANG_ES: "Consulta de video",
        LANG_FR: "Requête vidéo",
    },
    "mode.live_webcam": {
        LANG_EN: "Live webcam",
        LANG_ZH: "实时摄像头",
        LANG_ES: "Cámara en vivo",
        LANG_FR: "Caméra en direct",
    },
    "mode.measurement_update": {
        LANG_EN: "Measurement update",
        LANG_ZH: "实测回填",
        LANG_ES: "Actualización de medición",
        LANG_FR: "Mise à jour de mesure",
    },
    "mode.calibration_history": {
        LANG_EN: "Calibration history",
        LANG_ZH: "校准历史",
        LANG_ES: "Historial de calibración",
        LANG_FR: "Historique de calibrage",
    },
    "mode.pricing": {
        LANG_EN: "Pricing & pre-order",
        LANG_ZH: "定价与预订",
        LANG_ES: "Precios y reserva",
        LANG_FR: "Tarifs et précommande",
    },
    "mode.sidebar_section": {
        LANG_EN: "Mode",
        LANG_ZH: "模式",
        LANG_ES: "Modo",
        LANG_FR: "Mode",
    },
    # -----  New prediction page  -----
    "new.hero.title": {
        LANG_EN: "A decision, calibrated.",
        LANG_ZH: "把决定，校准。",
        LANG_ES: "Una decisión, calibrada.",
        LANG_FR: "Une décision, calibrée.",
    },
    "new.hero.subtitle": {
        LANG_EN: (
            "Tell the system a decision you're weighing. It compiles your "
            "input into a probability space across possible futures, "
            "stores a snapshot, and lets you score yourself later when "
            "reality has unfolded."
        ),
        LANG_ZH: (
            "把你在纠结的决定告诉系统。它会把你的输入编译成跨多个未来分支"
            "的概率空间，保存一份快照，并在事情真的发生后让你回来给自己打分。"
        ),
        LANG_ES: (
            "Cuéntale al sistema una decisión que estás sopesando. "
            "Compila tu entrada en un espacio de probabilidad sobre "
            "futuros posibles, guarda una instantánea, y te permite "
            "puntuarte después cuando la realidad se haya desarrollado."
        ),
        LANG_FR: (
            "Décrivez au système une décision que vous pesez. Il compile "
            "votre entrée en un espace de probabilités sur les futurs "
            "possibles, enregistre un instantané, et vous permet de vous "
            "évaluer plus tard quand la réalité s'est déroulée."
        ),
    },
    "new.fill_sample": {
        LANG_EN: "Fill with sample data",
        LANG_ZH: "自动填示例数据",
        LANG_ES: "Rellenar con datos de ejemplo",
        LANG_FR: "Remplir avec des données d'exemple",
    },
    "new.clear_form": {
        LANG_EN: "Clear form",
        LANG_ZH: "清空表单",
        LANG_ES: "Vaciar formulario",
        LANG_FR: "Effacer le formulaire",
    },
    "new.generate": {
        LANG_EN: "Generate prediction",
        LANG_ZH: "生成预测",
        LANG_ES: "Generar predicción",
        LANG_FR: "Générer la prédiction",
    },
    "new.howto.title": {
        LANG_EN: "How this works · 30 seconds",
        LANG_ZH: "30 秒读懂用法",
        LANG_ES: "Cómo funciona · 30 segundos",
        LANG_FR: "Comment ça marche · 30 secondes",
    },
    "new.owner_bias": {
        LANG_EN: "I am the project owner / this is a self-test",
        LANG_ZH: "我是项目作者 / 自测",
        LANG_ES: "Soy el creador del proyecto / es una autoprueba",
        LANG_FR: "Je suis l'auteur du projet / c'est un auto-test",
    },
    # -----  Live webcam page  -----
    "webcam.title": {
        LANG_EN: "Live webcam",
        LANG_ZH: "实时摄像头",
        LANG_ES: "Cámara en vivo",
        LANG_FR: "Caméra en direct",
    },
    "webcam.subtitle": {
        LANG_EN: (
            "Camera frames stream to the perception layer, entity "
            "trajectories accumulate, and the joint quantum state is "
            "rebuilt every few frames. Nothing about the stream is stored."
        ),
        LANG_ZH: (
            "摄像头帧进入感知层，目标轨迹逐步累积，每几帧重建一次联合量子"
            "状态。任何视频内容都不会被保存。"
        ),
        LANG_ES: (
            "Los fotogramas de la cámara fluyen a la capa de percepción, "
            "las trayectorias de entidades se acumulan, y el estado "
            "cuántico conjunto se reconstruye cada pocos fotogramas. Nada "
            "del stream se almacena."
        ),
        LANG_FR: (
            "Les images de la caméra alimentent la couche de perception, "
            "les trajectoires d'entités s'accumulent, et l'état quantique "
            "joint est reconstruit toutes les quelques images. Rien du "
            "flux n'est conservé."
        ),
    },
    # -----  Live state metrics  -----
    "live.frames_processed": {
        LANG_EN: "Frames processed",
        LANG_ZH: "已处理帧数",
        LANG_ES: "Fotogramas procesados",
        LANG_FR: "Images traitées",
    },
    "live.fps": {
        LANG_EN: "Observed FPS",
        LANG_ZH: "实际帧率",
        LANG_ES: "FPS observados",
        LANG_FR: "FPS observés",
    },
    "live.entities": {
        LANG_EN: "Live entities",
        LANG_ZH: "实时实体",
        LANG_ES: "Entidades en vivo",
        LANG_FR: "Entités en direct",
    },
    "live.joint_hyps": {
        LANG_EN: "Joint hypotheses",
        LANG_ZH: "联合假设",
        LANG_ES: "Hipótesis conjuntas",
        LANG_FR: "Hypothèses jointes",
    },
    # -----  Result render  -----
    "result.heatmap_title": {
        LANG_EN: "Probability mass across futures",
        LANG_ZH: "未来分布概率热力图",
        LANG_ES: "Masa de probabilidad entre futuros",
        LANG_FR: "Masse de probabilité entre les futurs",
    },
    "result.heatmap_reading": {
        LANG_EN: (
            "Each row is one branch; intensity = probability. Wishful and "
            "worst-case anchors are tagged."
        ),
        LANG_ZH: "每行是一条未来分支，颜色越亮 = 概率越高。最好和最坏锚点已标记。",
        LANG_ES: (
            "Cada fila es una rama; la intensidad = probabilidad. Los "
            "anclajes optimista y peor caso están etiquetados."
        ),
        LANG_FR: (
            "Chaque ligne est une branche ; intensité = probabilité. Les "
            "ancres optimiste et pire-cas sont étiquetées."
        ),
    },
}


def T(key: str, lang: str | None = None) -> str:
    """Translate `key` to the chosen UI language.

    Reads st.session_state.lang when lang is not passed. Falls back to
    EN when the key isn't present in the chosen language; logs nothing
    (the key itself is shown if it's missing in EN too, which is the
    last-resort signal that someone added a T() call without a
    translation entry).
    """
    if lang is None:
        try:
            import streamlit as st  # local import to keep _i18n importable in tests
            lang = st.session_state.get("ui_lang", DEFAULT_LANG)
        except Exception:
            lang = DEFAULT_LANG
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get(LANG_EN) or key


__all__ = [
    "LANG_EN",
    "LANG_ZH",
    "LANG_ES",
    "LANG_FR",
    "SUPPORTED_LANGS",
    "LANG_LABEL",
    "DEFAULT_LANG",
    "TRANSLATIONS",
    "T",
]
