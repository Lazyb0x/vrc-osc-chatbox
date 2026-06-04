"""跨平台 WebView 运行时检测 & 原生库注册模块。

用法：
    from vrcchatbox.platform import ensure_webview, handle_missing_webview, ensure_native_libs

    ensure_native_libs()  # 在导入 opuslib 等原生依赖之前调用

    if not ensure_webview():
        handle_missing_webview()
        raise RuntimeError("WebView runtime not found")
"""

import logging
import platform as _platform

logger = logging.getLogger(__name__)

# 仅在对应平台上导入具体检测模块


def ensure_native_libs() -> None:
    """将包内原生 DLL 添加到搜索路径（当前仅 Windows 需要 opus.dll）。"""
    system = _platform.system()
    if system == "Windows":
        from . import _win32

        _win32.ensure_native_libs()


def ensure_webview() -> bool:
    """检查当前平台的 WebView 运行时是否可用。"""
    system = _platform.system()

    if system == "Windows":
        from . import _win32

        return _win32.is_webview_available()

    return True


def handle_missing_webview() -> None:
    """弹出缺失 WebView 的提示对话框，用户确认后跳转下载页。"""
    system = _platform.system()

    if system == "Windows":
        from . import _win32

        if _win32.show_missing_dialog():
            _win32.open_download_page()
        return

    logger.error("未检测到系统的 WebView 运行环境")
