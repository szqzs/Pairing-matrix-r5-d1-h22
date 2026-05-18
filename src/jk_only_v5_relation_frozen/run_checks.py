#!/usr/bin/env python
"""Guardrail and structural checks for the JK-only implementation path."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pickle
import platform
import sys
import tempfile
import time
from itertools import product
from math import factorial
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

import sympy as sp

import basis
import cluster_rank_driver as crd
import fast_modular as fm
import jk_formula as jk
import modular_rank_search as mrs


HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_OUTPUT = os.path.join(HERE, "jk_only_check_results.json")
FORMULA_LEDGER = os.path.join(HERE, "JK_THEOREM_9_6_RANK5_G2.md")
GAMMA_LEDGER = os.path.join(HERE, "GAMMA_CONVENTION.md")
CERTIFICATE_FILES = (
    "__init__.py",
    "README.md",
    "JK_THEOREM_9_6_RANK5_G2.md",
    "GAMMA_CONVENTION.md",
    "fast_modular.py",
    "basis.py",
    "jk_formula.py",
    "cluster_rank_driver.py",
    "modular_rank_search.py",
    "residue_oracle.py",
    "sample_certificate.py",
    "speed_probe.py",
    "strict_degree_runner.py",
    "strict_relation_runner.py",
    "theorem_assisted_c12_candidate.py",
    "run_checks.py",
)
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "argparse",
    "ast",
    "dataclasses",
    "datetime",
    "fractions",
    "functools",
    "hashlib",
    "itertools",
    "json",
    "math",
    "os",
    "pickle",
    "platform",
    "pathlib",
    "resource",
    "shlex",
    "socket",
    "subprocess",
    "sys",
    "tempfile",
    "time",
    "typing",
    "sympy",
    "basis",
    "cluster_rank_driver",
    "fast_modular",
    "jk_formula",
    "modular_rank_search",
    "strict_degree_runner",
    "strict_relation_runner",
}
FORBIDDEN_SUBSTRINGS = tuple(
    "".join(parts)
    for parts in (
        ("reference", "_loader"),
        ("_reference", "_", "v", "45"),
        ("pairing_rank5_g2", "_", "v", "45"),
        ("local", "_newstead"),
    )
)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def python_files() -> Iterable[str]:
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [dirname for dirname in dirs if dirname != "__pycache__"]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(root, name)


def provenance() -> Dict[str, Any]:
    file_hashes = {}
    for relpath in CERTIFICATE_FILES:
        path = os.path.join(HERE, relpath)
        file_hashes[relpath] = sha256_file(path) if os.path.exists(path) else None
    return {
        "source": {
            "paper": "Jeffrey-Kirwan, Intersection theory on moduli spaces of holomorphic bundles of arbitrary rank on a Riemann surface",
            "arxiv_id": "alg-geom/9608029",
            "arxiv_version": "v2",
            "source_url": "https://arxiv.org/abs/alg-geom/9608029",
            "formula_scope": "Theorem 9.6 and Lemma 9.10 specialized to n=5, g=2, d=1",
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "sympy": sp.__version__,
        },
        "command": " ".join([sys.executable, *sys.argv]),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_sha256": file_hashes,
    }


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    return str(value)


def guardrail_scan() -> Dict[str, Any]:
    hits: List[Dict[str, Any]] = []
    for root, _dirs, files in os.walk(HERE):
        for name in files:
            if not (name.endswith(".py") or name.endswith(".md")):
                continue
            path = os.path.join(root, name)
            with open(path, "r", encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, start=1):
                    for needle in FORBIDDEN_SUBSTRINGS:
                        if needle in line:
                            hits.append({
                                "file": os.path.relpath(path, HERE),
                                "line": lineno,
                                "needle": needle,
                            })
    return {
        "status": "passed" if not hits else "failed",
        "forbidden_rule_count": len(FORBIDDEN_SUBSTRINGS),
        "hits": hits,
    }


def ast_import_allowlist_check() -> Dict[str, Any]:
    violations: List[Dict[str, Any]] = []
    observed: Set[str] = set()
    for path in python_files():
        with open(path, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    observed.add(root)
                    if root not in ALLOWED_IMPORT_ROOTS:
                        violations.append({
                            "file": os.path.relpath(path, HERE),
                            "line": node.lineno,
                            "module": alias.name,
                        })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".", 1)[0]
                observed.add(root)
                if root not in ALLOWED_IMPORT_ROOTS:
                    violations.append({
                        "file": os.path.relpath(path, HERE),
                        "line": node.lineno,
                        "module": module,
                    })
    return {
        "status": "passed" if not violations else "failed",
        "allowed_import_roots": sorted(ALLOWED_IMPORT_ROOTS),
        "observed_import_roots": sorted(observed),
        "violations": violations,
    }


def structural_checks() -> Dict[str, Any]:
    data = jk.structural_identities()
    required = {
        "tau2_plus_half_inner_is_zero": bool(data["tau2_plus_half_inner_is_zero"]),
        "B_at_delta0_equals_Y": bool(data["B_at_delta0_equals_Y"]),
        "c_tilde_exponent_matches": bool(data["c_tilde_exponent_matches"]),
        "det_ratio_delta0_is_one": bool(data["det_ratio_delta0_is_one"]),
        "collapsed_prefactor_is_5": bool(data["collapsed_prefactor_is_5"]),
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "required": required,
        "details": data,
    }


def delta_leq(left: jk.DeltaKey, right: jk.DeltaKey) -> bool:
    return all(left[i] <= right[i] for i in range(3))


def delta_monomials(max_delta: jk.DeltaKey) -> Iterable[jk.DeltaKey]:
    for e3 in range(max_delta[0] + 1):
        for e4 in range(max_delta[1] + 1):
            for e5 in range(max_delta[2] + 1):
                yield (e3, e4, e5)


def delta_symbol_power(delta: jk.DeltaKey) -> sp.Expr:
    out = sp.Integer(1)
    for symbol, exp in zip(jk.DELTA, delta):
        if exp:
            out *= symbol**exp
    return out


def compact_expr_dict(mapping: Dict[Any, sp.Expr]) -> Dict[str, str]:
    return {str(key): str(sp.factor(value)) for key, value in sorted(mapping.items(), key=lambda item: str(item[0]))}


def expr_is_zero(expr: sp.Expr) -> bool:
    return sp.expand(expr) == 0


def direct_even_kernel_terms(max_delta: jk.DeltaKey) -> Dict[Tuple[jk.DeltaKey, jk.DerivOrders], sp.Expr]:
    max_order = sum(max_delta)
    u_symbols = {
        (j, order): sp.Symbol(f"U{j}_{order}")
        for j in range(4)
        for order in range(max_order + 1)
    }
    u_flat = [u_symbols[(j, order)] for j in range(4) for order in range(max_order + 1)]

    linear = {
        (1, 0, 0): jk.c_direction_term(3),
        (0, 1, 0): jk.c_direction_term(4),
        (0, 0, 1): jk.c_direction_term(5),
    }
    exp_trunc = sp.Integer(0)
    for delta in delta_monomials(max_delta):
        coeff = sp.Integer(1)
        for unit, exp in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), delta):
            if exp:
                coeff *= linear[unit] ** exp / factorial(exp)
        exp_trunc += delta_symbol_power(delta) * coeff

    det_expr = jk.det_minus_hessian_ratio(jk.q_polynomial()) ** jk.GENUS
    den_expr = sp.Integer(1)
    for j in range(1, 5):
        eps = sum(
            jk.DELTA[rank - 3] * jk.b_perturbation(rank, j)
            for rank in range(3, 6)
        )
        factor = sp.Integer(0)
        for order in range(max_order + 1):
            factor += eps**order * u_symbols[(j - 1, order)] / factorial(order)
        den_expr *= factor

    poly = sp.Poly(sp.expand(exp_trunc * det_expr * den_expr), *jk.DELTA, *u_flat)
    out: Dict[Tuple[jk.DeltaKey, jk.DerivOrders], sp.Expr] = {}
    for monom, coeff in poly.terms():
        delta = tuple(int(e) for e in monom[:3])
        if not delta_leq(delta, max_delta):
            continue
        deriv: List[int | None] = [None, None, None, None]
        valid = True
        for exp, (j, order) in zip(monom[3:], ((j, order) for j in range(4) for order in range(max_order + 1))):
            if not exp:
                continue
            if exp != 1 or deriv[j] is not None:
                valid = False
                break
            deriv[j] = order
        if not valid or any(item is None for item in deriv):
            continue
        key = (delta, tuple(int(item) for item in deriv))  # type: ignore[arg-type]
        out[key] = sp.expand(out.get(key, sp.Integer(0)) + coeff)
    return {key: sp.expand(value) for key, value in out.items() if value != 0}


def generated_even_kernel_terms(max_delta: jk.DeltaKey) -> Dict[Tuple[jk.DeltaKey, jk.DerivOrders], sp.Expr]:
    return {
        (delta, deriv): sp.expand(expr)
        for delta, deriv, expr in jk.even_kernel_terms(max_delta)
    }


def compare_expr_maps(left: Dict[Any, sp.Expr], right: Dict[Any, sp.Expr]) -> bool:
    if set(left) != set(right):
        return False
    return all(expr_is_zero(left[key] - right[key]) for key in left)


def hessian_inverse_coeff(delta: jk.DeltaKey) -> sp.Matrix:
    h0 = jk.hessian_y_basis(jk.tau(2))
    h0_inv = h0.inv()
    if sum(delta) == 0:
        return h0_inv
    perturb = [h0_inv * jk.hessian_y_basis(jk.tau(r)) for r in (3, 4, 5)]
    out = sp.zeros(4, 4)
    order = sum(delta)
    for word in product(range(3), repeat=order):
        if tuple(word.count(i) for i in range(3)) != delta:
            continue
        term = sp.eye(4)
        for idx in word:
            term *= perturb[idx]
        out += term
    if order % 2:
        out = -out
    return out * h0_inv


def expected_hat_pair_coeff(r: int, s: int, delta: jk.DeltaKey) -> sp.Expr:
    gr = sp.Matrix(jk.tau_grad_y(r))
    gs = sp.Matrix(jk.tau_grad_y(s))
    return sp.factor(-(gr.T * hessian_inverse_coeff(delta) * gs)[0])


def deriv_order(index: int, order: int) -> jk.DerivOrders:
    data = [0, 0, 0, 0]
    data[index] = order
    return tuple(data)  # type: ignore[return-value]


def det_power_linear_coeff(rank: int) -> sp.Expr:
    h0_inv = jk.hessian_y_basis(jk.tau(2)).inv()
    a_mat = h0_inv * jk.hessian_y_basis(jk.tau(rank))
    return sp.factor(jk.GENUS * sp.trace(a_mat))


def det_power_second_same_rank_coeff(rank: int) -> sp.Expr:
    h0_inv = jk.hessian_y_basis(jk.tau(2)).inv()
    a_mat = h0_inv * jk.hessian_y_basis(jk.tau(rank))
    trace_a = sp.trace(a_mat)
    det_second = (trace_a**2 - sp.trace(a_mat * a_mat)) / 2
    return sp.factor(jk.GENUS * det_second + sp.Rational(jk.GENUS * (jk.GENUS - 1), 2) * trace_a**2)


def expected_even_first_order_terms(rank: int) -> Dict[Tuple[jk.DeltaKey, jk.DerivOrders], sp.Expr]:
    delta = (1 if rank == 3 else 0, 1 if rank == 4 else 0, 1 if rank == 5 else 0)
    linear_scalar = jk.c_direction_term(rank) + det_power_linear_coeff(rank)
    out: Dict[Tuple[jk.DeltaKey, jk.DerivOrders], sp.Expr] = {
        (delta, (0, 0, 0, 0)): sp.expand(linear_scalar)
    }
    for j in range(4):
        out[(delta, deriv_order(j, 1))] = jk.b_perturbation(rank, j + 1)
    return out


def expected_even_second_same_rank_terms(rank: int) -> Dict[Tuple[jk.DeltaKey, jk.DerivOrders], sp.Expr]:
    if rank != 3:
        raise ValueError("second-order lightweight check is currently used only for delta_3")
    delta: jk.DeltaKey = (2, 0, 0)
    exp_linear = jk.c_direction_term(rank)
    det_linear = det_power_linear_coeff(rank)
    scalar_linear = exp_linear + det_linear
    scalar_second = exp_linear**2 / 2 + det_power_second_same_rank_coeff(rank) + exp_linear * det_linear
    eps = [jk.b_perturbation(rank, j + 1) for j in range(4)]
    out: Dict[Tuple[jk.DeltaKey, jk.DerivOrders], sp.Expr] = {
        (delta, (0, 0, 0, 0)): sp.expand(scalar_second)
    }
    for j in range(4):
        out[(delta, deriv_order(j, 1))] = sp.expand(eps[j] * scalar_linear)
        out[(delta, deriv_order(j, 2))] = sp.expand(eps[j] ** 2 / 2)
    for j in range(4):
        for k in range(j + 1, 4):
            data = [0, 0, 0, 0]
            data[j] = 1
            data[k] = 1
            out[(delta, tuple(data))] = sp.expand(eps[j] * eps[k])  # type: ignore[arg-type]
    return out


def setup_generator_checks() -> Dict[str, Any]:
    even0 = jk.even_kernel_terms((0, 0, 0))
    hat22 = dict(jk.hat_pair_delta(2, 2, (0, 0, 0)))
    q0 = jk.q_polynomial().subs({delta: 0 for delta in jk.DELTA})
    direct_hat22 = jk.jk_hat_pair_coefficient(q0, 2, 2)

    even_results = {}
    for rank, delta in ((3, (1, 0, 0)), (4, (0, 1, 0)), (5, (0, 0, 1))):
        generated_all = generated_even_kernel_terms(delta)
        generated = {key: value for key, value in generated_all.items() if key[0] == delta}
        expected = expected_even_first_order_terms(rank)
        even_results[str(delta)] = {
            "matches_direct_identity": compare_expr_maps(generated, expected),
            "generated_terms": len(generated),
            "expected_terms": len(expected),
        }
    generated_second_all = generated_even_kernel_terms((2, 0, 0))
    generated_second = {key: value for key, value in generated_second_all.items() if key[0] == (2, 0, 0)}
    expected_second = expected_even_second_same_rank_terms(3)
    even_results[str((2, 0, 0))] = {
        "matches_direct_identity": compare_expr_maps(generated_second, expected_second),
        "generated_terms": len(generated_second),
        "expected_terms": len(expected_second),
    }

    hat_cases = (
        ((2, 2), (0, 0, 0)),
        ((2, 2), (1, 0, 0)),
        ((2, 2), (0, 1, 0)),
        ((2, 2), (0, 0, 1)),
        ((2, 2), (2, 0, 0)),
        ((2, 3), (0, 0, 0)),
        ((2, 3), (1, 0, 0)),
        ((3, 5), (0, 0, 0)),
        ((5, 5), (0, 0, 0)),
    )
    hat_results = {}
    for (r, s), delta in hat_cases:
        generated = dict(jk.hat_pair_delta(r, s, delta)).get(delta, sp.Integer(0))
        expected = expected_hat_pair_coeff(r, s, delta)
        hat_results[f"{(r, s)}@{delta}"] = expr_is_zero(generated - expected)

    required = {
        "even_zero_is_single_identity_term": even0 == (((0, 0, 0), (0, 0, 0, 0), sp.Integer(1)),),
        "hat22_delta0_matches_direct_formula": expr_is_zero(hat22[(0, 0, 0)] - direct_hat22),
        "low_delta_even_kernel_terms_match_direct_formula": all(item["matches_direct_identity"] for item in even_results.values()),
        "selected_hat_pair_delta_terms_match_matrix_identity": all(hat_results.values()),
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "required": required,
        "even_kernel_terms_delta0": even0,
        "hat22_delta0": hat22.get((0, 0, 0)),
        "direct_hat22_delta0": direct_hat22,
        "even_low_delta_results": even_results,
        "hat_pair_delta_results": hat_results,
    }


def delta_extraction_normalization_checks() -> Dict[str, Any]:
    d3, d4, _d5 = jk.DELTA
    y1, y2, _y3, _y4 = jk.Y
    zero_delta = {delta_symbol: 0 for delta_symbol in jk.DELTA}
    toy = sp.exp(d3 * y1 + d4 * y2)

    f3_squared_coeff = jk.delta_coefficient_at_zero(toy, (2, 0, 0))
    f3_squared_derivative = sp.diff(toy, d3, 2).subs(zero_delta)
    f3_squared_scaled = jk.f_factorial_scale((0, 2, 0, 0)) * f3_squared_coeff
    f3_squared_old_double_scaled = jk.f_factorial_scale((0, 2, 0, 0)) * f3_squared_derivative

    f4_squared_coeff = jk.delta_coefficient_at_zero(toy, (0, 2, 0))
    f4_squared_derivative = sp.diff(toy, d4, 2).subs(zero_delta)
    f4_squared_scaled = jk.f_factorial_scale((0, 0, 2, 0)) * f4_squared_coeff
    f4_squared_old_double_scaled = jk.f_factorial_scale((0, 0, 2, 0)) * f4_squared_derivative

    required = {
        "f3_squared_coefficient_has_delta_factorial_removed": expr_is_zero(f3_squared_coeff - y1**2 / 2),
        "f3_squared_final_scale_matches_derivative_extraction_once": expr_is_zero(
            f3_squared_scaled - f3_squared_derivative
        ),
        "f3_squared_old_double_factorial_would_fail": not expr_is_zero(
            f3_squared_old_double_scaled - f3_squared_scaled
        ),
        "f4_squared_coefficient_has_delta_factorial_removed": expr_is_zero(f4_squared_coeff - y2**2 / 2),
        "f4_squared_final_scale_matches_derivative_extraction_once": expr_is_zero(
            f4_squared_scaled - f4_squared_derivative
        ),
        "f4_squared_old_double_factorial_would_fail": not expr_is_zero(
            f4_squared_old_double_scaled - f4_squared_scaled
        ),
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "required": required,
        "f3_squared_coefficient": f3_squared_coeff,
        "f3_squared_scaled": f3_squared_scaled,
        "f3_squared_old_double_scaled": f3_squared_old_double_scaled,
        "f4_squared_coefficient": f4_squared_coeff,
        "f4_squared_scaled": f4_squared_scaled,
        "f4_squared_old_double_scaled": f4_squared_old_double_scaled,
    }


def b_mask_map_from_terms(terms: Iterable[Tuple[int, Sequence[jk.BLabel]]]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for coeff, labels in terms:
        target = jk.b_product_to_mask(labels)
        if target is None:
            continue
        sign, mask = target
        out[mask] = out.get(mask, 0) + coeff * sign
    return {mask: coeff for mask, coeff in out.items() if coeff}


def b_mask_map_from_gamma_exp(gamma_exp: Sequence[int]) -> Dict[int, int]:
    return b_mask_map_from_terms(jk.gamma_product_to_b_terms(gamma_exp))


def multiply_b_mask_maps(left: Dict[int, int], right: Dict[int, int]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for left_mask, left_coeff in left.items():
        for right_mask, right_coeff in right.items():
            wedge = jk.wedge_masks(left_mask, right_mask)
            if wedge is None:
                continue
            sign, mask = wedge
            out[mask] = out.get(mask, 0) + left_coeff * right_coeff * sign
    return {mask: coeff for mask, coeff in out.items() if coeff}


def gamma_checks() -> Dict[str, Any]:
    single_gamma_results = {}
    for idx, label in enumerate(jk.GAMMA_LABELS):
        exp = [0 for _ in jk.GAMMA_LABELS]
        exp[idx] = 1
        actual = b_mask_map_from_gamma_exp(exp)
        expected = b_mask_map_from_terms(jk.gamma_b_terms(*label))
        single_gamma_results[str(label)] = actual == expected

    symmetry_results = {}
    for r in range(2, 6):
        for s in range(2, 6):
            left = b_mask_map_from_terms(jk.gamma_b_terms(r, s))
            right = b_mask_map_from_terms(jk.gamma_b_terms(s, r))
            symmetry_results[str((r, s))] = left == right

    gamma22_exp = [0 for _ in jk.GAMMA_LABELS]
    gamma22_exp[jk.GAMMA_INDEX[(2, 2)]] = 1
    gamma22 = b_mask_map_from_gamma_exp(gamma22_exp)
    expected_gamma22 = b_mask_map_from_terms((
        (2, ((2, 1), (2, 3))),
        (2, ((2, 2), (2, 4))),
    ))

    gamma33_exp = [0 for _ in jk.GAMMA_LABELS]
    gamma33_exp[jk.GAMMA_INDEX[(3, 3)]] = 1
    product_exp = [0 for _ in jk.GAMMA_LABELS]
    product_exp[jk.GAMMA_INDEX[(2, 2)]] = 1
    product_exp[jk.GAMMA_INDEX[(3, 3)]] = 1
    actual_product = b_mask_map_from_gamma_exp(product_exp)
    expected_product = multiply_b_mask_maps(gamma22, b_mask_map_from_gamma_exp(gamma33_exp))

    gamma22_cubed_exp = [0 for _ in jk.GAMMA_LABELS]
    gamma22_cubed_exp[jk.GAMMA_INDEX[(2, 2)]] = 3
    gamma22_cubed = b_mask_map_from_gamma_exp(gamma22_cubed_exp)

    required = {
        "all_single_gamma_expansions_match_definition": all(single_gamma_results.values()),
        "gamma_is_symmetric_in_indices": all(symmetry_results.values()),
        "gamma22_matches_documented_simplification": gamma22 == expected_gamma22,
        "two_gamma_product_matches_exterior_multiplication": actual_product == expected_product and bool(actual_product),
        "gamma22_cubed_vanishes_by_exterior_degree": gamma22_cubed == {},
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "required": required,
        "single_gamma_results": single_gamma_results,
        "symmetry_results": symmetry_results,
        "gamma22_mask_coefficients": gamma22,
        "gamma22_gamma33_term_count": len(actual_product),
        "gamma22_cubed_term_count": len(gamma22_cubed),
    }


def sparse_mod_items(expr: sp.Expr, p: int) -> Tuple[Tuple[jk.Alpha, int], ...]:
    return tuple(sorted(fm.sympy_expr_to_sparse_mod(expr, p).items()))


def expected_gamma_mask_expansion_mod(gamma_exp: Sequence[int], p: int) -> Tuple[Tuple[int, int], ...]:
    expected = {
        mask: coeff % p
        for mask, coeff in b_mask_map_from_gamma_exp(gamma_exp).items()
        if coeff % p
    }
    return tuple(sorted(expected.items()))


def fast_modular_connection_checks() -> Dict[str, Any]:
    p = 1_000_003

    tau_results = {
        f"tau{r}": dict(fm.rank5_tau_mod(r, p)) == fm.sympy_expr_to_sparse_mod(jk.tau(r), p)
        for r in range(2, 6)
    }
    a_exp = (1, 0, 1, 0)
    tau_power_matches = (
        dict(fm.tau_power_mod(a_exp, p)) == fm.sympy_expr_to_sparse_mod(jk.a_monomial_factor(a_exp), p)
    )

    even_results = {}
    for max_delta in (
        (0, 0, 0),
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (2, 0, 0),
        (3, 0, 0),
        (2, 1, 0),
        (1, 1, 1),
    ):
        expected = tuple(
            (delta, deriv_orders, sparse_mod_items(expr, p))
            for delta, deriv_orders, expr in jk.even_kernel_terms(max_delta)
        )
        actual = fm.even_kernel_terms_mod(max_delta, p)
        even_results[str(max_delta)] = {
            "matches_symbolic_generator": actual == expected,
            "modular_term_count": len(actual),
            "symbolic_term_count": len(expected),
        }

    hat_results = {}
    for r, s, max_delta in (
        (2, 2, (0, 0, 0)),
        (2, 2, (1, 0, 0)),
        (2, 3, (0, 0, 0)),
        (3, 5, (0, 0, 0)),
        (5, 5, (0, 0, 0)),
        (2, 2, (3, 0, 0)),
        (2, 4, (1, 1, 0)),
    ):
        expected = tuple(
            (delta, sparse_mod_items(expr, p))
            for delta, expr in jk.hat_pair_delta(r, s, max_delta)
        )
        actual = fm.hat_pair_delta_mod(r, s, max_delta, p)
        hat_results[f"{(r, s)}@{max_delta}"] = actual == expected

    single_gamma_results = {}
    for idx, label in enumerate(jk.GAMMA_LABELS):
        exp = [0 for _ in jk.GAMMA_LABELS]
        exp[idx] = 1
        single_gamma_results[str(label)] = (
            fm.gamma_mask_expansion(tuple(exp), p) == expected_gamma_mask_expansion_mod(exp, p)
        )

    pair_mask = fm.bit_for_label((2, 1)) | fm.bit_for_label((2, 3))
    expected_pair_hat = tuple(
        (delta, sparse_mod_items(expr, p))
        for delta, expr in jk.hat_pair_delta(2, 2, (0, 0, 0))
    )
    actual_pair_hat = fm.b_hat_mask_mod(pair_mask, (0, 0, 0), p)

    zero_gamma = tuple(0 for _ in jk.GAMMA_LABELS)
    identity_delta = (((0, 0, 0), (((0, 0, 0, 0), 1),)),)
    inv5 = fm.mod_inv(5, p)
    special_series_results = {
        "F_residue_coeff_is_one": fm.special_derivative_dict_mod(0, -2, 8, p).get(-1) == 1,
        "F_prime_residue_coeff_is_minus_lambda": (
            fm.special_derivative_dict_mod(1, -2, 8, p).get(-1) == 2 * inv5 % p
        ),
    }
    residue_batch_results = {}
    residue_polys = (
        {(0, 0, 0, 0): 1},
        {(4, 0, 0, 0): 3, (1, 2, 0, 1): 5},
        {(0, 4, 2, 1): 7, (3, 0, 1, 0): 11, (1, 1, 1, 1): 13},
    )
    residue_derivs = ((0, 0, 0, 0), (1, 0, 0, 0), (2, 1, 0, 0), (0, 1, 2, 3))
    for poly in residue_polys:
        for deriv in residue_derivs:
            key = f"{poly}@{deriv}"
            residue_batch_results[key] = (
                fm.residue_poly_mod_batch(poly, deriv, p)
                == fm.residue_poly_mod_termwise(poly, deriv, p)
                == fm.residue_poly_mod(poly, deriv, p)
            )
    real_poly_residue_results = {}
    real_poly_residue_sample_counts = {}
    real_poly_residue_sample_plan = (
        ("zero_delta_real_pairing_poly", 0, 760, 1, False),
        ("mixed_delta_real_pairing_poly", 8, 760, 3, False),
        ("higher_delta_real_pairing_poly", 15, 760, 3, False),
        ("gamma_heavy_real_pairing_poly", 2, 1031, 1, True),
    )
    real_poly_residue_intended_count = sum(item[3] for item in real_poly_residue_sample_plan)
    gamma_heavy_real_poly_sample_seen = False
    source18, _raw_counts18, _meta18 = basis.independent_basis_by_chern(5, 22, [18])
    w_basis26, _w_meta26 = basis.independent_invariant_basis(5, 26)
    for label, row_idx, w_idx, wanted_count, requires_gamma in real_poly_residue_sample_plan:
        total = fm.add_invariant_exp(source18[18][row_idx].exp, w_basis26[w_idx].exp)
        if requires_gamma and sum(total.gamma) >= 4:
            gamma_heavy_real_poly_sample_seen = True
        target_delta = (total.f[1], total.f[2], total.f[3])
        b_delta = {
            delta: dict(poly)
            for delta, poly in fm.gamma_hat_mod(total.gamma, target_delta, p)
        }
        a_poly = dict(fm.tau_power_mod(total.a, p))
        sample_count = 0
        for kd, deriv_orders, kval_items in fm.even_kernel_terms_mod(target_delta, p):
            bd = fm.delta_sub(target_delta, kd)
            if bd is None or bd not in b_delta:
                continue
            full_poly = fm.sparse_mul(a_poly, fm.sparse_mul(dict(kval_items), b_delta[bd], p), p)
            if not full_poly:
                continue
            key = (
                f"{label}:row{row_idx}:{source18[18][row_idx].name}:"
                f"w{w_idx}:{w_basis26[w_idx].name}@{kd}/{deriv_orders}"
            )
            real_poly_residue_results[key] = (
                fm.residue_poly_mod_batch(full_poly, deriv_orders, p)
                == fm.residue_poly_mod_termwise(full_poly, deriv_orders, p)
            )
            sample_count += 1
            if sample_count >= wanted_count:
                break
        real_poly_residue_sample_counts[label] = sample_count
    try:
        fm.mod_inv(p, p)
        zero_denominator_rejected = False
    except ZeroDivisionError:
        zero_denominator_rejected = True

    required = {
        "rank5_tau_mod_matches_symbolic_tau": all(tau_results.values()),
        "tau_power_mod_matches_symbolic_a_factor": tau_power_matches,
        "even_kernel_mod_matches_symbolic_generator": all(
            item["matches_symbolic_generator"] for item in even_results.values()
        ),
        "hat_pair_mod_matches_symbolic_generator": all(hat_results.values()),
        "gamma_mask_mod_matches_jk_gamma_expansion": all(single_gamma_results.values()),
        "b_hat_pair_mod_matches_hat_pair_delta": actual_pair_hat == expected_pair_hat,
        "zero_gamma_hat_is_identity": fm.gamma_hat_mod(zero_gamma, (0, 0, 0), p) == identity_delta,
        "one_variable_special_series_matches_tiny_residue_identities": all(special_series_results.values()),
        "batched_residue_matches_termwise_residue": all(residue_batch_results.values()),
        "batched_residue_matches_termwise_on_real_pairing_polys": (
            len(real_poly_residue_results) == real_poly_residue_intended_count
            and all(real_poly_residue_results.values())
            and all(
                real_poly_residue_sample_counts[label] == wanted_count
                for label, _row_idx, _w_idx, wanted_count, _requires_gamma in real_poly_residue_sample_plan
            )
            and gamma_heavy_real_poly_sample_seen
        ),
        "residue_transition_has_no_fixed_cutoff_constant": not hasattr(fm, "RANK5_RESIDUE_SERIES_CUTOFF"),
        "modular_inverse_rejects_zero_denominator": zero_denominator_rejected,
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "prime": p,
        "required": required,
        "tau_results": tau_results,
        "tau_power_test_exponents": a_exp,
        "even_results": even_results,
        "hat_results": hat_results,
        "single_gamma_results": single_gamma_results,
        "pair_hat_term_count": len(actual_pair_hat),
        "special_series_results": special_series_results,
        "residue_batch_results": residue_batch_results,
        "real_poly_residue_results": real_poly_residue_results,
        "real_poly_residue_sample_counts": real_poly_residue_sample_counts,
        "real_poly_residue_intended_count": real_poly_residue_intended_count,
        "gamma_heavy_real_poly_sample_seen": gamma_heavy_real_poly_sample_seen,
        "zero_denominator_rejected": zero_denominator_rejected,
    }


def tiny_residue_checks() -> Dict[str, Any]:
    z = sp.Symbol("z")
    lam = sp.Rational(-2, 5)
    f = 1 / (1 - sp.exp(-z))
    res_f = jk.one_variable_residue(sp.exp(lam * z) * f, z, 10)
    res_df = jk.one_variable_residue(sp.exp(lam * z) * sp.diff(f, z), z, 10)
    required = {
        "res_exp_lambda_over_one_minus_exp_minus_z_is_one": expr_is_zero(res_f - 1),
        "res_exp_lambda_times_derivative_is_minus_lambda": expr_is_zero(res_df + lam),
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "required": required,
        "lambda": lam,
        "residue_basic": res_f,
        "residue_derivative": res_df,
    }


def rank_search_checks() -> Dict[str, Any]:
    p = 1_000_003
    prime_validation = mrs.validate_prime(p)
    try:
        mrs.validate_prime(1001)
        composite_rejected = False
    except ValueError:
        composite_rejected = True

    pivots: Dict[int, List[int]] = {}
    first_pivot, first_normalized = mrs.reduce_column([2, 0], pivots, p)
    if first_pivot is not None:
        pivots[first_pivot] = first_normalized
    second_pivot, second_normalized = mrs.reduce_column([2, 3], pivots, p)
    if second_pivot is not None:
        pivots[second_pivot] = second_normalized
    determinant_test = mrs.determinant_mod([[2, 2], [0, 3]], p) == 6
    synthetic_relation_columns = {0: [1, 0, 2], 1: [0, 1, 3]}
    synthetic_kernel, synthetic_kernel_norm = mrs.left_kernel_vector_from_selected_minor(
        row_count=3,
        selected_rows=[0, 1],
        selected_columns=[0, 1],
        column_vectors=synthetic_relation_columns,
        p=p,
    )
    relation_kernel_helper_ok = (
        synthetic_kernel == [p - 2, p - 3, 1]
        and synthetic_kernel_norm["omitted_row_index"] == 2
        and all(mrs.dot_mod(synthetic_kernel, col, p) == 0 for col in synthetic_relation_columns.values())
    )

    source_by_chern, _raw_counts, _meta = basis.independent_basis_by_chern(5, 22, [21, 22])
    w_basis, w_meta = basis.independent_invariant_basis(5, 26)
    source22 = source_by_chern[22]
    basis_dimensions_match = {
        "c21_source_dimension_is_one": len(source_by_chern[21]) == 1,
        "c22_source_dimension_is_one": len(source22) == 1,
        "w26_dimension_is_1039": len(w_basis) == 1039 and w_meta["invariant_rank"] == 1039,
    }

    full_rank_result = mrs.build_chern_result(
        22,
        source22,
        w_basis,
        p,
        "memory-cache",
        {0: [5]},
        [0],
        [0],
        [{"from_column_cache": False, "elapsed_seconds": 0.0}],
        {"mode": "unit-test"},
        compute_determinant=True,
        stop_reason="full_rank_reached",
    )
    partial_result = mrs.build_chern_result(
        22,
        source22,
        w_basis,
        p,
        "memory-cache",
        {},
        [],
        [],
        [],
        {"mode": "unit-test"},
        compute_determinant=True,
        stop_reason="max_columns_reached",
    )
    checkpoint_full_rank_result = mrs.build_chern_result(
        22,
        source22,
        w_basis,
        p,
        "memory-cache",
        {0: [5]},
        [0],
        [0],
        [{"from_column_cache": False, "elapsed_seconds": 0.0}],
        {"mode": "unit-test"},
        compute_determinant=False,
        stop_reason="checkpoint_pending",
    )
    singular_certificate_result = mrs.build_chern_result(
        22,
        source22,
        w_basis,
        p,
        "memory-cache",
        {0: [0]},
        [0],
        [0],
        [{"from_column_cache": False, "elapsed_seconds": 0.0}],
        {"mode": "unit-test"},
        compute_determinant=True,
        stop_reason="full_rank_reached",
    )
    try:
        mrs.parse_int_list("11,,12")
        empty_int_list_component_rejected = False
    except ValueError:
        empty_int_list_component_rejected = True

    with tempfile.TemporaryDirectory() as tmpdir:
        args = argparse.Namespace(source_degree=22, w_degree=26, column_cache_dir=tmpdir)
        cache_path = os.path.join(tmpdir, "columns.pkl")
        mrs.save_column_cache(cache_path, 22, p, source22, w_basis, args, {0: [5]})
        cache_roundtrip_ok = mrs.load_column_cache(cache_path, 22, p, source22, w_basis, args) == {0: [5]}
        with open(cache_path, "rb") as handle:
            payload = pickle.load(handle)
        payload["source_file_sha256"]["fast_modular.py"] = "stale"
        with open(cache_path, "wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        try:
            mrs.load_column_cache(cache_path, 22, p, source22, w_basis, args)
            stale_cache_rejected = False
        except RuntimeError:
            stale_cache_rejected = True

    with tempfile.TemporaryDirectory() as tmpdir:
        adaptive_payload = mrs.run_search(argparse.Namespace(
            prime=p,
            source_degree=22,
            w_degree=26,
            chern_degrees="22",
            column_order="cheap-probe",
            planner_sample_rows=1,
            probe_planner_sample_rows=1,
            probe_planner_pool_size=3,
            rank_planner_sample_rows=1,
            rank_planner_pool_size=3,
            evaluation_mode="adaptive-partial",
            max_columns=5,
            max_new_columns=None,
            max_seconds=None,
            column_cache_dir=tmpdir,
            save_column_cache_every=0,
            cache_first=True,
            checkpoint_output="",
            checkpoint_every=0,
            verbose=False,
            output=os.path.join(tmpdir, "adaptive.json"),
        ))
        adaptive_result = adaptive_payload["results"][0]
        adaptive_partial_ok = (
            adaptive_payload["status"] == "passed"
            and adaptive_result["status"] == "full_rank_mod_p"
            and adaptive_result["adaptive_partial_mode"]
            and adaptive_result["adaptive_partial_entries_evaluated"] <= len(source22) * 5
            and adaptive_result["certificate_status"] == "selected_minor_certified"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = os.path.join(tmpdir, "manifest.json")
        shard_dir = os.path.join(tmpdir, "shards")
        reduce_path = os.path.join(tmpdir, "reduce.json")
        verify_path = os.path.join(tmpdir, "verify.json")
        manifest_args = argparse.Namespace(
            prime=p,
            source_degree=22,
            w_degree=26,
            chern_degrees="22",
            column_order="cheap-probe",
            planner_sample_rows=1,
            probe_planner_sample_rows=1,
            probe_planner_pool_size=1,
            rank_planner_sample_rows=1,
            rank_planner_pool_size=1,
            columns_per_task=2,
            wave_size=10,
            shard_mode="task",
            output=manifest_path,
        )
        manifest_payload = crd.build_manifest(manifest_args)

        def mutated_manifest_rejected(mutator) -> bool:
            bad_manifest = json.loads(json.dumps(manifest_payload))
            mutator(bad_manifest)
            try:
                crd.assert_manifest_current(bad_manifest)
                return False
            except (RuntimeError, ValueError, KeyError):
                return True

        manifest_validator_results = {
            "duplicate_task_id_rejected": mutated_manifest_rejected(
                lambda bad: bad["tasks"][1].__setitem__("task_index", bad["tasks"][0]["task_index"])
            ),
            "empty_w_indices_rejected": mutated_manifest_rejected(
                lambda bad: bad["tasks"][0].__setitem__("w_indices", [])
            ),
            "invalid_manifest_cdegree_rejected": mutated_manifest_rejected(
                lambda bad: bad.__setitem__("chern_degrees", [999])
            ),
            "task_cdegree_outside_manifest_rejected": mutated_manifest_rejected(
                lambda bad: bad["tasks"][0].__setitem__("chern_degree", 21)
            ),
            "invalid_w_index_rejected": mutated_manifest_rejected(
                lambda bad: bad["tasks"][0].__setitem__("w_indices", [999999])
            ),
            "wave_index_inconsistency_rejected": mutated_manifest_rejected(
                lambda bad: bad["tasks"][0].__setitem__("wave_index", bad["tasks"][0]["wave_index"] + 1)
            ),
            "task_count_mismatch_rejected": mutated_manifest_rejected(
                lambda bad: bad.__setitem__("task_count", bad["task_count"] + 1)
            ),
            "prime_validation_mismatch_rejected": mutated_manifest_rejected(
                lambda bad: bad["prime_validation"].__setitem__("prime_verified", False)
            ),
            "truncated_manifest_rejected": mutated_manifest_rejected(
                lambda bad: (bad.__setitem__("tasks", bad["tasks"][:1]), bad.__setitem__("task_count", 1))
            ),
        }
        worker_payload = crd.compute_worker(argparse.Namespace(
            manifest=manifest_path,
            task_index="0",
            all_tasks=False,
            wave_index=None,
            shard_dir=shard_dir,
            shard_mode="auto",
            skip_existing=False,
            repair_existing=True,
            output="",
        ))
        reduce_payload = crd.reduce_shards(argparse.Namespace(
            manifest=manifest_path,
            shard_dir=shard_dir,
            shard_mode="auto",
            output=reduce_path,
        ))
        verify_payload = crd.verify_certificate(argparse.Namespace(
            manifest=manifest_path,
            reduce_output=reduce_path,
            second_prime=0,
            allow_in_progress=False,
            output=verify_path,
        ))
        verify_second_prime_payload = crd.verify_certificate(argparse.Namespace(
            manifest=manifest_path,
            reduce_output=reduce_path,
            second_prime=1000033,
            allow_in_progress=False,
            output="",
        ))
        wave_from_reduce = crd.plan_wave(argparse.Namespace(
            manifest=manifest_path,
            wave_index=0,
            chern_degrees="",
            previous_reduce=reduce_path,
            previous_verification=verify_path,
            output="",
        ))
        try:
            crd.plan_wave(argparse.Namespace(
                manifest=manifest_path,
                wave_index=0,
                chern_degrees="",
                previous_reduce=reduce_path,
                previous_verification="",
                output="",
            ))
            missing_previous_verification_rejected = False
        except RuntimeError:
            missing_previous_verification_rejected = True
        bad_reduce_path = os.path.join(tmpdir, "bad_reduce.json")
        bad_reduce_payload = json.loads(json.dumps(reduce_payload))
        bad_reduce_payload["manifest_sha256"] = "stale"
        with open(bad_reduce_path, "w", encoding="utf-8") as handle:
            json.dump(bad_reduce_payload, handle)
        try:
            crd.plan_wave(argparse.Namespace(
                manifest=manifest_path,
                wave_index=0,
                chern_degrees="",
                previous_reduce=bad_reduce_path,
                previous_verification=verify_path,
                output="",
            ))
            stale_previous_reduce_rejected = False
        except RuntimeError:
            stale_previous_reduce_rejected = True
        bad_reduce_cert_path = os.path.join(tmpdir, "bad_reduce_cert.json")
        bad_reduce_cert_payload = json.loads(json.dumps(reduce_payload))
        bad_reduce_cert_payload["results"][0]["certificate_complete"] = False
        with open(bad_reduce_cert_path, "w", encoding="utf-8") as handle:
            json.dump(bad_reduce_cert_payload, handle)
        try:
            crd.plan_wave(argparse.Namespace(
                manifest=manifest_path,
                wave_index=0,
                chern_degrees="",
                previous_reduce=bad_reduce_cert_path,
                previous_verification=verify_path,
                output="",
            ))
            forged_previous_reduce_rejected = False
        except RuntimeError:
            forged_previous_reduce_rejected = True
        try:
            crd.compute_worker(argparse.Namespace(
                manifest=manifest_path,
                task_index="0",
                all_tasks=False,
                wave_index=None,
                shard_dir=shard_dir,
                shard_mode="column",
                skip_existing=False,
                repair_existing=True,
                output="",
            ))
            shard_mode_mismatch_rejected = False
        except RuntimeError:
            shard_mode_mismatch_rejected = True
        try:
            crd.compute_worker(argparse.Namespace(
                manifest=manifest_path,
                task_index="999999",
                all_tasks=False,
                wave_index=None,
                shard_dir=shard_dir,
                shard_mode="auto",
                skip_existing=False,
                repair_existing=True,
                output="",
            ))
            empty_task_rejected = False
        except ValueError:
            empty_task_rejected = True
        manifest_sha = mrs.sha256_file(manifest_path)
        first_output = worker_payload["outputs"][0]
        with open(first_output["path"], "r", encoding="utf-8") as handle:
            shard_payload = json.load(handle)
        shard_payload["schema_version"] = -1
        with open(first_output["path"], "w", encoding="utf-8") as handle:
            json.dump(shard_payload, handle)
        try:
            crd.load_task_shard_bundle(
                manifest_payload,
                manifest_sha,
                shard_dir,
                manifest_payload["tasks"][0],
                len(source22),
                w_basis,
            )
            shard_schema_rejected = False
        except RuntimeError:
            shard_schema_rejected = True
        cluster_roundtrip_ok = (
            manifest_payload["task_count"] >= 1
            and worker_payload["outputs"]
            and worker_payload["outputs"][0]["status"] == "computed_task_bundle"
            and worker_payload["outputs"][0]["precomputed_entries_used"] >= 1
            and reduce_payload["kind"] == "jk_only_cluster_reduce_result"
            and reduce_payload["manifest_sha256"] == manifest_sha
            and reduce_payload["shard_mode"] == "task"
            and reduce_payload["results"][0]["status"] == "full_rank_mod_p"
            and reduce_payload["results"][0]["shard_mode"] == "task"
            and reduce_payload["results"][0]["selected_shard_certificates"]
            and reduce_payload["results"][0]["selected_minor_matrix_sha256"]
            and reduce_payload["reduction_log"]
            and verify_payload["status"] == "passed"
            and verify_second_prime_payload["status"] == "passed"
            and os.path.exists(reduce_path)
        )

    required = {
        "valid_prime_accepts_and_records_method": bool(prime_validation["prime_verified"]),
        "composite_modulus_rejected": composite_rejected,
        "reduce_column_finds_expected_pivots": first_pivot == 0 and second_pivot == 1,
        "determinant_mod_matches_known_value": determinant_test,
        "relation_kernel_helper_smoke": relation_kernel_helper_ok,
        "basis_dimensions_match_probe": all(basis_dimensions_match.values()),
        "full_rank_result_has_nonzero_minor_certificate": (
            full_rank_result["status"] == "full_rank_mod_p"
            and full_rank_result["selected_minor_determinant_mod_p"] == "5"
            and full_rank_result["selected_minor_matrix_mod_p"] == [["5"]]
            and bool(full_rank_result["selected_minor_matrix_sha256"])
        ),
        "checkpoint_full_rank_is_provisional_without_minor": (
            checkpoint_full_rank_result["status"] == "checkpoint_full_rank_unverified"
            and not checkpoint_full_rank_result["full_rank_mod_p"]
            and checkpoint_full_rank_result["certificate_status"] == "provisional_checkpoint"
        ),
        "singular_minor_certificate_status_is_not_certified": (
            singular_certificate_result["status"] == "rank_reached_but_selected_minor_singular"
            and singular_certificate_result["certificate_status"] == "selected_minor_singular"
            and not singular_certificate_result["certificate_complete"]
            and singular_certificate_result["certified_rank_lower_bound"] == 0
        ),
        "integer_list_empty_component_rejected": empty_int_list_component_rejected,
        "partial_status_does_not_pass": partial_result["status"] == "max_columns_reached",
        "column_cache_roundtrip_ok": cache_roundtrip_ok,
        "stale_cache_rejected": stale_cache_rejected,
        "adaptive_partial_rank_search_smoke": adaptive_partial_ok,
        "cluster_manifest_validator_rejects_bad_manifests": all(manifest_validator_results.values()),
        "cluster_manifest_worker_reduce_roundtrip_ok": cluster_roundtrip_ok,
        "cluster_previous_reduce_bound_to_manifest_hash": (
            wave_from_reduce["status"] == "no_unresolved_chern_degrees"
            and missing_previous_verification_rejected
            and stale_previous_reduce_rejected
            and forged_previous_reduce_rejected
        ),
        "cluster_shard_mode_mismatch_rejected": shard_mode_mismatch_rejected,
        "cluster_verify_certificate_roundtrip_ok": verify_payload["status"] == "passed",
        "cluster_verify_certificate_second_prime_ok": verify_second_prime_payload["status"] == "passed",
        "cluster_empty_task_selection_rejected": empty_task_rejected,
        "cluster_shard_schema_mismatch_rejected": shard_schema_rejected,
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "required": required,
        "prime_validation": prime_validation,
        "basis_dimensions": {
            "c21": len(source_by_chern[21]),
            "c22": len(source22),
            "w26": len(w_basis),
        },
        "basis_dimension_checks": basis_dimensions_match,
        "relation_kernel_helper_ok": relation_kernel_helper_ok,
        "synthetic_relation_kernel": synthetic_kernel,
        "full_rank_result_status": full_rank_result["status"],
        "checkpoint_full_rank_result_status": checkpoint_full_rank_result["status"],
        "singular_certificate_status": singular_certificate_result["certificate_status"],
        "partial_result_status": partial_result["status"],
        "manifest_validator_results": manifest_validator_results,
        "adaptive_partial_ok": adaptive_partial_ok,
        "cluster_roundtrip_ok": cluster_roundtrip_ok,
        "wave_from_reduce_status": wave_from_reduce["status"],
        "missing_previous_verification_rejected": missing_previous_verification_rejected,
        "stale_previous_reduce_rejected": stale_previous_reduce_rejected,
        "forged_previous_reduce_rejected": forged_previous_reduce_rejected,
        "shard_mode_mismatch_rejected": shard_mode_mismatch_rejected,
        "verify_certificate_status": verify_payload["status"],
        "verify_second_prime_status": verify_second_prime_payload["status"],
        "empty_task_rejected": empty_task_rejected,
        "shard_schema_rejected": shard_schema_rejected,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    started = time.time()
    checks = {
        "guardrail_scan": guardrail_scan(),
        "ast_import_allowlist": ast_import_allowlist_check(),
        "structural": structural_checks(),
        "setup_generator_checks": setup_generator_checks(),
        "delta_extraction_normalization_checks": delta_extraction_normalization_checks(),
        "gamma_checks": gamma_checks(),
        "fast_modular_connection_checks": fast_modular_connection_checks(),
        "tiny_residue_checks": tiny_residue_checks(),
        "rank_search_checks": rank_search_checks(),
    }
    payload = {
        "runner": "jk_only_run_checks",
        "status": "passed" if all(check["status"] == "passed" for check in checks.values()) else "failed",
        "elapsed_seconds": time.time() - started,
        "provenance": provenance(),
        "checks": checks,
    }
    ready = json_ready(payload)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(ready, handle, indent=2, sort_keys=True)
    print(json.dumps(ready, indent=2, sort_keys=True))
    if payload["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
