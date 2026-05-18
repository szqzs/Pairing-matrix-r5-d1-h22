# C12 Theorem-Assisted Candidate

The current `c12` artifact is not a full modular relation certificate.  It is a
theorem-assisted identification of the candidate relation line.

## Logical Form

The argument has two ingredients.

First, an external Higgs-moduli theorem says that the relevant relation in
ordinary degree `22` is unique up to scalar, Sp-invariant, Chern-homogeneous,
and lies in the Chern-degree-12 source space used here.

Second, the JK computation finds a selected rank-43 submatrix inside the
44-dimensional `c12` source.  Therefore the left kernel of that selected
submatrix is one-dimensional.

Assuming the theorem, the theorem-guaranteed relation line must lie in that
one-dimensional selected-kernel line.  Thus the selected JK submatrix identifies
the candidate line needed for the Higgs-moduli argument.

## Current Computed Evidence

The current candidate artifact records:

- source dimension `44`;
- selected rank `43` modulo the primary prime;
- one-dimensional selected left kernel;
- selected nonzero minor determinant modulo the primary prime;
- zero pairing against the `784` loaded `W26` columns used by the partial c12
  run;
- rational reconstruction of the modular kernel to a primitive integer vector;
- a second-prime selected-minor and line-comparison check, when the
  `second_prime` field is present.

## What Is Not Claimed

This artifact does not claim a full 1039-column JK annihilation certificate.
It also does not give a standalone computational proof that the relation
exists.  The existence and uniqueness input is the external theorem.

The rational coefficients are best read as a reconstructed candidate vector
until an exact-over-`Q` verification or an equally explicit independent
verification artifact is published.

## Stronger Certificate

A stronger full modular relation certificate would prove rank `43` and verify
that the normalized left-kernel vector annihilates all `1039` `W26` columns
modulo the recorded prime(s).  That stronger certificate is described in
[`RELATION_CERTIFICATE.md`](RELATION_CERTIFICATE.md), but it is not the current
public claim for `c12`.
