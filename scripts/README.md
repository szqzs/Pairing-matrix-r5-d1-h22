# Scripts

This directory is reserved for small extraction or validation helpers that
produce compact verified records from v5 rank or relation artifacts.

Scripts should never copy raw shards or caches into this repository.

Use `extract_verified_result.py` after a Chern-degree run has passed
the final, non-`--allow-in-progress` `verify-certificate` step:

```bash
python scripts/extract_verified_result.py \
  --chern-degree 18 \
  --manifest /path/to/work/c18/manifest.json \
  --reduce /path/to/work/c18/reduce.json \
  --verification /path/to/work/c18/verification.json \
  --manifest-command "python ... cluster_rank_driver.py manifest ..." \
  --worker-command "python ... cluster_rank_driver.py worker ..." \
  --reduce-command "python ... cluster_rank_driver.py reduce ..." \
  --verify-command "python ... cluster_rank_driver.py verify-certificate --second-prime 1000033 ..."
```

The script refuses to write `cXX/certificate.json` unless the verification
artifact passed, the reduce artifact has final status `passed`, the second
prime check is present by default, and all manifest/reduce/verification hashes
agree.

For strict runs, also pass the raw ledger/provenance paths so the compact
certificate can record their hashes without committing those raw files:

```bash
python scripts/extract_verified_result.py \
  --chern-degree 18 \
  --manifest /absolute/run/c18/manifest.json \
  --reduce /absolute/run/c18/reduce_final.json \
  --verification /absolute/run/c18/verification_final.json \
  --run-ledger /absolute/run/c18/ledger.jsonl \
  --run-provenance /absolute/run/c18/provenance.json \
  --manifest-command "..." \
  --worker-command "..." \
  --reduce-command "..." \
  --verify-command "..."
```

Use `extract_relation_certificate.py` for the c12-style corank-one relation
certificate after `relation-reduce` and `verify-relation-certificate` both
pass:

```bash
python scripts/extract_relation_certificate.py \
  --chern-degree 12 \
  --manifest /absolute/run/c12/manifest.json \
  --relation-reduce /absolute/run/c12/relation_reduce_final.json \
  --verification /absolute/run/c12/relation_verification_final.json \
  --manifest-command "..." \
  --worker-command "..." \
  --relation-reduce-command "..." \
  --verify-command "..."
```

Use `export_computed_columns.py` to publish the matrix columns actually
computed for a verified certificate.  The export is intentionally scoped as
`computed_shards_only`; it is a full matrix only when `full_w_basis_covered`
is true.

After extracting a new verified full-rank degree, the publication sequence is:

1. run `extract_verified_result.py`;
2. run `export_computed_columns.py`;
3. update `summary.json`;
4. run `refresh_degree_readmes.py`;
5. run `validate_publication.py --all`.

This keeps the root table, summary, degree README, certificate, and computed
column export in sync.

For the current c12 theorem-assisted milestone, publish
`c12/theorem_assisted_candidate.json` separately from any later full modular
relation certificate.  The c12 folder should say explicitly that the artifact
identifies the candidate line using the external uniqueness theorem and does
not check all `1039` `W26` columns.

If a later full c12 modular relation certificate is produced, publish it
separately from any rational/integer relation coefficient artifact.  The
relation folder should also get a relation-compatible committed column export
so readers can inspect the modular annihilation data without rerunning the full
computation.

Use `validate_publication.py` for a lightweight check of the committed public
record:

```bash
python scripts/validate_publication.py --all
```

This validates `summary.json`, the root status table, degree READMEs,
certificates, and computed-column exports.  It does not recompute JK entries.

Use `refresh_degree_readmes.py` after changing the verified-degree README
template:

```bash
python scripts/refresh_degree_readmes.py --all
```

This rewrites only verified `cXX/README.md` files from committed certificates
and computed-column exports.
