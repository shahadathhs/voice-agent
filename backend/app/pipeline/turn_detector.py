import numpy as np

from app.core.config import get_settings
from app.pipeline.session import SessionEvent
from app.vad import SileroVAD

WINDOW_SAMPLES = 512
CONTEXT_SAMPLES = 64
KEEP_TRAILING_S = 0.2


class TurnDetector:
    def __init__(self, vad: SileroVAD, sample_rate: int = 16000) -> None:
        settings = get_settings()
        self.vad = vad
        self.sample_rate = sample_rate
        self.threshold_start = settings.vad_threshold_start
        self.threshold_end = settings.vad_threshold_end
        self.silence_ms = settings.vad_silence_ms
        self.min_speech_ms = settings.vad_min_speech_ms
        self.max_utterance_ms = settings.vad_max_utterance_ms
        self.reset()

    @property
    def speech_active(self) -> bool:
        return self._speech_started

    def reset(self) -> None:
        self._pending = np.empty(0, dtype=np.int16)
        self._utterance: list[np.ndarray] = []
        self._speech_started = False
        self._speech_samples = 0
        self._trailing_silence_samples = 0

    def process_chunk(self, pcm16: bytes) -> list[SessionEvent]:
        audio = np.frombuffer(pcm16, dtype=np.int16)
        self._pending = np.concatenate([self._pending, audio])

        events: list[SessionEvent] = []
        window = WINDOW_SAMPLES + CONTEXT_SAMPLES

        while len(self._pending) >= window:
            segment = self._pending[:window]
            self._pending = self._pending[WINDOW_SAMPLES:]
            self._evaluate_window(segment, events)

        return events

    def _evaluate_window(self, segment: np.ndarray, events: list[SessionEvent]) -> None:
        probability = self.vad.probability(segment.astype(np.float32) / 32768.0)
        new_samples = segment[CONTEXT_SAMPLES:]

        if probability >= self.threshold_start:
            if not self._speech_started:
                self._speech_started = True
                events.append(SessionEvent("speech_start"))
            self._speech_samples += WINDOW_SAMPLES
            self._trailing_silence_samples = 0
            self._utterance.append(new_samples.copy())
        elif self._speech_started:
            self._utterance.append(new_samples.copy())
            if probability >= self.threshold_end:
                self._speech_samples += WINDOW_SAMPLES
                self._trailing_silence_samples = 0
            else:
                self._trailing_silence_samples += WINDOW_SAMPLES

        if self._speech_started and self._should_endpoint():
            events.extend(self._emit_utterance())

    def _should_endpoint(self) -> bool:
        silence_ms = self._trailing_silence_samples / self.sample_rate * 1000
        speech_ms = self._speech_samples / self.sample_rate * 1000
        return silence_ms >= self.silence_ms or speech_ms >= self.max_utterance_ms

    def _emit_utterance(self) -> list[SessionEvent]:
        speech_ms = self._speech_samples / self.sample_rate * 1000
        pcm = self._collect_audio()
        self.reset()
        self.vad.reset()
        if speech_ms < self.min_speech_ms:
            return []
        return [SessionEvent("utterance", {"audio_pcm": pcm, "duration_ms": round(speech_ms)})]

    def _collect_audio(self) -> bytes:
        if not self._utterance:
            return b""
        audio = np.concatenate(self._utterance)
        max_trailing = int(KEEP_TRAILING_S * self.sample_rate)
        drop = max(0, self._trailing_silence_samples - max_trailing)
        if drop > 0:
            audio = audio[:-drop]
        return audio.tobytes()
