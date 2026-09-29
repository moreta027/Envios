# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['plInventarioVencimiento.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('graph_config.json', '.')],
    hiddenimports=[
        'reportlab',
        'reportlab.lib',
        'reportlab.platypus',
        'reportlab.rl_config',
        'reportlab.pdfbase',
        'reportlab.pdfgen',
        'reportlab.lib.styles',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.colors',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='plInventarioVencimiento',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
