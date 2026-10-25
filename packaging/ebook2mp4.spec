# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

pdf_datas, pdf_binaries, pdf_imports = collect_all('pypdfium2')
raw_datas, raw_binaries, raw_imports = collect_all('pypdfium2_raw')

a = Analysis(
    ['../run.pyw'],
    pathex=[],
    binaries=pdf_binaries + raw_binaries,
    datas=pdf_datas + raw_datas,
    hiddenimports=pdf_imports + raw_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
