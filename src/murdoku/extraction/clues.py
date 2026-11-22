"""Built-in English clues from the application's explicit code table."""

import re

from murdoku.models import Clue, ClueId

from .raw import RawPuzzle, integer

BUILTIN_CLUES: dict[int, str] = {
    1: "There was no empty room.",
    2: "There was exactly one empty room.",
    3: "There was exactly one person on a chair.",
    4: "There was exactly one person on a bed.",
    5: "There was one or many empty room(s).",
    6: "Nobody was in the water.",
    7: "There was exactly one person on a carpet.",
    8: "There were exactly two empty rooms.",
    9: "There were exactly two persons on a chair.",
    10: "There were exactly three persons on a chair.",
    11: "No suspect was in a room with another suspect of opposite gender.",
}


def general_clues(raw: RawPuzzle) -> tuple[Clue, ...]:
    data = {**raw["PROPERTIES"], **raw.get("GRID", {})}
    clues: list[Clue] = []
    for key in sorted(data):
        if not re.fullmatch(r"clue_\d+", key):
            continue
        code = integer(data[key])
        if code in BUILTIN_CLUES:
            clues.append(Clue(id=ClueId(f"general_builtin_{key[5:]}"), text=BUILTIN_CLUES[code]))
        elif code not in {0, 101, 102}:
            raise ValueError(f"Unknown general clue code: {code}")
    for i in range(1, 4):
        text = data.get(f"clue_custom_text{i}", "").strip()
        if text:
            clues.append(Clue(id=ClueId(f"general_{i}"), text=text))
    if not any(c.id in {f"general_{i}" for i in range(1, 4)} for c in clues):
        for i in range(10):
            text = data.get(f"general_clue_{i}", "").strip()
            if text:
                clues.append(Clue(id=ClueId(f"general_{i + 1}"), text=text))
    return tuple(clues)
