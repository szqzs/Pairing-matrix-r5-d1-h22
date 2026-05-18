# Chern Degree 16

Status: verified

| Field | Value |
|---|---|
| Rank | 53 |
| Nullity | 0 |
| Source dimension | 53 |
| W-basis dimension | 1039 |
| Primary prime | 2305843009213693951 |
| Second prime | 1000033 |
| Selected rows | a2^3 f2^5, a2^2 f2^4 f4, a2^2 f2^4 gamma22, a2^2 f2^3 f3^2, a2 a3 f2^4 f3, a2 a4 f2^5, a2 f2^4 gamma24, a2 f2^3 f3 f5, a2 f2^3 f3 gamma23, a2 f2^3 f4^2, a2 f2^3 f4 gamma22, a2 f2^3 gamma22^2, a2 f2^2 f3^2 f4, a2 f2^2 f3^2 gamma22, a2 f2 f3^4, a3^2 f2^5, a3 f2^4 f5, a3 f2^4 gamma23, a3 f2^3 f3 f4, a3 f2^3 f3 gamma22, a3 f2^2 f3^3, a4 f2^4 f4, a4 f2^3 f3^2, a5 f2^4 f3, f2^3 f3 gamma25, f2^3 f4 gamma24, f2^3 f5^2, f2^3 f5 gamma23, f2^3 gamma22 gamma24, f2^2 f3^2 gamma24, f2^2 f3 f4 f5, f2^2 f3 f4 gamma23, f2^2 f3 f5 gamma22, f2^2 f3 gamma22 gamma23, f2^2 f4^3, f2^2 f4^2 gamma22, f2^2 f4 gamma22^2, f2 f3^3 f5, f2 f3^3 gamma23, f2 f3^2 f4^2, f2 f3^2 f4 gamma22, f2 f3^2 gamma22^2, f3^4 f4, f3^4 gamma22, a2 f2^4 gamma33, a4 f2^4 gamma22, f2^4 gamma35, f2^4 gamma44, f2^3 f3 gamma34, f2^3 f4 gamma33, f2^3 gamma22 gamma33, f2^3 gamma23^2, f2^2 f3^2 gamma33 |
| Selected columns | f2^13, a2 f2^11, a3 f2^10, a2^2 f2^9, a4 f2^9, a2 a3 f2^8, a5 f2^8, a2^3 f2^7, a2 a4 f2^7, a3^2 f2^7, a2^2 a3 f2^6, a2 a5 f2^6, a3 a4 f2^6, a2^4 f2^5, a2^2 a4 f2^5, a2 a3^2 f2^5, a3 a5 f2^5, a4^2 f2^5, a2^3 a3 f2^4, a2^2 a5 f2^4, a2 a3 a4 f2^4, a3^3 f2^4, a4 a5 f2^4, a2^5 f2^3, a2^3 a4 f2^3, a2^2 a3^2 f2^3, a2 a3 a5 f2^3, a2 a4^2 f2^3, a3^2 a4 f2^3, a5^2 f2^3, a2^4 a3 f2^2, a2^3 a5 f2^2, a2^2 a3 a4 f2^2, a2 a3^3 f2^2, a2 a4 a5 f2^2, a3^2 a5 f2^2, a3 a4^2 f2^2, a2^6 f2, a2^4 a4 f2, a2^3 a3^2 f2, a2^2 a3 a5 f2, a2^2 a4^2 f2, a2 a3^2 a4 f2, a2 a5^2 f2, f2^4 gamma55, f2^5 gamma45, f2^6 gamma35, f2^6 gamma44, f2^7 gamma25, f2^7 gamma34, f2^8 gamma24, f2^8 gamma33, f2^9 gamma23 |
| Certificate | [certificate.json](certificate.json) |
| Manifest SHA256 | `0e1fed76bd3f0f78f9ab52bec544a6f569a305db68d250799d7b6397935c3c9c` |
| Reduce SHA256 | `3d778cb04fd6aa6070de8f128b44132438bd6e9fd6ab5ce00e74f67e514627af` |
| Verification SHA256 | `dfa1d1f033c7bcb89f3253603f43170c95c475720a9ce2f4d4d50d578b0ea3f6` |

## Exact Commands

- `manifest`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest --chern-degrees 16 --column-order cheap-probe --columns-per-task 16 --wave-size 64 --shard-mode task --source-degree 22 --w-degree 26 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/manifest.json`
- `worker`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/manifest.json --task-index '<task_index_spec>' --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/shards --shard-mode task --no-repair-existing --output '<per-batch-worker-summary.json>'; exact per-batch commands are recorded in the raw strict-run ledger`
- `reduce`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/manifest.json --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/shards --shard-mode task --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/reduce_final.json`
- `verify_certificate`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/manifest.json --reduce-output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/reduce_final.json --second-prime 1000033 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c16/verification_final.json`
