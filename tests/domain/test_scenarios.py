from saynow_ai_demo.domain.scenarios import get_scenario


def test_cafe_order_scenario_defines_required_slots():
    scenario = get_scenario("cafe_order")

    assert scenario.id == "cafe_order"
    assert scenario.title == "카페에서 주문하기"
    assert scenario.max_turns == 4
    assert scenario.opening_question == "Hi! What would you like to order?"
    assert scenario.required_slots == (
        "drink",
        "size",
        "temperature",
        "for_here_or_to_go",
    )
    assert scenario.optional_slots == ("option",)


def test_get_scenario_rejects_unknown_id():
    try:
        get_scenario("unknown")
    except KeyError as exc:
        assert "unknown scenario: unknown" in str(exc)
    else:
        raise AssertionError("unknown scenario should raise KeyError")
