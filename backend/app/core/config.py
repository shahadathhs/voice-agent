from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Voice Agent"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000

    cors_origins: list[str] = ["http://localhost:3000"]

    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    stt_sample_rate: int = 16000
    rms_threshold: float = 0.008
    silence_duration_ms: int = 700
    min_utterance_ms: int = 300
    max_utterance_ms: int = 15000


@lru_cache
def get_settings() -> Settings:
    return Settings()
