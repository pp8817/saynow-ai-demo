import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnEvaluation:
    understood_score: int
    interpreted_as: str
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

Score calibration:
- understood_score means how likely a foreigner would understand the user's exact English message in this turn.
- Scenario completion is separate from understood_score. Missing slots should drive follow_up_question.
- Do not inflate beginner fragments. "I want latte" should be around 78 because the drink is clear but the expression is unnatural and incomplete.
- 90-100: natural, clear, and complete answer to the current question.
- 80-89: clear intention with minor unnatural wording.
- 70-79: understandable but beginner-like, fragmented, or missing small grammar words.
- 50-69: partially understandable but important meaning is ambiguous.
- 0-49: mostly unclear or unrelated.

Slot rules:
- Only include newly identified slot values in filled_slots.
- Do not invent slot values. For example, "I want latte" fills drink only, not size or temperature.

Language rules:
- interpreted_as must be Korean and start with "외국인에게는".
- Do not mention pronunciation or intonation because this transcript may come from the text endpoint.

Return only one JSON object with these keys:
- understood_score: integer from 0 to 100
- interpreted_as: short Korean explanation of what a foreigner would likely understand
- filled_slots: object of newly identified slot values
- follow_up_question: one short English question to fill the most important missing slot
"""


def parse_turn_evaluation(raw: str) -> TurnEvaluation:
    try:
        payload = _load_first_json_object(raw)
    except ValueError:
        return TurnEvaluation(
            understood_score=30,
            interpreted_as="AI가 발화 의미를 안정적으로 해석하지 못했습니다.",
            filled_slots={},
            follow_up_question="Could you say that again more clearly?",
        )

    return TurnEvaluation(
        understood_score=_clamp_score(payload.get("understood_score", 30)),
        interpreted_as=str(
            payload.get("interpreted_as")
            or "AI가 발화 의미를 안정적으로 해석하지 못했습니다."
        ),
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


def _clamp_score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 30
    return max(0, min(score, 100))
