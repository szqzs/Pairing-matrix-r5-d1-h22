# Chern Degree 17

Status: verified

| Field | Value |
|---|---|
| Rank | 28 |
| Nullity | 0 |
| Source dimension | 28 |
| W-basis dimension | 1039 |
| Primary prime | 2305843009213693951 |
| Second prime | 1000033 |
| Selected rows | a2^2 f2^5 f3, a2 a3 f2^6, a2 f2^5 f5, a2 f2^5 gamma23, a2 f2^4 f3 f4, a2 f2^4 f3 gamma22, a2 f2^3 f3^3, a3 f2^5 f4, a3 f2^4 f3^2, a4 f2^5 f3, a5 f2^6, f2^5 gamma25, f2^4 f3 gamma24, f2^4 f4 f5, f2^4 f4 gamma23, f2^4 f5 gamma22, f2^4 gamma22 gamma23, f2^3 f3^2 f5, f2^3 f3^2 gamma23, f2^3 f3 f4^2, f2^3 f3 f4 gamma22, f2^3 f3 gamma22^2, f2^2 f3^3 f4, f2^2 f3^3 gamma22, f2 f3^5, a3 f2^5 gamma22, f2^5 gamma34, f2^4 f3 gamma33 |
| Selected columns | f2^13, a2 f2^11, a3 f2^10, a2^2 f2^9, a4 f2^9, a2 a3 f2^8, a5 f2^8, a2^3 f2^7, a2 a4 f2^7, a3^2 f2^7, a2^2 a3 f2^6, a2 a5 f2^6, a3 a4 f2^6, a2^4 f2^5, a2^2 a4 f2^5, a2 a3^2 f2^5, a3 a5 f2^5, a4^2 f2^5, a2^3 a3 f2^4, a2^2 a5 f2^4, a2 a3 a4 f2^4, a3^3 f2^4, a4 a5 f2^4, a2^5 f2^3, a2^3 a4 f2^3, f2^4 gamma55, f2^5 gamma45, f2^6 gamma35 |
| Certificate | [certificate.json](certificate.json) |
| Manifest SHA256 | `d117d80eb022c0739a2bc18e9492ca4c034bdf935827787f7239ecb343f6f4f8` |
| Reduce SHA256 | `c2c102614c4c1039510e2e1bcb5715b959913dc249385c3c2ba48eb865abdc23` |
| Verification SHA256 | `1fc959d2bfcbde32c0190b6169e6ef9d291fcf74e8a38ee78a0f8901d7cc85c6` |

## Exact Commands

- `manifest`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest --chern-degrees 17 --column-order cheap-probe --columns-per-task 16 --wave-size 64 --shard-mode task --source-degree 22 --w-degree 26 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/manifest.json`
- `worker`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/manifest.json --task-index '<task_index_spec>' --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/shards --shard-mode task --no-repair-existing --output '<per-batch-worker-summary.json>'; exact per-batch commands are recorded in the raw strict-run ledger`
- `reduce`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/manifest.json --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/shards --shard-mode task --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/reduce_final.json`
- `verify_certificate`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/manifest.json --reduce-output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/reduce_final.json --second-prime 1000033 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c17/verification_final.json`
