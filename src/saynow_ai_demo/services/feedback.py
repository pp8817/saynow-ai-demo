import json
import re
from typing import Any

from saynow_ai_demo.domain.models import SessionState, Turn


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
- For each user answer, provide one better English expression and one Korean reason.
- Do not mention pronunciation or intonation because this demo may use text input.
- Korean fields must be concise and user-facing.
- Do not include heard_as. The server generates heard_as from filled slots.

Return only one JSON object with these keys:
- total_understood_score: integer from 0 to 100
- summary: Korean summary of the whole conversation
- turn_feedback: array with one item per user answer

Each turn_feedback item must have these keys:
- user_said: exact user transcript
- ai_question: assistant question or result after that answer
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
        "summary": _summary_for_session(session),
        "turn_feedback": _normalize_turn_feedback(payload, session),
    }
    return feedback


def build_rule_based_feedback(session: SessionState) -> dict[str, Any]:
    return {
        "scenario_result": session.result,
        "total_understood_score": _fallback_total_score(session),
        "summary": _summary_for_session(session),
        "turn_feedback": [
            {
                "user_said": turn.transcript,
                "ai_question": turn.assistant_message,
                "heard_as": _fallback_heard_as(turn),
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
                "heard_as": _normalize_heard_as(
                    raw_item.get("heard_as"),
                    turn,
                ),
                "better_expression": _better_expression_for_turn(turn, session),
                "reason": _reason_for_turn(turn),
            }
        )
    return normalized


def _normalize_heard_as(value: object, turn: Turn) -> str:
    if turn.filled_slots:
        return _fallback_heard_as(turn)
    text = str(value or "").strip()
    if not text or _is_awkward_heard_as(text):
        return _fallback_heard_as(turn)
    if text.startswith("외국인에게는"):
        text = "외국인은" + text.removeprefix("외국인에게는")
    if not text.startswith("외국인은"):
        return _fallback_heard_as(turn)
    return text


def _is_awkward_heard_as(text: str) -> bool:
    awkward_patterns = (
        '"',
        "“",
        "”",
        "라고 말",
        "라고 표현",
        "요청이 정확히 이해",
        "요청이 잘 이해",
    )
    return any(pattern in text for pattern in awkward_patterns)


def _fallback_heard_as(turn: Turn) -> str:
    slots = turn.filled_slots
    if not slots:
        return "외국인은 사용자가 필요한 정보를 말하려는 중이라고 이해할 가능성이 높아요."
    if "for_here_or_to_go" in slots:
        destination = _korean_order_destination(slots["for_here_or_to_go"])
        return f"외국인은 {destination}을 원한다는 뜻으로 이해할 가능성이 높아요."
    if "temperature" in slots and "drink" in slots:
        temperature = _korean_temperature(slots["temperature"])
        drink = _korean_drink(slots["drink"])
        return f"외국인은 {temperature} {drink}를 원한다는 뜻으로 이해할 가능성이 높아요."
    if "temperature" in slots:
        temperature = _korean_temperature(slots["temperature"])
        return f"외국인은 {temperature} 음료를 원한다는 뜻으로 이해할 가능성이 높아요."
    if "size" in slots:
        size = _korean_size(slots["size"])
        return f"외국인은 {size} 사이즈를 원한다는 뜻으로 이해할 가능성이 높아요."
    if "drink" in slots:
        drink = _korean_drink(slots["drink"])
        return f"외국인은 {drink}를 주문하려는 뜻으로 이해할 가능성이 높아요."
    return "외국인은 사용자가 상황에 필요한 정보를 전달하려는 뜻으로 이해할 가능성이 높아요."


def _korean_size(value: str) -> str:
    lower = value.lower()
    if "small" in lower:
        return "작은"
    if "medium" in lower:
        return "중간"
    if "large" in lower:
        return "큰"
    return value


def _korean_temperature(value: str) -> str:
    lower = value.lower()
    if "ice" in lower or "iced" in lower or "cold" in lower:
        return "차가운"
    if "hot" in lower or "warm" in lower:
        return "따뜻한"
    return value


def _korean_order_destination(value: str) -> str:
    lower = value.lower()
    if "to go" in lower or "take" in lower:
        return "포장"
    if "here" in lower:
        return "매장 이용"
    return value


def _korean_drink(value: str) -> str:
    lower = value.lower()
    if "latte" in lower:
        return "라떼"
    if "americano" in lower:
        return "아메리카노"
    if "coffee" in lower:
        return "커피"
    return value


def _fallback_total_score(session: SessionState) -> int:
    if not session.turns:
        return 0
    if session.result == "success":
        return 80
    if session.result == "failure":
        return 55
    return 0


def _summary_for_session(session: SessionState) -> str:
    if session.result == "success":
        return "대화 전체를 보면 필요한 정보가 전달되어 시나리오를 완료했어요."
    if session.result == "failure":
        return "대화 전체를 보면 일부 정보가 부족해서 시나리오를 완료하지 못했어요."
    return "세션이 끝나면 전체 대화를 기준으로 최종 피드백을 확인할 수 있어요."


def _better_expression_for_turn(turn: Turn, session: SessionState) -> str:
    slots = turn.filled_slots
    drink = _english_drink(slots.get("drink") or _drink_from_transcript(turn.transcript))
    size = _english_size(slots.get("size", ""))
    temperature = _english_temperature(slots.get("temperature", ""))

    if "for_here_or_to_go" in slots:
        destination = slots["for_here_or_to_go"].lower()
        if "to go" in destination or "take" in destination:
            return "To go, please."
        if "here" in destination:
            return "For here, please."

    if drink and size and temperature:
        return f"Can I get a {size} {temperature} {drink}, please?"
    if drink and size:
        return f"Can I get a {size} {drink}, please?"
    if drink and temperature:
        article = "an" if temperature == "iced" else "a"
        return f"Can I get {article} {temperature} {drink}, please?"
    if size:
        return f"A {size} one, please."
    if temperature:
        return f"{temperature.capitalize()}, please."
    if drink:
        return f"Can I get a {drink}, please?"

    return _default_better_expression(session)


def _reason_for_turn(turn: Turn) -> str:
    if turn.filled_slots:
        return "주문할 때는 완성된 문장으로 말하면 더 자연스럽게 들려요."
    return "더 자연스럽고 완성된 문장으로 말하면 실제 상황에서 더 안정적으로 전달됩니다."


def _default_better_expression(session: SessionState) -> str:
    if session.scenario.id == "cafe_order":
        return "Can I get a small iced latte to go?"
    return "Could you help me with this?"


def _english_size(value: str) -> str:
    lower = value.lower()
    if "small" in lower:
        return "small"
    if "medium" in lower:
        return "medium"
    if "large" in lower:
        return "large"
    return ""


def _english_temperature(value: str) -> str:
    lower = value.lower()
    if "ice" in lower or "iced" in lower or "cold" in lower:
        return "iced"
    if "hot" in lower or "warm" in lower:
        return "hot"
    return ""


def _english_drink(value: str) -> str:
    lower = value.lower()
    if "latte" in lower:
        return "latte"
    if "americano" in lower:
        return "americano"
    if "coffee" in lower:
        return "coffee"
    return ""


def _drink_from_transcript(transcript: str) -> str:
    return _english_drink(transcript)


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
