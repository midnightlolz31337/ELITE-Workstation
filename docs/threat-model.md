# Threat model (initial)

Assets: case evidence, source metadata, analyst notes, credentials held by external tools, local indexes, approval records, exported bundles.

Threats: malicious files and archives; prompt injection in retrieved content; poisoned metadata; compromised plugins/dependencies; unauthorized side effects; accidental public disclosure; local data loss; stale trust roots.

Controls to design and test: quarantine and resource limits; never treat content as executable instructions; separate untrusted evidence from policy and operator decisions; least-privilege adapters and explicit side-effect approval; secret scanning and allowlisted exports; backup/restore tests; versioned schemas and dependency provenance.

This is not a complete threat model or security certification.