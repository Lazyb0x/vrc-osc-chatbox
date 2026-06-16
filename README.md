# vrc-osc-chatbox

一个 VRChat OSC 聊天框输入界面，能让你使用拼音或者语音输入文字发送到 VRChat。

## 特性

- Web UI 可以从局域网其他设备的浏览器访问
- 中文拼音输入法虚拟键盘以及优化词库
- 基于大模型 API 的翻译
- 语音识别输入

## 食用

在游戏中开启 [OSC](https://docs.vrchat.com/docs/osc-overview#enabling-it) 功能。

从 [Releases](https://github.com/Lazyb0x/vrc-osc-chatbox/releases) 下载，解压后运行。

- `vrc-chatbox.exe` - 控制台模式
- `vrc-chatboxw.exe` - 窗口模式

程序默认使用 WebView 界面，如果不需要可以使用命令 `./vrc-chatbox.exe --serve` 启动，然后在浏览器中访问。

可以借助 VR overlay 工具如 [Desktop+](https://github.com/elvissteinjr/DesktopPlus) 在游戏中以叠加层显示。

## 构建

前端需要 pnpm，后端需要 python 3.11+ 和 uv。

运行：

```bash
cd ui
pnpm install
pnpm run dev
```

```bash
uv venv
uv sync
python main.py
```

前后端构建：

```bash
python build.py
```

词典构建，需要 Git Bash 和 Docker：

```bash
cd ui/dicts
bash build.sh
```

## 鸣谢

- [Naive UI](https://github.com/tusen-ai/naive-ui) - Vue 3 组件库
- [doubaoime-asr](https://github.com/yangmoling/doubaoime-asr) - 豆包输入法语音
- [zh-keyboard](https://github.com/dusionlike/zh-keyboard) - 中文虚拟键盘组件库
- [rime-ice](https://github.com/iDvel/rime-ice), [mw2fcitx](https://github.com/outloudvi/mw2fcitx) - 词库：雾凇拼音、萌娘百科
- Claude Code 和 DeepSeek
