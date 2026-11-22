"""Serializable, compositional constraint language."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from murdoku.models.grid import Position
from murdoku.models.ids import AreaId, ClueId, ObjectId, PersonId


class Node(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PersonRef(Node):
    kind: Literal["person"] = "person"
    id: PersonId


class VariableRef(Node):
    kind: Literal["variable"] = "variable"
    name: str = Field(min_length=1)


class PositionRef(Node):
    kind: Literal["position"] = "position"
    position: Position


class ObjectRef(Node):
    kind: Literal["object"] = "object"
    id: ObjectId


Ref = Annotated[PersonRef | VariableRef | PositionRef | ObjectRef, Field(discriminator="kind")]


class Integer(Node):
    op: Literal["integer"] = "integer"
    value: int


class Coordinate(Node):
    op: Literal["coordinate"] = "coordinate"
    target: Ref
    axis: Literal["row", "col"]


class Distance(Node):
    op: Literal["distance"] = "distance"
    left: Ref
    right: Ref
    metric: Literal["manhattan", "chebyshev"] = "manhattan"


class Count(Node):
    op: Literal["count"] = "count"
    variable: str = Field(min_length=1)
    domain: Literal["people", "cells", "objects"]
    where: Predicate


class Arithmetic(Node):
    op: Literal["arithmetic"] = "arithmetic"
    left: Number
    operator: Literal["add", "subtract"]
    right: Number


Number = Annotated[Integer | Coordinate | Distance | Count | Arithmetic, Field(discriminator="op")]


class Compare(Node):
    op: Literal["compare"] = "compare"
    left: Number
    relation: Literal["eq", "ne", "lt", "le", "gt", "ge"]
    right: Number


class InArea(Node):
    op: Literal["area"] = "area"
    target: Ref
    area: AreaId


class SameArea(Node):
    op: Literal["same_area"] = "same_area"
    left: Ref
    right: Ref


class Adjacent(Node):
    op: Literal["adjacent"] = "adjacent"
    left: Ref
    right: Ref
    same_area: bool = True


class Direction(Node):
    op: Literal["direction"] = "direction"
    left: Ref
    right: Ref
    direction: Literal[
        "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"
    ]


class OnObject(Node):
    op: Literal["on_object"] = "on_object"
    target: Ref
    object: ObjectId


class Attribute(Node):
    op: Literal["attribute"] = "attribute"
    target: Ref
    name: str
    value: str


class ObjectKind(Node):
    op: Literal["object_kind"] = "object_kind"
    target: Ref
    value: str


class Terrain(Node):
    op: Literal["terrain"] = "terrain"
    target: Ref
    value: str


class Equal(Node):
    op: Literal["equal"] = "equal"
    left: Ref
    right: Ref


class Boolean(Node):
    op: Literal["all", "any"]
    items: tuple[Predicate, ...]


class Not(Node):
    op: Literal["not"] = "not"
    item: Predicate


class Quantifier(Node):
    op: Literal["exists", "forall", "unique"]
    variable: str = Field(min_length=1)
    domain: Literal["people", "cells", "objects"]
    where: Predicate


Predicate = Annotated[
    Compare
    | InArea
    | SameArea
    | Adjacent
    | Direction
    | OnObject
    | Attribute
    | ObjectKind
    | Equal
    | Terrain
    | Boolean
    | Not
    | Quantifier,
    Field(discriminator="op"),
]

for _model in (Arithmetic, Count, Compare, Boolean, Not, Quantifier):
    _model.model_rebuild()


class Constraint(Node):
    clue_id: ClueId
    expression: Predicate


class ConstraintSet(Node):
    constraints: tuple[Constraint, ...]
