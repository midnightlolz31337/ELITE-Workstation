# ELITE Workstation Case Bundle Profile 1 (draft)

**Status:** experimental, unsigned, local transport format.

## Contents

A bundle is a ZIP archive containing exactly one `bundle.json` and the files of one verified case. Directories are implicit; directory entries are not accepted.

`bundle.json` has exactly these fields:

- `schema_version`: `elite-workstation-case-bundle/1`
- `case_id`: UUID matching the enclosed `case.json`
- `files`: lexically sorted array of objects containing exactly `path`, `size_bytes`, and lowercase hexadecimal `sha256`

Every file other than `bundle.json` must appear exactly once in `files`, and every inventory entry must correspond to exactly one archive member. Paths are relative, canonical POSIX paths, NFC-normalized, portable across common Windows filesystems, and must not collide after case folding.

## Deterministic export

The exporter verifies the source case before packaging. It sorts paths, fixes ZIP timestamps to 1980-01-01 00:00:00, uses stable regular-file permissions and DEFLATE compression, and writes the bundle inventory with sorted JSON keys and compact separators. Repeated exports of an unchanged case under the same implementation should be byte-identical.

## Import validation

The importer validates the complete central directory before extraction and rejects:

- absolute, traversal, non-canonical, non-NFC, backslash, reserved-device, alternate-stream, or case/Unicode-colliding paths;
- duplicate entries, directory entries, symlinks, and special files;
- encrypted members and compression methods other than STORED or DEFLATED;
- more than 1,000 entries, archive size over 512 MiB, any member over 256 MiB, aggregate uncompressed content over 1 GiB, paths over 1,024 UTF-8 bytes, a bundle manifest over 1 MiB, or compression ratios over 200:1;
- invalid/duplicate JSON keys, mismatched inventories, incorrect expanded sizes, and SHA-256 mismatches.

Files are streamed into a new staging directory. The complete case verifier runs before the staged case is promoted to a new destination. No existing destination is intentionally overwritten.

## Trust boundaries

The bundle inventory is unsigned. A party able to rewrite a bundle can also rewrite its inventory. Hashes provide consistency checks, not sender authentication, origin authenticity, truth, authorization, or non-repudiation. This profile does not encrypt data or establish a chain of custody. Use a separately authenticated and appropriately protected transport for sensitive cases.

## Open issues

Cross-platform filesystem semantics, interruption/fault-injection, durability, very large case handling, external signatures and key lifecycle, source-original inclusion policy, and independent implementation interoperability remain untested. This draft is not a public interoperability standard.
