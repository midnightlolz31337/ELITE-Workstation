# Architecture overview

## Design goals

Local-first operation, explicit trust boundaries, replaceable components, reproducible workflows, and portable data.

## Logical layers

1. User workspace — cases, notes, review decisions, local search.
2. Ingestion boundary — bounded import, quarantine, parsing, validation.
3. Evidence contracts — source records, artifacts, observations, assertions, provenance.
4. Tool adapters — explicit interfaces to independent tools and agents.
5. Optional federation — peer discovery and exchange; never required for local operation.
6. Export/recovery — inspectable case bundles and restore procedures.

## First executable vertical slice

The current prototype implements one narrow path:

`local JSONL/CSV → ELITE Ingestion Core → CURRENT.json verified generation → ELITE Protocol Observation 1.1.0 adapter → deterministic observations.jsonl → case.json`

The Workstation invokes the Ingestion Core CLI as a subprocess from an explicit local checkout and imports the Protocol adapter from another explicit local checkout. CI pins both dependencies to exact commits and runs synthetic JSONL and CSV end-to-end tests. This is an integration demonstrator, not a package manager or stable plugin system.

The case manifest records the source file's name, size, and whole-file SHA-256; ingestion generation ID and counts; the CURRENT pointer digest; and hashes/sizes for accepted, quarantine, and exported Observation files. The original source is not copied. The manifest is unsigned and does not prove authenticity or chain of custody.

UI depends on stable application interfaces; adapters depend on versioned contracts; core evidence records do not depend on a particular UI, provider, or hosted service. These remain design requirements beyond this first slice.
## Portable case transport (experimental)\n\nThe Workstation can export a verified case to a deterministic ZIP and import it into a new local case directory. The ZIP inventory records each file's relative path, byte length, and SHA-256. Import validates the archive structure and resource limits before extraction, stages the files, runs the case verifier, and only then promotes the restored case. No central service is involved. The inventory is unsigned and does not authenticate the sender or source.\n