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
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
uvicorn saynow_ai_demo.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다.

## 환경 변수

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `SAYNOW_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API 주소 |
| `SAYNOW_OLLAMA_MODEL` | `qwen2.5:7b-instruct` | 턴 평가에 사용할 로컬 LLM |
| `SAYNOW_WHISPER_MODEL` | `small.en` | faster-whisper STT 모델 |

## 로컬 모델 준비

Ollama를 설치한 뒤 다음 모델을 받습니다.

```bash
ollama pull qwen2.5:7b-instruct
```

로컬 환경에서 느리면 모델을 낮춰 실행합니다.

```bash
SAYNOW_WHISPER_MODEL=base.en SAYNOW_OLLAMA_MODEL=qwen2.5:3b-instruct uvicorn saynow_ai_demo.main:app --reload
```

## API

### 세션 시작

```http
POST /api/sessions
```

```json
{
  "scenario_id": "cafe_order"
}
```

### 음성 턴 제출

```http
POST /api/sessions/{session_id}/turns/audio
```

브라우저 녹음 파일을 `multipart/form-data`의 `audio` 필드로 전송합니다.

### 개발용 텍스트 턴 제출

```http
POST /api/sessions/{session_id}/turns/text
```

```json
{
  "transcript": "I want ice latte small size"
}
```

이 endpoint는 STT 모델을 설치하지 않은 상태에서도 AI Workflow를 확인하기 위한 개발용 기능입니다.

### 피드백 조회

```http
GET /api/sessions/{session_id}/feedback
```

## 테스트

```bash
.venv/bin/python -m pytest -q
```

## MVP 한계

- 발음/억양 정밀 분석은 하지 않습니다.
- 이해도는 STT transcript와 LLM 추론 기반의 소통 가능성 점수입니다.
- 로컬 PC 성능에 따라 응답 시간이 달라질 수 있습니다.
- `/turns/text`는 실제 음성 품질을 반영하지 않습니다.
