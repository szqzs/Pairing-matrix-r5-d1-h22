# Chern Degree 18

Status: verified

## What This Certifies

The committed certificate proves a full-rank modular JK pairing result for
Chern degree `18`.  The selected `16 x 16`
minor has nonzero determinant modulo the primary prime, and the certificate was
checked again at the second prime recorded below.

| Field | Value |
|---|---|
| Rank | 16 |
| Source-side nullity | 0 |
| Source dimension | 16 |
| W-basis dimension | 1039 |
| Computed W columns | 64/1039 |
| Computed entries | 1024 |
| Full W-basis covered | no |
| Primary prime | 2305843009213693951 |
| Second prime | 1000033 |
| Selected minor size | 16 x 16 |
| Certificate | [certificate.json](certificate.json) |
| Computed-column summary | [computed_entries.README.md](computed_entries.README.md) |
| Computed columns | [computed_columns_mod_p.json.gz](computed_columns_mod_p.json.gz) |
| Manifest SHA256 | `f6dcbba58a7f7e5f2e6799d7e35285e6df7612090dac43681ae8d4af1a91ffe0` |
| Reduce SHA256 | `9fd494d96c55614c40828d3b60af5cc156ab174aeb603c17d457dac869e0b53c` |
| Verification SHA256 | `06917c01659e49d0947dee5083dda66c9593f946724b68f7bc37e34588918797` |

The full selected row and column lists, determinant, hashes, and exact command
provenance are in [certificate.json](certificate.json).  The computed-column
export records the modular columns actually computed for this certificate; it
is not a full matrix unless `Full W-basis covered` says `yes`.

<details>
<summary>Selected rows</summary>

- `a2^2 f2^7`
- `a2 f2^6 f4`
- `a2 f2^6 gamma22`
- `a2 f2^5 f3^2`
- `a3 f2^6 f3`
- `a4 f2^7`
- `f2^6 gamma24`
- `f2^5 f3 f5`
- `f2^5 f3 gamma23`
- `f2^5 f4^2`
- `f2^5 f4 gamma22`
- `f2^5 gamma22^2`
- `f2^4 f3^2 f4`
- `f2^4 f3^2 gamma22`
- `f2^3 f3^4`
- `f2^6 gamma33`

</details>

<details>
<summary>Selected columns</summary>

- `f2^13`
- `a2 f2^11`
- `a3 f2^10`
- `a2^2 f2^9`
- `a4 f2^9`
- `a2 a3 f2^8`
- `a5 f2^8`
- `a2^3 f2^7`
- `a2 a4 f2^7`
- `a3^2 f2^7`
- `a2^2 a3 f2^6`
- `a2 a5 f2^6`
- `a3 a4 f2^6`
- `a2^4 f2^5`
- `a2^2 a4 f2^5`
- `f2^4 gamma55`

</details>

<details>
<summary>Exact commands</summary>

- `manifest`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py manifest --chern-degrees 18 --column-order cheap-probe --columns-per-task 16 --wave-size 64 --shard-mode task --source-degree 22 --w-degree 26 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/manifest.json`
- `reduce`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py reduce --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/manifest.json --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/shards --shard-mode task --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/reduce_final.json`
- `verify_certificate`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py verify-certificate --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/manifest.json --reduce-output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/reduce_final.json --second-prime 1000033 --output /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/verification_final.json`
- `worker`: `/opt/anaconda3/bin/python /Users/siqingzhang/Documents/Playground/sp_invariant_fast_algorithm_v5/jk_only/cluster_rank_driver.py worker --manifest /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/manifest.json --task-index '<task_index_spec>' --shard-dir /Users/siqingzhang/Documents/Playground/jk_v5_runs/long_20260517T223207Z/c18/shards --shard-mode task --no-repair-existing --output '<per-batch-worker-summary.json>'; exact per-batch commands are recorded in the raw strict-run ledger`

</details>
