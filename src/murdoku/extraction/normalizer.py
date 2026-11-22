"""Deterministic normalization with a strict boundary against solution leaks."""

import re
from decimal import Decimal

from murdoku.models import Clue, ClueId, Person, PersonId, Puzzle

from .clues import general_clues
from .errata import correct_map_terrain
from .map import normalize_map
from .raw import RawPuzzle, integer, section


def person_indices(raw: RawPuzzle) -> tuple[int, ...]:
    indices = sorted(
        int(k.removeprefix("char_name_"))
        for k in raw["CHARACTERS"]
        if re.fullmatch(r"char_name_\d+", k)
    )
    count = integer(raw["PROPERTIES"]["total_char"])
    if len(indices) != count:
        raise ValueError("Character count disagrees with named characters")
    return tuple(indices)


def canonical(value: str) -> str:
    """Strip decimal integer serialization without guessing attribute semantics."""
    if re.fullmatch(r"-?\d+(?:\.0+)?", value):
        return str(int(Decimal(value)))
    return value


def normalize(raw: RawPuzzle, puzzle_id: str) -> Puzzle:
    """Normalize required export fields, reporting missing data at the boundary."""
    try:
        return _normalize(raw, puzzle_id)
    except KeyError as error:
        raise ValueError(f"Missing required puzzle field or section: {error.args[0]}") from error


def _normalize(raw: RawPuzzle, puzzle_id: str) -> Puzzle:
    if integer(raw["PROPERTIES"].get("total_grids", "1")) != 1:
        raise ValueError("Only single-grid puzzle exports are supported")
    grid, areas, objects = normalize_map(raw)
    grid, source_corrections = correct_map_terrain(raw, grid)
    chars = raw["CHARACTERS"]
    people: list[Person] = []
    clues: list[Clue] = []
    victims: list[PersonId] = []
    fields = (
        "body",
        "skincolor",
        "hair",
        "haircolor",
        "facial",
        "clothes",
        "clothescolor",
        "hat",
        "accessory",
        "theme",
    )
    for i in person_indices(raw):
        pid = PersonId(f"char_{i}")
        attributes = {
            field: canonical(chars[f"char_{field}_{i}"])
            for field in fields
            if f"char_{field}_{i}" in chars
        }
        sex = integer(chars[f"char_sex_{i}"])
        if sex not in {0, 1}:
            raise ValueError(f"Unknown sex code: {sex}")
        attributes["sex"] = "female" if sex == 1 else "male"
        people.append(Person(id=pid, name=chars[f"char_name_{i}"], attributes=attributes))
        text = " ".join(
            chars.get(f"char_{part}_en_{i}", "").strip() for part in ("quote", "subquote")
        ).strip()
        if not text:
            raise ValueError(f"Missing English clue for {pid}")
        clues.append(Clue(id=ClueId(f"clue_person_{i}"), text=text, person=pid))
        if text.lower().startswith("the victim."):
            victims.append(pid)
    if len(victims) != 1:
        raise ValueError("Expected exactly one explicit victim clue")
    clues.extend(general_clues(raw))
    title = section(raw).get("title_en_", puzzle_id)
    return Puzzle(
        id=puzzle_id,
        title=title,
        grid=grid,
        areas=areas,
        objects=objects,
        people=tuple(people),
        victim=victims[0],
        clues=tuple(clues),
        source_corrections=source_corrections,
    )
