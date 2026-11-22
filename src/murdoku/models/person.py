from pydantic import Field

from .base import Frozen
from .ids import ClueId, PersonId


class Person(Frozen):
    id: PersonId
    name: str
    attributes: dict[str, str] = Field(default_factory=dict)


class Clue(Frozen):
    id: ClueId
    text: str
    person: PersonId | None = None
