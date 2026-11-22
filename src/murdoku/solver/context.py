"""Finite map encoding; person placements are the only decision variables."""

from dataclasses import dataclass

import z3

from murdoku.dsl.expressions import ObjectRef, PersonRef, Ref, VariableRef
from murdoku.models import Cell, GameObject, Person, PersonId, Position, Puzzle

Entity = Person | Cell | GameObject
Scope = dict[str, Entity]


@dataclass(frozen=True)
class Coordinates:
    row: z3.ArithRef
    col: z3.ArithRef


class Context:
    def __init__(self, puzzle: Puzzle):
        self.puzzle = puzzle
        self.positions = {
            person.id: Coordinates(z3.Int(f"row_{i}"), z3.Int(f"col_{i}"))
            for i, person in enumerate(puzzle.people)
        }
        self.areas = {area.id: i for i, area in enumerate(puzzle.areas)}
        self._area_cache = {
            (str(cell.position.row), str(cell.position.col)): z3.IntVal(self.areas[cell.area])
            for cell in puzzle.grid.cells
        }

    def entity(self, ref: Ref, scope: Scope) -> Entity | Position:
        if isinstance(ref, VariableRef):
            return scope[ref.name]
        if isinstance(ref, PersonRef):
            return next(p for p in self.puzzle.people if p.id == ref.id)
        if isinstance(ref, ObjectRef):
            return next(o for o in self.puzzle.objects if o.id == ref.id)
        return ref.position

    def coordinates(self, ref: Ref, scope: Scope) -> Coordinates:
        entity = self.entity(ref, scope)
        if isinstance(entity, Person):
            return self.positions[entity.id]
        pos = entity if isinstance(entity, Position) else entity.position
        return Coordinates(z3.IntVal(pos.row), z3.IntVal(pos.col))

    def area_at(self, coord: Coordinates) -> z3.ArithRef:
        key = (str(coord.row), str(coord.col))
        if key in self._area_cache:
            return self._area_cache[key]
        result = z3.IntVal(-1)
        for cell in self.puzzle.grid.cells:
            result = z3.If(self.at(coord, cell.position), self.areas[cell.area], result)
        self._area_cache[key] = result
        return result

    @staticmethod
    def at(coord: Coordinates, pos: Position) -> z3.BoolRef:
        return z3.And(coord.row == pos.row, coord.col == pos.col)

    def domain(self, domain: str) -> tuple[Entity, ...]:
        if domain == "people":
            return self.puzzle.people
        if domain == "objects":
            return self.puzzle.objects
        return self.puzzle.grid.cells

    def victim_position(self) -> Coordinates:
        return self.positions[self.puzzle.victim]

    def murderer(self, person: PersonId) -> z3.BoolRef:
        return self.area_at(self.positions[person]) == self.area_at(self.victim_position())
