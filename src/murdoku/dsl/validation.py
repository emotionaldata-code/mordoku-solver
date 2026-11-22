"""Reference and lexical-scope checks beyond the structural JSON schema."""

from murdoku.dsl.expressions import (
    Adjacent,
    Arithmetic,
    Attribute,
    Boolean,
    Compare,
    ConstraintSet,
    Coordinate,
    Count,
    Direction,
    Distance,
    Equal,
    InArea,
    Integer,
    Not,
    Number,
    ObjectKind,
    ObjectRef,
    OnObject,
    PersonRef,
    PositionRef,
    Predicate,
    Quantifier,
    Ref,
    SameArea,
    Terrain,
)
from murdoku.models import Puzzle


def validate_constraints(puzzle: Puzzle, constraints: ConstraintSet) -> None:
    people = {p.id for p in puzzle.people}
    objects = {o.id for o in puzzle.objects}
    areas = {a.id for a in puzzle.areas}
    clues = {c.id for c in puzzle.clues}

    def ref(node: Ref, scope: dict[str, str]) -> str:
        if isinstance(node, PersonRef):
            if node.id not in people:
                raise ValueError(f"Unknown person: {node.id}")
            return "people"
        if isinstance(node, ObjectRef):
            if node.id not in objects:
                raise ValueError(f"Unknown object: {node.id}")
            return "objects"
        if isinstance(node, PositionRef):
            if node.position.row >= puzzle.grid.height or node.position.col >= puzzle.grid.width:
                raise ValueError("Position is outside the grid")
            return "cells"
        if node.name not in scope:
            raise ValueError(f"Unbound variable: {node.name}")
        return scope[node.name]

    def number(node: Number, scope: dict[str, str]) -> None:
        if isinstance(node, Integer):
            return
        if isinstance(node, Coordinate):
            ref(node.target, scope)
        elif isinstance(node, Distance):
            ref(node.left, scope)
            ref(node.right, scope)
        elif isinstance(node, Arithmetic):
            number(node.left, scope)
            number(node.right, scope)
        else:
            quantified(node, scope)

    def quantified(node: Count | Quantifier, scope: dict[str, str]) -> None:
        if node.variable in scope:
            raise ValueError(f"Variable shadows an existing binding: {node.variable}")
        predicate(node.where, scope | {node.variable: node.domain})

    def predicate(node: Predicate, scope: dict[str, str]) -> None:
        if isinstance(node, Compare):
            number(node.left, scope)
            number(node.right, scope)
        elif isinstance(node, InArea):
            ref(node.target, scope)
            if node.area not in areas:
                raise ValueError(f"Unknown area: {node.area}")
        elif isinstance(node, (SameArea, Adjacent, Direction, Equal)):
            ref(node.left, scope)
            ref(node.right, scope)
        elif isinstance(node, OnObject):
            ref(node.target, scope)
            if node.object not in objects:
                raise ValueError(f"Unknown object: {node.object}")
        elif isinstance(node, (Attribute, ObjectKind)):
            domain = ref(node.target, scope)
            expected = "people" if isinstance(node, Attribute) else "objects"
            if domain != expected:
                raise ValueError(f"{node.op} requires a reference from {expected}")
            if isinstance(node, Attribute) and not any(
                node.name in p.attributes for p in puzzle.people
            ):
                raise ValueError(f"Unknown person attribute: {node.name}")
            if isinstance(node, ObjectKind) and node.value not in {o.kind for o in puzzle.objects}:
                raise ValueError(f"Unknown object kind: {node.value}")
        elif isinstance(node, Terrain):
            ref(node.target, scope)
            if node.value not in {tag for cell in puzzle.grid.cells for tag in cell.terrain}:
                raise ValueError(f"Unknown terrain: {node.value}")
        elif isinstance(node, Boolean):
            for item in node.items:
                predicate(item, scope)
        elif isinstance(node, Not):
            predicate(node.item, scope)
        else:
            quantified(node, scope)

    for constraint in constraints.constraints:
        if constraint.clue_id not in clues:
            raise ValueError(f"Unknown clue: {constraint.clue_id}")
        predicate(constraint.expression, {})
