# vrc-osc-chatbox

简单的 VRChat OSC 聊天框命令行输入界面。

## 安装

需要 Python >= 3.11。

```bash
pip install -e git+https://github.com/Lazyb0x/vrc-osc-chatbox.git#egg=vrc-osc-chatbox
```

## 使用

运行命令：

```bash
vrc-chatbox [--ip IP] [--port PORT]
```

- `--ip`: OSC服务器的IP地址（默认：127.0.0.1）
- `--port`: OSC服务器监听的端口（默认：9000）

输入消息，按回车一次换行，两次发出消息。

输入 'exit' 退出。

## 卸载

```bash
pip uninstall vrc-osc-chatbox
```