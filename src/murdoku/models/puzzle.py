from pydantic import model_validator

from .base import Frozen
from .grid import Area, GameObject, Grid
from .ids import PersonId
from .person import Clue, Person


class Puzzle(Frozen):
    id: str
    title: str
    grid: Grid
    areas: tuple[Area, ...]
    objects: tuple[GameObject, ...]
    people: tuple[Person, ...]
    victim: PersonId
    clues: tuple[Clue, ...]
    source_corrections: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_references(self) -> "Puzzle":
        for entities in (self.areas, self.objects, self.people, self.clues):
            ids = [entity.id for entity in entities]
            if len(set(ids)) != len(ids):
                raise ValueError("Entity identifiers must be unique within each category")
        people = {p.id for p in self.people}
        areas = {a.id for a in self.areas}
        if self.victim not in people:
            raise ValueError("Victim must reference a person")
        if any(c.person is not None and c.person not in people for c in self.clues):
            raise ValueError("Clue references an unknown person")
        if any(c.area not in areas for c in self.grid.cells):
            raise ValueError("Cell references an unknown area")
        cells = {(c.position.row, c.position.col): c for c in self.grid.cells}
        for obj in self.objects:
            key = (obj.position.row, obj.position.col)
            if key not in cells:
                raise ValueError("Object must be inside the grid")
            if not obj.occupiable and cells[key].occupiable:
                raise ValueError("Blocking object cannot occupy a walkable cell")
        return self
