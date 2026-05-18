# Jeffrey-Kirwan Theorem 9.6, Specialized to Rank 5 and Genus 2

Source: Lisa C. Jeffrey and Frances C. Kirwan, *Intersection theory on moduli
spaces of holomorphic bundles of arbitrary rank on a Riemann surface*,
arXiv:alg-geom/9608029, Section 9, especially Theorem 9.6 and Lemma 9.10.

We specialize to

```text
n = 5
g = 2
d = 1
```

The simple-root coordinates are

```text
Y_i = X_i - X_{i+1},  i=1,2,3,4.
```

With `x_1+...+x_5=0`, this gives

```text
x_1 = (4Y_1 + 3Y_2 + 2Y_3 + Y_4)/5
x_2 = (-Y_1 + 3Y_2 + 2Y_3 + Y_4)/5
x_3 = (-Y_1 - 2Y_2 + 2Y_3 + Y_4)/5
x_4 = (-Y_1 - 2Y_2 - 3Y_3 + Y_4)/5
x_5 = (-Y_1 - 2Y_2 - 3Y_3 - 4Y_4)/5.
```

The invariant polynomial `tau_r` is the elementary symmetric polynomial

```text
tau_r(X) = e_r(x_1,...,x_5).
```

The generating polynomial in Theorem 9.6 is

```text
q(X) = tau_2(X) + delta_3 tau_3(X) + delta_4 tau_4(X)
       + delta_5 tau_5(X).
```

The denominator uses

```text
B_j(X) = -(dq)_X(h_j),
```

where `h_j=e_j-e_{j+1}`.  In `Y` coordinates the directional derivatives are
the rows of the `A_4` Cartan matrix:

```text
h_1:  2 d/dY1 - d/dY2
h_2: -d/dY1 + 2 d/dY2 - d/dY3
h_3: -d/dY2 + 2 d/dY3 - d/dY4
h_4: -d/dY3 + 2 d/dY4.
```

At `delta_3=delta_4=delta_5=0`, one must have

```text
B_j(X) = Y_j.
```

The positive roots are

```text
x_i - x_j = Y_i + ... + Y_{j-1},  1 <= i < j <= 5.
```

Since `g=2`, the root denominator is

```text
D(X)^2 = product_{1<=i<j<=5} (x_i-x_j)^2.
```

For `d=1`, take

```text
c_tilde = (1/5,1/5,1/5,1/5,-4/5).
```

Then

```text
(dq)_X(c_tilde)
```

is the exponent in Theorem 9.6.  At `delta=0`, this is

```text
-(Y_1 + 2Y_2 + 3Y_3 + 4Y_4)/5.
```

For central `c`, the `W_4` sum collapses.  Since `n_+=10`, `g=2`, and
`n^g/n! * |W_4| = 25/120 * 24`, the scalar prefactor is

```text
5.
```

The odd classes are the paper classes

```text
b_r^j = (alpha_j, tau_r(U)).
```

Lemma 9.10 gives the exterior Gaussian

```text
hat_tau =
  - sum_{j=1}^2 sum_{r,s=2}^5
      s_r^j s_s^{j+2}
      (d tau_r)_X^T H_q(X)^(-1) (d tau_s)_X,
```

where `H_q` is the Hessian of `q` on the Cartan.  The implementation uses
`Y` coordinates consistently; the expression
`grad^T H^(-1) grad` and the determinant ratio are coordinate invariant when
all three are taken in the same coordinate system.

Thus for a monomial

```text
prod_r a_r^m_r prod_r f_r^nu_r prod b_r^j
```

the value is obtained by:

1. Taking the coefficient of the requested exterior `b` product in
   `exp(hat_tau)`.
2. Extracting the coefficient of
   `delta_3^nu_3 delta_4^nu_4 delta_5^nu_5`.
   In code this may be computed by differentiating in the delta variables,
   but then the derivative is divided by `nu_3! nu_4! nu_5!` to recover the
   coefficient.
3. Multiplying that coefficient once by `nu_2! nu_3! nu_4! nu_5!`.
4. Applying

```text
5 Res_{Y1=0} Res_{Y2=0} Res_{Y3=0} Res_{Y4=0}
```

to

```text
exp((dq)_X(c_tilde))
prod_r tau_r(X)^m_r
(det(H_q(X))/det(H_tau2(X)))^g
coefficient_from_exp_hat_tau
/
(
  D(X)^2
  product_{j=1}^4 (1 - exp(-B_j(X)))
).
```

Here `g=2`.  In code this term is exactly

```text
det_minus_hessian_ratio(q) ** GENUS.
```

The residue operator is applied inside-out in code: first `Y4`, then `Y3`,
then `Y2`, then `Y1`.
