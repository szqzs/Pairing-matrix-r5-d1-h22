# How To Read This Repository

This repository is meant to be a compact mathematical record, not a raw run
archive.  The first file to read is the status table in the root
[`README.md`](../README.md).

## What Is Being Computed

For each Chern degree `c`, the rows are the Sp-invariant ordinary-degree-22
classes of Chern degree `c`.  The columns are the Sp-invariant `W26` test
basis.  A matrix entry is the Jeffrey-Kirwan pairing of one row with one test
class, evaluated in the JK conventions used by the frozen source code.

For the formula dictionary and implementation checks, read
[`JK_VERIFICATION.md`](JK_VERIFICATION.md).  That page explains how the code
specializes Jeffrey-Kirwan's formula and how the source path is guarded against
legacy convention changes.

## What A Verified Full-Rank Degree Proves

For a verified full-rank degree, `certificate.json` records a selected square
minor whose determinant is nonzero modulo the primary prime.  The verifier
recomputes that selected minor from the JK evaluator, and also checks the same
certificate at a second prime.

This proves the displayed rank over the recorded finite fields.  For the
current full-rank certificates, a full `W26` matrix export is not needed: the
selected minor is the proof object.

When used as rational rank evidence, the relevant nonzero modular minor is
understood as the reduction of the JK formula at a prime where the recorded
arithmetic is valid.  Exact rational relation coefficients are not inferred
from this alone; they require the separate exact reconstruction/verification
step described for `c12`.

## What The Computed Columns File Contains

`computed_columns_mod_p.json.gz` records the modular pairing columns actually
computed during the certificate run.  It is not automatically a full matrix.
Use the `Computed W columns` field in the status table for a quick count.  The
per-degree folder records whether the committed column export covers the full
`W26` basis.

Each column stores:

- its `w_index` and `w_name`;
- the vector of pairings modulo the primary prime;
- a hash of that vector;
- whether that column was used in the selected-minor certificate.

## How To Inspect One Degree

For a quick human check, open a folder such as [`c22`](../c22/):

1. Read `README.md` for the mathematical claim and scope.
2. Open `certificate.json` for the selected rows, selected columns, determinant,
   primes, hashes, and exact provenance commands.
3. Open `computed_entries.README.md` to see how many matrix columns are
   committed.
4. If desired, inspect `computed_columns_mod_p.json.gz` for the actual modular
   entries.

For an automatic consistency check of the committed publication files, run:

```bash
python scripts/validate_publication.py --all
```

This validation is intentionally lightweight.  It checks the public artifacts,
not a full JK recomputation.

## Why c12 Is Different

The `c12` calculation is a relation calculation, not a full-rank calculation.
The current public object is a theorem-assisted candidate line, not the full
modular relation certificate.

The external theorem says that the relevant Higgs-moduli relation is a unique
line in this invariant Chern-degree-12 source space.  The JK computation then
identifies that line by finding a rank-43 selected submatrix in the
44-dimensional source.  This is enough for the theorem-assisted identification,
but it is not the same as checking annihilation against all `1039` `W26`
columns.

The rational/integer coefficients should still be read with the exact scope
recorded in the c12 artifact.

## Where The Engineering Details Live

The root README and degree folders are the mathematical front door.  Cluster
planning, shard mechanics, and longer provenance conventions live in the
specialized docs:

- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md)
- [`JK_VERIFICATION.md`](JK_VERIFICATION.md)
- [`C12_THEOREM_ASSISTED_CANDIDATE.md`](C12_THEOREM_ASSISTED_CANDIDATE.md)
- [`RELATION_CERTIFICATE.md`](RELATION_CERTIFICATE.md)
- [`CLUSTER.md`](CLUSTER.md)
