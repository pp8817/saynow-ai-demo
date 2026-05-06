from saynow_ai_demo.domain.models import SessionState, Turn
from saynow_ai_demo.domain.scenarios import get_scenario
from saynow_ai_demo.services.feedback import (
    build_rule_based_feedback,
    parse_session_feedback,
)


def test_build_rule_based_feedback_summarizes_conversation_after_session_ends():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want ice latte small size",
            filled_slots={"drink": "iced latte"},
            missing_slots=("for_here_or_to_go",),
            assistant_message="Is that for here or to go?",
        )
    )

    feedback = build_rule_based_feedback(session)

    assert feedback["scenario_result"] == "success"
    assert feedback["total_understood_score"] == 80
    assert feedback["turn_feedback"][0]["user_said"] == "I want ice latte small size"
    assert "understood_score" not in feedback["turn_feedback"][0]
    assert feedback["turn_feedback"][0]["ai_question"] == "Is that for here or to go?"


def test_parse_session_feedback_returns_total_score_and_turn_feedback():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want latte",
            filled_slots={"drink": "latte"},
            missing_slots=("size", "temperature"),
            assistant_message="Would you like it hot or cold?",
        )
    )
    raw = """
    {
      "total_understood_score": 76,
      "summary": "주문 의도는 전달됐지만 정보가 부족했습니다.",
      "turn_feedback": [
        {
          "user_said": "I want latte",
          "ai_question": "Would you like it hot or cold?",
          "heard_as": "외국인에게는 라떼를 원한다는 뜻으로 들려요.",
          "better_expression": "Can I get a latte?",
          "reason": "주문 상황에서는 Can I get이 더 자연스럽습니다."
        }
      ]
    }
    """

    feedback = parse_session_feedback(raw, session)

    assert feedback["scenario_result"] == "success"
    assert feedback["total_understood_score"] == 76
    assert feedback["turn_feedback"][0]["heard_as"].startswith("외국인에게는")
    assert "understood_score" not in feedback["turn_feedback"][0]
