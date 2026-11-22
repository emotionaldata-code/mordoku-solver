"""Check the Zoo's literal clues with concrete Python geometry, independently of Z3."""

from pathlib import Path

import z3
from pydantic import BaseModel

from murdoku.dsl.expressions import ConstraintSet
from murdoku.extraction.normalizer import normalize
from murdoku.extraction.raw import RAW_ADAPTER, integer
from murdoku.models import AreaId, Cell, PersonId, Puzzle, Solution
from murdoku.solver.engine import decode, prepare, solve

Point = tuple[int, int]
FIXTURES = Path(__file__).parents[1] / "fixtures"
PUZZLE_ID = "puzzle-the-zoo-expert"
HABITATS = frozenset(AreaId(f"area_{i}") for i in (1, 2, 3, 5, 6, 8))
ANIMALS = frozenset(("bear", "shark", "lion", "elephant", "crocodile", "penguin"))


class ConcreteZoo:
    """Evaluate original clues without AST traversal or solver predicate helpers."""

    def __init__(self, puzzle: Puzzle, solution: Solution):
        self.points: dict[int, Point] = {
            int(p.person.removeprefix("char_")): (p.position.row, p.position.col)
            for p in solution.placements
        }
        self.cells: dict[Point, Cell] = {
            (cell.position.row, cell.position.col): cell for cell in puzzle.grid.cells
        }
        self.objects: tuple[tuple[Point, str], ...] = tuple(
            ((obj.position.row, obj.position.col), obj.kind) for obj in puzzle.objects
        )
        self.murderer: PersonId = solution.murderer

    def area(self, person: int) -> AreaId:
        return self.cells[self.points[person]].area

    def area_count(self, person: int) -> int:
        return sum(self.area(other) == self.area(person) for other in self.points)

    def adjacent(self, person: int, point: Point) -> bool:
        row, col = self.points[person]
        return abs(row - point[0]) + abs(col - point[1]) == 1 and self.cells[
            point
        ].area == self.area(person)

    def beside(self, person: int, kind: str) -> bool:
        return any(name == kind and self.adjacent(person, pt) for pt, name in self.objects)

    def sitting(self, person: int) -> bool:
        return (self.points[person], "chair") in self.objects

    def in_water(self, person: int) -> bool:
        return "water" in self.cells[self.points[person]].terrain

    def beside_water(self, person: int) -> bool:
        return any(
            "water" in cell.terrain and self.adjacent(person, point)
            for point, cell in self.cells.items()
        )

    def beside_animal(self, person: int) -> bool:
        return any(self.beside(person, kind) for kind in ANIMALS)

    def check_clues(self) -> None:
        # Each assertion follows the original person's clue, in character order.
        assert self.points[0][0] == self.points[8][0] - 1
        assert self.area(1) == "area_9" and self.area_count(1) == 2
        assert any(self.area(i) == self.area(1) for i in range(8) if i != 1)
        assert self.points[2][0] == self.points[3][0] - 1
        assert self.area(3) == "area_0"
        assert self.beside(4, "table") and not self.sitting(4)
        assert self.beside(5, "chair")
        assert self.sitting(6) and self.area_count(6) == 1
        assert self.area_count(7) == 1
        assert self.beside_animal(8)
        assert not self.in_water(9) and self.beside_water(9)
        assert self.area(10) == self.area(12) and self.area_count(10) == 2
        assert self.in_water(11) and not self.beside_animal(11)
        assert self.points[12][1] == 1
        assert self.beside(13, "tree")
        assert self.beside(14, "boulder")
        assert self.area_count(15) == 2
        murderer = int(self.murderer.removeprefix("char_"))
        assert murderer != 15 and self.area(murderer) == self.area(15)
        # Visitors are 0..7, zookeepers 8..15; each habitat needs a zookeeper.
        assert all(self.area(i) not in HABITATS for i in range(8))
        assert all(any(self.area(i) == habitat for i in range(8, 16)) for habitat in HABITATS)
        assert len({row for row, _ in self.points.values()}) == 16
        assert len({col for _, col in self.points.values()}) == 16
        assert all(self.cells[point].occupiable for point in self.points.values())


def test_uncorrected_json_projection_has_exactly_four_layouts() -> None:
    raw = RAW_ADAPTER.validate_json((FIXTURES / "raw" / f"{PUZZLE_ID}.json").read_text())
    # These raw facts explain why the Bear Habitat offers another water position.
    assert integer(raw["GRID"]["floor_type_1"]) == 12
    assert integer(raw["GRID"]["room_code_12_0"]) == 1
    assert integer(raw["GRID"]["room_objects_11_1"]) == 53
    puzzle = normalize(raw, PUZZLE_ID)
    # Reconstruct the uncorrected semantic projection from preserved raw floor codes.
    cells = tuple(
        cell.model_copy(update={"terrain": (*cell.terrain, "water")})
        if cell.area == "area_1" and "water" not in cell.terrain
        else cell
        for cell in puzzle.grid.cells
    )
    puzzle = puzzle.model_copy(update={"grid": puzzle.grid.model_copy(update={"cells": cells})})
    constraints = ConstraintSet.model_validate_json(
        (FIXTURES / "constraints" / f"{PUZZLE_ID}.json").read_text()
    )
    context, solver = prepare(puzzle, constraints, timeout_ms=30000)
    solutions: set[Solution] = set()
    for _ in range(4):
        assert solver.check() == z3.sat
        solution = decode(context, solver.model())
        ConcreteZoo(puzzle, solution).check_clues()
        solutions.add(solution)
        solver.add(
            z3.Or(
                *(
                    z3.Not(context.at(context.positions[p.person], p.position))
                    for p in solution.placements
                )
            )
        )
    assert solver.check() == z3.unsat
    assert len(solutions) == 4
    assert {solution.murderer for solution in solutions} == {"char_9"}


class WaterEvidence(BaseModel):
    water_cells: tuple[Point, ...]


def test_published_map_water_manifest_yields_unique_layout() -> None:
    """Check normalized water against independent map evidence, without official answers."""
    raw = RAW_ADAPTER.validate_json((FIXTURES / "raw" / f"{PUZZLE_ID}.json").read_text())
    puzzle = normalize(raw, PUZZLE_ID)
    evidence = WaterEvidence.model_validate_json(
        (FIXTURES / "map_evidence" / f"{PUZZLE_ID}-water.json").read_text()
    )
    water = {(c.position.row, c.position.col) for c in puzzle.grid.cells if "water" in c.terrain}
    assert water == set(evidence.water_cells)
    assert len(water) == 30
    bear_cells = tuple(c for c in puzzle.grid.cells if c.area == "area_1")
    assert bear_cells
    assert all("water" not in c.terrain and "floor_type:12" in c.terrain for c in bear_cells)
    assert any("subarea:area_11" in c.terrain for c in bear_cells)
    constraints = ConstraintSet.model_validate_json(
        (FIXTURES / "constraints" / f"{PUZZLE_ID}.json").read_text()
    )
    result = solve(puzzle, constraints, timeout_ms=30000)
    assert result.status == "unique"
    assert result.solution is not None
    ConcreteZoo(puzzle, result.solution).check_clues()
