# AI Workflow 결정 기록

이 문서는 Say Now AI Workflow를 구현하면서 발생한 주요 기술 선택과 스펙 변경을 기록한다.

블로그 작성 시 다음 질문에 답할 수 있도록 유지한다.

- 왜 이 구성을 선택했는가?
- 어떤 대안을 제외했는가?
- 성능, 비용, 로컬 리소스 관점에서 어떤 차이가 있는가?
- 구현 중 스펙을 바꿨다면 무엇이 달라졌는가?

---

## 2026-05-06 - MVP 데모를 로컬 AI Workflow로 구현

### 변경 전

초기 검토 단계에서는 Upstage Solar 같은 API 기반 LLM을 사용할 수 있는지 확인했다. 다만 STT까지 Upstage 공개 API로 처리하기는 어려워 보여, API 조합을 쓰려면 별도 STT 서비스가 필요했다.

### 변경 후

MVP 데모는 로컬에서 무료로 실행 가능한 구성으로 구현한다.

```text
브라우저 음성 녹음
→ faster-whisper 기반 STT
→ Ollama 기반 로컬 LLM
→ 시나리오 상태 추적
→ 꼬리 질문 또는 성공/실패 판정
→ 최종 피드백
```

### 변경 이유

현재 목적은 AI 성능 최적화가 아니라 실제 Workflow 검증이다. API 토큰, 과금, 외부 서비스 설정에 의존하기보다 로컬에서 빠르게 실행 가능한 데모를 먼저 만드는 편이 적합하다.

### 성능 영향

로컬 STT와 로컬 LLM은 상용 API보다 품질이 낮거나 응답이 느릴 수 있다. 특히 다음 영역에서 차이가 날 수 있다.

- STT 정확도
- LLM의 한국어 피드백 품질
- structured JSON 출력 안정성
- 응답 속도

다만 이번 단계에서는 성능보다 Workflow 검증이 우선이므로 허용 가능한 차이로 본다.

### 비용 영향

API 토큰 비용이 발생하지 않는다. 최초 모델 다운로드와 로컬 실행 리소스만 필요하다.

### 리소스 영향

`faster-whisper small.en`과 Ollama 7B급 모델을 사용할 경우 로컬 CPU/메모리 사용량이 증가할 수 있다. 로컬 환경에서 느리면 다음 순서로 낮춘다.

```text
STT: small.en → base.en
LLM: 7B instruct 모델 → 더 작은 instruct 모델
```

### 구현 복잡도 영향

API 기반 구현보다 로컬 의존성 설치가 조금 늘어난다. 대신 네트워크/API key 없이 데모를 실행할 수 있고, adapter 구조를 두면 이후 OpenAI/Upstage 같은 외부 API로 교체할 수 있다.

## 2026-05-06 - 개발용 text turn endpoint 추가

### 변경 전

브라우저 음성 입력과 audio endpoint만 사용한다.

### 변경 후

`POST /api/sessions/{session_id}/turns/text` 개발용 endpoint를 추가했다.

### 변경 이유

STT 모델 설치 전에도 시나리오 시작, transcript 평가, slot 업데이트, 꼬리 질문, 피드백 조회까지 AI Workflow를 테스트할 수 있게 하기 위함이다.

### 성능 영향

텍스트 endpoint는 STT 품질, 발음, 녹음 품질을 반영하지 않는다. 따라서 실제 음성 Workflow보다 이해도 점수가 높거나 안정적으로 보일 수 있다.

### 비용 영향

변화 없음. 로컬 실행이므로 API 비용은 발생하지 않는다.

### 리소스 영향

STT 모델을 거치지 않기 때문에 더 가볍고 빠르게 Workflow를 테스트할 수 있다.

### 구현 복잡도 영향

API route가 하나 추가되지만, STT 문제와 LLM/상태 추적 문제를 분리해서 디버깅할 수 있어 전체 구현 리스크는 낮아진다.

---

## 2026-05-06 - 실행 명령을 python3 기준으로 정리

### 변경 전

초기 README 실행 예시는 `python` 명령을 사용했다.

### 변경 후

로컬 환경에서 확인된 명령에 맞춰 `python3`와 `.venv/bin/python` 기준으로 문서를 정리했다.

### 변경 이유

macOS 로컬 환경에서 `python` 명령이 없고 `python3`만 존재했다. 사용자가 그대로 실행했을 때 막히지 않도록 문서 명령을 실제 환경에 맞췄다.

### 성능 영향

없음.

### 비용 영향

없음.

### 리소스 영향

없음.

### 구현 복잡도 영향

없음. 문서 명령만 변경했다.

---

## 2026-05-06 - Ollama 미실행 시 local fallback evaluator 추가(폐기됨)

### 변경 전

`/turns/text`와 `/turns/audio`는 모두 Ollama LLM 호출에 의존했다. 로컬에서 Ollama가 실행 중이지 않으면 `127.0.0.1:11434` 연결 실패가 500 에러로 전파됐고, 브라우저 화면에서는 별도 메시지가 표시되지 않아 사용자가 아무 반응이 없다고 느낄 수 있었다.

### 변경 후

Ollama 호출이 실패하면 local rule-based fallback evaluator가 동작한다. fallback은 transcript의 키워드를 기준으로 `drink`, `temperature`, `size`, `for_here_or_to_go` slot을 채우고, 가장 먼저 빠진 slot에 대한 꼬리 질문을 생성한다.

### 변경 이유

현재 목적은 AI 성능 검증이 아니라 Workflow 검증이다. Ollama 설치 여부 때문에 세션 진행, slot 업데이트, 꼬리 질문, 피드백 조회를 테스트하지 못하는 것은 데모 목적과 맞지 않다.

### 성능 영향

Ollama가 정상 실행 중이면 기존처럼 LLM 기반 평가를 사용한다. Ollama가 없을 때는 fallback이 동작하므로 피드백 품질과 의미 해석 범위는 낮아진다. 대신 텍스트 기반 Workflow는 끊기지 않는다.

### 비용 영향

변화 없음. fallback도 로컬 코드이므로 API 비용이 발생하지 않는다.

### 리소스 영향

Ollama 미실행 상태에서는 LLM 모델을 로드하지 않아 더 가볍게 동작한다.

### 구현 복잡도 영향

fallback 규칙 코드가 추가되어 약간 복잡해졌다. 대신 데모 실행 안정성이 높아지고, Ollama 설치 전에도 테스트가 가능해졌다.

---

## 2026-05-06 - local fallback evaluator 제거 및 Ollama 경고 반환

### 변경 전

Ollama 호출이 실패하면 local rule-based fallback evaluator가 transcript 키워드를 기준으로 slot을 채우고 꼬리 질문을 생성했다.

### 변경 후

Ollama 호출이 실패하면 AI 평가를 진행하지 않고 `503` 응답으로 경고 문구를 반환한다.

```text
Ollama가 실행 중이 아니어서 AI 평가를 진행할 수 없습니다. `ollama serve` 실행 후 다시 시도하세요.
```

### 변경 이유

이번 테스트의 목적은 fallback 규칙이 아니라 Ollama LLM을 활용한 실제 AI Workflow를 확인하는 것이다. fallback이 동작하면 사용자가 Ollama가 사용된 것으로 오해할 수 있어, 실패 상태를 명시적으로 보여주는 편이 더 정확하다.

### 성능 영향

Ollama가 실행 중일 때의 성능은 변하지 않는다. Ollama가 없을 때는 더 이상 임의 점수나 꼬리 질문을 생성하지 않으므로, 실제 AI 평가 품질과 fallback 품질이 섞이지 않는다.

### 비용 영향

변화 없음. 로컬 실행이므로 API 비용은 발생하지 않는다.

### 리소스 영향

Ollama 미실행 시 추가 모델이나 fallback 연산을 수행하지 않는다.

### 구현 복잡도 영향

fallback 규칙 코드가 제거되어 LLM adapter의 책임이 단순해졌다. 대신 API는 `LocalLLMUnavailableError`를 `503` 경고 응답으로 변환한다.

---

## 변경 기록 템플릿

```markdown
## YYYY-MM-DD - 변경 제목

### 변경 전

### 변경 후

### 변경 이유

### 성능 영향

### 비용 영향

### 리소스 영향

### 구현 복잡도 영향
```
