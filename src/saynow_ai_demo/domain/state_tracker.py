from saynow_ai_demo.domain.models import SessionState


def extract_slots_from_transcript(transcript: str) -> dict[str, str]:
    normalized = f" {transcript.lower().strip()} "
    slots: dict[str, str] = {}

    if _contains_any(normalized, (" latte ", " lattes ")):
        slots["drink"] = "latte"
    elif _contains_any(normalized, (" americano ", " americanos ")):
        slots["drink"] = "americano"
    elif _contains_any(normalized, (" coffee ", " coffees ")):
        slots["drink"] = "coffee"

    if _contains_any(normalized, (" small ",)):
        slots["size"] = "small"
    elif _contains_any(normalized, (" medium ",)):
        slots["size"] = "medium"
    elif _contains_any(normalized, (" large ",)):
        slots["size"] = "large"

    if _contains_any(normalized, (" iced ", " ice ", " cold ")):
        slots["temperature"] = "iced"
    elif _contains_any(normalized, (" hot ", " warm ")):
        slots["temperature"] = "hot"

    if _contains_any(normalized, (" to go ", " takeaway ", " take away ")):
        slots["for_here_or_to_go"] = "to go"
    elif _contains_any(normalized, (" for here ", " here ")):
        slots["for_here_or_to_go"] = "for here"

    return slots


def merge_filled_slots(session: SessionState, new_slots: dict[str, str]) -> None:
    allowed_slots = set(session.scenario.required_slots) | set(
        session.scenario.optional_slots
    )
    for slot, value in new_slots.items():
        normalized = value.strip() if isinstance(value, str) else ""
        if slot in allowed_slots and normalized:
            session.filled_slots.setdefault(slot, normalized)


def get_missing_slots(session: SessionState) -> tuple[str, ...]:
    return tuple(
        slot
        for slot in session.scenario.required_slots
        if not session.filled_slots.get(slot)
    )


def is_complete(session: SessionState) -> bool:
    return not get_missing_slots(session)


def _contains_any(value: str, candidates: tuple[str, ...]) -> bool:
    return any(candidate in value for candidate in candidates)
