# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import playwright

playwright_dir = Path(playwright.__file__).parent
local_browsers = playwright_dir / 'driver' / 'package' / '.local-browsers'

datas = [('src/gui/styles/dark.qss', 'src/gui/styles')]
if local_browsers.exists():
    datas.append((str(local_browsers), 'playwright/driver/package/.local-browsers'))

a = Analysis(
    ['src/gui/app.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=['playwright.sync_api'],
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
    name='FBPoster',
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
    name='FBPoster',
)
