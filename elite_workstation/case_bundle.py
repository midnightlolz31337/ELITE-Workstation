"""Deterministic, bounded ZIP transport for verified local ELITE cases.

The bundle manifest is an unsigned transport inventory. It is not a trust root,
signature, source-authentication mechanism, or chain-of-custody attestation.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .verify import CaseVerificationError, verify_case

BUNDLE_SCHEMA = "elite-workstation-case-bundle/1"
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 1000
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_PATH_BYTES = 1024
MAX_COMPRESSION_RATIO = 200
CHUNK_SIZE = 64 * 1024


class CaseBundleError(ValueError):
    """Raised when a case bundle cannot be safely exported or imported."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CaseBundleError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _fingerprint(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _archive_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CaseBundleError("bundle contains an invalid path")
    if len(value.encode("utf-8")) > MAX_PATH_BYTES:
        raise CaseBundleError("bundle path exceeds length limit")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise CaseBundleError(f"unsafe bundle path: {value}")
    if path.as_posix() != value or ":" in path.parts[0]:
        raise CaseBundleError(f"non-canonical bundle path: {value}")
    return value


def _case_files(root: Path) -> list[dict[str, Any]]:
    entries = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise CaseBundleError(f"case contains a symlink: {path.relative_to(root)}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise CaseBundleError(f"case contains a non-regular file: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix()
        _archive_path(relative)
        size, digest = _fingerprint(path)
        if size > MAX_FILE_BYTES:
            raise CaseBundleError(f"case file exceeds bundle limit: {relative}")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise CaseBundleError("case exceeds total bundle size limit")
        entries.append({"path": relative, "size_bytes": size, "sha256": digest})
        if len(entries) > MAX_ENTRIES - 1:
            raise CaseBundleError("case contains too many files for a bundle")
    return entries


def export_case_bundle(case_path: str | Path, bundle_path: str | Path, *, protocol_path: str | Path | None = None) -> dict[str, Any]:
    """Write a deterministic ZIP bundle after verifying the source case."""
    case = Path(case_path)
    try:
        verified = verify_case(case, protocol_path=protocol_path)
    except CaseVerificationError as exc:
        raise CaseBundleError(f"case verification failed: {exc}") from exc
    if case.is_symlink() or not case.is_dir():
        raise CaseBundleError("case_path must be a regular directory")
    case = case.resolve()
    destination = Path(bundle_path)
    if destination.is_symlink() or destination.exists():
        raise CaseBundleError("bundle destination must be new; existing files are never overwritten")
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = _case_files(case)
    manifest = {
        "schema_version": BUNDLE_SCHEMA,
        "case_id": verified["case_id"],
        "files": entries,
    }
    total = sum(item["size_bytes"] for item in entries)
    if total > MAX_TOTAL_BYTES:
        raise CaseBundleError("case exceeds total bundle size limit")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            _write_member(archive, "bundle.json", _json_bytes(manifest))
            for entry in entries:
                info = _zip_info(entry["path"])
                with case.joinpath(*PurePosixPath(entry["path"]).parts).open("rb") as source:
                    with archive.open(info, "w") as target:
                        shutil.copyfileobj(source, target, CHUNK_SIZE)
        archive_size = temporary.stat().st_size
        if archive_size > MAX_ARCHIVE_BYTES:
            raise CaseBundleError("generated archive exceeds maximum archive size")
        # Hard-link publication fails rather than replacing an existing path.
        os.link(temporary, destination)
        temporary.unlink()
        temporary = None
        return {
            "bundle_path": str(destination),
            "case_id": verified["case_id"],
            "file_count": len(entries),
            "uncompressed_bytes": total,
            "archive_bytes": archive_size,
            "schema_version": BUNDLE_SCHEMA,
        }
    except (OSError, zipfile.BadZipFile) as exc:
        raise CaseBundleError(f"cannot export case bundle: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.flag_bits = 0
    return info


def _write_member(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    archive.writestr(_zip_info(name), data)


def import_case_bundle(bundle_path: str | Path, destination: str | Path, *, protocol_path: str | Path | None = None) -> dict[str, Any]:
    """Safely extract and verify a bundle into a new case directory."""
    archive_path = Path(bundle_path)
    if archive_path.is_symlink() or not archive_path.is_file():
        raise CaseBundleError("bundle_path must be a regular file, not a symlink")
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise CaseBundleError("archive exceeds maximum size")
    destination = Path(destination)
    if destination.is_symlink() or destination.exists():
        raise CaseBundleError("case destination must be new; existing cases are never overwritten")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.import-", dir=destination.parent))
    case_root = staging / "case"
    case_root.mkdir()
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_ENTRIES:
                raise CaseBundleError("archive entry count is invalid")
            names = []
            total = 0
            for info in infos:
                name = _archive_path(info.filename)
                if name in names:
                    raise CaseBundleError(f"duplicate archive entry: {name}")
                names.append(name)
                if info.is_dir() or info.flag_bits & 0x1:
                    raise CaseBundleError("directory entries and encrypted members are not supported")
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise CaseBundleError("unsupported ZIP compression method")
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode) or (mode and not stat.S_ISREG(mode)):
                    raise CaseBundleError("symlink or special-file archive member is forbidden")
                if info.file_size > MAX_FILE_BYTES:
                    raise CaseBundleError(f"archive member exceeds size limit: {name}")
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise CaseBundleError("archive exceeds total uncompressed size limit")
                if info.file_size and info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO:
                    raise CaseBundleError(f"archive member compression ratio exceeds limit: {name}")
            if names.count("bundle.json") != 1:
                raise CaseBundleError("archive must contain exactly one bundle.json")
            try:
                raw_manifest = archive.read("bundle.json")
                manifest = json.loads(raw_manifest.decode("utf-8"), object_pairs_hook=_unique_object)
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CaseBundleError("bundle.json is invalid") from exc
            if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "case_id", "files"}:
                raise CaseBundleError("bundle manifest structure is invalid")
            if manifest["schema_version"] != BUNDLE_SCHEMA or not isinstance(manifest["case_id"], str):
                raise CaseBundleError("unsupported bundle manifest version or case ID")
            if not isinstance(manifest["files"], list) or len(manifest["files"]) != len(infos) - 1:
                raise CaseBundleError("bundle file inventory does not match archive entries")
            declared = {}
            previous = ""
            for entry in manifest["files"]:
                if not isinstance(entry, dict) or set(entry) != {"path", "size_bytes", "sha256"}:
                    raise CaseBundleError("bundle file entry structure is invalid")
                name = _archive_path(entry["path"])
                if name == "bundle.json" or name in declared or name <= previous:
                    raise CaseBundleError("bundle inventory paths must be unique and sorted")
                previous = name
                size = entry["size_bytes"]
                digest = entry["sha256"]
                if isinstance(size, bool) or not isinstance(size, int) or size < 0 or size > MAX_FILE_BYTES:
                    raise CaseBundleError(f"bundle file size is invalid: {name}")
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                    raise CaseBundleError(f"bundle file digest is invalid: {name}")
                declared[name] = entry
            if set(names) != set(declared) | {"bundle.json"}:
                raise CaseBundleError("archive members do not match declared inventory")
            for name in sorted(declared):
                info = archive.getinfo(name)
                target = case_root.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                size = 0
                with archive.open(info, "r") as source, target.open("xb") as output:
                    while True:
                        chunk = source.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > declared[name]["size_bytes"] or size > MAX_FILE_BYTES:
                            raise CaseBundleError(f"archive member expanded beyond declared size: {name}")
                        digest.update(chunk)
                        output.write(chunk)
                if size != declared[name]["size_bytes"] or digest.hexdigest() != declared[name]["sha256"]:
                    raise CaseBundleError(f"archive member integrity mismatch: {name}")
        try:
            verified = verify_case(case_root, protocol_path=protocol_path)
        except CaseVerificationError as exc:
            raise CaseBundleError(f"imported case verification failed: {exc}") from exc
        if verified["case_id"] != manifest["case_id"]:
            raise CaseBundleError("bundle case ID does not match case.json")
        if destination.exists() or destination.is_symlink():
            raise CaseBundleError("case destination appeared during import; refusing to overwrite")
        os.rename(case_root, destination)
        return {
            "case_path": str(destination),
            "case_id": verified["case_id"],
            "file_count": len(declared),
            "accepted_count": verified["accepted_count"],
            "quarantine_count": verified["quarantine_count"],
            "observation_count": verified["observation_count"],
            "schema_version": BUNDLE_SCHEMA,
        }
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise CaseBundleError(f"cannot import case bundle: {exc}") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
