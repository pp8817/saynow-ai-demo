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
                    understood_score=82,
                    interpreted_as="The user wants a small iced latte.",
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
                    understood_score=88,
                    interpreted_as="The user completed the order.",
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
