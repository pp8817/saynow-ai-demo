from dataclasses import dataclass, field
from typing import Literal


ScenarioResult = Literal["in_progress", "success", "failure"]


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    opening_question: str
    max_turns: int
    required_slots: tuple[str, ...]
    optional_slots: tuple[str, ...] = ()


@dataclass
class Turn:
    id: str
    transcript: str
    filled_slots: dict[str, str]
    missing_slots: tuple[str, ...]
    assistant_message: str


@dataclass
class SessionState:
    id: str
    scenario: Scenario
    filled_slots: dict[str, str] = field(default_factory=dict)
    turns: list[Turn] = field(default_factory=list)
    result: ScenarioResult = "in_progress"

    @property
    def remaining_turns(self) -> int:
        return max(self.scenario.max_turns - len(self.turns), 0)
