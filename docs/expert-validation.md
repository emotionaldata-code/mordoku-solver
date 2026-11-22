# Expert map validation

The [public catalog](https://murdoku.com/play_puzzles/_puzzleCatalog.json) contained
seven Expert puzzles on November 22, 2026, its highest difficulty. All seven
resolved uniquely through the CLI, with exact
agreement on every placement and the murderer in the separate official answer.

| Catalog puzzle | Grid | Covered clues, excluding victim | Murderer | Result |
| --- | --- | --- | --- | --- |
| The CEO's Office | 16x16 | 17/17 | Carter | Unique, exact match |
| Main Street | 12x12 | 11/11 | Felicia | Unique, exact match |
| The Movie Studio | 16x16 | 16/16 | Natalia | Unique, exact match |
| The Zoo | 16x16 | 17/17 | Jim | Unique, exact match |
| The Golf Course | 16x16 | 17/17 | Breta | Unique, exact match |
| Solitary Confinement | 16x16 | 16/16 | Emilio | Unique, exact match |
| Mystery Islands | 16x16 | 16/16 | Miguel | Unique, exact match |

Three external agents translated the five new maps. They read normalized maps
and clues, authored DSL fixtures, and ran CLI validation, solving, and verification.
Movie Studio and Zoo reused existing clue translations against fresh CLI fetches.
The application code was unchanged. The parent compared sealed official answers
only after the translations produced their solutions. Answers and revealing hints
were never solver inputs.

The [machine-readable report](../reports/expert-validation-2026-11-22.json) records
the catalog, source and constraint hashes, coverage, and comparison results.
Fixtures are checked into `tests/fixtures/raw` and `tests/fixtures/constraints`;
all eleven fixture puzzles are included in offline integration tests.

Validation completed with 80 passing tests, clean Ruff lint and format checks,
and zero Pyright errors or warnings.

## Reproduction

For any puzzle identifier in the report:

```bash
puzzle=puzzle-the-ceos-office-expert
uv run murdoku fetch "https://murdoku.com/play/$puzzle" --output /tmp/puzzle.json
uv run murdoku clues /tmp/puzzle.json
uv run murdoku validate /tmp/puzzle.json "tests/fixtures/constraints/$puzzle.json"
uv run murdoku solve /tmp/puzzle.json "tests/fixtures/constraints/$puzzle.json" \
  --timeout-ms 120000 --output /tmp/result.json
uv run python -c 'import json; from pathlib import Path; r=json.loads(Path("/tmp/result.json").read_text()); Path("/tmp/solution.json").write_text(json.dumps(r["solution"]))'
uv run murdoku verify /tmp/puzzle.json /tmp/solution.json \
  --constraints "tests/fixtures/constraints/$puzzle.json"
```

`uv run pytest tests/integration/test_real_puzzles.py` independently checks the
stored fixtures against official ground truth after solving.

## Translation details and current limits

**The CEO's Office:** ownership is an unknown role, not a chair attribute.
The clues exclude six people from ownership, leaving four possible female owners
and six possible male owners. The DSL enumerates all 60 unordered sets containing
one woman and four men. Every set puts its members in distinct offices and applies
the owner-dependent spatial clues. Visitors remain allowed. This is a finite
expansion of the existential role selection, with no owner selected in advance.
The shared expression is repeated under its six dependent clue IDs because the
DSL has no cross-constraint role binding. Compact JSON keeps this fixture at
approximately 2.2 MB. Five nested person quantifiers were abandoned during slow
compilation; the final finite-set translation completed successfully.

**Solitary Confinement:** normalized area names are unreliable here because
positioned source labels do not necessarily share the numeric IDs of the regions
they name. Independent embedded text coordinates in the official unsolved PDF
identify Cell A-E as areas 2, 3, 17, 0, 1 and Reception as area 13. The normalizer
also omits boundary door/window metadata. The published clue highlighter defines
"in front" using both incident cells of every positive boundary opening; values
1 and 2 both qualify. The DSL translates these 17 map edges into their complete
33-cell frontage set, rather than inferring any person's position. The
[map evidence](../tests/fixtures/map_evidence/puzzle-solitary-confinement-expert.json)
records source hashes, PDF label coordinates and the opening list. Every clue,
including the door clue, is included in the final solve.

**Mystery Islands:** the same label-ID mismatch names the empty southeastern
island `Study Room` and the desert island `Cell E` in normalized output. The
translation uses their actual regions, areas 6 and 11, verified from source map
label anchors and physical map contents. Source title metadata also calls this
map `The Super Island`; the report retains both source and catalog titles.

**The Zoo:** the existing fingerprint-guarded terrain correction remains active.
Its independent unsolved-map evidence is documented in [extraction notes](extraction.md).

These successful solves do not remove the extraction limitations above. Solitary
and Mystery required map interpretation beyond the current normalized names;
door frontage was translated from original map metadata. No new source erratum
or solver patch was introduced to obtain these results.
