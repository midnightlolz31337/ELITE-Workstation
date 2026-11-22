# Architecture overview (draft)

## Design goals
Local-first operation, explicit trust boundaries, replaceable components, reproducible workflows, and portable data.

## Logical layers
1. User workspace — cases, notes, review decisions, local search.
2. Ingestion boundary — bounded import, quarantine, parsing, validation.
3. Evidence contracts — source records, artifacts, observations, assertions, provenance.
4. Tool adapters — explicit interfaces to independent tools and agents.
5. Optional federation — peer discovery and exchange; never required for local operation.
6. Export/recovery — inspectable case bundles and restore procedures.

UI depends on stable application interfaces; adapters depend on versioned contracts; core evidence records do not depend on a particular UI, provider, or hosted service. These are design requirements, not verified capabilities.