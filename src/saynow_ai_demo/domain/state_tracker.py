from saynow_ai_demo.domain.models import SessionState


def merge_filled_slots(session: SessionState, new_slots: dict[str, str]) -> None:
    allowed_slots = set(session.scenario.required_slots) | set(
        session.scenario.optional_slots
    )
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
