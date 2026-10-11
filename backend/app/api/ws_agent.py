import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.logger import logger
from app.llm import LLMError, build_messages
from app.pipeline.chunker import SentenceChunker
from app.pipeline.turn_detector import TurnDetector
from app.services import get_vad, llm, stt, tts

router = APIRouter()


async def audio_frames(samples: Any, frame_size: int) -> AsyncIterator[bytes]:
    for i in range(0, len(samples), frame_size):
        yield samples[i : i + frame_size].tobytes()


@router.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket, persona: str = "assistant") -> None:
    settings = get_settings()
    await websocket.accept()
    await websocket.send_json({"type": "connected", "persona": persona})

    if not tts.loaded:
        await websocket.send_json({"type": "model_status", "status": "loading"})
    await asyncio.gather(stt.get_model(), get_vad(), tts.ensure_loaded())
    await websocket.send_json({"type": "ready", "stage": "agent", "persona": persona})

    detector = TurnDetector(await get_vad(), sample_rate=settings.stt_sample_rate)
    history: list[dict[str, str]] = []
    state = "listening"
    turn_task: asyncio.Task | None = None

    async def handle_turn(pcm: bytes) -> None:
        nonlocal state
        turn_start = time.perf_counter()
        state = "thinking"
        await websocket.send_json({"type": "thinking"})

        try:
            result = await stt.transcribe(pcm, settings.stt_sample_rate)
            await websocket.send_json(
                {
                    "type": "transcript",
                    "text": result.text,
                    "language": result.language,
                    "audio_ms": round(result.audio_ms),
                    "stt_ms": round(result.elapsed_ms),
                }
            )
            if not result.text:
                return

            history.append({"role": "user", "content": result.text})
            queue: asyncio.Queue[str | None] = asyncio.Queue()

            async def tts_worker() -> None:
                nonlocal state
                first_frame = True
                while True:
                    sentence = await queue.get()
                    if sentence is None:
                        return
                    try:
                        samples, sample_rate = await tts.synth(sentence)
                    except Exception:
                        logger.exception("TTS synthesis failed")
                        continue
                    if first_frame:
                        first_frame = False
                        state = "speaking"
                        await websocket.send_json({"type": "speaking"})
                    async for frame in audio_frames(samples, settings.tts_frame_samples):
                        await websocket.send_bytes(frame)
                    await websocket.send_json({"type": "sentence_end", "text": sentence.strip()})

            worker = asyncio.create_task(tts_worker())
            try:
                chunker = SentenceChunker()
                reply: list[str] = []
                first_token_ms: int | None = None
                async for delta in llm.stream_chat(build_messages(history, persona)):
                    if first_token_ms is None:
                        first_token_ms = round((time.perf_counter() - turn_start) * 1000)
                    reply.append(delta)
                    await websocket.send_json({"type": "llm_delta", "text": delta})
                    for sentence in chunker.add(delta):
                        await queue.put(sentence)
                for sentence in chunker.flush():
                    await queue.put(sentence)
                await queue.put(None)
                await worker

                reply_text = "".join(reply).strip()
                if reply_text:
                    history.append({"role": "assistant", "content": reply_text})
                await websocket.send_json(
                    {
                        "type": "turn_done",
                        "metrics": {
                            "stt_ms": round(result.elapsed_ms),
                            "llm_first_token_ms": first_token_ms,
                            "total_ms": round((time.perf_counter() - turn_start) * 1000),
                        },
                    }
                )
            except asyncio.CancelledError:
                worker.cancel()
                queue.put_nowait(None)
                raise
        except LLMError as exc:
            await websocket.send_json({"type": "error", "reason": str(exc)})
        finally:
            state = "listening"

    logger.info(f"Agent WebSocket client connected (persona={persona})")
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if (text := message.get("text")) is not None:
                if text == "ping":
                    await websocket.send_json({"type": "pong"})
                continue
            if (audio := message.get("bytes")) is None:
                continue

            for event in detector.process_chunk(audio):
                if event.type == "speech_start":
                    if state in ("thinking", "speaking"):
                        if turn_task is not None:
                            turn_task.cancel()
                            turn_task = None
                        state = "listening"
                        await websocket.send_json({"type": "interrupted"})
                        logger.info("Barge-in: cancelled agent turn")
                    await websocket.send_json({"type": "speech_start"})
                elif event.type == "utterance":
                    turn_task = asyncio.create_task(handle_turn(event.payload["audio_pcm"]))
    except WebSocketDisconnect:
        pass
    finally:
        if turn_task is not None:
            turn_task.cancel()
        logger.info("Agent WebSocket client disconnected")
