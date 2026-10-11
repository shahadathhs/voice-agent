import numpy as np

from app.pipeline.turn_detector import TurnDetector

SAMPLE_RATE = 16000


class FakeVAD:
    def __init__(self) -> None:
        self.probs: list[float] = []

    def probability(self, chunk: np.ndarray) -> float:
        return self.probs.pop(0) if self.probs else 0.0

    def reset(self) -> None:
        pass


def make_detector() -> tuple[TurnDetector, FakeVAD]:
    vad = FakeVAD()
    return TurnDetector(vad, sample_rate=SAMPLE_RATE), vad


def chunk_of(ms: int) -> bytes:
    samples = int(SAMPLE_RATE * ms / 1000)
    t = np.linspace(0, ms / 1000, samples, endpoint=False)
    return (0.3 * np.sin(2 * np.pi * 200 * t) * 32767).astype(np.int16).tobytes()


def speech(n: int) -> list[float]:
    return [0.1, *[0.9] * n]


def feed(detector: TurnDetector, vad: FakeVAD, probs: list[float]) -> list:
    vad.probs = probs
    events: list = []
    for _ in range(30):
        events.extend(detector.process_chunk(chunk_of(600)))
        if not vad.probs and not detector.speech_active:
            break
    events.extend(detector.process_chunk(chunk_of(700)))
    return events


def test_speech_start_and_utterance() -> None:
    detector, vad = make_detector()
    events = feed(detector, vad, speech(12))
    types = [e.type for e in events]
    assert types == ["speech_start", "utterance"]
    pcm = events[1].payload["audio_pcm"]
    duration_ms = len(pcm) / 2 / SAMPLE_RATE * 1000
    assert 300 <= duration_ms <= 800


def test_below_threshold_noise_ignored() -> None:
    detector, vad = make_detector()
    assert feed(detector, vad, []) == []


def test_too_short_speech_not_emitted() -> None:
    detector, vad = make_detector()
    events = feed(detector, vad, speech(3))
    assert [e.type for e in events] == ["speech_start"]


def test_detector_reusable_after_utterance() -> None:
    detector, vad = make_detector()
    first = feed(detector, vad, speech(10))
    assert [e.type for e in first] == ["speech_start", "utterance"]

    second = feed(detector, vad, speech(10))
    assert [e.type for e in second] == ["speech_start", "utterance"]


def test_partial_window_carries_over() -> None:
    detector, vad = make_detector()
    vad.probs = speech(10)
    first = detector.process_chunk(chunk_of(100))
    assert [e.type for e in first] == ["speech_start"]
    rest = detector.process_chunk(chunk_of(1000))
    assert [e.type for e in rest] == ["utterance"]


def test_max_utterance_forced() -> None:
    detector, vad = make_detector()
    events = feed(detector, vad, speech(500))
    types = [e.type for e in events]
    assert "speech_start" in types
    assert "utterance" in types
