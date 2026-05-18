# Full Relation Certificate

This page describes the stronger full modular relation certificate.  The
current public `c12` object is weaker and theorem-assisted; see
[`C12_THEOREM_ASSISTED_CANDIDATE.md`](C12_THEOREM_ASSISTED_CANDIDATE.md).

A full `c12` relation certificate is not a full-rank claim.  It has two parts.

First, the reducer finds 43 selected source rows and 43 selected `W26` columns
whose selected minor has nonzero determinant modulo the primary prime.  This
certifies that the JK pairing matrix has rank at least 43.

Second, the reducer constructs a normalized left-kernel vector `u` of length 44
from that selected minor.  The verifier then checks `u^T M[:,j] = 0` for every
`W26` column `j`.  This certifies that the rank is at most 43 modulo the prime.
Together, these prove corank one modulo that prime across the full `W26` test
basis.

The second-prime check repeats the selected-minor and full-annihilation
certificate at a different prime.  It is a strong second-prime consistency
check.  It is not by itself a rational reconstruction of the relation vector;
an exact rational relation should be published with a separate
reconstruction/exact-verification artifact.

The Higgs-moduli conclusion uses an additional theorem outside this
computation: the relevant `H^22` relation is unique and lies in the invariant
Chern-degree-12 candidate space.  For the current theorem-assisted `c12`
artifact, that theorem is part of the claim.  A full relation certificate would
be stronger because it would check annihilation against all `1039` `W26`
columns directly.
