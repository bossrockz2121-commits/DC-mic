# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['setup_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('.\\dist-fastest\\D4C Mic Boost V.2.exe', 'payload'), ('.\\Uninstall-D4CMic.ps1', 'payload')],
    hiddenimports=[],
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
    name='D4C Mic Boost V.2 Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
