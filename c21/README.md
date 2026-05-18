# Chern Degree 21

Status: verified

## What This Certifies

The committed certificate proves a full-rank modular JK pairing result for
Chern degree `21`.  The selected `1 x 1`
minor has nonzero determinant modulo the primary prime, and the certificate was
checked again at the second prime recorded below.

| Field | Value |
|---|---|
| Rank | 1 |
| Source-side nullity | 0 |
| Source dimension | 1 |
| W-basis dimension | 1039 |
| Computed W columns | 8/1039 |
| Computed entries | 8 |
| Full W-basis covered | no |
| Primary prime | 2305843009213693951 |
| Second prime | 1000033 |
| Selected minor size | 1 x 1 |
| Certificate | [certificate.json](certificate.json) |
| Computed-column summary | [computed_entries.README.md](computed_entries.README.md) |
| Computed columns | [computed_columns_mod_p.json.gz](computed_columns_mod_p.json.gz) |
| Manifest SHA256 | `4541bdb6050e72efd77c89913cdd93312e28cde62a4dbb2a7cbbbfa260a8708d` |
| Reduce SHA256 | `e77025e57ea6c0524d778dcbe6f22836939a7febd78090277947532aced871c7` |
| Verification SHA256 | `3c2c665e645c47a0693bfd116e73dcfa62405541423d69b45e2edcff7b530cf5` |

The full selected row and column lists, determinant, hashes, and exact command
provenance are in [certificate.json](certificate.json).  The computed-column
export records the modular columns actually computed for this certificate; it
is not a full matrix unless `Full W-basis covered` says `yes`.

<details>
<summary>Selected rows</summary>

- `f2^9 f3`

</details>

<details>
<summary>Selected columns</summary>

- `a2 f2^11`

</details>

<details>
<summary>Exact commands</summary>

- `manifest`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest --chern-degrees 21 --column-order cheap-probe --columns-per-task 8 --wave-size 32 --shard-mode task --source-degree 22 --w-degree 26 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/manifest.json`
- `reduce`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/manifest.json --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/shards --shard-mode task --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/reduce_final.json`
- `verify_certificate`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/manifest.json --reduce-output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/reduce_final.json --second-prime 1000033 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/verification_final.json`
- `worker`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/manifest.json --task-index '<task_index_spec>' --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c21/shards --shard-mode task --no-repair-existing --output '<per-batch-worker-summary.json>'; exact per-batch commands are recorded in the raw strict-run ledger`

</details>
