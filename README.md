# Voice Agent

Real-time voice agent with streaming speech-to-text, LLM orchestration and neural
text-to-speech — natural turn-taking, barge-in support, sub-1.5s response latency.

**Status:** Phase 1 — live speech-to-text. Talk in your browser, see the transcript.

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

Open http://localhost:3000/play and hit **Start talking** — the browser streams
16kHz PCM over `/ws/stt`, the backend endpoints utterances via RMS silence
detection and transcribes them with faster-whisper.

## STT pipeline

```
mic (AudioWorklet, 16kHz PCM16) → WebSocket → RMS gate → utterance buffering
  → silence endpointing (700ms) → faster-whisper (base, int8, CPU) → transcript event
```

Tuning knobs (env vars, see `backend/app/core/config.py`): `WHISPER_MODEL`,
`RMS_THRESHOLD`, `SILENCE_DURATION_MS`, `MIN_UTTERANCE_MS`, `MAX_UTTERANCE_MS`.

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
- [x] Phase 1 — mic capture → streaming STT transcription
- [ ] Phase 2 — LLM streaming + TTS playback
- [ ] Phase 3 — VAD turn-taking, barge-in, latency instrumentation
- [ ] Phase 4 — conversation UI polish, latency dashboard
- [ ] Phase 5 — HF Spaces deploy, evals, demo video

## License

MIT
