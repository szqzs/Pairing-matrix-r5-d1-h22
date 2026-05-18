# Chern Degree 22

Status: verified

## What This Certifies

The committed certificate proves a full-rank modular JK pairing result for
Chern degree `22`.  The selected `1 x 1`
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
| Manifest SHA256 | `61972dcfced6f6490daa507db65c6fd660519a126de58dc085be3af5570a7611` |
| Reduce SHA256 | `1289792abf06602601cf992a6c9d4739856a40a54ba807b75c9f6ec1d2f520f2` |
| Verification SHA256 | `71e10375ec2b3cdae9a30c2c0da2cfa406c7a294e85c082105c61ab05ebb60b7` |

The full selected row and column lists, determinant, hashes, and exact command
provenance are in [certificate.json](certificate.json).  The computed-column
export records the modular columns actually computed for this certificate; it
is not a full matrix unless `Full W-basis covered` says `yes`.

<details>
<summary>Selected rows</summary>

- `f2^11`

</details>

<details>
<summary>Selected columns</summary>

- `f2^13`

</details>

<details>
<summary>Exact commands</summary>

- `manifest`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest --chern-degrees 22 --column-order cheap-probe --columns-per-task 8 --wave-size 32 --shard-mode task --source-degree 22 --w-degree 26 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/manifest.json`
- `reduce`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/manifest.json --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/shards --shard-mode task --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/reduce_final.json`
- `verify_certificate`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/manifest.json --reduce-output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/reduce_final.json --second-prime 1000033 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/verification_final.json`
- `worker`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/manifest.json --task-index '<task_index_spec>' --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c22/shards --shard-mode task --no-repair-existing --output '<per-batch-worker-summary.json>'; exact per-batch commands are recorded in the raw strict-run ledger`

</details>
