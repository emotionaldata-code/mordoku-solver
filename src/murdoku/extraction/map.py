"""Normalize map coordinates and expand the web app's multi-cell objects."""

from murdoku.models import Area, AreaId, Cell, GameObject, Grid, ObjectId, Position

from .object_catalog import object_spec
from .raw import RawPuzzle, coordinate_key, integer, modern, section


def object_codes(raw: RawPuzzle, width: int, height: int) -> dict[tuple[int, int], int]:
    data, recent = section(raw), modern(raw)
    codes = {
        (r, c): integer(data[coordinate_key("room_objects", r, c, recent)])
        for r in range(height)
        for c in range(width)
    }
    additions: list[tuple[int, int, int]] = []
    for (r, c), code in codes.items():
        offsets = [(0, 0)]
        # Rowboat 25 uses the same horizontal footprint as bed 6 in the renderer.
        if code in {6, 119, 21, 22, 25, 90}:
            offsets = [(0, 1)]
        elif code == 56:
            offsets = [(0, 1), (0, 2)]
        elif code in {7, 120}:
            offsets = [(1, 0)]
        elif code == 54:
            offsets = [(0, 1), (1, 0), (1, 1)]
        additions.extend((r + dr, c + dc, code) for dr, dc in offsets)
    for r, c, code in additions:
        if 0 <= r < height and 0 <= c < width and codes[r, c] == 0:
            codes[r, c] = code
    return codes


def main_area(data: dict[str, str], area: int) -> int:
    if integer(data.get(f"room_subroom_{area}", "0")) == 1:
        return integer(data[f"room_subroom_mainroom_{area}"])
    return area


def boundaries(
    data: dict[str, str], r: int, c: int, width: int, height: int, recent: bool, area: int
) -> tuple[str, ...]:
    walls: set[str] = set()
    for dr, dc, direction in ((-1, 0, "north"), (1, 0, "south"), (0, -1, "west"), (0, 1, "east")):
        nr, nc = r + dr, c + dc
        if not (0 <= nr < height and 0 <= nc < width):
            walls.add(direction)
        else:
            neighbor = integer(data[coordinate_key("room_code", nr, nc, recent)])
            if main_area(data, neighbor) != area:
                walls.add(direction)
    tags = [f"wall:{side}" for side in sorted(walls)]
    if walls:
        tags.append("wall")
    if walls & {"north", "south"} and walls & {"west", "east"}:
        tags.append("corner")
    return tuple(tags)


def normalize_map(raw: RawPuzzle) -> tuple[Grid, tuple[Area, ...], tuple[GameObject, ...]]:
    props, data, recent = raw["PROPERTIES"], section(raw), modern(raw)
    width, height = integer(props["grid_w"]), integer(props["grid_h"])
    if not 1 <= width <= 100 or not 1 <= height <= 100:
        raise ValueError("Grid dimensions outside supported range 1..100")
    codes = object_codes(raw, width, height)
    cells: list[Cell] = []
    objects: list[GameObject] = []
    area_ids: set[int] = set()
    for r in range(height):
        for c in range(width):
            position = Position(row=r, col=c)
            area = integer(data[coordinate_key("room_code", r, c, recent)])
            effective_area = main_area(data, area)
            area_ids.add(effective_area)
            code = codes[r, c]
            spec = object_spec(code) if code else None
            if spec:
                objects.append(
                    GameObject(
                        id=ObjectId(f"object_{r}_{c}"),
                        kind=spec.kind,
                        position=position,
                        occupiable=spec.occupiable,
                        code=code,
                    )
                )
            terrain = list(boundaries(data, r, c, width, height, recent, effective_area))
            if effective_area != area:
                terrain.append(f"subarea:area_{area}")
            for prefix in ("floor_type", "room_texture", "floor_height", "room_height"):
                key = f"{prefix}_{area}"
                if key in data:
                    value = integer(data[key])
                    terrain.append(f"{prefix}:{value}")
                    if prefix in {"floor_type", "room_texture"} and value in {12, 23}:
                        terrain.append("water")
                    if prefix in {"floor_type", "room_texture"} and value == 11:
                        terrain.append("sand")
            carpet_key = coordinate_key("carpet_objects", r, c, recent)
            if integer(data.get(carpet_key, "0")) == 5:
                terrain.append("carpet")
            cells.append(
                Cell(
                    position=position,
                    area=AreaId(f"area_{effective_area}"),
                    occupiable=spec.occupiable if spec else True,
                    terrain=tuple(terrain),
                )
            )
    areas = tuple(
        Area(id=AreaId(f"area_{i}"), name=data[f"room_name_{i}"]) for i in sorted(area_ids)
    )
    return Grid(width=width, height=height, cells=tuple(cells)), areas, tuple(objects)
