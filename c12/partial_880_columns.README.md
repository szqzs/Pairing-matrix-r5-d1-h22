# Partial c12 Pairing Columns Checkpoint

This folder checkpoint records the primary-prime c12 full-column run after it
was intentionally paused.  It preserves the completed modular pairing columns
so the run can be resumed and audited later.

This is not a theorem-assisted relation candidate and not a full relation
certificate.  It does not check all `1039` degree-26 `W26` columns.

| Field | Value |
|---|---:|
| Source rows | 44 |
| W26 columns | 1039 |
| Completed columns | 880 |
| Completed entries | 38720 |
| Completed task bundles | 55/65 |
| Full W26 covered | no |
| Primary prime | 2305843009213693951 |

Files:

- [`partial_880_columns_checkpoint.json`](partial_880_columns_checkpoint.json) records the checkpoint metadata and missing task bundles.
- [`partial_880_columns_mod_p.json.gz`](partial_880_columns_mod_p.json.gz) records the completed modular column vectors.

The missing task bundles are `50, 51, 55, 57, 58, 59, 61, 62, 63, 64`.
