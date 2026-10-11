import numpy as np

from app.pipeline import TranscriptionSession

SAMPLE_RATE = 16000


def speech_chunk(ms: int, freq: int = 200, amp: float = 0.3) -> bytes:
    t = np.linspace(0, ms / 1000, int(SAMPLE_RATE * ms / 1000), endpoint=False)
    samples = (amp * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    return samples.tobytes()


def silence_chunk(ms: int) -> bytes:
    return np.zeros(int(SAMPLE_RATE * ms / 1000), dtype=np.int16).tobytes()


def feed(session: TranscriptionSession, *chunks: bytes) -> list:
    events = []
    for chunk in chunks:
        events.extend(session.process_chunk(chunk))
    return events


def test_speech_start_and_utterance_events() -> None:
    session = TranscriptionSession()
    events = feed(
        session,
        silence_chunk(200),
        speech_chunk(100),
        speech_chunk(100),
        speech_chunk(100),
        speech_chunk(100),
        silence_chunk(700),
    )
    types = [e.type for e in events]
    assert types == ["speech_start", "utterance"]

    utterance = events[1]
    assert utterance.payload["audio_pcm"]
    duration_ms = len(utterance.payload["audio_pcm"]) / 2 / SAMPLE_RATE * 1000
    assert 400 <= duration_ms <= 700


def test_no_utterance_for_too_short_noise() -> None:
    session = TranscriptionSession()
    events = feed(session, speech_chunk(100), silence_chunk(700))
    assert [e.type for e in events] == ["speech_start"]


def test_session_resets_after_utterance() -> None:
    session = TranscriptionSession()
    feed(session, speech_chunk(500), silence_chunk(800))

    assert session.speech_active is False

    events = feed(session, speech_chunk(500), silence_chunk(800))
    types = [e.type for e in events]
    assert types == ["speech_start", "utterance"]


def test_continued_silence_does_not_retrigger() -> None:
    session = TranscriptionSession()
    events = feed(session, speech_chunk(500), silence_chunk(700), silence_chunk(2000))
    assert [e.type for e in events] == ["speech_start", "utterance"]


def test_max_utterance_forced_endpoint() -> None:
    session = TranscriptionSession()
    events = feed(session, *(speech_chunk(100) for _ in range(160)))
    types = [e.type for e in events]
    assert "utterance" in types
