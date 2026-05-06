import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnEvaluation:
    filled_slots: dict[str, str]
    follow_up_question: str


def build_turn_prompt(
    scenario_title: str,
    required_slots: tuple[str, ...],
    current_slots: dict[str, str],
    transcript: str,
) -> str:
    return f"""
You are evaluating a beginner English learner in this scenario: {scenario_title}.

Required slots: {list(required_slots)}
Already filled slots: {current_slots}
User transcript: {transcript}

Slot rules:
- Only include newly identified slot values in filled_slots.
- Do not invent slot values. For example, "I want latte" fills drink only, not size or temperature.
- During the conversation, do not score the answer and do not provide feedback.
- Your only job is slot tracking and the next follow-up question.

Return only one JSON object with these keys:
- filled_slots: object of newly identified slot values
- follow_up_question: one short English question to fill the most important missing slot
"""


def parse_turn_evaluation(raw: str) -> TurnEvaluation:
    try:
        payload = _load_first_json_object(raw)
    except ValueError:
        return TurnEvaluation(
            filled_slots={},
            follow_up_question="Could you say that again more clearly?",
        )

    return TurnEvaluation(
        filled_slots={
            str(key): str(value)
            for key, value in dict(payload.get("filled_slots") or {}).items()
            if str(value).strip()
        },
        follow_up_question=str(
            payload.get("follow_up_question")
            or "Could you say that again more clearly?"
        ),
    )


def _load_first_json_object(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("no JSON object found")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON object") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON object must be a dictionary")
    return data
