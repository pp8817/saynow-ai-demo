# Say Now MVP AI Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로컬에서 무료로 실행 가능한 Say Now MVP AI Workflow 데모를 만든다.

**Architecture:** FastAPI가 API와 정적 HTML 화면을 함께 제공한다. Domain 계층은 시나리오, 세션, slot 상태를 순수 Python으로 관리하고, STT와 LLM은 adapter로 분리해 테스트에서는 fake 구현을 주입한다. 실제 로컬 데모에서는 `faster-whisper`와 Ollama HTTP API를 사용한다.

**Tech Stack:** Python 3.11+, FastAPI, pytest, pydantic, python-multipart, faster-whisper, Ollama, plain HTML/CSS/JS

---

## 1. 파일 구조

생성할 파일은 다음과 같다.

```text
.
├── .gitignore
├── README.md
├── pyproject.toml
├── src/
│   └── saynow_ai_demo/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   └── schemas.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── llm.py
│       │   └── stt.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── scenarios.py
│       │   └── state_tracker.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── evaluator.py
│       │   ├── feedback.py
│       │   └── session_service.py
│       └── static/
│           └── index.html
└── tests/
    ├── conftest.py
    ├── api/
    │   └── test_app.py
    ├── domain/
    │   ├── test_scenarios.py
    │   └── test_state_tracker.py
    └── services/
        ├── test_evaluator.py
        ├── test_feedback.py
        └── test_session_service.py
```

역할은 다음과 같다.

| 파일 | 책임 |
| --- | --- |
| `pyproject.toml` | 패키지 메타데이터, 실행/테스트 의존성, pytest 설정 |
| `README.md` | 로컬 실행 방법, Ollama/faster-whisper 준비 방법, 데모 한계 |
| `config.py` | 환경변수 기반 설정 |
| `main.py` | `uvicorn saynow_ai_demo.main:app` 진입점 |
| `api/app.py` | FastAPI app factory, route 연결, static file 제공 |
| `api/schemas.py` | API 요청/응답 pydantic schema |
| `adapters/stt.py` | STT protocol, faster-whisper adapter |
| `adapters/llm.py` | LLM protocol, Ollama adapter |
| `domain/models.py` | Scenario, SessionState, Turn domain model |
| `domain/scenarios.py` | `cafe_order` 시나리오 정의 |
| `domain/state_tracker.py` | filled/missing slot merge, 성공 여부 계산 |
| `services/evaluator.py` | LLM 턴 평가 prompt, JSON parsing, fallback 처리 |
| `services/feedback.py` | 세션 종료 피드백 생성 |
| `services/session_service.py` | 세션 시작, 턴 처리, 피드백 조회 orchestration |
| `static/index.html` | 녹음, 대화, 피드백을 테스트하는 단일 화면 |

---

## 2. 구현 순서와 커밋 단위

| Task | 커밋 메시지 |
| --- | --- |
| Task 1 | `chore: 로컬 데모 파이썬 프로젝트 초기 설정 추가` |
| Task 2 | `feat: 카페 주문 시나리오 도메인 모델 추가` |
| Task 3 | `feat: 시나리오 상태 추적 로직 추가` |
| Task 4 | `feat: LLM 턴 평가 파서 추가` |
| Task 5 | `feat: 세션 워크플로우 서비스 추가` |
| Task 6 | `feat: FastAPI 워크플로우 API 추가` |
| Task 7 | `feat: 로컬 STT와 Ollama 어댑터 추가` |
| Task 8 | `feat: 브라우저 데모 화면 추가` |
| Task 9 | `docs: 로컬 실행 방법과 구현 결정 기록 보완` |

각 Task는 테스트 통과 후 커밋한다.

---

## Task 1: 프로젝트 초기 설정

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `pyproject.toml`
- Create: `src/saynow_ai_demo/__init__.py`
- Create: `src/saynow_ai_demo/main.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 프로젝트 설정 파일 작성**

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "saynow-ai-demo"
version = "0.1.0"
description = "Local MVP AI workflow demo for Say Now"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.111.0",
  "uvicorn[standard]>=0.30.0",
  "python-multipart>=0.0.9",
  "pydantic>=2.7.0",
  "httpx>=0.27.0",
  "faster-whisper>=1.0.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "pytest-cov>=5.0.0"
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

`.gitignore`:

```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
.DS_Store
.env
local-audio/
```

`README.md`:

```markdown
# Say Now AI Demo

Say Now의 MVP AI Workflow를 로컬에서 검증하는 데모입니다.

## 목표

사용자 음성 입력부터 STT, LLM 기반 이해도 평가, 시나리오 상태 추적, 꼬리 질문, 성공/실패 판정, 최종 피드백까지 한 번에 실행되는지 확인합니다.

## 기본 구성

- Backend: FastAPI
- UI: 단일 HTML/CSS/JS
- STT: faster-whisper
- LLM: Ollama
- 저장소: in-memory session

## 실행

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn saynow_ai_demo.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다.

## 로컬 모델 준비

Ollama를 설치한 뒤 다음 모델을 받습니다.

```bash
ollama pull qwen2.5:7b-instruct
```

## MVP 한계

- 발음/억양 정밀 분석은 하지 않습니다.
- 이해도는 STT transcript와 LLM 추론 기반의 소통 가능성 점수입니다.
- 로컬 PC 성능에 따라 응답 시간이 달라질 수 있습니다.
```

`src/saynow_ai_demo/__init__.py`:

```python
"""Say Now local AI workflow demo."""
```

`src/saynow_ai_demo/main.py`:

```python
from saynow_ai_demo.api.app import create_app

app = create_app()
```

`tests/conftest.py`:

```python
import pytest


@pytest.fixture
def cafe_transcript() -> str:
    return "I want an iced latte small size"
```

- [ ] **Step 2: 테스트 실행**

Run:

```bash
python -m pytest
```

Expected:

```text
collected 0 items
```

- [ ] **Step 3: 커밋**

```bash
git add .gitignore README.md pyproject.toml src/saynow_ai_demo/__init__.py src/saynow_ai_demo/main.py tests/conftest.py
git commit -m "chore: 로컬 데모 파이썬 프로젝트 초기 설정 추가"
```

---

## Task 2: 카페 주문 시나리오 도메인 모델

**Files:**
- Create: `src/saynow_ai_demo/domain/__init__.py`
- Create: `src/saynow_ai_demo/domain/models.py`
- Create: `src/saynow_ai_demo/domain/scenarios.py`
- Create: `tests/domain/test_scenarios.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/domain/test_scenarios.py`:

```python
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
```

- [ ] **Step 2: RED 확인**

Run:

```bash
python -m pytest tests/domain/test_scenarios.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'saynow_ai_demo.domain'
```

- [ ] **Step 3: 구현**

`src/saynow_ai_demo/domain/__init__.py`:

```python
"""Domain models and rules for Say Now workflow."""
```

`src/saynow_ai_demo/domain/models.py`:

```python
from dataclasses import dataclass, field
from typing import Literal


ScenarioResult = Literal["in_progress", "success", "failure"]


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    opening_question: str
    max_turns: int
    required_slots: tuple[str, ...]
    optional_slots: tuple[str, ...] = ()


@dataclass
class Turn:
    id: str
    transcript: str
    understood_score: int
    interpreted_as: str
    filled_slots: dict[str, str]
    missing_slots: tuple[str, ...]
    assistant_message: str


@dataclass
class SessionState:
    id: str
    scenario: Scenario
    filled_slots: dict[str, str] = field(default_factory=dict)
    turns: list[Turn] = field(default_factory=list)
    result: ScenarioResult = "in_progress"

    @property
    def remaining_turns(self) -> int:
        return max(self.scenario.max_turns - len(self.turns), 0)
```

`src/saynow_ai_demo/domain/scenarios.py`:

```python
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
```

- [ ] **Step 4: GREEN 확인**

Run:

```bash
python -m pytest tests/domain/test_scenarios.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: 커밋**

```bash
git add src/saynow_ai_demo/domain tests/domain/test_scenarios.py
git commit -m "feat: 카페 주문 시나리오 도메인 모델 추가"
```

---

## Task 3: 시나리오 상태 추적 로직

**Files:**
- Create: `src/saynow_ai_demo/domain/state_tracker.py`
- Create: `tests/domain/test_state_tracker.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/domain/test_state_tracker.py`:

```python
from saynow_ai_demo.domain.models import SessionState
from saynow_ai_demo.domain.scenarios import get_scenario
from saynow_ai_demo.domain.state_tracker import (
    get_missing_slots,
    is_complete,
    merge_filled_slots,
)


def test_merge_filled_slots_keeps_existing_values_when_new_value_is_empty():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.filled_slots = {"drink": "iced latte"}

    merge_filled_slots(session, {"drink": "", "size": "small"})

    assert session.filled_slots == {
        "drink": "iced latte",
        "size": "small",
    }


def test_get_missing_slots_returns_required_slots_not_yet_filled():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.filled_slots = {
        "drink": "iced latte",
        "temperature": "iced",
    }

    assert get_missing_slots(session) == ("size", "for_here_or_to_go")


def test_is_complete_returns_true_when_all_required_slots_are_filled():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.filled_slots = {
        "drink": "iced latte",
        "temperature": "iced",
        "size": "small",
        "for_here_or_to_go": "to go",
    }

    assert is_complete(session) is True
```

- [ ] **Step 2: RED 확인**

Run:

```bash
python -m pytest tests/domain/test_state_tracker.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'saynow_ai_demo.domain.state_tracker'
```

- [ ] **Step 3: 구현**

`src/saynow_ai_demo/domain/state_tracker.py`:

```python
from saynow_ai_demo.domain.models import SessionState


def merge_filled_slots(session: SessionState, new_slots: dict[str, str]) -> None:
    allowed_slots = set(session.scenario.required_slots) | set(session.scenario.optional_slots)
    for slot, value in new_slots.items():
        normalized = value.strip() if isinstance(value, str) else ""
        if slot in allowed_slots and normalized:
            session.filled_slots[slot] = normalized


def get_missing_slots(session: SessionState) -> tuple[str, ...]:
    return tuple(
        slot
        for slot in session.scenario.required_slots
        if not session.filled_slots.get(slot)
    )


def is_complete(session: SessionState) -> bool:
    return not get_missing_slots(session)
```

- [ ] **Step 4: GREEN 확인**

Run:

```bash
python -m pytest tests/domain/test_state_tracker.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: 커밋**

```bash
git add src/saynow_ai_demo/domain/state_tracker.py tests/domain/test_state_tracker.py
git commit -m "feat: 시나리오 상태 추적 로직 추가"
```

---

## Task 4: LLM 턴 평가 파서

**Files:**
- Create: `src/saynow_ai_demo/services/__init__.py`
- Create: `src/saynow_ai_demo/services/evaluator.py`
- Create: `tests/services/test_evaluator.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/services/test_evaluator.py`:

```python
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
```

- [ ] **Step 2: RED 확인**

Run:

```bash
python -m pytest tests/services/test_evaluator.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'saynow_ai_demo.services'
```

- [ ] **Step 3: 구현**

`src/saynow_ai_demo/services/__init__.py`:

```python
"""Application services for Say Now workflow."""
```

`src/saynow_ai_demo/services/evaluator.py`:

```python
import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnEvaluation:
    understood_score: int
    interpreted_as: str
    filled_slots: dict[str, str]
    follow_up_question: str


def build_turn_prompt(
    scenario_title: str,
    required_slots: tuple[str, ...],
    current_slots: dict[str, str],
    transcript: str,
) -> str:
    return f"""
You are evaluating a beginner English learner in this scenario: {scenario_title}.

Required slots: {list(required_slots)}
Already filled slots: {current_slots}
User transcript: {transcript}

Return only one JSON object with these keys:
- understood_score: integer from 0 to 100
- interpreted_as: short English explanation of what a foreigner would likely understand
- filled_slots: object of newly identified slot values
- follow_up_question: one short English question to fill the most important missing slot
"""


def parse_turn_evaluation(raw: str) -> TurnEvaluation:
    try:
        payload = _load_first_json_object(raw)
    except ValueError:
        return TurnEvaluation(
            understood_score=30,
            interpreted_as="AI가 발화 의미를 안정적으로 해석하지 못했습니다.",
            filled_slots={},
            follow_up_question="Could you say that again more clearly?",
        )

    return TurnEvaluation(
        understood_score=_clamp_score(payload.get("understood_score", 30)),
        interpreted_as=str(
            payload.get("interpreted_as")
            or "AI가 발화 의미를 안정적으로 해석하지 못했습니다."
        ),
        filled_slots={
            str(key): str(value)
            for key, value in dict(payload.get("filled_slots") or {}).items()
            if str(value).strip()
        },
        follow_up_question=str(
            payload.get("follow_up_question")
            or "Could you say that again more clearly?"
        ),
    )


def _load_first_json_object(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("no JSON object found")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON object") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON object must be a dictionary")
    return data


def _clamp_score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 30
    return max(0, min(score, 100))
```

- [ ] **Step 4: GREEN 확인**

Run:

```bash
python -m pytest tests/services/test_evaluator.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: 커밋**

```bash
git add src/saynow_ai_demo/services tests/services/test_evaluator.py
git commit -m "feat: LLM 턴 평가 파서 추가"
```

---

## Task 5: 세션 Workflow 서비스

**Files:**
- Create: `src/saynow_ai_demo/services/session_service.py`
- Create: `src/saynow_ai_demo/services/feedback.py`
- Create: `tests/services/test_session_service.py`
- Create: `tests/services/test_feedback.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/services/test_session_service.py`:

```python
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
```

`tests/services/test_feedback.py`:

```python
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
```

- [ ] **Step 2: RED 확인**

Run:

```bash
python -m pytest tests/services/test_session_service.py tests/services/test_feedback.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'saynow_ai_demo.services.session_service'
```

- [ ] **Step 3: 구현**

`src/saynow_ai_demo/services/feedback.py`:

```python
from typing import Any

from saynow_ai_demo.domain.models import SessionState


def build_fallback_feedback(session: SessionState) -> dict[str, Any]:
    scores = [turn.understood_score for turn in session.turns]
    total_score = round(sum(scores) / len(scores)) if scores else 0
    return {
        "scenario_result": session.result,
        "total_understood_score": total_score,
        "summary": "세션의 발화 기록을 바탕으로 생성한 기본 피드백입니다.",
        "turn_feedback": [
            {
                "user_said": turn.transcript,
                "understood_score": turn.understood_score,
                "interpreted_as": turn.interpreted_as,
                "better_expression": "Can I get a small iced latte?",
                "reason": "더 자연스러운 표현 예시입니다.",
            }
            for turn in session.turns
        ],
    }
```

`src/saynow_ai_demo/services/session_service.py`:

```python
from typing import Protocol
from uuid import uuid4

from saynow_ai_demo.domain.models import Scenario, SessionState, Turn
from saynow_ai_demo.domain.scenarios import get_scenario
from saynow_ai_demo.domain.state_tracker import (
    get_missing_slots,
    is_complete,
    merge_filled_slots,
)
from saynow_ai_demo.services.evaluator import TurnEvaluation


class Evaluator(Protocol):
    def evaluate(
        self,
        *,
        scenario: Scenario,
        current_slots: dict[str, str],
        transcript: str,
    ) -> TurnEvaluation:
        ...


class SessionService:
    def __init__(self, evaluator: Evaluator):
        self._evaluator = evaluator
        self._sessions: dict[str, SessionState] = {}

    def start_session(self, scenario_id: str) -> SessionState:
        scenario = get_scenario(scenario_id)
        session = SessionState(id=str(uuid4()), scenario=scenario)
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> SessionState:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"unknown session: {session_id}") from exc

    def submit_transcript(self, session_id: str, transcript: str) -> Turn:
        session = self.get_session(session_id)
        if session.result != "in_progress":
            raise ValueError(f"session already finished: {session.result}")

        evaluation = self._evaluator.evaluate(
            scenario=session.scenario,
            current_slots=dict(session.filled_slots),
            transcript=transcript,
        )
        merge_filled_slots(session, evaluation.filled_slots)
        missing_slots = get_missing_slots(session)

        if is_complete(session):
            session.result = "success"
            assistant_message = "Scenario cleared."
        elif session.remaining_turns <= 1:
            session.result = "failure"
            assistant_message = "The scenario was not cleared in time."
        else:
            assistant_message = evaluation.follow_up_question or _fallback_question(missing_slots)

        turn = Turn(
            id=f"turn-{len(session.turns) + 1}",
            transcript=transcript,
            understood_score=evaluation.understood_score,
            interpreted_as=evaluation.interpreted_as,
            filled_slots=dict(evaluation.filled_slots),
            missing_slots=missing_slots,
            assistant_message=assistant_message,
        )
        session.turns.append(turn)
        return turn


def _fallback_question(missing_slots: tuple[str, ...]) -> str:
    fallback_by_slot = {
        "drink": "What would you like to order?",
        "size": "What size would you like?",
        "temperature": "Would you like it hot or iced?",
        "for_here_or_to_go": "Is that for here or to go?",
    }
    first_missing = missing_slots[0] if missing_slots else "drink"
    return fallback_by_slot.get(first_missing, "Could you say that again?")
```

- [ ] **Step 4: GREEN 확인**

Run:

```bash
python -m pytest tests/services/test_session_service.py tests/services/test_feedback.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: 커밋**

```bash
git add src/saynow_ai_demo/services/session_service.py src/saynow_ai_demo/services/feedback.py tests/services/test_session_service.py tests/services/test_feedback.py
git commit -m "feat: 세션 워크플로우 서비스 추가"
```

---

## Task 6: FastAPI Workflow API

**Files:**
- Create: `src/saynow_ai_demo/api/__init__.py`
- Create: `src/saynow_ai_demo/api/schemas.py`
- Create: `src/saynow_ai_demo/api/app.py`
- Create: `tests/api/test_app.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/api/test_app.py`:

```python
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
    session_id = client.post("/api/sessions", json={"scenario_id": "cafe_order"}).json()["session_id"]

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
    session_id = client.post("/api/sessions", json={"scenario_id": "cafe_order"}).json()["session_id"]
    client.post(
        f"/api/sessions/{session_id}/turns/text",
        json={"transcript": "I want ice latte small size"},
    )

    response = client.get(f"/api/sessions/{session_id}/feedback")

    assert response.status_code == 200
    assert response.json()["turn_feedback"][0]["user_said"] == "I want ice latte small size"
```

Note: `/turns/text`는 STT 설치 전에도 Workflow를 검증하기 위한 개발용 endpoint다. 브라우저 기본 흐름은 `/turns/audio`를 사용한다.

- [ ] **Step 2: RED 확인**

Run:

```bash
python -m pytest tests/api/test_app.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'saynow_ai_demo.api'
```

- [ ] **Step 3: 구현**

`src/saynow_ai_demo/api/__init__.py`:

```python
"""FastAPI routes for Say Now demo."""
```

`src/saynow_ai_demo/api/schemas.py`:

```python
from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    scenario_id: str


class TextTurnRequest(BaseModel):
    transcript: str


class SessionResponse(BaseModel):
    session_id: str
    scenario_id: str
    assistant_message: str
    remaining_turns: int


class TurnResponse(BaseModel):
    turn_id: str
    transcript: str
    understood_score: int
    interpreted_as: str
    filled_slots: dict[str, str]
    missing_slots: list[str]
    is_scenario_complete: bool
    scenario_result: str
    assistant_message: str
    remaining_turns: int
```

`src/saynow_ai_demo/api/app.py`:

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from saynow_ai_demo.api.schemas import (
    SessionResponse,
    StartSessionRequest,
    TextTurnRequest,
    TurnResponse,
)
from saynow_ai_demo.domain.state_tracker import is_complete
from saynow_ai_demo.services.feedback import build_fallback_feedback
from saynow_ai_demo.services.session_service import Evaluator, SessionService


def create_app(evaluator: Evaluator | None = None) -> FastAPI:
    if evaluator is None:
        from saynow_ai_demo.adapters.llm import OllamaEvaluator

        evaluator = OllamaEvaluator()

    service = SessionService(evaluator=evaluator)
    app = FastAPI(title="Say Now AI Demo")

    @app.get("/")
    def index():
        static_path = Path(__file__).resolve().parents[1] / "static" / "index.html"
        return FileResponse(static_path)

    @app.post("/api/sessions", response_model=SessionResponse)
    def start_session(request: StartSessionRequest):
        try:
            session = service.start_session(request.scenario_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return SessionResponse(
            session_id=session.id,
            scenario_id=session.scenario.id,
            assistant_message=session.scenario.opening_question,
            remaining_turns=session.remaining_turns,
        )

    @app.post("/api/sessions/{session_id}/turns/text", response_model=TurnResponse)
    def submit_text_turn(session_id: str, request: TextTurnRequest):
        try:
            turn = service.submit_transcript(session_id, request.transcript)
            session = service.get_session(session_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return TurnResponse(
            turn_id=turn.id,
            transcript=turn.transcript,
            understood_score=turn.understood_score,
            interpreted_as=turn.interpreted_as,
            filled_slots=turn.filled_slots,
            missing_slots=list(turn.missing_slots),
            is_scenario_complete=is_complete(session),
            scenario_result=session.result,
            assistant_message=turn.assistant_message,
            remaining_turns=session.remaining_turns,
        )

    @app.get("/api/sessions/{session_id}/feedback")
    def get_feedback(session_id: str):
        try:
            session = service.get_session(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return build_fallback_feedback(session)

    return app
```

- [ ] **Step 4: GREEN 확인**

Run:

```bash
python -m pytest tests/api/test_app.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: 커밋**

```bash
git add src/saynow_ai_demo/api tests/api/test_app.py
git commit -m "feat: FastAPI 워크플로우 API 추가"
```

---

## Task 7: 로컬 STT와 Ollama 어댑터

**Files:**
- Create: `src/saynow_ai_demo/config.py`
- Create: `src/saynow_ai_demo/adapters/__init__.py`
- Create: `src/saynow_ai_demo/adapters/llm.py`
- Create: `src/saynow_ai_demo/adapters/stt.py`
- Modify: `src/saynow_ai_demo/api/app.py`
- Modify: `src/saynow_ai_demo/api/schemas.py`
- Create: `tests/services/test_ollama_evaluator.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/services/test_ollama_evaluator.py`:

```python
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
```

- [ ] **Step 2: RED 확인**

Run:

```bash
python -m pytest tests/services/test_ollama_evaluator.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'saynow_ai_demo.adapters'
```

- [ ] **Step 3: 구현**

`src/saynow_ai_demo/config.py`:

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("SAYNOW_OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("SAYNOW_OLLAMA_MODEL", "qwen2.5:7b-instruct")
    whisper_model: str = os.getenv("SAYNOW_WHISPER_MODEL", "small.en")


settings = Settings()
```

`src/saynow_ai_demo/adapters/__init__.py`:

```python
"""External AI adapters for local demo."""
```

`src/saynow_ai_demo/adapters/llm.py`:

```python
from typing import Protocol

import httpx

from saynow_ai_demo.config import settings
from saynow_ai_demo.domain.models import Scenario
from saynow_ai_demo.services.evaluator import (
    TurnEvaluation,
    build_turn_prompt,
    parse_turn_evaluation,
)


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


class OllamaClient:
    def __init__(self, base_url: str = settings.ollama_url, model: str = settings.ollama_model):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return str(response.json().get("response", ""))


class OllamaEvaluator:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or OllamaClient()

    def evaluate(
        self,
        *,
        scenario: Scenario,
        current_slots: dict[str, str],
        transcript: str,
    ) -> TurnEvaluation:
        prompt = build_turn_prompt(
            scenario_title=scenario.title,
            required_slots=scenario.required_slots,
            current_slots=current_slots,
            transcript=transcript,
        )
        return parse_turn_evaluation(self.llm_client.complete(prompt))
```

`src/saynow_ai_demo/adapters/stt.py`:

```python
from pathlib import Path
from typing import Protocol

from saynow_ai_demo.config import settings


class STTAdapter(Protocol):
    def transcribe(self, audio_path: Path) -> str:
        ...


class FasterWhisperSTTAdapter:
    def __init__(self, model_name: str = settings.whisper_model):
        self.model_name = model_name
        self._model = None

    def transcribe(self, audio_path: Path) -> str:
        model = self._get_model()
        segments, _info = model.transcribe(str(audio_path), language="en")
        return " ".join(segment.text.strip() for segment in segments).strip()

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        return self._model
```

- [ ] **Step 4: audio endpoint 추가**

`api/app.py`에 `UploadFile`, `File`, `tempfile`, `FasterWhisperSTTAdapter`를 연결한다.

핵심 route:

```python
@app.post("/api/sessions/{session_id}/turns/audio", response_model=TurnResponse)
async def submit_audio_turn(session_id: str, audio: UploadFile = File(...)):
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp.flush()
        transcript = stt_adapter.transcribe(Path(tmp.name))
    return _submit_transcript_response(service, session_id, transcript)
```

`create_app` signature는 다음처럼 바꾼다.

```python
def create_app(
    evaluator: Evaluator | None = None,
    stt_adapter: STTAdapter | None = None,
) -> FastAPI:
```

text/audio route가 같은 응답 변환 함수를 쓰도록 `_submit_transcript_response` helper를 만든다.

- [ ] **Step 5: GREEN 확인**

Run:

```bash
python -m pytest tests/services/test_ollama_evaluator.py tests/api/test_app.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 6: 커밋**

```bash
git add src/saynow_ai_demo/config.py src/saynow_ai_demo/adapters src/saynow_ai_demo/api tests/services/test_ollama_evaluator.py
git commit -m "feat: 로컬 STT와 Ollama 어댑터 추가"
```

---

## Task 8: 브라우저 데모 화면

**Files:**
- Create: `src/saynow_ai_demo/static/index.html`
- Modify: `tests/api/test_app.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/api/test_app.py`에 추가:

```python
def test_index_serves_demo_page():
    client = TestClient(create_app(evaluator=FakeEvaluator()))

    response = client.get("/")

    assert response.status_code == 200
    assert "Say Now AI Demo" in response.text
    assert "startSession" in response.text
```

- [ ] **Step 2: RED 확인**

Run:

```bash
python -m pytest tests/api/test_app.py::test_index_serves_demo_page -q
```

Expected:

```text
RuntimeError or 404 because index.html does not exist
```

- [ ] **Step 3: UI 구현**

`src/saynow_ai_demo/static/index.html`은 다음 기능을 포함한다.

- 세션 시작 버튼
- AI 메시지/사용자 transcript 대화 로그
- `MediaRecorder` 기반 녹음 시작/중지 버튼
- 개발용 텍스트 입력
- 최종 피드백 표시 영역

핵심 JavaScript 함수 이름:

```javascript
async function startSession() {}
async function submitTextTurn() {}
async function startRecording() {}
async function stopRecording() {}
async function submitAudioBlob(blob) {}
async function loadFeedback() {}
function appendMessage(role, text) {}
function renderFeedback(feedback) {}
```

UI는 한 화면에서 Workflow 확인이 가능하도록 구성한다.

- 왼쪽: 시나리오 상태, 남은 턴
- 가운데: 대화 로그
- 오른쪽 또는 하단: 최종 피드백

- [ ] **Step 4: GREEN 확인**

Run:

```bash
python -m pytest tests/api/test_app.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: 커밋**

```bash
git add src/saynow_ai_demo/static/index.html tests/api/test_app.py
git commit -m "feat: 브라우저 데모 화면 추가"
```

---

## Task 9: 문서 보완과 전체 검증

**Files:**
- Modify: `README.md`
- Modify: `docs/ai-workflow/decision-log.md`

- [ ] **Step 1: README 보완**

다음 내용을 `README.md`에 추가한다.

- `SAYNOW_OLLAMA_MODEL`
- `SAYNOW_WHISPER_MODEL`
- `/turns/text` 개발용 endpoint 설명
- 로컬 실행이 느릴 때 모델을 낮추는 방법
- 발음 정밀 분석은 MVP 범위가 아니라는 설명

- [ ] **Step 2: decision log 보완**

`/turns/text` 개발용 endpoint를 추가했다면 `docs/ai-workflow/decision-log.md`에 다음 결정을 기록한다.

```markdown
## 2026-05-06 - 개발용 text turn endpoint 추가

### 변경 전
브라우저 음성 입력과 audio endpoint만 사용

### 변경 후
`POST /api/sessions/{session_id}/turns/text` 개발용 endpoint 추가

### 변경 이유
STT 모델 설치 전에도 AI Workflow를 테스트할 수 있게 하기 위함

### 성능 영향
STT 품질을 반영하지 않으므로 실제 음성 Workflow와 다를 수 있음

### 비용 영향
변화 없음

### 리소스 영향
STT 모델을 거치지 않아 더 가볍게 테스트 가능

### 구현 복잡도 영향
API route 하나가 추가되지만 테스트와 디버깅이 쉬워짐
```

- [ ] **Step 3: 전체 테스트**

Run:

```bash
python -m pytest -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 4: 앱 smoke test**

Run:

```bash
uvicorn saynow_ai_demo.main:app --reload
```

Manual check:

```text
http://127.0.0.1:8000 접속
세션 시작 가능
개발용 텍스트 입력으로 꼬리 질문 반환
피드백 조회 가능
```

- [ ] **Step 5: 커밋**

```bash
git add README.md docs/ai-workflow/decision-log.md
git commit -m "docs: 로컬 실행 방법과 구현 결정 기록 보완"
```

---

## 3. 검증 기준

구현 완료 전 다음을 확인한다.

```bash
python -m pytest -q
```

로컬 앱 실행:

```bash
uvicorn saynow_ai_demo.main:app --reload
```

브라우저 확인:

```text
http://127.0.0.1:8000
```

기능 확인:

- 세션 시작 가능
- 텍스트 턴 제출 가능
- 음성 녹음 버튼 표시
- audio endpoint가 존재함
- slot 기반 꼬리 질문 반환
- required slot이 채워지면 성공 처리
- 턴 제한이 끝나면 실패 처리
- 피드백 조회 가능
- decision log에 스펙 변경 기록 존재

---

## 4. 계획 self-review

### 스펙 커버리지

| 스펙 요구사항 | 구현 Task |
| --- | --- |
| FastAPI + 단일 HTML 화면 | Task 1, 6, 8 |
| faster-whisper STT adapter | Task 7 |
| Ollama LLM adapter | Task 7 |
| in-memory session | Task 5 |
| 카페 주문 시나리오 | Task 2 |
| required slot 추적 | Task 3 |
| 꼬리 질문 생성 | Task 4, 5 |
| 성공/실패 판정 | Task 3, 5 |
| 세션 피드백 | Task 5 |
| 구현 결정 기록 | Task 9 |
| 테스트 | Task 2-9 |

### 모호성 제거

- 첫 시나리오는 `cafe_order` 하나만 구현한다.
- 개발용 text endpoint는 STT 설치 전 Workflow 검증을 위한 도구로 포함한다.
- 실제 음성 Workflow는 audio endpoint를 사용한다.
- LLM 품질은 자동 테스트 대상이 아니며, adapter 경계와 parsing만 테스트한다.
- 브라우저 UI는 production UI가 아니라 local demo UI다.
