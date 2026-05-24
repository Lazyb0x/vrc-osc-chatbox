import logging

import webview

logger = logging.getLogger(__name__)


def run_gui(port: int, debug: bool = False):
    window = webview.create_window(
        "OSC Chatbox", url=f"http://127.0.0.1:{port}", width=480, height=620
    )
    if not debug:
        webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False

    def on_loaded():
        # 允许文本被选中复制
        window.evaluate_js("""
            var style = document.createElement('style');
            style.textContent = 'body { -webkit-user-select: auto !important; user-select: auto !important; }';
            document.head.appendChild(style);
        """)

    webview.start(func=on_loaded, debug=True)
