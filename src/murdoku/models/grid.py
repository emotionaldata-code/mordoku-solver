from pydantic import Field, model_validator

from .base import Frozen
from .ids import AreaId, ObjectId


class Position(Frozen):
    row: int = Field(ge=0)
    col: int = Field(ge=0)


class Cell(Frozen):
    position: Position
    area: AreaId
    occupiable: bool = True
    terrain: tuple[str, ...] = ()


class Grid(Frozen):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    cells: tuple[Cell, ...]

    @model_validator(mode="after")
    def validate_cells(self) -> "Grid":
        positions = {(c.position.row, c.position.col) for c in self.cells}
        expected = {(r, c) for r in range(self.height) for c in range(self.width)}
        if positions != expected or len(self.cells) != len(expected):
            raise ValueError("Grid must contain each in-bounds cell exactly once")
        return self


class Area(Frozen):
    id: AreaId
    name: str


class GameObject(Frozen):
    id: ObjectId
    kind: str
    position: Position
    occupiable: bool
    code: int
