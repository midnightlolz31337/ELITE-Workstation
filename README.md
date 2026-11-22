# ELITE Workstation

A local-first integration layer for evidence-led OSINT workflows, combining independent tools without requiring a vendor-hosted coordinator.

## Mission
Provide a coherent workstation experience while keeping components replaceable, data exportable, and operator decisions explicit.

## Planned component boundaries
- Ingestion and quarantine: ELITE-Ingestion-Core.
- Evidence and provenance contracts: ELITE-Protocol.
- Agent/tool discovery: ELITE-Agent-Commons.
- Local case workspace and search.
- Optional mesh/federation adapters.
- Export, backup, and reproducible case bundles.

## Architecture rules
1. Core local workflows must work without LoLz-hosted services.
2. Integrations use documented, versioned interfaces.
3. Components can be replaced independently.
4. External inputs are untrusted until validated.
5. Side effects require explicit approval and bounded scope.
6. No secrets or private records enter public catalogues.
7. No token, blockchain, or proprietary coordinator is required.

## Status
BOOTSTRAP. This repository contains architecture scaffolding, not a working workstation. Do not claim readiness until clean-install, end-to-end, offline, export, and recovery tests pass.