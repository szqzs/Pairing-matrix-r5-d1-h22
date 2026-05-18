#!/usr/bin/env python
"""Paper-first JK formula utilities for rank 5, genus 2.

This module implements the specialization recorded in
`JK_THEOREM_9_6_RANK5_G2.md`.  It intentionally does not import any earlier
pairing implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, permutations
from math import factorial
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import sympy as sp


N = 5
GENUS = 2
TOP_DEGREE = 2 * (N * N - 1) * (GENUS - 1)
COLLAPSED_CENTRAL_PREFACTOR = sp.Integer(5)

Y = sp.symbols("Y1:5")
DELTA = sp.symbols("d3 d4 d5")

Alpha = Tuple[int, int, int, int]
DeltaKey = Tuple[int, int, int]
DerivOrders = Tuple[int, int, int, int]
BLabel = Tuple[int, int]
SparseDeltaPoly = Dict[DeltaKey, sp.Expr]
KernelTerms = Dict[Tuple[DeltaKey, DerivOrders], sp.Expr]
MaskPoly = Dict[int, sp.Expr]

ZERO_DELTA: DeltaKey = (0, 0, 0)
ZERO_DERIV: DerivOrders = (0, 0, 0, 0)

B_LABELS: Tuple[BLabel, ...] = tuple((r, j) for r in range(2, 6) for j in range(1, 5))
B_INDEX = {label: idx for idx, label in enumerate(B_LABELS)}

GAMMA_LABELS = tuple((r, s) for r in range(2, 6) for s in range(r, 6))
GAMMA_INDEX = {label: idx for idx, label in enumerate(GAMMA_LABELS)}

SIMPLE_COROOT_DIRECTIONS: Tuple[Alpha, ...] = (
    (2, -1, 0, 0),
    (-1, 2, -1, 0),
    (0, -1, 2, -1),
    (0, 0, -1, 2),
)


@dataclass(frozen=True)
class JKMonomial:
    """A monomial in JK paper classes."""

    a: Tuple[int, int, int, int] = (0, 0, 0, 0)
    f: Tuple[int, int, int, int] = (0, 0, 0, 0)
    b: Tuple[BLabel, ...] = ()

    def __post_init__(self) -> None:
        if len(self.a) != 4 or len(self.f) != 4:
            raise ValueError(f"bad exponent shape: {self}")
        for r, j in self.b:
            if r < 2 or r > 5 or j < 1 or j > 4:
                raise ValueError(f"bad JK b-label {(r, j)}")


def x_coordinates() -> Tuple[sp.Expr, ...]:
    y1, y2, y3, y4 = Y
    return (
        (4 * y1 + 3 * y2 + 2 * y3 + y4) / 5,
        (-y1 + 3 * y2 + 2 * y3 + y4) / 5,
        (-y1 - 2 * y2 + 2 * y3 + y4) / 5,
        (-y1 - 2 * y2 - 3 * y3 + y4) / 5,
        (-y1 - 2 * y2 - 3 * y3 - 4 * y4) / 5,
    )


@lru_cache(maxsize=None)
def tau(r: int) -> sp.Expr:
    if r < 2 or r > 5:
        raise ValueError(f"rank-5 JK tau index must be 2,...,5, got {r}")
    acc = sp.Integer(0)
    for combo in combinations(x_coordinates(), r):
        term = sp.Integer(1)
        for item in combo:
            term *= item
        acc += term
    return sp.expand(acc)


@lru_cache(maxsize=None)
def tau_grad_y(r: int) -> Tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]:
    tr = tau(r)
    return tuple(sp.expand(sp.diff(tr, y)) for y in Y)


def directional_derivative(expr: sp.Expr, direction_y: Sequence[int | sp.Expr]) -> sp.Expr:
    return sp.expand(sum(direction_y[i] * sp.diff(expr, Y[i]) for i in range(4)))


def q_polynomial() -> sp.Expr:
    d3, d4, d5 = DELTA
    return sp.expand(tau(2) + d3 * tau(3) + d4 * tau(4) + d5 * tau(5))


def c_tilde_direction_y() -> Alpha:
    # c_tilde=(1/5,1/5,1/5,1/5,-4/5), so dY=(0,0,0,1).
    return (0, 0, 0, 1)


def c_tilde_exponent(q: sp.Expr) -> sp.Expr:
    return directional_derivative(q, c_tilde_direction_y())


def b_map_components(q: sp.Expr) -> Tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]:
    return tuple(
        sp.expand(-directional_derivative(q, direction))
        for direction in SIMPLE_COROOT_DIRECTIONS
    )


@lru_cache(maxsize=None)
def b_perturbation(r: int, j: int) -> sp.Expr:
    """Coefficient of delta_r in B_j, with r=3,4,5 and j=1,...,4."""
    if r < 3 or r > 5 or j < 1 or j > 4:
        raise ValueError(f"expected r=3,...,5 and j=1,...,4, got {(r, j)}")
    return sp.expand(-directional_derivative(tau(r), SIMPLE_COROOT_DIRECTIONS[j - 1]))


@lru_cache(maxsize=None)
def c_direction_term(r: int) -> sp.Expr:
    """Directional derivative d(tau_r)(c_tilde)."""
    if r < 3 or r > 5:
        raise ValueError(f"expected r=3,...,5, got {r}")
    return sp.expand(directional_derivative(tau(r), c_tilde_direction_y()))


def positive_roots() -> Tuple[sp.Expr, ...]:
    roots: List[sp.Expr] = []
    for start in range(4):
        running = sp.Integer(0)
        for end in range(start, 4):
            running += Y[end]
            roots.append(sp.expand(running))
    return tuple(roots)


def denominator_root_product_squared() -> sp.Expr:
    prod = sp.Integer(1)
    for root in positive_roots():
        prod *= root**2
    return sp.expand(prod)


def hessian_y_basis(q: sp.Expr) -> sp.Matrix:
    return sp.Matrix([[sp.diff(q, left, right) for right in Y] for left in Y])


def det_minus_hessian_ratio(q: sp.Expr) -> sp.Expr:
    """Coordinate-invariant ratio det(-H_q)/det(-H_tau2)."""
    hq = hessian_y_basis(q)
    h0 = hessian_y_basis(tau(2))
    return sp.factor(hq.det() / h0.det())


def jk_hat_pair_coefficient(q: sp.Expr, r: int, s: int) -> sp.Expr:
    """Coefficient of source_r^j source_s^{j+2} in JK hat_tau."""
    h_inv = hessian_y_basis(q).inv()
    gr = sp.Matrix(tau_grad_y(r))
    gs = sp.Matrix(tau_grad_y(s))
    return sp.factor(-(gr.T * h_inv * gs)[0])


def mask_for_b_label(label: BLabel) -> int:
    return 1 << B_INDEX[label]


def wedge_masks(left: int, right: int) -> Optional[Tuple[int, int]]:
    if left & right:
        return None
    inversions = 0
    for i in range(len(B_LABELS)):
        if not (left & (1 << i)):
            continue
        inversions += sum(1 for j in range(i) if right & (1 << j))
    return (-1 if inversions % 2 else 1, left | right)


def exterior_mul(left: MaskPoly, right: MaskPoly) -> MaskPoly:
    out: MaskPoly = {}
    for m1, c1 in left.items():
        for m2, c2 in right.items():
            wedge = wedge_masks(m1, m2)
            if wedge is None:
                continue
            sign, mask = wedge
            out[mask] = sp.expand(out.get(mask, sp.Integer(0)) + sign * c1 * c2)
    return {mask: coeff for mask, coeff in out.items() if coeff != 0}


def b_product_to_mask(labels: Sequence[BLabel]) -> Optional[Tuple[int, int]]:
    mask = 0
    sign = 1
    for label in labels:
        wedge = wedge_masks(mask, mask_for_b_label(label))
        if wedge is None:
            return None
        step_sign, mask = wedge
        sign *= step_sign
    return sign, mask


def hat_tau_exterior_quadratic(q: sp.Expr) -> MaskPoly:
    out: MaskPoly = {}
    for left_side, right_side in ((1, 3), (2, 4)):
        for r in range(2, 6):
            for s in range(2, 6):
                left = mask_for_b_label((r, left_side))
                right = mask_for_b_label((s, right_side))
                wedge = wedge_masks(left, right)
                if wedge is None:
                    continue
                sign, mask = wedge
                coeff = sp.expand(sign * jk_hat_pair_coefficient(q, r, s))
                out[mask] = sp.expand(out.get(mask, sp.Integer(0)) + coeff)
    return {mask: coeff for mask, coeff in out.items() if coeff != 0}


def b_insertion_factor(q: sp.Expr, labels: Sequence[BLabel]) -> sp.Expr:
    target = b_product_to_mask(labels)
    if target is None:
        return sp.Integer(0)
    input_sign, target_mask = target
    if target_mask == 0:
        return sp.Integer(1)
    if target_mask.bit_count() % 2:
        return sp.Integer(0)
    quadratic = hat_tau_exterior_quadratic(q)
    pair_count = target_mask.bit_count() // 2
    power: MaskPoly = {0: sp.Integer(1)}
    for _ in range(pair_count):
        power = exterior_mul(power, quadratic)
        if not power:
            return sp.Integer(0)
    coeff = power.get(target_mask, sp.Integer(0)) / factorial(pair_count)
    return sp.expand(input_sign * coeff)


def gamma_b_terms(r: int, s: int) -> Tuple[Tuple[int, Tuple[BLabel, ...]], ...]:
    """Paper-level symplectic abbreviation gamma_rs in JK b variables."""
    if r < 2 or r > 5 or s < 2 or s > 5:
        raise ValueError(f"gamma labels must be between 2 and 5, got {(r, s)}")
    return (
        (1, ((r, 1), (s, 3))),
        (-1, ((r, 3), (s, 1))),
        (1, ((r, 2), (s, 4))),
        (-1, ((r, 4), (s, 2))),
    )


def gamma_product_to_b_terms(gamma_exp: Sequence[int]) -> Tuple[Tuple[int, Tuple[BLabel, ...]], ...]:
    """Expand a product of gamma_rs powers into signed JK b monomials."""
    if len(gamma_exp) != len(GAMMA_LABELS):
        raise ValueError(f"expected {len(GAMMA_LABELS)} gamma exponents, got {len(gamma_exp)}")
    terms: Dict[Tuple[BLabel, ...], int] = {(): 1}
    for idx, exp in enumerate(gamma_exp):
        if not exp:
            continue
        factor = gamma_b_terms(*GAMMA_LABELS[idx])
        for _ in range(int(exp)):
            new_terms: Dict[Tuple[BLabel, ...], int] = {}
            for labels, coeff in terms.items():
                base_mask = 0
                base_sign = 1
                ok = True
                for label in labels:
                    wedge = wedge_masks(base_mask, mask_for_b_label(label))
                    if wedge is None:
                        ok = False
                        break
                    step_sign, base_mask = wedge
                    base_sign *= step_sign
                if not ok:
                    continue
                for fcoeff, flabels in factor:
                    candidate = labels + flabels
                    target = b_product_to_mask(candidate)
                    if target is None:
                        continue
                    sign, mask = target
                    canonical = tuple(label for label in B_LABELS if mask & mask_for_b_label(label))
                    new_terms[canonical] = new_terms.get(canonical, 0) + coeff * fcoeff * sign
            terms = {labels: coeff for labels, coeff in new_terms.items() if coeff}
    return tuple(sorted((coeff, labels) for labels, coeff in terms.items() if coeff))


def a_monomial_factor(exponents: Sequence[int]) -> sp.Expr:
    out = sp.Integer(1)
    for offset, exp in enumerate(exponents):
        if exp:
            out *= tau(offset + 2) ** int(exp)
    return sp.expand(out)


def f_factorial_scale(exponents: Sequence[int]) -> int:
    out = 1
    for exp in exponents:
        out *= factorial(int(exp))
    return out


def delta_coefficient_at_zero(expr: sp.Expr, orders: Sequence[int]) -> sp.Expr:
    """Coefficient of delta_3^orders[0] delta_4^orders[1] delta_5^orders[2]."""
    if len(orders) != len(DELTA):
        raise ValueError(f"expected {len(DELTA)} delta orders, got {len(orders)}")
    out = expr
    scale = 1
    for delta_symbol, order in zip(DELTA, orders):
        order = int(order)
        if order:
            out = sp.diff(out, delta_symbol, order)
            scale *= factorial(order)
    out = out.subs({delta_symbol: 0 for delta_symbol in DELTA})
    return sp.factor(out / scale)


def generated_integrand(monomial: JKMonomial) -> sp.Expr:
    """The JK Theorem 9.6 generating integrand before delta extraction."""
    q = q_polynomial()
    denominator = denominator_root_product_squared()
    for component in b_map_components(q):
        denominator *= 1 - sp.exp(-component)

    numerator = sp.exp(c_tilde_exponent(q))
    numerator *= a_monomial_factor(monomial.a)
    numerator *= det_minus_hessian_ratio(q) ** GENUS
    numerator *= b_insertion_factor(q, monomial.b)
    return sp.factor(COLLAPSED_CENTRAL_PREFACTOR * numerator / denominator)


def extract_delta_integrand(monomial: JKMonomial) -> sp.Expr:
    coeff = delta_coefficient_at_zero(generated_integrand(monomial), monomial.f[1:])
    return sp.factor(f_factorial_scale(monomial.f) * coeff)


def one_variable_residue(expr: sp.Expr, var: sp.Symbol, series_order: int) -> sp.Expr:
    return sp.expand(sp.series(expr, var, 0, series_order).removeO().coeff(var, -1))


def iterated_residue(expr: sp.Expr, series_order: int = 80) -> sp.Expr:
    out = expr
    for var in reversed(Y):
        out = one_variable_residue(out, var, series_order)
    return sp.factor(out)


def jk_intersection_number(monomial: JKMonomial, series_order: int = 80) -> sp.Expr:
    return sp.factor(iterated_residue(extract_delta_integrand(monomial), series_order))


def top_degree(monomial: JKMonomial) -> int:
    total = 0
    for offset, exp in enumerate(monomial.a):
        r = offset + 2
        total += int(exp) * 2 * r
    for offset, exp in enumerate(monomial.f):
        r = offset + 2
        total += int(exp) * (2 * r - 2)
    for r, _j in monomial.b:
        total += 2 * r - 1
    return total


def _delta_leq(left: DeltaKey, right: DeltaKey) -> bool:
    return all(left[i] <= right[i] for i in range(3))


def _delta_add(left: DeltaKey, right: DeltaKey) -> DeltaKey:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _delta_poly_clean(poly: SparseDeltaPoly) -> SparseDeltaPoly:
    return {key: sp.expand(val) for key, val in poly.items() if val != 0}


def _delta_poly_add(
    left: SparseDeltaPoly,
    right: SparseDeltaPoly,
    scale: int | sp.Expr = 1,
) -> SparseDeltaPoly:
    out = dict(left)
    for key, val in right.items():
        out[key] = out.get(key, sp.Integer(0)) + scale * val
    return _delta_poly_clean(out)


def _delta_poly_scale(poly: SparseDeltaPoly, scale: int | sp.Expr) -> SparseDeltaPoly:
    return _delta_poly_clean({key: scale * val for key, val in poly.items()})


def _delta_poly_mul(left: SparseDeltaPoly, right: SparseDeltaPoly, max_delta: DeltaKey) -> SparseDeltaPoly:
    out: SparseDeltaPoly = {}
    for d1, v1 in left.items():
        for d2, v2 in right.items():
            key = _delta_add(d1, d2)
            if not _delta_leq(key, max_delta):
                continue
            out[key] = out.get(key, sp.Integer(0)) + v1 * v2
    return _delta_poly_clean(out)


def _delta_poly_pow(base: SparseDeltaPoly, exponent: int, max_delta: DeltaKey) -> SparseDeltaPoly:
    out: SparseDeltaPoly = {ZERO_DELTA: sp.Integer(1)}
    for _ in range(exponent):
        out = _delta_poly_mul(out, base, max_delta)
        if not out:
            break
    return out


def _delta_poly_exp_linear(linear: Dict[DeltaKey, sp.Expr], max_delta: DeltaKey) -> SparseDeltaPoly:
    out: SparseDeltaPoly = {}
    for e3 in range(max_delta[0] + 1):
        for e4 in range(max_delta[1] + 1):
            for e5 in range(max_delta[2] + 1):
                coeff = sp.Integer(1)
                for exp, key in ((e3, (1, 0, 0)), (e4, (0, 1, 0)), (e5, (0, 0, 1))):
                    if exp:
                        coeff *= linear[key] ** exp / factorial(exp)
                out[(e3, e4, e5)] = sp.expand(coeff)
    return _delta_poly_clean(out)


def _kernel_terms_mul_delta(
    terms: KernelTerms,
    poly: SparseDeltaPoly,
    max_delta: DeltaKey,
) -> KernelTerms:
    out: KernelTerms = {}
    for (kd, deriv), val in terms.items():
        for pd, pval in poly.items():
            nd = _delta_add(kd, pd)
            if not _delta_leq(nd, max_delta):
                continue
            key = (nd, deriv)
            out[key] = out.get(key, sp.Integer(0)) + val * pval
    return {key: sp.expand(val) for key, val in out.items() if val != 0}


def _delta_matrix_identity(size: int) -> List[List[SparseDeltaPoly]]:
    return [
        [{ZERO_DELTA: sp.Integer(1)} if i == j else {} for j in range(size)]
        for i in range(size)
    ]


def _delta_matrix_mul(
    left: List[List[SparseDeltaPoly]],
    right: List[List[SparseDeltaPoly]],
    max_delta: DeltaKey,
) -> List[List[SparseDeltaPoly]]:
    rows = len(left)
    cols = len(right[0])
    inner = len(right)
    out: List[List[SparseDeltaPoly]] = [[{} for _ in range(cols)] for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            acc: SparseDeltaPoly = {}
            for k in range(inner):
                acc = _delta_poly_add(acc, _delta_poly_mul(left[i][k], right[k][j], max_delta))
            out[i][j] = acc
    return out


@lru_cache(maxsize=None)
def hessian_inverse_delta(max_delta: DeltaKey) -> Tuple[Tuple[Tuple[Tuple[DeltaKey, sp.Expr], ...], ...], ...]:
    """Formal delta-series for H_q^{-1} in Y coordinates."""
    h0 = hessian_y_basis(tau(2))
    h0_inv = h0.inv()
    perturb = [h0_inv * hessian_y_basis(tau(r)) for r in (3, 4, 5)]
    units: Tuple[DeltaKey, ...] = ((1, 0, 0), (0, 1, 0), (0, 0, 1))

    a_mat: List[List[SparseDeltaPoly]] = [[{} for _ in range(4)] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            entry: SparseDeltaPoly = {}
            for unit, mat in zip(units, perturb):
                if _delta_leq(unit, max_delta) and mat[i, j] != 0:
                    entry[unit] = entry.get(unit, sp.Integer(0)) + mat[i, j]
            a_mat[i][j] = _delta_poly_clean(entry)

    series = _delta_matrix_identity(4)
    power = _delta_matrix_identity(4)
    for order in range(1, sum(max_delta) + 1):
        power = _delta_matrix_mul(power, a_mat, max_delta)
        sign = -1 if order % 2 else 1
        for i in range(4):
            for j in range(4):
                series[i][j] = _delta_poly_add(series[i][j], power[i][j], sign)

    out: List[List[SparseDeltaPoly]] = [[{} for _ in range(4)] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            acc: SparseDeltaPoly = {}
            for k in range(4):
                if h0_inv[k, j] != 0:
                    acc = _delta_poly_add(acc, _delta_poly_scale(series[i][k], h0_inv[k, j]))
            out[i][j] = acc

    return tuple(tuple(tuple(sorted(cell.items())) for cell in row) for row in out)


def _hessian_inverse_cell(max_delta: DeltaKey, i: int, j: int) -> SparseDeltaPoly:
    return dict(hessian_inverse_delta(max_delta)[i][j])


@lru_cache(maxsize=None)
def hat_pair_delta(r: int, s: int, max_delta: DeltaKey) -> Tuple[Tuple[DeltaKey, sp.Expr], ...]:
    """Paper-derived delta expansion of the JK hat_tau pair T_rs."""
    gr = tau_grad_y(r)
    gs = tau_grad_y(s)
    acc: SparseDeltaPoly = {}
    for i in range(4):
        for j in range(4):
            cell = _hessian_inverse_cell(max_delta, i, j)
            if cell:
                acc = _delta_poly_add(acc, _delta_poly_scale(cell, -gr[i] * gs[j]))
    return tuple(sorted(acc.items()))


def _det_ratio_delta_power(max_delta: DeltaKey, power: int) -> SparseDeltaPoly:
    h0 = hessian_y_basis(tau(2))
    h0_inv = h0.inv()
    perturb = [h0_inv * hessian_y_basis(tau(r)) for r in (3, 4, 5)]
    units: Tuple[DeltaKey, ...] = ((1, 0, 0), (0, 1, 0), (0, 0, 1))

    matrix: List[List[SparseDeltaPoly]] = []
    for i in range(4):
        row: List[SparseDeltaPoly] = []
        for j in range(4):
            entry: SparseDeltaPoly = {ZERO_DELTA: sp.Integer(1) if i == j else sp.Integer(0)}
            for unit, mat in zip(units, perturb):
                if _delta_leq(unit, max_delta) and mat[i, j] != 0:
                    entry[unit] = entry.get(unit, sp.Integer(0)) + mat[i, j]
            row.append(_delta_poly_clean(entry))
        matrix.append(row)

    det_poly: SparseDeltaPoly = {}
    for perm in permutations(range(4)):
        inversions = sum(1 for i in range(4) for j in range(i + 1, 4) if perm[i] > perm[j])
        term: SparseDeltaPoly = {ZERO_DELTA: sp.Integer(-1 if inversions % 2 else 1)}
        for i, j in enumerate(perm):
            term = _delta_poly_mul(term, matrix[i][j], max_delta)
            if not term:
                break
        det_poly = _delta_poly_add(det_poly, term)
    return _delta_poly_pow(det_poly, power, max_delta)


def _denominator_taylor_terms(max_delta: DeltaKey) -> KernelTerms:
    if max_delta == ZERO_DELTA:
        return {(ZERO_DELTA, ZERO_DERIV): sp.Integer(1)}
    terms: KernelTerms = {(ZERO_DELTA, ZERO_DERIV): sp.Integer(1)}
    max_order = sum(max_delta)
    unit_to_rank = {(1, 0, 0): 3, (0, 1, 0): 4, (0, 0, 1): 5}
    for j in range(1, 5):
        eps: SparseDeltaPoly = {
            key: b_perturbation(rank, j)
            for key, rank in unit_to_rank.items()
            if _delta_leq(key, max_delta)
        }
        factor: KernelTerms = {}
        for order in range(max_order + 1):
            eps_power = _delta_poly_pow(eps, order, max_delta)
            if not eps_power:
                continue
            deriv = [0, 0, 0, 0]
            deriv[j - 1] = order
            scale = sp.Rational(1, factorial(order))
            for kd, val in eps_power.items():
                key = (kd, tuple(deriv))  # type: ignore[arg-type]
                factor[key] = factor.get(key, sp.Integer(0)) + val * scale

        new_terms: KernelTerms = {}
        for (d1, der1), v1 in terms.items():
            for (d2, der2), v2 in factor.items():
                nd = _delta_add(d1, d2)
                if not _delta_leq(nd, max_delta):
                    continue
                nder = tuple(der1[i] + der2[i] for i in range(4))
                key = (nd, nder)  # type: ignore[assignment]
                new_terms[key] = new_terms.get(key, sp.Integer(0)) + v1 * v2
        terms = {key: sp.expand(val) for key, val in new_terms.items() if val != 0}
    return terms


@lru_cache(maxsize=None)
def even_kernel_terms(max_delta: DeltaKey) -> Tuple[Tuple[DeltaKey, DerivOrders, sp.Expr], ...]:
    """Paper-derived even delta kernel for the fast residue path.

    This is the coefficient expansion of

        exp(dq(c_tilde)-dtau2(c_tilde))
        (det(H_q)/det(H_tau2))^GENUS
        prod_j F(Y_j + epsilon_j)

    where F(y)=1/(1-exp(-y)).  The derivative orders record which
    derivative F^(m)(Y_j) is left for the residue evaluator.
    """
    exp_delta = _delta_poly_exp_linear(
        {
            (1, 0, 0): c_direction_term(3),
            (0, 1, 0): c_direction_term(4),
            (0, 0, 1): c_direction_term(5),
        },
        max_delta,
    )
    det_delta = _det_ratio_delta_power(max_delta, GENUS)
    terms = _denominator_taylor_terms(max_delta)
    terms = _kernel_terms_mul_delta(terms, exp_delta, max_delta)
    terms = _kernel_terms_mul_delta(terms, det_delta, max_delta)
    return tuple((kd, deriv, sp.expand(val)) for (kd, deriv), val in sorted(terms.items()))


def structural_identities() -> Dict[str, object]:
    q = q_polynomial()
    q0 = q.subs({delta: 0 for delta in DELTA})
    xs = x_coordinates()
    inner = sp.expand(sum(x * x for x in xs))
    b0 = tuple(sp.factor(component.subs({delta: 0 for delta in DELTA})) for component in b_map_components(q))
    c0 = sp.factor(c_tilde_exponent(q).subs({delta: 0 for delta in DELTA}))
    return {
        "top_degree": TOP_DEGREE,
        "tau2_plus_half_inner_is_zero": sp.factor(tau(2) + inner / 2) == 0,
        "B_at_delta0": b0,
        "B_at_delta0_equals_Y": b0 == Y,
        "c_tilde_exponent_delta0": c0,
        "c_tilde_exponent_matches": sp.factor(c0 + (Y[0] + 2 * Y[1] + 3 * Y[2] + 4 * Y[3]) / 5) == 0,
        "det_ratio_delta0": sp.factor(det_minus_hessian_ratio(q0)),
        "det_ratio_delta0_is_one": sp.factor(det_minus_hessian_ratio(q0) - 1) == 0,
        "collapsed_prefactor": int(COLLAPSED_CENTRAL_PREFACTOR),
        "collapsed_prefactor_is_5": COLLAPSED_CENTRAL_PREFACTOR == 5,
    }
