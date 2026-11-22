"""Universal placement and crime-scene rules."""

import z3

from murdoku.solver.context import Context


def base_rules(ctx: Context) -> tuple[z3.BoolRef, ...]:
    positions = tuple(ctx.positions.values())
    allowed = tuple(c for c in ctx.puzzle.grid.cells if c.occupiable)
    rules = [z3.Or(*(ctx.at(p, c.position) for c in allowed)) for p in positions]
    # Each row and each column contains at most one person, including rectangles.
    rules.extend(
        (z3.Distinct(*(p.row for p in positions)), z3.Distinct(*(p.col for p in positions)))
    )
    others = [ctx.murderer(p.id) for p in ctx.puzzle.people if p.id != ctx.puzzle.victim]
    rules.append(z3.Sum([z3.IntVal(0), *(z3.If(item, 1, 0) for item in others)]) == 1)
    return tuple(rules)
