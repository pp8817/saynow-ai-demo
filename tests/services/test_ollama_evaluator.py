import pytest

from saynow_ai_demo.domain.models import SessionState, Turn
from saynow_ai_demo.adapters.llm import LocalLLMUnavailableError, OllamaEvaluator
from saynow_ai_demo.domain.scenarios import get_scenario


class FakeLLMClient:
    def complete(self, prompt: str) -> str:
        assert "카페에서 주문하기" in prompt
        return """
        {
          "filled_slots": {
            "drink": "coffee",
            "for_here_or_to_go": "to go"
          },
          "follow_up_question": "What size would you like?"
        }
        """


class FailingLLMClient:
    def complete(self, prompt: str) -> str:
        raise ConnectionError("ollama is not running")


class FakeFeedbackLLMClient:
    def complete(self, prompt: str) -> str:
        assert "Evaluate the whole conversation only after the session has ended" in prompt
        assert "I want latte" in prompt
        return """
        {
          "total_understood_score": 76,
          "summary": "주문 의도는 전달됐지만 정보가 부족했습니다.",
          "turn_feedback": [
            {
              "user_said": "I want latte",
              "ai_question": "Would you like it hot or cold?",
              "better_expression": "Can I get a latte?",
              "reason": "주문 상황에서는 Can I get이 더 자연스럽습니다."
            }
          ]
        }
        """


def test_ollama_evaluator_uses_llm_client_and_parses_result():
    evaluator = OllamaEvaluator(llm_client=FakeLLMClient())

    result = evaluator.evaluate(
        scenario=get_scenario("cafe_order"),
        current_slots={},
        transcript="coffee to go",
    )

    assert result.filled_slots == {
        "drink": "coffee",
        "for_here_or_to_go": "to go",
    }
    assert result.follow_up_question == "What size would you like?"


def test_ollama_evaluator_raises_warning_error_when_local_llm_is_unavailable():
    evaluator = OllamaEvaluator(llm_client=FailingLLMClient())

    with pytest.raises(LocalLLMUnavailableError) as exc_info:
        evaluator.evaluate(
            scenario=get_scenario("cafe_order"),
            current_slots={},
            transcript="I want ice latte small size",
        )

    assert "Ollama가 실행 중이 아니어서 AI 평가를 진행할 수 없습니다." in str(
        exc_info.value
    )


def test_ollama_evaluator_generates_final_session_feedback():
    scenario = get_scenario("cafe_order")
    session = SessionState(id="s1", scenario=scenario, result="success")
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want latte",
            filled_slots={"drink": "latte"},
            missing_slots=("size", "temperature"),
            assistant_message="Would you like it hot or cold?",
        )
    )
    evaluator = OllamaEvaluator(llm_client=FakeFeedbackLLMClient())

    feedback = evaluator.generate_feedback(session)

    assert feedback["total_understood_score"] == 82
    assert feedback["turn_feedback"][0]["heard_as"].startswith("외국인은")
    assert feedback["turn_feedback"][0]["understood_score"] == 70
    assert feedback["turn_feedback"][0]["score_delta"] == 8
    assert feedback["turn_feedback"][0]["improved_understood_score"] == 78
