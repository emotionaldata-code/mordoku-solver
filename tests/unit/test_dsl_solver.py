from unittest.mock import patch

import pytest
import z3
from pydantic import ValidationError

from murdoku.dsl.expressions import ConstraintSet
from murdoku.dsl.validation import validate_constraints
from murdoku.models import (
    Area,
    AreaId,
    Cell,
    Clue,
    ClueId,
    GameObject,
    Grid,
    ObjectId,
    Person,
    PersonId,
    Position,
    Puzzle,
)
from murdoku.solver.compiler import Compiler
from murdoku.solver.context import Context
from murdoku.solver.engine import solve, verify


@pytest.fixture
def tiny() -> Puzzle:
    return Puzzle(
        id="tiny",
        title="Tiny",
        victim=PersonId("v"),
        grid=Grid(
            width=2,
            height=2,
            cells=tuple(
                Cell(position=Position(row=r, col=c), area=AreaId("a"), terrain=("wall",))
                for r in range(2)
                for c in range(2)
            ),
        ),
        areas=(Area(id=AreaId("a"), name="Room"),),
        objects=(
            GameObject(
                id=ObjectId("o"),
                kind="seat",
                code=1,
                position=Position(row=0, col=0),
                occupiable=True,
            ),
        ),
        people=(
            Person(id=PersonId("p"), name="Person", attributes={"sex": "male"}),
            Person(id=PersonId("v"), name="Victim", attributes={"sex": "female"}),
        ),
        clues=(Clue(id=ClueId("c"), text="A clue"), Clue(id=ClueId("d"), text="Another clue")),
    )


def document(expression: str, clue: str = "c") -> ConstraintSet:
    return ConstraintSet.model_validate_json(
        '{"constraints":[{"clue_id":"' + clue + '","expression":' + expression + "}]}"
    )


P = '{"kind":"person","id":"p"}'
V = '{"kind":"person","id":"v"}'
OBJ = '{"kind":"object","id":"o"}'
X = '{"kind":"variable","name":"x"}'
ZERO = '{"kind":"position","position":{"row":0,"col":0}}'
ONE = '{"kind":"position","position":{"row":1,"col":1}}'


@pytest.mark.parametrize(
    "expression",
    [
        '{"op":"area","target":' + P + ',"area":"a"}',
        '{"op":"same_area","left":' + P + ',"right":' + V + "}",
        '{"op":"on_object","target":' + P + ',"object":"o"}',
        '{"op":"equal","left":' + P + ',"right":' + OBJ + "}",
        '{"op":"attribute","target":' + P + ',"name":"sex","value":"male"}',
        '{"op":"object_kind","target":' + OBJ + ',"value":"seat"}',
        '{"op":"terrain","target":' + P + ',"value":"wall"}',
        '{"op":"direction","left":' + P + ',"right":' + V + ',"direction":"northwest"}',
        '{"op":"not","item":{"op":"equal","left":' + P + ',"right":' + V + "}}",
        '{"op":"all","items":[]}',
        '{"op":"any","items":[{"op":"all","items":[]}]}',
        '{"op":"unique","domain":"people","variable":"x","where":'
        '{"op":"attribute","target":' + X + ',"name":"sex","value":"male"}}',
        '{"op":"forall","domain":"people","variable":"x","where":'
        '{"op":"area","target":' + X + ',"area":"a"}}',
        '{"op":"exists","domain":"objects","variable":"x","where":'
        '{"op":"object_kind","target":' + X + ',"value":"seat"}}',
        '{"op":"adjacent","left":' + ZERO + ',"right":'
        '{"kind":"position","position":{"row":0,"col":1}}}',
        '{"op":"compare","left":{"op":"distance","left":'
        + ZERO
        + ',"right":'
        + ONE
        + '},"relation":"eq","right":{"op":"integer","value":2}}',
        '{"op":"compare","left":{"op":"distance","metric":"chebyshev","left":'
        + ZERO
        + ',"right":'
        + ONE
        + '},"relation":"eq","right":{"op":"integer","value":1}}',
        '{"op":"compare","left":{"op":"count","variable":"x","domain":"cells",'
        '"where":{"op":"terrain","target":' + X + ',"value":"wall"}},"relation":"eq",'
        '"right":{"op":"integer","value":4}}',
        '{"op":"compare","left":{"op":"arithmetic","operator":"subtract",'
        '"left":{"op":"coordinate","target":' + V + ',"axis":"row"},'
        '"right":{"op":"coordinate","target":' + P + ',"axis":"row"}},'
        '"relation":"eq","right":{"op":"integer","value":1}}',
    ],
)
def test_primitives(tiny: Puzzle, expression: str) -> None:
    constraints = document(expression)
    assert ConstraintSet.model_validate_json(constraints.model_dump_json()) == constraints
    validate_constraints(tiny, constraints)
    ctx = Context(tiny)
    solver = z3.Solver()
    solver.add(ctx.at(ctx.positions[PersonId("p")], Position(row=0, col=0)))
    solver.add(ctx.at(ctx.positions[PersonId("v")], Position(row=1, col=1)))
    solver.add(z3.Not(Compiler(ctx).predicate(constraints.constraints[0].expression)))
    assert solver.check() == z3.unsat


def test_outcomes_and_verification(tiny: Puzzle) -> None:
    assert solve(tiny, ConstraintSet(constraints=())).status == "multiple"
    clue = document('{"op":"on_object","target":' + P + ',"object":"o"}')
    result = solve(tiny, clue)
    assert result.status == "unique" and result.solution is not None
    assert verify(tiny, result.solution, clue)
    wrong = result.solution.model_copy(update={"murderer": PersonId("v")})
    assert not verify(tiny, wrong)
    inverse = document(
        '{"op":"not","item":{"op":"on_object","target":' + P + ',"object":"o"}}', "d"
    )
    conflict = solve(tiny, ConstraintSet(constraints=clue.constraints + inverse.constraints))
    assert conflict.status == "unsat" and set(conflict.conflicting_clues) == {"c", "d"}
    with patch("murdoku.solver.engine.z3.Solver.check", return_value=z3.unknown):
        assert solve(tiny, clue).status == "unknown"


@pytest.mark.parametrize(
    "expression",
    [
        '{"op":"area","target":{"kind":"person","id":"missing"},"area":"a"}',
        '{"op":"area","target":' + X + ',"area":"a"}',
        '{"op":"area","target":' + P + ',"area":"missing"}',
        '{"op":"on_object","target":' + P + ',"object":"missing"}',
        '{"op":"attribute","target":' + ZERO + ',"name":"sex","value":"male"}',
        '{"op":"exists","variable":"x","domain":"people","where":'
        '{"op":"exists","variable":"x","domain":"people","where":{"op":"all","items":[]}}}',
    ],
)
def test_semantic_errors(tiny: Puzzle, expression: str) -> None:
    with pytest.raises(ValueError):
        validate_constraints(tiny, document(expression))


def test_schema_and_invalid_structure() -> None:
    assert "discriminator" in str(ConstraintSet.model_json_schema())
    with pytest.raises(ValidationError):
        document('{"op":"execute","code":"anything"}')


def test_unknown_during_uniqueness(tiny: Puzzle) -> None:
    from murdoku.solver.engine import prepare

    constraints = ConstraintSet(constraints=())
    context, solver = prepare(tiny, constraints, 1000)
    assert solver.check() == z3.sat
    with (
        patch("murdoku.solver.engine.prepare", return_value=(context, solver)),
        patch("murdoku.solver.engine.z3.Solver.check", side_effect=[z3.sat, z3.unknown]),
    ):
        result = solve(tiny, constraints)
    assert result.status == "unknown" and result.solution is not None
    assert result.reason is not None and result.reason.startswith("Uniqueness:")


def test_empty_domain_counts(tiny: Puzzle) -> None:
    without_objects = tiny.model_copy(update={"objects": ()})
    constraints = document(
        '{"op":"compare","left":{"op":"count","variable":"x",'
        '"domain":"objects","where":{"op":"all","items":[]}},'
        '"relation":"eq","right":{"op":"integer","value":0}}'
    )
    assert solve(without_objects, constraints).status == "multiple"
    unique = document(
        '{"op":"unique","variable":"x","domain":"objects","where":{"op":"all","items":[]}}'
    )
    assert solve(without_objects, unique).status == "unsat"
