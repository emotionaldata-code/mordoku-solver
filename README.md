# Murdoku Solver

A Python solver for [Murdoku](https://murdoku.com), the murder mystery logic game.
Download the original puzzle data, translate its clues into a typed JSON constraint
language, and let Z3 find the placements and identify the murderer.

The solver checks uniqueness and reports conflicting clues when constraints are
unsatisfiable. It runs locally, without AI services. Clue interpretation is manual:
a human or an external agent supplies the constraints.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run murdoku --help
```

## Solve a puzzle

```bash
uv run murdoku fetch https://murdoku.com/play/puzzle-lake-fishing-medium \
  --output puzzle.json
uv run murdoku clues puzzle.json
uv run murdoku schema --output schema.json
```

Read the clues and [DSL reference](docs/dsl.md), then write `constraints.json`.
The repository includes manually translated examples in
[`tests/fixtures/constraints`](tests/fixtures/constraints).

```bash
uv run murdoku validate puzzle.json constraints.json
uv run murdoku solve puzzle.json constraints.json --output result.json
```

The result distinguishes `unique`, `multiple`, `unsat`, and `unknown`.
`--timeout-ms` sets the Z3 timeout for each satisfiability check. A result includes
its first solution when available; uniqueness requires a second check that blocks
the complete assignment. An unsatisfiable core identifies a conflicting subset
of clue identifiers, which need not be the smallest possible subset.

To verify a candidate, save the result's `solution` member as `solution.json`:

```bash
uv run murdoku verify puzzle.json solution.json --constraints constraints.json
```

Without `--constraints`, verification checks the map and universal game rules.
With it, verification also checks the translated clues. It does not compare with
the publisher's answer. A unique solution proves uniqueness for the supplied
constraints; it does not prove that the English clues were translated correctly.

Commands emit JSON. Invalid input produces a JSON error on stderr and exit code 2;
verification of an invalid candidate exits with code 1.

## How it works

- **Extraction:** HTTPX retrieves the original JSON. A deterministic normalizer
  handles modern and legacy layouts, including inverted legacy coordinates,
  decimal integer strings, water, and objects spanning several cells.
- **Models:** Pydantic validates puzzle structure and references. Coordinates are
  zero-based `row`/`col`; identifiers are explicit and stable.
- **DSL:** A discriminated AST supports spatial predicates, person attributes,
  numeric comparisons, counts, Boolean composition, and finite quantifiers.
  Each constraint carries its original clue identifier.
- **Solver:** Map encoding, universal rules, DSL compilation, and search are
  separate modules. Official answers and revealing hints are excluded from
  normalized puzzles and never enter the solver.

Object codes and occupancy follow the website's published implementation; unknown
codes fail explicitly. See [extraction notes](docs/extraction.md) for provenance and
format details. Appearance attributes preserve their original numeric codes rather
than assigning unverified descriptions.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Tests use checked-in JSON from eleven public puzzles, including every Expert map
in the catalog checked on November 22, 2026. They run offline. Integration tests
compare solver output with separately decoded official answers; those answers
are test ground truth only.

Source lives in `src/murdoku`, tests and fixtures in `tests`. No Python file may
exceed 250 lines. Z3's untyped dependency boundary uses a small local stub; the
application is checked with Pyright in strict mode.

### Public fixture results

| Puzzle | Result | Ground truth check |
| --- | --- | --- |
| Lake Fishing | Unique | Exact placements and murderer |
| The Movie Studio | Unique | Exact placements and murderer |
| The Hiking Trip | Unique | Exact placements and murderer |
| The Commercial Square | Unique | Exact placements and murderer |
| Sleeping with the Fishes | Unique | Exact placements and murderer |
| The Zoo | Unique, with documented map correction | Exact placements and murderer |
| The CEO's Office | Unique | Exact placements and murderer |
| Main Street | Unique | Exact placements and murderer |
| The Golf Course | Unique | Exact placements and murderer |
| Solitary Confinement | Unique, with manual map interpretation | Exact placements and murderer |
| Mystery Islands | Unique, with manual map interpretation | Exact placements and murderer |

All seven Expert maps passed the CLI workflow. The
[Expert validation report](docs/expert-validation.md) records the results and
translation details, including map metadata missing from normalized output and
the finite ownership translation used for The CEO's Office.

The Zoo's JSON assigns a water texture to the Bear Habitat, contrary to the
water symbols in the official printable map. A correction guarded by a fingerprint
of the map removes that semantic tag while retaining the original numeric codes.
Normalized output records `source_corrections`; answers and hints do not affect
the fingerprint. Without this correction, the literal export permits four layouts,
all identifying Jim. See the [source evidence and reproduction](docs/extraction.md).
