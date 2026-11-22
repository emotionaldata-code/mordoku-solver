"""Official answers for test comparisons only; never imported by the solver."""

from decimal import Decimal

from murdoku.models import PersonId, Placement, Position, Solution

from .normalizer import person_indices
from .raw import RawPuzzle, integer, modern


def official_solution(raw: RawPuzzle) -> Solution:
    props = raw["PROPERTIES"]
    data = {**raw.get("GRID", {}), **raw["CHARACTERS"]}
    placements: list[Placement] = []
    for i in person_indices(raw):
        if modern(raw):
            row, col = integer(data[f"solution_y_{i}"]), integer(data[f"solution_x_{i}"])
        else:
            size = Decimal(props["cellsize"])
            if size <= 0:
                raise ValueError("Cell size must be positive")
            col = int((Decimal(data[f"letter_xpos_{i}"]) - Decimal(props["grid_rx"])) / size)
            row = int((Decimal(data[f"letter_ypos_{i}"]) - Decimal(props["grid_ry"])) / size)
        placements.append(
            Placement(person=PersonId(f"char_{i}"), position=Position(row=row, col=col))
        )
    return Solution(
        placements=tuple(placements), murderer=PersonId(f"char_{integer(props['murderer'])}")
    )
