# Scripts

This directory is reserved for small extraction or validation helpers that
produce compact verified records from v5 `manifest`, `reduce`, and
`verify-certificate` artifacts.

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
