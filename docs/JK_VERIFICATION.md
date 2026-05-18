# JK Formula Implementation Checks

This page explains what Jeffrey-Kirwan formula is being implemented, how it
specializes to rank `5`, genus `2`, determinant degree `1`, and where the
corresponding factors appear in the frozen v5 source.

The source paper is Jeffrey and Kirwan, *Intersection theory on moduli spaces
of holomorphic bundles of arbitrary rank on a Riemann surface*,
arXiv:alg-geom/9608029, especially Theorem 9.6 and Lemma 9.10.  The frozen
formula ledger is
[`src/jk_only_v5_relation_frozen/JK_THEOREM_9_6_RANK5_G2.md`](../src/jk_only_v5_relation_frozen/JK_THEOREM_9_6_RANK5_G2.md).

## Full Formula First

In Jeffrey-Kirwan notation, set

$$
q(X)=\tau_2(X)+\delta_3\tau_3(X)+\cdots+\delta_n\tau_n(X),
\qquad
B_j(X)=-(dq)_X(h_j),
$$

where `h_j=e_j-e_{j+1}` and `Y_j=X_j-X_{j+1}`.  For a monomial in the
generators, Theorem 9.6 has the following residue form:

$$
\begin{aligned}
&\int_{\mathcal M(n,d)}
\exp(f_2+\delta_3 f_3+\cdots+\delta_n f_n)
\prod_{r=2}^n a_r^{m_r}
\prod_{r=2}^n\prod_{k=1}^{2g}(b_r^k)^{p_{r,k}}
\\
&\quad =
\frac{(-1)^{n_+(g-1)}}{n!}
\sum_{w\in W_{n-1}}
\operatorname*{Res}_{Y_1=0}\cdots
\operatorname*{Res}_{Y_{n-1}=0}
\Biggl[
\frac{
e^{(dq)_X(\widetilde{w c})}
\prod_{r=2}^n \tau_r(X)^{m_r}
}{
D(X)^{2g-2}
\prod_{j=1}^{n-1}(1-e^{-B_j(X)})
}
\\
&\hspace{8em}\cdot
\int_{T^{2g}}
\exp\!\left(
-\sum_{a,b=1}^{n-1}\sum_{j=1}^{g}
\zeta_a^j\zeta_b^{j+g}
\partial^2q_X(\hat u_a,\hat u_b)
\right)
\\
&\hspace{11em}\cdot
\prod_{r=2}^n\prod_{k=1}^{2g}
\left(
\sum_{a=1}^{n-1}(d\tau_r)_X(\hat u_a)\zeta_a^k
\right)^{p_{r,k}}
\Biggr].
\end{aligned}
$$

Lemma 9.10 packages the `T^{2g}` integral into an exterior Gaussian.  In the
form used by the code, this says:

$$
\widehat{\tau}(X)=
-\sum_{a,b=1}^{n-1}\sum_{r,s=2}^n\sum_{j=1}^{g}
s_r^j s_s^{j+g}
(d\tau_r)_X(\hat u_a)
(d\tau_s)_X(\hat u_b)
\bigl(H_q(X)^{-1}\bigr)_{ab}.
$$

Equivalently, the odd part of the JK pairing is obtained by differentiating
`exp(hat_tau)` in the auxiliary odd parameters `s_r^j`, then setting all
`s_r^j=0`.

With that convention, the same formula can be read as:

$$
\begin{aligned}
&\int_{\mathcal M(n,d)}
\exp(f_2+\delta_3 f_3+\cdots+\delta_n f_n)
\prod_{r=2}^n a_r^{m_r}
\prod_{r,k}(b_r^k)^{p_{r,k}}
\\
&\quad =
\frac{(-1)^{n_+(g-1)}}{n!}
\sum_{w\in W_{n-1}}
\operatorname*{Res}_{Y_1=0}\cdots
\operatorname*{Res}_{Y_{n-1}=0}
\left[
\frac{
e^{(dq)_X(\widetilde{w c})}
\prod_{r=2}^n \tau_r(X)^{m_r}
\operatorname{Coeff}_{\prod(b_r^k)^{p_{r,k}}}
\bigl(e^{\widehat{\tau}(X)}\bigr)
}{
D(X)^{2g-2}
\prod_{j=1}^{n-1}(1-e^{-B_j(X)})
}
\right].
\end{aligned}
$$

The rest of this document explains every factor in this formula and then
points to the exact source lines implementing it.

## Dissecting The Paper Formula

Theorem 9.6 computes pairings on the fixed-determinant moduli space `M(n,d)`
by an iterated residue in simple-root coordinates

$$
Y_i=X_i-X_{i+1},\qquad i=1,\ldots,n-1.
$$

Let

$$
q(X)=\tau_2(X)+\delta_3\tau_3(X)+\cdots+\delta_n\tau_n(X),
$$

where `tau_r` is the elementary symmetric invariant polynomial in the
coordinates `x_1,...,x_n` with `sum x_i = 0`.  The paper defines

$$
B_j(X)=-(dq)_X(h_j),\qquad h_j=e_j-e_{j+1}.
$$

For a monomial in the even classes `a_r`, `f_r` and odd classes `b_r^j`, the
formula has this shape:

$$
\begin{aligned}
&\int_{\mathcal M(n,d)}
\exp(f_2+\delta_3 f_3+\cdots+\delta_n f_n)
\prod_r a_r^{m_r}
\prod_{r,j}(b_r^j)^{p_{r,j}}
\\
&\quad =
\frac{(-1)^{n_+(g-1)}}{n!}
\sum_{w\in W_{n-1}}
\operatorname*{Res}_{Y_1=0}\cdots
\operatorname*{Res}_{Y_{n-1}=0}
\left[
\frac{
\exp((dq)_X(\widetilde{w c}))
\prod_r \tau_r(X)^{m_r}
\operatorname{OddPart}(X,\delta,b)
}{
D(X)^{2g-2}
\prod_{j=1}^{n-1}(1-\exp(-B_j(X)))
}
\right].
\end{aligned}
$$

Here `n_+ = n(n-1)/2`, `D(X)` is the product of the positive roots, and
`tilde{w c}` is the representative used by Jeffrey-Kirwan in the simple-root
fundamental domain.  The `OddPart` is the integral over `T^{2g}` in Theorem
9.6(a).  Lemma 9.10 rewrites that torus integral as the coefficient extraction
from an exterior Gaussian:

$$
\widehat{\tau}(X)=
-\sum_{a,b=1}^{n-1}\sum_{r,s=2}^{n}\sum_{j=1}^{g}
s_r^j s_s^{j+g}
(d\tau_r)_X(\hat u_a)
(d\tau_s)_X(\hat u_b)
\bigl(H_q(X)^{-1}\bigr)_{ab}.
$$

Thus the odd-class contribution is obtained by taking the coefficient of the
requested `b`-monomial in `exp(hat_tau)`.

The main pieces are therefore:

- `exp((dq)_X(tilde{w c}))`: the determinant-degree and Weyl-summand
  exponential;
- `prod tau_r(X)^m_r`: the `a_r` classes;
- `Coeff(exp(hat_tau))`: the odd `b_r^j` classes;
- `D(X)^{2g-2}`: the positive-root denominator;
- `prod_j(1-exp(-B_j(X)))`: the simple-root denominator from the JK residue;
- extracting powers of `delta_r`: the `f_r` classes for `r>=3`;
- the initial `exp(f_2)`: the source of the `f_2` factorial.

## Rank 5, Genus 2, Degree 1

For this repository we set

$$
n=5,\qquad g=2,\qquad d=1.
$$

There are four simple-root variables, and the `x_i` are

$$
\begin{aligned}
x_1&=\frac{4Y_1+3Y_2+2Y_3+Y_4}{5},\\
x_2&=\frac{-Y_1+3Y_2+2Y_3+Y_4}{5},\\
x_3&=\frac{-Y_1-2Y_2+2Y_3+Y_4}{5},\\
x_4&=\frac{-Y_1-2Y_2-3Y_3+Y_4}{5},\\
x_5&=\frac{-Y_1-2Y_2-3Y_3-4Y_4}{5}.
\end{aligned}
$$

The generating polynomial is

$$
q=\tau_2+\delta_3\tau_3+\delta_4\tau_4+\delta_5\tau_5.
$$

The ten positive roots are

$$
x_i-x_j=Y_i+Y_{i+1}+\cdots+Y_{j-1},
\qquad 1\le i<j\le 5,
$$

so, since `g=2`, the root denominator is

$$
D(X)^2=\prod_{1\le i<j\le 5}(x_i-x_j)^2.
$$

For determinant degree `1`, we use

$$
\widetilde c=\left(\frac15,\frac15,\frac15,\frac15,-\frac45\right).
$$

At `delta = 0`,

$$
(dq)_X(\widetilde c)=
-\frac{Y_1+2Y_2+3Y_3+4Y_4}{5}.
$$

Because `c` is central, the `W_4` summands coincide.  The factor

$$
\frac{n^g}{n!}\,|W_4|
=\frac{25}{120}\cdot 24
=5
$$

is the scalar prefactor used in the code.  The sign is positive because
`n_+(g-1) = 10`.

For a monomial

$$
\prod_{r=2}^5 a_r^{m_r}
\prod_{r=2}^5 f_r^{\nu_r}
\prod_{r\le s}\gamma_{rs}^{e_{rs}},
$$

the implemented pairing is:

$$
\begin{aligned}
\operatorname{JK}_{5,2,1}
\left(
\prod_{r=2}^5 a_r^{m_r}
\prod_{r=2}^5 f_r^{\nu_r}
\prod_{r\le s}\gamma_{rs}^{e_{rs}}
\right)
&=
5\left(\prod_{r=2}^5 \nu_r!\right)
[\delta_3^{\nu_3}\delta_4^{\nu_4}\delta_5^{\nu_5}]
\\
&\quad\cdot
\operatorname*{Res}_{Y_1=0}
\operatorname*{Res}_{Y_2=0}
\operatorname*{Res}_{Y_3=0}
\operatorname*{Res}_{Y_4=0}
\\
&\quad\cdot
\left[
\frac{
\exp((dq)_X(\widetilde c))
\prod_{r=2}^5 \tau_r(X)^{m_r}
\left(\det H_q(X)/\det H_{\tau_2}(X)\right)^2
\Gamma_{\mathbf e}(X,\delta)
}{
D(X)^2
\prod_{j=1}^4(1-\exp(-B_j(X)))
}
\right].
\end{aligned}
$$

The `f_2` class is already present through `exp(f_2)`, so an `f_2^nu_2`
factor contributes only the factorial `nu_2!`; there is no `delta_2`.
The term `Gamma_e(X,delta)` denotes the coefficient of the requested product
of `gamma_rs` classes after expanding each `gamma_rs` into JK `b_r^j`
variables and taking the corresponding coefficient in `exp(hat_tau)`.

## Odd Variables And Gamma

The paper's odd classes are

$$
b_r^j=(\alpha_j,\tau_r(U)),
\qquad 2\le r\le 5,\quad 1\le j\le 4.
$$

The symbols `gamma_rs` are only Sp-invariant abbreviations in the exterior
algebra on these `b_r^j`; they are not extra generators and are not rescaled.
The convention is recorded in
[`src/jk_only_v5_relation_frozen/GAMMA_CONVENTION.md`](../src/jk_only_v5_relation_frozen/GAMMA_CONVENTION.md):

$$
\gamma_{rs}
=b_r^1b_s^3-b_r^3b_s^1+b_r^2b_s^4-b_r^4b_s^2.
$$

Every `gamma` product is expanded into signed paper-level `b` monomials before
the `exp(hat_tau)` coefficient is evaluated.

## Code Map

The symbolic paper-first implementation is
[`jk_formula.py`](../src/jk_only_v5_relation_frozen/jk_formula.py).  The fast
modular implementation is
[`fast_modular.py`](../src/jk_only_v5_relation_frozen/fast_modular.py).  The
modular code is not a different formula; it is a sparse-polynomial and modular
residue implementation of the same factors.

| Formula piece | Source location |
|---|---|
| `n=5`, `g=2`, top degree, scalar prefactor `5` | [`jk_formula.py` lines 20-26](../src/jk_only_v5_relation_frozen/jk_formula.py#L20-L26) |
| JK odd labels `b_r^j`, gamma labels, simple coroot directions `h_j` | [`jk_formula.py` lines 39-50](../src/jk_only_v5_relation_frozen/jk_formula.py#L39-L50) |
| Simple-root coordinates `x_i(Y)` | [`jk_formula.py` lines 69-77](../src/jk_only_v5_relation_frozen/jk_formula.py#L69-L77) |
| `tau_r = e_r(x_1,...,x_5)` | [`jk_formula.py` lines 80-90](../src/jk_only_v5_relation_frozen/jk_formula.py#L80-L90) |
| `q = tau_2 + delta_3 tau_3 + delta_4 tau_4 + delta_5 tau_5` | [`jk_formula.py` lines 103-105](../src/jk_only_v5_relation_frozen/jk_formula.py#L103-L105) |
| `c_tilde` direction and exponent `(dq)_X(c_tilde)` | [`jk_formula.py` lines 108-114](../src/jk_only_v5_relation_frozen/jk_formula.py#L108-L114) |
| `B_j = -(dq)_X(h_j)` | [`jk_formula.py` lines 117-129](../src/jk_only_v5_relation_frozen/jk_formula.py#L117-L129) |
| Positive roots and `D(X)^2` | [`jk_formula.py` lines 140-154](../src/jk_only_v5_relation_frozen/jk_formula.py#L140-L154) |
| Hessian determinant ratio | [`jk_formula.py` lines 157-165](../src/jk_only_v5_relation_frozen/jk_formula.py#L157-L165) |
| `hat_tau` pair coefficient `-grad tau_r^T H_q^{-1} grad tau_s` | [`jk_formula.py` lines 168-173](../src/jk_only_v5_relation_frozen/jk_formula.py#L168-L173) |
| Exterior algebra multiplication and `exp(hat_tau)` coefficient | [`jk_formula.py` lines 180-248](../src/jk_only_v5_relation_frozen/jk_formula.py#L180-L248) |
| `gamma_rs` expansion into paper `b` variables | [`jk_formula.py` lines 251-296](../src/jk_only_v5_relation_frozen/jk_formula.py#L251-L296) |
| Symbolic generating integrand | [`jk_formula.py` lines 329-340](../src/jk_only_v5_relation_frozen/jk_formula.py#L329-L340) |
| Delta coefficient extraction and `prod nu_r!` scale | [`jk_formula.py` lines 314-345](../src/jk_only_v5_relation_frozen/jk_formula.py#L314-L345) |
| Ordered iterated residue `Y_4`, then `Y_3`, then `Y_2`, then `Y_1` | [`jk_formula.py` lines 348-360](../src/jk_only_v5_relation_frozen/jk_formula.py#L348-L360) |

## Fast Modular Evaluation

The actual rank searches use modular arithmetic for speed.  The modular path
uses the same factorization as the symbolic formula:

| Formula piece | Modular source location |
|---|---|
| Modular `x_i(Y)` and `tau_r` | [`fast_modular.py` lines 155-186](../src/jk_only_v5_relation_frozen/fast_modular.py#L155-L186) |
| `prod tau_r^m_r` for the `a` classes | [`fast_modular.py` lines 189-195](../src/jk_only_v5_relation_frozen/fast_modular.py#L189-L195) |
| `c_tilde` and `B_j` perturbation terms | [`fast_modular.py` lines 311-324](../src/jk_only_v5_relation_frozen/fast_modular.py#L311-L324) |
| Delta expansion of `exp((dq)(c_tilde))` | [`fast_modular.py` lines 344-364](../src/jk_only_v5_relation_frozen/fast_modular.py#L344-L364) |
| Delta expansion of `H_q^{-1}` and `hat_tau` | [`fast_modular.py` lines 407-479](../src/jk_only_v5_relation_frozen/fast_modular.py#L407-L479) |
| Delta expansion of `(det H_q / det H_tau2)^2` | [`fast_modular.py` lines 482-509](../src/jk_only_v5_relation_frozen/fast_modular.py#L482-L509) |
| Taylor expansion of `prod_j 1/(1-exp(-B_j))` around `B_j=Y_j` | [`fast_modular.py` lines 512-549](../src/jk_only_v5_relation_frozen/fast_modular.py#L512-L549) |
| Combined even kernel | [`fast_modular.py` lines 552-571](../src/jk_only_v5_relation_frozen/fast_modular.py#L552-L571) |
| Gamma expansion and `exp(hat_tau)` coefficient | [`fast_modular.py` lines 630-725](../src/jk_only_v5_relation_frozen/fast_modular.py#L630-L725) |
| One-variable residue transitions for the four ordered residues | [`fast_modular.py` lines 756-969](../src/jk_only_v5_relation_frozen/fast_modular.py#L756-L969) |
| Final modular pairing value, including prefactor `5` and `prod nu_r!` | [`fast_modular.py` lines 996-1010](../src/jk_only_v5_relation_frozen/fast_modular.py#L996-L1010) |

The key computational trick is that the factor

$$
\frac{1}{1-\exp(-B_j)}
$$

is written as a Taylor expansion around `B_j = Y_j`.  The derivative orders of
the base function

$$
F(Y_j)=\frac{1}{1-\exp(-Y_j)}
$$

are stored as part of the kernel.  The residue evaluator then applies those
derivatives while carrying the root denominator `D(X)^2` through the ordered
residue transitions.

## Guardrails Against Legacy Conventions

The v5 folder was built as a JK-only path:

- it does not import the previous v4.5 or Newstead-normalized implementations;
- `gamma_rs` is expanded into the paper-level odd variables before evaluation;
- certificates record source-file hashes and basis digests;
- final verifiers recompute selected minors directly from the frozen JK
  evaluator, not from cached matrix entries alone.

## Automated Checks

The script
[`run_checks.py`](../src/jk_only_v5_relation_frozen/run_checks.py)
runs formula and engineering guardrails before publication-style runs.  These
checks are intentionally small, but they test the parts most likely to hide a
convention error:

- structural identities from the paper specialization, including
  `B_j = Y_j` at `delta = 0`, the `c_tilde` exponent, the Hessian determinant
  ratio at `delta = 0`, and the collapsed prefactor `5`;
- gamma expansion in the exterior algebra, including symmetry in `r,s`, the
  documented `gamma22` simplification, products of gamma classes, and exterior
  nilpotence;
- agreement between the fast modular setup and the slower symbolic
  paper-derived setup for mixed and higher delta terms;
- batched residue evaluation against termwise residue evaluation, including
  real pairing polynomials and a gamma-heavy sample;
- cluster manifest, worker, reducer, previous-reduce, and verifier guardrails,
  including second-prime selected-minor verification.

The independent sample script
[`sample_certificate.py`](../src/jk_only_v5_relation_frozen/sample_certificate.py)
evaluates several top-degree sample pairings at multiple primes and rationally
reconstructs the answers, including no-gamma, mixed-delta, single-gamma, and
double-gamma samples.

## What The Degree Certificates Add

The checks above support the formula implementation.  The per-degree
certificates are the actual computational proof objects for the published rank
claims.  For a verified full-rank degree, the certificate records a selected
minor, its nonzero determinant modulo the primary prime, and a final verifier
that recomputes the selected minor from the JK evaluator.  A second-prime
verification is included as an arithmetic guard.

For `c12`, the current public object is different: it is a theorem-assisted
candidate line, described in
[`C12_THEOREM_ASSISTED_CANDIDATE.md`](C12_THEOREM_ASSISTED_CANDIDATE.md).
It should not be read as a full-W modular annihilation certificate.

## Limitations

These checks do not replace a line-by-line human proof of the implementation.
They document the formula dictionary, prevent known wrong conventions from
entering the v5 path, and make each published certificate reproducible from a
hashed source snapshot.  Exact rational relation coefficients require their
own reconstruction and exact or independent-prime verification artifact.
