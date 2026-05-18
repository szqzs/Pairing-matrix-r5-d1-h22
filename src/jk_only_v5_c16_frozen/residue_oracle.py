#!/usr/bin/env python
"""Small independent residue oracle for the JK-only fast modular path."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from functools import lru_cache
from typing import Any, Dict, List, Tuple

import sympy as sp

import fast_modular as fm


HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_OUTPUT = os.path.join(HERE, "residue_oracle_results.json")
ORACLE_PRIME = 1_000_003

Alpha = Tuple[int, int, int, int]
DerivOrders = Tuple[int, int, int, int]
DenomPowers = Tuple[int, ...]

ROOT_INTERVALS = tuple((i, j) for i in range(4) for j in range(i + 1, 5))
ROOT_INDEX = {interval: idx for idx, interval in enumerate(ROOT_INTERVALS)}
ROOT_POWERS = tuple(2 for _ in ROOT_INTERVALS)
ZERO_ALPHA: Alpha = (0, 0, 0, 0)
ZERO_DENOM = tuple(0 for _ in ROOT_INTERVALS)
BASE_LAMBDA_NUMS = (-1, -2, -3, -4)

Z = sp.Symbol("z")


def mod_inv(value: int, p: int) -> int:
    value %= p
    if value == 0:
        raise ZeroDivisionError(f"denominator is 0 modulo prime {p}")
    return pow(value, p - 2, p)


def rational_mod(value: sp.Expr, p: int) -> int:
    rat = sp.Rational(value)
    return int(rat.p) % p * mod_inv(int(rat.q), p) % p


@lru_cache(maxsize=None)
def roots_with_current_variable(var_idx: int) -> Tuple[Tuple[int, int], ...]:
    out = []
    for interval, pos in ROOT_INDEX.items():
        if interval[1] != var_idx + 1:
            continue
        lower_pos = -1 if interval[0] == var_idx else ROOT_INDEX[(interval[0], var_idx)]
        out.append((pos, lower_pos))
    return tuple(out)


def survivable_y_bound(
    var_idx: int,
    deriv_orders: DerivOrders,
    denom_powers: DenomPowers,
    current_root_pos: int,
) -> int:
    simple_pos = ROOT_INDEX[(var_idx, var_idx + 1)]
    simple_drop = denom_powers[simple_pos] if current_root_pos < simple_pos else 0
    return deriv_orders[var_idx] + simple_drop


@lru_cache(maxsize=None)
def binomial_coeffs_from_sympy(root_power: int, max_m: int, p: int) -> Tuple[int, ...]:
    series = sp.series((1 + Z) ** (-root_power), Z, 0, max_m + 1).removeO()
    return tuple(rational_mod(series.coeff(Z, m), p) for m in range(max_m + 1))


@lru_cache(maxsize=None)
def special_coeff_from_sympy(order: int, lam_num: int, y_exp: int, p: int) -> int:
    target_exp = -1 - y_exp
    factor = 1 / (1 - sp.exp(-Z))
    if order:
        factor = sp.diff(factor, Z, order)
    expr = sp.exp(sp.Rational(lam_num, 5) * Z) * factor
    coeff = sp.series(expr, Z, 0, max(4, target_exp + 2)).removeO().coeff(Z, target_exp)
    return rational_mod(coeff, p)


@lru_cache(maxsize=None)
def brute_variable_transition_mod(
    var_idx: int,
    deriv_orders: DerivOrders,
    y_exp: int,
    denom_powers: DenomPowers,
    p: int,
) -> Tuple[Tuple[DenomPowers, int], ...]:
    states: Dict[Tuple[int, DenomPowers], int] = {(int(y_exp), denom_powers): 1}
    for pos, lower_pos in roots_with_current_variable(var_idx):
        next_states: Dict[Tuple[int, DenomPowers], int] = {}
        for (cur_y_exp, current_denoms), state_coeff in states.items():
            root_power = current_denoms[pos]
            if not root_power:
                key = (cur_y_exp, current_denoms)
                next_states[key] = (next_states.get(key, 0) + state_coeff) % p
                continue

            base_denoms_list = list(current_denoms)
            base_denoms_list[pos] = 0
            base_denoms = tuple(base_denoms_list)
            y_bound = survivable_y_bound(var_idx, deriv_orders, base_denoms, pos)

            if lower_pos < 0:
                next_y_exp = cur_y_exp - root_power
                if next_y_exp <= y_bound:
                    key = (next_y_exp, base_denoms)
                    next_states[key] = (next_states.get(key, 0) + state_coeff) % p
                continue

            max_m = y_bound - cur_y_exp
            if max_m < 0:
                continue
            for m, binom_coeff in enumerate(binomial_coeffs_from_sympy(root_power, max_m, p)):
                expanded_denoms = list(base_denoms)
                expanded_denoms[lower_pos] += root_power + m
                key = (cur_y_exp + m, tuple(expanded_denoms))
                next_states[key] = (next_states.get(key, 0) + state_coeff * binom_coeff) % p

        states = {key: val for key, val in next_states.items() if val % p}
        if not states:
            return ()

    out: Dict[DenomPowers, int] = {}
    for (cur_y_exp, current_denoms), state_coeff in states.items():
        special_coeff = special_coeff_from_sympy(
            deriv_orders[var_idx],
            BASE_LAMBDA_NUMS[var_idx],
            cur_y_exp,
            p,
        )
        if special_coeff:
            out[current_denoms] = (out.get(current_denoms, 0) + state_coeff * special_coeff) % p
    return tuple(sorted((denoms, coeff) for denoms, coeff in out.items() if coeff % p))


def slow_residue_monomial_mod(alpha: Alpha, deriv_orders: DerivOrders, p: int) -> int:
    terms: Dict[Tuple[Alpha, DenomPowers], int] = {(alpha, ROOT_POWERS): 1}
    for var_idx in reversed(range(4)):
        new_terms: Dict[Tuple[Alpha, DenomPowers], int] = {}
        for (current_alpha, denom_powers), coeff in terms.items():
            next_alpha_list = list(current_alpha)
            next_alpha_list[var_idx] = 0
            next_alpha = tuple(next_alpha_list)  # type: ignore[assignment]
            for new_denoms, transition_coeff in brute_variable_transition_mod(
                var_idx,
                deriv_orders,
                current_alpha[var_idx],
                denom_powers,
                p,
            ):
                key = (next_alpha, new_denoms)
                new_terms[key] = (new_terms.get(key, 0) + coeff * transition_coeff) % p
        terms = {key: val for key, val in new_terms.items() if val % p}
        if not terms:
            return 0

    total = 0
    for (current_alpha, denom_powers), coeff in terms.items():
        if current_alpha == ZERO_ALPHA and denom_powers == ZERO_DENOM:
            total = (total + coeff) % p
    return total


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


def run_oracle(p: int = ORACLE_PRIME) -> Dict[str, Any]:
    special_cases = [
        (0, -2, -1),
        (1, -2, -1),
        (2, -3, 0),
        (3, -4, 2),
    ]
    special_results = {}
    for order, lam_num, y_exp in special_cases:
        target_exp = -1 - y_exp
        fast = fm.special_derivative_dict_mod(order, lam_num, max(0, target_exp), p).get(target_exp, 0)
        brute = special_coeff_from_sympy(order, lam_num, y_exp, p)
        special_results[str((order, lam_num, y_exp))] = {
            "fast": fast,
            "brute": brute,
            "matches": fast == brute,
        }

    transition_cases = [
        (3, (0, 0, 0, 0), 0, ROOT_POWERS),
        (3, (0, 0, 0, 1), 2, ROOT_POWERS),
        (2, (0, 0, 0, 0), 0, (2, 2, 4, 0, 2, 4, 0, 4, 0, 0)),
        (2, (0, 0, 0, 0), 0, (2, 2, 4, 0, 2, 5, 0, 5, 0, 0)),
    ]
    transition_results = {}
    for var_idx, deriv_orders, y_exp, denom_powers in transition_cases:
        fast = fm.variable_transition_mod(var_idx, deriv_orders, y_exp, denom_powers, p)
        brute = brute_variable_transition_mod(var_idx, deriv_orders, y_exp, denom_powers, p)
        transition_results[str((var_idx, deriv_orders, y_exp, denom_powers))] = {
            "fast_term_count": len(fast),
            "brute_term_count": len(brute),
            "matches": fast == brute,
        }

    residue_cases = [
        ((0, 0, 0, 0), (0, 0, 0, 0)),
        ((2, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 0, 0, 2), (0, 0, 0, 1)),
        ((4, 3, 2, 1), (1, 0, 0, 0)),
        ((5, 4, 3, 2), (0, 1, 0, 0)),
    ]
    residue_results = {}
    for alpha, deriv_orders in residue_cases:
        fast = fm.residue_monomial_mod(alpha, deriv_orders, p)
        brute = slow_residue_monomial_mod(alpha, deriv_orders, p)
        residue_results[str((alpha, deriv_orders))] = {
            "fast": fast,
            "brute": brute,
            "matches": fast == brute,
        }

    required = {
        "special_coefficients_match_sympy_laurent_series": all(
            item["matches"] for item in special_results.values()
        ),
        "variable_transitions_match_sympy_binomial_oracle": all(
            item["matches"] for item in transition_results.values()
        ),
        "composed_monomial_residues_match_slow_oracle": all(
            item["matches"] for item in residue_results.values()
        ),
    }
    return {
        "runner": "jk_only_residue_oracle",
        "status": "passed" if all(required.values()) else "failed",
        "prime": p,
        "required": required,
        "special_results": special_results,
        "transition_results": transition_results,
        "residue_results": residue_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", type=int, default=ORACLE_PRIME)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    started = time.time()
    payload = run_oracle(args.prime)
    payload["elapsed_seconds"] = time.time() - started
    ready = json_ready(payload)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(ready, handle, indent=2, sort_keys=True)
    print(json.dumps(ready, indent=2, sort_keys=True))
    if payload["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
