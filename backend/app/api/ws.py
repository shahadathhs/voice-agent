import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.logger import logger

router = APIRouter()


async def handle_control_message(websocket: WebSocket, raw: str) -> None:
    try:
        message: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "reason": "invalid_json"})
        return

    msg_type = message.get("type")
    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
    else:
        await websocket.send_json({"type": "ack", "reply_to": msg_type})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    settings = get_settings()
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "ready",
            "stage": "echo",
            "version": settings.app_version,
        }
    )
    logger.info("WebSocket client connected")

    bytes_echoed = 0
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if (text := message.get("text")) is not None:
                await handle_control_message(websocket, text)
            elif (audio := message.get("bytes")) is not None:
                bytes_echoed += len(audio)
                await websocket.send_bytes(audio)
    except WebSocketDisconnect:
        pass
    finally:
        logger.info(f"WebSocket client disconnected (echoed {bytes_echoed} bytes)")
