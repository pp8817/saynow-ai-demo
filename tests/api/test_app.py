from fastapi.testclient import TestClient

from saynow_ai_demo.api.app import create_app
from saynow_ai_demo.services.evaluator import TurnEvaluation


class FakeEvaluator:
    def evaluate(self, *, scenario, current_slots, transcript):
        return TurnEvaluation(
            understood_score=80,
            interpreted_as="The user wants a small iced latte.",
            filled_slots={
                "drink": "iced latte",
                "temperature": "iced",
                "size": "small",
            },
            follow_up_question="Is that for here or to go?",
        )


class FakeSTTAdapter:
    def transcribe(self, audio_path):
        assert audio_path.exists()
        return "I want ice latte small size"


def test_start_session_api_returns_opening_question():
    client = TestClient(create_app(evaluator=FakeEvaluator()))

    response = client.post("/api/sessions", json={"scenario_id": "cafe_order"})

    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "cafe_order"
    assert body["assistant_message"] == "Hi! What would you like to order?"
    assert body["remaining_turns"] == 4


def test_submit_text_turn_api_returns_follow_up():
    client = TestClient(create_app(evaluator=FakeEvaluator()))
    session_id = client.post(
        "/api/sessions", json={"scenario_id": "cafe_order"}
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/turns/text",
        json={"transcript": "I want ice latte small size"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["understood_score"] == 80
    assert body["missing_slots"] == ["for_here_or_to_go"]
    assert body["assistant_message"] == "Is that for here or to go?"


def test_feedback_api_returns_fallback_feedback():
    client = TestClient(create_app(evaluator=FakeEvaluator()))
    session_id = client.post(
        "/api/sessions", json={"scenario_id": "cafe_order"}
    ).json()["session_id"]
    client.post(
        f"/api/sessions/{session_id}/turns/text",
        json={"transcript": "I want ice latte small size"},
    )

    response = client.get(f"/api/sessions/{session_id}/feedback")

    assert response.status_code == 200
    assert response.json()["turn_feedback"][0]["user_said"] == (
        "I want ice latte small size"
    )


def test_submit_audio_turn_api_uses_stt_adapter():
    client = TestClient(
        create_app(evaluator=FakeEvaluator(), stt_adapter=FakeSTTAdapter())
    )
    session_id = client.post(
        "/api/sessions", json={"scenario_id": "cafe_order"}
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/turns/audio",
        files={"audio": ("sample.webm", b"fake audio bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "I want ice latte small size"
    assert body["assistant_message"] == "Is that for here or to go?"
