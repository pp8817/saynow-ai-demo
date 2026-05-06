from saynow_ai_demo.domain.models import SessionState
from saynow_ai_demo.domain.scenarios import get_scenario
from saynow_ai_demo.domain.state_tracker import (
    extract_slots_from_transcript,
    get_missing_slots,
    is_complete,
    merge_filled_slots,
)


def test_merge_filled_slots_keeps_existing_values_when_new_value_is_empty():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.filled_slots = {"drink": "iced latte"}

    merge_filled_slots(session, {"drink": "", "size": "small"})

    assert session.filled_slots == {
        "drink": "iced latte",
        "size": "small",
    }


def test_merge_filled_slots_does_not_overwrite_existing_values():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.filled_slots = {"temperature": "iced"}

    merge_filled_slots(session, {"temperature": "hot"})

    assert session.filled_slots == {"temperature": "iced"}


def test_extract_slots_from_transcript_handles_short_cafe_answers():
    assert extract_slots_from_transcript("I want ice latte") == {
        "drink": "latte",
        "temperature": "iced",
    }
    assert extract_slots_from_transcript("small please") == {"size": "small"}
    assert extract_slots_from_transcript("here") == {
        "for_here_or_to_go": "for here"
    }
    assert extract_slots_from_transcript("I'm to go") == {
        "for_here_or_to_go": "to go"
    }


def test_get_missing_slots_returns_required_slots_not_yet_filled():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.filled_slots = {
        "drink": "iced latte",
        "temperature": "iced",
    }

    assert get_missing_slots(session) == ("size", "for_here_or_to_go")


def test_is_complete_returns_true_when_all_required_slots_are_filled():
    session = SessionState(id="s1", scenario=get_scenario("cafe_order"))
    session.filled_slots = {
        "drink": "iced latte",
        "temperature": "iced",
        "size": "small",
        "for_here_or_to_go": "to go",
    }

    assert is_complete(session) is True
