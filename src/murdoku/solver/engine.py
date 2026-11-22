"""Solver execution, decoding, uniqueness proof, and diagnostic clue cores."""

from typing import Literal

import z3

from murdoku.dsl.expressions import ConstraintSet
from murdoku.dsl.validation import validate_constraints
from murdoku.models import ClueId, Placement, Position, Puzzle, Solution
from murdoku.models.base import Frozen
from murdoku.solver.base_rules import base_rules
from murdoku.solver.compiler import Compiler
from murdoku.solver.context import Context


class SolveResult(Frozen):
    status: Literal["unique", "multiple", "unsat", "unknown"]
    solution: Solution | None = None
    alternative: Solution | None = None
    conflicting_clues: tuple[ClueId, ...] = ()
    reason: str | None = None


def prepare(
    puzzle: Puzzle, constraints: ConstraintSet, timeout_ms: int
) -> tuple[Context, z3.Solver]:
    if timeout_ms <= 0:
        raise ValueError("Timeout must be positive")
    validate_constraints(puzzle, constraints)
    ctx, solver = Context(puzzle), z3.Solver()
    solver.set(timeout=timeout_ms)
    solver.add(*base_rules(ctx))
    compiler = Compiler(ctx)
    grouped: dict[ClueId, list[z3.BoolRef]] = {}
    for item in constraints.constraints:
        grouped.setdefault(item.clue_id, []).append(compiler.predicate(item.expression))
    for index, expressions in enumerate(grouped.values()):
        solver.assert_and_track(z3.And(*expressions), f"clue_{index}")
    return ctx, solver


def decode(ctx: Context, model: z3.ModelRef) -> Solution:
    placements = tuple(
        Placement(
            person=person,
            position=Position(
                row=model.eval(coord.row).as_long(), col=model.eval(coord.col).as_long()
            ),
        )
        for person, coord in ctx.positions.items()
    )
    victim = next(p.position for p in placements if p.person == ctx.puzzle.victim)
    areas = {c.position: c.area for c in ctx.puzzle.grid.cells}
    murderer = next(
        p.person
        for p in placements
        if p.person != ctx.puzzle.victim and areas[p.position] == areas[victim]
    )
    return Solution(placements=placements, murderer=murderer)


def solve(puzzle: Puzzle, constraints: ConstraintSet, timeout_ms: int = 10000) -> SolveResult:
    ctx, solver = prepare(puzzle, constraints, timeout_ms)
    status = solver.check()
    if status == z3.unsat:
        ids = tuple(dict.fromkeys(c.clue_id for c in constraints.constraints))
        labels = {str(label) for label in solver.unsat_core()}
        return SolveResult(
            status="unsat",
            conflicting_clues=tuple(cid for i, cid in enumerate(ids) if f"clue_{i}" in labels),
        )
    if status != z3.sat:
        return SolveResult(status="unknown", reason=solver.reason_unknown())
    solution = decode(ctx, solver.model())
    solver.add(
        z3.Or(*(z3.Not(ctx.at(ctx.positions[p.person], p.position)) for p in solution.placements))
    )
    second = solver.check()
    if second == z3.unsat:
        return SolveResult(status="unique", solution=solution)
    if second == z3.sat:
        return SolveResult(
            status="multiple", solution=solution, alternative=decode(ctx, solver.model())
        )
    return SolveResult(
        status="unknown", solution=solution, reason=f"Uniqueness: {solver.reason_unknown()}"
    )


def verify(
    puzzle: Puzzle,
    solution: Solution,
    constraints: ConstraintSet | None = None,
    timeout_ms: int = 10000,
) -> bool:
    if {p.person for p in solution.placements} != {p.id for p in puzzle.people}:
        raise ValueError("Solution must place every puzzle person exactly once")
    if solution.murderer == puzzle.victim:
        return False
    ctx, solver = prepare(puzzle, constraints or ConstraintSet(constraints=()), timeout_ms)
    for placement in solution.placements:
        solver.add(ctx.at(ctx.positions[placement.person], placement.position))
    solver.add(ctx.murderer(solution.murderer))
    status = solver.check()
    if status != z3.sat and status != z3.unsat:
        raise ValueError(f"Verification unknown: {solver.reason_unknown()}")
    return status == z3.sat
