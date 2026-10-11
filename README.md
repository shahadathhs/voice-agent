# Voice Agent

Real-time voice agent you talk to in the browser: streaming speech-to-text, LLM
orchestration and neural text-to-speech over a single WebSocket — with natural
turn-taking and barge-in (interrupt it mid-sentence and it stops and listens).

Speech models run locally on CPU in Docker. Only the LLM call leaves the machine.

```
Mic ──▶ Silero VAD ──▶ faster-whisper ──▶ Groq LLM ──▶ Kokoro TTS ──▶ Speaker
        turn detection    STT (local)      streaming     (local)      streamed
```

## Highlights

- **Turn-taking** — Silero VAD (ONNX, 2MB) with hysteresis endpointing decides when
  you finished speaking. No push-to-talk.
- **Barge-in** — talking over the agent cancels the LLM stream and audio playback
  instantly via a server-side state machine (listening → thinking → speaking).
- **Sentence-chunked TTS** — the reply starts playing after the first complete
  sentence; the LLM is still generating the rest.
- **Instrumented latency** — every turn reports STT ms, LLM first-token ms and total
  turn ms to the client, shown live in the UI.
- **Local speech models** — faster-whisper (int8) + Kokoro (int8 ONNX) on CPU.
- **Evals included** — latency benchmark (p50/p95 per stage) and WER scripts.

## Architecture

Monorepo with two deployable pieces:

```
backend/   FastAPI + WebSockets (Python 3.12, uv)
  app/api/          WS endpoints: /ws/agent, /ws/stt, /ws (echo)
  app/pipeline/     turn detection (VAD), sentence chunker, state machine
  app/stt/          faster-whisper wrapper (lazy-load, async)
  app/tts/          Kokoro ONNX wrapper (lazy-load, async)
  app/llm/          Groq streaming client + personas
  app/vad/          Silero VAD (onnxruntime, no torch)
  app/evals/        latency benchmark + WER
web/       Next.js 16 (App Router, Tailwind)
  app/agent/        live conversation UI with latency dashboard
  app/play/         raw socket/STT test bench
deploy/    HF Space template
```

### Agent WebSocket protocol (`/ws/agent?persona=...`)

```
client → server : binary frames (16kHz mono PCM16 mic chunks)
server → client : JSON events + binary frames (24kHz mono float32 TTS audio)

{"type": "ready"}                         models loaded
{"type": "speech_start"}                  user started talking
{"type": "thinking"}                      transcribing + generating
{"type": "speaking"}                      first audio frame coming
{"type": "transcript", "text", "stt_ms"}  what you said
{"type": "llm_delta", "text"}             streamed reply tokens
{"type": "turn_done", "metrics"}          latency report
{"type": "interrupted"}                   barge-in acknowledged
```

## Quick start

```bash
make install          # backend (uv) + web (npm)
cp backend/.env.example backend/.env   # add your free GROQ_API_KEY
make dev              # backend :8000 + web :3000
```

Open http://localhost:3000/agent → **Start conversation** → talk.

Docker instead:

```bash
GROQ_API_KEY=... make up
```

Get a free Groq key at https://console.groq.com (free tier is enough).

## Tuning

All knobs live in `backend/.env` (see `.env.example`): VAD thresholds and silence
window, Whisper model size/compute, TTS voice, LLM model and max tokens.

## Evals

```bash
cd backend

# latency benchmark: STT → LLM first token → TTS first sentence (p50/p95)
uv run python -m app.evals.latency --iterations 5

# word error rate
uv run python -m app.evals.wer --text "reference text|||hypothesis text"
uv run python -m app.evals.wer --pairs pairs.json
```

## Deployment

The demo runs 100% free-tier:

1. **Backend → Hugging Face Space** (Docker SDK, free 2 vCPU):
   create a Space, push `backend/` with the front-matter from
   [`deploy/hf-space-README.md`](deploy/hf-space-README.md) prepended to its README,
   add `GROQ_API_KEY` as a Space secret. Models download on first boot and are
   cached while the Space stays warm.
2. **Frontend → Vercel**: import the repo, root dir `web/`, set
   `NEXT_PUBLIC_API_WS_URL=wss://<your-space>.hf.space`.
3. Record a local demo as backup for cold starts.

## Development

```bash
make lint       # ruff (backend) + eslint (web)
make test       # backend tests (24)
make build      # web production build + docker images
make help       # all targets
```

## Roadmap

- [x] Phase 0 — monorepo scaffold, WebSocket echo, CI
- [x] Phase 1 — mic capture → streaming STT transcription
- [x] Phase 2 — LLM streaming + sentence-chunked TTS playback
- [x] Phase 3 — Silero VAD turn-taking, barge-in, latency instrumentation
- [x] Phase 4 — conversation UI, personas, latency dashboard
- [x] Phase 5 — evals, HF Spaces + Vercel deploy config
- [ ] Voice-activity visualization / word-level partial transcripts
- [ ] Streaming (chunked) TTS inference

## Stack

FastAPI · WebSockets · Silero VAD · faster-whisper (CTranslate2) · Groq ·
Kokoro ONNX · onnxruntime · Next.js 16 · WebAudio/AudioWorklet · Docker ·
GitHub Actions

## License

MIT
