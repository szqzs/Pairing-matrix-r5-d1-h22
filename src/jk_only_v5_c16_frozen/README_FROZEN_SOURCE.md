# Frozen JK-Only v5 Source Used For c16

This folder is a reader-facing copy of the JK-only v5 implementation state
used to certify the current `c16`, `c17`, and `c18` milestones.

The raw source snapshot made at the beginning of the long run is recorded in
`SOURCE_SNAPSHOT.sha256`.  The per-file hashes used by the computation are also
stored inside each degree's manifest/certificate.

This folder is intentionally frozen.  Later relation-certificate work for
`c12` should live in a separate source folder or in the working v5 tree with a
new source hash, so the old rank certificates remain auditable.
