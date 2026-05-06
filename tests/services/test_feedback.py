from saynow_ai_demo.domain.models import SessionState, Turn
from saynow_ai_demo.domain.scenarios import get_scenario
from saynow_ai_demo.services.feedback import build_fallback_feedback


def test_build_fallback_feedback_summarizes_turns():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want ice latte small size",
            understood_score=82,
            interpreted_as="Small iced latte.",
            filled_slots={"drink": "iced latte"},
            missing_slots=("for_here_or_to_go",),
            assistant_message="Is that for here or to go?",
        )
    )

    feedback = build_fallback_feedback(session)

    assert feedback["scenario_result"] == "success"
    assert feedback["total_understood_score"] == 82
    assert feedback["turn_feedback"][0]["user_said"] == "I want ice latte small size"
