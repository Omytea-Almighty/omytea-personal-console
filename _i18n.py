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
    # -----  Mode 7: Traditional × Calibrated (Nye-clock)  -----
    "mode.traditional": {
        LANG_EN: "Traditional × Calibrated",
        LANG_ZH: "古法 × 校准",
        LANG_ES: "Tradicional × Calibrado",
        LANG_FR: "Traditionnel × Calibré",
    },
    "trad.hero.title": {
        LANG_EN: "Two priors, one dial.",
        LANG_ZH: "两种先验，一个表盘。",
        LANG_ES: "Dos priors, un dial.",
        LANG_FR: "Deux a priori, un cadran.",
    },
    "trad.hero.subtitle": {
        LANG_EN: (
            "The outer ring is your 八字 五行 balance — wood, fire, earth, "
            "metal, water. The inner ring is the model's calibrated "
            "branch distribution. The centre is the posterior when both "
            "are weighted together. Pick the weight; the dial moves."
        ),
        LANG_ZH: (
            "外圈是你八字的五行分布——木火土金水；内圈是模型校准过的"
            "未来分支；中心读数是两者按你设定的权重融合后的后验。"
            "权重一调，表盘就动。"
        ),
        LANG_ES: (
            "El anillo exterior es tu balance 五行 de 八字 — madera, "
            "fuego, tierra, metal, agua. El anillo interior es la "
            "distribución calibrada del modelo. El centro es el "
            "posterior cuando ambos se ponderan juntos."
        ),
        LANG_FR: (
            "L'anneau externe est ton équilibre 五行 du 八字 — bois, feu, "
            "terre, métal, eau. L'anneau interne est la distribution "
            "calibrée du modèle. Le centre est le postérieur quand les "
            "deux sont pondérés ensemble."
        ),
    },
    "trad.birth.section": {
        LANG_EN: "Your birth",
        LANG_ZH: "出生信息",
        LANG_ES: "Tu nacimiento",
        LANG_FR: "Votre naissance",
    },
    "trad.birth.year": {
        LANG_EN: "Year",
        LANG_ZH: "年",
        LANG_ES: "Año",
        LANG_FR: "Année",
    },
    "trad.birth.month": {
        LANG_EN: "Month",
        LANG_ZH: "月",
        LANG_ES: "Mes",
        LANG_FR: "Mois",
    },
    "trad.birth.day": {
        LANG_EN: "Day",
        LANG_ZH: "日",
        LANG_ES: "Día",
        LANG_FR: "Jour",
    },
    "trad.birth.hour": {
        LANG_EN: "Hour (0–23)",
        LANG_ZH: "小时（0–23）",
        LANG_ES: "Hora (0–23)",
        LANG_FR: "Heure (0–23)",
    },
    "trad.birth.hint": {
        LANG_EN: (
            "Local clock time at birth. Used only to derive the 八字 "
            "pillars + 五行 share — never stored, never sent off-device."
        ),
        LANG_ZH: (
            "出生当地的本地时间。仅用于推算八字四柱 + 五行比例——"
            "不会保存，也不会离开你的设备。"
        ),
        LANG_ES: (
            "Hora local al nacer. Sólo se usa para derivar las 八字 "
            "pillars + balance 五行 — nunca se guarda."
        ),
        LANG_FR: (
            "Heure locale à la naissance. Utilisée uniquement pour "
            "dériver les 八字 + 五行 — jamais enregistrée."
        ),
    },
    "trad.outcome.select": {
        LANG_EN: "Outcome you care about",
        LANG_ZH: "你关心的结果",
        LANG_ES: "Resultado que te importa",
        LANG_FR: "Résultat qui vous importe",
    },
    "trad.outcome.career_success": {
        LANG_EN: "Career success",
        LANG_ZH: "事业有成",
        LANG_ES: "Éxito profesional",
        LANG_FR: "Réussite professionnelle",
    },
    "trad.outcome.marriage_stable": {
        LANG_EN: "Marriage / partnership stability",
        LANG_ZH: "婚姻 / 关系稳定",
        LANG_ES: "Estabilidad de pareja",
        LANG_FR: "Stabilité conjugale",
    },
    "trad.outcome.wealth_accumulation": {
        LANG_EN: "Wealth accumulation",
        LANG_ZH: "财富积累",
        LANG_ES: "Acumulación de riqueza",
        LANG_FR: "Accumulation de richesse",
    },
    "trad.outcome.health_strong": {
        LANG_EN: "Strong health",
        LANG_ZH: "身体康健",
        LANG_ES: "Salud robusta",
        LANG_FR: "Santé robuste",
    },
    "trad.outcome.learning_good": {
        LANG_EN: "Learning / academic",
        LANG_ZH: "学业 / 学习",
        LANG_ES: "Aprendizaje / académico",
        LANG_FR: "Apprentissage / scolaire",
    },
    "trad.outcome.conflict_low": {
        LANG_EN: "Low conflict / smooth ties",
        LANG_ZH: "少口舌 / 关系顺",
        LANG_ES: "Bajo conflicto",
        LANG_FR: "Faible conflit",
    },
    "trad.combine.label": {
        LANG_EN: "How to combine",
        LANG_ZH: "融合方式",
        LANG_ES: "Cómo combinar",
        LANG_FR: "Méthode de fusion",
    },
    "trad.combine.mixture": {
        LANG_EN: "α-mixture (linear)",
        LANG_ZH: "α-混合（线性）",
        LANG_ES: "Mezcla α (lineal)",
        LANG_FR: "Mélange α (linéaire)",
    },
    "trad.combine.bayesian": {
        LANG_EN: "Bayesian update",
        LANG_ZH: "贝叶斯更新",
        LANG_ES: "Actualización bayesiana",
        LANG_FR: "Mise à jour bayésienne",
    },
    "trad.combine.off": {
        LANG_EN: "Off (model only)",
        LANG_ZH: "关闭（只用模型）",
        LANG_ES: "Apagado (sólo modelo)",
        LANG_FR: "Désactivé (modèle seul)",
    },
    "trad.alpha.label": {
        LANG_EN: "Traditional-prior weight (α)",
        LANG_ZH: "古法权重 α",
        LANG_ES: "Peso del prior tradicional (α)",
        LANG_FR: "Poids du prior traditionnel (α)",
    },
    "trad.alpha.hint": {
        LANG_EN: (
            "0 = ignore the traditional prior entirely; 1 = the centre "
            "reading is purely the 五行 prior. 0.2–0.4 is the "
            "honest-curiosity range."
        ),
        LANG_ZH: (
            "0 = 完全忽略古法；1 = 中心读数完全是五行先验。"
            "0.2–0.4 是一个比较诚实的好奇区间。"
        ),
        LANG_ES: (
            "0 = ignorar el prior tradicional; 1 = la lectura central "
            "es puramente 五行. 0.2–0.4 es el rango de curiosidad honesta."
        ),
        LANG_FR: (
            "0 = ignorer le prior traditionnel ; 1 = la lecture "
            "centrale est purement 五行. 0.2–0.4 est la plage de "
            "curiosité honnête."
        ),
    },
    "trad.compile": {
        LANG_EN: "Read the dial",
        LANG_ZH: "读这个表盘",
        LANG_ES: "Leer el dial",
        LANG_FR: "Lire le cadran",
    },
    "trad.legend": {
        LANG_EN: (
            "Outer ring = 五行 share from your 八字. Inner ring = "
            "model-calibrated branch probabilities. Centre = "
            "combined posterior."
        ),
        LANG_ZH: (
            "外圈 = 八字推得的五行分布；内圈 = 模型校准过的分支概率；"
            "中心 = 两者融合后的后验。"
        ),
        LANG_ES: (
            "Anillo exterior = balance 五行 de tu 八字. Anillo interior "
            "= probabilidades calibradas del modelo. Centro = "
            "posterior combinado."
        ),
        LANG_FR: (
            "Anneau externe = équilibre 五行 de votre 八字. Anneau "
            "interne = probabilités calibrées du modèle. Centre = "
            "postérieur combiné."
        ),
    },
    "trad.disclaimer": {
        LANG_EN: (
            "Not deterministic fortune-telling — an explicitly weighted "
            "prior the user chooses (or doesn't) to use. The model's "
            "unweighted output is always shown alongside the combined "
            "view so you can see the shift."
        ),
        LANG_ZH: (
            "不是确定的命理预言——它只是一个用户主动选择是否使用的"
            "可调权重先验。模型未加权的原始输出始终与融合视图并列展示，"
            "让你看清差异从哪里来。"
        ),
        LANG_ES: (
            "No es adivinación determinista — un prior con peso "
            "explícito que el usuario elige usar o no. La salida no "
            "ponderada del modelo siempre se muestra junto al posterior."
        ),
        LANG_FR: (
            "Pas de prédiction déterministe — un prior pondéré que "
            "l'utilisateur choisit (ou non) d'utiliser. La sortie non "
            "pondérée du modèle est toujours affichée à côté."
        ),
    },
    "trad.no_input": {
        LANG_EN: "Fill in your birth + outcome above, then read the dial.",
        LANG_ZH: "上方填好出生信息和你关心的结果，再读这个表盘。",
        LANG_ES: "Rellena tu nacimiento + resultado arriba, luego lee el dial.",
        LANG_FR: "Remplissez la naissance + le résultat ci-dessus, puis lisez le cadran.",
    },
    "trad.center.dominant_fmt": {
        LANG_EN: "{element}-dominant 五行",
        LANG_ZH: "五行偏{element}",
        LANG_ES: "五行 con dominio de {element}",
        LANG_FR: "五行 dominé par {element}",
    },
    "trad.metric.model": {
        LANG_EN: "Model-only probability",
        LANG_ZH: "模型独立预测",
        LANG_ES: "Probabilidad sólo-modelo",
        LANG_FR: "Probabilité modèle seul",
    },
    "trad.metric.tradition": {
        LANG_EN: "Traditional-prior probability",
        LANG_ZH: "古法先验概率",
        LANG_ES: "Probabilidad prior tradicional",
        LANG_FR: "Probabilité prior traditionnel",
    },
    "trad.metric.combined": {
        LANG_EN: "Combined posterior",
        LANG_ZH: "融合后验",
        LANG_ES: "Posterior combinado",
        LANG_FR: "Postérieur combiné",
    },
    "trad.metric.model_short": {
        LANG_EN: "MODEL",
        LANG_ZH: "模型",
        LANG_ES: "MODELO",
        LANG_FR: "MODÈLE",
    },
    "trad.metric.combined_short": {
        LANG_EN: "COMBINED",
        LANG_ZH: "融合",
        LANG_ES: "COMBINADO",
        LANG_FR: "COMBINÉ",
    },
    "trad.lens.invite_chip": {
        LANG_EN: "an old read of the same prediction",
        LANG_ZH: "古法读这同一份预测",
        LANG_ES: "una lectura tradicional de la misma predicción",
        LANG_FR: "une lecture traditionnelle de la même prédiction",
    },
    "trad.lens.expander_label": {
        LANG_EN: "Time-honored lens · open",
        LANG_ZH: "古法视角 · 展开",
        LANG_ES: "Lente tradicional · abrir",
        LANG_FR: "Lecture traditionnelle · ouvrir",
    },
    "trad.using_sample": {
        LANG_EN: (
            "Sample branches shown — generate a real prediction in the "
            "New-prediction tab and the dial reads from your own decision."
        ),
        LANG_ZH: (
            "当前用的是示例分支——回到「新预测」生成一份真实预测，"
            "表盘就会读你自己的决定。"
        ),
        LANG_ES: (
            "Mostrando ramas de muestra — genera una predicción real en la "
            "pestaña Nueva predicción y el dial leerá tu propia decisión."
        ),
        LANG_FR: (
            "Branches d'exemple — générez une vraie prédiction dans "
            "l'onglet Nouvelle prédiction et le cadran lira votre décision."
        ),
    },
    # -----  Other-page heroes (Apple-style two-tier)  -----
    "video.hero.title": {
        LANG_EN: "Watch a clip. Get the futures.",
        LANG_ZH: "看一段视频，得到未来分布。",
        LANG_ES: "Mira un clip. Obtén los futuros.",
        LANG_FR: "Regardez un clip. Obtenez les futurs.",
    },
    "video.hero.subtitle": {
        LANG_EN: (
            "Upload a short clip. The system samples keyframes, runs "
            "the perception pipeline, asks a local vision model to "
            "read the scene, and emits calibrated future-scenario "
            "branches."
        ),
        LANG_ZH: (
            "上传一段短视频。系统会抽帧、跑感知层、让本地视觉模型"
            "读懂画面，并输出校准过的未来分支概率分布。"
        ),
        LANG_ES: (
            "Sube un clip corto. El sistema muestrea fotogramas clave, "
            "ejecuta la percepción, le pide a un modelo de visión local "
            "que lea la escena, y emite ramas calibradas."
        ),
        LANG_FR: (
            "Téléversez un court clip. Le système échantillonne les "
            "images clés, exécute la perception, demande à un modèle "
            "de vision local de lire la scène, puis émet des branches "
            "calibrées."
        ),
    },
    "measurement.hero.title": {
        LANG_EN: "Tell it what actually happened.",
        LANG_ZH: "告诉它真实发生了什么。",
        LANG_ES: "Cuéntale lo que pasó de verdad.",
        LANG_FR: "Dis-lui ce qui s'est réellement passé.",
    },
    "measurement.hero.subtitle": {
        LANG_EN: (
            "Look up a past prediction by ID, score each branch by how "
            "much it materialized, and the system computes calibration "
            "(Brier, log-loss) on your forecast. The measurement loop "
            "is the whole point — predictions you never score teach "
            "you nothing."
        ),
        LANG_ZH: (
            "用 ID 找回之前的预测，根据真实情况给每个分支打分；"
            "系统会算出 Brier / log-loss 校准指标。"
            "回填测量是这个系统的关键——不复盘的预测什么都教不会你。"
        ),
        LANG_ES: (
            "Busca una predicción pasada por ID, puntúa cada rama "
            "según cuánto se materializó, y el sistema calcula la "
            "calibración (Brier, log-loss). El bucle de medición es "
            "el propósito."
        ),
        LANG_FR: (
            "Retrouvez une prédiction par identifiant, notez chaque "
            "branche selon ce qui s'est matérialisé, et le système "
            "calcule la calibration (Brier, log-loss)."
        ),
    },
    "calibration.hero.title": {
        LANG_EN: "How well-calibrated are you?",
        LANG_ZH: "你的判断校准得怎样？",
        LANG_ES: "¿Qué tan bien calibrado estás?",
        LANG_FR: "À quel point êtes-vous calibré ?",
    },
    "calibration.hero.subtitle": {
        LANG_EN: (
            "Aggregate Brier and log-loss across all of your scored "
            "predictions — what you genuinely got right, what you "
            "fooled yourself about, and whether you trended better "
            "over time."
        ),
        LANG_ZH: (
            "把你打过分的预测全部汇总，看 Brier / log-loss 校准趋势——"
            "哪些是真懂，哪些是自欺，以及随时间有没有进步。"
        ),
        LANG_ES: (
            "Agrega Brier y log-loss en todas tus predicciones "
            "puntuadas — qué acertaste de verdad y si mejoraste con "
            "el tiempo."
        ),
        LANG_FR: (
            "Agrège Brier et log-loss sur toutes vos prédictions "
            "notées — ce que vous avez vraiment bien fait et si vous "
            "vous êtes amélioré avec le temps."
        ),
    },
    "pricing.hero.title": {
        LANG_EN: "An honest price, posted in advance.",
        LANG_ZH: "事先公开的、诚实的价格。",
        LANG_ES: "Un precio honesto, publicado por adelantado.",
        LANG_FR: "Un prix honnête, affiché à l'avance.",
    },
    "pricing.hero.subtitle": {
        LANG_EN: (
            "Free during the public beta. After v1.0 the Personal tier "
            "stays free for 25 predictions / month; heavier use moves "
            "to a flat monthly. No card collected until billing actually "
            "starts."
        ),
        LANG_ZH: (
            "公开 beta 期间完全免费。v1.0 以后个人档每月 25 次预测"
            "依旧免费，重度使用按固定月费。开始计费前不收信用卡。"
        ),
        LANG_ES: (
            "Gratis durante la beta pública. Después de v1.0 el plan "
            "Personal sigue gratis para 25 predicciones/mes; uso "
            "intensivo pasa a una mensualidad fija."
        ),
        LANG_FR: (
            "Gratuit pendant la bêta publique. Après v1.0 le plan "
            "Personnel reste gratuit jusqu'à 25 prédictions/mois ; "
            "usage intensif passe à un forfait mensuel."
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
