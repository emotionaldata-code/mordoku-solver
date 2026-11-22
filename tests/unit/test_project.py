from pathlib import Path


def test_python_files_stay_within_line_limit() -> None:
    root = Path(__file__).parents[2]
    for folder in ("src", "tests", "typings", "scripts"):
        for path in (root / folder).rglob("*"):
            if path.suffix not in {".py", ".pyi"}:
                continue
            assert len(path.read_text().splitlines()) <= 250, str(path)
