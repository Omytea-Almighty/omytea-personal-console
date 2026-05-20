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
    # -----  Sidebar navigation (history-rail shell)  -----
    "nav.new_prediction": {
        LANG_EN: "✦  New prediction",
        LANG_ZH: "✦  新预测",
        LANG_ES: "✦  Nueva predicción",
        LANG_FR: "✦  Nouvelle prédiction",
    },
    "nav.history": {
        LANG_EN: "History",
        LANG_ZH: "历史",
        LANG_ES: "Historial",
        LANG_FR: "Historique",
    },
    "nav.history.empty": {
        LANG_EN: "No predictions yet. Run one and it appears here.",
        LANG_ZH: "还没有预测。生成一个就会出现在这里。",
        LANG_ES: "Aún no hay predicciones. Ejecuta una y aparecerá aquí.",
        LANG_FR: "Pas encore de prédictions. Lancez-en une et elle apparaîtra ici.",
    },
    "nav.more": {
        LANG_EN: "More",
        LANG_ZH: "更多",
        LANG_ES: "Más",
        LANG_FR: "Plus",
    },
    "nav.more.hint": {
        LANG_EN: "Video, live camera, the 玄学 lens, and other surfaces.",
        LANG_ZH: "视频、实时摄像头、玄学透镜及其它界面。",
        LANG_ES: "Video, cámara en vivo, la lente 玄学 y otras superficies.",
        LANG_FR: "Vidéo, caméra en direct, la lentille 玄学 et autres surfaces.",
    },
    "nav.settings": {
        LANG_EN: "Settings",
        LANG_ZH: "设置",
        LANG_ES: "Ajustes",
        LANG_FR: "Paramètres",
    },
    "settings.language": {
        LANG_EN: "Language",
        LANG_ZH: "语言",
        LANG_ES: "Idioma",
        LANG_FR: "Langue",
    },
    "settings.currency": {
        LANG_EN: "Currency",
        LANG_ZH: "货币",
        LANG_ES: "Moneda",
        LANG_FR: "Devise",
    },
    "history.bucket.today": {
        LANG_EN: "Today",
        LANG_ZH: "今天",
        LANG_ES: "Hoy",
        LANG_FR: "Aujourd'hui",
    },
    "history.bucket.yesterday": {
        LANG_EN: "Yesterday",
        LANG_ZH: "昨天",
        LANG_ES: "Ayer",
        LANG_FR: "Hier",
    },
    "history.bucket.prev7": {
        LANG_EN: "Previous 7 days",
        LANG_ZH: "前 7 天",
        LANG_ES: "Últimos 7 días",
        LANG_FR: "7 derniers jours",
    },
    "history.bucket.prev30": {
        LANG_EN: "Previous 30 days",
        LANG_ZH: "前 30 天",
        LANG_ES: "Últimos 30 días",
        LANG_FR: "30 derniers jours",
    },
    "measurement.opened_from_history": {
        LANG_EN: "Opened from history",
        LANG_ZH: "从历史记录打开",
        LANG_ES: "Abierto desde el historial",
        LANG_FR: "Ouvert depuis l'historique",
    },
    "measurement.not_found": {
        LANG_EN: "This prediction is no longer available in this session.",
        LANG_ZH: "本次会话中已找不到该预测记录。",
        LANG_ES: "Esta predicción ya no está disponible en esta sesión.",
        LANG_FR: "Cette prédiction n'est plus disponible dans cette session.",
    },
    # -----  Unified composer (workspace input modalities)  -----
    "composer.section": {
        LANG_EN: "Compose your prediction",
        LANG_ZH: "组合你的预测输入",
        LANG_ES: "Compón tu predicción",
        LANG_FR: "Composez votre prédiction",
    },
    "composer.scenario": {
        LANG_EN: "Scenario",
        LANG_ZH: "情景",
        LANG_ES: "Escenario",
        LANG_FR: "Scénario",
    },
    "composer.attach": {
        LANG_EN: "+  Attach",
        LANG_ZH: "+  附加",
        LANG_ES: "+  Adjuntar",
        LANG_FR: "+  Joindre",
    },
    "composer.attach.hint": {
        LANG_EN: "Add a video or files to ground the prediction in real input.",
        LANG_ZH: "附加视频或文件，让预测建立在真实输入之上。",
        LANG_ES: "Añade un video o archivos para fundamentar la predicción.",
        LANG_FR: "Ajoutez une vidéo ou des fichiers pour ancrer la prédiction.",
    },
    "composer.attach.video": {
        LANG_EN: "Video",
        LANG_ZH: "视频",
        LANG_ES: "Video",
        LANG_FR: "Vidéo",
    },
    "composer.attach.files": {
        LANG_EN: "Other files (context)",
        LANG_ZH: "其它文件（上下文）",
        LANG_ES: "Otros archivos (contexto)",
        LANG_FR: "Autres fichiers (contexte)",
    },
    "composer.attach.video_ready": {
        LANG_EN: "Video attached — the analysis panel opens below.",
        LANG_ZH: "已附加视频 —— 分析面板已在下方展开。",
        LANG_ES: "Video adjunto — el panel de análisis se abre abajo.",
        LANG_FR: "Vidéo jointe — le panneau d'analyse s'ouvre ci-dessous.",
    },
    "composer.attach.files_ready": {
        LANG_EN: "context file(s) attached.",
        LANG_ZH: "个上下文文件已附加。",
        LANG_ES: "archivo(s) de contexto adjunto(s).",
        LANG_FR: "fichier(s) de contexte joint(s).",
    },
    "composer.attach.panel": {
        LANG_EN: "Attached video — scene prediction",
        LANG_ZH: "附加视频 —— 场景预测",
        LANG_ES: "Video adjunto — predicción de escena",
        LANG_FR: "Vidéo jointe — prédiction de scène",
    },
    "composer.attach.panel_hint": {
        LANG_EN: (
            "The attached video is analyzed as its own scene prediction "
            "with the same branch / coherence / evidence machinery."
        ),
        LANG_ZH: (
            "附加的视频会作为独立的场景预测来分析，使用相同的分支 / 相干 / "
            "证据机制。"
        ),
        LANG_ES: (
            "El video adjunto se analiza como su propia predicción de "
            "escena con la misma maquinaria de ramas / coherencia."
        ),
        LANG_FR: (
            "La vidéo jointe est analysée comme sa propre prédiction de "
            "scène avec la même machinerie de branches / cohérence."
        ),
    },
    "composer.live": {
        LANG_EN: "Live video",
        LANG_ZH: "实时视频",
        LANG_ES: "Video en vivo",
        LANG_FR: "Vidéo en direct",
    },
    "composer.live.hint": {
        LANG_EN: "Stream your camera as a live input modality.",
        LANG_ZH: "把摄像头作为实时输入模态接入。",
        LANG_ES: "Transmite tu cámara como modalidad de entrada en vivo.",
        LANG_FR: "Diffusez votre caméra comme modalité d'entrée en direct.",
    },
    "composer.live.panel": {
        LANG_EN: "Live camera — continuous perception",
        LANG_ZH: "实时摄像头 —— 连续感知",
        LANG_ES: "Cámara en vivo — percepción continua",
        LANG_FR: "Caméra en direct — perception continue",
    },
    "composer.lens": {
        LANG_EN: "玄学 lens",
        LANG_ZH: "玄学透镜",
        LANG_ES: "Lente 玄学",
        LANG_FR: "Lentille 玄学",
    },
    "composer.lens.hint": {
        LANG_EN: (
            "An optional traditional-prior lens on the same prediction. "
            "Off by default — the substance is the world model."
        ),
        LANG_ZH: (
            "对同一预测的可选传统先验透镜。默认关闭 —— 实质是世界模型。"
        ),
        LANG_ES: (
            "Una lente opcional de prior tradicional sobre la misma "
            "predicción. Desactivada por defecto."
        ),
        LANG_FR: (
            "Une lentille optionnelle de prior traditionnel sur la même "
            "prédiction. Désactivée par défaut."
        ),
    },
    # -----  History tree (user-owned categories + labels)  -----
    "history.manage": {
        LANG_EN: "Manage categories",
        LANG_ZH: "管理分类",
        LANG_ES: "Gestionar categorías",
        LANG_FR: "Gérer les catégories",
    },
    "history.new_category": {
        LANG_EN: "New category name",
        LANG_ZH: "新分类名称",
        LANG_ES: "Nombre de nueva categoría",
        LANG_FR: "Nom de la nouvelle catégorie",
    },
    "history.new_category.ph": {
        LANG_EN: "e.g. Career, Investing, Health",
        LANG_ZH: "例如：职业、投资、健康",
        LANG_ES: "p. ej. Carrera, Inversión, Salud",
        LANG_FR: "ex. Carrière, Investissement, Santé",
    },
    "history.create_category": {
        LANG_EN: "Create category",
        LANG_ZH: "创建分类",
        LANG_ES: "Crear categoría",
        LANG_FR: "Créer la catégorie",
    },
    "history.category_name": {
        LANG_EN: "Category name",
        LANG_ZH: "分类名称",
        LANG_ES: "Nombre de categoría",
        LANG_FR: "Nom de la catégorie",
    },
    "history.delete_category": {
        LANG_EN: "Delete this category (predictions stay, uncategorized)",
        LANG_ZH: "删除此分类（预测保留，归为未分类）",
        LANG_ES: "Eliminar esta categoría (las predicciones quedan sin categoría)",
        LANG_FR: "Supprimer cette catégorie (les prédictions restent, non classées)",
    },
    "history.filter_by_label": {
        LANG_EN: "Filter by label",
        LANG_ZH: "按标签筛选",
        LANG_ES: "Filtrar por etiqueta",
        LANG_FR: "Filtrer par étiquette",
    },
    "history.all_labels": {
        LANG_EN: "All predictions",
        LANG_ZH: "全部预测",
        LANG_ES: "Todas las predicciones",
        LANG_FR: "Toutes les prédictions",
    },
    "history.no_label_match": {
        LANG_EN: "No predictions carry that label.",
        LANG_ZH: "没有预测带有该标签。",
        LANG_ES: "Ninguna predicción tiene esa etiqueta.",
        LANG_FR: "Aucune prédiction ne porte cette étiquette.",
    },
    "history.uncategorized": {
        LANG_EN: "Uncategorized",
        LANG_ZH: "未分类",
        LANG_ES: "Sin categoría",
        LANG_FR: "Non classé",
    },
    # -----  Prediction organizer (category + labels on a prediction)  --
    "organizer.title": {
        LANG_EN: "Organize · category & labels",
        LANG_ZH: "整理 · 分类与标签",
        LANG_ES: "Organizar · categoría y etiquetas",
        LANG_FR: "Organiser · catégorie et étiquettes",
    },
    "organizer.category": {
        LANG_EN: "Category",
        LANG_ZH: "分类",
        LANG_ES: "Categoría",
        LANG_FR: "Catégorie",
    },
    "organizer.uncategorized": {
        LANG_EN: "— Uncategorized —",
        LANG_ZH: "— 未分类 —",
        LANG_ES: "— Sin categoría —",
        LANG_FR: "— Non classé —",
    },
    "organizer.no_categories": {
        LANG_EN: "Create categories in the sidebar's Manage categories panel.",
        LANG_ZH: "在侧边栏的「管理分类」面板中创建分类。",
        LANG_ES: "Crea categorías en el panel Gestionar categorías de la barra lateral.",
        LANG_FR: "Créez des catégories dans le panneau Gérer les catégories.",
    },
    "organizer.labels": {
        LANG_EN: "Labels",
        LANG_ZH: "标签",
        LANG_ES: "Etiquetas",
        LANG_FR: "Étiquettes",
    },
    "organizer.no_labels": {
        LANG_EN: "No labels yet. Add one below.",
        LANG_ZH: "还没有标签。在下方添加。",
        LANG_ES: "Aún no hay etiquetas. Añade una abajo.",
        LANG_FR: "Pas encore d'étiquettes. Ajoutez-en une ci-dessous.",
    },
    "organizer.remove_label": {
        LANG_EN: "Remove this label",
        LANG_ZH: "移除此标签",
        LANG_ES: "Quitar esta etiqueta",
        LANG_FR: "Retirer cette étiquette",
    },
    "organizer.add_label": {
        LANG_EN: "Add a label",
        LANG_ZH: "添加标签",
        LANG_ES: "Añadir una etiqueta",
        LANG_FR: "Ajouter une étiquette",
    },
    "organizer.add_label.ph": {
        LANG_EN: "e.g. urgent, revisit-Q3, high-stakes",
        LANG_ZH: "例如：紧急、Q3复盘、高风险",
        LANG_ES: "p. ej. urgente, revisar-T3, alto-riesgo",
        LANG_FR: "ex. urgent, revoir-T3, enjeux-élevés",
    },
    "organizer.add_label_btn": {
        LANG_EN: "Add label",
        LANG_ZH: "添加",
        LANG_ES: "Añadir etiqueta",
        LANG_FR: "Ajouter l'étiquette",
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
    "new.howto.body": {
        LANG_EN: (
            "1. **Compose.** Describe a decision in the scenario fields, "
            "or attach a video / toggle live camera with the **+** bar "
            "above. Optionally turn on the 玄学 lens.\n"
            "2. **Run.** The system produces 6–8 future branches with "
            "priors, a wishful and a worst-case anchor, off-diagonal "
            "correlations, and a recommended-evidence list "
            "(ΔP in percentage points).\n"
            "3. **Come back later.** Every prediction appears in the "
            "**History** rail on the left. Click one to reopen it and "
            "score how each branch actually materialized — the system "
            "computes your calibration (Brier / log-loss). Organize the "
            "rail into your own categories and labels.\n\n"
            "Not fortune-telling, not medical / legal / financial "
            "advice. No external API required — runs end-to-end locally "
            "when self-hosted with Ollama."
        ),
        LANG_ZH: (
            "1. **组合输入。** 在情景字段里描述一个决定，或用上方的 "
            "**+** 工具栏附加视频 / 开启实时摄像头。可选地打开玄学透镜。\n"
            "2. **运行。** 系统会生成 6–8 个带先验的未来分支、一个理想"
            "锚点和一个最坏锚点、非对角相关性，以及一份推荐证据清单"
            "（ΔP 以百分点计）。\n"
            "3. **稍后回来。** 每份预测都会出现在左侧的**历史**栏。"
            "点击任意一份即可重新打开并为各分支实际兑现程度打分——"
            "系统会算出你的校准度（Brier / 对数损失）。你还可以把历史栏"
            "整理成自己的分类和标签。\n\n"
            "这不是算命，也不构成医疗 / 法律 / 金融建议。无需外部 API——"
            "本地用 Ollama 自托管即可端到端运行。"
        ),
        LANG_ES: (
            "1. **Componer.** Describe una decisión en los campos del "
            "escenario, o adjunta un video / activa la cámara en vivo "
            "con la barra **+** de arriba. Opcionalmente activa la "
            "lente 玄学.\n"
            "2. **Ejecutar.** El sistema produce 6–8 ramas futuras con "
            "priors, un ancla optimista y otra pesimista, correlaciones "
            "fuera de la diagonal y una lista de evidencia recomendada "
            "(ΔP en puntos porcentuales).\n"
            "3. **Vuelve más tarde.** Cada predicción aparece en el "
            "panel **Historial** a la izquierda. Haz clic para reabrirla "
            "y puntuar cómo se materializó cada rama. Organiza el panel "
            "en tus propias categorías y etiquetas.\n\n"
            "No es adivinación, ni asesoramiento médico / legal / "
            "financiero. No requiere API externa."
        ),
        LANG_FR: (
            "1. **Composer.** Décrivez une décision dans les champs du "
            "scénario, ou joignez une vidéo / activez la caméra en "
            "direct avec la barre **+** ci-dessus. Activez "
            "éventuellement la lentille 玄学.\n"
            "2. **Lancer.** Le système produit 6–8 branches futures avec "
            "priors, une ancre optimiste et une pessimiste, des "
            "corrélations hors-diagonale et une liste de preuves "
            "recommandées (ΔP en points de pourcentage).\n"
            "3. **Revenez plus tard.** Chaque prédiction apparaît dans "
            "le panneau **Historique** à gauche. Cliquez pour la "
            "rouvrir et noter comment chaque branche s'est concrétisée. "
            "Organisez le panneau en vos propres catégories et "
            "étiquettes.\n\n"
            "Ni divination, ni conseil médical / juridique / financier. "
            "Aucune API externe requise."
        ),
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
    # -----  Output-region view toggle (OMY-V415 #60 D)  -----
    "output.view.quantum": {
        LANG_EN: "Quantum heatmap",
        LANG_ZH: "量子热力图",
        LANG_ES: "Mapa cuántico",
        LANG_FR: "Carte quantique",
    },
    "output.view.xuanxue": {
        LANG_EN: "玄学 Nye Clock",
        LANG_ZH: "玄学时轮",
        LANG_ES: "Reloj Nye 玄学",
        LANG_FR: "Horloge Nye 玄学",
    },
    "output.view.label": {
        LANG_EN: "Output view",
        LANG_ZH: "输出视图",
        LANG_ES: "Vista de salida",
        LANG_FR: "Vue de sortie",
    },
    "output.view.hint": {
        LANG_EN: (
            "Switch the output region between the quantum prediction "
            "heatmap and the 玄学 Nye Clock lens. The quantum view is "
            "the default; 玄学 is the opt-in alternate."
        ),
        LANG_ZH: (
            "在量子预测热力图与玄学时轮透镜之间切换输出区。"
            "量子视图为默认；玄学为可选替代视图。"
        ),
        LANG_ES: (
            "Cambia la región de salida entre el mapa de calor cuántico "
            "y la lente del Reloj Nye 玄学. La vista cuántica es la "
            "predeterminada."
        ),
        LANG_FR: (
            "Basculez la région de sortie entre la carte de chaleur "
            "quantique et la lentille de l'Horloge Nye 玄学. La vue "
            "quantique est par défaut."
        ),
    },
    "result.heatmap_reading": {
        LANG_EN: (
            "Each row is one future; each column a slice of your scoring "
            "horizon. Read across a row to see one future's likelihood "
            "evolve; read down a column for the whole distribution at "
            "that moment. The spread sharpens from uncertain (now) "
            "toward the calibrated probabilities (your horizon)."
        ),
        LANG_ZH: (
            "每一行是一条未来分支，每一列是你评分时限上的一个切片。"
            "横看一行 = 这条未来的概率随时间如何演变；纵看一列 = "
            "那个时刻的整体概率分布。分布从「现在」的不确定逐步收敛"
            "到「时限」处校准过的概率。"
        ),
        LANG_ES: (
            "Cada fila es un futuro; cada columna un tramo de tu "
            "horizonte. A lo largo de una fila ves cómo evoluciona una "
            "probabilidad; hacia abajo en una columna, la distribución "
            "en ese momento."
        ),
        LANG_FR: (
            "Chaque ligne est un futur ; chaque colonne une tranche de "
            "votre horizon. En lisant une ligne : l'évolution d'une "
            "probabilité ; en lisant une colonne : la distribution à "
            "cet instant."
        ),
    },
    # -----  Interactive heatmap + camera component (v10 port)  -----
    "heatmap.camera_btn": {
        LANG_EN: "Use my camera",
        LANG_ZH: "使用摄像头",
        LANG_ES: "Usar mi cámara",
        LANG_FR: "Utiliser ma caméra",
    },
    "heatmap.video_btn": {
        LANG_EN: "Drop a video file",
        LANG_ZH: "拖入视频文件",
        LANG_ES: "Soltar un archivo de vídeo",
        LANG_FR: "Déposer une vidéo",
    },
    "heatmap.stop_btn": {
        LANG_EN: "Stop",
        LANG_ZH: "停止",
        LANG_ES: "Detener",
        LANG_FR: "Arrêter",
    },
    "heatmap.preview_title": {
        LANG_EN: "Camera feed",
        LANG_ZH: "摄像头画面",
        LANG_ES: "Señal de cámara",
        LANG_FR: "Flux caméra",
    },
    "heatmap.motion_watching": {
        LANG_EN: "Watching for motion…",
        LANG_ZH: "正在检测运动…",
        LANG_ES: "Buscando movimiento…",
        LANG_FR: "Détection de mouvement…",
    },
    "heatmap.camera_off": {
        LANG_EN: "Camera off · scene-default forecast.",
        LANG_ZH: "摄像头关闭 · 使用默认场景预测。",
        LANG_ES: "Cámara apagada · pronóstico por defecto.",
        LANG_FR: "Caméra éteinte · prévision par défaut.",
    },
    "heatmap.no_motion": {
        LANG_EN: (
            "Live · no motion detected. Try waving your hand or "
            "stepping side to side."
        ),
        LANG_ZH: "实时 · 未检测到运动。试着挥手或左右移动。",
        LANG_ES: (
            "En vivo · sin movimiento. Mueve la mano o desplázate de "
            "lado a lado."
        ),
        LANG_FR: (
            "En direct · aucun mouvement. Agitez la main ou "
            "déplacez-vous latéralement."
        ),
    },
    "heatmap.cell_hint": {
        LANG_EN: "Hover a cell to highlight it · click a cell for detail.",
        LANG_ZH: "悬停高亮单元格 · 点击查看详情。",
        LANG_ES: "Pasa el cursor para resaltar · haz clic para detalle.",
        LANG_FR: "Survolez pour surligner · cliquez pour le détail.",
    },
    "heatmap.axis_now": {
        LANG_EN: "now",
        LANG_ZH: "现在",
        LANG_ES: "ahora",
        LANG_FR: "maintenant",
    },
    "heatmap.iframe_camera_note": {
        LANG_EN: (
            "The live webcam is blocked inside this embedded panel "
            "(browser security). Drop a video file here — the motion "
            "detector runs on it exactly the same way — or use the "
            "Live webcam surface in the sidebar for direct capture."
        ),
        LANG_ZH: (
            "出于浏览器安全限制，嵌入式面板内无法直接调用实时摄像头。"
            "请在此拖入一个视频文件——运动检测会以完全相同的方式运行——"
            "或使用侧栏的实时摄像头入口进行直接采集。"
        ),
        LANG_ES: (
            "La webcam en vivo está bloqueada dentro de este panel "
            "incrustado (seguridad del navegador). Suelta un archivo de "
            "vídeo aquí — el detector de movimiento funciona igual — o "
            "usa la sección de webcam en vivo de la barra lateral."
        ),
        LANG_FR: (
            "La webcam en direct est bloquée dans ce panneau intégré "
            "(sécurité du navigateur). Déposez une vidéo ici — le "
            "détecteur de mouvement fonctionne pareil — ou utilisez la "
            "webcam en direct depuis la barre latérale."
        ),
    },
    "heatmap.idle_note": {
        LANG_EN: (
            "The grid is uniform — a world with no evidence yet. Run a "
            "prediction below, or drop a video to drive it live."
        ),
        LANG_ZH: (
            "网格是均匀的——一个还没有证据的世界。在下方运行一次预测，"
            "或拖入视频实时驱动它。"
        ),
        LANG_ES: (
            "La cuadrícula es uniforme — un mundo aún sin evidencia. "
            "Ejecuta una predicción abajo o suelta un vídeo para "
            "controlarla en vivo."
        ),
        LANG_FR: (
            "La grille est uniforme — un monde encore sans preuve. "
            "Lancez une prédiction ci-dessous, ou déposez une vidéo "
            "pour la piloter en direct."
        ),
    },
    "heatmap.live_note": {
        LANG_EN: (
            "The camera is driving the math — motion in the frame "
            "shifts the forecast live, with no submit click."
        ),
        LANG_ZH: "摄像头正在驱动计算——画面中的运动会实时改变预测，无需点击提交。",
        LANG_ES: (
            "La cámara controla el cálculo — el movimiento en el "
            "cuadro desplaza el pronóstico en vivo, sin pulsar enviar."
        ),
        LANG_FR: (
            "La caméra pilote le calcul — le mouvement dans l'image "
            "décale la prévision en direct, sans clic d'envoi."
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
        LANG_EN: "Two priors, one instrument.",
        LANG_ZH: "两种先验，一台仪器。",
        LANG_ES: "Dos priors, un instrumento.",
        LANG_FR: "Deux a priori, un instrument.",
    },
    "trad.hero.subtitle": {
        LANG_EN: (
            "Read the same prediction through a time-honored lens — "
            "八字, 占星, 易经, and Tarot all together, mapped onto one "
            "Nye Clock solar system. Each system is an explicitly "
            "weighted prior, never a verdict; the model's own number is "
            "always shown beside the 玄学-consensus one. Adjust the "
            "weight, watch the instrument move."
        ),
        LANG_ZH: (
            "用一种古法视角重读同一份预测——八字、占星、易经、"
            "塔罗一并纳入，映射到同一台 Nye Clock 太阳系仪器上。"
            "每一种体系都只是一个可调权重的先验，绝非定论；模型自己的"
            "数字始终与玄学共识数字并列展示。调权重，看仪器随之转动。"
        ),
        LANG_ES: (
            "Lee la misma predicción a través de una lente tradicional "
            "— 八字, 占星, 易经 y Tarot juntos, mapeados en un sistema "
            "solar Nye Clock. Cada sistema es un prior con peso "
            "explícito, nunca un veredicto; el número del modelo "
            "siempre se muestra junto al de consenso 玄学."
        ),
        LANG_FR: (
            "Lisez la même prédiction à travers une lentille "
            "traditionnelle — 八字, 占星, 易经 et Tarot réunis, "
            "projetés sur un système solaire Nye Clock. Chaque système "
            "est un prior pondéré explicitement, jamais un verdict ; le "
            "chiffre du modèle est toujours affiché à côté du consensus "
            "玄学."
        ),
    },
    "trad.birth.section": {
        LANG_EN: "Your birth",
        LANG_ZH: "出生信息",
        LANG_ES: "Tu nacimiento",
        LANG_FR: "Votre naissance",
    },
    "trad.system.label": {
        LANG_EN: "Divination system",
        LANG_ZH: "占卜体系",
        LANG_ES: "Sistema de adivinación",
        LANG_FR: "Système de divination",
    },
    "trad.system.bazi": {
        LANG_EN: "八字 BaZi",
        LANG_ZH: "八字",
        LANG_ES: "八字 BaZi",
        LANG_FR: "八字 BaZi",
    },
    "trad.system.ziwei": {
        LANG_EN: "紫微 ZiWei",
        LANG_ZH: "紫微斗数",
        LANG_ES: "紫微 ZiWei",
        LANG_FR: "紫微 ZiWei",
    },
    "trad.system.iching": {
        LANG_EN: "易经 I Ching",
        LANG_ZH: "易经",
        LANG_ES: "易经 I Ching",
        LANG_FR: "易经 Yi Jing",
    },
    "trad.system.tarot": {
        LANG_EN: "Tarot",
        LANG_ZH: "塔罗牌",
        LANG_ES: "Tarot",
        LANG_FR: "Tarot",
    },
    "trad.system.astro": {
        LANG_EN: "Astrology",
        LANG_ZH: "星座星盘",
        LANG_ES: "Astrología",
        LANG_FR: "Astrologie",
    },
    "trad.cast.hint": {
        LANG_EN: (
            "Cast deterministically from this prediction — the same "
            "prediction always yields the same reading. No birth data "
            "needed for this system."
        ),
        LANG_ZH: (
            "由这份预测确定性地起卦 / 抽牌——同一份预测每次结果相同。"
            "这个体系不需要出生信息。"
        ),
        LANG_ES: (
            "Se obtiene de forma determinista de esta predicción — la "
            "misma predicción siempre da la misma lectura. Este sistema "
            "no necesita datos de nacimiento."
        ),
        LANG_FR: (
            "Tiré de manière déterministe de cette prédiction — la même "
            "prédiction donne toujours la même lecture. Pas de données "
            "de naissance nécessaires."
        ),
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
    "trad.lens.in_output_note": {
        LANG_EN: (
            "玄学 lens on — switch to the 玄学 Nye Clock view with the "
            "toggle at the top of the output region above."
        ),
        LANG_ZH: (
            "玄学透镜已开启 —— 用上方输出区顶部的切换按钮即可切到"
            "玄学时轮视图。"
        ),
        LANG_ES: (
            "Lente 玄学 activada — cambia a la vista del Reloj Nye 玄学 "
            "con el conmutador en la parte superior de la salida."
        ),
        LANG_FR: (
            "Lentille 玄学 activée — basculez vers la vue de l'Horloge "
            "Nye 玄学 avec le commutateur en haut de la sortie."
        ),
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
