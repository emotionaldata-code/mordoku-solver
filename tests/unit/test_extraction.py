from pathlib import Path

import httpx
import pytest

from murdoku.extraction.client import fetch, puzzle_id
from murdoku.extraction.ground_truth import official_solution
from murdoku.extraction.normalizer import normalize
from murdoku.extraction.object_catalog import object_spec
from murdoku.extraction.raw import RAW_ADAPTER, integer

FIXTURES = Path(__file__).parents[1] / "fixtures" / "raw"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_real_formats_are_deterministic_and_answers_are_separate(path: Path) -> None:
    raw = RAW_ADAPTER.validate_json(path.read_text())
    puzzle = normalize(raw, path.stem)
    assert puzzle == normalize(raw, path.stem)
    assert len(puzzle.people) == integer(raw["PROPERTIES"]["total_char"])
    assert len(puzzle.grid.cells) == puzzle.grid.width * puzzle.grid.height
    answer = official_solution(raw)
    cells = {c.position: c for c in puzzle.grid.cells}
    assert all(cells[p.position].occupiable for p in answer.placements)
    serialized = puzzle.model_dump_json()
    assert "solution_x" not in serialized
    assert "letter_xpos" not in serialized
    assert "player_hint" not in serialized
    assert "murderer" not in type(puzzle).model_fields


def test_legacy_rectangular_coordinates_and_decimal_numbers() -> None:
    raw = RAW_ADAPTER.validate_json(
        (FIXTURES / "puzzle-sleeping-with-the-fishes-hard.json").read_text()
    )
    puzzle = normalize(raw, "fish")
    assert (puzzle.grid.width, puzzle.grid.height) == (11, 9)
    corner = next(o for o in puzzle.objects if (o.position.row, o.position.col) == (8, 10))
    assert corner.kind == "shelf"
    assert integer("00009.000000") == 9
    with pytest.raises(ValueError):
        integer("1.5")


def test_modern_coordinate_order() -> None:
    raw = RAW_ADAPTER.validate_json((FIXTURES / "puzzle-lake-fishing-medium.json").read_text())
    puzzle = normalize(raw, "lake")
    obj = next(o for o in puzzle.objects if (o.position.row, o.position.col) == (0, 4))
    assert obj.kind == "boulder"
    assert not obj.occupiable


def test_water_subrooms_keep_terrain_but_share_logical_area() -> None:
    raw = RAW_ADAPTER.validate_json((FIXTURES / "puzzle-the-zoo-expert.json").read_text())
    puzzle = normalize(raw, "zoo")
    subroom = [c for c in puzzle.grid.cells if "subarea:area_10" in c.terrain]
    assert subroom
    assert all(c.area == "area_6" and "water" in c.terrain for c in subroom)


def test_catalog_rejects_unverified_codes() -> None:
    assert object_spec(76).kind == "boat"
    assert object_spec(76).occupiable
    with pytest.raises(ValueError, match="Unsupported object"):
        object_spec(99999)


@pytest.mark.parametrize(
    "url",
    [
        "http://murdoku.com/play/puzzle-x",
        "https://evil.example/play/puzzle-x",
        "https://murdoku.com/play/../secrets",
        "https://murdoku.com/play/puzzle-x?redirect=1",
    ],
)
def test_url_validation(url: str) -> None:
    with pytest.raises(ValueError):
        puzzle_id(url)


def test_fetch_uses_json_resource() -> None:
    payload = (FIXTURES / "puzzle-lake-fishing-medium.json").read_bytes()

    def respond(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == (
            "https://murdoku.com/play_puzzles/en/puzzle-lake-fishing-medium.json"
        )
        return httpx.Response(200, content=payload)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        raw = fetch("https://murdoku.com/play/puzzle-lake-fishing-medium", client=client)
    assert integer(raw["PROPERTIES"]["grid_w"]) == 8


def test_builtin_general_clues_have_verified_text_and_identifiers() -> None:
    raw = RAW_ADAPTER.validate_json((FIXTURES / "puzzle-lake-fishing-medium.json").read_text())
    raw["PROPERTIES"]["clue_0"] = "6.000000"
    puzzle = normalize(raw, "lake")
    builtin = next(c for c in puzzle.clues if c.id == "general_builtin_0")
    assert builtin.text == "Nobody was in the water."
    raw["PROPERTIES"]["clue_0"] = "999"
    with pytest.raises(ValueError, match="Unknown general clue code"):
        normalize(raw, "lake")


def test_legacy_rowboat_expands_horizontal_renderer_footprint() -> None:
    raw = RAW_ADAPTER.validate_json(
        (FIXTURES / "puzzle-sleeping-with-the-fishes-hard.json").read_text()
    )
    assert integer(raw["GRID"]["room_objects_2_0"]) == 25
    assert integer(raw["GRID"]["room_objects_3_0"]) == 0
    puzzle = normalize(raw, "boats")
    objects = {(o.position.row, o.position.col): o for o in puzzle.objects}
    assert objects[0, 2].kind == objects[0, 3].kind == "rowboat"
    assert objects[0, 3].occupiable


@pytest.mark.parametrize("section", ["PROPERTIES", "CHARACTERS", "GRID"])
def test_missing_required_sections_are_validation_errors(section: str) -> None:
    raw = RAW_ADAPTER.validate_json(
        (FIXTURES / "puzzle-sleeping-with-the-fishes-hard.json").read_text()
    )
    del raw[section]
    with pytest.raises(ValueError, match="Missing required puzzle field or section"):
        normalize(raw, "broken")


def test_missing_cell_and_multiple_grids_fail_clearly() -> None:
    raw = RAW_ADAPTER.validate_json((FIXTURES / "puzzle-lake-fishing-medium.json").read_text())
    raw["PROPERTIES"]["total_grids"] = "2"
    with pytest.raises(ValueError, match="Only single-grid"):
        normalize(raw, "broken")
    raw["PROPERTIES"]["total_grids"] = "1"
    del raw["CHARACTERS"]["room_code_0_0"]
    with pytest.raises(ValueError, match="room_code_0_0"):
        normalize(raw, "broken")


def test_cli_reports_malformed_export_as_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import json

    from typer.testing import CliRunner

    import murdoku.cli as cli
    from murdoku.extraction.raw import RawPuzzle

    def malformed(_url: str) -> RawPuzzle:
        return {"PROPERTIES": {"total_grids": "1"}}

    monkeypatch.setattr(cli, "download", malformed)
    result = CliRunner().invoke(
        cli.app,
        [
            "fetch",
            "https://murdoku.com/play/puzzle-broken",
            "--output",
            str(tmp_path / "puzzle.json"),
        ],
    )
    assert result.exit_code == 2
    assert "Missing required puzzle field or section" in result.stderr
    assert "Traceback" not in result.stderr
    assert json.loads(result.stderr)["error"]
    assert not (tmp_path / "puzzle.json").exists()
