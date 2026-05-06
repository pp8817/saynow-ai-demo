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

## 로컬 모델 준비

Ollama를 설치한 뒤 다음 모델을 받습니다.

```bash
ollama pull qwen2.5:7b-instruct
```

## MVP 한계

- 발음/억양 정밀 분석은 하지 않습니다.
- 이해도는 STT transcript와 LLM 추론 기반의 소통 가능성 점수입니다.
- 로컬 PC 성능에 따라 응답 시간이 달라질 수 있습니다.
