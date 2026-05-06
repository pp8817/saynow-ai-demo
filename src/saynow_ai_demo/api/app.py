import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from saynow_ai_demo.adapters.stt import STTAdapter
from saynow_ai_demo.api.schemas import (
    SessionResponse,
    StartSessionRequest,
    TextTurnRequest,
    TurnResponse,
)
from saynow_ai_demo.domain.state_tracker import is_complete
from saynow_ai_demo.services.feedback import build_fallback_feedback
from saynow_ai_demo.services.session_service import Evaluator, SessionService


def create_app(
    evaluator: Evaluator | None = None,
    stt_adapter: STTAdapter | None = None,
) -> FastAPI:
    if evaluator is None:
        from saynow_ai_demo.adapters.llm import OllamaEvaluator

        evaluator = OllamaEvaluator()
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
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return build_fallback_feedback(session)

    return app


def _submit_transcript_response(
    service: SessionService,
    session_id: str,
    transcript: str,
) -> TurnResponse:
    try:
        turn = service.submit_transcript(session_id, transcript)
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
