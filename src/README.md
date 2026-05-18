# Frozen Source Snapshots

The folders here are reader-facing source snapshots.  They are included so that
the committed certificates can be tied to a concrete version of the JK-only
implementation.

## Folders

- [`jk_only_v5_c16_frozen`](jk_only_v5_c16_frozen/) is the frozen source used
  for the verified full-rank milestones originally published for `c16`, `c17`,
  and `c18`.
- [`jk_only_v5_relation_frozen`](jk_only_v5_relation_frozen/) is the
  relation-capable source snapshot used for the verified `c11`, `c19`, `c20`,
  `c21`, and `c22` milestones, and for the `c12` theorem-assisted candidate
  extractor.

These snapshots are not raw run folders.  Raw manifests, logs, and shards live
outside this repository unless a compact publication artifact explicitly records
them.  The source hashes in each certificate are the link between the public
record and the code that produced it.

For most readers, the best path is:

1. start with the root status table;
2. read the relevant `cXX/README.md`;
3. inspect `certificate.json`;
4. use the source snapshots only when rerunning or auditing the implementation.
