# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Omytea Personal Future Console — Tier 3
# single-binary variant. Bundles everything into ONE executable file
# under dist/ instead of the one-folder layout produced by the
# default omytea-console.spec.
#
# Trade-offs vs. one-folder:
#   + Single artifact to download / distribute (cleaner UX, easier
#     to ship over email / chat / cloud storage)
#   + No "the user accidentally moved one file out of the folder"
#     class of failure modes
#   - Startup is slower: the bootloader unpacks the bundle into a
#     temp dir on every launch (~3-8 seconds vs. ~1-2 seconds for
#     one-folder)
#   - Larger single artifact file size (compression doesn't help
#     much because most weight is binary deps)
#
# When to use which:
#   - End-user "download this single file and double-click" → onefile
#   - Power-user / developer iteration → one-folder (faster startup)
#
# Build:
#     pip install 'pyinstaller>=6.0,<7.0'
#     pyinstaller --noconfirm omytea-console-onefile.spec
#
# Output:
#     dist/omytea-console        (macOS / Linux — a single ELF/Mach-O)
#     dist/omytea-console.exe    (Windows — a single PE)
#
# Run:
#     ./dist/omytea-console      # browser tab opens at 127.0.0.1:8501

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


block_cipher = None


# Package metadata — see sibling spec for full rationale. Without
# this the bundle dies at launch with PackageNotFoundError because
# streamlit does importlib.metadata.version('streamlit') at import.
metadata_datas = []
metadata_datas += copy_metadata('streamlit')
for opt_meta in ('altair', 'pandas', 'pyarrow', 'numpy', 'pillow',
                 'requests', 'pydantic', 'opencv-python-headless'):
    try:
        metadata_datas += copy_metadata(opt_meta)
    except Exception:
        pass


# Same data files as the one-folder spec — kept in sync intentionally.
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
    ('_brand.py', '.'),
    ('scenarios', 'scenarios'),
    ('llm_backends', 'llm_backends'),
    ('.streamlit', '.streamlit'),
    ('samples', 'samples'),
    ('PRIVACY_POLICY.md', '.'),
    ('README.md', '.'),
]
datas += collect_data_files('streamlit')
datas += metadata_datas
for opt_pkg in ('altair', 'pandas', 'pyarrow'):
    try:
        datas += collect_data_files(opt_pkg)
    except Exception:
        pass


hiddenimports = []
hiddenimports += collect_submodules('streamlit')
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
        'torch',
        'tensorflow',
        'jax',
        'pytest',
        'hypothesis',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


# ----- The single-file variant: EXE bundles binaries + datas
# directly; there is no COLLECT step. That's what makes this
# "onefile" vs the sibling spec's "one-folder".
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='omytea-console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
