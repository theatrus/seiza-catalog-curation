#!/usr/bin/env python3

import json
import math
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    print("error: validation requires Python 3.11 or newer", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_ROLES = {
    "catalog-extent",
    "preferred-render",
    "fallback-extent",
    "brightness-level",
    "component",
}
GEOMETRY_QUALITIES = {"catalog", "curated", "estimated", "derived"}
RELATION_KINDS = {
    "same-as",
    "component-of",
    "parent-of",
    "duplicate-of",
    "catalog-alias",
}
SELECTION_FACETS = {
    "preferred-identity",
    "preferred-position",
    "preferred-geometry",
    "preferred-photometry",
    "preferred-classification",
}


def fail(path: Path, message: str) -> None:
    raise ValueError(f"{path.relative_to(ROOT)}: {message}")


def expect_keys(path: Path, value: dict, allowed: set[str], required: set[str]) -> None:
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown:
        fail(path, f"unknown fields: {', '.join(sorted(unknown))}")
    if missing:
        fail(path, f"missing fields: {', '.join(sorted(missing))}")


def validate_evidence(path: Path, evidence: object) -> None:
    if not isinstance(evidence, list):
        fail(path, "evidence must be an array of tables")
    for item in evidence:
        if not isinstance(item, dict):
            fail(path, "evidence entry must be a table")
        expect_keys(path, item, {"kind", "citation", "url", "notes"}, set())
        if not any(isinstance(value, str) and value.strip() for value in item.values()):
            fail(path, "evidence entry must contain kind, citation, url, or notes")


def finite_number(path: Path, value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(path, f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        fail(path, f"{name} must be finite")
    return result


def validate_document(
    path: Path,
    document: dict,
    target_ids: set[str],
    correction_ids: set[str],
    outline_files: set[str],
) -> tuple[int, int]:
    expect_keys(
        path,
        document,
        {
            "schema_version",
            "id",
            "target_id",
            "notes",
            "evidence",
            "geometries",
            "outlines",
            "relations",
            "selections",
        },
        {"schema_version", "id", "target_id"},
    )
    if document["schema_version"] != 2:
        fail(path, "schema_version must be 2")
    document_id = document["id"]
    if not isinstance(document_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", document_id):
        fail(path, "id must contain lowercase letters, digits, and hyphens")
    if path.stem != document_id:
        fail(path, f"filename must be {document_id}.toml")
    target_id = document["target_id"]
    if not isinstance(target_id, str) or not target_id.strip():
        fail(path, "target_id must be a non-empty string")
    if target_id in target_ids:
        fail(path, f"duplicate target_id {target_id}")
    target_ids.add(target_id)
    validate_evidence(path, document.get("evidence", []))

    geometries = document.get("geometries", [])
    if not isinstance(geometries, list):
        fail(path, "geometries must be an array of tables")
    for geometry in geometries:
        expect_keys(
            path,
            geometry,
            {
                "id",
                "type",
                "center_ra_deg",
                "center_dec_deg",
                "major_arcmin",
                "minor_arcmin",
                "position_angle_deg",
                "role",
                "quality",
                "method",
                "notes",
                "preferred",
                "evidence",
            },
            {"id", "type", "center_ra_deg", "center_dec_deg", "major_arcmin"},
        )
        correction_id = geometry["id"]
        if not isinstance(correction_id, str) or not correction_id.strip():
            fail(path, "geometry id must be a non-empty string")
        if correction_id in correction_ids:
            fail(path, f"duplicate geometry id {correction_id}")
        correction_ids.add(correction_id)
        if geometry["type"] != "ellipse":
            fail(path, "only ellipse geometry is supported in schema v2")
        ra = finite_number(path, geometry["center_ra_deg"], "center_ra_deg")
        dec = finite_number(path, geometry["center_dec_deg"], "center_dec_deg")
        major = finite_number(path, geometry["major_arcmin"], "major_arcmin")
        if not 0 <= ra < 360 or not -90 <= dec <= 90 or major <= 0:
            fail(path, "ellipse center or major axis is out of range")
        if "minor_arcmin" in geometry and finite_number(path, geometry["minor_arcmin"], "minor_arcmin") <= 0:
            fail(path, "minor_arcmin must be positive")
        if "position_angle_deg" in geometry:
            angle = finite_number(path, geometry["position_angle_deg"], "position_angle_deg")
            if not 0 <= angle < 180:
                fail(path, "position_angle_deg must be in [0, 180)")
        if geometry.get("role", "fallback-extent") not in GEOMETRY_ROLES:
            fail(path, "unknown geometry role")
        if geometry.get("quality", "estimated") not in GEOMETRY_QUALITIES:
            fail(path, "unknown geometry quality")
        validate_evidence(path, geometry.get("evidence", []))

    outlines = document.get("outlines", [])
    if not isinstance(outlines, list):
        fail(path, "outlines must be an array of tables")
    for outline in outlines:
        expect_keys(
            path,
            outline,
            {
                "file",
                "source_record_id",
                "role",
                "quality",
                "method",
                "notes",
                "preferred",
                "evidence",
            },
            {"file"},
        )
        filename = outline["file"]
        if (
            not isinstance(filename, str)
            or "/" in filename
            or "\\" in filename
            or not filename.endswith(".txt")
        ):
            fail(path, "outline file must be one .txt basename")
        if filename in outline_files:
            fail(path, f"duplicate outline mapping {filename}")
        outline_files.add(filename)
        if outline.get("role", "brightness-level") not in GEOMETRY_ROLES:
            fail(path, "unknown outline role")
        if outline.get("quality", "catalog") not in GEOMETRY_QUALITIES:
            fail(path, "unknown outline quality")
        validate_evidence(path, outline.get("evidence", []))

    for relation in document.get("relations", []):
        expect_keys(
            path,
            relation,
            {"kind", "related_id", "source_record_id", "notes", "evidence"},
            {"kind", "related_id"},
        )
        if relation["kind"] not in RELATION_KINDS:
            fail(path, "unknown relation kind")
        validate_evidence(path, relation.get("evidence", []))

    for selection in document.get("selections", []):
        expect_keys(
            path,
            selection,
            {"facet", "source_record_id", "geometry_id", "notes", "evidence"},
            {"facet"},
        )
        if selection["facet"] not in SELECTION_FACETS:
            fail(path, "unknown selection facet")
        validate_evidence(path, selection.get("evidence", []))

    return len(geometries), len(outlines)


def main() -> int:
    metadata = json.loads((ROOT / "curation.json").read_text(encoding="utf-8"))
    if metadata.get("schema_version") != 2 or not metadata.get("repository"):
        raise ValueError("curation.json must declare repository and schema_version 2")
    target_ids: set[str] = set()
    correction_ids: set[str] = set()
    outline_files: set[str] = set()
    documents = sorted((ROOT / "objects").rglob("*"))
    if any(path.is_file() and path.suffix != ".toml" for path in documents):
        raise ValueError("objects/ may contain only TOML documents")
    paths = [path for path in documents if path.is_file()]
    geometry_count = 0
    outline_count = 0
    for path in paths:
        with path.open("rb") as handle:
            document = tomllib.load(handle)
        geometries, outlines = validate_document(
            path, document, target_ids, correction_ids, outline_files
        )
        geometry_count += geometries
        outline_count += outlines
    print(
        f"valid schema v2: {len(paths)} objects, "
        f"{geometry_count} corrected geometries, {outline_count} outline mappings"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
