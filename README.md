# Voice Agent

Real-time voice agent with streaming speech-to-text, LLM orchestration and neural
text-to-speech — natural turn-taking, barge-in support, sub-1.5s response latency.

**Status:** Phase 0 — foundation. WebSocket echo pipeline live.

## The pipeline

```
Mic → VAD (Silero) → STT (faster-whisper) → LLM (Groq) → TTS (Kokoro) → Speaker
```

- **Turn-taking** — Silero VAD detects end-of-speech, no push-to-talk
- **Barge-in** — interrupt the agent mid-sentence, streams cancel instantly
- **Sentence-chunked TTS** — audio starts playing while the LLM is still generating
- **Local ASR/TTS** — speech models run in Docker on your machine

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, WebSockets, uv |
| STT | faster-whisper |
| LLM | Groq API (streaming) |
| TTS | kokoro-onnx |
| VAD | Silero-vad |
| Frontend | Next.js 16, React 19, Tailwind, WebAudio API |
| Infra | Docker Compose, GitHub Actions |

## Quick start

### Docker Compose (recommended)

```bash
make up
# web:  http://localhost:3000
# api:  http://localhost:8000

make down   # stop
```

### Local development

```bash
make install   # backend (uv) + web (npm)
make dev       # backend :8000 + web :3000 with hot reload
```

Open http://localhost:3000/play, connect to `ws://localhost:8000/ws` and send a
test chunk to verify the pipeline.

## Development

```bash
make lint     # ruff (backend) + eslint (web)
make format   # auto-format backend
make test     # backend tests
make build    # web production build + docker images
make help     # list all targets
```

## Roadmap

- [x] Phase 0 — monorepo scaffold, WebSocket echo, CI
- [ ] Phase 1 — mic capture → streaming STT transcription
- [ ] Phase 2 — LLM streaming + TTS playback
- [ ] Phase 3 — VAD turn-taking, barge-in, latency instrumentation
- [ ] Phase 4 — conversation UI polish, latency dashboard
- [ ] Phase 5 — HF Spaces deploy, evals, demo video

## License

MIT
