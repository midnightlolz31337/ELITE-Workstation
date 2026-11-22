"""Integrity verifier for local Workstation case directories."""
from __future__ import annotations

import hashlib
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


class CaseVerificationError(ValueError):
    """Raised when a local case fails structural or integrity checks."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CaseVerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, json.JSONDecodeError) as exc:
        raise CaseVerificationError(f"cannot read JSON file {path.name}: {exc}") from exc


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise CaseVerificationError(f"{field} must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaseVerificationError(f"{field} is not valid ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CaseVerificationError(f"{field} must include a timezone")


def _safe_file(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise CaseVerificationError("case file path is invalid")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        raise CaseVerificationError(f"unsafe case file path: {relative}")
    candidate = root.joinpath(*rel.parts)
    current = candidate
    while current != root:
        if current.is_symlink():
            raise CaseVerificationError(f"symlinked case path is not allowed: {relative}")
        current = current.parent
    resolved = candidate.resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise CaseVerificationError(f"case file is missing or outside the case directory: {relative}")
    return resolved


def _fingerprint(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _jsonl_count(path: Path) -> int:
    count = 0
    size = 0
    last_byte = None
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            size += len(chunk)
            count += chunk.count(bytes([10]))
            if chunk:
                last_byte = chunk[-1]
    if size and last_byte != 10:
        raise CaseVerificationError(f"JSONL file is not newline-terminated: {path.name}")
    return count


def _require_mapping(value: Any, name: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise CaseVerificationError(f"{name} has an invalid structure")
    return value


def _require_count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CaseVerificationError(f"{name} must be a non-negative integer")
    return value


def _verify_file(root: Path, entry: dict[str, Any], expected_path: str | None = None) -> Path:
    if set(entry) != {"path", "size_bytes", "sha256"}:
        raise CaseVerificationError("case file entry has an invalid structure")
    if expected_path is not None and entry["path"] != expected_path:
        raise CaseVerificationError(f"case file path does not match committed generation: {entry['path']}")
    path = _safe_file(root, entry["path"])
    size, digest = _fingerprint(path)
    if size != _require_count(entry["size_bytes"], f"{entry['path']} size"):
        raise CaseVerificationError(f"case file size mismatch: {entry['path']}")
    expected_digest = entry["sha256"]
    if not isinstance(expected_digest, str) or len(expected_digest) != 64 or any(c not in "0123456789abcdef" for c in expected_digest):
        raise CaseVerificationError(f"case file SHA-256 is invalid: {entry['path']}")
    if digest != expected_digest:
        raise CaseVerificationError(f"case file SHA-256 mismatch: {entry['path']}")
    return path


def verify_case(case_path: str | Path, *, protocol_path: str | Path | None = None) -> dict[str, Any]:
    """Verify case structure, CURRENT linkage, file digests, and Observation content hashes.

    This verifies consistency against the unsigned case manifest. It does not
    authenticate the source, owner, case creator, or truth of the evidence.
    """
    root = Path(case_path)
    if root.is_symlink() or not root.is_dir():
        raise CaseVerificationError("case_path must be an existing directory, not a symlink")
    root = root.resolve()
    manifest_path = root / "case.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CaseVerificationError("case.json is missing or unsafe")
    manifest = _load_json(manifest_path)
    required = {
        "schema_version", "case_id", "created_at", "source", "timestamps",
        "ingestion", "observations", "accepted", "quarantine", "limitations",
    }
    _require_mapping(manifest, "case.json", required)
    if manifest["schema_version"] != "elite-workstation-case/0.1-draft":
        raise CaseVerificationError("unsupported case manifest version")
    try:
        case_id = str(uuid.UUID(manifest["case_id"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise CaseVerificationError("case_id is not a UUID") from exc
    if case_id != manifest["case_id"]:
        raise CaseVerificationError("case_id is not canonical")
    _validate_timestamp(manifest["created_at"], "created_at")

    source = _require_mapping(
        manifest["source"], "source",
        {"source_id", "source_uri", "input_name", "format", "size_bytes", "sha256"},
    )
    if not all(isinstance(source[k], str) and source[k] for k in ("source_id", "source_uri", "input_name")):
        raise CaseVerificationError("source identity fields are invalid")
    if source["format"] not in ("jsonl", "csv"):
        raise CaseVerificationError("source format is unsupported")
    _require_count(source["size_bytes"], "source size")
    if not isinstance(source["sha256"], str) or len(source["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in source["sha256"]):
        raise CaseVerificationError("source SHA-256 is invalid")

    timestamps = _require_mapping(manifest["timestamps"], "timestamps", {"observed_at_default", "collected_at"})
    _validate_timestamp(timestamps["observed_at_default"], "observed_at_default")
    _validate_timestamp(timestamps["collected_at"], "collected_at")

    ingestion = _require_mapping(
        manifest["ingestion"], "ingestion",
        {"generation_id", "accepted_count", "quarantine_count", "current_pointer", "current_pointer_sha256"},
    )
    try:
        generation_id = str(uuid.UUID(ingestion["generation_id"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise CaseVerificationError("ingestion generation_id is not a UUID") from exc
    if generation_id != ingestion["generation_id"]:
        raise CaseVerificationError("ingestion generation_id is not canonical")
    accepted_count = _require_count(ingestion["accepted_count"], "accepted_count")
    quarantine_count = _require_count(ingestion["quarantine_count"], "quarantine_count")
    if ingestion["current_pointer"] != "ingestion/CURRENT.json":
        raise CaseVerificationError("current pointer path is invalid")
    current_path = _safe_file(root, ingestion["current_pointer"])
    current_size, current_digest = _fingerprint(current_path)
    del current_size
    pointer_digest = ingestion["current_pointer_sha256"]
    if not isinstance(pointer_digest, str) or len(pointer_digest) != 64 or any(ch not in "0123456789abcdef" for ch in pointer_digest):
        raise CaseVerificationError("CURRENT.json SHA-256 value is invalid")
    if current_digest != pointer_digest:
        raise CaseVerificationError("CURRENT.json SHA-256 mismatch")

    current = _load_json(current_path)
    _require_mapping(
        current, "CURRENT.json",
        {"schema_version", "generation_id", "generation_path", "created_at", "accepted_count", "quarantine_count", "files"},
    )
    if current["schema_version"] != "1" or current["generation_id"] != generation_id:
        raise CaseVerificationError("CURRENT.json generation identity mismatch")
    _validate_timestamp(current["created_at"], "CURRENT.json created_at")
    if current["generation_path"] != f"generations/{generation_id}":
        raise CaseVerificationError("CURRENT.json generation path mismatch")
    if _require_count(current["accepted_count"], "CURRENT accepted_count") != accepted_count:
        raise CaseVerificationError("CURRENT accepted_count mismatch")
    if _require_count(current["quarantine_count"], "CURRENT quarantine_count") != quarantine_count:
        raise CaseVerificationError("CURRENT quarantine_count mismatch")
    current_files = _require_mapping(current["files"], "CURRENT files", {"accepted.jsonl", "quarantine.jsonl"})

    accepted_entry = _require_mapping(manifest["accepted"], "accepted", {"path", "size_bytes", "sha256"})
    quarantine_entry = _require_mapping(manifest["quarantine"], "quarantine", {"path", "size_bytes", "sha256"})
    generation_prefix = f"ingestion/{current['generation_path']}"
    accepted_path = _verify_file(root, accepted_entry, f"{generation_prefix}/accepted.jsonl")
    quarantine_path = _verify_file(root, quarantine_entry, f"{generation_prefix}/quarantine.jsonl")
    for name, case_entry, path in (
        ("accepted.jsonl", accepted_entry, accepted_path),
        ("quarantine.jsonl", quarantine_entry, quarantine_path),
    ):
        pointer_entry = _require_mapping(current_files[name], f"CURRENT {name}", {"path", "size", "sha256"})
        if pointer_entry["path"] != f"{current['generation_path']}/{name}":
            raise CaseVerificationError(f"CURRENT path mismatch for {name}")
        pointer_size = _require_count(pointer_entry["size"], f"CURRENT {name} size")
        pointer_digest = pointer_entry["sha256"]
        if not isinstance(pointer_digest, str) or len(pointer_digest) != 64 or any(ch not in "0123456789abcdef" for ch in pointer_digest):
            raise CaseVerificationError(f"CURRENT SHA-256 is invalid: {name}")
        size, digest = _fingerprint(path)
        if size != pointer_size or digest != pointer_digest:
            raise CaseVerificationError(f"CURRENT file integrity mismatch: {name}")
        expected_lines = accepted_count if name == "accepted.jsonl" else quarantine_count
        if _jsonl_count(path) != expected_lines:
            raise CaseVerificationError(f"record count mismatch: {name}")

    observations_entry = _require_mapping(
        manifest["observations"], "observations", {"path", "count", "size_bytes", "sha256"},
    )
    observation_count = _require_count(observations_entry["count"], "observation count")
    if observation_count != accepted_count:
        raise CaseVerificationError("Observation count does not match accepted ingestion count")
    observation_path = _verify_file(
        root,
        {"path": observations_entry["path"], "size_bytes": observations_entry["size_bytes"], "sha256": observations_entry["sha256"]},
        "observations.jsonl",
    )
    if _jsonl_count(observation_path) != observation_count:
        raise CaseVerificationError("Observation JSONL record count mismatch")

    validator = None
    if protocol_path is not None:
        protocol_root = Path(protocol_path).resolve()
        if not (protocol_root / "validator.py").is_file():
            raise CaseVerificationError("protocol_path does not contain validator.py")
        sys.path.insert(0, str(protocol_root))
        try:
            from validator import validate_document
            validator = validate_document
        except Exception as exc:
            raise CaseVerificationError(f"cannot load Protocol validator: {exc}") from exc

    with observation_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                observation = json.loads(line, object_pairs_hook=_unique_object)
            except json.JSONDecodeError as exc:
                raise CaseVerificationError(f"invalid Observation JSON at line {line_number}") from exc
            if not isinstance(observation, dict):
                raise CaseVerificationError(f"Observation at line {line_number} is not an object")
            content = observation.get("content")
            integrity = observation.get("integrity")
            if not isinstance(content, dict) or not isinstance(content.get("text"), str) or not isinstance(integrity, dict):
                raise CaseVerificationError(f"Observation content/integrity is invalid at line {line_number}")
            if integrity.get("algorithm") != "sha-256" or integrity.get("scope") != "content.text.utf8":
                raise CaseVerificationError(f"Observation digest scope is invalid at line {line_number}")
            actual = hashlib.sha256(content["text"].encode("utf-8")).hexdigest()
            if integrity.get("digest") != actual:
                raise CaseVerificationError(f"Observation content digest mismatch at line {line_number}")
            if validator is not None:
                try:
                    validator("observation", observation)
                except Exception as exc:
                    raise CaseVerificationError(f"Protocol validation failed at line {line_number}: {exc}") from exc

    limitations = manifest["limitations"]
    if not isinstance(limitations, list) or any(not isinstance(item, str) for item in limitations):
        raise CaseVerificationError("case limitations must be a list of strings")
    return {
        "case_id": case_id,
        "accepted_count": accepted_count,
        "quarantine_count": quarantine_count,
        "observation_count": observation_count,
        "verified_files": [
            "case.json", "ingestion/CURRENT.json",
            accepted_entry["path"], quarantine_entry["path"], observations_entry["path"],
        ],
        "integrity_basis": "unsigned case manifest and local SHA-256 consistency checks; not source authentication",
    }
