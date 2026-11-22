from pydantic import model_validator

from .base import Frozen
from .grid import Position
from .ids import PersonId


class Placement(Frozen):
    person: PersonId
    position: Position


class Solution(Frozen):
    placements: tuple[Placement, ...]
    murderer: PersonId

    @model_validator(mode="after")
    def validate_people(self) -> "Solution":
        ids = [p.person for p in self.placements]
        if len(set(ids)) != len(ids) or self.murderer not in ids:
            raise ValueError("Solution requires distinct people and a placed murderer")
        return self
