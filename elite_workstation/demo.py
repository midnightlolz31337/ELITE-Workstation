"""First local-first Ingestion Core → Protocol case demonstrator."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class WorkstationDemoError(RuntimeError):
    """Raised when a local demonstrator run cannot complete safely."""


def _file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"size_bytes": size, "sha256": digest.hexdigest()}


def _write_json(path: Path, document: dict[str, Any]) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(document, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write(chr(10))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def run_local_demo(
    *,
    input_path: str | Path,
    case_path: str | Path,
    source_id: str,
    source_uri: str,
    observed_at: str,
    collected_at: str,
    ingestion_core_path: str | Path,
    protocol_path: str | Path,
    source_format: str | None = None,
    operator_asserts_authorized: bool = False,
) -> dict[str, Any]:
    """Run local ingestion, validate accepted observations, and export a case.

    Component source directories are explicit local inputs. Their code is
    executed/imported, so callers must point to trusted, reviewed checkouts.
    Imported evidence itself is never executed.
    """
    source = Path(input_path)
    if source.is_symlink() or not source.is_file():
        raise WorkstationDemoError("input_path must be an existing regular file, not a symlink")
    source = source.resolve()

    ingestion_root = Path(ingestion_core_path).resolve()
    protocol_root = Path(protocol_path).resolve()
    if not (ingestion_root / "elite_ingestion" / "cli.py").is_file():
        raise WorkstationDemoError("ingestion_core_path does not contain elite_ingestion/cli.py")
    if not (protocol_root / "adapters" / "ingestion_v1.py").is_file() or not (protocol_root / "validator.py").is_file():
        raise WorkstationDemoError("protocol_path does not contain the versioned adapter and validator")

    fmt = source_format or source.suffix.lstrip(".").lower()
    if fmt not in {"jsonl", "csv"}:
        raise WorkstationDemoError("source_format must be jsonl or csv (or use a matching file extension)")
    if not isinstance(source_id, str) or not source_id.strip():
        raise WorkstationDemoError("source_id must be a non-empty string")
    if not isinstance(source_uri, str) or not source_uri.strip():
        raise WorkstationDemoError("source_uri must be supplied explicitly")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise WorkstationDemoError("observed_at must be supplied explicitly")
    if not isinstance(collected_at, str) or not collected_at.strip():
        raise WorkstationDemoError("collected_at must be supplied explicitly")

    destination = Path(case_path)
    if destination.is_symlink() or destination.exists():
        raise WorkstationDemoError("case_path must be a new path; existing cases are never overwritten")
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    source_before = _file_fingerprint(source)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    try:
        ingestion_output = staging / "ingestion"
        command = [
            sys.executable, "-m", "elite_ingestion.cli", "ingest",
            str(source), "--source-id", source_id,
            "--format", fmt, "--output-dir", str(ingestion_output),
        ]
        if operator_asserts_authorized:
            command.append("--operator-asserts-authorized")
        try:
            subprocess.run(
                command, cwd=ingestion_root, check=True,
                capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "Ingestion Core failed").strip()
            raise WorkstationDemoError(f"Ingestion Core failed: {detail}") from exc

        # The adapter is loaded only from the explicit, trusted Protocol checkout.
        sys.path.insert(0, str(protocol_root))
        try:
            from adapters.ingestion_v1 import export_current_generation
        except Exception as exc:
            raise WorkstationDemoError(f"cannot load Protocol adapter: {exc}") from exc

        current_pointer = ingestion_output / "CURRENT.json"
        observations_path = staging / "observations.jsonl"
        try:
            exported_count = export_current_generation(
                current_pointer,
                observations_path,
                source_uri=source_uri,
                collected_at=collected_at,
                observed_at=observed_at,
            )
        except Exception as exc:
            raise WorkstationDemoError(f"Protocol adaptation/export failed: {exc}") from exc

        source_after = _file_fingerprint(source)
        if source_after != source_before:
            raise WorkstationDemoError("source file changed while the import was running")

        current = json.loads(current_pointer.read_text(encoding="utf-8"))
        if exported_count != current["accepted_count"]:
            raise WorkstationDemoError("exported Observation count does not match accepted ingestion count")
        generation = ingestion_output / current["generation_path"]
        accepted_path = generation / "accepted.jsonl"
        quarantine_path = generation / "quarantine.jsonl"
        case_id = str(uuid.uuid4())
        case_manifest = {
            "schema_version": "elite-workstation-case/0.1-draft",
            "case_id": case_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "source_id": source_id,
                "source_uri": source_uri,
                "input_name": source.name,
                "format": fmt,
                **source_before,
            },
            "timestamps": {
                "observed_at": observed_at,
                "collected_at": collected_at,
            },
            "ingestion": {
                "generation_id": current["generation_id"],
                "accepted_count": current["accepted_count"],
                "quarantine_count": current["quarantine_count"],
                "current_pointer": "ingestion/CURRENT.json",
                "current_pointer_sha256": _file_fingerprint(current_pointer)["sha256"],
            },
            "observations": {
                "path": "observations.jsonl",
                "count": exported_count,
                **_file_fingerprint(observations_path),
            },
            "accepted": {
                "path": str(accepted_path.relative_to(staging)),
                **_file_fingerprint(accepted_path),
            },
            "quarantine": {
                "path": str(quarantine_path.relative_to(staging)),
                **_file_fingerprint(quarantine_path),
            },
            "limitations": [
                "The original input file is not copied into the case; only its name, size, and SHA-256 are recorded.",
                "The operator authorization flag is an assertion only, not identity, legal authority, or policy enforcement.",
                "Digests establish integrity relative to recorded values, not source authenticity or truth.",
                "The case manifest is unsigned and does not establish chain of custody.",
                "This demonstrator has no search UI, source registry, network collection, or autonomous actions.",
            ],
        }
        _write_json(staging / "case.json", case_manifest)
        os.rename(staging, destination)
        staging = None
        return {
            "case_id": case_id,
            "case_path": str(destination),
            "accepted_count": current["accepted_count"],
            "quarantine_count": current["quarantine_count"],
            "observation_count": exported_count,
        }
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
