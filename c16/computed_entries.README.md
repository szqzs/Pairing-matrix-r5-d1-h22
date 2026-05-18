# Computed Pairing Entries for c16

`computed_columns_mod_p.json.gz` contains the pairing columns actually computed modulo the primary
prime for this certificate.

This is not automatically a full pairing matrix.  For this artifact:

| Field | Value |
|---|---:|
| Source rows | 53 |
| W-basis columns | 1039 |
| Computed columns | 128 |
| Computed entries | 6784 |
| Full W-basis covered | no |

The column vectors are ordered by source-row index and each column records its
`w_index`, `w_name`, vector hash, and whether it was used in the selected-minor
rank certificate.
