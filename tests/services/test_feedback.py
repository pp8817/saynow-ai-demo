from saynow_ai_demo.domain.models import SessionState, Turn
from saynow_ai_demo.domain.scenarios import get_scenario
from saynow_ai_demo.services.feedback import (
    build_feedback_prompt,
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
    assert feedback["turn_feedback"][0]["understood_score"] == 60
    assert feedback["turn_feedback"][0]["score_delta"] == 12
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
    assert feedback["turn_feedback"][0]["heard_as"].startswith("외국인은")
    assert feedback["turn_feedback"][0]["understood_score"] == 70
    assert feedback["turn_feedback"][0]["score_delta"] == 8


def test_build_feedback_prompt_does_not_request_heard_as_from_llm():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="small please",
            filled_slots={"size": "small"},
            missing_slots=("temperature", "for_here_or_to_go"),
            assistant_message="Would you like your latte hot or cold?",
        )
    )

    prompt = build_feedback_prompt(session)

    assert "Do not include heard_as" in prompt
    assert "The server generates heard_as from filled slots" in prompt
    assert "heard_as:" not in prompt


def test_parse_session_feedback_replaces_literal_translation_heard_as():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="small please",
            filled_slots={"size": "small"},
            missing_slots=("temperature", "for_here_or_to_go"),
            assistant_message="Would you like your latte hot or cold?",
        )
    )
    raw = """
    {
      "total_understood_score": 72,
      "summary": "주문은 이어졌습니다.",
      "turn_feedback": [
        {
          "user_said": "small please",
          "ai_question": "Would you like your latte hot or cold?",
          "heard_as": "외국인에게는 \\"소마일라떼를 주세요\\"라고 말했으며, 크기에 대한 요청이 잘 이해되었습니다.",
          "better_expression": "A small one, please.",
          "reason": "주문 맥락에서 더 자연스럽습니다."
        }
      ]
    }
    """

    feedback = parse_session_feedback(raw, session)
    heard_as = feedback["turn_feedback"][0]["heard_as"]

    assert heard_as == "외국인은 작은 사이즈를 원한다는 뜻으로 이해할 가능성이 높아요."
    assert "라고 말했" not in heard_as
    assert '"' not in heard_as


def test_parse_session_feedback_prefers_slot_based_heard_as():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want latte",
            filled_slots={"drink": "latte"},
            missing_slots=("size", "temperature", "for_here_or_to_go"),
            assistant_message="Would you like a small, medium, or large latte?",
        )
    )
    raw = """
    {
      "total_understood_score": 80,
      "summary": "주문이 진행되었습니다.",
      "turn_feedback": [
        {
          "user_said": "I want latte",
          "ai_question": "Would you like a small, medium, or large latte?",
          "heard_as": "외국인은 라떼를 원한다는 뜻으로 작은 사이즈를 요청할 가능성이 높아요.",
          "better_expression": "Can I get a latte?",
          "reason": "더 자연스러운 주문 표현입니다."
        }
      ]
    }
    """

    feedback = parse_session_feedback(raw, session)

    assert feedback["turn_feedback"][0]["heard_as"] == (
        "외국인은 라떼를 주문하려는 뜻으로 이해할 가능성이 높아요."
    )


def test_parse_session_feedback_uses_natural_rule_based_summary():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I'm to go",
            filled_slots={"for_here_or_to_go": "to go"},
            missing_slots=(),
            assistant_message="Scenario cleared.",
        )
    )
    raw = """
    {
      "total_understood_score": 95,
      "summary": "토탈 이해 점수는 95점이며, 갈 거라 답했습니다.",
      "turn_feedback": []
    }
    """

    feedback = parse_session_feedback(raw, session)

    assert feedback["summary"] == (
        "대화 전체를 보면 필요한 정보가 전달되어 시나리오를 완료했어요."
    )


def test_parse_session_feedback_prefers_slot_based_better_expression():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want small latte",
            filled_slots={"size": "small"},
            missing_slots=("for_here_or_to_go",),
            assistant_message="Is that for here or to go?",
        )
    )
    raw = """
    {
      "total_understood_score": 95,
      "summary": "대화가 완료되었습니다.",
      "turn_feedback": [
        {
          "user_said": "I want small latte",
          "ai_question": "Is that for here or to go?",
          "better_expression": "Do you want it to go or here?",
          "reason": "이 질문은 고객에게 더 명확합니다."
        }
      ]
    }
    """

    feedback = parse_session_feedback(raw, session)
    turn_feedback = feedback["turn_feedback"][0]

    assert turn_feedback["better_expression"] == "I want a small latte."
    assert turn_feedback["reason"] == (
        "기존 표현은 유지하고, 관사나 어순만 조금 더 자연스럽게 다듬었어요."
    )


def test_rule_based_feedback_includes_turn_score_and_score_lift():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want ice latte",
            filled_slots={"drink": "latte", "temperature": "iced"},
            missing_slots=("size", "for_here_or_to_go"),
            assistant_message="What size would you like?",
        )
    )

    feedback = build_rule_based_feedback(session)
    turn_feedback = feedback["turn_feedback"][0]

    assert turn_feedback["understood_score"] == 75
    assert turn_feedback["score_delta"] == 12
    assert turn_feedback["improved_understood_score"] == 87


def test_feedback_uses_plus_one_expression_instead_of_perfect_sentence():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want ice latte",
            filled_slots={"drink": "latte", "temperature": "iced"},
            missing_slots=("size", "for_here_or_to_go"),
            assistant_message="What size would you like?",
        )
    )

    feedback = build_rule_based_feedback(session)
    turn_feedback = feedback["turn_feedback"][0]

    assert turn_feedback["better_expression"] == "I want an iced latte."
    assert turn_feedback["better_expression"] != "Can I get an iced latte, please?"
    assert turn_feedback["reason"] == (
        "지금 문장에서 크게 바꾸지 않고, 'ice latte'만 자연스러운 "
        "'iced latte'로 고쳤어요."
    )


def test_feedback_keeps_short_answers_as_small_plus_one_changes():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.extend(
        [
            Turn(
                id="turn-1",
                transcript="small size",
                filled_slots={"size": "small"},
                missing_slots=("temperature", "for_here_or_to_go"),
                assistant_message="Would you like it hot or iced?",
            ),
            Turn(
                id="turn-2",
                transcript="here",
                filled_slots={"for_here_or_to_go": "for here"},
                missing_slots=(),
                assistant_message="Scenario cleared.",
            ),
        ]
    )

    feedback = build_rule_based_feedback(session)

    assert feedback["turn_feedback"][0]["better_expression"] == "Small, please."
    assert feedback["turn_feedback"][1]["better_expression"] == "For here, please."
    assert feedback["turn_feedback"][0]["score_delta"] == 10
    assert feedback["turn_feedback"][1]["score_delta"] == 3
