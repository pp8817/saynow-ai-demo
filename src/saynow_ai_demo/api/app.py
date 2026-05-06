import tempfile
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from saynow_ai_demo.adapters.llm import LocalLLMUnavailableError
from saynow_ai_demo.adapters.stt import STTAdapter
from saynow_ai_demo.api.schemas import (
    SessionResponse,
    StartSessionRequest,
    TextTurnRequest,
    TurnResponse,
)
from saynow_ai_demo.domain.models import SessionState
from saynow_ai_demo.domain.state_tracker import is_complete
from saynow_ai_demo.services.feedback import build_rule_based_feedback
from saynow_ai_demo.services.session_service import Evaluator, SessionService


class FeedbackGenerator(Protocol):
    def generate_feedback(self, session: SessionState) -> dict:
        ...


class RuleBasedFeedbackGenerator:
    def generate_feedback(self, session: SessionState) -> dict:
        return build_rule_based_feedback(session)


def create_app(
    evaluator: Evaluator | None = None,
    feedback_generator: FeedbackGenerator | None = None,
    stt_adapter: STTAdapter | None = None,
) -> FastAPI:
    if evaluator is None:
        from saynow_ai_demo.adapters.llm import OllamaEvaluator

        ollama_evaluator = OllamaEvaluator()
        evaluator = ollama_evaluator
        if feedback_generator is None:
            feedback_generator = ollama_evaluator
    if feedback_generator is None:
        feedback_generator = RuleBasedFeedbackGenerator()
    if stt_adapter is None:
        from saynow_ai_demo.adapters.stt import FasterWhisperSTTAdapter

        stt_adapter = FasterWhisperSTTAdapter()

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
        return _submit_transcript_response(service, session_id, request.transcript)

    @app.post("/api/sessions/{session_id}/turns/audio", response_model=TurnResponse)
    async def submit_audio_turn(session_id: str, audio: UploadFile = File(...)):
        suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
            tmp.write(await audio.read())
            tmp.flush()
            transcript = stt_adapter.transcribe(Path(tmp.name))
        return _submit_transcript_response(service, session_id, transcript)

    @app.get("/api/sessions/{session_id}/feedback")
    def get_feedback(session_id: str):
        try:
            session = service.get_session(session_id)
            if session.result == "in_progress":
                raise ValueError("세션 종료 후 최종 피드백을 확인할 수 있습니다.")
            return feedback_generator.generate_feedback(session)
        except LocalLLMUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def _submit_transcript_response(
    service: SessionService,
    session_id: str,
    transcript: str,
) -> TurnResponse:
    try:
        turn = service.submit_transcript(session_id, transcript)
        session = service.get_session(session_id)
    except LocalLLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TurnResponse(
        turn_id=turn.id,
        transcript=turn.transcript,
        filled_slots=turn.filled_slots,
        missing_slots=list(turn.missing_slots),
        is_scenario_complete=is_complete(session),
        scenario_result=session.result,
        assistant_message=turn.assistant_message,
        remaining_turns=session.remaining_turns,
    )
