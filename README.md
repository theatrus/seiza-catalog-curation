# Seiza catalog curation

This repository is the source of truth for Seiza-authored object identity
relations, geometry corrections, selection policy, and exceptional source
remappings. It does not copy or enumerate ordinary upstream catalog data.

The Seiza builder consumes a pinned, clean checkout. Each curated object has
one `objects/<id>.toml` document containing its target identifier and any
geometry corrections, exceptional outline remappings, relations, selections,
notes, and structured evidence. Keeping all decisions about an object together
makes a review diff complete and avoids coordinating rows across global tables.

Seiza imports normally named OpenNGC outline files directly from the upstream
source. They belong here only when a human decision is needed to map one to a
different object or change its role, quality, or preferred status.

`schema/v2/object-curation.schema.json` is the machine-readable contract.
Taplo-compatible editors discover it through `.taplo.toml`. Unknown fields,
duplicate document or correction IDs, duplicate target documents, invalid
references, and out-of-range geometry fail the Seiza build.

`curation.json` identifies this repository and schema. Seiza derives the exact
commit from Git when building and records it with checksums in `objects.bin`.

Corrections retain the original catalog measurement as a separate source
record. A correction never overwrites or pretends to be supplied by upstream.
Evidence belongs beside the decision it supports and may record a kind,
citation, URL, and multiline notes directly in the object document.

Validate the repository with Python 3.11 or newer, without downloading any
upstream catalog:

```shell
python scripts/validate.py
```

Seiza-authored curation data and notes are dedicated to the public domain under
CC0-1.0. Referenced upstream catalogs and imagery retain their own terms.
