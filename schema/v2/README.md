# Per-object curation schema v2

Every file under `objects/` is a complete curation document for exactly one
canonical target. Its filename stem must match its lowercase `id`, and no two
documents may use the same `target_id`.

A document may combine these arrays:

- `geometries`: complete atomic ellipse corrections, including provenance and
  optional preferred-render selection;
- `outlines`: exceptional remappings or policy changes for upstream outline
  files that normal catalog ingestion cannot infer;
- `relations`: typed identity and hierarchy relationships;
- `selections`: explicit preferred identity, position, geometry, photometry,
  or classification decisions;
- `evidence`: structured document-level sources inherited by its decisions.

Each decision can also carry `notes` and its own nested `evidence`. Evidence
has optional `kind`, `citation`, `url`, and multiline `notes`, with at least
one populated field. Unknown fields are errors.

The JSON Schema in this directory is suitable for Taplo and editor validation.
The Seiza builder performs the additional cross-file and upstream-reference
checks that JSON Schema cannot express.
