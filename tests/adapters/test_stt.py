from pathlib import Path

from saynow_ai_demo.adapters.stt import (
    FasterWhisperSTTAdapter,
    normalize_transcript_text,
)


class FakeSegment:
    def __init__(self, text: str):
        self.text = text


class FakeWhisperModel:
    def __init__(self):
        self.kwargs = None

    def transcribe(self, audio_path: str, **kwargs):
        self.kwargs = kwargs
        assert audio_path == "sample.webm"
        return [FakeSegment(" I want nice latte "), FakeSegment(" small sides ")], object()


def test_stt_adapter_uses_stable_english_options_and_domain_prompt():
    model = FakeWhisperModel()
    adapter = FasterWhisperSTTAdapter()
    adapter._model = model

    transcript = adapter.transcribe(Path("sample.webm"))

    assert transcript == "I want iced latte small size"
    assert model.kwargs["language"] == "en"
    assert model.kwargs["beam_size"] == 5
    assert model.kwargs["vad_filter"] is True
    assert model.kwargs["condition_on_previous_text"] is False
    assert "iced latte" in model.kwargs["initial_prompt"]


def test_normalize_transcript_text_handles_common_cafe_stt_errors():
    assert normalize_transcript_text("I want lce latte") == "I want iced latte"
    assert normalize_transcript_text("I want ice latte") == "I want iced latte"
    assert normalize_transcript_text("small sides") == "small size"
    assert normalize_transcript_text("for hair") == "for here"
