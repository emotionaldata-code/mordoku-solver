# /// script
# requires-python = ">=3.12"
# dependencies = ["pymupdf>=1.26,<2"]
# ///
"""Match the official print edition's water vectors without reading pixels or answers."""

import argparse
import hashlib
import importlib
import json
from collections import Counter
from pathlib import Path
from typing import Protocol, TypedDict, cast

SOURCE_URL = "https://murdoku.com/pdf/the-zoo-bw.pdf"
SOURCE_SHA256 = "89ba76e14d8ba9811aeb92538544636be31ae9bd7538c7edf8dee84b3048f4d8"
TOLERANCE = 0.0001


class Point(Protocol):
    x: float
    y: float


class Rectangle(Protocol):
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    height: float


class Drawing(TypedDict):
    rect: Rectangle
    items: list[tuple[object, ...]]


type Word = tuple[float, float, float, float, str, int, int, int]


class Page(Protocol):
    def get_drawings(self) -> list[Drawing]: ...
    def get_text(self, option: str) -> list[Word]: ...
    def get_images(self, *, full: bool) -> list[tuple[int, ...]]: ...
    def get_image_rects(self, xref: int) -> list[Rectangle]: ...


class Document(Protocol):
    def __getitem__(self, index: int) -> Page: ...
    def close(self) -> None: ...


class PdfModule(Protocol):
    def open(self, filename: str) -> Document: ...


class Evidence(TypedDict):
    puzzle_id: str
    source_url: str
    source_sha256: str
    method: str
    tolerance: float
    legend_commands: dict[str, int]
    water_cells: list[tuple[int, int]]


def commands(drawing: Drawing) -> dict[str, int]:
    return dict(Counter(str(item[0]) for item in drawing["items"]))


def signature(drawing: Drawing) -> tuple[float, ...]:
    rect = drawing["rect"]
    values: list[float] = []
    for item in drawing["items"]:
        if item[0] not in {"c", "l"}:
            raise ValueError("Water glyph must contain only cubic curves and lines")
        for raw_point in item[1:]:
            point = cast(Point, raw_point)
            values.extend(((point.x - rect.x0) / rect.width, (point.y - rect.y0) / rect.height))
    return tuple(values)


def audit(path: Path) -> Evidence:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(
            "PDF differs from the documented source; re-audit before updating evidence"
        )
    # The protocol confines the third-party PDF boundary to the operations used here.
    pdf = cast(PdfModule, cast(object, importlib.import_module("pymupdf")))
    document = pdf.open(str(path))
    try:
        page = document[0]
        drawings = page.get_drawings()
        words = [word for word in page.get_text("words") if word[4].lower() == "water"]
        label = min(words, key=lambda word: word[1])
        center_x = (label[0] + label[2]) / 2
        candidates = [drawing for drawing in drawings if commands(drawing) == {"c": 112, "l": 29}]
        legend = min(
            candidates,
            key=lambda drawing: (
                abs((drawing["rect"].x0 + drawing["rect"].x1) / 2 - center_x)
                + abs(drawing["rect"].y1 - label[1])
            ),
        )
        if not (legend["rect"].y1 <= label[3] and legend["rect"].y0 >= label[1] - 35):
            raise ValueError("Could not associate the water legend with its vector glyph")
        reference = signature(legend)
        image_rects = [
            rect for entry in page.get_images(full=True) for rect in page.get_image_rects(entry[0])
        ]
        grid = max(image_rects, key=lambda rect: rect.width * rect.height)
        width, height = grid.width / 16, grid.height / 16
        cells: set[tuple[int, int]] = set()
        for drawing in candidates:
            if drawing is legend:
                continue
            if tuple(item[0] for item in drawing["items"]) != tuple(
                item[0] for item in legend["items"]
            ):
                continue
            points = signature(drawing)
            if len(points) != len(reference):
                continue
            if max(abs(a - b) for a, b in zip(points, reference, strict=True)) > TOLERANCE:
                continue
            rect = drawing["rect"]
            row = int(((rect.y0 + rect.y1) / 2 - grid.y0) // height)
            col = int(((rect.x0 + rect.x1) / 2 - grid.x0) // width)
            if 0 <= row < 16 and 0 <= col < 16:
                cells.add((row, col))
        if len(cells) != 30:
            raise ValueError(f"Expected 30 independently matched water tiles, found {len(cells)}")
        return Evidence(
            puzzle_id="puzzle-the-zoo-expert",
            source_url=SOURCE_URL,
            source_sha256=digest,
            method="Water legend vector geometry matched after per-axis bounding-box "
            "normalization; identical cubic/line command sequence, "
            "no pixels, OCR, or answer inputs.",
            tolerance=TOLERANCE,
            legend_commands=commands(legend),
            water_cells=sorted(cells),
        )
    finally:
        document.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Local copy of the official black-and-white PDF")
    args = parser.parse_args()
    print(json.dumps(audit(args.pdf), indent=2))


if __name__ == "__main__":
    main()
