"""Build script: builds frontend, then packages with PyInstaller."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd, cwd=None):
    print(f"{cwd if cwd else '.'}>", " ".join(map(str, cmd)))
    env = os.environ.copy()
    subprocess.check_call([str(x) for x in cmd], cwd=cwd, env=env)


def build_frontend():
    ui_dir = ROOT / "ui"
    pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd") or "pnpm"
    run([pnpm, "run", "build"], cwd=ui_dir)


def _write_version_file():
    """生成 file_version_info.txt，PyInstaller spec 用其嵌入 exe 右键属性版本号。"""
    from vrcchatbox import __version__

    parts = __version__.split(".")
    ver_tuple = tuple(map(int, parts)) + (0,) * (4 - len(parts))
    ver_tuple = ver_tuple[:4]
    ver_str = ".".join(str(v) for v in ver_tuple)

    content = f"""# UTF-8
#
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={ver_tuple},
        prodvers={ver_tuple},
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo([
            StringTable(
                u'040904B0',
                [StringStruct(u'CompanyName', u''),
                 StringStruct(u'FileDescription', u'VRC OSC Chatbox'),
                 StringStruct(u'FileVersion', u'{ver_str}'),
                 StringStruct(u'InternalName', u'vrc-chatbox'),
                 StringStruct(u'LegalCopyright', u'MIT License'),
                 StringStruct(u'OriginalFilename', u'vrc-chatbox.exe'),
                 StringStruct(u'ProductName', u'vrc-chatbox'),
                 StringStruct(u'ProductVersion', u'{ver_str}'),
                 ])
        ]),
        VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
    ]
)
"""
    path = ROOT / "file_version_info.txt"
    path.write_text(content, encoding="utf-8")
    print(f"Generated: {path} (version {__version__})")


def _remove_version_file():
    _ver_file = ROOT / "file_version_info.txt"
    if _ver_file.exists():
        _ver_file.unlink()


def build_pyinstaller():
    # 生成 Windows 版本信息文件，供 spec 嵌入 exe 右键属性
    _write_version_file()

    # 只装生产依赖 + build 工具，排除 ipykernel/IPython 等 dev 依赖
    run(["uv", "sync", "--no-dev", "--group", "build"])
    try:
        run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "vrc-chatbox.spec",
                "--clean",
                "--noconfirm",
            ]
        )
    finally:
        _remove_version_file()
        # 恢复完整开发环境
        run(["uv", "sync"])


def main():
    print("=== Build Frontend ===")
    build_frontend()

    print()
    print("=== PyInstaller ===")
    build_pyinstaller()

    print()
    print("Build complete!")
    print(f"Output: {ROOT / 'dist' / 'vrc-chatbox'}")


if __name__ == "__main__":
    main()
