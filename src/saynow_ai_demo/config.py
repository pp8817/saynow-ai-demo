import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("SAYNOW_OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("SAYNOW_OLLAMA_MODEL", "qwen2.5:7b-instruct")
    whisper_model: str = os.getenv("SAYNOW_WHISPER_MODEL", "small.en")


settings = Settings()
