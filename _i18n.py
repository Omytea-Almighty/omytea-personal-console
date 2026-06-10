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
        # Iter #10: brand subtitle was technical positioning ("Probability-
        # calibrated decision support") — corporate-speak the stumbled-in
        # visitor doesn't parse. Replaced with a 4-word imperative that
        # describes the workflow: type → see. The workspace title "Your
        # futures" + the chips already do the heavy lifting; the tagline
        # just reinforces the verb-object pair.
        LANG_EN: "Type a decision · see its futures.",
        LANG_ZH: "写下一个决定 · 看见它的未来。",
        LANG_ES: "Escribe una decisión · ve sus futuros.",
        LANG_FR: "Écrivez une décision · voyez ses futurs.",
    },
    "brand.disclaimer": {
        # Iter #5 (design-self-explains): 3 lines of legal-ese in the
        # sidebar = forced reading. The first-time visitor doesn't
        # need to parse "calibrated future scenarios with
        # measurement-update feedback" to use the app. Trimmed to one
        # short line; the full legal copy lives in Privacy.
        LANG_EN: "Calibrated forecasts · not advice · see Privacy.",
        LANG_ZH: "校准过的概率预测 · 非建议 · 详见隐私政策。",
        LANG_ES: "Pronósticos calibrados · no es asesoría · ver Privacidad.",
        LANG_FR: "Prévisions calibrées · pas un conseil · voir Confidentialité.",
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
        LANG_EN: "New prediction",
        LANG_ZH: "新预测",
        LANG_ES: "Nueva predicción",
        LANG_FR: "Nouvelle prédiction",
    },
    "nav.history": {
        LANG_EN: "History",
        LANG_ZH: "历史",
        LANG_ES: "Historial",
        LANG_FR: "Historique",
    },
    "nav.history.empty": {
        # Iter #9: trimmed from "No predictions yet. Run one and it
        # appears here." — the empty list below the History eyebrow
        # IS the empty-state cue (no list items = no predictions).
        # Reading "run one and it appears here" instructs the user
        # what the design already shows.
        LANG_EN: "Your history will fill in here.",
        LANG_ZH: "你的历史会出现在这里。",
        LANG_ES: "Tu historial aparecerá aquí.",
        LANG_FR: "Votre historique apparaîtra ici.",
    },
    "nav.more": {
        LANG_EN: "More",
        LANG_ZH: "更多",
        LANG_ES: "Más",
        LANG_FR: "Plus",
    },
    "nav.more.hint": {
        LANG_EN: "Score past outcomes, your calibration record, and pricing.",
        LANG_ZH: "回填结果、查看校准记录、定价方案。",
        LANG_ES: "Evalúa resultados pasados, tu registro de calibración y precios.",
        LANG_FR: "Évaluez les résultats passés, votre calibration et les tarifs.",
    },
    "nav.settings": {
        LANG_EN: "Settings",
        LANG_ZH: "设置",
        LANG_ES: "Ajustes",
        LANG_FR: "Paramètres",
    },
    "nav.back_workspace": {
        LANG_EN: "←  Back to workspace",
        LANG_ZH: "←  返回工作区",
        LANG_ES: "←  Volver al espacio de trabajo",
        LANG_FR: "←  Retour à l'espace de travail",
    },
    "nav.settings_here": {
        LANG_EN: "⚙  You're in Settings",
        LANG_ZH: "⚙  已在设置页",
        LANG_ES: "⚙  Ya estás en Ajustes",
        LANG_FR: "⚙  Déjà dans les Paramètres",
    },
    # -----  Account / sign-in (sidebar bottom-left)  -----
    "account.login": {
        LANG_EN: "Log in  /  Sign up",
        LANG_ZH: "登录  /  注册",
        LANG_ES: "Iniciar sesión  /  Registrarse",
        LANG_FR: "Connexion  /  Inscription",
    },
    "account.login_hint": {
        LANG_EN: "Log in to save your prediction history across devices.",
        LANG_ZH: "登录后可跨设备保存你的预测历史。",
        LANG_ES: "Inicia sesión para guardar tu historial en todos tus dispositivos.",
        LANG_FR: "Connectez-vous pour enregistrer votre historique sur vos appareils.",
    },
    "account.logout": {
        LANG_EN: "Log out",
        LANG_ZH: "退出登录",
        LANG_ES: "Cerrar sesión",
        LANG_FR: "Se déconnecter",
    },
    "account.not_configured": {
        LANG_EN: "Google sign-in isn't set up yet — add the OIDC secrets to enable it.",
        LANG_ZH: "Google 登录尚未配置 —— 填入 OIDC secrets 后即可启用。",
        LANG_ES: "El inicio de sesión con Google aún no está configurado: añade los secretos OIDC.",
        LANG_FR: "La connexion Google n'est pas encore configurée — ajoutez les secrets OIDC.",
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
    # -----  Settings surface — categories, descriptions, About  -----
    "settings.subtitle": {
        LANG_EN: "Language, model, personalization — the levers behind every prediction.",
        LANG_ZH: "语言、模型、个性化 —— 每一次预测背后的调节项。",
        LANG_ES: "Idioma, modelo, personalización: las palancas detrás de cada predicción.",
        LANG_FR: "Langue, modèle, personnalisation — les leviers de chaque prédiction.",
    },
    "settings.cat.general": {
        LANG_EN: "General",
        LANG_ZH: "通用",
        LANG_ES: "General",
        LANG_FR: "Général",
    },
    "settings.cat.prediction": {
        LANG_EN: "Prediction defaults",
        LANG_ZH: "预测默认值",
        LANG_ES: "Predicción",
        LANG_FR: "Prédiction",
    },
    "settings.cat.model": {
        LANG_EN: "Model & API",
        LANG_ZH: "模型与 API",
        LANG_ES: "Modelo y API",
        LANG_FR: "Modèle et API",
    },
    "settings.cat.personalization": {
        LANG_EN: "Personalization",
        LANG_ZH: "个性化",
        LANG_ES: "Personalización",
        LANG_FR: "Personnalisation",
    },
    "settings.cat.data": {
        LANG_EN: "Data & privacy",
        LANG_ZH: "数据与隐私",
        LANG_ES: "Datos y privacidad",
        LANG_FR: "Données et confidentialité",
    },
    "settings.cat.about": {
        LANG_EN: "About",
        LANG_ZH: "关于",
        LANG_ES: "Acerca de",
        LANG_FR: "À propos",
    },
    "settings.general.desc": {
        LANG_EN: "Display language, region, and how prices appear across the console.",
        LANG_ZH: "显示语言、地区，以及价格在控制台中的呈现方式。",
        LANG_ES: "Idioma de la interfaz, región y cómo se muestran los precios en la consola.",
        LANG_FR: "Langue d'affichage, région et présentation des prix dans la console.",
    },
    "settings.prediction.desc": {
        LANG_EN: "Defaults the composer starts from on every new prediction — set them once, reuse them every time.",
        LANG_ZH: "撰写新预测时编排器默认采用的初始值 —— 设一次，之后每次复用。",
        LANG_ES: "Valores con los que el compositor arranca en cada nueva predicción: configúralos una vez.",
        LANG_FR: "Les valeurs de départ du compositeur à chaque nouvelle prédiction — réglez-les une fois.",
    },
    "settings.prediction.horizon": {
        LANG_EN: "Default time horizon",
        LANG_ZH: "默认时间跨度",
        LANG_ES: "Horizonte temporal por defecto",
        LANG_FR: "Horizon temporel par défaut",
    },
    "settings.prediction.horizon.help": {
        LANG_EN: "Seeds the composer's time-horizon field. You can still change it on any individual prediction.",
        LANG_ZH: "为编排器的时间跨度字段设定初始值。单次预测仍可随时更改。",
        LANG_ES: "Define el valor inicial del horizonte en el compositor. Puedes cambiarlo en cada predicción.",
        LANG_FR: "Initialise le champ d'horizon du compositeur. Vous pouvez le modifier sur chaque prédiction.",
    },
    "settings.prediction.lens": {
        LANG_EN: "Start with the Metaphysics lens on",
        LANG_ZH: "默认开启玄学透镜",
        LANG_ES: "Empezar con la lente metafísica activada",
        LANG_FR: "Démarrer avec la loupe métaphysique activée",
    },
    "settings.prediction.lens.help": {
        LANG_EN: "When on, every new prediction opens with the Metaphysics lens already enabled in the composer.",
        LANG_ZH: "开启后，每次新预测都会在编排器中默认启用玄学透镜。",
        LANG_ES: "Si está activado, cada predicción se abre con la lente metafísica ya activada en el compositor.",
        LANG_FR: "Si activé, chaque prédiction s'ouvre avec la loupe métaphysique déjà activée dans le compositeur.",
    },
    "settings.model.desc": {
        LANG_EN: "Choose the LLM backend and supply your own API keys for power-user models.",
        LANG_ZH: "选择 LLM 后端，并为高级模型填入你自己的 API 密钥。",
        LANG_ES: "Elige el backend LLM y aporta tus propias claves API para modelos avanzados.",
        LANG_FR: "Choisissez le backend LLM et fournissez vos propres clés API pour les modèles avancés.",
    },
    "settings.model.backend.label": {
        LANG_EN: "LLM backend",
        LANG_ZH: "LLM 后端",
        LANG_ES: "Backend LLM",
        LANG_FR: "Backend LLM",
    },
    "settings.model.backend.help": {
        LANG_EN: "Default rotates across free-tier providers. Pick a specific backend to pin it; supply your key below.",
        LANG_ZH: "默认在多个免费后端之间自动轮转。选择具体后端则固定使用它，并在下方填入你的 API 密钥。",
        LANG_ES: "Por defecto, rota entre proveedores de capa gratuita. Selecciona uno específico para fijarlo y proporciona la clave abajo.",
        LANG_FR: "Par défaut, alterne entre les fournisseurs en tier gratuit. Choisissez-en un pour le fixer ; fournissez votre clé en dessous.",
    },
    "settings.model.backend.default": {
        LANG_EN: "Default · rotates free-tier providers",
        LANG_ZH: "默认 · 自动轮转免费后端",
        LANG_ES: "Por defecto · rota proveedores gratuitos",
        LANG_FR: "Par défaut · alterne les fournisseurs gratuits",
    },
    "settings.model.backend.ollama": {
        LANG_EN: "Ollama · local",
        LANG_ZH: "Ollama · 本地",
        LANG_ES: "Ollama · local",
        LANG_FR: "Ollama · local",
    },
    "settings.model.backend.anthropic": {
        LANG_EN: "Anthropic · Claude",
        LANG_ZH: "Anthropic · Claude",
        LANG_ES: "Anthropic · Claude",
        LANG_FR: "Anthropic · Claude",
    },
    "settings.model.backend.groq": {
        LANG_EN: "Groq · fast inference",
        LANG_ZH: "Groq · 高速推理",
        LANG_ES: "Groq · inferencia rápida",
        LANG_FR: "Groq · inférence rapide",
    },
    "settings.model.backend.openai": {
        LANG_EN: "OpenAI · GPT-4 / GPT-5",
        LANG_ZH: "OpenAI · GPT-4 / GPT-5",
        LANG_ES: "OpenAI · GPT-4 / GPT-5",
        LANG_FR: "OpenAI · GPT-4 / GPT-5",
    },
    "settings.model.api_key.label": {
        LANG_EN: "API key",
        LANG_ZH: "API 密钥",
        LANG_ES: "Clave API",
        LANG_FR: "Clé API",
    },
    "settings.model.api_key.help": {
        LANG_EN: "Lives only in this browser session. Never written to disk, never logged, never sent anywhere except the provider's API.",
        LANG_ZH: "只保存在当前浏览器会话中。不写入磁盘、不记录日志、除了发给对应的 API 提供商外不会发往任何地方。",
        LANG_ES: "Sólo en esta sesión del navegador. Nunca se escribe en disco ni se envía a ningún otro sitio.",
        LANG_FR: "Vit uniquement dans cette session du navigateur. Jamais écrit sur disque, jamais envoyé ailleurs.",
    },
    "settings.model.ollama_url.label": {
        LANG_EN: "Ollama URL",
        LANG_ZH: "Ollama 地址",
        LANG_ES: "URL de Ollama",
        LANG_FR: "URL d'Ollama",
    },
    "settings.model.ollama_url.help": {
        LANG_EN: "Local Ollama server URL. Default works for an Ollama install on the same machine.",
        LANG_ZH: "本地 Ollama 服务地址。默认值适用于同机部署。",
        LANG_ES: "URL del servidor Ollama local. El valor por defecto sirve para una instalación en la misma máquina.",
        LANG_FR: "URL du serveur Ollama local. La valeur par défaut convient à une installation locale.",
    },
    "settings.model.status.default": {
        LANG_EN: "Default rotation active — no key required.",
        LANG_ZH: "正在使用默认轮转 —— 无需 API 密钥。",
        LANG_ES: "Rotación por defecto activa — no se requiere clave.",
        LANG_FR: "Rotation par défaut active — pas de clé requise.",
    },
    "settings.model.status.pinned": {
        LANG_EN: "Backend pinned for this session. Key (if any) is held in memory only.",
        LANG_ZH: "本次会话已固定后端。密钥（若有）仅保存在内存中。",
        LANG_ES: "Backend fijado para esta sesión. La clave (si la hay) sólo se guarda en memoria.",
        LANG_FR: "Backend fixé pour cette session. La clé (si présente) reste en mémoire uniquement.",
    },
    "settings.personalization.desc": {
        LANG_EN: "A display name, a standing context the model reuses, the readout tone — and your birth data when the Metaphysics lens is on.",
        LANG_ZH: "显示名称、模型可复用的固定背景信息、解读语气，以及打开玄学透镜时使用的出生信息。",
        LANG_ES: "Un nombre visible, un contexto permanente que el modelo reutiliza, el tono de lectura — y tus datos de nacimiento cuando la lente metafísica está activa.",
        LANG_FR: "Un nom affiché, un contexte permanent réutilisé par le modèle, le ton de lecture — et vos données de naissance lorsque la loupe métaphysique est active.",
    },
    "settings.personalization.section.profile": {
        LANG_EN: "Profile",
        LANG_ZH: "个人资料",
        LANG_ES: "Perfil",
        LANG_FR: "Profil",
    },
    "settings.personalization.section.tone": {
        LANG_EN: "Readout",
        LANG_ZH: "解读",
        LANG_ES: "Lectura",
        LANG_FR: "Lecture",
    },
    "settings.personalization.section.birth": {
        LANG_EN: "Birth data — for the Metaphysics lens",
        LANG_ZH: "出生信息 —— 用于玄学透镜",
        LANG_ES: "Datos de nacimiento — para la lente metafísica",
        LANG_FR: "Données de naissance — pour la loupe métaphysique",
    },
    "settings.personalization.display_name": {
        LANG_EN: "Display name",
        LANG_ZH: "显示名称",
        LANG_ES: "Nombre visible",
        LANG_FR: "Nom affiché",
    },
    "settings.personalization.display_name.placeholder": {
        LANG_EN: "What we call you in the readout",
        LANG_ZH: "解读时如何称呼你",
        LANG_ES: "Cómo te llamamos en la lectura",
        LANG_FR: "Comment vous appeler dans la lecture",
    },
    "settings.personalization.display_name.help": {
        LANG_EN: "Used in the readout greeting. Defaults to your sign-in name when blank.",
        LANG_ZH: "用于解读开头的称呼。留空时默认采用你的登录名。",
        LANG_ES: "Se usa en el saludo de la lectura. Por defecto, tu nombre de inicio de sesión.",
        LANG_FR: "Utilisé dans la salutation de la lecture. Par défaut, votre nom de connexion.",
    },
    "settings.personalization.about_you": {
        LANG_EN: "About you",
        LANG_ZH: "关于你",
        LANG_ES: "Sobre ti",
        LANG_FR: "À propos de vous",
    },
    "settings.personalization.about_you.placeholder": {
        LANG_EN: "A few sentences the model reuses across predictions — your age, your work, what shapes your decisions.",
        LANG_ZH: "几句话，模型会在每次预测中复用——你的年龄、职业，以及影响你决策的因素。",
        LANG_ES: "Unas frases que el modelo reutiliza en cada predicción — tu edad, tu trabajo, lo que da forma a tus decisiones.",
        LANG_FR: "Quelques phrases que le modèle réutilise à chaque prédiction — votre âge, votre travail, ce qui forme vos décisions.",
    },
    "settings.personalization.about_you.help": {
        LANG_EN: "Reused as standing context on every prediction. Edit freely; it stays in this browser session only.",
        LANG_ZH: "作为固定背景，在每次预测中复用。可随时编辑；仅保存在当前浏览器会话中。",
        LANG_ES: "Reutilizado como contexto permanente en cada predicción. Edítalo libremente; sólo se guarda en esta sesión del navegador.",
        LANG_FR: "Réutilisé comme contexte permanent à chaque prédiction. Modifiez-le librement ; conservé uniquement dans cette session du navigateur.",
    },
    "settings.personalization.tone": {
        LANG_EN: "Readout tone",
        LANG_ZH: "解读语气",
        LANG_ES: "Tono de la lectura",
        LANG_FR: "Ton de la lecture",
    },
    "settings.personalization.tone.plain": {
        LANG_EN: "Plain — analytical",
        LANG_ZH: "平实 —— 分析式",
        LANG_ES: "Plano — analítico",
        LANG_FR: "Sobre — analytique",
    },
    "settings.personalization.tone.calibrated": {
        LANG_EN: "Calibrated — explicit uncertainty",
        LANG_ZH: "校准 —— 明确表达不确定性",
        LANG_ES: "Calibrado — incertidumbre explícita",
        LANG_FR: "Calibré — incertitude explicite",
    },
    "settings.personalization.tone.warm": {
        LANG_EN: "Warm — first-person concern",
        LANG_ZH: "温暖 —— 第一人称的关切",
        LANG_ES: "Cálido — preocupación en primera persona",
        LANG_FR: "Chaleureux — préoccupation à la première personne",
    },
    "settings.personalization.tone.help": {
        LANG_EN: "How the readout addresses you. Plain reads as a report; Calibrated foregrounds the probability language; Warm uses first-person concern.",
        LANG_ZH: "解读如何与你对话。平实如同报告；校准更强调概率措辞；温暖以第一人称的关切书写。",
        LANG_ES: "Cómo se dirige la lectura a ti. Plano se lee como un informe; Calibrado destaca el lenguaje probabilístico; Cálido usa la primera persona.",
        LANG_FR: "Comment la lecture s'adresse à vous. Sobre se lit comme un rapport ; Calibré met en avant le langage probabiliste ; Chaleureux à la première personne.",
    },
    "settings.personalization.birth.toggle": {
        LANG_EN: "Use my birth data in the Metaphysics lens",
        LANG_ZH: "在玄学透镜中使用我的出生信息",
        LANG_ES: "Usar mis datos de nacimiento en la lente metafísica",
        LANG_FR: "Utiliser mes données de naissance dans la loupe métaphysique",
    },
    "settings.personalization.birth.toggle.help": {
        LANG_EN: "When on, BaZi · ZiWei · ascendant are computed from your birth data. When off, those modules show a sample reading and a small 'set birth in Settings' hint.",
        LANG_ZH: "开启后，八字、紫薇与上升星座会基于你的出生信息推算。关闭时这些模块会显示样例解读以及一条「请到设置中填写出生信息」的提示。",
        LANG_ES: "Si está activo, BaZi · ZiWei · ascendente se calculan con tus datos. Si está apagado, esos módulos muestran una lectura de muestra.",
        LANG_FR: "Activé : BaZi · ZiWei · ascendant sont calculés à partir de vos données. Désactivé : ces modules affichent une lecture exemple.",
    },
    "settings.personalization.birth.city": {
        LANG_EN: "Birth city (optional)",
        LANG_ZH: "出生城市（可选）",
        LANG_ES: "Ciudad de nacimiento (opcional)",
        LANG_FR: "Ville de naissance (optionnel)",
    },
    "settings.personalization.birth.city.placeholder": {
        LANG_EN: "e.g. Shanghai · Beijing · New York",
        LANG_ZH: "如 上海 · 北京 · 纽约",
        LANG_ES: "p. ej. Shanghái · Pekín · Nueva York",
        LANG_FR: "p. ex. Shanghai · Pékin · New York",
    },
    "settings.personalization.birth.city.help": {
        LANG_EN: "Optional. Free text — used only to compute the rising sign when supported. Never geocoded server-side.",
        LANG_ZH: "可选。自由文本——仅在支持的模块中用于推算上升星座，不会在服务端做地理编码。",
        LANG_ES: "Opcional. Texto libre — sólo se usa para calcular el signo ascendente cuando es posible.",
        LANG_FR: "Optionnel. Texte libre — utilisé uniquement pour calculer le signe ascendant lorsque c'est possible.",
    },
    "settings.personalization.birth.privacy": {
        LANG_EN: "Birth data lives only in this browser session. It is never written to disk, never logged, and never sent off-device.",
        LANG_ZH: "出生信息只保存在当前浏览器会话中，不会写入磁盘，不会被日志记录，也不会离开你的设备。",
        LANG_ES: "Los datos de nacimiento sólo viven en esta sesión del navegador. Nunca se escriben en disco ni se envían fuera del dispositivo.",
        LANG_FR: "Les données de naissance ne vivent que dans cette session du navigateur. Jamais écrites sur disque, jamais envoyées hors de l'appareil.",
    },
    "settings.personalization.birth.unset_hint": {
        LANG_EN: "Set your birth data in Settings → Personalization to enable BaZi · ZiWei · ascendant. The other modules still work without it.",
        LANG_ZH: "在「设置 → 个性化」中填写出生信息后即可启用 八字、紫薇、上升星座。其余模块无须出生信息也能正常工作。",
        LANG_ES: "Configura tus datos de nacimiento en Ajustes → Personalización para activar BaZi · ZiWei · ascendente. Los demás módulos funcionan sin ellos.",
        LANG_FR: "Renseignez vos données de naissance dans Paramètres → Personnalisation pour activer BaZi · ZiWei · ascendant. Les autres modules fonctionnent sans elles.",
    },
    "settings.data.desc": {
        LANG_EN: "Export your prediction history, clear it, and see how your data is stored.",
        LANG_ZH: "导出你的预测历史、清空历史，并了解你的数据如何存储。",
        LANG_ES: "Exporta tu historial de predicciones, bórralo y consulta cómo se almacenan tus datos.",
        LANG_FR: "Exportez votre historique de prédictions, effacez-le et voyez comment vos données sont stockées.",
    },
    "settings.data.export.title": {
        LANG_EN: "Export your data",
        LANG_ZH: "导出你的数据",
        LANG_ES: "Exporta tus datos",
        LANG_FR: "Exporter vos données",
    },
    "settings.data.export.help": {
        LANG_EN: "Download every prediction you have run — CSV for a quick table, JSON for the full record.",
        LANG_ZH: "下载你运行过的每一条预测 —— CSV 是速览表格，JSON 是完整记录。",
        LANG_ES: "Descarga todas tus predicciones: CSV para una tabla rápida, JSON para el registro completo.",
        LANG_FR: "Téléchargez toutes vos prédictions — CSV pour un tableau rapide, JSON pour l'enregistrement complet.",
    },
    "settings.data.export.csv": {
        LANG_EN: "Download CSV",
        LANG_ZH: "下载 CSV",
        LANG_ES: "Descargar CSV",
        LANG_FR: "Télécharger le CSV",
    },
    "settings.data.export.json": {
        LANG_EN: "Download JSON",
        LANG_ZH: "下载 JSON",
        LANG_ES: "Descargar JSON",
        LANG_FR: "Télécharger le JSON",
    },
    "settings.data.empty": {
        LANG_EN: "No predictions yet — nothing to export.",
        LANG_ZH: "还没有预测 —— 暂无可导出的内容。",
        LANG_ES: "Aún no hay predicciones: nada que exportar.",
        LANG_FR: "Pas encore de prédictions — rien à exporter.",
    },
    "settings.data.clear.title": {
        LANG_EN: "Clear prediction history",
        LANG_ZH: "清除预测历史",
        LANG_ES: "Borrar el historial de predicciones",
        LANG_FR: "Effacer l'historique de prédictions",
    },
    "settings.data.clear.help": {
        LANG_EN: "Permanently remove every prediction tied to this handle. This cannot be undone.",
        LANG_ZH: "永久删除与当前账户关联的所有预测。此操作无法撤销。",
        LANG_ES: "Elimina permanentemente todas las predicciones de esta cuenta. No se puede deshacer.",
        LANG_FR: "Supprime définitivement toutes les prédictions liées à ce compte. Action irréversible.",
    },
    "settings.data.clear.btn": {
        LANG_EN: "Clear history",
        LANG_ZH: "清除历史",
        LANG_ES: "Borrar historial",
        LANG_FR: "Effacer l'historique",
    },
    "settings.data.clear.confirm": {
        LANG_EN: "Permanently delete all {n} predictions? This cannot be undone.",
        LANG_ZH: "确定永久删除全部 {n} 条预测吗？此操作无法撤销。",
        LANG_ES: "¿Eliminar permanentemente las {n} predicciones? No se puede deshacer.",
        LANG_FR: "Supprimer définitivement les {n} prédictions ? Action irréversible.",
    },
    "settings.data.clear.yes": {
        LANG_EN: "Yes, clear everything",
        LANG_ZH: "是，全部清除",
        LANG_ES: "Sí, borrar todo",
        LANG_FR: "Oui, tout effacer",
    },
    "settings.data.clear.cancel": {
        LANG_EN: "Cancel",
        LANG_ZH: "取消",
        LANG_ES: "Cancelar",
        LANG_FR: "Annuler",
    },
    "settings.data.clear.done": {
        LANG_EN: "Cleared {n} prediction(s).",
        LANG_ZH: "已清除 {n} 条预测。",
        LANG_ES: "Se borraron {n} predicciones.",
        LANG_FR: "{n} prédiction(s) effacée(s).",
    },
    "settings.data.note": {
        LANG_EN: "Predictions are kept in a SQLite database on the app server. Streamlit Cloud's filesystem is ephemeral — the history is also wiped automatically whenever the app restarts. Durable per-account storage is on the roadmap.",
        LANG_ZH: "预测保存在应用服务器的 SQLite 数据库中。Streamlit Cloud 的文件系统是临时的 —— 应用每次重启时历史也会被自动清空。持久化的按账户存储仍在规划中。",
        LANG_ES: "Las predicciones se guardan en una base de datos SQLite en el servidor. El sistema de archivos de Streamlit Cloud es efímero: el historial también se borra al reiniciarse la app. El almacenamiento duradero por cuenta está en la hoja de ruta.",
        LANG_FR: "Les prédictions sont stockées dans une base SQLite sur le serveur. Le système de fichiers de Streamlit Cloud est éphémère — l'historique est aussi effacé à chaque redémarrage de l'app. Un stockage durable par compte est prévu.",
    },
    "settings.planned.badge": {
        LANG_EN: "Planned",
        LANG_ZH: "规划中",
        LANG_ES: "Previsto",
        LANG_FR: "Prévu",
    },
    "settings.planned.note": {
        LANG_EN: "This section is on the Settings roadmap and arrives in an upcoming update. The line above describes what it will hold — there are no placeholder controls.",
        LANG_ZH: "本板块已列入设置路线图，将在后续更新中上线。上方一行说明它将包含的内容 —— 此处没有任何占位控件。",
        LANG_ES: "Esta sección está en la hoja de ruta de Ajustes y llegará en una próxima actualización. La línea anterior describe su contenido; no hay controles de relleno.",
        LANG_FR: "Cette section figure sur la feuille de route des Paramètres et arrivera bientôt. La ligne ci-dessus décrit son contenu ; aucun contrôle factice ici.",
    },
    "settings.currency.help": {
        LANG_EN: "Affects price displays in Pricing. Billing currency stays USD; non-USD displays are approximate.",
        LANG_ZH: "影响定价页面中的价格显示。结算货币仍为美元；非美元显示为近似值。",
        LANG_ES: "Afecta a los precios mostrados en Precios. La facturación sigue en USD; las demás divisas son aproximadas.",
        LANG_FR: "Affecte l'affichage des prix dans Tarifs. La facturation reste en USD ; les autres devises sont approximatives.",
    },
    "settings.about.what": {
        LANG_EN: "Omytea Console is a probability-calibrated decision-support tool. It maps a decision into branching futures with explicit probabilities — it is not a deterministic oracle and does not tell you what will happen.",
        LANG_ZH: "Omytea Console 是一款经概率校准的决策支持工具。它把一个决策展开为带明确概率的分支未来 —— 它不是确定性的预言机，也不会告诉你必然会发生什么。",
        LANG_ES: "Omytea Console es una herramienta de apoyo a la decisión calibrada por probabilidad. Convierte una decisión en futuros ramificados con probabilidades explícitas; no es un oráculo determinista.",
        LANG_FR: "Omytea Console est un outil d'aide à la décision calibré en probabilité. Il transforme une décision en futurs ramifiés avec des probabilités explicites ; ce n'est pas un oracle déterministe.",
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
    # Iter #30 — composer folds into this expander after a prediction
    # is rendered, so the result page's attention stays on the
    # story/evidence/revisit-reminder. Founder round-2 audit ask.
    "composer.edit_and_rerun": {
        LANG_EN: "Edit inputs and re-run",
        LANG_ZH: "编辑输入并重新预测",
        LANG_ES: "Editar entradas y volver a ejecutar",
        LANG_FR: "Modifier les entrées et relancer",
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
    "composer.live.active_note": {
        LANG_EN: (
            "Live video is on — it is running in the output region "
            "above (camera, motion loop and live heatmap together). "
            "Toggle off to return to the prediction heatmap."
        ),
        LANG_ZH: (
            "实时视频已开启——正在上方输出区运行（摄像头、运动检测循环"
            "与实时热力图协同）。关闭开关即可返回预测热力图。"
        ),
        LANG_ES: (
            "El video en vivo está activado — se ejecuta en la región "
            "de salida de arriba (cámara, bucle de movimiento y mapa "
            "de calor en vivo juntos). Desactívalo para volver al mapa "
            "de calor de predicción."
        ),
        LANG_FR: (
            "La vidéo en direct est activée — elle s'exécute dans la "
            "région de sortie ci-dessus (caméra, boucle de mouvement et "
            "carte de chaleur en direct ensemble). Désactivez pour "
            "revenir à la carte de chaleur de prédiction."
        ),
    },
    "live_video.embed_caption": {
        LANG_EN: (
            "Live perception — camera, pixel-diff motion loop and live "
            "heatmap, running together in one frame. Start the camera "
            "inside the panel and allow access when your browser asks."
        ),
        LANG_ZH: (
            "实时感知——摄像头、像素差分运动循环与实时热力图在同一画面中"
            "协同运行。在面板内启动摄像头，并在浏览器询问时允许访问。"
        ),
        LANG_ES: (
            "Percepción en vivo — cámara, bucle de movimiento por "
            "diferencia de píxeles y mapa de calor en vivo, juntos en un "
            "solo marco. Inicia la cámara dentro del panel y permite el "
            "acceso cuando el navegador lo pida."
        ),
        LANG_FR: (
            "Perception en direct — caméra, boucle de mouvement par "
            "différence de pixels et carte de chaleur en direct, "
            "ensemble dans un seul cadre. Démarrez la caméra dans le "
            "panneau et autorisez l'accès quand le navigateur le "
            "demande."
        ),
    },
    "composer.lens": {
        # Iter #11: composer toggle label shortened so it fits one
        # line in the now-narrow modality column (iter #4 cut it from
        # full-width to left-third). "Metaphysics lens" wrapped to
        # two lines. "Lens" alone reads as the affordance label;
        # tooltip still says "Metaphysics lens" via the help= text
        # for users hovering for context.
        LANG_EN: "Lens",
        LANG_ZH: "透镜",
        LANG_ES: "Lente",
        LANG_FR: "Loupe",
    },
    # Iter #48 — chip-loaded toast. Immediate confirmation a
    # suggestion chip filled the form, so a user on the slow
    # free-tier server doesn't click again or submit before the
    # fields paint (which caused a confusing "Missing required
    # field" error).
    "composer.chip_loaded": {
        LANG_EN: "✓ Example loaded — review below, then “See my futures →”",
        LANG_ZH: "✓ 示例已填入 — 往下看一眼，再点“See my futures →”",
        LANG_ES: "✓ Ejemplo cargado — revisa abajo y pulsa “See my futures →”",
        LANG_FR: "✓ Exemple chargé — vérifiez ci-dessous, puis « See my futures → »",
    },
    "composer.more_fields": {
        LANG_EN: "More details (optional)",
        LANG_ZH: "更多字段（可选）",
        LANG_ES: "Más detalles (opcional)",
        LANG_FR: "Plus de détails (facultatif)",
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
        # Iter #6: "Generate prediction" is operational language. Renamed
        # to a destination phrase — what the user GETS by clicking, not
        # what the system DOES. ChatGPT calls it "Send", we name the
        # outcome.
        LANG_EN: "See my futures →",
        LANG_ZH: "查看我的未来 →",
        LANG_ES: "Ver mis futuros →",
        LANG_FR: "Voir mes futurs →",
    },
    "new.generating": {
        # Iter #50: the generate wait is 10-25s on the free-tier host.
        # The old hard-coded English spinner ("Compiling input →
        # BeliefProgram → hypothesis space…") leaked internal jargon and
        # was never localised, so a non-EN beta tester saw English tech-
        # speak freeze for 15s and read it as broken. Plain language +
        # "a few seconds" sets the expectation that the wait is normal.
        LANG_EN: "Reading your inputs and simulating the futures — this can take a few seconds…",
        LANG_ZH: "正在读取你的输入、推演各种未来——可能需要几秒钟……",
        LANG_ES: "Leyendo tus datos y simulando los futuros — esto puede tardar unos segundos…",
        LANG_FR: "Lecture de vos données et simulation des futurs — cela peut prendre quelques secondes…",
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
    # -----  Engine receipt (iter #51) — prove a real model computed this  -----
    "result.engine.headline": {
        LANG_EN: "Computed live by the Omytea world-model engine — not a template.",
        LANG_ZH: "由 Omytea 世界模型引擎实时计算——不是套模板。",
        LANG_ES: "Calculado en vivo por el motor de modelo del mundo de Omytea — no es una plantilla.",
        LANG_FR: "Calculé en direct par le moteur de modèle du monde d'Omytea — pas un gabarit.",
    },
    "result.engine.m_branches": {
        LANG_EN: "Futures mapped",
        LANG_ZH: "推演的未来",
        LANG_ES: "Futuros mapeados",
        LANG_FR: "Futurs cartographiés",
    },
    "result.engine.m_links": {
        LANG_EN: "Correlated links",
        LANG_ZH: "关联链接",
        LANG_ES: "Vínculos correlados",
        LANG_FR: "Liens corrélés",
    },
    "result.engine.m_substrate": {
        LANG_EN: "Engine",
        LANG_ZH: "引擎",
        LANG_ES: "Motor",
        LANG_FR: "Moteur",
    },
    "result.engine.substrate_on": {
        LANG_EN: "Omytea ρ",
        LANG_ZH: "Omytea ρ",
        LANG_ES: "Omytea ρ",
        LANG_FR: "Omytea ρ",
    },
    "result.engine.substrate_off": {
        LANG_EN: "Omytea",
        LANG_ZH: "Omytea",
        LANG_ES: "Omytea",
        LANG_FR: "Omytea",
    },
    "result.engine.expander": {
        LANG_EN: "How we worked this out",
        LANG_ZH: "我们是怎么算出来的",
        LANG_ES: "Cómo lo calculamos",
        LANG_FR: "Comment nous avons calculé cela",
    },
    # Iter #50 — result-page view-mode options. Were hardcoded English in
    # app.py, so ZH/ES/FR users saw English labels mid-result. Localized
    # here; app.py branches off the stable key, not the localized label.
    "result.view.story": {
        LANG_EN: "Story",
        LANG_ZH: "故事",
        LANG_ES: "Relato",
        LANG_FR: "Récit",
    },
    "result.view.comparison": {
        LANG_EN: "Comparison table",
        LANG_ZH: "对比表",
        LANG_ES: "Tabla comparativa",
        LANG_FR: "Tableau comparatif",
    },
    "result.view.timeline": {
        LANG_EN: "Decision timeline",
        LANG_ZH: "决策时间线",
        LANG_ES: "Cronología de decisión",
        LANG_FR: "Chronologie de décision",
    },
    "result.view.continuous": {
        LANG_EN: "Continuous distribution",
        LANG_ZH: "连续分布",
        LANG_ES: "Distribución continua",
        LANG_FR: "Distribution continue",
    },
    # Iter #53 — the view-RENDERER headings (shown after the iter-50 radio
    # switches view). iter-50 localized the radio chips but these headings
    # stayed English, so a zh user picking 对比表 landed on an English
    # "Branch comparison table" heading. Localized to match the chips.
    "result.view.comparison_title": {
        LANG_EN: "Branch comparison table",
        LANG_ZH: "分支对比表",
        LANG_ES: "Tabla comparativa de ramas",
        LANG_FR: "Tableau comparatif des branches",
    },
    "result.view.timeline_title": {
        LANG_EN: "Decision timeline",
        LANG_ZH: "决策时间线",
        LANG_ES: "Cronología de la decisión",
        LANG_FR: "Chronologie de la décision",
    },
    "result.view.continuous_title": {
        LANG_EN: "Continuous probability density over time",
        LANG_ZH: "随时间变化的连续概率密度",
        LANG_ES: "Densidad de probabilidad continua en el tiempo",
        LANG_FR: "Densité de probabilité continue dans le temps",
    },
    # Iter #51 — result-page "Technical details" expander (the joint
    # off-diagonal correlation + Lindblad coherence-decay section). Was
    # hardcoded English in app.py, so zh/es/fr users opening it saw English
    # in the one place the physics machinery shows. Localized here.
    "result.tech.expander": {
        LANG_EN: "Technical details · joint structure & coherence decay",
        LANG_ZH: "技术细节 · 联合结构与相干衰减",
        LANG_ES: "Detalles técnicos · estructura conjunta y decaimiento de coherencia",
        LANG_FR: "Détails techniques · structure conjointe et décroissance de cohérence",
    },
    "result.tech.caption": {
        LANG_EN: "Advanced view. Most users can skip this — the story, probabilities, and evidence above already answer the question. Open this only if you want the underlying correlation structure and how it relaxes over time.",
        LANG_ZH: "进阶视图。多数人可以跳过——上面的叙述、概率与证据已经回答了问题。只有当你想看底层的关联结构、以及它如何随时间松弛时，才需要展开。",
        LANG_ES: "Vista avanzada. La mayoría puede omitirla: el relato, las probabilidades y la evidencia de arriba ya responden la pregunta. Ábrela solo si quieres la estructura de correlación subyacente y cómo se relaja con el tiempo.",
        LANG_FR: "Vue avancée. La plupart peuvent l'ignorer : le récit, les probabilités et les preuves ci-dessus répondent déjà à la question. Ne l'ouvrez que si vous voulez la structure de corrélation sous-jacente et comment elle se relâche au fil du temps.",
    },
    "result.tech.joint_subheader": {
        LANG_EN: "Joint hypothesis correlations",
        LANG_ZH: "联合假设关联",
        LANG_ES: "Correlaciones de hipótesis conjuntas",
        LANG_FR: "Corrélations d'hypothèses conjointes",
    },
    "result.tech.joint_caption": {
        LANG_EN: "How different futures are correlated. Positive = tend to co-occur. Negative = mutually exclusive.",
        LANG_ZH: "不同未来之间如何关联。正值 ＝ 倾向同时发生；负值 ＝ 互斥。",
        LANG_ES: "Cómo se correlacionan los distintos futuros. Positivo = tienden a coexistir. Negativo = mutuamente excluyentes.",
        LANG_FR: "Comment les différents futurs sont corrélés. Positif = tendent à coexister. Négatif = mutuellement exclusifs.",
    },
    # Iter #52 — result-page "Recommended evidence to collect" section. Was
    # hardcoded English in app.py (subheader + caption + per-item "Most
    # affects" + "Expected ΔP" metric label), so zh/es/fr users saw English.
    # Localized here; same bug-051/052 class.
    "result.evidence.subheader": {
        LANG_EN: "Recommended evidence to collect",
        LANG_ZH: "建议收集的证据",
        LANG_ES: "Evidencia recomendada para recopilar",
        LANG_FR: "Preuves recommandées à recueillir",
    },
    "result.evidence.caption": {
        LANG_EN: "Each item shows the expected ±percentage-point shift in the most-likely branch's probability if you collect that evidence. Larger ΔP = more decision-relevant. (Values do not sum to 1 — each is an independent expected shift.)",
        LANG_ZH: "每一项显示：若你收集该证据，最可能分支的概率预计会有多大的 ±百分点变化。ΔP 越大 ＝ 对决策越关键。（各项不求和为 1——每一项都是独立的预期变化。）",
        LANG_ES: "Cada elemento muestra el cambio esperado en ±puntos porcentuales en la probabilidad de la rama más probable si recopilas esa evidencia. Mayor ΔP = más relevante para la decisión. (Los valores no suman 1: cada uno es un cambio esperado independiente.)",
        LANG_FR: "Chaque élément indique la variation attendue en ±points de pourcentage de la probabilité de la branche la plus probable si vous recueillez cette preuve. ΔP plus grand = plus pertinent pour la décision. (Les valeurs ne totalisent pas 1 — chacune est une variation attendue indépendante.)",
    },
    "result.evidence.most_affects": {
        LANG_EN: "Most affects: `{branch}`",
        LANG_ZH: "影响最大：`{branch}`",
        LANG_ES: "Más afecta a: `{branch}`",
        LANG_FR: "Affecte le plus : `{branch}`",
    },
    "result.evidence.expected_dp": {
        LANG_EN: "Expected ΔP",
        LANG_ZH: "预期 ΔP",
        LANG_ES: "ΔP esperado",
        LANG_FR: "ΔP attendu",
    },
    "result.lead.most_likely": {
        LANG_EN: "Most likely:",
        LANG_ZH: "最可能：",
        LANG_ES: "Lo más probable:",
        LANG_FR: "Le plus probable :",
    },
    "result.lead.hinges": {
        LANG_EN: "It mostly hinges on {driver}.",
        LANG_ZH: "主要取决于{driver}。",
        LANG_ES: "Depende sobre todo de {driver}.",
        LANG_FR: "Cela dépend surtout de {driver}.",
    },
    "result.lead.mapped": {
        LANG_EN: "We mapped {n} realistic ways this could go and weighed them against your situation.",
        LANG_ZH: "我们推演了 {n} 种现实的发展方式，并结合你的具体情况做了权衡。",
        LANG_ES: "Mapeamos {n} formas realistas en que esto podría ir y las sopesamos según tu situación.",
        LANG_FR: "Nous avons cartographié {n} évolutions réalistes possibles et les avons pondérées selon votre situation.",
    },
    "result.engine.tech_footnote": {
        LANG_EN: "For the curious: each path is a diagonal of the belief state ρ; the links are off-diagonal coherences; the time axis is decoherence.",
        LANG_ZH: "给好奇的人：每条路径是信念态 ρ 的对角元；关联是非对角相干项；时间轴是退相干。",
        LANG_ES: "Para curiosos: cada camino es una diagonal del estado de creencia ρ; los vínculos son coherencias fuera de diagonal; el eje del tiempo es decoherencia.",
        LANG_FR: "Pour les curieux : chaque voie est une diagonale de l'état de croyance ρ ; les liens sont des cohérences hors-diagonale ; l'axe temporel est la décohérence.",
    },
    "result.engine.belief_state": {
        LANG_EN: "How likely we think each path is",
        LANG_ZH: "我们认为每条路径的可能性",
        LANG_ES: "Qué probabilidad damos a cada camino",
        LANG_FR: "La probabilité que nous donnons à chaque voie",
    },
    "result.engine.compiled_note": {
        LANG_EN: "We weighed {n} possible paths against your specific situation, looked at which outcomes tend to move together ({m} links found), and how the odds shift as time passes — that's the chart above.",
        LANG_ZH: "我们把 {n} 条可能的路径结合你的具体情况做了权衡，看了哪些结果往往会一起发生（发现 {m} 处关联），以及随时间推移概率如何变化——也就是上面那张图。",
        LANG_ES: "Sopesamos {n} caminos posibles según tu situación, vimos qué resultados tienden a ir juntos ({m} vínculos) y cómo cambian las probabilidades con el tiempo — ese es el gráfico de arriba.",
        LANG_FR: "Nous avons pondéré {n} voies possibles selon votre situation, observé quels résultats vont souvent ensemble ({m} liens) et comment les probabilités évoluent avec le temps — c'est le graphique ci-dessus.",
    },
    "result.heatmap_title": {
        # Iter #3 (design-self-explains): "Probability mass across
        # futures" is jargon a first-time visitor doesn't parse — the
        # heatmap below carries the meaning, the title should just
        # name the surface. Replaced with the shortest concrete label
        # that fits next to the heatmap without instructing the user.
        # Iter #52 — blanked: the region is now headed by the step-②
        # label ("② Your possible futures") on the idle preview and by
        # the plain "Most likely: …" takeaway on the result page, so this
        # baked-in component title was a duplicate heading. Empty string
        # → the .sect-label div carries only its margin (no visible bar).
        LANG_EN: "",
        LANG_ZH: "",
        LANG_ES: "",
        LANG_FR: "",
    },
    # ===================================================================
    # Iter #66 (OMY-V415 / M2 / Acceptance #66) — bulk i18n sweep.
    # The result page's story/comparison/timeline/continuous view bodies,
    # the drill-down loop, coherence-decay chart, the measurement-update
    # + calibration-history pages, the pricing page, and the video /
    # webcam scene-query modes still rendered hardcoded English even when
    # the chrome around them was localized. These keys close that gap.
    # Dispatch-coupled strings (radio/selectbox option labels that drive
    # an `if x == "...":` or are stored) keep STABLE keys in app.py and
    # only the *display label* is localized — same discipline as the
    # iter-50 result.view.* radio.
    # -----  Story-view branch section headers  -----
    "result.story.wishful_header": {
        LANG_EN: "🌟 Best plausible case",
        LANG_ZH: "🌟 最佳合理情形",
        LANG_ES: "🌟 Mejor caso plausible",
        LANG_FR: "🌟 Meilleur cas plausible",
    },
    "result.story.wishful_caption": {
        LANG_EN: "The hoped-for future. Low probability but emotionally vivid. Use this as the anchor for thinking about what evidence / actions would shift its probability upward.",
        LANG_ZH: "你所期待的未来。概率不高，但情感上鲜明。把它当作锚点，思考哪些证据 / 行动能把它的概率往上推。",
        LANG_ES: "El futuro deseado. Baja probabilidad pero emocionalmente vívido. Úsalo como ancla para pensar qué evidencia o acciones elevarían su probabilidad.",
        LANG_FR: "L'avenir espéré. Faible probabilité mais émotionnellement marquant. Servez-vous-en comme ancrage pour réfléchir aux preuves / actions qui augmenteraient sa probabilité.",
    },
    "result.story.realistic_header": {
        LANG_EN: "📊 Most-likely futures",
        LANG_ZH: "📊 最可能的未来",
        LANG_ES: "📊 Futuros más probables",
        LANG_FR: "📊 Futurs les plus probables",
    },
    "result.story.realistic_caption": {
        LANG_EN: "{n} realistic branches across decision options: {options}",
        LANG_ZH: "{n} 条现实分支，覆盖各决策选项：{options}",
        LANG_ES: "{n} ramas realistas entre las opciones de decisión: {options}",
        LANG_FR: "{n} branches réalistes parmi les options de décision : {options}",
    },
    "result.story.worst_header": {
        LANG_EN: "⚠️ Worst plausible case",
        LANG_ZH: "⚠️ 最坏合理情形",
        LANG_ES: "⚠️ Peor caso plausible",
        LANG_FR: "⚠️ Pire cas plausible",
    },
    "result.story.worst_caption": {
        LANG_EN: "The future to actively avoid. Low probability but specific. Use this to identify what preventive actions you should take regardless of which decision you pick.",
        LANG_ZH: "需要主动规避的未来。概率不高，但很具体。用它来识别：无论你选哪个决策，都应采取哪些预防行动。",
        LANG_ES: "El futuro que debes evitar activamente. Baja probabilidad pero específico. Úsalo para identificar qué acciones preventivas tomar sin importar qué decisión elijas.",
        LANG_FR: "L'avenir à éviter activement. Faible probabilité mais précis. Servez-vous-en pour repérer les actions préventives à prendre quelle que soit la décision choisie.",
    },
    # -----  Comparison-table view  -----
    "result.compare.caption": {
        LANG_EN: "Same data as the story view, laid out for quick scanning. Useful when you need to compare two branches' probability / decision / key driver side-by-side.",
        LANG_ZH: "与故事视图相同的数据，排版便于快速浏览。当你需要并排比较两条分支的概率 / 决策 / 关键驱动因素时很有用。",
        LANG_ES: "Los mismos datos que la vista de relato, dispuestos para una lectura rápida. Útil cuando necesitas comparar la probabilidad / decisión / factor clave de dos ramas lado a lado.",
        LANG_FR: "Les mêmes données que la vue récit, présentées pour un survol rapide. Utile pour comparer côte à côte la probabilité / décision / facteur clé de deux branches.",
    },
    "result.compare.empty": {
        LANG_EN: "No branches to compare.",
        LANG_ZH: "没有可比较的分支。",
        LANG_ES: "No hay ramas para comparar.",
        LANG_FR: "Aucune branche à comparer.",
    },
    # -----  Timeline view  -----
    "result.timeline.caption": {
        LANG_EN: "How each decision option fans out into branches over {horizon}. 🌟 = best-case anchor · 📊 = realistic · ⚠️ = worst-case anchor.",
        LANG_ZH: "在 {horizon} 内，每个决策选项如何展开成分支。🌟 ＝ 最佳情形锚点 · 📊 ＝ 现实 · ⚠️ ＝ 最坏情形锚点。",
        LANG_ES: "Cómo cada opción de decisión se ramifica a lo largo de {horizon}. 🌟 = ancla del mejor caso · 📊 = realista · ⚠️ = ancla del peor caso.",
        LANG_FR: "Comment chaque option de décision se ramifie sur {horizon}. 🌟 = ancrage meilleur cas · 📊 = réaliste · ⚠️ = ancrage pire cas.",
    },
    # -----  Continuous-distribution view  -----
    "result.continuous.empty": {
        LANG_EN: "No branches to plot a continuous distribution for.",
        LANG_ZH: "没有可用于绘制连续分布的分支。",
        LANG_ES: "No hay ramas para trazar una distribución continua.",
        LANG_FR: "Aucune branche pour tracer une distribution continue.",
    },
    "result.continuous.caption": {
        LANG_EN: "Each of {n} branches contributes a Gaussian kernel (σ ≈ {sigma:.1f} months) at a heuristic characteristic time — wishful branches centered around month {wishful_mo:.1f}, realistic around month {realistic_mo:.1f}, worst around month {worst_mo:.1f}. The curve is the probability-weighted sum. Use this when the discrete-branch table feels too engineering-shaped.",
        LANG_ZH: "{n} 条分支各贡献一个高斯核（σ ≈ {sigma:.1f} 个月），位于一个启发式的特征时间——期望分支约在第 {wishful_mo:.1f} 个月，现实分支约在第 {realistic_mo:.1f} 个月，最坏分支约在第 {worst_mo:.1f} 个月。曲线是按概率加权的总和。当离散分支表显得太工程化时，用这个视图。",
        LANG_ES: "Cada una de las {n} ramas aporta un núcleo gaussiano (σ ≈ {sigma:.1f} meses) en un tiempo característico heurístico: las ramas optimistas centradas en torno al mes {wishful_mo:.1f}, las realistas en torno al mes {realistic_mo:.1f}, las peores en torno al mes {worst_mo:.1f}. La curva es la suma ponderada por probabilidad. Úsala cuando la tabla de ramas discretas resulte demasiado técnica.",
        LANG_FR: "Chacune des {n} branches apporte un noyau gaussien (σ ≈ {sigma:.1f} mois) à un temps caractéristique heuristique — branches optimistes centrées vers le mois {wishful_mo:.1f}, réalistes vers le mois {realistic_mo:.1f}, pires vers le mois {worst_mo:.1f}. La courbe est la somme pondérée par probabilité. À utiliser quand le tableau de branches discrètes paraît trop technique.",
    },
    "result.continuous.xaxis_caption": {
        LANG_EN: "x-axis = sample index 0…N along the time horizon; first sample is t=0 and last is t={last_mo:.0f} months.",
        LANG_ZH: "横轴 ＝ 沿时间跨度的采样序号 0…N；第一个采样为 t=0，最后一个为 t={last_mo:.0f} 个月。",
        LANG_ES: "eje x = índice de muestra 0…N a lo largo del horizonte temporal; la primera muestra es t=0 y la última t={last_mo:.0f} meses.",
        LANG_FR: "axe x = indice d'échantillon 0…N sur l'horizon temporel ; le premier échantillon est t=0 et le dernier t={last_mo:.0f} mois.",
    },
    # -----  Drill-down loop  -----
    "result.drilldown.expander": {
        LANG_EN: "🔍 Drill down on one of these futures",
        LANG_ZH: "🔍 深入研究其中一个未来",
        LANG_ES: "🔍 Profundizar en uno de estos futuros",
        LANG_FR: "🔍 Approfondir l'un de ces futurs",
    },
    "result.drilldown.caption": {
        LANG_EN: "Pick a branch you care about most — typically the wishful one if you want to plan toward it, or the worst-case if you want to plan around it — and the system will expand it into a 3-paragraph deeper narrative + concrete actions this week + dependencies that gate it + sensitivity preview.",
        LANG_ZH: "选一条你最在意的分支——通常是你想为之规划的期望分支，或你想规避的最坏分支——系统会把它展开成 3 段更深入的叙述 ＋ 本周的具体行动 ＋ 制约它的依赖条件 ＋ 敏感性预览。",
        LANG_ES: "Elige la rama que más te importe —normalmente la optimista si quieres planificar hacia ella, o la peor si quieres planificar para evitarla— y el sistema la expandirá en una narrativa más profunda de 3 párrafos + acciones concretas esta semana + dependencias que la condicionan + vista previa de sensibilidad.",
        LANG_FR: "Choisissez la branche qui vous importe le plus — généralement l'optimiste si vous voulez planifier vers elle, ou la pire si vous voulez la contourner — et le système la développera en un récit plus approfondi de 3 paragraphes + actions concrètes cette semaine + dépendances qui la conditionnent + aperçu de sensibilité.",
    },
    "result.drilldown.empty": {
        LANG_EN: "No branches to drill into.",
        LANG_ZH: "没有可深入研究的分支。",
        LANG_ES: "No hay ramas para profundizar.",
        LANG_FR: "Aucune branche à approfondir.",
    },
    "result.drilldown.run": {
        LANG_EN: "Run drill-down",
        LANG_ZH: "运行深入研究",
        LANG_ES: "Ejecutar análisis",
        LANG_FR: "Lancer l'analyse",
    },
    "result.drilldown.show_cached": {
        LANG_EN: "Show cached drill-down",
        LANG_ZH: "显示已缓存的深入研究",
        LANG_ES: "Mostrar análisis en caché",
        LANG_FR: "Afficher l'analyse en cache",
    },
    "result.drilldown.rerun": {
        LANG_EN: "↻ Re-run (force refresh)",
        LANG_ZH: "↻ 重新运行（强制刷新）",
        LANG_ES: "↻ Volver a ejecutar (forzar actualización)",
        LANG_FR: "↻ Relancer (forcer l'actualisation)",
    },
    "result.drilldown.deeper_narrative": {
        LANG_EN: "Deeper narrative",
        LANG_ZH: "更深入的叙述",
        LANG_ES: "Narrativa más profunda",
        LANG_FR: "Récit plus approfondi",
    },
    "result.drilldown.actions": {
        LANG_EN: "Concrete actions this week",
        LANG_ZH: "本周的具体行动",
        LANG_ES: "Acciones concretas esta semana",
        LANG_FR: "Actions concrètes cette semaine",
    },
    "result.drilldown.effort": {
        LANG_EN: "Effort: {effort}",
        LANG_ZH: "投入：{effort}",
        LANG_ES: "Esfuerzo: {effort}",
        LANG_FR: "Effort : {effort}",
    },
    "result.drilldown.expected_effect": {
        LANG_EN: "Expected effect: {effect}",
        LANG_ZH: "预期效果：{effect}",
        LANG_ES: "Efecto esperado: {effect}",
        LANG_FR: "Effet attendu : {effect}",
    },
    "result.drilldown.dependencies": {
        LANG_EN: "Conditional dependencies",
        LANG_ZH: "条件依赖",
        LANG_ES: "Dependencias condicionales",
        LANG_FR: "Dépendances conditionnelles",
    },
    "result.drilldown.current_state": {
        LANG_EN: "Current state: {state}",
        LANG_ZH: "当前状态：{state}",
        LANG_ES: "Estado actual: {state}",
        LANG_FR: "État actuel : {state}",
    },
    "result.drilldown.if_fails": {
        LANG_EN: "If this fails: {impact}",
        LANG_ZH: "若此项失败：{impact}",
        LANG_ES: "Si esto falla: {impact}",
        LANG_FR: "Si cela échoue : {impact}",
    },
    "result.drilldown.sensitivity": {
        LANG_EN: "Sensitivity preview",
        LANG_ZH: "敏感性预览",
        LANG_ES: "Vista previa de sensibilidad",
        LANG_FR: "Aperçu de sensibilité",
    },
    "result.drilldown.sensitivity_caption": {
        LANG_EN: "What collecting each piece of evidence would do to this branch's probability specifically (in percentage points).",
        LANG_ZH: "收集每一项证据，具体会让这条分支的概率发生多大变化（以百分点计）。",
        LANG_ES: "Lo que recopilar cada evidencia haría a la probabilidad de esta rama en concreto (en puntos porcentuales).",
        LANG_FR: "Ce que recueillir chaque preuve ferait à la probabilité de cette branche précisément (en points de pourcentage).",
    },
    "result.drilldown.if_supports": {
        LANG_EN: "If signal supports",
        LANG_ZH: "若信号支持",
        LANG_ES: "Si la señal apoya",
        LANG_FR: "Si le signal appuie",
    },
    "result.drilldown.if_against": {
        LANG_EN: "If signal cuts against",
        LANG_ZH: "若信号相反",
        LANG_ES: "Si la señal contradice",
        LANG_FR: "Si le signal contredit",
    },
    "result.drilldown.cached_at": {
        LANG_EN: "Cached at {ts:.0f} (unix). Re-run with the refresh button if context has changed materially.",
        LANG_ZH: "缓存于 {ts:.0f}（unix 时间）。若上下文已发生实质变化，请用刷新按钮重新运行。",
        LANG_ES: "En caché desde {ts:.0f} (unix). Vuelve a ejecutar con el botón de actualizar si el contexto ha cambiado sustancialmente.",
        LANG_FR: "En cache depuis {ts:.0f} (unix). Relancez avec le bouton d'actualisation si le contexte a sensiblement changé.",
    },
    # -----  Coherence-decay chart  -----
    "result.coherence.header": {
        LANG_EN: "📉 Coherence decay over time",
        LANG_ZH: "📉 相干性随时间衰减",
        LANG_ES: "📉 Decaimiento de coherencia en el tiempo",
        LANG_FR: "📉 Décroissance de cohérence dans le temps",
    },
    "result.coherence.caption": {
        LANG_EN: "Off-diagonal magnitudes |ρ_ab| evolve under a Lindblad decoherence channel at γ=0.05/month (pure-decay; no phase rotation shown). When a pair's magnitude approaches zero, those two futures stop interfering and become independent — you've lost the window where they're 'coupled enough to reason about together.'",
        LANG_ZH: "非对角幅值 |ρ_ab| 在 γ=0.05/月 的 Lindblad 退相干通道下演化（纯衰减；不显示相位旋转）。当某一对的幅值趋近零时，这两个未来就不再相互干涉、变得独立——你失去了那个它们「耦合到足以一起推理」的窗口。",
        LANG_ES: "Las magnitudes fuera de diagonal |ρ_ab| evolucionan bajo un canal de decoherencia de Lindblad a γ=0.05/mes (decaimiento puro; sin rotación de fase). Cuando la magnitud de un par se acerca a cero, esos dos futuros dejan de interferir y se vuelven independientes: has perdido la ventana en que estaban 'lo bastante acoplados para razonarlos juntos'.",
        LANG_FR: "Les magnitudes hors-diagonale |ρ_ab| évoluent sous un canal de décohérence de Lindblad à γ=0,05/mois (décroissance pure ; pas de rotation de phase). Quand la magnitude d'une paire approche zéro, ces deux futurs cessent d'interférer et deviennent indépendants — vous avez perdu la fenêtre où ils étaient « assez couplés pour être raisonnés ensemble ».",
    },
    "result.coherence.decay_summary": {
        LANG_EN: "**Decay summary over {n} months** (γ={gamma:.2f}/month; analytic reference ≈ {ref:.2f}× of initial)",
        LANG_ZH: "**{n} 个月内的衰减汇总**（γ={gamma:.2f}/月；解析参考 ≈ 初始值的 {ref:.2f} 倍）",
        LANG_ES: "**Resumen de decaimiento en {n} meses** (γ={gamma:.2f}/mes; referencia analítica ≈ {ref:.2f}× del inicial)",
        LANG_FR: "**Résumé de décroissance sur {n} mois** (γ={gamma:.2f}/mois ; référence analytique ≈ {ref:.2f}× de l'initial)",
    },
    "result.coherence.rho_now": {
        LANG_EN: "|ρ| now",
        LANG_ZH: "|ρ| 当前",
        LANG_ES: "|ρ| ahora",
        LANG_FR: "|ρ| maintenant",
    },
    "result.coherence.rho_at": {
        LANG_EN: "|ρ| @ {n}mo",
        LANG_ZH: "|ρ| @ {n}个月",
        LANG_ES: "|ρ| @ {n}m",
        LANG_FR: "|ρ| @ {n}mois",
    },
    "result.coherence.decay_delta": {
        LANG_EN: "Δ decay",
        LANG_ZH: "Δ 衰减",
        LANG_ES: "Δ decaimiento",
        LANG_FR: "Δ décroissance",
    },
    "result.coherence.interpretation": {
        LANG_EN: "Interpretation: a strong, slowly-decaying coherence means you can still treat those two futures as 'linked' when planning. A coherence that has already collapsed by your decision horizon means the two are practically independent outcomes — preventive action against one no longer biases the other.",
        LANG_ZH: "解读：一个强且缓慢衰减的相干性，意味着规划时你仍可把这两个未来视为「关联的」。而一个在你的决策期限前就已坍缩的相干性，意味着这两者实际上是独立的结果——对其一采取预防行动不再影响另一个。",
        LANG_ES: "Interpretación: una coherencia fuerte y de decaimiento lento significa que aún puedes tratar esos dos futuros como 'vinculados' al planificar. Una coherencia que ya ha colapsado para tu horizonte de decisión significa que los dos son resultados prácticamente independientes: la acción preventiva contra uno ya no afecta al otro.",
        LANG_FR: "Interprétation : une cohérence forte et à décroissance lente signifie que vous pouvez encore traiter ces deux futurs comme « liés » lors de la planification. Une cohérence déjà effondrée à votre horizon de décision signifie que les deux sont des issues pratiquement indépendantes — une action préventive contre l'un n'influence plus l'autre.",
    },
    # -----  Result view-mode radio label (hidden, a11y)  -----
    "result.view.radio_label": {
        LANG_EN: "View",
        LANG_ZH: "视图",
        LANG_ES: "Vista",
        LANG_FR: "Vue",
    },
    # -----  Measurement-update page  -----
    "measurement.original_branches": {
        LANG_EN: "Original prediction branches",
        LANG_ZH: "原始预测分支",
        LANG_ES: "Ramas de predicción originales",
        LANG_FR: "Branches de prédiction d'origine",
    },
    "measurement.what_happened": {
        LANG_EN: "What actually happened?",
        LANG_ZH: "实际发生了什么？",
        LANG_ES: "¿Qué pasó en realidad?",
        LANG_FR: "Que s'est-il réellement passé ?",
    },
    "measurement.what_happened_caption": {
        LANG_EN: "For each branch, indicate how much it matched reality. 1.0 = fully materialized, 0.0 = didn't happen, intermediate values for partial matches. The values get auto-normalized.",
        LANG_ZH: "对每条分支，标注它与现实的吻合程度。1.0 ＝ 完全实现，0.0 ＝ 没有发生，部分吻合取中间值。这些值会自动归一化。",
        LANG_ES: "Para cada rama, indica cuánto coincidió con la realidad. 1.0 = se materializó por completo, 0.0 = no ocurrió, valores intermedios para coincidencias parciales. Los valores se normalizan automáticamente.",
        LANG_FR: "Pour chaque branche, indiquez à quel point elle a correspondu à la réalité. 1.0 = pleinement réalisée, 0.0 = pas arrivée, valeurs intermédiaires pour les correspondances partielles. Les valeurs sont normalisées automatiquement.",
    },
    "measurement.sean_ellis_label": {
        LANG_EN: "**Sean Ellis disappointment test** (PMF indicator)",
        LANG_ZH: "**Sean Ellis 失望度测试**（PMF 指标）",
        LANG_ES: "**Prueba de decepción de Sean Ellis** (indicador de PMF)",
        LANG_FR: "**Test de déception de Sean Ellis** (indicateur de PMF)",
    },
    "measurement.sean_ellis_question": {
        LANG_EN: "If you could no longer use this prediction tool, how would you feel?",
        LANG_ZH: "如果你再也不能使用这个预测工具，你会有什么感受？",
        LANG_ES: "Si ya no pudieras usar esta herramienta de predicción, ¿cómo te sentirías?",
        LANG_FR: "Si vous ne pouviez plus utiliser cet outil de prédiction, comment vous sentiriez-vous ?",
    },
    "measurement.sean_ellis_very": {
        LANG_EN: "Very disappointed",
        LANG_ZH: "非常失望",
        LANG_ES: "Muy decepcionado",
        LANG_FR: "Très déçu",
    },
    "measurement.sean_ellis_somewhat": {
        LANG_EN: "Somewhat disappointed",
        LANG_ZH: "有些失望",
        LANG_ES: "Algo decepcionado",
        LANG_FR: "Un peu déçu",
    },
    "measurement.sean_ellis_not": {
        LANG_EN: "Not disappointed",
        LANG_ZH: "不失望",
        LANG_ES: "Nada decepcionado",
        LANG_FR: "Pas déçu",
    },
    "measurement.effort_label": {
        LANG_EN: "**Effort test** (retention quality over {horizon})",
        LANG_ZH: "**投入度测试**（在 {horizon} 内的留存质量）",
        LANG_ES: "**Prueba de esfuerzo** (calidad de retención durante {horizon})",
        LANG_FR: "**Test d'effort** (qualité de rétention sur {horizon})",
    },
    "measurement.effort_window_fallback": {
        LANG_EN: "the measurement window",
        LANG_ZH: "测量窗口期",
        LANG_ES: "la ventana de medición",
        LANG_FR: "la fenêtre de mesure",
    },
    "measurement.effort_question": {
        LANG_EN: "Over the past {horizon}, did you self-return to the tool?",
        LANG_ZH: "在过去 {horizon} 里，你是否主动回来使用这个工具？",
        LANG_ES: "Durante {horizon}, ¿volviste a la herramienta por iniciativa propia?",
        LANG_FR: "Au cours de {horizon}, êtes-vous revenu à l'outil de vous-même ?",
    },
    "measurement.effort_self_returned": {
        LANG_EN: "I came back to it on my own initiative (opened it without being reminded)",
        LANG_ZH: "我主动回来用它（没人提醒就自己打开了）",
        LANG_ES: "Volví por iniciativa propia (lo abrí sin que me lo recordaran)",
        LANG_FR: "J'y suis revenu de ma propre initiative (ouvert sans rappel)",
    },
    "measurement.effort_needed_reminder": {
        LANG_EN: "I came back only when reminded (the operator nudged me)",
        LANG_ZH: "只有被提醒时我才回来（运营方推了我一下）",
        LANG_ES: "Solo volví cuando me lo recordaron (el operador me animó)",
        LANG_FR: "Je ne suis revenu que lorsqu'on me l'a rappelé (l'opérateur m'a relancé)",
    },
    "measurement.effort_did_not_return": {
        LANG_EN: "I did not return to the tool",
        LANG_ZH: "我没有再回来用这个工具",
        LANG_ES: "No volví a la herramienta",
        LANG_FR: "Je ne suis pas revenu à l'outil",
    },
    "measurement.submit": {
        LANG_EN: "Submit measurement update",
        LANG_ZH: "提交测量更新",
        LANG_ES: "Enviar actualización de medición",
        LANG_FR: "Soumettre la mise à jour de mesure",
    },
    "measurement.saved": {
        LANG_EN: "Measurement saved.",
        LANG_ZH: "测量已保存。",
        LANG_ES: "Medición guardada.",
        LANG_FR: "Mesure enregistrée.",
    },
    # -----  Calibration-history page  -----
    "calibration.global_caption": {
        LANG_EN: "Showing aggregate calibration across **all** demo users (no handle entered).",
        LANG_ZH: "正在显示**所有**演示用户的汇总校准数据（未输入用户名）。",
        LANG_ES: "Mostrando la calibración agregada de **todos** los usuarios de demostración (sin identificador).",
        LANG_FR: "Affichage de la calibration agrégée de **tous** les utilisateurs de démonstration (aucun identifiant saisi).",
    },
    "calibration.empty": {
        LANG_EN: "No measurement updates recorded yet. After a prediction's horizon date passes, score it on the **Measurement update** page to populate this view — that's where your calibration track record builds up.",
        LANG_ZH: "还没有记录任何测量更新。当某个预测的期限日期过去后，在 **测量更新** 页面给它打分，就能填充这个视图——你的校准记录就是在那里积累起来的。",
        LANG_ES: "Aún no se han registrado actualizaciones de medición. Cuando pase la fecha de horizonte de una predicción, puntúala en la página **Actualización de medición** para poblar esta vista: ahí se construye tu historial de calibración.",
        LANG_FR: "Aucune mise à jour de mesure enregistrée pour l'instant. Une fois la date d'horizon d'une prédiction passée, notez-la sur la page **Mise à jour de mesure** pour alimenter cette vue — c'est là que se construit votre historique de calibration.",
    },
    "calibration.metric_measurements": {
        LANG_EN: "Measurements",
        LANG_ZH: "测量次数",
        LANG_ES: "Mediciones",
        LANG_FR: "Mesures",
    },
    "calibration.metric_mean_brier": {
        LANG_EN: "Mean Brier",
        LANG_ZH: "平均 Brier",
        LANG_ES: "Brier medio",
        LANG_FR: "Brier moyen",
    },
    "calibration.metric_mean_logloss": {
        LANG_EN: "Mean log-loss",
        LANG_ZH: "平均对数损失",
        LANG_ES: "Log-loss medio",
        LANG_FR: "Log-loss moyen",
    },
    "calibration.brier_reference": {
        LANG_EN: "Brier score reference: 0 = perfect calibration; 1 = perfectly wrong (uniform-prior baseline ≈ 0.5 for 5-way categorical).",
        LANG_ZH: "Brier 分数参考：0 ＝ 完美校准；1 ＝ 完全错误（5 类分类的均匀先验基线 ≈ 0.5）。",
        LANG_ES: "Referencia de puntuación Brier: 0 = calibración perfecta; 1 = totalmente equivocado (línea base de prior uniforme ≈ 0.5 para categórica de 5 vías).",
        LANG_FR: "Référence du score de Brier : 0 = calibration parfaite ; 1 = totalement faux (base de prior uniforme ≈ 0,5 pour une catégorielle à 5 voies).",
    },
    "calibration.owner_bias_header": {
        LANG_EN: "Owner-bias breakdown",
        LANG_ZH: "所有者偏差分解",
        LANG_ES: "Desglose de sesgo del propietario",
        LANG_FR: "Ventilation du biais du propriétaire",
    },
    "calibration.owner_bias_caption": {
        LANG_EN: "Some predictions are flagged as project-owner self-tests. The founder explicitly noted that owner data points may carry bias (NPS/utility scored higher than a neutral user would). This breakdown shows the same metrics computed with and without owner-flagged measurements.",
        LANG_ZH: "有些预测被标记为项目所有者的自测。创始人明确指出，所有者的数据点可能带有偏差（NPS / 效用打分比中立用户更高）。这个分解显示在包含与排除所有者标记测量两种情况下计算的相同指标。",
        LANG_ES: "Algunas predicciones están marcadas como autopruebas del propietario del proyecto. El fundador señaló explícitamente que los datos del propietario pueden tener sesgo (NPS/utilidad puntuados más alto de lo que lo haría un usuario neutral). Este desglose muestra las mismas métricas calculadas con y sin las mediciones marcadas como del propietario.",
        LANG_FR: "Certaines prédictions sont marquées comme auto-tests du propriétaire du projet. Le fondateur a explicitement noté que les données du propriétaire peuvent comporter un biais (NPS/utilité notés plus haut qu'un utilisateur neutre). Cette ventilation montre les mêmes métriques calculées avec et sans les mesures marquées propriétaire.",
    },
    "calibration.real_users_only": {
        LANG_EN: "**Real users only (owner excluded)**",
        LANG_ZH: "**仅真实用户（排除所有者）**",
        LANG_ES: "**Solo usuarios reales (propietario excluido)**",
        LANG_FR: "**Utilisateurs réels seulement (propriétaire exclu)**",
    },
    "calibration.owner_only": {
        LANG_EN: "**Owner self-tests only**",
        LANG_ZH: "**仅所有者自测**",
        LANG_ES: "**Solo autopruebas del propietario**",
        LANG_FR: "**Auto-tests du propriétaire seulement**",
    },
    "calibration.no_non_owner": {
        LANG_EN: "No non-owner measurements yet.",
        LANG_ZH: "还没有非所有者的测量。",
        LANG_ES: "Aún no hay mediciones de no propietarios.",
        LANG_FR: "Aucune mesure hors propriétaire pour l'instant.",
    },
    "calibration.no_owner": {
        LANG_EN: "No owner-flagged measurements yet.",
        LANG_ZH: "还没有标记为所有者的测量。",
        LANG_ES: "Aún no hay mediciones marcadas como del propietario.",
        LANG_FR: "Aucune mesure marquée propriétaire pour l'instant.",
    },
    "calibration.owner_delta": {
        LANG_EN: "Δ (owner − non-owner) Brier = {sign}{delta:.4f}. Negative delta means owner self-test scored 'better calibrated' than the neutral sample — interpret as ownership bias.",
        LANG_ZH: "Δ（所有者 − 非所有者）Brier = {sign}{delta:.4f}。负的 delta 意味着所有者自测比中立样本「校准得更好」——应理解为所有权偏差。",
        LANG_ES: "Δ (propietario − no propietario) Brier = {sign}{delta:.4f}. Un delta negativo significa que la autoprueba del propietario obtuvo 'mejor calibración' que la muestra neutral: interprétalo como sesgo de propiedad.",
        LANG_FR: "Δ (propriétaire − hors propriétaire) Brier = {sign}{delta:.4f}. Un delta négatif signifie que l'auto-test du propriétaire est « mieux calibré » que l'échantillon neutre — à interpréter comme un biais de propriété.",
    },
    "calibration.trend_header": {
        LANG_EN: "Calibration trend",
        LANG_ZH: "校准趋势",
        LANG_ES: "Tendencia de calibración",
        LANG_FR: "Tendance de calibration",
    },
    "calibration.trend_caption": {
        LANG_EN: "Brier score per measurement, oldest → newest. **Down and to the right** means you're getting more calibrated over time. 0 is perfect; 0.5 is uniform-prior baseline; 1 is perfectly wrong.",
        LANG_ZH: "每次测量的 Brier 分数，从旧到新。**向右下方** 意味着你随时间越来越校准。0 为完美；0.5 为均匀先验基线；1 为完全错误。",
        LANG_ES: "Puntuación Brier por medición, de la más antigua a la más reciente. **Hacia abajo y a la derecha** significa que te calibras mejor con el tiempo. 0 es perfecto; 0.5 es la línea base de prior uniforme; 1 es totalmente equivocado.",
        LANG_FR: "Score de Brier par mesure, du plus ancien au plus récent. **Vers le bas et la droite** signifie que vous vous calibrez mieux avec le temps. 0 est parfait ; 0,5 est la base de prior uniforme ; 1 est totalement faux.",
    },
    "calibration.trend_direction": {
        LANG_EN: "Direction over your scored history: **{trend}** (early third Brier ≈ {early:.3f} → recent third ≈ {late:.3f}; delta {delta:+.3f}, negative is good).",
        LANG_ZH: "你打分历史的方向：**{trend}**（前三分之一 Brier ≈ {early:.3f} → 近三分之一 ≈ {late:.3f}；delta {delta:+.3f}，负值为好）。",
        LANG_ES: "Dirección a lo largo de tu historial puntuado: **{trend}** (primer tercio Brier ≈ {early:.3f} → tercio reciente ≈ {late:.3f}; delta {delta:+.3f}, negativo es bueno).",
        LANG_FR: "Direction sur votre historique noté : **{trend}** (premier tiers Brier ≈ {early:.3f} → tiers récent ≈ {late:.3f} ; delta {delta:+.3f}, négatif c'est bon).",
    },
    "calibration.trend_improving": {
        LANG_EN: "improving",
        LANG_ZH: "在改善",
        LANG_ES: "mejorando",
        LANG_FR: "en amélioration",
    },
    "calibration.trend_regressing": {
        LANG_EN: "regressing",
        LANG_ZH: "在退步",
        LANG_ES: "empeorando",
        LANG_FR: "en régression",
    },
    "calibration.trend_flat": {
        LANG_EN: "flat",
        LANG_ZH: "持平",
        LANG_ES: "estable",
        LANG_FR: "stable",
    },
    "calibration.track_record_header": {
        LANG_EN: "Per-prediction track record",
        LANG_ZH: "逐预测的历史记录",
        LANG_ES: "Historial por predicción",
        LANG_FR: "Bilan par prédiction",
    },
    "calibration.track_record_caption": {
        LANG_EN: "Your most recent scored predictions. Each card shows the probability you assigned to the future that actually happened — the single number you most want to see.",
        LANG_ZH: "你最近打过分的预测。每张卡片显示你为「实际发生的那个未来」所赋予的概率——你最想看的那个数字。",
        LANG_ES: "Tus predicciones puntuadas más recientes. Cada tarjeta muestra la probabilidad que asignaste al futuro que realmente ocurrió: el único número que más quieres ver.",
        LANG_FR: "Vos prédictions notées les plus récentes. Chaque carte montre la probabilité que vous avez attribuée au futur qui s'est réellement produit — le seul chiffre que vous voulez vraiment voir.",
    },
    "calibration.track_record_empty": {
        LANG_EN: "No per-prediction records yet. The aggregate above counts all measurements across users; individual records show up here only when you scored predictions under this user handle.",
        LANG_ZH: "还没有逐预测的记录。上面的汇总统计了所有用户的全部测量；只有当你以这个用户名给预测打过分时，单条记录才会显示在这里。",
        LANG_ES: "Aún no hay registros por predicción. El agregado de arriba cuenta todas las mediciones entre usuarios; los registros individuales aparecen aquí solo cuando puntuaste predicciones con este identificador.",
        LANG_FR: "Aucun enregistrement par prédiction pour l'instant. L'agrégat ci-dessus compte toutes les mesures, tous utilisateurs confondus ; les enregistrements individuels n'apparaissent ici que lorsque vous avez noté des prédictions sous cet identifiant.",
    },
    # -----  Pricing page  -----
    "pricing.currency_usd": {
        LANG_EN: "Prices shown in **US Dollars** — the canonical billing currency.",
        LANG_ZH: "价格以**美元**显示——标准计费货币。",
        LANG_ES: "Precios mostrados en **dólares estadounidenses**, la moneda de facturación canónica.",
        LANG_FR: "Prix affichés en **dollars américains**, la devise de facturation de référence.",
    },
    "pricing.currency_other": {
        LANG_EN: "Prices shown in **{name} ({code})** — an approximate conversion; canonical billing is USD.",
        LANG_ZH: "价格以**{name}（{code}）**显示——为近似换算；标准计费仍为美元。",
        LANG_ES: "Precios mostrados en **{name} ({code})**, una conversión aproximada; la facturación canónica es en USD.",
        LANG_FR: "Prix affichés en **{name} ({code})**, une conversion approximative ; la facturation de référence est en USD.",
    },
    "pricing.tier_comparison": {
        LANG_EN: "Tier comparison",
        LANG_ZH: "套餐对比",
        LANG_ES: "Comparación de niveles",
        LANG_FR: "Comparaison des forfaits",
    },
    "pricing.includes": {
        LANG_EN: "**Includes:**",
        LANG_ZH: "**包含：**",
        LANG_ES: "**Incluye:**",
        LANG_FR: "**Comprend :**",
    },
    "pricing.for_persona": {
        LANG_EN: "*For:* {persona}",
        LANG_ZH: "*适合：* {persona}",
        LANG_ES: "*Para:* {persona}",
        LANG_FR: "*Pour :* {persona}",
    },
    "pricing.not_available": {
        LANG_EN: "⏳ Not available for purchase yet",
        LANG_ZH: "⏳ 暂未开放购买",
        LANG_ES: "⏳ Aún no disponible para compra",
        LANG_FR: "⏳ Pas encore disponible à l'achat",
    },
    "pricing.preorder_header": {
        LANG_EN: "Express pre-order interest",
        LANG_ZH: "表达预订意向",
        LANG_ES: "Expresa tu interés de prepedido",
        LANG_FR: "Exprimer un intérêt de précommande",
    },
    "pricing.preorder_caption": {
        LANG_EN: "Tell us which tier interests you and how much you'd actually pay (USD). This is honest PMF research; we don't take payment or commit you to anything.",
        LANG_ZH: "告诉我们你对哪个套餐感兴趣、以及你实际愿意付多少（美元）。这是真实的 PMF 调研；我们不收款，也不会让你承诺任何事。",
        LANG_ES: "Dinos qué nivel te interesa y cuánto pagarías realmente (USD). Es investigación honesta de PMF; no cobramos ni te comprometemos a nada.",
        LANG_FR: "Dites-nous quel forfait vous intéresse et combien vous paieriez réellement (USD). C'est une étude PMF honnête ; nous ne prenons aucun paiement et ne vous engageons à rien.",
    },
    "pricing.preorder_submit": {
        LANG_EN: "Submit pre-order interest",
        LANG_ZH: "提交预订意向",
        LANG_ES: "Enviar interés de prepedido",
        LANG_FR: "Soumettre l'intérêt de précommande",
    },
    "pricing.handle_required": {
        LANG_EN: "Please provide your handle.",
        LANG_ZH: "请填写你的用户名。",
        LANG_ES: "Indica tu identificador, por favor.",
        LANG_FR: "Veuillez indiquer votre identifiant.",
    },
    "pricing.preorder_recorded": {
        LANG_EN: "Recorded: {amount} for {tier}. Thanks — this directly feeds the v4.17 billing-integration prioritization.",
        LANG_ZH: "已记录：{tier} 出价 {amount}。谢谢——这会直接用于 v4.17 计费集成的优先级排序。",
        LANG_ES: "Registrado: {amount} para {tier}. Gracias: esto alimenta directamente la priorización de integración de facturación v4.17.",
        LANG_FR: "Enregistré : {amount} pour {tier}. Merci — cela alimente directement la priorisation de l'intégration de facturation v4.17.",
    },
    "pricing.signal_header": {
        LANG_EN: "Current pre-order signal",
        LANG_ZH: "当前预订信号",
        LANG_ES: "Señal de prepedido actual",
        LANG_FR: "Signal de précommande actuel",
    },
    "pricing.signal_caption": {
        LANG_EN: "Aggregate willingness-to-pay across all submissions per tier. Helps the founder spot which tier has actual demand vs which is theoretical.",
        LANG_ZH: "各套餐所有提交的付费意愿汇总。帮助创始人识别哪个套餐有真实需求、哪个只是理论上的。",
        LANG_ES: "Disposición a pagar agregada de todos los envíos por nivel. Ayuda al fundador a ver qué nivel tiene demanda real frente a cuál es teórico.",
        LANG_FR: "Disposition à payer agrégée pour tous les envois par forfait. Aide le fondateur à repérer quel forfait a une demande réelle et lequel reste théorique.",
    },
    # -----  Video scene-query mode  -----
    "video.analyze_button": {
        LANG_EN: "🚀 Analyze video",
        LANG_ZH: "🚀 分析视频",
        LANG_ES: "🚀 Analizar video",
        LANG_FR: "🚀 Analyser la vidéo",
    },
    "video.err_no_file": {
        LANG_EN: "Please upload a video file first.",
        LANG_ZH: "请先上传一个视频文件。",
        LANG_ES: "Sube primero un archivo de video.",
        LANG_FR: "Veuillez d'abord téléverser un fichier vidéo.",
    },
    "video.err_no_question": {
        LANG_EN: "Please enter a question about the scene.",
        LANG_ZH: "请输入一个关于场景的问题。",
        LANG_ES: "Introduce una pregunta sobre la escena.",
        LANG_FR: "Veuillez saisir une question sur la scène.",
    },
    "video.err_no_handle": {
        LANG_EN: "Please provide a handle (any string).",
        LANG_ZH: "请填写一个用户名（任意字符串均可）。",
        LANG_ES: "Indica un identificador (cualquier texto).",
        LANG_FR: "Veuillez indiquer un identifiant (n'importe quel texte).",
    },
    "video.scene_complete": {
        LANG_EN: "✓ Scene analysis complete.",
        LANG_ZH: "✓ 场景分析完成。",
        LANG_ES: "✓ Análisis de escena completado.",
        LANG_FR: "✓ Analyse de la scène terminée.",
    },
    "video.prediction_id_caption": {
        LANG_EN: "Prediction ID (save this for later measurement-update): `{pid}`",
        LANG_ZH: "预测 ID（保存它，以便日后做测量更新）：`{pid}`",
        LANG_ES: "ID de predicción (guárdalo para la actualización de medición posterior): `{pid}`",
        LANG_FR: "ID de prédiction (conservez-le pour la mise à jour de mesure ultérieure) : `{pid}`",
    },
    "video.entity_quantum_header": {
        LANG_EN: "⚛ Entity-trajectory quantum evolution",
        LANG_ZH: "⚛ 实体轨迹量子演化",
        LANG_ES: "⚛ Evolución cuántica de trayectoria de entidades",
        LANG_FR: "⚛ Évolution quantique de trajectoire d'entités",
    },
    "video.entity_quantum_caption": {
        LANG_EN: "For each tracked entity, the system synthesizes three future-position hypotheses (continue / accelerate / decelerate). These are combined into a JointWaveFunction across up to 3 entities, then evolved under a Lindblad open-system operator over a short horizon. The decaying off-diagonal magnitudes below show how correlations between entity-trajectory futures wash out into independent classical outcomes.",
        LANG_ZH: "对每个被追踪的实体，系统合成三种未来位置假设（继续 / 加速 / 减速）。它们被组合成一个跨最多 3 个实体的 JointWaveFunction，然后在短期内由 Lindblad 开放系统算子演化。下方衰减的非对角幅值显示：实体轨迹未来之间的关联如何消散成独立的经典结果。",
        LANG_ES: "Para cada entidad rastreada, el sistema sintetiza tres hipótesis de posición futura (continuar / acelerar / desacelerar). Se combinan en una JointWaveFunction de hasta 3 entidades y luego evolucionan bajo un operador de sistema abierto de Lindblad en un horizonte corto. Las magnitudes fuera de diagonal decrecientes de abajo muestran cómo las correlaciones entre los futuros de trayectoria de entidades se disuelven en resultados clásicos independientes.",
        LANG_FR: "Pour chaque entité suivie, le système synthétise trois hypothèses de position future (continuer / accélérer / décélérer). Elles sont combinées en une JointWaveFunction sur jusqu'à 3 entités, puis évoluées sous un opérateur de système ouvert de Lindblad sur un court horizon. Les magnitudes hors-diagonale décroissantes ci-dessous montrent comment les corrélations entre les futurs de trajectoire d'entités se dissolvent en issues classiques indépendantes.",
    },
    "video.no_entities_evolve": {
        LANG_EN: "No trackable entities to evolve.",
        LANG_ZH: "没有可演化的可追踪实体。",
        LANG_ES: "No hay entidades rastreables que evolucionar.",
        LANG_FR: "Aucune entité suivie à faire évoluer.",
    },
    "video.joint_unavailable": {
        LANG_EN: "Joint evolution unavailable in this environment — the frame stream and entity tracking still ran above.",
        LANG_ZH: "此环境下无法进行联合演化——上方的帧流与实体追踪仍已运行。",
        LANG_ES: "Evolución conjunta no disponible en este entorno: el flujo de fotogramas y el seguimiento de entidades sí se ejecutaron arriba.",
        LANG_FR: "Évolution conjointe indisponible dans cet environnement — le flux d'images et le suivi des entités ont quand même été exécutés ci-dessus.",
    },
    "video.metric_joint_hyps": {
        LANG_EN: "Joint hypotheses",
        LANG_ZH: "联合假设",
        LANG_ES: "Hipótesis conjuntas",
        LANG_FR: "Hypothèses conjointes",
    },
    "video.metric_offdiag_pairs": {
        LANG_EN: "Off-diagonal pairs",
        LANG_ZH: "非对角对",
        LANG_ES: "Pares fuera de diagonal",
        LANG_FR: "Paires hors-diagonale",
    },
    "video.metric_entities_evolved": {
        LANG_EN: "Entities evolved",
        LANG_ZH: "已演化实体",
        LANG_ES: "Entidades evolucionadas",
        LANG_FR: "Entités évoluées",
    },
    "video.no_offdiag": {
        LANG_EN: "No off-diagonal coherences generated (need ≥2 entities with informative trajectories). Skipping evolution.",
        LANG_ZH: "未生成非对角相干（需要 ≥2 个具有信息性轨迹的实体）。跳过演化。",
        LANG_ES: "No se generaron coherencias fuera de diagonal (se necesitan ≥2 entidades con trayectorias informativas). Omitiendo evolución.",
        LANG_FR: "Aucune cohérence hors-diagonale générée (≥2 entités avec trajectoires informatives requises). Évolution ignorée.",
    },
    "video.no_snapshots": {
        LANG_EN: "No evolution snapshots to display.",
        LANG_ZH: "没有可显示的演化快照。",
        LANG_ES: "No hay instantáneas de evolución para mostrar.",
        LANG_FR: "Aucun instantané d'évolution à afficher.",
    },
    # -----  Live-webcam mode  -----
    "webcam.stack_missing": {
        LANG_EN: "The live-webcam stream stack isn't installed in this environment. The Video query tab (above in the sidebar) accepts uploaded video files and runs the same perception + quantum pipeline.",
        LANG_ZH: "此环境未安装实时摄像头流的依赖栈。侧边栏上方的「视频查询」标签接受上传的视频文件，并运行相同的感知 ＋ 量子流水线。",
        LANG_ES: "La pila de transmisión de cámara web en vivo no está instalada en este entorno. La pestaña de consulta de video (arriba en la barra lateral) acepta archivos de video subidos y ejecuta la misma cadena de percepción + cuántica.",
        LANG_FR: "La pile de flux webcam en direct n'est pas installée dans cet environnement. L'onglet de requête vidéo (en haut de la barre latérale) accepte les fichiers vidéo téléversés et exécute le même pipeline perception + quantique.",
    },
    "webcam.tuning_expander": {
        LANG_EN: "Tuning (advanced)",
        LANG_ZH: "调参（进阶）",
        LANG_ES: "Ajustes (avanzado)",
        LANG_FR: "Réglages (avancé)",
    },
    "webcam.live_state": {
        LANG_EN: "Live state",
        LANG_ZH: "实时状态",
        LANG_ES: "Estado en vivo",
        LANG_FR: "État en direct",
    },
    "webcam.refresh_state": {
        LANG_EN: "🔄 Refresh state",
        LANG_ZH: "🔄 刷新状态",
        LANG_ES: "🔄 Actualizar estado",
        LANG_FR: "🔄 Actualiser l'état",
    },
    "webcam.reset_session": {
        LANG_EN: "🧹 Reset session",
        LANG_ZH: "🧹 重置会话",
        LANG_ES: "🧹 Reiniciar sesión",
        LANG_FR: "🧹 Réinitialiser la session",
    },
    "webcam.no_entities_tracked": {
        LANG_EN: "No entities tracked yet. Start the webcam above and move something within the frame.",
        LANG_ZH: "还没有追踪到任何实体。启动上方的摄像头，并在画面中移动一些东西。",
        LANG_ES: "Aún no se rastrean entidades. Inicia la cámara web de arriba y mueve algo dentro del encuadre.",
        LANG_FR: "Aucune entité suivie pour l'instant. Démarrez la webcam ci-dessus et déplacez quelque chose dans le cadre.",
    },
    "webcam.no_joint_state": {
        LANG_EN: "No joint quantum state yet. Coherence chart will appear after the first rebuild (every {n} frames by default).",
        LANG_ZH: "还没有联合量子态。相干性图表将在首次重建后出现（默认每 {n} 帧一次）。",
        LANG_ES: "Aún no hay estado cuántico conjunto. El gráfico de coherencia aparecerá tras la primera reconstrucción (cada {n} fotogramas por defecto).",
        LANG_FR: "Aucun état quantique conjoint pour l'instant. Le graphique de cohérence apparaîtra après la première reconstruction (tous les {n} images par défaut).",
    },
    "webcam.ask_vision_header": {
        LANG_EN: "🎯 Ask vision LLM about the current scene",
        LANG_ZH: "🎯 就当前场景询问视觉 LLM",
        LANG_ES: "🎯 Pregunta al LLM de visión sobre la escena actual",
        LANG_FR: "🎯 Interroger le LLM de vision sur la scène actuelle",
    },
    "webcam.capture_predict": {
        LANG_EN: "📸 Capture & predict",
        LANG_ZH: "📸 捕获并预测",
        LANG_ES: "📸 Capturar y predecir",
        LANG_FR: "📸 Capturer et prédire",
    },
    "webcam.cannot_capture": {
        LANG_EN: "Cannot capture yet: {reason}",
        LANG_ZH: "尚无法捕获：{reason}",
        LANG_ES: "Aún no se puede capturar: {reason}",
        LANG_FR: "Capture impossible pour l'instant : {reason}",
    },
    "webcam.err_no_question": {
        LANG_EN: "Please type a question first.",
        LANG_ZH: "请先输入一个问题。",
        LANG_ES: "Escribe primero una pregunta.",
        LANG_FR: "Veuillez d'abord saisir une question.",
    },
    "webcam.err_no_handle": {
        LANG_EN: "Please enter a handle (any string is fine).",
        LANG_ZH: "请输入一个用户名（任意字符串均可）。",
        LANG_ES: "Introduce un identificador (cualquier texto sirve).",
        LANG_FR: "Veuillez saisir un identifiant (n'importe quel texte convient).",
    },
    "webcam.footer_persisted": {
        LANG_EN: "Camera frames stream to the perception layer in memory only; nothing about the stream is persisted.",
        LANG_ZH: "摄像头帧仅在内存中流向感知层；关于该流的任何内容都不会被持久化。",
        LANG_ES: "Los fotogramas de la cámara se transmiten a la capa de percepción solo en memoria; nada de la transmisión se guarda.",
        LANG_FR: "Les images de la caméra sont transmises à la couche de perception uniquement en mémoire ; rien du flux n'est conservé.",
    },
    "webcam.footer_frames_only": {
        LANG_EN: "Frames-only preview — full perception + quantum stages are enabled when the host has the parent Omytea package available.",
        LANG_ZH: "仅帧预览——当主机具备父级 Omytea 包时，完整的感知 ＋ 量子阶段才会启用。",
        LANG_ES: "Vista previa solo de fotogramas: las etapas completas de percepción + cuántica se habilitan cuando el host dispone del paquete Omytea padre.",
        LANG_FR: "Aperçu images seules — les étapes complètes de perception + quantique sont activées lorsque l'hôte dispose du paquet Omytea parent.",
    },
    # -----  Score-due reminder banner  -----
    "score.due_banner": {
        LANG_EN: "📅 **Time to score**: {decision} — predicted {when}. How did this future actually play out?",
        LANG_ZH: "📅 **该打分了**：{decision} —— 预测于 {when}。这个未来实际是怎么发展的？",
        LANG_ES: "📅 **Hora de puntuar**: {decision} — predicho {when}. ¿Cómo se desarrolló realmente este futuro?",
        LANG_FR: "📅 **Moment de noter** : {decision} — prédit {when}. Comment ce futur s'est-il réellement déroulé ?",
    },
    "score.due_decision_fallback": {
        LANG_EN: "(your prediction)",
        LANG_ZH: "（你的预测）",
        LANG_ES: "(tu predicción)",
        LANG_FR: "(votre prédiction)",
    },
    "score.now_button": {
        LANG_EN: "Score now →",
        LANG_ZH: "立即打分 →",
        LANG_ES: "Puntuar ahora →",
        LANG_FR: "Noter maintenant →",
    },
    "score.when_months_ago": {
        LANG_EN: "~{n} months ago",
        LANG_ZH: "约 {n} 个月前",
        LANG_ES: "hace ~{n} meses",
        LANG_FR: "il y a ~{n} mois",
    },
    "score.when_weeks_ago": {
        LANG_EN: "~{n} weeks ago",
        LANG_ZH: "约 {n} 周前",
        LANG_ES: "hace ~{n} semanas",
        LANG_FR: "il y a ~{n} semaines",
    },
    "score.when_days_ago": {
        LANG_EN: "{n} days ago",
        LANG_ZH: "{n} 天前",
        LANG_ES: "hace {n} días",
        LANG_FR: "il y a {n} jours",
    },
    # -----  Misc surfaces caught in the iter-66 sweep  -----
    "banner.beta_dismiss": {
        LANG_EN: "Got it — continue",
        LANG_ZH: "知道了——继续",
        LANG_ES: "Entendido — continuar",
        LANG_FR: "Compris — continuer",
    },
    "composer.advanced_options": {
        LANG_EN: "Advanced options",
        LANG_ZH: "高级选项",
        LANG_ES: "Opciones avanzadas",
        LANG_FR: "Options avancées",
    },
    "composer.user_handle_required": {
        LANG_EN: "Please provide a user handle.",
        LANG_ZH: "请提供一个用户名。",
        LANG_ES: "Indica un identificador de usuario, por favor.",
        LANG_FR: "Veuillez fournir un identifiant utilisateur.",
    },
    "composer.compilation_failed": {
        LANG_EN: "Compilation failed: {exc}",
        LANG_ZH: "编译失败：{exc}",
        LANG_ES: "Error de compilación: {exc}",
        LANG_FR: "Échec de la compilation : {exc}",
    },
    "result.drilldown.failed": {
        LANG_EN: "Drill-down failed: {exc}",
        LANG_ZH: "深入研究失败：{exc}",
        LANG_ES: "Error del análisis: {exc}",
        LANG_FR: "Échec de l'analyse : {exc}",
    },
    "measurement.no_predictions_for_user": {
        LANG_EN: "No predictions found for user `{user_id}`.",
        LANG_ZH: "未找到用户 `{user_id}` 的任何预测。",
        LANG_ES: "No se encontraron predicciones para el usuario `{user_id}`.",
        LANG_FR: "Aucune prédiction trouvée pour l'utilisateur `{user_id}`.",
    },
    "video.ingestion_failed": {
        LANG_EN: "Video ingestion failed: {reason}\n\nIf this says 'opencv-python or numpy not installed', run: `pip install opencv-python-headless`. If it says 'mock mode enabled', unset `OMYTEA_CONSOLE_MOCK` in your shell.",
        LANG_ZH: "视频读取失败：{reason}\n\n如果提示「opencv-python or numpy not installed」，请运行：`pip install opencv-python-headless`。如果提示「mock mode enabled」，请在 shell 中取消设置 `OMYTEA_CONSOLE_MOCK`。",
        LANG_ES: "Error al procesar el video: {reason}\n\nSi dice 'opencv-python or numpy not installed', ejecuta: `pip install opencv-python-headless`. Si dice 'mock mode enabled', desactiva `OMYTEA_CONSOLE_MOCK` en tu shell.",
        LANG_FR: "Échec du traitement de la vidéo : {reason}\n\nSi le message indique « opencv-python or numpy not installed », exécutez : `pip install opencv-python-headless`. S'il indique « mock mode enabled », désactivez `OMYTEA_CONSOLE_MOCK` dans votre shell.",
    },
    "video.sampled_summary": {
        LANG_EN: "✓ Sampled {n_frames} frames · {n_entities} entities tracked · detector: `{detector}` · video duration: {duration:.1f}s @ {fps:.0f}fps",
        LANG_ZH: "✓ 采样 {n_frames} 帧 · 追踪到 {n_entities} 个实体 · 检测器：`{detector}` · 视频时长：{duration:.1f}秒 @ {fps:.0f}fps",
        LANG_ES: "✓ {n_frames} fotogramas muestreados · {n_entities} entidades rastreadas · detector: `{detector}` · duración del video: {duration:.1f}s @ {fps:.0f}fps",
        LANG_FR: "✓ {n_frames} images échantillonnées · {n_entities} entités suivies · détecteur : `{detector}` · durée de la vidéo : {duration:.1f}s @ {fps:.0f}fps",
    },
    "video.fallback_warning": {
        LANG_EN: "⚠ Vision LLM fallback engaged. {reason}\n\nThe branches below come from a deterministic stub and are NOT grounded in the specific video content. The entity-tracking + quantum-operator evolution still uses the real per-frame detections.",
        LANG_ZH: "⚠ 已启用视觉 LLM 回退。{reason}\n\n下方的分支来自一个确定性的桩，并未基于具体的视频内容。实体追踪 ＋ 量子算子演化仍使用真实的逐帧检测。",
        LANG_ES: "⚠ Respaldo del LLM de visión activado. {reason}\n\nLas ramas de abajo provienen de un stub determinista y NO se basan en el contenido específico del video. El seguimiento de entidades + la evolución del operador cuántico siguen usando las detecciones reales por fotograma.",
        LANG_FR: "⚠ Repli du LLM de vision activé. {reason}\n\nLes branches ci-dessous proviennent d'un stub déterministe et ne sont PAS fondées sur le contenu vidéo spécifique. Le suivi d'entités + l'évolution de l'opérateur quantique utilisent toujours les détections réelles image par image.",
    },
    "video.scene_compilation_failed": {
        LANG_EN: "Scene compilation failed: {exc}",
        LANG_ZH: "场景编译失败：{exc}",
        LANG_ES: "Error de compilación de la escena: {exc}",
        LANG_FR: "Échec de la compilation de la scène : {exc}",
    },
    "video.evolution_skipped": {
        LANG_EN: "Evolution skipped: {reason}",
        LANG_ZH: "已跳过演化：{reason}",
        LANG_ES: "Evolución omitida: {reason}",
        LANG_FR: "Évolution ignorée : {reason}",
    },
    "video.offdiag_caption": {
        LANG_EN: "Off-diagonal magnitude |⟨joint_i | ρ | joint_j⟩| over {n_ticks} Lindblad ticks at γ={gamma:.2f}. Each line = one joint-hypothesis pair. Lines converging to zero = those two correlated futures have lost their coherence and are now effectively independent classical outcomes.",
        LANG_ZH: "非对角幅值 |⟨joint_i | ρ | joint_j⟩|，历经 {n_ticks} 个 Lindblad 时间步，γ={gamma:.2f}。每条线 ＝ 一对联合假设。线收敛到零 ＝ 这两个相关的未来已失去相干性，现在实际上是独立的经典结果。",
        LANG_ES: "Magnitud fuera de diagonal |⟨joint_i | ρ | joint_j⟩| a lo largo de {n_ticks} pasos de Lindblad a γ={gamma:.2f}. Cada línea = un par de hipótesis conjuntas. Las líneas que convergen a cero = esos dos futuros correlacionados han perdido su coherencia y ahora son resultados clásicos prácticamente independientes.",
        LANG_FR: "Magnitude hors-diagonale |⟨joint_i | ρ | joint_j⟩| sur {n_ticks} pas de Lindblad à γ={gamma:.2f}. Chaque ligne = une paire d'hypothèses conjointes. Les lignes convergeant vers zéro = ces deux futurs corrélés ont perdu leur cohérence et sont désormais des issues classiques pratiquement indépendantes.",
    },
    "webcam.rebuilt_caption": {
        LANG_EN: "Rebuilt at frame {frame}. Each line = one joint-hypothesis pair magnitude over Lindblad ticks. Lines decaying to 0 = correlated futures losing coherence.",
        LANG_ZH: "在第 {frame} 帧重建。每条线 ＝ 一对联合假设的幅值随 Lindblad 时间步的变化。线衰减到 0 ＝ 相关的未来正在失去相干性。",
        LANG_ES: "Reconstruido en el fotograma {frame}. Cada línea = la magnitud de un par de hipótesis conjuntas a lo largo de los pasos de Lindblad. Las líneas que decaen a 0 = futuros correlacionados que pierden coherencia.",
        LANG_FR: "Reconstruit à l'image {frame}. Chaque ligne = la magnitude d'une paire d'hypothèses conjointes au fil des pas de Lindblad. Les lignes décroissant vers 0 = futurs corrélés perdant leur cohérence.",
    },
    "webcam.storage_failed": {
        LANG_EN: "Saved-prediction storage failed (prediction still shown below): {exc}",
        LANG_ZH: "预测存储失败（预测仍显示在下方）：{exc}",
        LANG_ES: "Error al guardar la predicción (la predicción aún se muestra abajo): {exc}",
        LANG_FR: "Échec de l'enregistrement de la prédiction (la prédiction reste affichée ci-dessous) : {exc}",
    },
    # -----  Numbered step narrative (legible workspace logic)  -----
    "workspace.step1.title": {
        LANG_EN: "①  What are you deciding between?",
        LANG_ZH: "①  你在纠结什么决定？",
        LANG_ES: "①  ¿Entre qué estás decidiendo?",
        LANG_FR: "①  Entre quoi hésitez-vous ?",
    },
    "workspace.step1.sub": {
        LANG_EN: "Write it below in a sentence — or tap an example to try.",
        LANG_ZH: "在下面一句话写下来，或点一个例子快速试试。",
        LANG_ES: "Escríbelo abajo en una frase — o toca un ejemplo.",
        LANG_FR: "Écrivez-le en une phrase ci-dessous — ou touchez un exemple.",
    },
    "workspace.step2.title": {
        LANG_EN: "Your possible futures",
        LANG_ZH: "你的多重未来",
        LANG_ES: "Tus futuros posibles",
        LANG_FR: "Vos futurs possibles",
    },
    "workspace.step2.sub_idle": {
        LANG_EN: "Type a decision below — each path's odds appear here.",
        LANG_ZH: "在下面写下你的决定，每条路有多大可能就会画在这里。",
        LANG_ES: "Escribe una decisión abajo — aquí aparecen las probabilidades.",
        LANG_FR: "Saisissez une décision ci-dessous — les probabilités s'affichent ici.",
    },
    # -----  Output-region view toggle (OMY-V415 #60 D)  -----
    "output.view.quantum": {
        LANG_EN: "Quantum heatmap",
        LANG_ZH: "量子热力图",
        LANG_ES: "Mapa cuántico",
        LANG_FR: "Carte quantique",
    },
    "output.view.xuanxue": {
        LANG_EN: "Metaphysics lens",
        LANG_ZH: "玄学时轮",
        LANG_ES: "Lente metafísica",
        LANG_FR: "Loupe métaphysique",
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
            "heatmap and the Metaphysics lens. The quantum view is "
            "the default; the Metaphysics lens is the opt-in alternate."
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
            "Each row is one future; each column a moment on the way "
            "to your horizon."
        ),
        LANG_ZH: "每一行是一条未来分支，每一列是通往你时限路上的一个时刻。",
        LANG_ES: (
            "Cada fila es un futuro; cada columna un momento camino "
            "a tu horizonte."
        ),
        LANG_FR: (
            "Chaque ligne est un futur ; chaque colonne un instant "
            "vers votre horizon."
        ),
    },
    # Iter #21 P1.4 part 1 — per-branch "Why this probability?"
    # reveal. Founder live-audit: "给每个概率加一句 '为什么是这个概率
    # / 哪些输入最影响它 / 置信度多高'". Skeleton uses existing
    # Hypothesis fields; full ΔP-style driver attribution comes later.
    "result.why_probability_label": {
        LANG_EN: "Why this probability?",
        LANG_ZH: "为什么是这个概率？",
        LANG_ES: "¿Por qué esta probabilidad?",
        LANG_FR: "Pourquoi cette probabilité ?",
    },
    "result.why_hinges_on": {
        LANG_EN: "Hinges on:",
        LANG_ZH: "关键不确定性：",
        LANG_ES: "Depende de:",
        LANG_FR: "Dépend de :",
    },
    "result.why_depends_on": {
        LANG_EN: "Requires decision:",
        LANG_ZH: "依赖决策：",
        LANG_ES: "Requiere decisión:",
        LANG_FR: "Décision requise :",
    },
    "result.why_no_extras": {
        # Honest fallback when the underlying Hypothesis surfaces
        # neither a key uncertainty driver nor a decision dependency.
        # Better than rendering an empty expander or fabricating a
        # plausible-sounding sentence.
        LANG_EN: (
            "No specific driver was surfaced for this branch — its "
            "probability comes from the base scenario distribution."
        ),
        LANG_ZH: (
            "这条分支没有被识别出特定驱动因子 — 概率来自基础场景分布。"
        ),
        LANG_ES: (
            "No se ha identificado un motor específico para esta rama — "
            "su probabilidad procede de la distribución base."
        ),
        LANG_FR: (
            "Aucun moteur spécifique n'a été identifié pour cette branche "
            "— sa probabilité provient de la distribution de base."
        ),
    },
    "result.why_drivers_coming": {
        # Iter 21 placeholder, kept for backwards compatibility but
        # no longer rendered in iter 22+ since the real top-drivers
        # list now ships (key: result.why_top_drivers).
        LANG_EN: (
            "Full driver breakdown — which inputs pushed this up or "
            "down, and how much would change it — is coming in a "
            "later release."
        ),
        LANG_ZH: (
            "完整的驱动因子拆解 — 哪些输入把这条概率往上推、哪些往下"
            "拉、以及多大的变化能改变它 — 将在后续版本中加入。"
        ),
        LANG_ES: (
            "El desglose completo de impulsores — qué entradas la "
            "subieron o bajaron y cuánto cambiaría — llegará en una "
            "versión posterior."
        ),
        LANG_FR: (
            "Décomposition complète des moteurs — quels intrants l'ont "
            "fait monter ou descendre, et de combien — à venir dans "
            "une prochaine version."
        ),
    },
    # Iter #22 P1.4 Phase 2 — real driver list shipped, filtered from
    # recommended_evidence by target_branch == branch.label. Each item
    # carries an evidence_label, an expected_delta_p, and a rationale.
    "result.why_top_drivers": {
        LANG_EN: "Top drivers for this branch",
        LANG_ZH: "影响这条分支的主要因子",
        LANG_ES: "Principales impulsores para esta rama",
        LANG_FR: "Principaux moteurs de cette branche",
    },
    # Iter #26 — confidence tier i18n (P1.4 Phase 3 follow-up).
    # Iter 25 surfaced an English-only qualitative tier next to the
    # probability in the meta line. These three keys route those
    # strings through T() so ZH/ES/FR users see the right label.
    # The wording for each language was chosen so the tier reads as
    # qualitative meta-info (italicized in the caption) rather than
    # a competing number.
    # Iter #30 — confidence tier copy made plain-English actionable.
    # Founder round-2 audit: "soft estimate / single-source 是诚实的,
    # 但初级用户可能不知道它意味着什么". Now reads as "what does this
    # mean for me" not as quant jargon.
    "result.confidence_well_calibrated": {
        LANG_EN: "high confidence — multiple levers identified",
        LANG_ZH: "高置信度 · 已识别多个杠杆",
        LANG_ES: "alta confianza — varios factores identificados",
        LANG_FR: "haute confiance — plusieurs leviers identifiés",
    },
    "result.confidence_single_source": {
        LANG_EN: "medium confidence — based on one signal",
        LANG_ZH: "中等置信度 · 基于单一信号",
        LANG_ES: "confianza media — basada en una señal",
        LANG_FR: "confiance moyenne — basée sur un signal",
    },
    "result.confidence_soft_estimate": {
        LANG_EN: "low confidence — collect evidence to sharpen",
        LANG_ZH: "低置信度 · 收集证据可以更准",
        LANG_ES: "baja confianza — recopilar evidencia para refinar",
        LANG_FR: "faible confiance — collecter des preuves pour affiner",
    },
    # Iter #40 — probability_provenance labels (founder round-3 #2).
    # The "Source:" tag tells the user WHERE the probability number
    # came from — orthogonal to the confidence tier which answers HOW
    # STRONG the signal is. Together they prevent "soft estimate"
    # being misread as statistical confidence (the founder's
    # specific concern). 4 values × 4 locales.
    "result.provenance_source_label": {
        LANG_EN: "Source:",
        LANG_ZH: "来源:",
        LANG_ES: "Fuente:",
        LANG_FR: "Source :",
    },
    "result.provenance_llm_estimate": {
        LANG_EN: "LLM estimate (no calibration history yet)",
        LANG_ZH: "LLM 估算 (尚无校准历史)",
        LANG_ES: "estimación de LLM (sin historial calibrado)",
        LANG_FR: "estimation LLM (pas encore d'historique calibré)",
    },
    "result.provenance_evidence_proxy": {
        LANG_EN: "evidence-weighted (driver count proxies signal strength)",
        LANG_ZH: "证据加权 (用驱动因子数量代理信号强度)",
        LANG_ES: "ponderado por evidencia (recuento de impulsores)",
        LANG_FR: "pondéré par preuves (nombre de moteurs identifiés)",
    },
    "result.provenance_historical_calibrated": {
        LANG_EN: "historically calibrated (your prior measurements)",
        LANG_ZH: "历史校准 (基于你过去的打分记录)",
        LANG_ES: "calibrado históricamente (mediciones previas)",
        LANG_FR: "calibré historiquement (vos mesures antérieures)",
    },
    "result.provenance_user_adjusted": {
        LANG_EN: "user-adjusted (you nudged this manually)",
        LANG_ZH: "用户调整 (你手动改过)",
        LANG_ES: "ajustado por usuario (modificado manualmente)",
        LANG_FR: "ajusté par l'utilisateur (modification manuelle)",
    },
    # Iter #41 — Measurement-Update prediction_id input field (founder
    # round-4 P0 #3). Users arriving from a .ics calendar link on a
    # different device can paste the prediction ID directly without
    # remembering their original `tester-xxxx` handle.
    "measurement.lookup_by_id_label": {
        LANG_EN: "Have a prediction ID? Paste it here",
        LANG_ZH: "有 prediction ID? 粘贴在这里",
        LANG_ES: "¿Tienes un ID de predicción? Pégalo aquí",
        LANG_FR: "Vous avez un ID de prédiction ? Collez-le ici",
    },
    "measurement.pid_input_label": {
        LANG_EN: "Prediction ID (from your calendar reminder)",
        LANG_ZH: "Prediction ID (从日历提醒里复制)",
        LANG_ES: "ID de predicción (del recordatorio de calendario)",
        LANG_FR: "ID de prédiction (depuis votre rappel calendrier)",
    },
    "measurement.pid_input_placeholder": {
        LANG_EN: "abc12345-...",
        LANG_ZH: "abc12345-...",
        LANG_ES: "abc12345-...",
        LANG_FR: "abc12345-...",
    },
    "measurement.not_found_by_id": {
        LANG_EN: (
            "No prediction found for that ID. Double-check the UUID "
            "from your calendar reminder."
        ),
        LANG_ZH: (
            "没找到这个 ID 对应的预测. 请核对日历提醒里的 UUID."
        ),
        LANG_ES: (
            "No se encontró ninguna predicción para ese ID. Revisa "
            "el UUID en tu recordatorio."
        ),
        LANG_FR: (
            "Aucune prédiction trouvée pour cet ID. Vérifiez l'UUID "
            "dans votre rappel."
        ),
    },
    "measurement.found_by_id": {
        LANG_EN: "Opened by prediction ID",
        LANG_ZH: "通过 prediction ID 打开",
        LANG_ES: "Abierto por ID de predicción",
        LANG_FR: "Ouvert par ID de prédiction",
    },
    "measurement.handle_label": {
        LANG_EN: "Your handle (if you remember it)",
        LANG_ZH: "你的 handle (如果记得)",
        LANG_ES: "Tu identificador (si lo recuerdas)",
        LANG_FR: "Votre identifiant (si vous vous en souvenez)",
    },
    "measurement.outcome_validation_error": {
        LANG_EN: (
            "Set at least one outcome above 0 — leaving everything "
            "at 0 means 'no outcome reported', which pollutes "
            "calibration data. Move the slider(s) for whichever "
            "branch(es) actually materialized."
        ),
        LANG_ZH: (
            "请将至少一个分支调到 0 以上 — 全部为 0 表示\"没有任何"
            "结果\", 会污染校准数据. 把实际发生的分支滑块移动一下."
        ),
        LANG_ES: (
            "Pon al menos un resultado por encima de 0 — dejar todo "
            "en 0 contamina los datos de calibración. Mueve los "
            "deslizadores para las ramas que realmente ocurrieron."
        ),
        LANG_FR: (
            "Mettez au moins un résultat au-dessus de 0 — tout laisser "
            "à 0 pollue les données de calibration. Déplacez les "
            "curseurs pour les branches qui se sont réellement "
            "produites."
        ),
    },
    # Iter #42 B1 — top-of-result CTA row keys. Founder round-4
    # audit: "Add calendar / Copy ID / Score later" were buried
    # below the entire result page. Now surfaced right under the
    # prediction-ID caption.
    "result.cta.add_calendar": {
        LANG_EN: "📅  Add to calendar",
        LANG_ZH: "📅  加日历提醒",
        LANG_ES: "📅  Añadir al calendario",
        LANG_FR: "📅  Ajouter au calendrier",
    },
    "result.cta.add_calendar.hint": {
        LANG_EN: (
            "Downloads a .ics calendar event for the review date so "
            "the reminder lives in your real calendar — not just "
            "this app."
        ),
        LANG_ZH: (
            "下载 .ics 日历事件，复盘提醒会进入你真实的日历，"
            "不止存在 app 里。"
        ),
        LANG_ES: (
            "Descarga un evento de calendario .ics para la fecha de "
            "revisión — el recordatorio vive en tu calendario real."
        ),
        LANG_FR: (
            "Télécharge un événement .ics pour la date de revue — "
            "le rappel vit dans votre vrai calendrier."
        ),
    },
    "result.cta.score_later": {
        LANG_EN: "Score later  →",
        LANG_ZH: "稍后打分  →",
        LANG_ES: "Puntuar después  →",
        LANG_FR: "Évaluer plus tard  →",
    },
    "result.cta.score_later.hint": {
        LANG_EN: (
            "Opens the Measurement Update flow with this prediction "
            "pre-loaded — useful if you already know the outcome."
        ),
        LANG_ZH: (
            "打开 Measurement Update 流程并预加载这条预测 — "
            "如果你已经知道结果可以直接打分。"
        ),
        LANG_ES: (
            "Abre el flujo de Measurement Update con esta predicción "
            "precargada — útil si ya conoces el resultado."
        ),
        LANG_FR: (
            "Ouvre le flux Measurement Update avec cette prédiction "
            "préchargée — utile si vous connaissez déjà le résultat."
        ),
    },
    # Iter #43 — JSON snapshot download (ephemeral-storage
    # mitigation). The demo DB sits on Streamlit Cloud's
    # ephemeral filesystem; offering the user a `.json` they can
    # keep locally means their PMF data survives any redeploy.
    "result.cta.save_snapshot": {
        LANG_EN: "💾  Save snapshot",
        LANG_ZH: "💾  保存快照",
        LANG_ES: "💾  Guardar copia",
        LANG_FR: "💾  Sauvegarder",
    },
    "result.cta.save_snapshot.hint": {
        LANG_EN: (
            "Downloads a .json copy of this prediction to your "
            "device. The demo's server storage is ephemeral — "
            "keeping the snapshot means you can restore the "
            "prediction (or send it to us to restore) if our DB "
            "is wiped before you score it."
        ),
        LANG_ZH: (
            "下载这条预测的 .json 副本到你的设备。Demo 服务器存储是"
            "易失的 — 留一份本地快照，万一服务器在你打分前被清空，"
            "你仍能恢复这条预测（或发回给我们恢复）。"
        ),
        LANG_ES: (
            "Descarga una copia .json de esta predicción a tu "
            "dispositivo. El almacenamiento del servidor demo es "
            "efímero — guardar la copia permite restaurar la "
            "predicción si la base de datos se borra."
        ),
        LANG_FR: (
            "Télécharge une copie .json de cette prédiction sur "
            "votre appareil. Le stockage du serveur démo est "
            "éphémère — garder la copie permet de restaurer la "
            "prédiction si la base de données est effacée."
        ),
    },
    "result.save.zone_title": {
        LANG_EN: "Save this, or come back when you know the outcome",
        LANG_ZH: "保存，或在知道结果后回来打分",
        LANG_ES: "Guárdalo o vuelve cuando sepas el resultado",
        LANG_FR: "Enregistrez-le ou revenez quand vous connaîtrez le résultat",
    },
    "result.save.zone_sub": {
        LANG_EN: "Keep a copy, drop a reminder in your calendar, or score it once the outcome is in.",
        LANG_ZH: "留个副本、在日历里设个提醒，或在结果出来后给它打分。",
        LANG_ES: "Guarda una copia, añade un recordatorio al calendario o puntúalo cuando llegue el resultado.",
        LANG_FR: "Gardez une copie, ajoutez un rappel à votre agenda, ou évaluez-le une fois le résultat connu.",
    },
    "result.save.id_label": {
        LANG_EN: "Your prediction ID — keep this to score it later (hover to copy):",
        LANG_ZH: "你的预测 ID — 留着它以便日后打分（悬停复制）：",
        LANG_ES: "Tu ID de predicción — guárdalo para puntuarlo después (pasa el cursor para copiar):",
        LANG_FR: "Votre ID de prédiction — gardez-le pour l'évaluer plus tard (survolez pour copier) :",
    },
    "result.review_anchor": {
        # Slimmed bottom anchor. Iter #53 — the calendar download moved
        # from the top to the "save / come back later" zone below the
        # chart, so this pointer now says "save section above".
        LANG_EN: (
            "Reminder set for {review_date} (about {horizon} out). "
            "The calendar download is in the save section above."
        ),
        LANG_ZH: (
            "提醒已设为 {review_date}（约 {horizon} 后）。"
            "日历下载在上方的保存区。"
        ),
        LANG_ES: (
            "Recordatorio para {review_date} (a unos {horizon} "
            "vista). La descarga del calendario está en la sección "
            "de guardado, más arriba."
        ),
        LANG_FR: (
            "Rappel prévu pour {review_date} (environ {horizon} "
            "plus tard). Le téléchargement du calendrier est dans "
            "la section d'enregistrement, plus haut."
        ),
    },
    # Iter #46 — restore-from-snapshot widget on Measurement
    # Update. Closes the snapshot↔restore loop with the iter 43
    # `💾 Save snapshot` (.json) download on the result page so
    # beta testers can survive any data wipe (Turso outage,
    # accidental redeploy, account deletion) by keeping their
    # .json locally.
    "measurement.restore_label": {
        LANG_EN: "Restore from .json snapshot",
        LANG_ZH: "从 .json 快照恢复",
        LANG_ES: "Restaurar desde .json",
        LANG_FR: "Restaurer depuis .json",
    },
    "measurement.restore_hint": {
        LANG_EN: (
            "Upload the `omytea-prediction-*.json` file you "
            "downloaded from the result page's **💾 Save snapshot** "
            "button. Use this if you can't find the prediction in "
            "the demo's storage anymore."
        ),
        LANG_ZH: (
            "上传你在结果页 **💾 保存快照** 按钮下载的 "
            "`omytea-prediction-*.json` 文件。"
            "如果在 demo 存储里找不到那条预测了，用这个恢复。"
        ),
        LANG_ES: (
            "Sube el archivo `omytea-prediction-*.json` que "
            "descargaste con el botón **💾 Guardar copia** en la "
            "página de resultados."
        ),
        LANG_FR: (
            "Téléverse le fichier `omytea-prediction-*.json` que tu "
            "as téléchargé depuis le bouton **💾 Sauvegarder** sur "
            "la page de résultats."
        ),
    },
    "measurement.restore_upload_label": {
        LANG_EN: "Drop .json file here (or click to browse)",
        LANG_ZH: "把 .json 拖到这里 (或点击浏览)",
        LANG_ES: "Suelta el .json aquí (o haz clic para buscar)",
        LANG_FR: "Dépose le .json ici (ou clique pour parcourir)",
    },
    "measurement.restore_invalid": {
        LANG_EN: (
            "This file doesn't look like an Omytea prediction "
            "snapshot. Re-download from the result page."
        ),
        LANG_ZH: (
            "这个文件不像是 Omytea 预测快照。请重新从结果页下载。"
        ),
        LANG_ES: (
            "Este archivo no parece una instantánea de Omytea. "
            "Descárgalo de nuevo desde la página de resultados."
        ),
        LANG_FR: (
            "Ce fichier ne ressemble pas à un instantané Omytea. "
            "Re-télécharge depuis la page de résultats."
        ),
    },
    "measurement.restore_schema_mismatch": {
        LANG_EN: (
            "This snapshot uses a different schema version. It may "
            "be from a future Omytea release; we can't restore it "
            "automatically. Contact support with the file attached."
        ),
        LANG_ZH: (
            "这份快照使用了不同的 schema 版本。可能来自未来版本的 "
            "Omytea；无法自动恢复。请把文件发给客服。"
        ),
        LANG_ES: (
            "Esta copia usa una versión de esquema diferente. No "
            "podemos restaurarla automáticamente. Contacta soporte "
            "con el archivo adjunto."
        ),
        LANG_FR: (
            "Cette sauvegarde utilise une autre version du schéma. "
            "Restauration automatique impossible — contacte le "
            "support avec le fichier en pièce jointe."
        ),
    },
    "measurement.restore_failed": {
        LANG_EN: "Couldn't restore this prediction",
        LANG_ZH: "无法恢复这条预测",
        LANG_ES: "No se pudo restaurar esta predicción",
        LANG_FR: "Impossible de restaurer cette prédiction",
    },
    "measurement.restore_success": {
        LANG_EN: "Restored — scoring this prediction now",
        LANG_ZH: "已恢复 — 现在为这条预测打分",
        LANG_ES: "Restaurada — puntuando esta predicción",
        LANG_FR: "Restaurée — évaluation en cours",
    },
    # Iter #42 B3 — Measurement Update PMF required-pick validation
    # messages. Founder round-4 audit: defaults were pre-biased
    # (NPS=5 / Sean Ellis 'Somewhat disappointed' / effort
    # 'needed_reminder') — change to required explicit pick so the
    # PMF signal isn't an artifact of users clicking submit
    # without reading.
    "measurement.sean_ellis_required": {
        LANG_EN: (
            "Please pick one option for the Sean Ellis "
            "disappointment test before submitting."
        ),
        LANG_ZH: (
            "提交前请为 Sean Ellis 失望测试选择一个选项。"
        ),
        LANG_ES: (
            "Por favor elige una opción del test de decepción de "
            "Sean Ellis antes de enviar."
        ),
        LANG_FR: (
            "Choisissez une option pour le test de déception de "
            "Sean Ellis avant de soumettre."
        ),
    },
    "measurement.effort_required": {
        LANG_EN: (
            "Please pick one option for the effort test before "
            "submitting."
        ),
        LANG_ZH: (
            "提交前请为努力测试选择一个选项。"
        ),
        LANG_ES: (
            "Por favor elige una opción del test de esfuerzo antes "
            "de enviar."
        ),
        LANG_FR: (
            "Choisissez une option pour le test d'effort avant de "
            "soumettre."
        ),
    },
    # Iter #41 — beta test consent banner (founder round-4 P1 #5).
    # Shown above the cold-start composer so first-time visitors
    # understand the data posture before they type anything.
    "beta.banner_title": {
        LANG_EN: "Research beta — please read",
        LANG_ZH: "研究 beta — 请先阅读",
        LANG_ES: "Beta de investigación — por favor lee",
        LANG_FR: "Bêta de recherche — à lire",
    },
    # Iter #48 — compacted to ~2 lines so the cold-start fold leads
    # with the actionable input (chips + decision field) instead of
    # a 5-line wall of text. Keeps the load-bearing consent (beta /
    # don't-paste-sensitive / data-on-server / desktop); the
    # save-the-ID + 3-month detail is reinforced on the result
    # page's CTA row + reminder, so it's dropped from first paint.
    "beta.banner_body": {
        LANG_EN: (
            "Early research beta — best on desktop. **Don't paste "
            "sensitive info** (bank, passport, SSN, other people's "
            "full names). Predictions save to the demo server; see "
            "Privacy for details."
        ),
        LANG_ZH: (
            "早期研究 beta，建议用桌面浏览器。**不要输入敏感信息**"
            "（银行账号、护照、SSN、第三方全名）。预测会存到 demo "
            "服务器；详见隐私政策。"
        ),
        LANG_ES: (
            "Beta de investigación temprana — mejor en escritorio. "
            "**No pegues información sensible** (banco, pasaporte, "
            "SSN, nombres de terceros). Las predicciones se guardan "
            "en el servidor demo; ver Privacidad."
        ),
        LANG_FR: (
            "Bêta de recherche précoce — préférez un ordinateur. "
            "**Ne collez pas d'informations sensibles** (banque, "
            "passeport, noms de tiers). Les prédictions sont "
            "enregistrées sur le serveur démo ; voir Confidentialité."
        ),
    },
    "result.why_no_specific_drivers": {
        # Iter #30 — rewrite. Founder round-2 audit: previous copy
        # "No specific evidence items were attributed... half-finished
        # explanation". Now phrased as actionable next step instead of
        # apology — what the user can DO to sharpen the estimate.
        LANG_EN: (
            "To sharpen this branch's probability, focus on the key "
            "uncertainty above — that's the lever this estimate is "
            "most sensitive to."
        ),
        LANG_ZH: (
            "想让这条分支的概率更准, 重点看上面那条 \"hinges on\" — "
            "这是当前估计最敏感的杠杆。"
        ),
        LANG_ES: (
            "Para afinar la probabilidad de esta rama, céntrate en la "
            "incertidumbre clave de arriba — es la palanca a la que más "
            "responde la estimación."
        ),
        LANG_FR: (
            "Pour affiner la probabilité de cette branche, concentrez-vous "
            "sur l'incertitude clé ci-dessus — c'est le levier auquel "
            "l'estimation est la plus sensible."
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
        # Iter #8: emptied. "Hover a cell to highlight it · click a
        # cell for detail." is interaction instruction text — telling
        # the user the affordance instead of letting hover BE the
        # affordance. Standard direct-manipulation pattern: cells
        # respond when hovered/clicked; no caption needed.
        LANG_EN: "",
        LANG_ZH: "",
        LANG_ES: "",
        LANG_FR: "",
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
    "heatmap.preview_badge": {
        # Iteration #19 P1.2: short uppercase label in the heat-head
        # shown only when the heatmap is in idle mode (no prediction
        # has been submitted). Makes the cold-start state visually
        # unambiguous as illustrative rather than a generated result.
        LANG_EN: "Example preview",
        LANG_ZH: "示例预览",
        LANG_ES: "Vista previa de ejemplo",
        LANG_FR: "Aperçu d'exemple",
    },
    "heatmap.idle_note": {
        # Iteration #1: shortened from "The grid is uniform — a world
        # with no evidence yet. Run a prediction below..." (text-heavy
        # crutch) to a single soft pointer. The grid's own grey
        # uniformity is the "no evidence yet" cue; users don't need to
        # read it.
        # Iter #55 — the ONE idle line (narrative + reading are hidden in
        # idle mode now): merged pointer + how-to-read in a single breath.
        LANG_EN: (
            "Empty grid · waiting for your decision below ↓ — each row "
            "is one future, each column a moment toward your horizon."
        ),
        LANG_ZH: (
            "空网格 · 等待你在下方写下决定 ↓ —— 每一行是一条未来，"
            "每一列是通往时限路上的一个时刻。"
        ),
        LANG_ES: (
            "Cuadrícula vacía · esperando tu decisión abajo ↓ — cada "
            "fila es un futuro, cada columna un momento hacia tu "
            "horizonte."
        ),
        LANG_FR: (
            "Grille vide · en attente de votre décision ci-dessous ↓ — "
            "chaque ligne est un futur, chaque colonne un moment vers "
            "votre horizon."
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
    # -----  Heatmap card head + likelihood legend + reading narrative  -----
    # The {slot}s are filled in Python (render_heatmap_camera_component)
    # from the live branch distribution — v10's one-line answer sentence.
    "heatmap.head_title": {
        # Iter #3 — same de-jargonization as the outer title; the
        # heatmap's branch rows + horizon columns already SAY this.
        LANG_EN: "How likely each path is · over time",
        LANG_ZH: "每条路径的可能性 · 随时间变化",
        LANG_ES: "Qué probable es cada camino · en el tiempo",
        LANG_FR: "Probabilité de chaque voie · dans le temps",
    },
    "heatmap.head_hint": {
        LANG_EN: "click a cell for detail",
        LANG_ZH: "点击单元格查看详情",
        LANG_ES: "haz clic en una celda para ver el detalle",
        LANG_FR: "cliquez sur une cellule pour le détail",
    },
    "heatmap.legend_label": {
        LANG_EN: "Likelihood:",
        LANG_ZH: "可能性：",
        LANG_ES: "Probabilidad:",
        LANG_FR: "Vraisemblance :",
    },
    "heatmap.legend_rare": {
        LANG_EN: "rare",
        LANG_ZH: "罕见",
        LANG_ES: "raro",
        LANG_FR: "rare",
    },
    "heatmap.legend_likely": {
        LANG_EN: "most likely",
        LANG_ZH: "最可能",
        LANG_ES: "más probable",
        LANG_FR: "le plus probable",
    },
    "heatmap.y_axis_caption": {
        LANG_EN: "outcome branch",
        LANG_ZH: "结果分支",
        LANG_ES: "rama de resultado",
        LANG_FR: "branche d'issue",
    },
    "heatmap.narrative_prediction": {
        LANG_EN: (
            "Most likely “{branch}” — it carries about "
            "{pct}% of the probability mass at your {horizon}, with the "
            "distribution widening as the horizon stretches."
        ),
        LANG_ZH: (
            "最可能的是“{branch}”——在你的{horizon}时点"
            "它占据约 {pct}% 的概率质量，且分布随时限拉长而展宽。"
        ),
        LANG_ES: (
            "Lo más probable es “{branch}”: concentra cerca "
            "del {pct}% de la masa de probabilidad en tu {horizon}, y la "
            "distribución se amplía al alejarse el horizonte."
        ),
        LANG_FR: (
            "Le plus probable est « {branch} » : il "
            "porte environ {pct} % de la masse de probabilité "
            "à votre {horizon}, la distribution s'élargissant "
            "à mesure que l'horizon s'étire."
        ),
    },
    "heatmap.narrative_idle": {
        # Iteration #1 (design-self-explains): the empty-state used to
        # spell out the math ("distribution is uniform...") which is
        # exactly the kind of explainer-text crutch a first-time visitor
        # has to READ in order to understand. Replaced with a single
        # short prompt that *points* the user at the action — the grid's
        # own emptiness already conveys "no data yet".
        LANG_EN: "Your probability distribution will appear here ↓",
        LANG_ZH: "你的概率分布会显示在这里 ↓",
        LANG_ES: "Tu distribución de probabilidad aparecerá aquí ↓",
        LANG_FR: "Votre distribution de probabilité apparaîtra ici ↓",
    },
    "heatmap.narrative_live": {
        LANG_EN: (
            "The camera is driving the math — motion in the frame "
            "shifts where the probability mass concentrates, live."
        ),
        LANG_ZH: (
            "摄像头正在驱动计算——画面中的运动会实时改变"
            "概率质量聚集的位置。"
        ),
        LANG_ES: (
            "La cámara controla el cálculo: el movimiento en el "
            "cuadro desplaza, en vivo, dónde se concentra la masa de "
            "probabilidad."
        ),
        LANG_FR: (
            "La caméra pilote le calcul : le mouvement dans l'image "
            "déplace, en direct, là où se concentre la "
            "masse de probabilité."
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
        # Iter #16: quiet page name × 4 locales.
        LANG_EN: "Metaphysics lens · standalone",
        LANG_ZH: "玄学透镜 · 独立视图",
        LANG_ES: "Lente metafísica · vista independiente",
        LANG_FR: "Loupe métaphysique · vue autonome",
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
        # Iter #13 (design-self-explains): trimmed from a 4-line
        # paragraph explaining the lens's epistemic posture to one
        # short line. The MODEL → ↑/↓ → COMBINED visual delta strip
        # right above already SHOWS that the model's unweighted output
        # is rendered alongside the combined view — the paragraph was
        # telling the user what the design already conveys. Full
        # epistemic note lives in /docs/PRIVACY_POLICY.md (linked from
        # the sidebar footer's Privacy line).
        LANG_EN: "Symbolic prior · not a fortune · the model output stays visible above.",
        LANG_ZH: "符号先验 · 非预言 · 上方的模型原始输出始终可见。",
        LANG_ES: "Prior simbólico · no es predicción · la salida del modelo sigue visible arriba.",
        LANG_FR: "Prior symbolique · pas une prédiction · la sortie du modèle reste visible.",
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
    "lens.header.eyebrow": {
        LANG_EN: "Metaphysics lens",
        LANG_ZH: "玄学透镜",
        LANG_ES: "Lente metafísica",
        LANG_FR: "Loupe métaphysique",
    },
    "lens.header.title": {
        LANG_EN: "Five symbolic priors, overlaid on the model — never replacing it.",
        LANG_ZH: "五种符号先验，叠加在世界模型之上 —— 而不是替代它。",
        LANG_ES: "Cinco priores simbólicos, superpuestos al modelo — nunca lo reemplazan.",
        LANG_FR: "Cinq priors symboliques, superposés au modèle — jamais en remplacement.",
    },
    "lens.header.desc": {
        LANG_EN: (
            "易经 cast · 八字 four pillars · 紫薇 12-palace · tarot draw · "
            "natal sky — each casts a vote on this decision; their joint "
            "auspice is mixed into the world-model probability you already "
            "see. The number that matters is COMBINED."
        ),
        LANG_ZH: (
            "易经卦象 · 八字四柱 · 紫薇十二宫 · 塔罗三牌 · 出生天象——"
            "每一个体系对这次决定投一票，它们的合意被混入你已经看到的"
            "世界模型概率中。最终看 COMBINED 这个数字。"
        ),
        LANG_ES: (
            "Yi Jing · pilares BaZi · 12 palacios ZiWei · tirada de tarot · "
            "cielo natal — cada uno emite un voto sobre esta decisión; su "
            "auspicio conjunto se mezcla con la probabilidad del modelo. "
            "El número que importa es COMBINED."
        ),
        LANG_FR: (
            "Tirage du Yi Jing · piliers BaZi · 12 palais ZiWei · tirage "
            "de tarot · ciel natal — chacun vote sur cette décision ; "
            "leur auspice conjoint est mêlé à la probabilité du modèle. "
            "Le nombre qui compte est COMBINED."
        ),
    },
    "lens.consensus.favours": {
        LANG_EN: "Across the symbolic systems, the lens favours **{branch}** — {pct} consensus.",
        LANG_ZH: "在所有符号系统的合议中，本透镜更倾向 **{branch}** —— 合意 {pct}。",
        LANG_ES: "En los sistemas simbólicos, la lente favorece **{branch}** — consenso {pct}.",
        LANG_FR: "Parmi les systèmes symboliques, la loupe favorise **{branch}** — consensus {pct}.",
    },
    "lens.consensus.contests": {
        LANG_EN: "The symbolic systems disagree — no branch is clearly favoured. Treat the lens as a tie-breaker only.",
        LANG_ZH: "符号系统之间意见不一——没有哪个分支被明显偏向。把透镜当作平手时的一票即可。",
        LANG_ES: "Los sistemas simbólicos no coinciden — ninguna rama tiene clara preferencia. Trata la lente como desempate.",
        LANG_FR: "Les systèmes symboliques divergent — aucune branche n'est nettement favorite. Traitez la loupe comme un départage.",
    },
    "lens.consensus.no_prediction": {
        LANG_EN: "No prediction yet — generate one in the composer and the lens will pull a specific branch up or down.",
        LANG_ZH: "还没有预测——在编排器里跑一份，透镜就会把某个分支往上或往下拉。",
        LANG_ES: "Aún no hay predicción — genera una en el compositor y la lente subirá o bajará una rama concreta.",
        LANG_FR: "Pas encore de prédiction — générez-en une dans le compositeur et la loupe poussera une branche précise.",
    },
    "lens.consensus.line": {
        LANG_EN: "Model alone {model} · Joint symbolic auspice {tradition} · COMBINED {combined} ({tag})",
        LANG_ZH: "纯模型 {model} · 符号系统合意 {tradition} · 组合 COMBINED {combined}（{tag}）",
        LANG_ES: "Sólo modelo {model} · Auspicio simbólico conjunto {tradition} · COMBINADO {combined} ({tag})",
        LANG_FR: "Modèle seul {model} · Auspice symbolique conjoint {tradition} · COMBINÉ {combined} ({tag})",
    },
    "lens.module.astrolabe.title": {
        LANG_EN: "Celestial dial — 八字 × 占星",
        LANG_ZH: "天体盘 —— 八字 × 占星",
        LANG_ES: "Dial celeste — BaZi × astrología",
        LANG_FR: "Cadran céleste — BaZi × astrologie",
    },
    "lens.module.astrolabe.desc": {
        LANG_EN: "Your four pillars and your natal sky on one dial — read together. Their joint auspice pulls the focal branch up or down.",
        LANG_ZH: "你的四柱与本命天象，画在同一张盘上一起读。它们的合意把焦点分支的概率往上或往下拉。",
        LANG_ES: "Tus cuatro pilares y tu cielo natal en un solo dial — leídos juntos. Su auspicio conjunto sube o baja la rama focal.",
        LANG_FR: "Vos quatre piliers et votre ciel natal sur un seul cadran — lus ensemble. Leur auspice conjoint pousse la branche focale.",
    },
    "lens.module.iching.title": {
        LANG_EN: "易经 — I Ching cast",
        LANG_ZH: "易经卦象",
        LANG_ES: "易经 — tirada del I Ching",
        LANG_FR: "易经 — tirage du Yi Jing",
    },
    "lens.module.iching.desc": {
        LANG_EN: "Cast deterministically from this prediction's text — same prediction → same hexagram. When the cast has moving lines (变爻), the derived hexagram (变卦) appears alongside the primary, showing how the situation transforms.",
        LANG_ZH: "由这份预测文本确定性起卦——同一份预测每次都得到同一卦。出现变爻时，变卦会与本卦并列展示，呈现局势的转化。",
        LANG_ES: "Trazado de forma determinista del texto — la misma predicción da el mismo hexagrama. Cuando hay líneas móviles (变爻), el hexagrama derivado (变卦) aparece junto al primario, mostrando la transformación de la situación.",
        LANG_FR: "Tiré de manière déterministe du texte — la même prédiction donne le même hexagramme. Lorsque le tirage a des lignes mobiles (变爻), l'hexagramme dérivé (变卦) apparaît à côté du primaire, montrant la transformation.",
    },
    "lens.module.tarot.title": {
        LANG_EN: "Tarot — three-card draw",
        LANG_ZH: "塔罗三牌阵",
        LANG_ES: "Tarot — tirada de tres cartas",
        LANG_FR: "Tarot — tirage à trois cartes",
    },
    "lens.module.tarot.desc": {
        LANG_EN: "Past · present · future for this decision, deterministic from the prediction text. (L8 will replace the placeholder visuals with real card art.)",
        LANG_ZH: "针对这份决定的 过去 · 现在 · 未来 三牌阵，结果由预测文本确定。（L8 起将用真正的牌面取代占位图。）",
        LANG_ES: "Pasado · presente · futuro para esta decisión, determinista a partir del texto. (L8 reemplazará los visuales por cartas reales.)",
        LANG_FR: "Passé · présent · futur pour cette décision, déterministe à partir du texte. (L8 remplacera les visuels par de vraies cartes.)",
    },
    "lens.module.bazi_pillars.title": {
        LANG_EN: "Four Pillars · 八字",
        LANG_ZH: "四柱八字",
        LANG_ES: "Cuatro Pilares · 八字",
        LANG_FR: "Quatre Piliers · 八字",
    },
    "lens.module.bazi_pillars.desc": {
        LANG_EN: "Year / month / day / hour pillars derived from your birth — heavenly stem, earthly branch, and five-element tag for each.",
        LANG_ZH: "由你的出生信息推出的年/月/日/时四柱——每一柱包含天干、地支与对应的五行。",
        LANG_ES: "Pilares año / mes / día / hora derivados de tu nacimiento — tallo celestial, rama terrestre y elemento de cada uno.",
        LANG_FR: "Piliers année / mois / jour / heure dérivés de votre naissance — tige céleste, branche terrestre et élément pour chacun.",
    },
    "lens.module.delta.title": {
        LANG_EN: "Per-branch modulation",
        LANG_ZH: "每个分支的调制量",
        LANG_ES: "Modulación por rama",
        LANG_FR: "Modulation par branche",
    },
    "lens.module.delta.desc": {
        LANG_EN: "For each branch in the heatmap: the model's own probability vs. the lens-combined probability, drawn side by side so you can see which branches the lens lifts and which it lowers.",
        LANG_ZH: "对热力图中的每个分支：模型原始概率 vs. 透镜融合后的概率，左右并列，让你看清透镜把哪些分支抬升、哪些压低。",
        LANG_ES: "Para cada rama del mapa de calor: probabilidad del modelo vs. la combinada con la lente, lado a lado.",
        LANG_FR: "Pour chaque branche du mapa de calor : probabilité du modèle vs. probabilité combinée avec la loupe, côte à côte.",
    },
    "lens.module.ziwei.title": {
        LANG_EN: "紫微 — 12-palace chart",
        LANG_ZH: "紫微 —— 十二宫盘",
        LANG_ES: "紫微 — 12 palacios",
        LANG_FR: "紫微 — 12 palais",
    },
    "lens.module.ziwei.desc": {
        LANG_EN: "Twelve palaces (life · siblings · spouse · children · wealth · health · travel · friends · career · property · fortune · parents) with the major stars placed from your birth day + hour. 命宫 is highlighted; stars are tinted by 吉 (light) · 中 (neutral) · 凶 (rose).",
        LANG_ZH: "十二宫（命 · 兄弟 · 夫妻 · 子女 · 财帛 · 疾厄 · 迁移 · 交友 · 官禄 · 田宅 · 福德 · 父母），按你的生辰落主星。命宫高亮；主星按吉（亮）/ 中 / 凶（玫红）配色。",
        LANG_ES: "Doce palacios con las estrellas mayores colocadas según tu nacimiento. 命宫 destacado; las estrellas se tiñen por su naturaleza 吉 / 中 / 凶.",
        LANG_FR: "Douze palais avec les étoiles majeures placées selon votre naissance. 命宫 mis en évidence ; les étoiles teintées selon 吉 / 中 / 凶.",
    },
    "lens.module.astro.title": {
        LANG_EN: "Natal wheel — sun · moon · 12 signs",
        LANG_ZH: "本命星盘 —— 日 · 月 · 十二宫",
        LANG_ES: "Carta natal — sol · luna · 12 signos",
        LANG_FR: "Carte natale — soleil · lune · 12 signes",
    },
    "lens.module.astro.desc": {
        LANG_EN: "A real natal wheel — sun sign + moon sign placed on the zodiac ring. Drawn with monochrome line-art glyphs; the ascendant (rising sign) requires birth city + lat/long, which the console does not collect.",
        LANG_ZH: "真实的本命星盘——太阳与月亮分别落在十二宫之上。星座符号采用单色线条字形；上升星座需要出生城市的经纬度，本控制台暂不采集。",
        LANG_ES: "Una carta natal real — signo solar y lunar sobre el círculo zodiacal. Glifos monocromos en línea; el ascendente requiere coordenadas que no recogemos.",
        LANG_FR: "Une vraie carte natale — soleil et lune sur le cercle zodiacal. Glyphes en ligne monochrome ; l'ascendant requiert des coordonnées non collectées.",
    },
    "lens.module.chips.title": {
        LANG_EN: "Per-tradition vote",
        LANG_ZH: "各体系投票",
        LANG_ES: "Voto por tradición",
        LANG_FR: "Vote par tradition",
    },
    "lens.module.chips.desc": {
        LANG_EN: "Each tradition's favourability, side by side. The joint auspice above is their equal-weight mean — agreement = stronger pull, disagreement = weaker pull.",
        LANG_ZH: "并排展示每个体系的吉凶分。上方的合意是它们的等权平均——意见越一致，拉力越强；越分散，拉力越弱。",
        LANG_ES: "La favorabilidad de cada tradición, lado a lado. El auspicio conjunto es su media simple — más acuerdo, más tirón.",
        LANG_FR: "La favorabilité de chaque tradition, côte à côte. L'auspice conjoint est leur moyenne — plus d'accord, plus de tirage.",
    },
    "lens.module.readout.title": {
        LANG_EN: "How the lens modulates the model",
        LANG_ZH: "透镜如何调制模型",
        LANG_ES: "Cómo modula la lente al modelo",
        LANG_FR: "Comment la loupe module le modèle",
    },
    "lens.module.readout.desc": {
        LANG_EN: "Model is the world-model alone. Tradition is the joint symbolic auspice. Combined is the α-weighted mix that's actually used.",
        LANG_ZH: "Model 是纯世界模型；Tradition 是符号系统的合意；Combined 是实际使用的、按 α 权重融合后的结果。",
        LANG_ES: "Model = sólo modelo. Tradition = auspicio conjunto. Combined = mezcla ponderada por α, la realmente usada.",
        LANG_FR: "Model = modèle seul. Tradition = auspice conjoint. Combined = mélange pondéré par α, celui réellement utilisé.",
    },
    "lens.module.takeaway.title": {
        LANG_EN: "What this means for your decision",
        LANG_ZH: "这对你的决定意味着什么",
        LANG_ES: "Qué significa esto para tu decisión",
        LANG_FR: "Ce que cela signifie pour votre décision",
    },
    "lens.module.takeaway.lift": {
        LANG_EN: "The lens lifts the focal branch from {model} to {combined} — a {delta} upward modulation.",
        LANG_ZH: "透镜把焦点分支从 {model} 上调到 {combined}——一次 {delta} 的向上调制。",
        LANG_ES: "La lente sube la rama focal de {model} a {combined} — modulación al alza de {delta}.",
        LANG_FR: "La loupe relève la branche focale de {model} à {combined} — modulation à la hausse de {delta}.",
    },
    "lens.module.takeaway.drop": {
        LANG_EN: "The lens lowers the focal branch from {model} to {combined} — a {delta} downward modulation.",
        LANG_ZH: "透镜把焦点分支从 {model} 下调到 {combined}——一次 {delta} 的向下调制。",
        LANG_ES: "La lente baja la rama focal de {model} a {combined} — modulación a la baja de {delta}.",
        LANG_FR: "La loupe abaisse la branche focale de {model} à {combined} — modulation à la baisse de {delta}.",
    },
    "lens.module.takeaway.flat": {
        LANG_EN: "The symbolic systems land near-neutral — the lens leaves the focal branch essentially unchanged ({model} → {combined}).",
        LANG_ZH: "符号系统给出的合意接近中性——透镜基本上没有改变焦点分支（{model} → {combined}）。",
        LANG_ES: "Los sistemas simbólicos son casi neutros — la lente apenas cambia la rama focal ({model} → {combined}).",
        LANG_FR: "Les systèmes symboliques sont quasi neutres — la loupe laisse la branche focale presque inchangée ({model} → {combined}).",
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
        # Iter #16: quiet page name × 4 locales.
        LANG_EN: "Video query",
        LANG_ZH: "视频查询",
        LANG_ES: "Consulta por vídeo",
        LANG_FR: "Requête par vidéo",
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
        # Iter #15: marketing-hero title trimmed × 4 locales to a
        # quiet page name. The form below names what to do.
        LANG_EN: "Score a past prediction",
        LANG_ZH: "为过去的预测打分",
        LANG_ES: "Puntúa una predicción pasada",
        LANG_FR: "Évaluer une prédiction passée",
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
        # Iter #15: quiet page name × 4 locales.
        LANG_EN: "Your calibration record",
        LANG_ZH: "你的校准记录",
        LANG_ES: "Tu historial de calibración",
        LANG_FR: "Votre historique de calibration",
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
        # Iter #15: quiet page name × 4 locales.
        LANG_EN: "Pricing",
        LANG_ZH: "定价",
        LANG_ES: "Precios",
        LANG_FR: "Tarifs",
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
    # Bug fix (iter #11): the prior `entry.get(lang) or entry.get(EN)
    # or key` chain treated an EMPTY STRING translation ("") as missing
    # and fell through to the raw key — so iter #8's intentional
    # `heatmap.cell_hint = ""` rendered the literal key string on the
    # page. Distinguish "missing" (None) from "intentionally blank"
    # ("") and honour empty strings as valid translations.
    val = entry.get(lang)
    if val is None:
        val = entry.get(LANG_EN)
    if val is None:
        return key
    return val


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
