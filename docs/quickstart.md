# Quickstart — local demonstrator

This repository contains a local CLI demonstrator, not an installer or full workstation release. The demonstrator runs without network access after its component checkouts and Python dependencies are present.

## 1. Check out the components

Clone these repositories and check out the exact commits recorded in `integrations/registry.yaml`:

- [ELITE-Ingestion-Core](https://github.com/midnightlolz31337/ELITE-Ingestion-Core)
- [ELITE-Protocol](https://github.com/midnightlolz31337/ELITE-Protocol)

The integration registry pins branch commits that are currently in open, unmerged pull requests. They are experimental dependencies, not released packages. Review the diffs and trust the code before executing it.

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

The `--case-dir` must be a new path. Existing cases are never overwritten. The case contains:

- `case.json`: case metadata and file digests;
- `ingestion/CURRENT.json`: committed ingestion-generation pointer;
- the referenced accepted and quarantine JSONL files;
- `observations.jsonl`: validated accepted Observations.

The original input is not copied into the case. Its name, size, and whole-file SHA-256 are recorded; keep the original separately if retention is required.

## 4. Verify the result

Inspect `case.json`, compare accepted/quarantine/Observation counts, and independently hash the listed files. The case manifest is unsigned; it is not a cryptographic chain-of-custody record.

## Limitations

No network collection, source registry, search UI, case collaboration, signed manifests, automated source authorization, or complete backup/restore is included. Imported content is never executed. Component checkouts are executable code and must be trusted independently. Use synthetic fixtures until the security and licensing gates are resolved.
