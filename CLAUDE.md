# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 在本项目中工作时提供指导。

## 项目概述

VRChat OSC Chatbox — 一个通过 OSC（Open Sound Control）协议向 VRChat 聊天框发送消息的桌面工具。支持文字输入、LLM 翻译、语音识别，提供 Web 前端 GUI 和命令行两种交互方式。

## 环境配置

本项目使用 [uv](https://github.com/astral-sh/uv) 管理，Python >= 3.11。

```bash
# 创建虚拟环境并安装依赖
uv venv
uv sync

# 前端（ui/ 目录）使用 pnpm
cd ui && pnpm install && pnpm run build
```

## 命令

```bash
# 默认模式：启动服务器 + 打开 GUI 窗口
python main.py

# 仅启动服务器（不打开 GUI）
python main.py --serve

# 命令行交互模式（终端内使用）
python main.py --console

# 自定义参数
python main.py --osc-host 127.0.0.1 --osc-port 9000 --server-host 0.0.0.0 --server-port 8000 --debug
```

**CLI 参数：** `--config`（配置文件路径）、`--osc-host`、`--osc-port`、`--server-host`、`--server-port`、`--debug`、`--version`。

## 架构

```
[浏览器 / WebView GUI]  ←WebSocket→  [FastAPI 服务器]
                                           |
                                    消息处理器 (MessageProcessor)
                                           |
                                    处理管道 (Pipeline)
                                           |
                           ┌───────────────┼───────────────┐
                           │                               │
                      翻译处理器                          OSC 客户端
                           │                               │
                      翻译代理 (LLM)                  UDP /chatbox/input
                           │                               │
                      OpenAI API                       VRChat 客户端

[麦克风音频]  ←WebSocket /api/asr→  [语音识别流]
                                           |
                                  doubaoime_asr 子模块 → 豆包 ASR 服务
```

### 关键模块

- **入口点** — CLI 参数解析，分发到 GUI / 服务器 / 控制台三种运行模式
- **WebSocket 服务器** — 提供主聊天通道（`/api/oscws`）和语音识别通道（`/api/asr`），同时托管前端静态文件
- **消息管道** — 基于优先级的异步生成器链，通过 `@msg_register` 装饰器注册处理器，按 `order` 排序执行
- **消息处理器** — 中枢调度：接收 WebSocket 消息，路由到管道处理后发送至 OSC 客户端
- **翻译代理** — 通过 OpenAI 函数调用让 LLM 自主控制翻译开关和目标语言，带 1.1 秒防抖
- **OSC 客户端** — 封装 pythonosc，向 VRChat 发送 `/chatbox/input` 和 `/chatbox/typing`
- **GUI** — pywebview 桌面窗口，加载前端页面
- **语音识别** — 封装豆包 ASR 异步流，转为统一字典协议                              |

### 语音识别 (ASR)

通过 git submodule `doubaoime-asr` 接入豆包输入法 ASR 服务：

- `doubaoime-asr` 是独立维护的包（v0.2.0），位于 `doubaoime-asr/`
- 模拟 Android 设备注册，通过 WebSocket + Protobuf 协议通信
- 封装为 async generator，统一输出 `{"type": "interim|final", "text": "..."}` 字典协议
- 服务器端 `/api/asr` WebSocket 接收 PCM 音频，流式返回转录结果
- 首次使用自动获取并缓存设备凭证至 `asr-credentials.json`

### 前端

- Vue 3 + TypeScript + Vite，位于 `ui/`
- 使用 Naive UI 组件库、`@zh-keyboard/pinyin` 中文输入法
- 构建产物输出到 `ui/dist/`，运行时由 FastAPI 从 `static/` 托管
- 内嵌 Rime 输入法引擎（WASM），支持拼音输入

## 关键 OSC 地址

- `/chatbox/input` — VRChat 聊天框输入
  - 参数：`[message: str, bypass_keyboard: bool, notify: bool]`
- `/chatbox/typing` — VRChat 打字状态指示
  - 参数：`[is_typing: bool]`

## WebSocket 协议

### `/api/oscws` — 主聊天通道

接收 JSON 消息（字段与 `Message` 数据类对应）：

```json
{
  "data": "要发送的文字",
  "realtime": true,
  "languages": ["en"],
  "clipboard": false
}
```

返回处理后的文本。连接时推送初始配置状态。

### `/api/asr` — 语音识别通道

接收二进制 PCM 音频帧（16kHz, mono, 16bit），返回 JSON：

```json
{"type": "interim", "text": "临时识别结果"}
{"type": "final", "text": "最终识别结果"}
```

## REST API

- `GET /api/ip-info` — 服务器端口 + 本机 IP 列表
- `GET /api/config` — 完整配置 JSON
- `POST /api/config` — 更新配置（JSON body）
- `GET /{path}` — SPA 静态文件（支持 PyInstaller 打包路径）

## 配置文件

| 文件                   | 用途                                          |
| ---------------------- | --------------------------------------------- |
| `config.yml`           | 运行时配置（含中文注释，首次运行自动生成）    |
| `logging.yml`          | Python logging dict 配置（colorlog 彩色输出） |
| `asr-credentials.json` | 豆包 ASR 设备凭证（自动获取并缓存）           |
| `pyrightconfig.json`   | Pyright 类型检查配置                          |

## 构建与打包

```bash
# 完整构建（前端 + PyInstaller）
python build.py
```

构建流程：

1. `cd ui && pnpm run build` 编译前端
2. PyInstaller 根据 `vrc-chatbox.spec` 打包
3. 生成两个 exe：`vrc-chatbox.exe`（控制台模式）和 `vrc-chatboxw.exe`（窗口模式）
4. 输出到 `dist/vrc-chatbox-<version>/`

## 静态检查 / Lint

```bash
# 检查单个文件
uv run python -m pyright vrcchatbox/utils/app_context.py

# 检查整个项目
uv run python -m pyright .
```
