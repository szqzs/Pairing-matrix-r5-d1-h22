# Cluster Reproduction Notes

The same certificates can be produced on a cluster by splitting manifest tasks
across workers.  Use absolute paths for every artifact.

Create a manifest:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest \
  --chern-degrees 18 \
  --column-order cheap-probe \
  --columns-per-task 16 \
  --wave-size 64 \
  --shard-mode task \
  --output "$RUN_ROOT/c18/manifest.json"
```

Plan one wave:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py wave \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --wave-index 0 \
  --chern-degrees 18 \
  --output "$RUN_ROOT/c18/waves/wave_000.json"
```

Compute a task or SLURM array task:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --task-index "$SLURM_ARRAY_TASK_ID" \
  --shard-dir "$RUN_ROOT/c18/shards" \
  --shard-mode task \
  --no-repair-existing \
  --output "$RUN_ROOT/c18/worker_summaries/task_${SLURM_ARRAY_TASK_ID}.json"
```

For full-rank degrees, reduce and verify:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --shard-dir "$RUN_ROOT/c18/shards" \
  --shard-mode task \
  --output "$RUN_ROOT/c18/reduce_final.json"

python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate \
  --manifest "$RUN_ROOT/c18/manifest.json" \
  --reduce-output "$RUN_ROOT/c18/reduce_final.json" \
  --second-prime 1000033 \
  --output "$RUN_ROOT/c18/verification_final.json"
```

For the c12 relation, compute all manifest tasks first, then use:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py relation-reduce \
  --manifest "$RUN_ROOT/c12/manifest.json" \
  --shard-dir "$RUN_ROOT/c12/shards" \
  --shard-mode task \
  --chern-degrees 12 \
  --expected-kernel-dimension 1 \
  --output "$RUN_ROOT/c12/relation_reduce_final.json"

python sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-relation-certificate \
  --manifest "$RUN_ROOT/c12/manifest.json" \
  --relation-reduce-output "$RUN_ROOT/c12/relation_reduce_final.json" \
  --second-prime 1000033 \
  --output "$RUN_ROOT/c12/relation_verification_final.json"
```
