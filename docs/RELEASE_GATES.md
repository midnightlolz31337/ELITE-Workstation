# Workstation release gates

The current code is a local demonstrator. Do not call it a complete workstation, production-ready, secure, certified, or released.

## Required before a public alpha

- [ ] Select and approve a license for this repository; review contributor provenance and third-party notices.
- [ ] Resolve licenses and compatibility across Ingestion Core, Protocol, and future integrations.
- [ ] Move experimental dependency pins to reviewed, stable component revisions or define a supported vendoring/package policy.
- [ ] Define a versioned case-manifest schema and independent validator.
- [ ] Add a signed-manifest/attestation design only after key ownership, rotation, revocation, and recovery are specified.
- [ ] Add clean-install tests on supported platforms.
- [ ] Add offline operation, backup, restore, and corruption-recovery tests.
- [ ] Add resource limits for case size, record count, output size, and storage exhaustion.
- [ ] Add a policy/authorization boundary that does not confuse operator assertions with verified authority.
- [ ] Review component loading, dependency provenance, and supply-chain controls.
- [ ] Define safe logging, secret handling, data retention, and secure deletion expectations.
- [ ] Add a user-facing review workflow for quarantined records and provenance.
- [ ] Add independent conformance tests and reproducible build evidence.

## Required before a stable release

- [ ] Supported platform and upgrade policy.
- [ ] Stable public API/CLI and backward-compatible case format.
- [ ] Signed release artifacts and reproducible checksums.
- [ ] Security review and documented vulnerability reporting process.
- [ ] Tested export/import across independent implementations.
- [ ] Clear governance and contribution process.

## Current licensing status

No license is selected for this repository. Public visibility does not itself grant permission to use, modify, or redistribute the code. Do not assume the component repositories' branch-level Apache-2.0 statements apply to this repository.

- [ ] Formalize and independently review the portable bundle profile, including cross-platform path behavior and atomic destination promotion.
- [ ] Add cross-platform and filesystem fault-injection tests for interrupted export/import and durability.
- [ ] Decide whether portable cases should include source originals or only their recorded fingerprints.
\n- [ ] Define source-original classification, access control, secure deletion, retention, and encryption expectations before enabling source-copy retention in any public production release.\n- [ ] Review the case and bundle formats for backward-compatible optional source-copy metadata and verify that default behavior never retains originals.\n