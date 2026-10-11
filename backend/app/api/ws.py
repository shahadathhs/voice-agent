import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.logger import logger
from app.pipeline import TranscriptionSession
from app.services import stt

router = APIRouter()


async def handle_control_message(websocket: WebSocket, raw: str) -> None:
    try:
        message: dict = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "reason": "invalid_json"})
        return

    msg_type = message.get("type")
    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
    else:
        await websocket.send_json({"type": "ack", "reply_to": msg_type})


@router.websocket("/ws")
async def websocket_echo(websocket: WebSocket) -> None:
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


@router.websocket("/ws/stt")
async def websocket_stt(websocket: WebSocket) -> None:
    settings = get_settings()
    await websocket.accept()

    if not stt.loaded:
        await websocket.send_json({"type": "model_status", "status": "loading"})
    await stt.get_model()
    await websocket.send_json({"type": "ready", "stage": "stt"})
    logger.info("STT WebSocket client connected")

    session = TranscriptionSession(sample_rate=settings.stt_sample_rate)

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if (text := message.get("text")) is not None:
                await handle_control_message(websocket, text)
                continue
            if (audio := message.get("bytes")) is None:
                continue

            for event in session.process_chunk(audio):
                if event.type == "speech_start":
                    await websocket.send_json({"type": "speech_start"})
                elif event.type == "utterance":
                    result = await stt.transcribe(
                        event.payload["audio_pcm"], settings.stt_sample_rate
                    )
                    await websocket.send_json(
                        {
                            "type": "transcript",
                            "text": result.text,
                            "language": result.language,
                            "audio_ms": round(result.audio_ms),
                            "stt_ms": round(result.elapsed_ms),
                        }
                    )
    except WebSocketDisconnect:
        pass
    finally:
        logger.info("STT WebSocket client disconnected")
