import asyncio
import contextlib
import json
import logging
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.websockets import WebSocket
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from vrcchatbox.config import Config
from vrcchatbox.message import Message, MessageProcessor
from vrcchatbox.osc_client import OSCClient
from vrcchatbox.utils.logger import get_log_config
from vrcchatbox.utils.netutil import IpInfo, get_ip_address

from vrcchatbox.asr_service import asr_stream

logger = logging.getLogger(__name__)


def create_app(config: Config, host: str, port: int, message_processor: MessageProcessor):

    class ApiResponse(BaseModel):
        code: int = 0
        msg: str = "success"
        data: Optional[Any] = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        logger.info("Shutting down web server")

    app = FastAPI(lifespan=lifespan)
    api_router = APIRouter(prefix="/api")

    # ========== 全局异常处理器 ==========

    @app.exception_handler(WebSocketDisconnect)
    async def websocket_disconnect_handler(websocket: WebSocket, exc: WebSocketDisconnect):
        logger.info("Client disconnected")

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ApiResponse(code=500, msg=str(exc)).model_dump(),
        )

    @api_router.websocket("/oscws")
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

    # ========== 语音识别 (ASR) WebSocket ==========

    @api_router.websocket("/asr")
    async def asr_websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        # 用队列解耦接收与发送
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        async def receive_audio():
            try:
                while True:
                    msg = await websocket.receive()
                    if msg["type"] == "websocket.receive":
                        if "bytes" in msg:
                            await audio_queue.put(msg["bytes"])
                        elif "text" in msg:
                            data = json.loads(msg["text"])
                            if data.get("action") == "stop":
                                await audio_queue.put(None)
                                return
                    else:
                        break
            except WebSocketDisconnect:
                pass
            except Exception:
                logger.exception("ASR receive error")
            finally:
                await audio_queue.put(None)

        async def audio_source():
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                yield chunk

        receive_task = asyncio.create_task(receive_audio())

        try:
            async for result in asr_stream(
                audio_source(),
                credential_path=config.asr.credential_path if hasattr(config, "asr") else None,
            ):
                await websocket.send_json(result)
                if result["type"] == "error":
                    break
        except WebSocketDisconnect:
            logger.info("ASR client disconnected")
        except Exception as e:
            logger.error(f"ASR endpoint error: {e}", exc_info=True)
        finally:
            receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receive_task
            with contextlib.suppress(Exception):
                await websocket.close()

    @api_router.get("/ip-info")
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

    @api_router.get("/config")
    async def get_config():
        return ApiResponse(data=config.to_dict())

    @api_router.post("/config")
    async def update_config(data: dict[str, dict]):
        config.update_from_dict(data)
        config.save()
        return ApiResponse()

    app.include_router(api_router)

    # SPA fallback
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if getattr(sys, "frozen", False):
            static_dir = Path(getattr(sys, "_MEIPASS", "")) / "static"
        else:
            static_dir = Path(__file__).parent.parent / "static"

        target = static_dir / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(static_dir / "index.html")

    return app


def run_server(
    config: Config, host: str, port: int, osc_host: str, osc_port: int, block: bool = True
) -> tuple[uvicorn.Server, threading.Thread | None]:
    osc_client = OSCClient(osc_host, osc_port)
    message_processor = MessageProcessor(config, osc_client)
    app = create_app(config, host, port, message_processor)
    uvicorn_config = uvicorn.Config(app, host=host, port=port, log_config=get_log_config())
    server = uvicorn.Server(uvicorn_config)

    if block:
        try:
            server.run()
        except KeyboardInterrupt:
            pass
        return server, None
    else:
        t = threading.Thread(target=server.run, daemon=True)
        t.start()
        return server, t
