from fastapi.testclient import TestClient

from saynow_ai_demo.adapters.llm import OllamaEvaluator
from saynow_ai_demo.api.app import create_app
from saynow_ai_demo.services.evaluator import TurnEvaluation


class FakeEvaluator:
    def evaluate(self, *, scenario, current_slots, transcript):
        return TurnEvaluation(
            filled_slots={
                "drink": "iced latte",
                "temperature": "iced",
                "size": "small",
            },
            follow_up_question="Is that for here or to go?",
        )


class CompleteFakeEvaluator:
    def evaluate(self, *, scenario, current_slots, transcript):
        return TurnEvaluation(
            filled_slots={
                "drink": "iced latte",
                "temperature": "iced",
                "size": "small",
                "for_here_or_to_go": "to go",
            },
            follow_up_question="",
        )


class FakeSTTAdapter:
    def transcribe(self, audio_path):
        assert audio_path.exists()
        return "I want ice latte small size"


class FailingLLMClient:
    def complete(self, prompt: str) -> str:
        raise ConnectionError("ollama is not running")


class FakeFeedbackGenerator:
    def generate_feedback(self, session):
        return {
            "scenario_result": session.result,
            "total_understood_score": 84,
            "summary": "주문 의도와 핵심 정보가 전달됐습니다.",
            "turn_feedback": [
                {
                    "user_said": turn.transcript,
                    "ai_question": turn.assistant_message,
                    "heard_as": "외국인은 작은 아이스 라떼 주문으로 이해할 가능성이 높아요.",
                    "better_expression": "Can I get a small iced latte?",
                    "reason": "카페에서는 Can I get이 더 자연스럽습니다.",
                }
                for turn in session.turns
            ],
        }


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
    assert "understood_score" not in body
    assert "interpreted_as" not in body
    assert body["missing_slots"] == ["for_here_or_to_go"]
    assert body["assistant_message"] == "Is that for here or to go?"


def test_feedback_api_returns_final_feedback_after_session_ends():
    client = TestClient(create_app(evaluator=CompleteFakeEvaluator()))
    session_id = client.post(
        "/api/sessions", json={"scenario_id": "cafe_order"}
    ).json()["session_id"]
    client.post(
        f"/api/sessions/{session_id}/turns/text",
        json={"transcript": "I want ice latte small size"},
    )

    response = client.get(f"/api/sessions/{session_id}/feedback")

    assert response.status_code == 200
    body = response.json()
    assert body["total_understood_score"] == 80
    assert body["turn_feedback"][0]["user_said"] == "I want ice latte small size"
    assert body["turn_feedback"][0]["heard_as"].startswith("외국인은")
    assert body["turn_feedback"][0]["understood_score"] == 95
    assert body["turn_feedback"][0]["score_delta"] == 12
    assert body["turn_feedback"][0]["improved_understood_score"] == 98


def test_feedback_api_rejects_in_progress_session():
    client = TestClient(
        create_app(
            evaluator=FakeEvaluator(),
            feedback_generator=FakeFeedbackGenerator(),
        )
    )
    session_id = client.post(
        "/api/sessions", json={"scenario_id": "cafe_order"}
    ).json()["session_id"]

    response = client.get(f"/api/sessions/{session_id}/feedback")

    assert response.status_code == 400
    assert response.json()["detail"] == "세션 종료 후 최종 피드백을 확인할 수 있습니다."


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
    assert "understood_score" not in body
    assert body["assistant_message"] == "Is that for here or to go?"


def test_index_serves_demo_page():
    client = TestClient(create_app(evaluator=FakeEvaluator()))

    response = client.get("/")

    assert response.status_code == 200
    assert "Say Now AI Demo" in response.text
    assert "startSession" in response.text
    assert "상황 진행" not in response.text
    assert "missionStrip" in response.text
    assert "renderMissionProgress" in response.text
    assert "slotChip" in response.text
    assert "voicePanel" in response.text
    assert "waveform" in response.text
    assert "scenarioPreview" in response.text
    assert "feedbackScoreBand" in response.text
    assert "scoreMeter" in response.text
    assert "부족한 정보:" not in response.text
    assert "white-space: pre-line" in response.text
    assert "이해도 ${body.understood_score}" not in response.text
    assert "대화별 피드백" in response.text
    assert "외국인 이해도" in response.text
    assert "+1 표현" in response.text
    assert "numberOrZero" in response.text
    assert "recordingStatus" in response.text
    assert "녹음 중" in response.text
    assert "recordingTimer" in response.text
    assert "피드백 생성 중" in response.text
    assert "loadFeedback({ auto: true })" in response.text
    assert "setFeedbackLoading" in response.text


def test_text_turn_returns_warning_when_ollama_is_unavailable():
    client = TestClient(
        create_app(evaluator=OllamaEvaluator(llm_client=FailingLLMClient()))
    )
    session_id = client.post(
        "/api/sessions", json={"scenario_id": "cafe_order"}
    ).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/turns/text",
        json={"transcript": "I want ice latte small size"},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == (
        "Ollama가 실행 중이 아니어서 AI 평가를 진행할 수 없습니다. "
        "`ollama serve` 실행 후 다시 시도하세요."
    )
