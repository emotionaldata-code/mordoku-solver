# Source normalization

The HTTP client reads the original English JSON from
`https://murdoku.com/play_puzzles/en/{puzzle_id}.json`; the catalog is available
at `https://murdoku.com/play_puzzles/_puzzleCatalog.json`. Fetch accepts public
HTTPS puzzle URLs on `murdoku.com`, validates the path, checks HTTP errors, and
validates the string-valued sections before normalization.

The six raw test fixtures are snapshots downloaded from those public resources.
They remain upstream data; their text and artwork belong to their original
owners. They contain answers, so the solver receives only normalized `Puzzle`
objects, never raw fixtures.

## Verified conventions

The site's public application module
[`puzzle-core-Cla4GAxx.js`](https://murdoku.com/play/assets/puzzle-core-Cla4GAxx.js),
retrieved November 22, 2026, defines the conventions used here:

- Version 2 stores cells in `CHARACTERS`, with suffixes `row_col`.
- Legacy exports store cells in `GRID`, with suffixes `col_row`.
- Coordinates exposed by this project are always zero-based `(row, col)`.
- Numeric strings such as `9.000000` are integral decimals, parsed without
  floating-point rounding. Fractional values are rejected for integer fields.
- Object catalog entries explicitly provide name and occupiability. Unknown
  codes fail with an error. Code zero denotes no cell object; border decorations
  with null occupiability are blocked when used as cell objects.
- Beds 6/119, rowboat 25, cars 21/22 and carriage 90 occupy two horizontal cells; beds
  7/120 occupy two vertical cells; bus 56 spans three horizontal cells; elephant
  54 occupies a two-by-two footprint. Expansion fills only previously empty cells.
- Subrooms share their parent logical area. Their original identifier survives
  as `subarea:area_N` terrain, and their own floor type is retained. This matters
  for water within animal habitats in the Zoo puzzle.
- Floor/texture codes 12 and 23 identify water; 11 identifies sand. Raw numeric
  floor and height tags are retained. Carpet occupancy is stored separately.
- Sex code 0 means male, 1 female. Other portrait properties retain canonical
  numeric codes; no names or meanings are guessed for appearance codes.
- A wall is a logical-area boundary or an outer border. `wall`, `wall:north`,
  `wall:south`, `wall:east`, and `wall:west` tags record these boundaries. `corner`
  means at least one vertical and one horizontal wall meet at the cell.

## Answer isolation

Normalization copies only explicit puzzle fields, clue text, map data and
portrait attributes. It excludes `murderer`, `solution_*`, `letter_*`,
`solution_text_*` and `player_hint_*` fields. The victim is identified from the
explicit English victim clue rather than by reading the answer.

`extraction.ground_truth.official_solution` exists solely to compare test results
with upstream answers. Modern answers use `solution_x/y`; legacy answers are
computed from `letter_xpos/ypos`, `grid_rx/ry`, and `cellsize`, following the web
application's conversion. Neither compilation nor solving imports that helper.

The normalizer supports the observed single-grid exports. It intentionally
rejects missing required coordinates, unknown object codes and ambiguous victim
identity instead of filling in inferred puzzle content.

## Legacy rowboat correction

The current web normalizer omits code 25 from its expansion list. We explicitly
expand the legacy rowboat horizontally by two cells. The renderer in
[`app-core-BEfE3huk.js`](https://murdoku.com/play/assets/app-core-BEfE3huk.js)
assigns `obj_rowboat.svg` exactly the same `scale:2.2`, `offsetX:5`, `offsetY:-20`,
`positionMode:"topLeft"` geometry as horizontal bed 6. Independently, the Sleeping
with the Fishes general clue describes a boat entirely inside two empty columns.
This is a supported correction to an upstream inconsistency, not a rule inferred
from the official placements. A regression test checks anchor expansion directly.

## Verified Zoo terrain correction

The Zoo export incorrectly marks the entire Bear Habitat, including subroom 11,
as water through `floor_type_1` and `floor_type_11`, both `12.000000`. The general
texture catalog alone cannot recover the intended map. Independent evidence
comes from the official [black-and-white puzzle PDF](https://murdoku.com/pdf/the-zoo-bw.pdf),
which contains the puzzle and legend, without solution placements.

The water legend's base vector path consists of 112 cubic curves and 29 lines.
After normalizing each coordinate to its bounding box, exactly 30 map paths have
identical command sequences and coordinates within `0.0001`. The largest observed
coordinate difference is less than `0.000068`. Their centers map to every cell in
raw areas 2 (17 cells), 10 (5), 12 (4), and 13 (4). Neither raw area 1 nor 11
contains a matching water glyph. This comparison reads PDF drawing instructions
and text coordinates; it uses no rendered pixels, OCR, computer vision or answers.
The color PDF flattens terrain into a raster image; the black-and-white edition
preserves these additional vector water tiles.

The committed evidence manifest is
[`tests/fixtures/map_evidence/puzzle-the-zoo-expert-water.json`](../tests/fixtures/map_evidence/puzzle-the-zoo-expert-water.json).
It lists the 30 independently recovered cells, method, tolerance and source hash.
The PDF SHA-256 is
`89ba76e14d8ba9811aeb92538544636be31ae9bd7538c7edf8dee84b3048f4d8`.

Normalization applies correction `zoo-water-print-map-v1`: remove only the semantic
`water` tag from logical area 1, including its subroom 11. Original
`floor_type:12` tags remain available for provenance; no replacement grass code
is invented. `Puzzle.source_corrections` records the applied correction.

The correction is guarded by SHA-256
`f428286ebbf47526b83d7682e0cab28c40cdeeb8977e24801aaba4bc68cb02a5`
of canonical JSON containing only `GRID` fields with prefixes `room_code_`,
`room_objects_`, `floor_type_`, `room_subroom_`, plus `PROPERTIES.grid_w` and
`PROPERTIES.grid_h`. Canonical serialization sorts keys and uses separators
`(',', ':')`. Answers, hints, character placements and clue translations do not
participate in the guard. Changed upstream map data does not receive this
correction until re-audited.

Reproduce the proof independently, with Python 3.12 and `uv`:

```bash
curl -fsSL https://murdoku.com/pdf/the-zoo-bw.pdf -o /tmp/the-zoo-bw.pdf
uv run --script scripts/audit_zoo_water.py /tmp/the-zoo-bw.pdf > /tmp/zoo-water.json
diff -u tests/fixtures/map_evidence/puzzle-the-zoo-expert-water.json /tmp/zoo-water.json
```

The optional audit script installs PyMuPDF in an isolated environment; normal
fetching, solving and tests do not require a PDF dependency or download. The
script checks the source hash, locates the water legend by extracted text and
vector geometry, derives grid bounds from the map image placement, and matches
path coordinates without reading that image's pixels. It does not accept raw
puzzle JSON or official answers as input.
