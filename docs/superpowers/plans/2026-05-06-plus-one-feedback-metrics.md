# Plus-One Feedback Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 최종 피드백에서 각 답변별로 기존 문장에서 한 단계만 개선한 보완 문장, 발화별 외국인 이해도, 보완 문장 사용 시 예상 이해도 상승폭을 표시한다.

**Architecture:** 피드백 결과는 서버에서 deterministic rule 기반으로 안정화한다. LLM은 전체 점수와 요약 생성에만 보조적으로 사용하고, 발화별 점수/상승폭/보완 문장은 `Turn.filled_slots`, `Turn.transcript`, `Turn.missing_slots`를 기준으로 계산한다. 프론트는 새 필드를 그대로 렌더링하되, 기존 응답과의 호환성을 유지한다.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, vanilla HTML/CSS/JavaScript.

---

## File Structure

- Modify: `src/saynow_ai_demo/services/feedback.py`
  - 발화별 이해도 계산 함수 추가
  - 보완 문장 사용 시 예상 이해도 상승폭 계산 함수 추가
  - 기존 완성형 보완 문장을 `+1 개선 문장`으로 변경
  - `turn_feedback` item에 `understood_score`, `score_delta`, `improved_understood_score` 추가

- Modify: `src/saynow_ai_demo/static/index.html`
  - 최종 피드백 UI에 발화별 이해도와 예상 상승폭 표시
  - 보완 문장 라벨을 사용자가 이해하기 쉬운 형태로 표시

- Modify: `tests/services/test_feedback.py`
  - `+1 개선 문장`이 완성형 문장보다 우선되는지 검증
  - 발화별 이해도와 상승폭이 포함되는지 검증
  - 짧은 답변 `here`, `iced`, `small size`가 과하게 완성형으로 바뀌지 않는지 검증

- Modify: `tests/api/test_app.py`
  - `/feedback` 응답에 새 필드가 포함되는지 API 수준에서 검증

- Modify: `docs/ai-workflow/decision-log.md`
  - 피드백 정책 변경 기록
  - "완벽한 문장"이 아니라 "+1 개선 문장"을 쓰는 이유 기록

---

## Product Rules

### Rule 1: 보완 문장은 완벽한 정답보다 +1 개선을 우선한다

예시는 다음 기준으로 맞춘다.

| 사용자 답변 | 기존 완성형 | 변경 후 +1 개선 |
| --- | --- | --- |
| `I want ice latte` | `Can I get an iced latte, please?` | `I want an iced latte.` |
| `I want small latte` | `Can I get a small latte, please?` | `I want a small latte.` |
| `small size` | `A small one, please.` | `Small, please.` |
| `iced` | `Iced, please.` | `Iced, please.` |
| `here` | `For here, please.` | `For here, please.` |

### Rule 2: 발화별 이해도는 "그 발화만 봤을 때 통할 가능성"이다

발화별 이해도는 최종 total 이해도와 다르다.

추천 계산식:

```text
base = 45
+ filled slot 1개당 15점
+ 완성된 주문 문장처럼 보이면 10점
- STT/오타 의심 패턴이 있으면 10점
- 필요한 slot이 하나도 채워지지 않으면 20점
최종값은 35~95 사이로 clamp
```

MVP에서는 실제 발음/억양을 보지 않으므로 이 점수는 "발음 점수"가 아니라 "외국인이 의미를 이해할 가능성"이다.

### Rule 3: 상승폭은 보완 문장을 쓰면 올라갈 "예상치"다

```text
improved_understood_score = min(98, understood_score + score_delta)
score_delta = improved_understood_score - understood_score
```

추천 상승폭:

| 상황 | 상승폭 |
| --- | --- |
| slot은 전달됐지만 관사/어순이 어색함 | +8 |
| 단어만 말했지만 맥락상 통함 | +10 |
| `ice latte`처럼 흔한 비원어민 표현 | +12 |
| 이미 자연스러운 짧은 응답 | +3 |
| 정보 전달이 거의 안 됨 | +15 |

---

## Task 1: Feedback Domain Tests

**Files:**
- Modify: `tests/services/test_feedback.py`

- [ ] **Step 1: Write failing test for per-turn scores**

Append this test to `tests/services/test_feedback.py`.

```python
def test_rule_based_feedback_includes_turn_score_and_score_lift():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want ice latte",
            filled_slots={"drink": "latte", "temperature": "iced"},
            missing_slots=("size", "for_here_or_to_go"),
            assistant_message="What size would you like?",
        )
    )

    feedback = build_rule_based_feedback(session)
    turn_feedback = feedback["turn_feedback"][0]

    assert turn_feedback["understood_score"] == 75
    assert turn_feedback["score_delta"] == 12
    assert turn_feedback["improved_understood_score"] == 87
```

- [ ] **Step 2: Write failing test for +1 expression**

Append this test to `tests/services/test_feedback.py`.

```python
def test_feedback_uses_plus_one_expression_instead_of_perfect_sentence():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.append(
        Turn(
            id="turn-1",
            transcript="I want ice latte",
            filled_slots={"drink": "latte", "temperature": "iced"},
            missing_slots=("size", "for_here_or_to_go"),
            assistant_message="What size would you like?",
        )
    )

    feedback = build_rule_based_feedback(session)
    turn_feedback = feedback["turn_feedback"][0]

    assert turn_feedback["better_expression"] == "I want an iced latte."
    assert turn_feedback["better_expression"] != "Can I get an iced latte, please?"
    assert turn_feedback["reason"] == (
        "지금 문장에서 크게 바꾸지 않고, 'ice latte'만 자연스러운 'iced latte'로 고쳤어요."
    )
```

- [ ] **Step 3: Write failing test for short answers**

Append this test to `tests/services/test_feedback.py`.

```python
def test_feedback_keeps_short_answers_as_small_plus_one_changes():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.result = "success"
    session.turns.extend(
        [
            Turn(
                id="turn-1",
                transcript="small size",
                filled_slots={"size": "small"},
                missing_slots=("temperature", "for_here_or_to_go"),
                assistant_message="Would you like it hot or iced?",
            ),
            Turn(
                id="turn-2",
                transcript="here",
                filled_slots={"for_here_or_to_go": "for here"},
                missing_slots=(),
                assistant_message="Scenario cleared.",
            ),
        ]
    )

    feedback = build_rule_based_feedback(session)

    assert feedback["turn_feedback"][0]["better_expression"] == "Small, please."
    assert feedback["turn_feedback"][1]["better_expression"] == "For here, please."
    assert feedback["turn_feedback"][0]["score_delta"] == 10
    assert feedback["turn_feedback"][1]["score_delta"] == 3
```

- [ ] **Step 4: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/services/test_feedback.py -q
```

Expected:

```text
FAILED tests/services/test_feedback.py::test_rule_based_feedback_includes_turn_score_and_score_lift
FAILED tests/services/test_feedback.py::test_feedback_uses_plus_one_expression_instead_of_perfect_sentence
FAILED tests/services/test_feedback.py::test_feedback_keeps_short_answers_as_small_plus_one_changes
```

- [ ] **Step 5: Commit failing tests**

Do not commit failing tests alone unless the team explicitly wants red commits. In this repository, keep the red test and implementation in the same final commit for this task.

---

## Task 2: Feedback Scoring Implementation

**Files:**
- Modify: `src/saynow_ai_demo/services/feedback.py`
- Test: `tests/services/test_feedback.py`

- [ ] **Step 1: Add per-turn feedback fields**

In `_normalize_turn_feedback`, replace the appended dictionary with this shape.

```python
understood_score = _turn_understood_score(turn)
score_delta = _score_delta_for_turn(turn)
normalized.append(
    {
        "user_said": str(raw_item.get("user_said") or turn.transcript),
        "ai_question": str(raw_item.get("ai_question") or turn.assistant_message),
        "heard_as": _normalize_heard_as(raw_item.get("heard_as"), turn),
        "understood_score": understood_score,
        "better_expression": _better_expression_for_turn(turn, session),
        "score_delta": score_delta,
        "improved_understood_score": min(98, understood_score + score_delta),
        "reason": _reason_for_turn(turn),
    }
)
```

- [ ] **Step 2: Add the same fields to rule-based fallback**

In `build_rule_based_feedback`, replace the inline `turn_feedback` list item with a helper call.

```python
"turn_feedback": [_feedback_for_turn(turn, session) for turn in session.turns],
```

Add this helper below `build_rule_based_feedback`.

```python
def _feedback_for_turn(turn: Turn, session: SessionState) -> dict[str, object]:
    understood_score = _turn_understood_score(turn)
    score_delta = _score_delta_for_turn(turn)
    return {
        "user_said": turn.transcript,
        "ai_question": turn.assistant_message,
        "heard_as": _fallback_heard_as(turn),
        "understood_score": understood_score,
        "better_expression": _better_expression_for_turn(turn, session),
        "score_delta": score_delta,
        "improved_understood_score": min(98, understood_score + score_delta),
        "reason": _reason_for_turn(turn),
    }
```

- [ ] **Step 3: Add turn score helper**

Add these functions near `_fallback_total_score`.

```python
def _turn_understood_score(turn: Turn) -> int:
    if not turn.transcript.strip():
        return 35

    score = 45 + (len(turn.filled_slots) * 15)

    text = turn.transcript.lower().strip()
    if _looks_like_complete_sentence(text):
        score += 10
    if _has_common_transcription_issue(text):
        score -= 10
    if not turn.filled_slots:
        score -= 20

    return max(35, min(score, 95))


def _looks_like_complete_sentence(text: str) -> bool:
    starters = ("i want ", "i'd like ", "i would like ", "can i get ", "could i get ")
    return text.startswith(starters)


def _has_common_transcription_issue(text: str) -> bool:
    issue_patterns = (" lce ", " ice latte", " im ", " i'm to go")
    padded = f" {text} "
    return any(pattern in padded for pattern in issue_patterns)
```

- [ ] **Step 4: Add score delta helper**

Add this function below `_turn_understood_score`.

```python
def _score_delta_for_turn(turn: Turn) -> int:
    text = turn.transcript.lower().strip()
    if not turn.filled_slots:
        return 15
    if text in {"here", "to go", "iced", "hot"}:
        return 3
    if text in {"small", "medium", "large", "small size", "medium size", "large size"}:
        return 10
    if "ice latte" in text or "lce latte" in text:
        return 12
    return 8
```

- [ ] **Step 5: Run targeted tests**

Run:

```bash
.venv/bin/python -m pytest tests/services/test_feedback.py -q
```

Expected:

```text
10 passed
```

- [ ] **Step 6: Commit**

Run:

```bash
git add src/saynow_ai_demo/services/feedback.py tests/services/test_feedback.py
git commit -m "feat: 발화별 이해도와 상승폭 계산 추가"
```

---

## Task 3: Plus-One Expression Implementation

**Files:**
- Modify: `src/saynow_ai_demo/services/feedback.py`
- Test: `tests/services/test_feedback.py`

- [ ] **Step 1: Replace perfect sentence logic with plus-one logic**

Replace `_better_expression_for_turn` with this implementation.

```python
def _better_expression_for_turn(turn: Turn, session: SessionState) -> str:
    text = turn.transcript.strip()
    lowered = text.lower()
    slots = turn.filled_slots
    drink = _english_drink(slots.get("drink") or _drink_from_transcript(turn.transcript))
    size = _english_size(slots.get("size", ""))
    temperature = _english_temperature(slots.get("temperature", ""))

    if "for_here_or_to_go" in slots:
        destination = slots["for_here_or_to_go"].lower()
        if "to go" in destination or "take" in destination:
            return "To go, please."
        if "here" in destination:
            return "For here, please."

    if size and not drink and not temperature:
        return f"{size.capitalize()}, please."

    if temperature and not drink and not size:
        return f"{temperature.capitalize()}, please."

    if drink and temperature and "ice latte" in lowered:
        return f"I want an {temperature} {drink}."

    if drink and temperature and "lce latte" in lowered:
        return f"I want an {temperature} {drink}."

    if drink and size and lowered.startswith("i want "):
        return f"I want a {size} {drink}."

    if drink and temperature and lowered.startswith("i want "):
        article = "an" if temperature == "iced" else "a"
        return f"I want {article} {temperature} {drink}."

    if drink and lowered.startswith("i want "):
        return f"I want a {drink}."

    if drink and size and temperature:
        return f"A {size} {temperature} {drink}, please."

    if drink and size:
        return f"A {size} {drink}, please."

    if drink and temperature:
        article = "An" if temperature == "iced" else "A"
        return f"{article} {temperature} {drink}, please."

    if drink:
        return f"A {drink}, please."

    return _default_better_expression(session)
```

- [ ] **Step 2: Replace reason helper with specific plus-one reasons**

Replace `_reason_for_turn` with this implementation.

```python
def _reason_for_turn(turn: Turn) -> str:
    text = turn.transcript.lower().strip()
    slots = turn.filled_slots

    if "ice latte" in text or "lce latte" in text:
        return "지금 문장에서 크게 바꾸지 않고, 'ice latte'만 자연스러운 'iced latte'로 고쳤어요."
    if "for_here_or_to_go" in slots:
        return "짧게 답해도 통하지만, 'please'를 붙이면 더 자연스럽게 들려요."
    if text in {"small", "medium", "large", "small size", "medium size", "large size"}:
        return "단어만 말해도 통하지만, 'please'를 붙이면 더 부드럽게 들려요."
    if slots:
        return "기존 표현은 유지하고, 관사나 어순만 조금 더 자연스럽게 다듬었어요."
    return "뜻이 더 잘 전달되도록 최소한의 표현만 보완했어요."
```

- [ ] **Step 3: Run targeted tests**

Run:

```bash
.venv/bin/python -m pytest tests/services/test_feedback.py -q
```

Expected:

```text
10 passed
```

- [ ] **Step 4: Commit**

Run:

```bash
git add src/saynow_ai_demo/services/feedback.py tests/services/test_feedback.py
git commit -m "feat: 보완 문장을 플러스원 표현으로 변경"
```

---

## Task 4: API Contract Test

**Files:**
- Modify: `tests/api/test_app.py`

- [ ] **Step 1: Add API response test**

Append or update the feedback API test in `tests/api/test_app.py` with these assertions.

```python
def test_feedback_response_includes_turn_scores(client):
    start = client.post("/api/sessions", json={"scenario_id": "cafe_order"})
    session_id = start.json()["session_id"]

    client.post(
        f"/api/sessions/{session_id}/turns/text",
        json={"transcript": "I want ice latte small size"},
    )
    client.post(
        f"/api/sessions/{session_id}/turns/text",
        json={"transcript": "here"},
    )

    response = client.get(f"/api/sessions/{session_id}/feedback")

    assert response.status_code == 200
    turn_feedback = response.json()["turn_feedback"][0]
    assert "understood_score" in turn_feedback
    assert "score_delta" in turn_feedback
    assert "improved_understood_score" in turn_feedback
```

- [ ] **Step 2: Run API tests**

Run:

```bash
.venv/bin/python -m pytest tests/api/test_app.py -q
```

Expected:

```text
8 passed
```

- [ ] **Step 3: Commit**

Run:

```bash
git add tests/api/test_app.py
git commit -m "test: 피드백 응답 점수 필드 검증 추가"
```

---

## Task 5: Frontend Feedback Rendering

**Files:**
- Modify: `src/saynow_ai_demo/static/index.html`

- [ ] **Step 1: Update `renderFeedback` markup**

In `renderFeedback`, replace each `feedback-block` item template with this structure.

```javascript
              <div class="feedback-block">
                <strong>내 답변: ${escapeHtml(turn.user_said)}</strong>
                <div class="notice">AI 응답: ${escapeHtml(turn.ai_question)}</div>
                <div>
                  <strong>외국인 이해도</strong>
                  <span>${Number(turn.understood_score || 0)}%</span>
                  <span class="ok">+${Number(turn.score_delta || 0)}%</span>
                </div>
                <div>${escapeHtml(turn.heard_as)}</div>
                <div class="ok">
                  +1 표현: ${escapeHtml(turn.better_expression)}
                </div>
                <div class="notice">
                  이 표현을 쓰면 약 ${Number(turn.improved_understood_score || 0)}%까지 이해될 가능성이 있어요.
                </div>
                <div class="notice">${escapeHtml(turn.reason)}</div>
              </div>
```

- [ ] **Step 2: Keep backward compatibility**

Add this small helper above `renderFeedback`.

```javascript
      function numberOrZero(value) {
        const number = Number(value);
        return Number.isFinite(number) ? number : 0;
      }
```

Then use it in the template.

```javascript
${numberOrZero(turn.understood_score)}%
+${numberOrZero(turn.score_delta)}%
${numberOrZero(turn.improved_understood_score)}%
```

- [ ] **Step 3: Run static/API tests**

Run:

```bash
.venv/bin/python -m pytest tests/api/test_app.py -q
```

Expected:

```text
8 passed
```

- [ ] **Step 4: Commit**

Run:

```bash
git add src/saynow_ai_demo/static/index.html
git commit -m "feat: 최종 피드백에 발화별 이해도 표시"
```

---

## Task 6: Documentation

**Files:**
- Modify: `docs/ai-workflow/decision-log.md`

- [ ] **Step 1: Add decision log entry**

Append this section to `docs/ai-workflow/decision-log.md`.

```markdown
## 피드백 보완 문장을 +1 개선 방식으로 변경

### 배경

기존 최종 피드백은 사용자가 말한 문장을 바탕으로 자연스럽고 완성도 높은 문장을 제공했다.

예를 들어 `I want ice latte`에 대해 `Can I get an iced latte, please?`를 제공했다.

하지만 Say Now의 핵심 가치는 "내 영어가 실제로 통하는지 확인하고, 바로 한 단계만 더 낫게 말해보는 것"이다. 초보자에게 너무 완성된 문장을 바로 제시하면 사용자가 본인의 표현과 피드백 사이의 거리를 크게 느낄 수 있다.

### 변경

- 보완 문장을 완벽한 문장보다 기존 문장에서 +1 개선된 문장으로 제공한다.
- 각 발화마다 외국인 이해도 %를 표시한다.
- 보완 문장을 사용했을 때 예상 이해도 상승폭을 표시한다.
- 발화별 점수는 발음/억양 점수가 아니라 의미 전달 가능성 점수로 정의한다.

### 예시

| 사용자 답변 | 기존 방식 | 변경 방식 |
| --- | --- | --- |
| `I want ice latte` | `Can I get an iced latte, please?` | `I want an iced latte.` |
| `small size` | `A small one, please.` | `Small, please.` |
| `here` | `For here, please.` | `For here, please.` |

### 기대 효과

- 사용자는 본인이 한 말이 얼마나 통했는지 먼저 확인할 수 있다.
- 피드백이 지나치게 어려운 정답처럼 느껴지지 않는다.
- "내 표현도 통한다"와 "조금만 바꾸면 더 잘 통한다"를 동시에 전달할 수 있다.
```

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/ai-workflow/decision-log.md
git commit -m "docs: 플러스원 피드백 정책 기록"
```

---

## Task 7: End-to-End Verification

**Files:**
- No code changes

- [ ] **Step 1: Run full test suite**

Run:

```bash
.venv/bin/python -m pytest
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Run local server**

Run:

```bash
.venv/bin/uvicorn saynow_ai_demo.main:app --host 127.0.0.1 --port 8000
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8000
```

- [ ] **Step 3: Manual scenario**

Open `http://127.0.0.1:8000` and test this conversation.

```text
I want ice latte
small size
iced
here
```

Expected final feedback:

```text
시나리오 결과: success
내 답변: I want ice latte
외국인 이해도: 75% +12%
+1 표현: I want an iced latte.

내 답변: small size
외국인 이해도: 60% +10%
+1 표현: Small, please.

내 답변: iced
외국인 이해도: 60% +3%
+1 표현: Iced, please.

내 답변: here
외국인 이해도: 60% +3%
+1 표현: For here, please.
```

- [ ] **Step 4: Push**

Run:

```bash
git push origin feat/mvp-ai-workflow-demo
```

Expected:

```text
feat/mvp-ai-workflow-demo -> feat/mvp-ai-workflow-demo
```

---

## Self-Review

### Spec Coverage

- "+1된 문장" 요구사항: Task 1, Task 3
- 각 답변별 외국인 이해도 % 표시: Task 1, Task 2, Task 4, Task 5
- 보완 문장 사용 시 이해도 상승폭 표시: Task 1, Task 2, Task 4, Task 5
- 계획만 수립: 이 문서는 구현 계획만 추가하고 실제 제품 코드는 변경하지 않는다.

### Placeholder Scan

이 계획에는 `TBD`, `TODO`, `implement later`를 사용하지 않았다. 각 코드 변경 단계에는 구체적인 함수명, 파일명, 테스트명, 예상 결과가 포함되어 있다.

### Type Consistency

새 필드명은 모든 계층에서 동일하게 유지한다.

```text
understood_score
score_delta
improved_understood_score
```

`understood_score`는 발화별 점수이고, 기존 `total_understood_score`는 세션 전체 점수다.
