from typing import Protocol
from uuid import uuid4

from saynow_ai_demo.domain.models import Scenario, SessionState, Turn
from saynow_ai_demo.domain.scenarios import get_scenario
from saynow_ai_demo.domain.state_tracker import (
    extract_slots_from_transcript,
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

        missing_slots_before_turn = get_missing_slots(session)
        evaluation = self._evaluator.evaluate(
            scenario=session.scenario,
            current_slots=dict(session.filled_slots),
            transcript=transcript,
        )
        transcript_slots = extract_slots_from_transcript(transcript)
        turn_slots = {
            **evaluation.filled_slots,
            **transcript_slots,
        }
        turn_slots = _filter_slots_for_current_question(
            session=session,
            missing_slots_before_turn=missing_slots_before_turn,
            turn_slots=turn_slots,
        )
        newly_filled_slots = {
            slot: value
            for slot, value in turn_slots.items()
            if slot not in session.filled_slots
        }
        merge_filled_slots(session, turn_slots)
        missing_slots = get_missing_slots(session)

        if is_complete(session):
            session.result = "success"
            assistant_message = "Scenario cleared."
        elif session.remaining_turns <= 1:
            session.result = "failure"
            assistant_message = "The scenario was not cleared in time."
        else:
            assistant_message = _fallback_question(missing_slots)

        turn = Turn(
            id=f"turn-{len(session.turns) + 1}",
            transcript=transcript,
            filled_slots=dict(newly_filled_slots),
            missing_slots=missing_slots,
            assistant_message=assistant_message,
        )
        session.turns.append(turn)
        return turn


def _filter_slots_for_current_question(
    *,
    session: SessionState,
    missing_slots_before_turn: tuple[str, ...],
    turn_slots: dict[str, str],
) -> dict[str, str]:
    if not missing_slots_before_turn:
        return {}

    missing_slot_set = set(missing_slots_before_turn)
    slots_for_missing_values = {
        slot: value for slot, value in turn_slots.items() if slot in missing_slot_set
    }
    if not session.turns:
        return slots_for_missing_values

    expected_slot = missing_slots_before_turn[0]
    if expected_slot not in slots_for_missing_values:
        return {}
    return slots_for_missing_values


def _fallback_question(missing_slots: tuple[str, ...]) -> str:
    fallback_by_slot = {
        "drink": "What would you like to order?",
        "size": "What size would you like?",
        "temperature": "Would you like it hot or iced?",
        "for_here_or_to_go": "Is that for here or to go?",
    }
    first_missing = missing_slots[0] if missing_slots else "drink"
    return fallback_by_slot.get(first_missing, "Could you say that again?")
