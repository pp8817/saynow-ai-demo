import json
import re
from typing import Any

from saynow_ai_demo.domain.models import SessionState, Turn
from saynow_ai_demo.domain.state_tracker import extract_slots_from_transcript


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
        "total_understood_score": _total_understood_score(session),
        "summary": _summary_for_session(session),
        "turn_feedback": _normalize_turn_feedback(payload, session),
    }
    return feedback


def build_rule_based_feedback(session: SessionState) -> dict[str, Any]:
    return {
        "scenario_result": session.result,
        "total_understood_score": _total_understood_score(session),
        "summary": _summary_for_session(session),
        "turn_feedback": [_feedback_for_turn(turn, session) for turn in session.turns],
    }


def _feedback_for_turn(turn: Turn, session: SessionState) -> dict[str, object]:
    understood_score = _turn_understood_score(turn)
    score_delta = _score_delta_for_turn(turn)
    return {
        "user_said": turn.transcript,
        "ai_question": turn.assistant_message,
        "heard_as": _fallback_heard_as(turn),
        "understood_score": understood_score,
        "better_expression": _better_expression_for_turn(turn, session),
        "score_delta": score_delta,
        "improved_understood_score": min(98, understood_score + score_delta),
        "reason": _reason_for_turn(turn),
    }


def _normalize_turn_feedback(
    payload: dict[str, Any],
    session: SessionState,
) -> list[dict[str, object]]:
    raw_items = payload.get("turn_feedback")
    if not isinstance(raw_items, list):
        return build_rule_based_feedback(session)["turn_feedback"]

    normalized: list[dict[str, object]] = []
    for index, turn in enumerate(session.turns):
        raw_item = raw_items[index] if index < len(raw_items) else {}
        if not isinstance(raw_item, dict):
            raw_item = {}
        understood_score = _turn_understood_score(turn)
        score_delta = _score_delta_for_turn(turn)
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
                "understood_score": understood_score,
                "better_expression": _better_expression_for_turn(turn, session),
                "score_delta": score_delta,
                "improved_understood_score": min(98, understood_score + score_delta),
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
    if not slots and _is_missed_follow_up_answer(turn):
        expected_label = _korean_slot_label(turn.missing_slots[0])
        return (
            f"AI는 {expected_label}를 물었지만, 사용자는 다른 정보를 먼저 말한 "
            "것으로 보여요."
        )
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


def _total_understood_score(session: SessionState) -> int:
    if not session.turns:
        return 0
    average_turn_score = round(
        sum(_turn_understood_score(turn) for turn in session.turns) / len(session.turns)
    )
    if session.result == "success":
        return min(95, average_turn_score + 12)
    if session.result == "failure":
        return max(35, average_turn_score - 5)
    return average_turn_score


def _turn_understood_score(turn: Turn) -> int:
    if not turn.transcript.strip():
        return 35

    score = 45 + (len(turn.filled_slots) * 15)
    text = turn.transcript.lower().strip()
    if _looks_like_complete_sentence(text):
        score += 10
    if _has_common_transcription_issue(text):
        score -= 10
    if not turn.filled_slots:
        score -= 20
    return max(35, min(score, 95))


def _looks_like_complete_sentence(text: str) -> bool:
    starters = ("i want ", "i'd like ", "i would like ", "can i get ", "could i get ")
    return text.startswith(starters)


def _has_common_transcription_issue(text: str) -> bool:
    issue_patterns = (" lce ", " ice latte", " im ", " i'm to go")
    padded = f" {text} "
    return any(pattern in padded for pattern in issue_patterns)


def _score_delta_for_turn(turn: Turn) -> int:
    text = turn.transcript.lower().strip()
    if not turn.filled_slots:
        return 15
    if text in {"here", "to go", "iced", "hot"}:
        return 3
    if text in {"small", "medium", "large", "small size", "medium size", "large size"}:
        return 10
    if "ice latte" in text or "lce latte" in text:
        return 12
    return 8


def _summary_for_session(session: SessionState) -> str:
    if session.result == "success":
        return "대화 전체를 보면 필요한 정보가 전달되어 시나리오를 완료했어요."
    if session.result == "failure":
        return "대화 전체를 보면 일부 정보가 부족해서 시나리오를 완료하지 못했어요."
    return "세션이 끝나면 전체 대화를 기준으로 최종 피드백을 확인할 수 있어요."


def _better_expression_for_turn(turn: Turn, session: SessionState) -> str:
    lowered = turn.transcript.strip().lower()
    slots = turn.filled_slots
    drink = _english_drink(slots.get("drink") or _drink_from_transcript(turn.transcript))
    size = _english_size(slots.get("size", ""))
    temperature = _english_temperature(slots.get("temperature", ""))

    if not slots and _is_missed_follow_up_answer(turn):
        return _example_answer_for_slot(turn.missing_slots[0])

    if "for_here_or_to_go" in slots:
        destination = slots["for_here_or_to_go"].lower()
        if "to go" in destination or "take" in destination:
            return "To go, please."
        if "here" in destination:
            return "For here, please."

    if size and not drink and not temperature:
        return f"{size.capitalize()}, please."
    if temperature and not drink and not size:
        return f"{temperature.capitalize()}, please."
    if drink and ("ice latte" in lowered or "lce latte" in lowered):
        return f"I want an iced {drink}."
    if drink and size and temperature and lowered.startswith("i want "):
        return _plus_one_full_drink_order(
            lowered=lowered,
            size=size,
            temperature=temperature,
            drink=drink,
        )
    if drink and size and lowered.startswith("i want "):
        return f"I want a {size} {drink}."
    if drink and temperature and lowered.startswith("i want "):
        article = "an" if temperature == "iced" else "a"
        return f"I want {article} {temperature} {drink}."
    if drink and lowered.startswith("i want "):
        return f"I want a {drink}."
    if drink and size and temperature:
        return f"A {size} {temperature} {drink}, please."
    if drink and size:
        return f"A {size} {drink}, please."
    if drink and temperature:
        article = "An" if temperature == "iced" else "A"
        return f"{article} {temperature} {drink}, please."
    if drink:
        return f"A {drink}, please."

    return _default_better_expression(session)


def _reason_for_turn(turn: Turn) -> str:
    text = turn.transcript.lower().strip()
    slots = turn.filled_slots
    if not slots and _is_missed_follow_up_answer(turn):
        expected_label = _korean_slot_label(turn.missing_slots[0])
        expected_answer = _example_answer_for_slot(turn.missing_slots[0])
        return (
            f"현재 질문에는 {expected_label}를 먼저 답해야 해서, 짧게 "
            f"'{expected_answer}'라고 말하는 편이 더 정확해요."
        )
    if "ice latte" in text or "lce latte" in text:
        return (
            "지금 문장에서 크게 바꾸지 않고, 'ice latte'만 자연스러운 "
            "'iced latte'로 고쳤어요."
        )
    if "for_here_or_to_go" in slots:
        return "짧게 답해도 통하지만, 'please'를 붙이면 더 자연스럽게 들려요."
    if text in {"small", "medium", "large", "small size", "medium size", "large size"}:
        return "단어만 말해도 통하지만, 'please'를 붙이면 더 부드럽게 들려요."
    if slots:
        return "기존 표현은 유지하고, 관사나 어순만 조금 더 자연스럽게 다듬었어요."
    return "뜻이 더 잘 전달되도록 최소한의 표현만 보완했어요."


def _default_better_expression(session: SessionState) -> str:
    if session.scenario.id == "cafe_order":
        return "Can I get a small iced latte to go?"
    return "Could you help me with this?"


def _plus_one_full_drink_order(
    *,
    lowered: str,
    size: str,
    temperature: str,
    drink: str,
) -> str:
    order_phrase = f"{size} {temperature} {drink}"
    article = "an" if order_phrase[0] in "aeiou" else "a"
    complete_order = f"I want {article} {order_phrase}"
    if complete_order.lower() in lowered and "please" not in lowered:
        return f"{complete_order}, please."
    return f"{complete_order}."


def _is_missed_follow_up_answer(turn: Turn) -> bool:
    if not turn.transcript.strip() or turn.filled_slots or not turn.missing_slots:
        return False
    expected_slot = turn.missing_slots[0]
    if not _example_answer_for_slot(expected_slot):
        return False
    transcript_slots = extract_slots_from_transcript(turn.transcript)
    return bool(transcript_slots and expected_slot not in transcript_slots)


def _example_answer_for_slot(slot: str) -> str:
    examples = {
        "drink": "A latte, please.",
        "size": "Small, please.",
        "temperature": "Iced, please.",
        "for_here_or_to_go": "For here, please.",
    }
    return examples.get(slot, "")


def _korean_slot_label(slot: str) -> str:
    labels = {
        "drink": "음료",
        "size": "사이즈",
        "temperature": "온도",
        "for_here_or_to_go": "매장/포장 여부",
    }
    return labels.get(slot, "필요한 정보")


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
