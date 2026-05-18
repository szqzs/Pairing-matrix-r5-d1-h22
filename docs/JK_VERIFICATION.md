# JK Formula Dictionary and Implementation Checks

This page records the dictionary between Jeffrey-Kirwan Theorem 9.11, Lemma
10.11, and the frozen v5 evaluator used in this repository.  It explains which
JK formula is implemented, how it specializes to rank `5`, genus `2`,
determinant degree `1`, and where the corresponding factors appear in source.

This page is not itself a rank certificate.  The degree folders certify the
published rank claims.  This page explains why the evaluator used in those
certificates follows the JK formula with the conventions stated here.

A published matrix entry is obtained as follows.  One source-row class and one
`W26` test class are multiplied, expanded in the universal classes
$a_r,f_r,\gamma_{rs}$, each $\gamma_{rs}$ is expanded into the paper odd
variables $b_r^k$, and the JK residue formula below is applied termwise.

The source paper is Jeffrey and Kirwan, *Intersection theory on moduli spaces
of holomorphic bundles of arbitrary rank on a Riemann surface*,
arXiv:alg-geom/9608029, especially Theorem 9.11 and Lemma 10.11 in the printed
arXiv PDF.  The arXiv TeX source labels these as `t9.6` and `l9.10`; that
source-label convention explains the historical frozen ledger filename
[`src/jk_only_v5_relation_frozen/JK_THEOREM_9_6_RANK5_G2.md`](../src/jk_only_v5_relation_frozen/JK_THEOREM_9_6_RANK5_G2.md).
The frozen source files are left byte-for-byte as the certificates recorded
them, so this page is the corrected reader-facing numbering guide.

Roadmap:

1. introduce the objects in the paper formula;
2. state the JK residue formula in paper notation;
3. explain how the torus integral becomes the Hessian and odd-variable
   factors used by code;
4. specialize to rank `5`, genus `2`, determinant degree `1`;
5. map the factors to source files and list the checks.

## Notation Before The Formula

We first list the objects that occur in the Jeffrey-Kirwan residue formula.

- $C$ is a compact Riemann surface of genus $g$.
- $\mathcal M(n,d)$ is the fixed-determinant moduli space of stable bundles
  of rank `n` and determinant degree `d`, with `gcd(n,d)=1`.
- $T$ is the maximal torus used in the JK localization calculation.  Its
  complexified Lie algebra is the hyperplane

$$
\mathfrak t_{\mathbb C}
=\{X=(x_1,\ldots,x_n)\in\mathbb C^n:x_1+\cdots+x_n=0\}.
$$

- $X$ is the residue variable: a point of
  $\mathfrak t_{\mathbb C}$.  Writing
  $X=(x_1,\ldots,x_n)$ means that $x_i$ is the `i`th coordinate function
  evaluated on this variable point.  Thus the $x_i$ are not fixed numbers;
  later they are rewritten in the simple-root coordinates $Y_i$.
- $Y_i$ is the `i`th simple-root coordinate of the same variable point $X$:

$$
Y_i=x_i-x_{i+1},\qquad i=1,\ldots,n-1.
$$

- The vector $e_i$ is the `i`th standard coordinate vector in $\mathbb C^n$.
- $h_i$ is the corresponding simple coroot direction:

$$
h_i=e_i-e_{i+1}\in\mathfrak t_{\mathbb C}.
$$

- $\tau_r$ is the `r`th elementary symmetric invariant polynomial in the
  coordinates of $X$.  Thus $\tau_r$ is an element of the invariant polynomial
  ring on $\mathfrak t_{\mathbb C}$:

$$
\tau_r(X)=e_r(x_1,\ldots,x_n),\qquad r=2,\ldots,n.
$$

- $a_r$, $b_r^k$, and $f_r$ are the universal cohomology classes in the JK
  paper:

$$
a_r\in H^{2r},\qquad b_r^k\in H^{2r-1},\qquad f_r\in H^{2r-2}.
$$

  The exponents $m_r$, $p_{r,k}$, and $\nu_r$ below record a monomial in
  those classes.  In the odd $b$ sector, $p_{r,k}$ is effectively `0` or `1`
  after exterior-algebra reduction.
- $\delta_r$ is a formal even parameter used to extract powers of $f_r$.
  It is not a cohomology class; it is the bookkeeping variable dual to $f_r$
  in the exponential generating function.  Algebraically, the formula is
  expanded in the formal polynomial variables $\delta_3,\ldots,\delta_n$.
- $q$ is the formal invariant polynomial

$$
q(X)=\tau_2(X)+\delta_3\tau_3(X)+\cdots+\delta_n\tau_n(X).
$$

- $(dq)_X$ is the cotangent vector obtained by differentiating $q$ at $X$, so
  $(dq)_X(v)$ is the directional derivative of $q$ in the tangent direction
  $v$.
- $B_i(X)$ is the JK simple-root denominator input:

$$
B_i(X)=-(dq)_X(h_i).
$$

- $D(X)$ is the product of the positive roots, hence a polynomial function of
  $X$:

$$
D(X)=\prod_{1\le i\lt j\le n}(x_i-x_j).
$$

- $n_+$ is the number of positive roots:

$$
n_+=\frac{n(n-1)}2.
$$

- $W_{n-1}$ is the symmetric group $S_{n-1}$ that appears as the finite
  Weyl-summation set in Theorem 9.11 after the fixed-determinant reduction.
  This is JK's summation set, not the full $S_n$ Weyl group notation.  In our
  rank-5 specialization it has `24` elements.  This $W_{n-1}$ is unrelated to
  the repository's `W26` test basis.
- $c_{\mathrm{JK}}$ records the determinant parameter in the JK theorem, and
  $\widetilde{w c_{\mathrm{JK}}}$ is the JK lift of the Weyl-translated
  determinant vector into the simple-root fundamental domain.  This
  determinant parameter is not the repository's Chern-degree label `c12`,
  `c13`, and so on.
- $\hat u_a$, for $a=1,\ldots,n-1$, is the tangent basis used by JK for the
  Hessian and gradient terms.  In the code it is represented by the simple
  coroot basis.
- $H_q(X)$ is the Hessian matrix of $q$ at $X$ in the $\hat u_a$ basis, so it
  is an $(n-1)\times(n-1)$ matrix with entries in the same formal coefficient
  ring as $q$.
- $\zeta_a^k$ is an exterior variable on the torus factor $T^{2g}$, with
  $a=1,\ldots,n-1$ and $k=1,\ldots,2g$.
- $s_r^k$ is an auxiliary exterior variable used in Lemma 10.11.  It
  represents the paper odd class $b_r^k$ during coefficient extraction.
- The symbol $\int_{T^{2g}}$ in Theorem 9.11 is the exterior-algebra integral,
  meaning the top-degree coefficient extraction in the $\zeta$ variables.

## Paper Formula

With this notation fixed, Theorem 9.11 gives the following residue form for a
monomial in the universal generators:

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
\mathrm{Res}_{Y_1=0}\cdots
\mathrm{Res}_{Y_{n-1}=0}
\Biggl[
\frac{
e^{(dq)_X(\widetilde{w c_{\mathrm{JK}}})}
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

We write the iterated residue in the same order as the paper.  In code the
same nested iterated residue operator is applied inside-out, so the rank-5
evaluator applies the residues in the order $Y_4,Y_3,Y_2,Y_1$.

Lemma 10.11 packages the odd insertions in the $T^{2g}$ integral into an
exterior Gaussian.  In the form used by the code, this says:

$$
\widehat{\tau}(X)=
-\sum_{a,b=1}^{n-1}\sum_{r,s=2}^n\sum_{j=1}^{g}
s_r^j s_s^{j+g}
(d\tau_r)_X(\hat u_a)
(d\tau_s)_X(\hat u_b)
\bigl(H_q(X)^{-1}\bigr)_{ab}.
$$

Equivalently, the odd part of the JK pairing is obtained by extracting the
coefficient of the corresponding monomial in the auxiliary odd parameters
$s_r^j$ from $\exp(\widehat{\tau})$.

When the $T^{2g}$ integral is evaluated, the Gaussian part also contributes
the scalar $n^g$ and, in the JK normalization used here, the Hessian
determinant normalization

$$
\left(\frac{\det H_q(X)}{\det H_{\tau_2}(X)}\right)^g.
$$

The distinction is visible already in Theorem 9.11: part (a), displayed above,
keeps the $T^{2g}$ integral and has prefactor $1/n!$, while part (b), after
evaluating the no-odd-insertion torus integral, has the prefactor $n^g/n!$ and
the Hessian determinant.  Thus the inverse-Hessian contractions in
$\widehat{\tau}$ encode the odd insertions, while $n^g$ and this determinant
ratio come from the Gaussian evaluation.  In our genus-2 specialization this
ratio is squared.  The denominator
$\det H_{\tau_2}$ is the JK normalization at the base quadratic form
$q=\tau_2$, so the ratio is `1` when $\delta_3=\cdots=\delta_n=0$.  This is
why the automated checks include the identity "determinant ratio equals `1` at
$\delta=0$."

The main factors are therefore:

| Formula factor | Meaning in the pairing |
|---|---|
| $\exp((dq)_X(\widetilde{w c_{\mathrm{JK}}}))$ | determinant-degree and Weyl-summand exponential |
| $\prod_r \tau_r(X)^{m_r}$ | insertions of the even classes $a_r$ |
| coefficient of $e^{\widehat{\tau}(X)}$ | insertions of the odd classes $b_r^k$ |
| $n^g$ | scalar from evaluating the $T^{2g}$ Gaussian |
| $(\det H_q(X)/\det H_{\tau_2}(X))^g$ | Gaussian determinant normalization |
| $D(X)^{2g-2}$ | positive-root denominator |
| $\prod_j(1-\exp(-B_j(X)))$ | simple-root denominator from the JK residue |
| coefficient extraction in $\delta_r$ | insertions of $f_r$ for $r\ge 3$ |
| the initial $\exp(f_2)$ | source of the $f_2$ factorial |

## Rank 5, Genus 2, Degree 1

For this repository we set

$$
n=5,\qquad g=2,\qquad d=1.
$$

There are four simple-root variables, and the $x_i$ are

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
\qquad 1\le i\lt j\le 5,
$$

so, since `g=2`, the root denominator is

$$
D(X)^2=\prod_{1\le i\lt j\le 5}(x_i-x_j)^2.
$$

For determinant degree `1`, we use

$$
\widetilde c=\left(\frac15,\frac15,\frac15,\frac15,-\frac45\right).
$$

At $\delta=0$,

$$
(dq)_X(\widetilde c)=
-\frac{Y_1+2Y_2+3Y_3+4Y_4}{5}.
$$

This displayed $\delta=0$ value is a normalization check.  The computation
keeps the full $\delta$-dependent exponent before extracting the requested
coefficient.

For determinant degree `1`, the chosen lift $\widetilde c$ has its first four
coordinates equal.  The JK $W_4$ summation in this specialization
permutes those first four coordinates, so the summands are identical and the
Weyl sum contributes $|W_4|=24$ with no additional signs or permutation
factors.  This is the rank-5, degree-1 specialization recorded in the frozen
formula ledger, not a general simplification of every JK residue.  The scalar
prefactor is therefore

$$
\frac{n^g}{n!}\,|W_4|
=\frac{25}{120}\cdot 24
=5
$$

The sign is positive because $n_+(g-1)=10$.

For a monomial

$$
\prod_{r=2}^5 a_r^{m_r}
\prod_{r=2}^5 f_r^{\nu_r}
\prod_{r\le s}\gamma_{rs}^{e_{rs}},
$$

the implemented pairing is obtained from the exponential generating function.
For $r\ge 3$, the power $f_r^{\nu_r}$ is recovered by extracting the
$\delta_r^{\nu_r}$ coefficient and multiplying by $\nu_r!$.  The class $f_2$
is already present in the initial $\exp(f_2)$ term, so the monomial
$f_2^{\nu_2}$ contributes the remaining factorial $\nu_2!$.  Thus the
implemented pairing is:

$$
\begin{aligned}
\mathrm{JK}_{5,2,1}
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
\mathrm{Res}_{Y_1=0}
\mathrm{Res}_{Y_2=0}
\mathrm{Res}_{Y_3=0}
\mathrm{Res}_{Y_4=0}
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

As above, this residue product is displayed in paper order; the code applies
the same nested operator inside-out.

The term $\Gamma_{\mathbf e}(X,\delta)$ denotes the coefficient of the
requested product of $\gamma_{rs}$ classes after expanding each $\gamma_{rs}$
into JK $b_r^k$ variables and taking the corresponding coefficient of the
auxiliary $s$-monomial in $\exp(\widehat{\tau})$.

## Odd Variables And Gamma

The paper's odd classes are indexed by a chosen symplectic basis
$\alpha_1,\ldots,\alpha_4$ of $H_1(C)$:

$$
b_r^k=(\alpha_k,\tau_r(U)),
\qquad 2\le r\le 5,\quad 1\le k\le 4.
$$

The symbols $\gamma_{rs}$ are only Sp-invariant abbreviations in the exterior
algebra on these $b_r^k$; they are not extra generators and are not rescaled.
The convention is recorded in
[`src/jk_only_v5_relation_frozen/GAMMA_CONVENTION.md`](../src/jk_only_v5_relation_frozen/GAMMA_CONVENTION.md):

$$
\gamma_{rs}
=b_r^1b_s^3-b_r^3b_s^1+b_r^2b_s^4-b_r^4b_s^2.
$$

Every $\gamma$ product is expanded into signed paper-level $b$ monomials before
the $\exp(\widehat{\tau})$ coefficient is evaluated.

The mathematical formula dictionary ends here.  The remaining sections are for
readers who want to audit how these factors are represented and checked in the
frozen source.

## Code Map

The symbolic paper-first implementation is
[`jk_formula.py`](../src/jk_only_v5_relation_frozen/jk_formula.py).  The fast
modular implementation is
[`fast_modular.py`](../src/jk_only_v5_relation_frozen/fast_modular.py).  The
modular code is not a different formula; it is a sparse-polynomial and modular
residue implementation of the same rational factors after finite-field
reduction.

| Formula piece | Source location |
|---|---|
| `n=5`, `g=2`, top degree, scalar prefactor `5` | [`jk_formula.py` lines 20-26](../src/jk_only_v5_relation_frozen/jk_formula.py#L20-L26) |
| JK odd labels `b_r^k`, gamma labels, simple coroot directions `h_j` | [`jk_formula.py` lines 39-50](../src/jk_only_v5_relation_frozen/jk_formula.py#L39-L50) |
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

### Modular Primes

The prime is not part of the JK formula; it is part of the finite-field
implementation of the same rational formula.  The published certificates use
the following primes:

| Role | Prime | Use |
|---|---:|---|
| Primary prime | `2305843009213693951 = 2^61 - 1` | Main modular column evaluation, rank search, and selected-minor certificate |
| Second prime | `1000033` | Second-prime recomputation of the selected minor as an arithmetic guard |

The primary prime is the default in
[`fast_modular.py` line 17](../src/jk_only_v5_relation_frozen/fast_modular.py#L17).
Both primes are checked by the rank-search code using deterministic
Miller-Rabin for integers below `2^64`; see
[`modular_rank_search.py` lines 148-189](../src/jk_only_v5_relation_frozen/modular_rank_search.py#L148-L189).

For the finite ordinary/cohomological degree-22 computations published here,
all modular inversions actually required by the evaluator exist at these
primes.  The
fixed coordinate denominators come from the rank-5 simple-root substitution
and include powers of `5`; the remaining inversions come from the finite
Taylor/exponential and exterior-Gaussian coefficient extractions used by this
degree range, and all required factorial/Taylor orders are far below
`1000033`, hence also far below `2^61 - 1`.  If a denominator were zero modulo
the chosen prime, the modular evaluator would fail at the modular inverse step
rather than silently produce a certificate.

This is a finite-computation statement.  It should not be read as a claim
that the same two primes avoid every denominator appearing in the infinite JK
generating series.

The key computational trick is that the factor

$$
\frac{1}{1-\exp(-B_j)}
$$

is written as a finite formal Taylor expansion around `B_j = Y_j`, truncated to
the degree needed for the requested coefficient and residue.  This is not an
analytic convergence argument.  The derivative orders of the base function

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
- representative agreement checks between the fast modular setup and the
  slower symbolic paper-derived setup for mixed and higher delta terms;
- batched residue evaluation against termwise residue evaluation, including
  real pairing polynomials and a gamma-heavy sample;
- certificate infrastructure guardrails for manifests, workers, reducers,
  previous reductions, and verifiers, including second-prime selected-minor
  verification.

The separate sample script
[`sample_certificate.py`](../src/jk_only_v5_relation_frozen/sample_certificate.py)
evaluates several top-degree sample pairings at multiple primes and rationally
reconstructs the answers, including no-gamma, mixed-delta, single-gamma, and
double-gamma samples.

## What The Degree Certificates Add

The checks above support the formula implementation.  The per-degree
certificates are computational proof objects for the stated modular rank
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
They document the formula dictionary, guard against known wrong conventions
entering the v5 path, and make each published certificate reproducible from a
hashed source snapshot.  Exact rational relation coefficients require their own
reconstruction and exact verification, or a bounded rational-reconstruction
argument with additional-prime checks.
