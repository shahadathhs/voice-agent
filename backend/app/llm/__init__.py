import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logger import logger

PERSONAS: dict[str, str] = {
    "assistant": (
        "You are a friendly voice assistant in a real-time spoken conversation. "
        "Keep replies short and natural: 1-3 sentences, plain words, no markdown, "
        "no lists, no emoji. Speak as if talking out loud."
    ),
    "interviewer": (
        "You are a technical interviewer practicing behavioral interview questions "
        "with the user. Ask one clear question at a time, listen to the answer, and "
        "briefly respond before moving on. Keep replies under 3 sentences."
    ),
    "storyteller": (
        "You are a storyteller telling very short spoken stories. Each reply continues "
        "the tale in 2-4 vivid sentences with a natural speaking rhythm. No markdown, "
        "no headings, just spoken prose."
    ),
}


class LLMError(Exception):
    pass


class GroqClient:
    def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        return self._stream(messages)

    async def _stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        settings = get_settings()
        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": messages,
            "stream": True,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }
        headers = {"Authorization": f"Bearer {settings.groq_api_key}"}

        try:
            async with (
                httpx.AsyncClient(
                    base_url=settings.groq_base_url,
                    timeout=httpx.Timeout(60.0, connect=10.0),
                ) as client,
                client.stream(
                    "POST", "/chat/completions", json=payload, headers=headers
                ) as response,
            ):
                if response.status_code != 200:
                    body = (await response.aread()).decode(errors="replace")
                    logger.error(f"Groq API error {response.status_code}: {body[:300]}")
                    raise LLMError(f"Groq API returned {response.status_code}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data.strip() == "[DONE]":
                        return
                    parsed = json.loads(data)
                    delta = parsed["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
        except httpx.HTTPError as exc:
            raise LLMError(f"Groq request failed: {exc}") from exc


def build_messages(history: list[dict[str, str]], persona: str) -> list[dict[str, str]]:
    from app.core.config import get_settings

    system = PERSONAS.get(persona, PERSONAS["assistant"])
    trimmed = history[-get_settings().max_history_messages :]
    return [{"role": "system", "content": system}, *trimmed]
