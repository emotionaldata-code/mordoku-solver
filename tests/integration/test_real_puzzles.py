"""Solve independently translated clues, then compare with sealed official answers."""

from pathlib import Path

import pytest

from murdoku.dsl.expressions import ConstraintSet
from murdoku.extraction.ground_truth import official_solution
from murdoku.extraction.normalizer import normalize
from murdoku.extraction.raw import RAW_ADAPTER
from murdoku.solver.engine import solve, verify

FIXTURES = Path(__file__).parents[1] / "fixtures"
PUZZLES = (
    "lake-fishing-medium",
    "the-movie-studio-expert",
    "the-ceos-office-expert",
    "solitary-confinement-expert",
    "main-street-expert",
    "the-golf-expert",
    "mystery-islands-expert",
    "the-zoo-expert",
    "the-hiking-trip-hard",
    "the-commercial-square-hard",
    "sleeping-with-the-fishes-hard",
)


@pytest.mark.parametrize("name", PUZZLES)
def test_official_ground_truth(name: str) -> None:
    puzzle_id = f"puzzle-{name}"
    raw = RAW_ADAPTER.validate_json((FIXTURES / "raw" / f"{puzzle_id}.json").read_text())
    puzzle = normalize(raw, puzzle_id)
    constraints = ConstraintSet.model_validate_json(
        (FIXTURES / "constraints" / f"{puzzle_id}.json").read_text()
    )
    assert {c.clue_id for c in constraints.constraints} == {
        c.id for c in puzzle.clues if c.person != puzzle.victim
    }
    result = solve(puzzle, constraints, timeout_ms=30000)
    expected = official_solution(raw)
    assert verify(puzzle, expected, constraints)
    assert result.status == "unique", result.model_dump_json()
    assert result.solution == expected
