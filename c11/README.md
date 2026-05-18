# Chern Degree 11

Status: verified

| Field | Value |
|---|---|
| Rank | 7 |
| Nullity | 0 |
| Source dimension | 7 |
| W-basis dimension | 1039 |
| Primary prime | 2305843009213693951 |
| Second prime | 1000033 |
| Selected rows | a2^4 a3, a2^3 a5, a2^2 a3 a4, a2 a3^3, a2 a4 a5, a3^2 a5, a3 a4^2 |
| Selected columns | f2^13, a2 f2^11, a3 f2^10, a2^2 f2^9, a4 f2^9, a2 a3 f2^8, a5 f2^8 |
| Certificate | [certificate.json](certificate.json) |
| Manifest SHA256 | `f77247a4efc6ae66dbecd7f39a8ee8b62b5169320c448ffa86d2f54a3bdc789e` |
| Reduce SHA256 | `3db3515782cc4a632b211f13f2ad12b87c215e91c36f52f2da865722244e403b` |
| Verification SHA256 | `aa39e8466911e965b61a0bfc378d04940e66042f3f01c909bf286086ffe0d478` |

## Exact Commands

- `manifest`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest --chern-degrees 11 --column-order cheap-probe --columns-per-task 8 --wave-size 32 --shard-mode task --source-degree 22 --w-degree 26 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/manifest.json`
- `worker`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/manifest.json --task-index '<task_index_spec>' --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/shards --shard-mode task --no-repair-existing --output '<per-batch-worker-summary.json>'; exact per-batch commands are recorded in the raw strict-run ledger`
- `reduce`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/manifest.json --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/shards --shard-mode task --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/reduce_final.json`
- `verify_certificate`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/manifest.json --reduce-output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/reduce_final.json --second-prime 1000033 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/easy_degrees_20260518T035205Z/c11/verification_final.json`
