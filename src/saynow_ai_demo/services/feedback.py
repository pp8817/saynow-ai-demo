from typing import Any

from saynow_ai_demo.domain.models import SessionState


def build_fallback_feedback(session: SessionState) -> dict[str, Any]:
    scores = [turn.understood_score for turn in session.turns]
    total_score = round(sum(scores) / len(scores)) if scores else 0
    return {
        "scenario_result": session.result,
        "total_understood_score": total_score,
        "summary": "세션의 발화 기록을 바탕으로 생성한 기본 피드백입니다.",
        "turn_feedback": [
            {
                "user_said": turn.transcript,
                "understood_score": turn.understood_score,
                "interpreted_as": turn.interpreted_as,
                "better_expression": "Can I get a small iced latte?",
                "reason": "더 자연스러운 표현 예시입니다.",
            }
            for turn in session.turns
        ],
    }
