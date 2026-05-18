# Chern Degree 12

Status: theorem-assisted candidate

This folder records the current `c12` relation candidate line.  It is not a
full `1039`-column JK relation certificate.

The external Higgs-moduli theorem says that the relevant ordinary-degree-22
relation is unique up to scalar, Sp-invariant, Chern-homogeneous, and lies in
this Chern-degree-12 source space.  The JK computation identifies the line by
finding a rank-43 selected submatrix inside the 44-dimensional source space.

## Summary

| Field | Value |
|---|---:|
| Selected rank | 43 |
| Selected source-side nullity | 1 |
| Source dimension | 44 |
| W-basis dimension | 1039 |
| Loaded W columns checked | 784 |
| Full W-basis covered | no |
| Primary prime | 2305843009213693951 |
| Second prime | 1000033 |
| Candidate artifact | [theorem_assisted_candidate.json](theorem_assisted_candidate.json) |
| Coefficients | [relation_coefficients.md](relation_coefficients.md) |

## Paused Full-Column Checkpoint

A later primary-prime full-column run was intentionally paused after `880` of
the `1039` degree-26 `W26` columns had been computed.  That checkpoint is
published separately so the partial data is not lost:

- [partial checkpoint summary](partial_880_columns.README.md)
- [partial checkpoint metadata](partial_880_columns_checkpoint.json)
- [partial modular column vectors](partial_880_columns_mod_p.json.gz)

This checkpoint is not a full relation certificate and does not change the
theorem-assisted status recorded above.

## What This Identifies

The selected `43 x 43` JK minor is nonzero modulo the primary prime.  Its left
kernel in the 44-dimensional source is therefore one-dimensional.  Under the
external uniqueness theorem, the theorem-guaranteed relation line must be this
selected-kernel line.

The candidate vector also pairs to zero against all `784` loaded `W26` columns
available from the stopped c12 run.  The selected minor and the reconstructed
rational line were additionally checked at the second prime `1000033`.

## What Is Not Claimed

This is not a full modular relation certificate: the remaining `255` `W26`
columns were not checked by this artifact.  It is also not a standalone
computational proof that the Higgs-moduli relation exists; that existence and
uniqueness input comes from the external theorem.

The reconstructed primitive integer coefficients are published as the
candidate vector for this theorem-assisted argument.  A later exact-over-`Q`
verification can be added as a separate artifact.
