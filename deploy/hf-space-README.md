---
title: Voice Agent
emoji: 🎙️
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: true
license: mit
---

# Voice Agent — backend

Real-time voice agent WebSocket server. This Space runs the FastAPI backend;
the Next.js frontend lives in the main repo (deploy it on Vercel and point
`NEXT_PUBLIC_API_WS_URL` at this Space's `wss://` URL).

## Endpoints

- `GET /health` — service + model status
- `WS /ws/agent?persona=assistant` — full agent pipeline
- `WS /ws/stt` — transcription only
- `WS /ws` — echo test

## Notes

- Models (Silero VAD, faster-whisper, Kokoro) download on first start into
  `/data/model-cache` and are cached while the Space is warm.
- Set `GROQ_API_KEY` as a Space secret to enable the LLM brain.
