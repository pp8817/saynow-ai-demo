import re
from pathlib import Path
from typing import Protocol

from saynow_ai_demo.config import settings

CAFE_STT_PROMPT = (
    "Cafe ordering English. Common phrases: iced latte, hot latte, "
    "small size, medium size, large size, for here, to go."
)


class STTAdapter(Protocol):
    def transcribe(self, audio_path: Path) -> str:
        ...


def normalize_transcript_text(transcript: str) -> str:
    text = " ".join(transcript.split())
    replacements = (
        (r"\blce latte\b", "iced latte"),
        (r"\bice latte\b", "iced latte"),
        (r"\bnice latte\b", "iced latte"),
        (r"\bsmall sides\b", "small size"),
        (r"\bmedium sides\b", "medium size"),
        (r"\blarge sides\b", "large size"),
        (r"\bfor hair\b", "for here"),
        (r"\btwo go\b", "to go"),
        (r"\bto-go\b", "to go"),
        (r"\btake out\b", "to go"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text.strip()


class FasterWhisperSTTAdapter:
    def __init__(self, model_name: str = settings.whisper_model):
        self.model_name = model_name
        self._model = None

    def transcribe(self, audio_path: Path) -> str:
        model = self._get_model()
        segments, _info = model.transcribe(
            str(audio_path),
            language="en",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
            initial_prompt=CAFE_STT_PROMPT,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return normalize_transcript_text(transcript)

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )
        return self._model
