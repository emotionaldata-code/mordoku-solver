"""Compile a validated AST by finite expansion, with no source evaluation."""

import z3

from murdoku.dsl.expressions import (
    Adjacent,
    Arithmetic,
    Attribute,
    Boolean,
    Compare,
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
    Predicate,
    Quantifier,
    SameArea,
    Terrain,
)
from murdoku.models import GameObject, Person
from murdoku.solver.context import Context, Scope


def absolute(value: z3.ArithRef) -> z3.ArithRef:
    return z3.If(value >= 0, value, 0 - value)


class Compiler:
    def __init__(self, context: Context):
        self.ctx = context

    def number(self, node: Number, scope: Scope) -> z3.ArithRef:
        if isinstance(node, Integer):
            return z3.IntVal(node.value)
        if isinstance(node, Coordinate):
            coordinates = self.ctx.coordinates(node.target, scope)
            return coordinates.row if node.axis == "row" else coordinates.col
        if isinstance(node, Arithmetic):
            left, right = self.number(node.left, scope), self.number(node.right, scope)
            return left + right if node.operator == "add" else left - right
        if isinstance(node, Distance):
            left, right = (
                self.ctx.coordinates(node.left, scope),
                self.ctx.coordinates(node.right, scope),
            )
            row, col = absolute(left.row - right.row), absolute(left.col - right.col)
            return row + col if node.metric == "manhattan" else z3.If(row >= col, row, col)
        return z3.Sum([z3.IntVal(0), *(z3.If(item, 1, 0) for item in self.expand(node, scope))])

    def expand(self, node: Count | Quantifier, scope: Scope) -> tuple[z3.BoolRef, ...]:
        return tuple(
            self.predicate(node.where, scope | {node.variable: entity})
            for entity in self.ctx.domain(node.domain)
        )

    def predicate(self, node: Predicate, scope: Scope | None = None) -> z3.BoolRef:
        scope = {} if scope is None else scope
        if isinstance(node, Compare):
            left, right = self.number(node.left, scope), self.number(node.right, scope)
            match node.relation:
                case "eq":
                    return left == right
                case "ne":
                    return left != right
                case "lt":
                    return left < right
                case "le":
                    return left <= right
                case "gt":
                    return left > right
                case "ge":
                    return left >= right
        if isinstance(node, InArea):
            return (
                self.ctx.area_at(self.ctx.coordinates(node.target, scope))
                == self.ctx.areas[node.area]
            )
        if isinstance(node, (SameArea, Adjacent, Direction, Equal)):
            left, right = (
                self.ctx.coordinates(node.left, scope),
                self.ctx.coordinates(node.right, scope),
            )
            same = self.ctx.area_at(left) == self.ctx.area_at(right)
            if isinstance(node, SameArea):
                return same
            if isinstance(node, Equal):
                # People and objects have identity even if they happen to share a cell.
                a, b = self.ctx.entity(node.left, scope), self.ctx.entity(node.right, scope)
                if isinstance(a, Person) and isinstance(b, Person):
                    return z3.BoolVal(a.id == b.id)
                if isinstance(a, GameObject) and isinstance(b, GameObject):
                    return z3.BoolVal(a.id == b.id)
                return z3.And(left.row == right.row, left.col == right.col)
            if isinstance(node, Adjacent):
                distance = absolute(left.row - right.row) + absolute(left.col - right.col)
                return z3.And(distance == 1, same if node.same_area else True)
            checks: list[z3.BoolRef] = []
            if "north" in node.direction:
                checks.append(left.row < right.row)
            if "south" in node.direction:
                checks.append(left.row > right.row)
            if "east" in node.direction:
                checks.append(left.col > right.col)
            if "west" in node.direction:
                checks.append(left.col < right.col)
            return z3.And(*checks)
        if isinstance(node, OnObject):
            left = self.ctx.coordinates(node.target, scope)
            right = self.ctx.coordinates(ObjectRef(id=node.object), scope)
            return z3.And(left.row == right.row, left.col == right.col)
        if isinstance(node, (Attribute, ObjectKind)):
            entity = self.ctx.entity(node.target, scope)
            if isinstance(node, Attribute):
                return z3.BoolVal(
                    isinstance(entity, Person) and entity.attributes.get(node.name) == node.value
                )
            return z3.BoolVal(isinstance(entity, GameObject) and entity.kind == node.value)
        if isinstance(node, Terrain):
            target = self.ctx.coordinates(node.target, scope)
            return z3.Or(
                *(
                    self.ctx.at(target, cell.position)
                    for cell in self.ctx.puzzle.grid.cells
                    if node.value in cell.terrain
                )
            )
        if isinstance(node, Boolean):
            compiled_items: list[z3.BoolRef] = []
            for item in node.items:
                compiled = self.predicate(item, scope)
                if node.op == "all" and z3.is_false(compiled):
                    return compiled
                if node.op == "any" and z3.is_true(compiled):
                    return compiled
                compiled_items.append(compiled)
            return z3.And(*compiled_items) if node.op == "all" else z3.Or(*compiled_items)
        if isinstance(node, Not):
            return z3.Not(self.predicate(node.item, scope))
        items = self.expand(node, scope)
        if node.op == "exists":
            return z3.Or(*items)
        if node.op == "forall":
            return z3.And(*items)
        return z3.Sum([z3.IntVal(0), *(z3.If(item, 1, 0) for item in items)]) == 1
