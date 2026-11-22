"""Source-backed map corrections, guarded against changes to upstream geometry."""

from hashlib import sha256
from json import dumps

from murdoku.models import Grid

from .raw import RawPuzzle, modern

ZOO_MAP_DIGEST = "f428286ebbf47526b83d7682e0cab28c40cdeeb8977e24801aaba4bc68cb02a5"
ZOO_WATER_CORRECTION = "zoo-water-print-map-v1"


def correct_map_terrain(raw: RawPuzzle, grid: Grid) -> tuple[Grid, tuple[str, ...]]:
    """Match the official print map without reading answers or guessing a floor code.

    The black-and-white PDF's water glyphs exclude the entire Bear Habitat,
    whereas this legacy JSON labels both its ground and its subroom as water.
    See docs/extraction.md for the independent vector evidence and provenance.
    """
    if modern(raw):
        return grid, ()
    prefixes = ("room_code_", "room_objects_", "floor_type_", "room_subroom_")
    fields = {key: value for key, value in raw["GRID"].items() if key.startswith(prefixes)}
    fields.update({key: raw["PROPERTIES"][key] for key in ("grid_w", "grid_h")})
    digest = sha256(dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != ZOO_MAP_DIGEST:
        return grid, ()
    cells = tuple(
        cell.model_copy(update={"terrain": tuple(tag for tag in cell.terrain if tag != "water")})
        if cell.area == "area_1"
        else cell
        for cell in grid.cells
    )
    return grid.model_copy(update={"cells": cells}), (ZOO_WATER_CORRECTION,)
