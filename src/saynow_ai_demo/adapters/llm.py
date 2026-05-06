from typing import Protocol

import httpx

from saynow_ai_demo.config import settings
from saynow_ai_demo.domain.models import Scenario
from saynow_ai_demo.services.evaluator import (
    TurnEvaluation,
    build_turn_prompt,
    parse_turn_evaluation,
)


class LocalLLMUnavailableError(RuntimeError):
    """Raised when the local Ollama server cannot be reached."""


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


class OllamaClient:
    def __init__(
        self,
        base_url: str = settings.ollama_url,
        model: str = settings.ollama_model,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return str(response.json().get("response", ""))


class OllamaEvaluator:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or OllamaClient()

    def evaluate(
        self,
        *,
        scenario: Scenario,
        current_slots: dict[str, str],
        transcript: str,
    ) -> TurnEvaluation:
        prompt = build_turn_prompt(
            scenario_title=scenario.title,
            required_slots=scenario.required_slots,
            current_slots=current_slots,
            transcript=transcript,
        )
        try:
            raw_response = self.llm_client.complete(prompt)
        except Exception as exc:
            raise LocalLLMUnavailableError(
                "Ollama가 실행 중이 아니어서 AI 평가를 진행할 수 없습니다. "
                "`ollama serve` 실행 후 다시 시도하세요."
            ) from exc
        return parse_turn_evaluation(raw_response)
