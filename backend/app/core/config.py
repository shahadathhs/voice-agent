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

    model_cache_dir: str = "model-cache"

    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 300

    tts_voice: str = "af_heart"
    tts_lang: str = "en-us"
    tts_speed: float = 1.0
    tts_frame_samples: int = 8192

    stt_sample_rate: int = 16000
    rms_threshold: float = 0.008
    silence_duration_ms: int = 700
    min_utterance_ms: int = 300
    max_utterance_ms: int = 15000

    vad_threshold_start: float = 0.5
    vad_threshold_end: float = 0.35
    vad_silence_ms: int = 600
    vad_min_speech_ms: int = 250
    vad_max_utterance_ms: int = 15000

    max_history_messages: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
