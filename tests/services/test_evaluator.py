from saynow_ai_demo.services.evaluator import (
    TurnEvaluation,
    build_turn_prompt,
    parse_turn_evaluation,
)


def test_parse_turn_evaluation_extracts_json_object():
    raw = """
    Here is the result:
    {
      "filled_slots": {
        "drink": "iced latte",
        "temperature": "iced",
        "size": "small"
      },
      "follow_up_question": "Is that for here or to go?"
    }
    """

    result = parse_turn_evaluation(raw)

    assert result == TurnEvaluation(
        filled_slots={
            "drink": "iced latte",
            "temperature": "iced",
            "size": "small",
        },
        follow_up_question="Is that for here or to go?",
    )


def test_parse_turn_evaluation_returns_safe_fallback_for_invalid_json():
    result = parse_turn_evaluation("not json")

    assert result.filled_slots == {}
    assert result.follow_up_question == "Could you say that again more clearly?"


def test_build_turn_prompt_contains_scenario_and_transcript():
    prompt = build_turn_prompt(
        scenario_title="카페에서 주문하기",
        required_slots=("drink", "size"),
        current_slots={"drink": "iced latte"},
        transcript="small size please",
    )

    assert "카페에서 주문하기" in prompt
    assert "drink" in prompt
    assert "small size please" in prompt
    assert "JSON" in prompt


def test_build_turn_prompt_only_requests_slot_tracking_result():
    prompt = build_turn_prompt(
        scenario_title="카페에서 주문하기",
        required_slots=("drink", "temperature", "size"),
        current_slots={},
        transcript="I want latte",
    )

    assert "I want latte" in prompt
    assert "filled_slots" in prompt
    assert "follow_up_question" in prompt
    assert "understood_score" not in prompt
    assert "interpreted_as" not in prompt
