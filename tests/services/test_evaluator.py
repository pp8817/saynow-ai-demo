from saynow_ai_demo.services.evaluator import (
    TurnEvaluation,
    build_turn_prompt,
    parse_turn_evaluation,
)


def test_parse_turn_evaluation_extracts_json_object():
    raw = """
    Here is the result:
    {
      "understood_score": 82,
      "interpreted_as": "The user wants a small iced latte.",
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
        understood_score=82,
        interpreted_as="The user wants a small iced latte.",
        filled_slots={
            "drink": "iced latte",
            "temperature": "iced",
            "size": "small",
        },
        follow_up_question="Is that for here or to go?",
    )


def test_parse_turn_evaluation_returns_safe_fallback_for_invalid_json():
    result = parse_turn_evaluation("not json")

    assert result.understood_score == 30
    assert result.interpreted_as == "AI가 발화 의미를 안정적으로 해석하지 못했습니다."
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


def test_build_turn_prompt_calibrates_beginner_expression_scores():
    prompt = build_turn_prompt(
        scenario_title="카페에서 주문하기",
        required_slots=("drink", "temperature", "size"),
        current_slots={},
        transcript="I want latte",
    )

    assert "I want latte" in prompt
    assert "Score calibration" in prompt
    assert "78" in prompt
    assert "Scenario completion is separate from understood_score" in prompt
    assert "interpreted_as must be Korean" in prompt
