# Threat model (initial)

## Assets

Case evidence, source metadata, analyst notes, credentials held by external tools, local indexes, approval records, exported bundles, and component source checkouts.

## Threats

Malicious files and archives; prompt injection in retrieved content; poisoned metadata; compromised plugins/dependencies; unauthorized side effects; accidental public disclosure; local data loss; stale trust roots; tampered generation pointers; compromised component checkouts; and source files changing during ingestion.

## Current demonstrator controls

- Ingestion Core enforces bounded input handling and quarantines malformed or policy-blocked records.
- Workstation fingerprints the source before and after ingestion and aborts if it changes.
- Protocol adapter verifies CURRENT metadata, canonical generation paths, symlink boundaries, file sizes, SHA-256 digests, newline termination, and manifest counts.
- Source format is carried in each ingestion envelope; callers cannot relabel CSV normalized-row digests as JSONL line-byte digests.
- Only accepted envelopes are converted to Observations.
- Observation content digests are recomputed over exact UTF-8 text bytes.
- Case output is staged and promoted only after ingestion, validation, export, and manifest creation succeed.
- Existing case directories are never overwritten.
- The case verifier checks safe paths, symlink boundaries, CURRENT linkage, file hashes/sizes/counts, one-to-one accepted-envelope-to-Observation provenance, content digests, and optional Protocol schema conformance.
- Component code paths are explicit local inputs; component source code is trusted code and must be reviewed before execution/import.
- Imported evidence is treated as data and is never executed.

## Known limitations

The operator authorization flag is only an assertion. There is no identity provider, source registry, legal authorization engine, network collection, signed manifest, authenticated chain of custody, or cryptographic case signature. The original input is not copied into the case. Parent-directory crash durability is platform/filesystem dependent. A case manifest and hashes do not establish source authenticity or truth.

This is not a complete threat model or security certification.

## Portable bundle controls (experimental)

- Export starts by verifying the source case and rejects symlinks and non-regular files.
- ZIP output uses stable member ordering, timestamps, permissions, and compression settings.
- Import rejects path traversal, non-canonical and cross-platform-colliding paths, duplicate entries, symlinks/special files, encryption, unsupported compression, excessive compression ratios, oversized files, excessive entry counts, and aggregate-size overflow.
- Extraction is staged; each member's actual byte count and SHA-256 are checked against the unsigned inventory; the complete case is verified before promotion.
- The bundle inventory is not signed. A malicious sender can create a self-consistent bundle; authenticity and chain of custody remain out of scope.

## Source snapshot and retention controls

- Ingestion runs against a staged snapshot rather than a mutable external path. The source and snapshot fingerprints must match before ingestion, and the external source is checked again after processing.
- Original source bytes are not retained by default. `--include-source-copy` explicitly opts into retaining the snapshot in the case.
- When present, the retained source copy is checked against the recorded original byte count and SHA-256 during case verification.
- Portable case bundles include retained source files. Bundles are not encrypted; operators must classify source data and control access, transfer, retention, and deletion.
- A matching digest proves consistency with the recorded fingerprint, not source authenticity or truth.