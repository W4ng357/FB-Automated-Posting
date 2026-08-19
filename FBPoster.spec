# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

SPEC_ROOT = Path(os.path.abspath(SPEC)).parent
SRC_DIR = SPEC_ROOT / "src"

datas = [
    (str(SRC_DIR / "gui" / "styles" / "dark.qss"), "src/gui/styles"),
]

# Dynamically locate and bundle Playwright's Chromium browser if installed locally
try:
    import playwright
    pw_dir = Path(playwright.__file__).parent
    local_browsers = pw_dir / "driver" / "package" / ".local-browsers"
    if local_browsers.is_dir():
        datas.append((str(local_browsers), "playwright/driver/package/.local-browsers"))
        print(f"[SPEC] Bundling Playwright browsers from: {local_browsers}")
except ImportError:
    pass

# Collect system platforminputcontexts plugins (Fcitx5 / IBus) on Linux for Vietnamese IME
if sys.platform.startswith("linux"):
    for search_path in [
        Path("/usr/lib/qt6/plugins/platforminputcontexts"),
        Path("/usr/lib64/qt6/plugins/platforminputcontexts"),
        Path("/usr/lib/x86_64-linux-gnu/qt6/plugins/platforminputcontexts"),
        Path("/usr/lib/qt/plugins/platforminputcontexts"),
    ]:
        if search_path.is_dir():
            for plugin_file in search_path.glob("*.so"):
                datas.append((str(plugin_file), "PySide6/Qt/plugins/platforminputcontexts"))
                print(f"[SPEC] Bundling IME plugin: {plugin_file}")

hidden_imports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "playwright",
    "playwright.sync_api",
    "app_paths",
    "session_manager",
    "models",
    "models.listing",
    "models.saved_group",
    "models.facebook_account",
    "models.listing_posting_task",
    "models.account_posting_plan",
    "models.posting_progress",
    "models.posting_result_entry",
    "models.post_result",
    "models.group_target",
    "services",
    "services.listing_service",
    "services.group_service",
    "services.facebook_account_service",
    "services.listing_repository",
    "services.listing_asset_manager",
    "services.listing_draft_manager",
    "services.group_repository",
    "services.group_asset_manager",
    "services.facebook_account_repository",
    "services.facebook_account_asset_manager",
    "services.account_posting_service",
    "services.account_session_registry",
    "services.caption_generator",
    "services.content_loader",
    "facebook",
    "facebook.account_profile",
    "facebook.group_metadata",
    "facebook.group_poster",
    "facebook.get_group_name",
    "facebook.get_post_url",
    "gui",
    "gui.app",
    "gui.main_window",
    "gui.system_tray",
    "gui.dialogs",
    "gui.pages",
    "gui.widgets",
    "gui.workers",
]

a = Analysis(
    [str(SRC_DIR / "gui" / "app.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pytest"],
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FBPoster',
)

onefile_exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FBPoster-standalone',
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
