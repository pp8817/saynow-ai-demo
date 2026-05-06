from pathlib import Path
from typing import Protocol

from saynow_ai_demo.config import settings


class STTAdapter(Protocol):
    def transcribe(self, audio_path: Path) -> str:
        ...


class FasterWhisperSTTAdapter:
    def __init__(self, model_name: str = settings.whisper_model):
        self.model_name = model_name
        self._model = None

    def transcribe(self, audio_path: Path) -> str:
        model = self._get_model()
        segments, _info = model.transcribe(str(audio_path), language="en")
        return " ".join(segment.text.strip() for segment in segments).strip()

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )
        return self._model
