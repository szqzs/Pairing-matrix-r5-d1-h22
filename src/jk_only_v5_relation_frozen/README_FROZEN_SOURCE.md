# Frozen JK-Only v5 Relation Source

This folder is a reader-facing copy of the relation-capable JK-only v5 source
prepared after the verified c16/c17/c18 run was paused.

It includes the c12 corank-one relation infrastructure:

- `cluster_rank_driver.py relation-reduce`
- `cluster_rank_driver.py verify-relation-certificate`
- `strict_relation_runner.py`
- the shared JK formula, basis, and modular evaluator layers
- the publication extractors in `publication_scripts/`

`SOURCE_MANIFEST.sha256` records relative per-file SHA256 hashes for this
frozen source copy.

Use this folder as the source reference for future c12 relation certificates.
The older `src/jk_only_v5_c16_frozen/` folder remains the source reference for
the already verified c16/c17/c18 rank certificates.
