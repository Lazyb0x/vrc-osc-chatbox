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


def build_pyinstaller():
    # 只装生产依赖 + build 工具，排除 ipykernel/IPython 等 dev 依赖
    run(["uv", "sync", "--no-dev", "--group", "build"])
    try:
        run([
            sys.executable, "-m", "PyInstaller",
            "vrc-chatbox.spec",
            "--clean",
            "--noconfirm",
        ])
    finally:
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
