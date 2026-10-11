from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from app.core.config import get_settings

TRAILING_SILENCE_S = 0.2


@dataclass
class SessionEvent:
    type: str
    payload: dict = field(default_factory=dict)


class TranscriptionSession:
    def __init__(self, sample_rate: int = 16000) -> None:
        settings = get_settings()
        self.sample_rate = sample_rate
        self.rms_threshold = settings.rms_threshold
        self.silence_ms = settings.silence_duration_ms
        self.min_utterance_ms = settings.min_utterance_ms
        self.max_utterance_ms = settings.max_utterance_ms

        self._buffer: list[np.ndarray] = []
        self._buffer_samples = 0
        self._speech_samples = 0
        self._silence_samples = 0
        self._speech_started = False

        self.on_speech_start: Callable[[], None] | None = None

    @property
    def speech_active(self) -> bool:
        return self._speech_started

    def process_chunk(self, pcm16: bytes) -> list[SessionEvent]:
        audio = np.frombuffer(pcm16, dtype=np.int16)
        rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))) / 32768.0

        events: list[SessionEvent] = []

        if rms >= self.rms_threshold:
            if not self._speech_started:
                self._speech_started = True
                events.append(SessionEvent("speech_start"))
                if self.on_speech_start:
                    self.on_speech_start()
            self._silence_samples = 0
            self._speech_samples += len(audio)
        elif self._speech_started:
            self._silence_samples += len(audio)

        if self._speech_started:
            self._buffer.append(audio)
            self._buffer_samples += len(audio)

        if self._should_endpoint():
            pcm = self._trimmed_pcm()
            speech_ms = self._speech_samples / self.sample_rate * 1000
            self._reset()
            if speech_ms >= self.min_utterance_ms:
                events.append(
                    SessionEvent("utterance", {"audio_pcm": pcm, "duration_ms": round(speech_ms)})
                )

        return events

    def _should_endpoint(self) -> bool:
        if not self._speech_started:
            return False
        buffer_ms = self._buffer_samples / self.sample_rate * 1000
        silence_ms = self._silence_samples / self.sample_rate * 1000
        return silence_ms >= self.silence_ms or buffer_ms >= self.max_utterance_ms

    def _trimmed_pcm(self) -> bytes:
        if not self._buffer:
            return b""
        pcm = np.concatenate(self._buffer)
        max_trailing = int(TRAILING_SILENCE_S * self.sample_rate)
        drop = max(0, self._silence_samples - max_trailing)
        if drop > 0:
            pcm = pcm[:-drop]
        return pcm.tobytes()

    def _reset(self) -> None:
        self._buffer = []
        self._buffer_samples = 0
        self._speech_samples = 0
        self._silence_samples = 0
        self._speech_started = False
