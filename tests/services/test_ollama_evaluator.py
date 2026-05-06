from saynow_ai_demo.adapters.llm import OllamaEvaluator
from saynow_ai_demo.domain.scenarios import get_scenario


class FakeLLMClient:
    def complete(self, prompt: str) -> str:
        assert "카페에서 주문하기" in prompt
        return """
        {
          "understood_score": 90,
          "interpreted_as": "The user wants coffee to go.",
          "filled_slots": {
            "drink": "coffee",
            "for_here_or_to_go": "to go"
          },
          "follow_up_question": "What size would you like?"
        }
        """


def test_ollama_evaluator_uses_llm_client_and_parses_result():
    evaluator = OllamaEvaluator(llm_client=FakeLLMClient())

    result = evaluator.evaluate(
        scenario=get_scenario("cafe_order"),
        current_slots={},
        transcript="coffee to go",
    )

    assert result.understood_score == 90
    assert result.filled_slots == {
        "drink": "coffee",
        "for_here_or_to_go": "to go",
    }
    assert result.follow_up_question == "What size would you like?"
