# -*- mode: python ; coding: utf-8 -*-

from motion_analysis_2d.defs import project_name, app_version, module_name


block_cipher = None

a = Analysis(
    [f"{module_name}/main_widget.py"],
    pathex=[],
    binaries=[],
    datas=[(f"{module_name}/resource/{module_name}.svg", f"{module_name}/resource")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"{project_name}-{app_version}",
    icon=f"{module_name}/resource/{module_name}.ico",
    debug=True,
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
