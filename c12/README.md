# Chern Degree 12

Status: pending relation

## Expected Certificate

This degree is reserved for the corank-one relation calculation.  The source
space has dimension `44`, and the target modular certificate should prove rank
`43` with source-side nullity `1`.  The relation verifier is expected to check
that the normalized modular left-kernel vector annihilates all `1039` `W26`
columns.

| Field | Value |
|---|---|
| Certified rank | pending; target 43 |
| Source-side nullity | pending; target 1 |
| Source dimension | 44 |
| W-basis dimension | 1039 |
| Expected selected minor size | 43 x 43 |
| Computed W columns | pending |
| Full W-basis covered | pending; required for the modular relation check |
| Primary prime | TBD |
| Second prime | TBD |
| Relation certificate | pending `relation_certificate.json` |
| Rational coefficients | not published |

Verified relation files will be added here after the c12 run passes
`relation-reduce` and `verify-relation-certificate`.

The modular relation certificate, when published, will not by itself be the
final rational relation.  Rational/integer coefficients require a separate
exact reconstruction and exact JK annihilation verification over `Q`.
