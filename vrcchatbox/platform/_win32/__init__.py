"""Windows 平台：注册表检测 WebView2 + 原生 DLL 注册。"""

import logging
import os
import webbrowser
import winreg
from pathlib import Path
from tkinter import messagebox

logger = logging.getLogger(__name__)

WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_DOWNLOAD_URL = "https://developer.microsoft.com/microsoft-edge/webview2"


def is_webview_available() -> bool:
    """检查 WebView2 运行时是否已安装。

    参考 Microsoft 官方文档：
    https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution

    通过读取注册表中 Evergreen WebView2 Runtime 的 pv 值判断：
    - 若 pv 值存在且不为空、不为 "0.0.0.0"，则已安装
    - 否则视为未安装
    """
    registry_path = rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"

    # 按官方推荐顺序检查：先 HKLM（系统安装），再 HKCU（用户安装）
    hives: list[tuple[int, str, int]] = [
        (winreg.HKEY_LOCAL_MACHINE, registry_path, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_LOCAL_MACHINE, registry_path, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_CURRENT_USER, registry_path, 0),
    ]

    for hive, path, access in hives:
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | access) as key:
                pv, _ = winreg.QueryValueEx(key, "pv")
                if pv and pv != "0.0.0.0":
                    logger.debug(f"WebView2 found: hive={hive}, pv={pv}")
                    return True
        except FileNotFoundError:
            continue
        except Exception:
            logger.debug(f"Failed to read registry at {path}", exc_info=True)
            continue

    logger.warning("WebView2 runtime not found")
    return False


def show_missing_dialog() -> bool:
    return messagebox.askyesno(
        title="缺少运行环境",
        message=(
            "未检测到 Microsoft Edge WebView2 运行环境，\n"
            "本应用需要它来显示界面。\n\n"
            "是否前往下载页面？"
        ),
    )


def open_download_page() -> None:
    webbrowser.open(WEBVIEW2_DOWNLOAD_URL)


def ensure_native_libs() -> None:
    """将随包分发的原生 DLL 注册到 Windows 搜索路径。

    opuslib 在模块级别调用 find_library('opus')，该函数在 Windows
    上底层走 SearchPath API，只认系统目录和 PATH，不认 add_dll_directory。
    因此需要同时使用两种注册方式。

    PyInstaller 打包后 _win32 目录不存在（DLL 已在 exe 同级目录，
    Windows 自动搜索），此时直接跳过。
    """
    dll_dir = Path(__file__).parent

    # PyInstaller 打包后目录结构不同，跳过
    if not dll_dir.exists():
        return

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_dir))

    # find_library → SearchPath → 只认 PATH
    path = os.environ.get("PATH", "")
    if str(dll_dir) not in path:
        os.environ["PATH"] = str(dll_dir) + os.pathsep + path

    logger.debug(f"Registered DLL directory: {dll_dir}")
