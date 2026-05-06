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
    filled_slots: dict[str, str]
    missing_slots: list[str]
    is_scenario_complete: bool
    scenario_result: str
    assistant_message: str
    remaining_turns: int
