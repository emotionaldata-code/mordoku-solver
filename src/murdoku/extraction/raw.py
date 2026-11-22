"""Typed boundary for the site's string-valued JSON export."""

from decimal import Decimal, InvalidOperation

from pydantic import TypeAdapter

type RawPuzzle = dict[str, dict[str, str]]
RAW_ADAPTER = TypeAdapter(RawPuzzle)


def integer(value: str) -> int:
    try:
        number = Decimal(value)
        if not number.is_finite() or number != number.to_integral_value():
            raise ValueError(f"Expected an integer, received {value!r}")
        return int(number)
    except InvalidOperation as error:
        raise ValueError(f"Invalid numeric value: {value!r}") from error


def modern(raw: RawPuzzle) -> bool:
    return integer(raw["PROPERTIES"].get("puzzle_version", "1")) >= 2


def section(raw: RawPuzzle) -> dict[str, str]:
    return raw["CHARACTERS"] if modern(raw) else raw["GRID"]


def coordinate_key(prefix: str, row: int, col: int, recent: bool) -> str:
    return f"{prefix}_{row}_{col}" if recent else f"{prefix}_{col}_{row}"
