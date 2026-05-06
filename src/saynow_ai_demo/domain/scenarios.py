from saynow_ai_demo.domain.models import Scenario


CAFE_ORDER = Scenario(
    id="cafe_order",
    title="카페에서 주문하기",
    opening_question="Hi! What would you like to order?",
    max_turns=4,
    required_slots=("drink", "size", "temperature", "for_here_or_to_go"),
    optional_slots=("option",),
)

SCENARIOS: dict[str, Scenario] = {
    CAFE_ORDER.id: CAFE_ORDER,
}


def get_scenario(scenario_id: str) -> Scenario:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise KeyError(f"unknown scenario: {scenario_id}") from exc
