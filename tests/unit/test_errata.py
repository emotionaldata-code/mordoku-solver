from pathlib import Path

from murdoku.extraction.normalizer import normalize
from murdoku.extraction.raw import RAW_ADAPTER

FIXTURE = Path(__file__).parents[1] / "fixtures/raw/puzzle-the-zoo-expert.json"


def test_zoo_correction_preserves_original_codes_and_source_data() -> None:
    raw = RAW_ADAPTER.validate_json(FIXTURE.read_text())
    original = {name: fields.copy() for name, fields in raw.items()}
    puzzle = normalize(raw, "zoo")
    assert puzzle.source_corrections == ("zoo-water-print-map-v1",)
    bear = [cell for cell in puzzle.grid.cells if cell.area == "area_1"]
    assert len(bear) == 35
    assert all("floor_type:12" in cell.terrain and "water" not in cell.terrain for cell in bear)
    assert raw == original


def test_changed_map_does_not_receive_a_stale_correction() -> None:
    raw = RAW_ADAPTER.validate_json(FIXTURE.read_text())
    raw["GRID"]["floor_type_1"] = "10.000000"
    puzzle = normalize(raw, "zoo")
    assert puzzle.source_corrections == ()
    subroom = [cell for cell in puzzle.grid.cells if "subarea:area_11" in cell.terrain]
    assert subroom and all("water" in cell.terrain for cell in subroom)


def test_correction_fingerprint_ignores_every_answer_and_hint() -> None:
    raw = RAW_ADAPTER.validate_json(FIXTURE.read_text())
    expected = normalize(raw, "zoo")
    for fields in raw.values():
        for key in tuple(fields):
            if key == "murderer" or key.startswith(("letter_", "solution_", "player_hint_")):
                del fields[key]
    assert normalize(raw, "zoo") == expected
