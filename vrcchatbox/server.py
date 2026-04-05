from email import message
import json
import logging
from fastapi import FastAPI, Request
from fastapi.websockets import WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.websockets import WebSocketDisconnect
import uvicorn

from vrcchatbox.config import Config
from vrcchatbox.osc_client import OSCClient
from vrcchatbox.message import Message
from vrcchatbox.utils.app_context import AppContext
from vrcchatbox.utils.logger import get_log_config

logger = logging.getLogger(__name__)


def create_app(osc_ip: str, osc_port: int):
    app = FastAPI()
    osc_client = OSCClient(osc_ip, osc_port)
    config = Config()
    config.load()
    AppContext.add(config)
    message_processor = Message(config=config)

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
                text = json.loads(msg_json).get("data")
                if text is None or text.strip() == "":
                    osc_client.chatbox_input("")
                    continue
                escaped = text.replace("\n", "\\n")
                logger.debug(f"Received: {escaped}")
                
                async for processed_text in message_processor.process(text):
                    osc_client.chatbox_input(processed_text)
                    response = json.dumps({"data": processed_text})
                    await websocket.send_text(response)
                
            except WebSocketDisconnect:
                break

    # 挂载静态文件目录（挂载到根目录，html=True 启用 SPA fallback）
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app


def run_server(host, port, osc_ip: str, osc_port: int):
    app = create_app(osc_ip, osc_port)
    uvicorn.run(app, host=host, port=port, log_config=get_log_config())
