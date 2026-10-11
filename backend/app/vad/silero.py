import asyncio
from pathlib import Path

import numpy as np
import onnxruntime as ort

from app.core.logger import logger
from app.core.models import SILERO_VAD_URL, ensure_model

CONTEXT_SAMPLES = 64
WINDOW_SAMPLES = 512


class SileroVAD:
    def __init__(self, model_path: str | Path) -> None:
        options = ort.SessionOptions()
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.reset()
        logger.info("Silero VAD loaded")

    @classmethod
    async def create(cls) -> "SileroVAD":
        path = await asyncio.to_thread(ensure_model, "silero_vad.onnx", SILERO_VAD_URL)
        return cls(path)

    def reset(self) -> None:
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SAMPLES), dtype=np.float32)

    def probability(self, chunk: np.ndarray) -> float:
        x = np.concatenate([self._context, chunk.reshape(1, -1)], axis=1).astype(np.float32)
        outputs, state = self.session.run(
            None,
            {
                "input": x,
                "state": self._state,
                "sr": np.array(16000, dtype=np.int64),
            },
        )
        self._state = state
        self._context = x[:, -CONTEXT_SAMPLES:]
        return float(outputs[0][0])
