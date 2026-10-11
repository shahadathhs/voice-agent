import urllib.request
from pathlib import Path

from app.core.config import get_settings
from app.core.logger import logger

SILERO_VAD_URL = (
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
)
KOKORO_BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
KOKORO_MODEL = "kokoro-v1.0.int8.onnx"
KOKORO_VOICES = "voices-v1.0.bin"


def cache_dir() -> Path:
    path = Path(get_settings().model_cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_model(name: str, url: str) -> Path:
    dest = cache_dir() / name
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    logger.info(f"Downloading model '{name}' to {dest}...")
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)
    logger.info(f"Downloaded {name} ({dest.stat().st_size // 1024 // 1024}MB)")
    return dest
