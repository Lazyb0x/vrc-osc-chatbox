import asyncio
from contextlib import asynccontextmanager
import json
import logging
import sys
import threading
from typing import Any, Optional
import webbrowser
from pathlib import Path

from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect

from vrcchatbox.config import Config
from vrcchatbox.message import Message, MessageProcessor
from vrcchatbox.osc_client import OSCClient
from vrcchatbox.utils.logger import get_log_config
from vrcchatbox.utils.netutil import get_ip_address, IpInfo

logger = logging.getLogger(__name__)


def create_app(config: Config, host: str, port: int, osc_host: str, osc_port: int):

    class ApiResponse(BaseModel):
        code: int = 0
        msg: str = "success"
        data: Optional[Any] = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动完成后打开浏览器
        threading.Timer(1, lambda: webbrowser.open(f"http://{host}:{port}")).start()
        yield
        logger.info("Shutting down web server")

    app = FastAPI(root_path="/api", lifespan=lifespan)
    osc_client = OSCClient(osc_host, osc_port)
    message_processor = MessageProcessor(config=config)

    # ========== 全局异常处理器 ==========

    @app.exception_handler(WebSocketDisconnect)
    async def websocket_disconnect_handler(websocket: WebSocket, exc: WebSocketDisconnect):
        logger.info("Client disconnected")

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    @app.websocket("/oscws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        # 建立连接时发送配置内容
        await websocket.send_text(
            json.dumps(
                {
                    "translation": config.translate.enable,
                    "languages": config.translate.languages,
                }
            )
        )

        while True:
            try:
                msg_json = await websocket.receive_text()
                logger.debug(f"Received: {msg_json}")

                message = Message.from_dict(json.loads(msg_json))

                async def backgroud_task():
                    async for processed_text in message_processor.process(message):
                        osc_client.chatbox_input(processed_text)
                        response = json.dumps(
                            {
                                "data": processed_text,
                                "translation": config.translate.enable,
                                "languages": config.translate.languages,
                            }
                        )
                        await websocket.send_text(response)

                asyncio.create_task(backgroud_task())

            except WebSocketDisconnect:
                break

    @app.get("/ip-info")
    async def get_ip_info():
        ip_infos: list[IpInfo] = get_ip_address()
        return ApiResponse(
            data={
                "port": port,
                "ipInfos": [
                    {
                        "ip": ip_info.ip,
                        "networkName": ip_info.network_name,
                        "networkPrefix": ip_info.network_prefix,
                        "adapterName": ip_info.adapter_name,
                    }
                    for ip_info in ip_infos
                ],
            }
        )

    # 挂载静态文件目录（挂载到根目录，html=True 启用 SPA fallback）
    if getattr(sys, "frozen", False):
        static_dir = Path(sys._MEIPASS) / "static"
    else:
        static_dir = Path(__file__).parent.parent / "static"

    # favicon
    favicon_file = static_dir / "favicon.ico"
    if favicon_file.exists():

        @app.get("/favicon.ico")
        async def favicon():
            return FileResponse(favicon_file)

    # SPA fallback
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        target = static_dir / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(static_dir / "index.html")

    return app


def run_server(
    config: Config, host: str, port: int, osc_host: str, osc_port: int, block: bool = True
) -> uvicorn.Server:
    app = create_app(config, host, port, osc_host, osc_port)

    uvicorn_config = uvicorn.Config(app, host=host, port=port, log_config=get_log_config())
    server = uvicorn.Server(uvicorn_config)

    if block:
        try:
            server.run()
        except KeyboardInterrupt:
            pass
    else:
        t = threading.Thread(target=server.run, daemon=True)
        t.start()

    return server
