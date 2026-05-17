# Pairing Matrix Records for Rank 5, Degree 1, Genus 2, Ordinary Degree 22

This repository is the clean public record for the JK-only reproduction of the
pairing-matrix rank computations for the cohomology ring of the moduli space of
rank 5, genus 2 vector bundles in determinant degree 1.

Only verified milestones should be committed here. Raw worker shards, local
caches, ledgers, logs, and exploratory dumps should stay outside this
repository.

## Status

| Chern degree | Folder | Status | Rank | Nullity | Certificate |
|---:|---|---|---:|---:|---|
| 11 | [c11](c11/) | pending | TBD | TBD | pending |
| 12 | [c12](c12/) | pending | TBD | TBD | pending |
| 13 | [c13](c13/) | pending | TBD | TBD | pending |
| 14 | [c14](c14/) | pending | TBD | TBD | pending |
| 15 | [c15](c15/) | pending | TBD | TBD | pending |
| 16 | [c16](c16/) | pending | TBD | TBD | pending |
| 17 | [c17](c17/) | verified | 28 | 0 | [certificate.json](c17/certificate.json) |
| 18 | [c18](c18/) | verified | 16 | 0 | [certificate.json](c18/certificate.json) |
| 19 | [c19](c19/) | pending | TBD | TBD | pending |
| 20 | [c20](c20/) | pending | TBD | TBD | pending |
| 21 | [c21](c21/) | pending | TBD | TBD | pending |
| 22 | [c22](c22/) | pending | TBD | TBD | pending |

## JK-Only Algorithm Summary

The computation uses only the Jeffrey-Kirwan formula from Theorem 9.6 and
Lemma 9.10 of Jeffrey-Kirwan, specialized to rank 5, genus 2, determinant
degree 1.

For each Chern degree `c`, the code builds the JK Sp-invariant source basis in
ordinary degree 22 and pairs it against the JK Sp-invariant `W26` test basis.
Each entry is evaluated modulo a certified large prime. Columns are ordered by
a cheap workload score or by a small JK probe, then row-reduced incrementally.
A rank claim is accepted only after a selected square minor has nonzero
determinant modulo the prime.

The distributed workflow is:

1. Build a manifest that records the exact formula/code hashes, basis digests,
   prime, task order, and shard mode.
2. Compute task-bundle shards for the manifest.
3. Reduce verified shards to a selected-minor certificate.
4. Run `verify-certificate`, which recomputes the selected minor directly from
   the JK evaluator and checks the determinant and matrix hash. A second prime
   may be supplied as an additional nonvanishing check.
5. Extract the compact result only from the final reduce and final
   `verify-certificate` artifact. Intermediate `--allow-in-progress`
   verification artifacts are continuation gates only.
6. Commit only the compact verified summary for that Chern degree.

The planned staged order is `c18`, `c17`, then `c16,c15,c13,c14`, then
`c19,c20,c21,c22`, and finally `c12,c11`. The order does not affect the
certificate, but it keeps the canaries and hardest middle cases separated.

## Local Reproduction

Run from the workspace that contains both the v5 implementation checkout and
this publication repository. The strict runner writes raw artifacts into an
absolute timestamped run directory and records the exact per-batch commands in
its ledger:

```bash
RUN_ROOT="/absolute/path/to/jk_v5_runs/$(date -u +%Y%m%dT%H%M%SZ)"

python sp_invariant_fast_algorithm_v5/jk_only/strict_degree_runner.py run-degree \
  --chern-degree 18 \
  --run-root "$RUN_ROOT" \
  --column-order cheap-probe \
  --columns-per-task 16 \
  --wave-size 64 \
  --task-batch-size 4 \
  --second-prime 1000033 \
  --extract-publication
```

The runner reduces and verifies after each small task batch. It publishes to
the matching `cXX/` folder only after the final reduce has status `passed` and
the final certificate verification has passed with the second prime.

## Cluster Reproduction

Use absolute paths in every command. Never rely on the driver defaults for
`--manifest`, `--shard-dir`, or `--output`.

Create a wave plan:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py wave \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --wave-index 0 \
  --chern-degrees 18 \
  --output "$RUN_ROOT/c18/waves/wave_000.json"
```

Submit one SLURM array task per planned manifest task, or a small explicit
task range:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --task-index "$SLURM_ARRAY_TASK_ID" \
  --shard-dir "$RUN_ROOT/c18/shards" \
  --shard-mode task \
  --no-repair-existing \
  --output "$RUN_ROOT/c18/worker_summaries/task_${SLURM_ARRAY_TASK_ID}.json"
```

Reduce and verify after each submitted batch:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --shard-dir "$RUN_ROOT/c18/shards" \
  --shard-mode task \
  --output "$RUN_ROOT/c18/reductions/reduce_wave000_batch000.json"

python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --reduce-output "$RUN_ROOT/c18/reductions/reduce_wave000_batch000.json" \
  --allow-in-progress \
  --output "$RUN_ROOT/c18/verifications/verification_wave000_batch000.json"
```

For the final publication certificate, omit `--allow-in-progress` and supply
the second prime:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --reduce-output "$RUN_ROOT/c18/reduce_final.json" \
  --second-prime 1000033 \
  --output "$RUN_ROOT/c18/verification_final.json"
```

For later waves, provide both the prior reduce output and its verification
artifact:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py wave \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --wave-index 1 \
  --previous-reduce "$RUN_ROOT/c18/reductions/reduce_wave000_batch000.json" \
  --previous-verification "$RUN_ROOT/c18/verifications/verification_wave000_batch000.json" \
  --output "$RUN_ROOT/c18/waves/wave_001.json"
```

## Result Folder Contents

Each `cXX/` folder should contain:

- `README.md`: compact human-readable rank/nullity and command record.
- `certificate.json`: compact selected-minor certificate and provenance.
- optional `notes.md`: short comments about retries or environment issues.

Do not commit raw shards, large caches, full matrices, or exploratory logs.
