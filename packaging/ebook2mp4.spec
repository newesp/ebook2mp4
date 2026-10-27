# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, copy_metadata
from pathlib import Path

pdf_datas, pdf_binaries, pdf_imports = collect_all('pypdfium2')
raw_datas, raw_binaries, raw_imports = collect_all('pypdfium2_raw')
conversion_datas, conversion_binaries, conversion_imports = collect_all('opencc')
voice_datas, voice_binaries, voice_imports = collect_all('edge_tts')
certificate_datas, certificate_binaries, certificate_imports = collect_all('certifi')
voice_runtime = Path(SPECPATH).parent / '.scratch' / 'voice-runtime'
if not (voice_runtime / 'ffmpeg.exe').is_file():
    raise RuntimeError('Run packaging/prepare_voice.py with verified FFmpeg before building.')
ocr_runtime = Path(SPECPATH).parent / '.scratch' / 'ocr-runtime'
if not (ocr_runtime / 'tesseract.exe').is_file():
    raise RuntimeError('Run packaging/prepare_ocr.py with build dependencies before building.')

a = Analysis(
    ['../run.pyw'],
    pathex=[],
    binaries=pdf_binaries + raw_binaries + voice_binaries + certificate_binaries,
    datas=pdf_datas + raw_datas + conversion_datas + voice_datas + certificate_datas + copy_metadata('edge-tts') + copy_metadata('opencc-python-reimplemented') + copy_metadata('pillow') + [(str(voice_runtime), 'tools/ffmpeg'), (str(ocr_runtime), 'tools/tesseract'), (str(Path(SPECPATH) / 'licenses'), 'licenses')],
    hiddenimports=pdf_imports + raw_imports + conversion_imports + voice_imports + certificate_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy'],  # Optional PDFium array adapter; rendering uses Pillow.
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ebook2mp4',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ebook2mp4',
)
