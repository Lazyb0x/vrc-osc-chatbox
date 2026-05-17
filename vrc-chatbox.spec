# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("static", "static"),
        ("logging.yml", "."),
    ],
    hiddenimports=[
        "pystray",
        "pystray._win32",
        "colorlog",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# 命令行版本：有控制台
# exclude_binaries=True 表示不把依赖打进 exe，交由 COLLECT 统一管理
exe_console = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="vrc-chatbox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# GUI 版本：无控制台（windowed）
exe_windowed = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="vrc-chatboxw",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# COLLECT 把两个 exe 和所有共享依赖放进同一个输出目录
# 两个 exe 共享同一份 .pyd / .dll / datas，不会重复打包
coll = COLLECT(
    exe_console,
    exe_windowed,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="vrc-chatbox",
)
