import json
import re
from typing import Any

from saynow_ai_demo.domain.models import SessionState


def build_feedback_prompt(session: SessionState) -> str:
    conversation = [
        {
            "turn_id": turn.id,
            "user_said": turn.transcript,
            "ai_question_after_user_answer": turn.assistant_message,
            "filled_slots": turn.filled_slots,
            "missing_slots_after_turn": list(turn.missing_slots),
        }
        for turn in session.turns
    ]
    return f"""
You are generating final feedback for a beginner English learner.

Scenario: {session.scenario.title}
Scenario result: {session.result}
Required slots: {list(session.scenario.required_slots)}
Final filled slots: {session.filled_slots}
Conversation JSON: {json.dumps(conversation, ensure_ascii=False)}

Feedback rules:
- Evaluate the whole conversation only after the session has ended.
- Return one final total_understood_score, not a score for each turn.
- For each user answer, show what a foreigner would likely understand and one better expression.
- Do not mention pronunciation or intonation because this demo may use text input.
- Korean fields must be concise and user-facing.

Return only one JSON object with these keys:
- total_understood_score: integer from 0 to 100
- summary: Korean summary of the whole conversation
- turn_feedback: array with one item per user answer

Each turn_feedback item must have these keys:
- user_said: exact user transcript
- ai_question: assistant question or result after that answer
- heard_as: Korean explanation that starts with "외국인에게는"
- better_expression: one better English expression
- reason: Korean reason for the better expression
"""


def parse_session_feedback(raw: str, session: SessionState) -> dict[str, Any]:
    try:
        payload = _load_first_json_object(raw)
    except ValueError:
        return build_rule_based_feedback(session)

    feedback = {
        "scenario_result": session.result,
        "total_understood_score": _clamp_score(
            payload.get("total_understood_score", _fallback_total_score(session))
        ),
        "summary": str(
            payload.get("summary")
            or "대화 전체를 기준으로 생성한 최종 피드백입니다."
        ),
        "turn_feedback": _normalize_turn_feedback(payload, session),
    }
    return feedback


def build_rule_based_feedback(session: SessionState) -> dict[str, Any]:
    return {
        "scenario_result": session.result,
        "total_understood_score": _fallback_total_score(session),
        "summary": "대화 전체를 기준으로 생성한 기본 최종 피드백입니다.",
        "turn_feedback": [
            {
                "user_said": turn.transcript,
                "ai_question": turn.assistant_message,
                "heard_as": "외국인에게는 사용자가 상황에 필요한 정보를 전달하려는 것으로 들려요.",
                "better_expression": _default_better_expression(session),
                "reason": "더 자연스럽고 완성된 문장으로 말하면 실제 상황에서 더 안정적으로 전달됩니다.",
            }
            for turn in session.turns
        ],
    }


def _normalize_turn_feedback(
    payload: dict[str, Any],
    session: SessionState,
) -> list[dict[str, str]]:
    raw_items = payload.get("turn_feedback")
    if not isinstance(raw_items, list):
        return build_rule_based_feedback(session)["turn_feedback"]

    normalized: list[dict[str, str]] = []
    for index, turn in enumerate(session.turns):
        raw_item = raw_items[index] if index < len(raw_items) else {}
        if not isinstance(raw_item, dict):
            raw_item = {}
        normalized.append(
            {
                "user_said": str(raw_item.get("user_said") or turn.transcript),
                "ai_question": str(
                    raw_item.get("ai_question") or turn.assistant_message
                ),
                "heard_as": str(
                    raw_item.get("heard_as")
                    or "외국인에게는 사용자가 상황에 필요한 정보를 전달하려는 것으로 들려요."
                ),
                "better_expression": str(
                    raw_item.get("better_expression")
                    or _default_better_expression(session)
                ),
                "reason": str(
                    raw_item.get("reason")
                    or "더 자연스럽고 완성된 문장으로 말하면 실제 상황에서 더 안정적으로 전달됩니다."
                ),
            }
        )
    return normalized


def _fallback_total_score(session: SessionState) -> int:
    if not session.turns:
        return 0
    if session.result == "success":
        return 80
    if session.result == "failure":
        return 55
    return 0


def _default_better_expression(session: SessionState) -> str:
    if session.scenario.id == "cafe_order":
        return "Can I get a small iced latte to go?"
    return "Could you help me with this?"


def _load_first_json_object(raw: str) -> dict[str, Any]:
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
        return 0
    return max(0, min(score, 100))
