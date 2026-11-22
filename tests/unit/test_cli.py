import json
from pathlib import Path

from typer.testing import CliRunner

from murdoku.cli import app
from murdoku.extraction.normalizer import normalize
from murdoku.extraction.raw import RAW_ADAPTER

runner = CliRunner()
RAW = Path(__file__).parents[1] / "fixtures/raw/puzzle-lake-fishing-medium.json"


def write_puzzle(tmp_path: Path) -> Path:
    path = tmp_path / "puzzle.json"
    puzzle = normalize(RAW_ADAPTER.validate_json(RAW.read_bytes()), RAW.stem)
    path.write_text(puzzle.model_dump_json(), encoding="utf-8")
    return path


def test_schema_is_json(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    result = runner.invoke(app, ["schema", "--output", str(path)])
    assert result.exit_code == 0, result.output
    assert '"discriminator"' in path.read_text()
    json.loads(path.read_text())


def test_clues_include_text_and_ids(tmp_path: Path) -> None:
    path = write_puzzle(tmp_path)
    result = runner.invoke(app, ["clues", str(path)])
    assert result.exit_code == 0, result.output
    assert '"clue_person_0"' in result.output
    assert "He was on a boat." in result.output
    assert "solution_x" not in result.output


def test_invalid_input_is_machine_readable(tmp_path: Path) -> None:
    path = write_puzzle(tmp_path)
    constraints = tmp_path / "constraints.json"
    constraints.write_text('{"constraints": [{"bad": true}]}')
    result = runner.invoke(app, ["validate", str(path), str(constraints)])
    assert result.exit_code == 2
    assert '"error"' in result.output


def test_fetch_rejects_foreign_hosts(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["fetch", "https://example.com/play/puzzle-a", "--output", str(tmp_path / "p.json")]
    )
    assert result.exit_code == 2
    assert '"error"' in result.output
