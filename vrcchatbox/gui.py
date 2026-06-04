import logging

import webview
from webview.errors import WebViewException

from vrcchatbox.platform import ensure_webview, handle_missing_webview

logger = logging.getLogger(__name__)


def run_gui(port: int, debug: bool = False):
    # 启动前先检查 WebView 运行时
    if not ensure_webview():
        handle_missing_webview()
        raise RuntimeError("WebView runtime not found")

    window = webview.create_window(
        "OSC Chatbox", url=f"http://127.0.0.1:{port}", width=480, height=720
    )
    if window is None:
        raise RuntimeError("Failed to create webview window")
    if not debug:
        webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False

    def on_loaded():
        # 允许文本被选中复制
        window.evaluate_js("""
            var style = document.createElement('style');
            style.textContent = 'body { -webkit-user-select: auto !important; user-select: auto !important; }';
            document.head.appendChild(style);
        """)

    try:
        webview.start(func=on_loaded, debug=True)
    except WebViewException:
        # ensure_webview 通过了但 start 仍失败（如 pythonnet 未安装）
        handle_missing_webview()
        raise
