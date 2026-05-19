# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Omytea Personal Future Console — Tier 2
# native packaging. Builds a one-folder bundle (faster startup, easier
# debugging than --onefile) under dist/omytea-console/.
#
# Build:
#     pip install 'pyinstaller>=6.0,<7.0'
#     pyinstaller --noconfirm omytea-console.spec
#
# Run the bundle:
#     dist/omytea-console/omytea-console
# A browser tab opens at http://127.0.0.1:8501.
#
# Master plan §10 multi-substrate portability: this spec produces a
# self-contained Python environment but still expects the user to
# install Ollama separately (the vision model alone is multi-GB; bundling
# it would balloon the artifact past any reasonable download size).
# The Streamlit app launches in mock mode if Ollama isn't found.

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
)


block_cipher = None


# ----- Data files: anything the app reads at runtime that PyInstaller
# wouldn't otherwise discover by import-analysis.
datas = [
    ('app.py', '.'),
    ('compiler.py', '.'),
    ('console.py', '.'),
    ('storage.py', '.'),
    ('currency.py', '.'),
    ('pricing.py', '.'),
    ('video_ingest.py', '.'),
    ('video_state.py', '.'),
    ('visualization.py', '.'),
    ('webcam_stream.py', '.'),
    ('streamlit_app.py', '.'),
    ('scenarios', 'scenarios'),
    ('llm_backends', 'llm_backends'),
    ('.streamlit', '.streamlit'),
    ('samples', 'samples'),
    ('PRIVACY_POLICY.md', '.'),
    ('README.md', '.'),
]

# Streamlit ships static assets (HTML, CSS, JS for the web frontend)
# that bootstrap.run() loads from the installed wheel. PyInstaller's
# default analysis can miss them. ``collect_data_files`` pulls them in.
datas += collect_data_files('streamlit')

# Some optional deps that get conditionally imported at runtime —
# include their data files in case the user enables the corresponding
# code path (e.g. the streamlit-webrtc Mode 6 path).
for opt_pkg in ('altair', 'pandas', 'pyarrow'):
    try:
        datas += collect_data_files(opt_pkg)
    except Exception:
        pass


# ----- Hidden imports: modules referenced via runtime dynamic import
# (importlib / __import__) that PyInstaller can't statically detect.
hiddenimports = []

# Streamlit pulls in many submodules dynamically.
hiddenimports += collect_submodules('streamlit')

# Omytea substrate — these are conditionally imported in
# video_ingest / video_state / webcam_stream via ``_try_import_substrate``.
# If the bundle should be substrate-aware, the user installs omytea
# separately and these imports succeed at runtime; if not, we degrade
# gracefully. List them here so the bundle would work IF substrate is
# present on the build machine.
for sub in (
    'omytea',
    'omytea.quantum',
    'omytea.joint_belief',
    'omytea.models',
    'omytea.dynamics.lindblad',
    'omytea.dynamics.protocol',
    'omytea.perception',
    'omytea.perception_yolo',
    'omytea.camera_ingest',
):
    hiddenimports.append(sub)

# LLM backends — conditionally imported per provider availability.
for backend in (
    'llm_backends',
    'llm_backends.base',
    'llm_backends.ollama_backend',
    'llm_backends.ollama_vision_backend',
    'llm_backends.anthropic_backend',
    'llm_backends.gemini_backend',
    'llm_backends.groq_backend',
    'llm_backends.cloudflare_backend',
    'llm_backends.openai_backend',
    'llm_backends.mock_backend',
):
    hiddenimports.append(backend)

# Webcam stack — only required if the user opts into Mode 6.
for opt in ('streamlit_webrtc', 'aiortc', 'av'):
    hiddenimports.append(opt)


a = Analysis(
    ['bootstrap_native.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavy ML stacks the Console doesn't need at runtime.
        'torch',
        'tensorflow',
        'jax',
        # Test deps
        'pytest',
        'hypothesis',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='omytea-console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # UPX has issues with macOS notarization
    console=True,      # Keep terminal visible so logs are reachable
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='omytea-console',
)
