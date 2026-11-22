# Constraint language

The DSL is a JSON AST. Export its complete discriminated JSON Schema with
`murdoku schema --output schema.json`; validate documents with
`murdoku validate puzzle.json constraints.json` before solving.
All nodes forbid extra fields. Coordinates are **zero-based**: `row` increases
southward and `col` eastward. IDs come from the normalized puzzle, never from
names guessed by the translator.

A document associates each expression with its original clue:

```json
{
  "constraints": [
    {
      "clue_id": "clue_person_0",
      "expression": {
        "op": "area",
        "target": {"kind": "person", "id": "char_0"},
        "area": "area_2"
      }
    }
  ]
}
```

Use the actual clue ID printed by `murdoku clues`; the example is illustrative.
Several constraints may reference the same clue. Their conjunction is tracked
under one label for unsatisfiable-core diagnostics.

## References

| `kind` | Fields | Meaning |
| --- | --- | --- |
| `person` | `id` | A named person's unknown location |
| `object` | `id` | An object's fixed location |
| `position` | `position: {row, col}` | A fixed map location |
| `variable` | `name` | A lexically bound entity |

Variables range over `people`, `cells`, or `objects`. They cannot shadow an
existing binding; references outside their quantifier scope are invalid.
`attribute` requires a person and `object_kind` an object.

## Predicates

| `op` | Fields | Meaning |
| --- | --- | --- |
| `area` | `target`, `area` | Location belongs to this area ID |
| `same_area` | `left`, `right` | Both locations belong to the same area |
| `on_object` | `target`, `object` | Location equals this object's location |
| `adjacent` | `left`, `right`, `same_area=true` | Manhattan distance 1; same area by default |
| `direction` | `left`, `right`, `direction` | Left is north/south/east/west or a diagonal of right |
| `equal` | `left`, `right` | Same identity for two people or two objects; otherwise same location |
| `attribute` | `target`, `name`, `value` | Person's normalized attribute equals value |
| `object_kind` | `target`, `value` | Object's normalized kind equals value |
| `terrain` | `target`, `value` | Location has this normalized terrain tag |
| `compare` | `left`, `relation`, `right` | Compare numeric expressions |
| `all`, `any` | `items` | Conjunction or disjunction |
| `not` | `item` | Negation |
| `exists`, `forall`, `unique` | `variable`, `domain`, `where` | Finite quantification; unique means exactly one |

Cardinal direction predicates constrain only their named axis. For instance
`north` means a smaller row, with no column restriction; `northwest` means
both a smaller row and a smaller column. For directly north, add equal columns.
To express exclusion, negate a predicate. An implication is `any` of the negated
premise and the conclusion. Empty `all`/`forall` are true; empty `any`/`exists`
are false.

## Numbers

| `op` | Fields | Meaning |
| --- | --- | --- |
| `integer` | `value` | Integer constant |
| `coordinate` | `target`, `axis: row/col` | Reference's row or column |
| `distance` | `left`, `right`, `metric` | Manhattan (default) or Chebyshev distance |
| `arithmetic` | `left`, `operator: add/subtract`, `right` | Integer arithmetic |
| `count` | `variable`, `domain`, `where` | Number of matching entities |

Comparison relations are `eq`, `ne`, `lt`, `le`, `gt`, `ge`.
A count of people in the same area **includes the subject**. Exclude that person
with `not equal` when translating "other people".

For example, adjacency to any tree is compositional:

```json
{
  "op": "exists",
  "variable": "tree",
  "domain": "objects",
  "where": {
    "op": "all",
    "items": [
      {"op": "object_kind", "target": {"kind": "variable", "name": "tree"}, "value": "tree"},
      {
        "op": "adjacent",
        "left": {"kind": "person", "id": "char_0"},
        "right": {"kind": "variable", "name": "tree"}
      }
    ]
  }
}
```

The fixture documents in `tests/fixtures/constraints` contain complete manual
translations of eleven public puzzles and examples of nested quantification,
counts, relative coordinates, terrain, and exclusions.

## Solving and verification

The solver always enforces valid occupiable cells, at most one person per row
and column (also on rectangular maps), and exactly one other person in the
victim's area. It determines the murderer from that placement, without reading
an official solution. A second solve blocks every placement in the first model
to establish uniqueness. `unknown` also covers an unfinished uniqueness proof;
its first solution, when present, remains a satisfying placement.

An unsatisfiable core identifies a conflicting subset of clue IDs, not
necessarily the smallest subset. Universal game rules are untracked; a map
inconsistent by itself can therefore produce an empty clue core.

`verify` without constraints checks universal rules and the murderer's identity.
Supply `--constraints` to verify the manual clue translation too. Verification
never claims that untranslated natural-language clues have been checked.
