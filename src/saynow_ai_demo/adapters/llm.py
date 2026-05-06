from typing import Protocol

import httpx

from saynow_ai_demo.config import settings
from saynow_ai_demo.domain.models import Scenario
from saynow_ai_demo.services.evaluator import (
    TurnEvaluation,
    build_turn_prompt,
    parse_turn_evaluation,
)


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
            return parse_turn_evaluation(self.llm_client.complete(prompt))
        except Exception:
            return build_local_fallback_evaluation(
                required_slots=scenario.required_slots,
                current_slots=current_slots,
                transcript=transcript,
            )


def build_local_fallback_evaluation(
    *,
    required_slots: tuple[str, ...],
    current_slots: dict[str, str],
    transcript: str,
) -> TurnEvaluation:
    lowered = transcript.lower()
    filled_slots: dict[str, str] = {}

    drink = _detect_drink(lowered)
    if drink:
        filled_slots["drink"] = drink

    temperature = _detect_temperature(lowered)
    if temperature:
        filled_slots["temperature"] = temperature

    size = _detect_size(lowered)
    if size:
        filled_slots["size"] = size

    order_type = _detect_order_type(lowered)
    if order_type:
        filled_slots["for_here_or_to_go"] = order_type

    merged_slots = {**current_slots, **filled_slots}
    missing_slots = tuple(
        slot for slot in required_slots if not merged_slots.get(slot)
    )
    return TurnEvaluation(
        understood_score=_fallback_score(filled_slots),
        interpreted_as=_fallback_interpretation(filled_slots),
        filled_slots=filled_slots,
        follow_up_question=_fallback_question(missing_slots),
    )


def _detect_drink(lowered: str) -> str:
    if "latte" in lowered:
        return "latte"
    if "americano" in lowered:
        return "americano"
    if "coffee" in lowered:
        return "coffee"
    if "tea" in lowered:
        return "tea"
    return ""


def _detect_temperature(lowered: str) -> str:
    if "ice " in lowered or "iced" in lowered:
        return "iced"
    if "hot" in lowered:
        return "hot"
    return ""


def _detect_size(lowered: str) -> str:
    for size in ("small", "medium", "large", "tall", "grande", "venti"):
        if size in lowered:
            return size
    return ""


def _detect_order_type(lowered: str) -> str:
    if "to go" in lowered or "take out" in lowered or "takeout" in lowered:
        return "to go"
    if "for here" in lowered or "here" in lowered:
        return "for here"
    return ""


def _fallback_score(filled_slots: dict[str, str]) -> int:
    return min(50 + len(filled_slots) * 8, 90)


def _fallback_interpretation(filled_slots: dict[str, str]) -> str:
    if not filled_slots:
        return "Local fallback could not identify the user's order clearly."
    details = ", ".join(f"{slot}: {value}" for slot, value in filled_slots.items())
    return f"Local fallback understood these order details: {details}."


def _fallback_question(missing_slots: tuple[str, ...]) -> str:
    fallback_by_slot = {
        "drink": "What would you like to order?",
        "size": "What size would you like?",
        "temperature": "Would you like it hot or iced?",
        "for_here_or_to_go": "Is that for here or to go?",
    }
    first_missing = missing_slots[0] if missing_slots else "drink"
    return fallback_by_slot.get(first_missing, "Could you say that again?")
