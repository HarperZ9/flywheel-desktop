"""Validate the fail-closed Flywheel Desktop release and payload contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "packaging" / "release-manifest.schema.json"
SCHEMA_KEYWORDS = {
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "title",
    "type",
    "const",
    "enum",
    "required",
    "properties",
    "additionalProperties",
    "oneOf",
    "pattern",
    "minLength",
    "maxLength",
}
WINDOWS_DEVICE_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


class ContractError(ValueError):
    """A release input does not satisfy the canonical contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ContractError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _read_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"could not read JSON {path}: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_unique_object)
    except ContractError:
        raise
    except json.JSONDecodeError as exc:
        raise ContractError(f"could not parse JSON {path}: {exc}") from exc


def _json_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        return set(left) == set(right) and all(_json_equal(left[key], right[key]) for key in left)  # type: ignore[index]
    if isinstance(left, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right))  # type: ignore[arg-type]
    return left == right


def _resolve_ref(root: Mapping[str, Any], reference: object) -> Mapping[str, Any]:
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise ContractError(f"unsupported schema reference: {reference}")
    node: object = root
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, Mapping) or token not in node:
            raise ContractError(f"unresolved schema reference: {reference}")
        node = node[token]
    if not isinstance(node, Mapping):
        raise ContractError(f"schema reference is not an object: {reference}")
    return node


def _matches_type(value: object, expected: object) -> bool:
    checks = {
        "object": lambda item: isinstance(item, Mapping),
        "string": lambda item: isinstance(item, str),
        "null": lambda item: item is None,
    }
    if expected not in checks:
        raise ContractError(f"unsupported schema type: {expected}")
    return checks[expected](value)


def _validate_schema(
    value: object,
    schema: Mapping[str, Any],
    root: Mapping[str, Any],
    label: str,
) -> None:
    unknown_keywords = set(schema) - SCHEMA_KEYWORDS
    if unknown_keywords:
        raise ContractError(f"unsupported schema keywords at {label}: {sorted(unknown_keywords)}")
    if "$ref" in schema:
        _validate_schema(value, _resolve_ref(root, schema["$ref"]), root, label)
    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        raise ContractError(f"{label} must have JSON type {expected_type}")
    if "const" in schema and not _json_equal(value, schema["const"]):
        raise ContractError(f"{label} does not match the pinned contract")
    if "enum" in schema and not any(_json_equal(value, item) for item in schema["enum"]):
        raise ContractError(f"{label} is outside the permitted values")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ContractError(f"{label} is shorter than the schema minimum")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ContractError(f"{label} is longer than the schema maximum")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ContractError(f"{label} does not match the required pattern")
    if isinstance(value, Mapping):
        required = schema.get("required", [])
        missing = set(required) - set(value)
        if missing:
            raise ContractError(f"{label} is missing required keys: {sorted(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ContractError(f"{label} has unknown keys: {sorted(unknown)}")
        for key, child_schema in properties.items():
            if key in value:
                _validate_schema(value[key], child_schema, root, f"{label}.{key}")
    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            try:
                _validate_schema(value, branch, root, label)
            except ContractError:
                continue
            matches += 1
        if matches != 1:
            raise ContractError(f"{label} must match exactly one schema branch; matched={matches}")


def validate_manifest(value: object) -> Mapping[str, Any]:
    schema = _read_json(SCHEMA_PATH)
    if not isinstance(schema, Mapping):
        raise ContractError("release manifest schema must be an object")
    _validate_schema(value, schema, schema, "manifest")
    if not isinstance(value, Mapping):  # established by the schema; keeps typing honest
        raise ContractError("manifest must be an object")
    artifacts = value["artifacts"]
    for name in artifacts.values():
        if not isinstance(name, str) or Path(name).name != name or "\\" in name:
            raise ContractError("artifact names must be basenames")
        folded = name.casefold()
        if any(label not in folded for label in ("internal", "unsigned", "nonredistributable")):
            raise ContractError("artifact names must carry internal/unsigned/nonredistributable labels")
    return value


def _literal_path(value: object) -> tuple[str, list[str]]:
    if not isinstance(value, str) or not value:
        raise ContractError("payload path must be a non-empty string")
    if "\\" in value or any(character in value for character in '*?[]<>:"|'):
        raise ContractError(f"payload path must be a literal Win32-safe POSIX path: {value}")
    if any(ord(character) < 32 for character in value):
        raise ContractError(f"payload path contains a Windows control character: {value!r}")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ContractError(f"payload path cannot be absolute or drive-relative: {value}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ContractError(f"payload path contains traversal or a non-canonical segment: {value}")
    for part in parts:
        if part.endswith((".", " ")):
            raise ContractError(f"payload path contains a Win32-normalized segment: {value}")
        if part.split(".", 1)[0].casefold() in WINDOWS_DEVICE_NAMES:
            raise ContractError(f"payload path contains a reserved Windows device name: {value}")
    if PurePosixPath(value).as_posix() != value:
        raise ContractError(f"payload path is not canonical: {value}")
    return value, parts


def _validate_allowlisted(path: str, roots: Sequence[Mapping[str, str]]) -> None:
    for root in roots:
        prefix = root["path"]
        if root["kind"] == "file" and path == prefix:
            return
        if root["kind"] == "tree" and path.startswith(prefix + "/"):
            return
    raise ContractError(f"payload path is outside permitted roots: {path}")


def _validate_not_forbidden(path: str, parts: Sequence[str], policy: Mapping[str, Any]) -> None:
    folded_parts = [part.casefold() for part in parts]
    folded_path = path.casefold()
    if any(part in policy["segments"] for part in folded_parts):
        raise ContractError(f"payload path contains a forbidden segment: {path}")
    if any(part in policy["names"] for part in folded_parts):
        raise ContractError(f"payload path contains a forbidden name: {path}")
    if any(part.startswith(tuple(policy["name_prefixes"])) for part in folded_parts):
        raise ContractError(f"payload path contains a forbidden name prefix: {path}")
    if any(fragment in part for part in folded_parts for fragment in policy["name_fragments"]):
        raise ContractError(f"payload path contains a forbidden name fragment: {path}")
    if any(part.endswith(tuple(policy["suffixes"])) for part in folded_parts):
        raise ContractError(f"payload path contains a forbidden suffix: {path}")
    padded = f"/{folded_path}/"
    if any(f"/{subpath}/" in padded for subpath in policy["subpaths"]):
        raise ContractError(f"payload path contains a forbidden subpath: {path}")


def validate_payload_list(manifest: Mapping[str, Any], value: object) -> int:
    if not isinstance(value, Mapping) or set(value) != {"schema_version", "paths"}:
        raise ContractError("payload list must contain exactly schema_version and paths")
    paths = value["paths"]
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("payload list schema_version must be the JSON integer 1")
    if not isinstance(paths, list) or not paths:
        raise ContractError("payload list paths must be a non-empty list")
    policy = manifest["payload_policy"]
    seen: dict[str, str] = {}
    for raw_path in paths:
        path, parts = _literal_path(raw_path)
        folded = path.casefold()
        if folded in seen:
            raise ContractError(f"case-insensitive payload collision: {seen[folded]} and {path}")
        seen[folded] = path
        _validate_allowlisted(path, policy["permitted_roots"])
        _validate_not_forbidden(path, parts, policy["forbidden"])
    return len(seen)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--payload-list", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = validate_manifest(_read_json(args.manifest))
        payload_count = None
        if args.payload_list is not None:
            payload_count = validate_payload_list(manifest, _read_json(args.payload_list))
    except ContractError as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "schema_version": 1,
                "result": "PASS",
                "manifest": str(args.manifest.resolve()),
                "manifest_state": manifest["manifest_state"],
                "payload_path_count": payload_count,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
