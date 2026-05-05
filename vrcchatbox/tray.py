import logging
import webbrowser

from PIL import Image, ImageDraw, ImageFont

from vrcchatbox.config import Config

logger = logging.getLogger(__name__)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """加载合适的字体，优先系统字体，失败则用默认字体。"""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # Windows 微软雅黑
        "C:/Windows/Fonts/segoeui.ttf",  # Windows Segoe UI
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _create_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角矩形背景
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=14,
        fill=(66, 133, 244, 255),
    )

    # 聊天气泡小尾巴（左下角）
    draw.polygon(
        [
            (margin + 2, size - margin - 6),
            (margin - 2, size - margin + 4),
            (margin + 12, size - margin - 4),
        ],
        fill=(66, 133, 244, 255),
    )

    # 文字 "VC"
    font = _load_font(22)
    draw.text((size // 2, size // 2 + 1), "VC", fill="white", anchor="mm", font=font)

    return img


def run_tray(config: Config, host: str, port: int, on_exit=None) -> None:
    """启动系统托盘图标（阻塞，需在主线程调用）。"""
    import pystray

    icon_image = _create_icon_image()

    def open_web():
        webbrowser.open(f"http://{host}:{port}")

    def on_exit_clicked(icon, item):
        icon.stop()
        if on_exit:
            on_exit()

    def reload_config():
        config.load()

    menu = pystray.Menu(
        pystray.MenuItem("打开网页", open_web, default=True),
        pystray.MenuItem("重新加载配置", reload_config),
        pystray.MenuItem("退出", on_exit_clicked),
    )

    icon = pystray.Icon("vrc-chatbox", icon_image, "VRChat Chatbox", menu)
    icon.run()
