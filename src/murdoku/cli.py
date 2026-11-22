"""JSON-first command line interface for external constraint authors."""

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Annotated

import httpx
import typer
from pydantic import BaseModel

from murdoku.dsl.expressions import ConstraintSet
from murdoku.dsl.validation import validate_constraints
from murdoku.extraction.client import fetch as download
from murdoku.extraction.client import puzzle_id
from murdoku.extraction.normalizer import normalize
from murdoku.models import Clue, Puzzle, Solution
from murdoku.solver.engine import solve, verify

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def guarded[**P](function: Callable[P, None]) -> Callable[P, None]:
    @wraps(function)
    def run(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            function(*args, **kwargs)
        except (ValueError, OSError, httpx.HTTPError) as exc:
            typer.echo(Error(error=str(exc)).model_dump_json(), err=True)
            raise typer.Exit(2) from exc

    return run


class Error(BaseModel):
    error: str


class ValidationResult(BaseModel):
    valid: bool


def load[T: BaseModel](path: Path, model: type[T]) -> T:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def emit(model: BaseModel, output: Path | None = None) -> None:
    content = model.model_dump_json(indent=2) + "\n"
    if output is None:
        typer.echo(content, nl=False)
    else:
        output.write_text(content, encoding="utf-8")


@app.command()
@guarded
def fetch(url: str, output: Annotated[Path, typer.Option("--output", "-o")]) -> None:
    """Download and normalize a puzzle without official positions or hints."""
    emit(normalize(download(url), puzzle_id(url)), output)


@app.command()
@guarded
def clues(puzzle: Path) -> None:
    """List original clue identifiers and text as JSON."""

    class Clues(BaseModel):
        clues: tuple[Clue, ...]

    emit(Clues(clues=load(puzzle, Puzzle).clues))


@app.command()
@guarded
def schema(output: Annotated[Path | None, typer.Option("--output", "-o")] = None) -> None:
    """Export the ConstraintSet JSON Schema."""
    import json

    content = json.dumps(ConstraintSet.model_json_schema(), indent=2) + "\n"
    if output is None:
        typer.echo(content, nl=False)
    else:
        output.write_text(content, encoding="utf-8")


@app.command()
@guarded
def validate(puzzle: Path, constraints: Path) -> None:
    """Check DSL syntax, references, and quantified variable scopes."""
    validate_constraints(load(puzzle, Puzzle), load(constraints, ConstraintSet))
    emit(ValidationResult(valid=True))


@app.command(name="solve")
@guarded
def solve_command(
    puzzle: Path,
    constraints: Path,
    timeout_ms: Annotated[int, typer.Option(min=1)] = 10000,
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Solve and check uniqueness; output includes status and diagnostics."""
    emit(solve(load(puzzle, Puzzle), load(constraints, ConstraintSet), timeout_ms), output)


@app.command(name="verify")
@guarded
def verify_command(
    puzzle: Path,
    solution: Path,
    constraints: Annotated[Path | None, typer.Option("--constraints")] = None,
) -> None:
    """Verify a solution against map/game rules and optionally translated clues."""
    rules = load(constraints, ConstraintSet) if constraints is not None else None
    valid = verify(load(puzzle, Puzzle), load(solution, Solution), rules)
    emit(ValidationResult(valid=valid))
    if not valid:
        raise typer.Exit(1)
