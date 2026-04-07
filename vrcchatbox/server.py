import asyncio
import json
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect

from vrcchatbox.config import Config
from vrcchatbox.message import Message, MessageProcessor
from vrcchatbox.osc_client import OSCClient
from vrcchatbox.utils.app_context import AppContext
from vrcchatbox.utils.logger import get_log_config

logger = logging.getLogger(__name__)


def create_app(config: Config, osc_ip: str, osc_port: int):
    app = FastAPI()
    osc_client = OSCClient(osc_ip, osc_port)
    message_processor = MessageProcessor(config=config)

    # ========== 全局异常处理器 ==========

    @app.exception_handler(WebSocketDisconnect)
    async def websocket_disconnect_handler(
        websocket: WebSocket, exc: WebSocketDisconnect
    ):
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
        while True:
            try:
                msg_json = await websocket.receive_text()
                logger.debug(f"Received: {msg_json}")

                message = Message.from_dict(json.loads(msg_json))
                if message.data is None or message.data.strip() == "":
                    osc_client.chatbox_input("")
                    continue

                async def backgroud_task():
                    async for processed_text in message_processor.process(message):
                        osc_client.chatbox_input(processed_text)
                        response = json.dumps({"data": processed_text})
                        await websocket.send_text(response)

                asyncio.create_task(backgroud_task())

            except WebSocketDisconnect:
                break

    # 挂载静态文件目录（挂载到根目录，html=True 启用 SPA fallback）
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app


def run_server(config: Config, host: str, port: int, osc_ip: str, osc_port: int):
    app = create_app(config, osc_ip, osc_port)
    uvicorn.run(app, host=host, port=port, log_config=get_log_config())
