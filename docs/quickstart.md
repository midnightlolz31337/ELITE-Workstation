# Quickstart — local demonstrator

This repository contains a local CLI demonstrator, not an installer or full workstation release. The demonstrator runs without network access after its component checkouts and Python dependencies are present.

## 1. Check out the components

From the Workstation repository root, clone the component repositories and check out the exact revisions recorded in `integrations/registry.yaml`:

```bash
git clone https://github.com/midnightlolz31337/ELITE-Ingestion-Core
git -C ELITE-Ingestion-Core checkout e7ff07339a3b5256cca0e983f03ccc579b6cfdeb

git clone https://github.com/midnightlolz31337/ELITE-Protocol
git -C ELITE-Protocol checkout 5f8339d926fe0c5cb0b380d324795eebcd2cabac
```

These are experimental branch commits from open, unmerged pull requests, not stable releases. Review the source before running it.

Install Protocol's validation dependency:

```bash
python -m pip install --requirement ELITE-Protocol/requirements.txt
```

## 2. Prepare a local input

The demonstrator accepts JSONL or CSV. Use synthetic data first. Do not point it at sensitive or regulated material until you have reviewed the data-handling and threat-model limitations.

## 3. Run the local case flow

From the Workstation repository root:

```bash
python -m elite_workstation.cli demo ./examples/sample.jsonl \
  --case-dir ./cases/demo-001 \
  --source-id synthetic-demo \
  --source-uri https://example.org/synthetic-demo \
  --observed-at 2026-11-22T12:00:00Z \
  --collected-at 2026-11-22T12:30:00Z \
  --ingestion-core ./ELITE-Ingestion-Core \
  --protocol ./ELITE-Protocol \
  --operator-asserts-authorized
```

The authorization flag records only an operator assertion. It does not authenticate the operator or establish legal, contractual, or organizational authority. Without the flag, records lacking authorization are quarantined; they are not exported as Observations.

If a source record contains its own `observed_at` timestamp, that value takes precedence over the command-line fallback. The case manifest labels the command-line value `observed_at_default` to avoid implying that it applied to every record.

The `--case-dir` must be a new path. Existing cases are never overwritten. The case contains:

- `case.json`: case metadata and file digests;
- `ingestion/CURRENT.json`: committed ingestion-generation pointer;
- the referenced accepted and quarantine JSONL files;
- `observations.jsonl`: validated accepted Observations.

The original input is not copied into the case. Its name, size, and whole-file SHA-256 are recorded; keep the original separately if retention is required.

## 4. Verify the result

Run the local verifier, optionally using the pinned Protocol checkout for full Observation schema validation:

```bash
python -m elite_workstation.cli verify ./cases/demo-001 --protocol ./ELITE-Protocol
```

The verifier checks case structure, safe paths, symlink boundaries, CURRENT linkage, file hashes and sizes, JSONL counts, accepted-envelope-to-Observation correspondence, and content digests. The case manifest is unsigned; verification proves consistency against the local manifest, not source authenticity or a cryptographic chain of custody.


## 5. Export and restore a portable case

Export a case only after verification:

```bash
python -m elite_workstation.cli export-bundle ./cases/demo-001 ./exports/demo-001.zip --protocol ./ELITE-Protocol
```

Restore it to a new directory on another local workstation:

```bash
python -m elite_workstation.cli import-bundle ./exports/demo-001.zip ./cases/restored-demo-001 --protocol ./ELITE-Protocol
python -m elite_workstation.cli verify ./cases/restored-demo-001 --protocol ./ELITE-Protocol
```

The importer rejects unsafe or colliding paths, duplicate entries, symlinks and special files, encrypted entries, unsupported compression, oversized members, excessive compression ratios, and file inventory mismatches. Extraction is staged and the restored case is verified before promotion. Existing destination paths are never intentionally overwritten.

The bundle's `bundle.json` is an **unsigned transport inventory**. Its hashes detect accidental corruption and mismatch against the inventory; they do not authenticate the sender, prove source authenticity, or establish chain of custody. Keep sensitive source material encrypted and transfer it through a channel appropriate to its classification. The prototype does not encrypt bundles.

## Limitations

No network collection, source registry, search UI, case collaboration, signed manifests, automated source authorization, or complete backup/restore is included. Imported content is never executed. Component checkouts are executable code and must be trusted independently. Use synthetic fixtures until the security and licensing gates are resolved.

