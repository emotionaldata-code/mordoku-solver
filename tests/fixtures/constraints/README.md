# Manually translated constraints

These eleven JSON files translate the original English clues into the typed DSL.
They use normalized map identifiers and zero-based coordinates. Individual
constraints retain `clue_person_N`; general constraints retain `general_N`.
Victim clues are enforced by the universal crime-scene rule.

Translations were written from clue text and map metadata. No official placement,
murderer, hint, or solution text was used as a constraint. The integration test
opens the separate ground-truth adapter only after solving.

Specific conventions:

- Exactly N rows/columns apart compares coordinate differences, without requiring
  a shared column/row. Ordinary directions likewise impose no alignment.
- "With" means the same logical area; "alone with" requires an area count of two.
- The Hiking Trip cap and glasses clues select portrait codes `hat=3` and
  `accessory=1`. These are Aubrey's and Clark's own attributes: their clues place
  them in the respective areas and say everyone there shares that appearance.
  This is a clue-specific inference, not a global invented appearance catalog.
- Empty rows/columns follow from rectangular base rules; their clue constraints
  specify bears in empty rows and the full two-column footprint of an empty boat.
- Store/set groups are explicitly enumerated from map names. Walls and corners
  use the normalized spatial tags.

All eleven fixtures resolve uniquely to the official answer. The Zoo requires the
[documented terrain correction](../../../docs/extraction.md#verified-zoo-terrain-correction),
derived from the official unsolved printable map. The clue constraints themselves
remain unchanged; the original JSON terrain would admit four layouts.

The five additional Expert translations were produced through the CLI without
answer access. See the [Expert audit](../../../docs/expert-validation.md) for
ownership scopes, manually interpreted map labels, door frontage, and the
separate official-answer comparison.
