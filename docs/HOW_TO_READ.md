# How To Read This Repository

This repository is meant to be a compact mathematical record, not a raw run
archive.  The first file to read is the status table in the root
[`README.md`](../README.md).

## What Is Being Computed

For each Chern degree `c`, the rows are the Sp-invariant ordinary-degree-22
classes of Chern degree `c`.  The columns are the Sp-invariant `W26` test
basis.  A matrix entry is the Jeffrey-Kirwan pairing of one row with one test
class, evaluated in the JK conventions used by the frozen source code.

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
Use the `Computed W columns` and `Full W?` fields in the status table to see
the scope.

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
The intended modular certificate has rank `43` in a `44`-dimensional source
space, plus a normalized left-kernel vector that annihilates all `W26` columns
modulo the recorded prime.

That modular vector identifies the finite-field relation line.  It is not, by
itself, the final rational relation.  The rational/integer coefficients should
be published only after exact reconstruction and exact JK annihilation
verification over `Q`.

## Where The Engineering Details Live

The root README and degree folders are the mathematical front door.  Cluster
planning, shard mechanics, and longer provenance conventions live in the
specialized docs:

- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md)
- [`RELATION_CERTIFICATE.md`](RELATION_CERTIFICATE.md)
- [`CLUSTER.md`](CLUSTER.md)
