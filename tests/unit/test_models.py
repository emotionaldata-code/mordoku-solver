import pytest
from pydantic import ValidationError

from murdoku.models import AreaId, Cell, Grid, Placement, Position, Solution
from murdoku.models.ids import PersonId


def test_grid_requires_complete_unique_coordinates() -> None:
    cell = Cell(position=Position(row=0, col=0), area=AreaId("room"))
    with pytest.raises(ValidationError, match="each in-bounds"):
        Grid(width=2, height=1, cells=(cell, cell))
    with pytest.raises(ValidationError):
        Position(row=-1, col=0)


def test_models_reject_unknown_fields_and_mutation() -> None:
    with pytest.raises(ValidationError):
        Position.model_validate({"row": 0, "col": 0, "x": 3})
    position = Position(row=0, col=0)
    with pytest.raises(ValidationError, match="frozen"):
        position.row = 3


def test_solution_requires_valid_distinct_people() -> None:
    placement = Placement(person=PersonId("A"), position=Position(row=0, col=0))
    with pytest.raises(ValidationError):
        Solution(placements=(placement, placement), murderer=PersonId("A"))
    with pytest.raises(ValidationError):
        Solution(placements=(placement,), murderer=PersonId("B"))
