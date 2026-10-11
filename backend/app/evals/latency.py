import argparse
import asyncio
import time
import wave
from pathlib import Path
from statistics import median

import numpy as np

from app.core.config import get_settings
from app.llm import LLMError, build_messages
from app.pipeline.chunker import SentenceChunker
from app.services import llm, stt, tts

FIXED_UTTERANCE = "Hey, can you tell me a fun fact about the ocean?"
SAMPLE_WAV = Path("/tmp/voice-agent-eval-turn.wav")


async def make_fake_user_audio() -> bytes:
    settings = get_settings()
    samples, rate = await tts.synth(FIXED_UTTERANCE)
    with wave.open(str(SAMPLE_WAV), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((samples * 32767).astype(np.int16).tobytes())

    import av

    container = av.open(str(SAMPLE_WAV))
    resampler = av.AudioResampler(format="s16", layout="mono", rate=settings.stt_sample_rate)
    pcm = bytearray()
    for frame in container.decode(audio=0):
        for resampled in resampler.resample(frame):
            pcm.extend(resampled.to_ndarray().tobytes())
    return bytes(pcm)


async def run(prompt: str, iterations: int) -> dict[str, list[float]]:
    await stt.get_model()
    await tts.ensure_loaded()
    pcm = await make_fake_user_audio()

    stt_times: list[float] = []
    llm_times: list[float] = []
    tts_times: list[float] = []
    totals: list[float] = []

    for i in range(iterations):
        turn_start = time.perf_counter()

        t0 = time.perf_counter()
        result = await stt.transcribe(pcm, get_settings().stt_sample_rate)
        stt_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        first_sentence: str | None = None
        chunker = SentenceChunker()
        try:
            async for delta in llm.stream_chat(
                build_messages([{"role": "user", "content": prompt or result.text}], "assistant")
            ):
                if first_sentence is None:
                    llm_times.append((time.perf_counter() - t0) * 1000)
                    for sentence in chunker.add(delta):
                        first_sentence = sentence
                        break
                if first_sentence is not None:
                    break
            if first_sentence is None:
                for sentence in chunker.flush():
                    if first_sentence is None:
                        first_sentence = sentence
        except LLMError:
            print("LLM not configured — set GROQ_API_KEY to benchmark the full pipeline")
            raise SystemExit(1) from None

        t0 = time.perf_counter()
        await tts.synth(first_sentence or "Okay.")
        tts_times.append((time.perf_counter() - t0) * 1000)

        totals.append((time.perf_counter() - turn_start) * 1000)
        print(f"  turn {i + 1}/{iterations} done")

    return {
        "stt_ms": stt_times,
        "llm_first_token_ms": llm_times,
        "tts_first_sentence_ms": tts_times,
        "turn_total_ms": totals,
    }


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * p))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice agent latency benchmark")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--prompt", default="Tell me a one-sentence fun fact about space.")
    args = parser.parse_args()

    print(f"Benchmarking {args.iterations} turns (STT → LLM first token → TTS first sentence)...")
    results = asyncio.run(run(args.prompt, args.iterations))

    print(f"\n{'stage':26s} {'median':>10s} {'p95':>10s}")
    print("-" * 48)
    for name, values in results.items():
        print(f"{name:26s} {median(values):9.1f}ms {percentile(values, 0.95):9.1f}ms")


if __name__ == "__main__":
    main()
