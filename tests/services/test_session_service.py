from saynow_ai_demo.services.evaluator import TurnEvaluation
from saynow_ai_demo.services.session_service import SessionService


class FakeEvaluator:
    def __init__(self, evaluations):
        self.evaluations = list(evaluations)

    def evaluate(self, *, scenario, current_slots, transcript):
        return self.evaluations.pop(0)


def test_start_session_returns_opening_question():
    service = SessionService(evaluator=FakeEvaluator([]))

    session = service.start_session("cafe_order")

    assert session.scenario.id == "cafe_order"
    assert session.remaining_turns == 4
    assert session.result == "in_progress"


def test_submit_transcript_updates_slots_and_asks_follow_up():
    service = SessionService(
        evaluator=FakeEvaluator(
            [
                TurnEvaluation(
                    filled_slots={
                        "drink": "iced latte",
                        "temperature": "iced",
                        "size": "small",
                    },
                    follow_up_question="Is that for here or to go?",
                )
            ]
        )
    )
    session = service.start_session("cafe_order")

    turn = service.submit_transcript(session.id, "I want ice latte small size")

    assert turn.assistant_message == "Is that for here or to go?"
    assert turn.missing_slots == ("for_here_or_to_go",)
    assert service.get_session(session.id).result == "in_progress"


def test_submit_transcript_marks_success_when_required_slots_are_complete():
    service = SessionService(
        evaluator=FakeEvaluator(
            [
                TurnEvaluation(
                    filled_slots={
                        "drink": "iced latte",
                        "temperature": "iced",
                        "size": "small",
                        "for_here_or_to_go": "to go",
                    },
                    follow_up_question="",
                )
            ]
        )
    )
    session = service.start_session("cafe_order")

    turn = service.submit_transcript(session.id, "Small iced latte to go")

    assert turn.assistant_message == "Scenario cleared."
    assert turn.missing_slots == ()
    assert service.get_session(session.id).result == "success"


def test_submit_transcript_uses_transcript_slots_and_missing_slot_questions():
    service = SessionService(
        evaluator=FakeEvaluator(
            [
                TurnEvaluation(
                    filled_slots={"drink": "latte"},
                    follow_up_question="What size would you like?",
                ),
                TurnEvaluation(
                    filled_slots={},
                    follow_up_question="Would you like your latte iced or hot?",
                ),
                TurnEvaluation(
                    filled_slots={},
                    follow_up_question="Could you say that again?",
                ),
            ]
        )
    )
    session = service.start_session("cafe_order")

    first_turn = service.submit_transcript(session.id, "I want ice latte")
    second_turn = service.submit_transcript(session.id, "I want small latte")
    final_turn = service.submit_transcript(session.id, "here")

    assert first_turn.filled_slots == {
        "drink": "latte",
        "temperature": "iced",
    }
    assert first_turn.missing_slots == ("size", "for_here_or_to_go")
    assert second_turn.filled_slots == {"size": "small"}
    assert second_turn.assistant_message == "Is that for here or to go?"
    assert final_turn.filled_slots == {"for_here_or_to_go": "for here"}
    assert final_turn.assistant_message == "Scenario cleared."
    assert service.get_session(session.id).result == "success"
