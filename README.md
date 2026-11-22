# ELITE Workstation

A local-first integration layer for evidence-led OSINT workflows. No vendor-hosted coordinator, mandatory cloud account, token, or blockchain is required.

## Current status

**Status: PROTOTYPE** The first executable local vertical slice now connects ELITE Ingestion Core to ELITE Protocol:

1. Import a local JSONL or CSV file through bounded ingestion.
2. Preserve accepted and quarantined outputs in a committed generation.
3. Verify the generation pointer, output digests, source-format provenance, and counts.
4. Convert accepted envelopes into schema-validated ELITE Observations.
5. Export deterministic Observation JSONL and create a local case manifest.
6. Re-verify the case, file hashes, record counts, and Observation content digests with `elite-workstation verify`.

This is a demonstrator, not a complete OSINT workstation, supported installer, or production release. It has no search UI, source registry, network collection, analyst collaboration, signed chain of custody, or full backup/restore workflow.

## Architecture rules

- Local core workflows must not depend on LoLz-hosted services.
- Integrations use explicit, versioned interfaces and pinned source revisions.
- Components remain replaceable and independently testable.
- Imported evidence is untrusted data, never executable instructions.
- Quarantined records never enter the Observation export.
- Authorization flags are operator assertions, not authentication or legal/policy enforcement.
- Source digests and content digests are separate; neither establishes truth.
- Private case data and credentials never enter public catalogues.

## Run the demonstrator

See [docs/quickstart.md](docs/quickstart.md). It requires local checkouts of the two component repositories at the exact revisions listed in [integrations/registry.yaml](integrations/registry.yaml).

## Release gates

See [docs/RELEASE_GATES.md](docs/RELEASE_GATES.md). This repository currently has no selected open-source license; do not describe it as licensed open source or redistribute it under an assumed license. The Apache-2.0 branch-level statements in component repositories do not automatically apply here.

**The evidence matters more than the announcement.** A passing integration test demonstrates only the pinned synthetic path—not full workstation readiness, source authenticity, or production security.
