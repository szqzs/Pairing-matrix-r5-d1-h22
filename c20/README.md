# Chern Degree 20

Status: verified

## What This Certifies

The committed certificate proves a full-rank modular JK pairing result for
Chern degree `20`.  The selected `4 x 4`
minor has nonzero determinant modulo the primary prime, and the certificate was
checked again at the second prime recorded below.

| Field | Value |
|---|---|
| Rank | 4 |
| Source-side nullity | 0 |
| Source dimension | 4 |
| W-basis dimension | 1039 |
| Computed W columns | 8/1039 |
| Computed entries | 32 |
| Full W-basis covered | no |
| Primary prime | 2305843009213693951 |
| Second prime | 1000033 |
| Selected minor size | 4 x 4 |
| Certificate | [certificate.json](certificate.json) |
| Computed-column summary | [computed_entries.README.md](computed_entries.README.md) |
| Computed columns | [computed_columns_mod_p.json.gz](computed_columns_mod_p.json.gz) |
| Manifest SHA256 | `b796df8dc2ef475b9bad0d7f17e3bb8e4e986b73e9b400db6cb7b45108d07562` |
| Reduce SHA256 | `2066a974b88002a8d57b74a9ac9fc630dac6215aa802d1947db5cf9fdb757309` |
| Verification SHA256 | `d87d319ffa21d4aaed23a268ffc4a2316d2be82cfe2e6e824f7e9ee0b431478c` |

The full selected row and column lists, determinant, hashes, and exact command
provenance are in [certificate.json](certificate.json).  The computed-column
export records the modular columns actually computed for this certificate; it
is not a full matrix unless `Full W-basis covered` says `yes`.

<details>
<summary>Selected rows</summary>

- `a2 f2^9`
- `f2^8 f4`
- `f2^8 gamma22`
- `f2^7 f3^2`

</details>

<details>
<summary>Selected columns</summary>

- `f2^13`
- `a2 f2^11`
- `a3 f2^10`
- `a2^2 f2^9`

</details>

<details>
<summary>Exact commands</summary>

- `manifest`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest --chern-degrees 20 --column-order cheap-probe --columns-per-task 8 --wave-size 32 --shard-mode task --source-degree 22 --w-degree 26 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/manifest.json`
- `reduce`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/manifest.json --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/shards --shard-mode task --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/reduce_final.json`
- `verify_certificate`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/manifest.json --reduce-output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/reduce_final.json --second-prime 1000033 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/verification_final.json`
- `worker`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/manifest.json --task-index '<task_index_spec>' --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c20/shards --shard-mode task --no-repair-existing --output '<per-batch-worker-summary.json>'; exact per-batch commands are recorded in the raw strict-run ledger`

</details>
