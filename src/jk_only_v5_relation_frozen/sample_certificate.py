#!/usr/bin/env python
"""Small exact sample certificate for the JK-only fast modular pairing."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import dataclass
from math import factorial
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

import sympy as sp
from sympy.ntheory.modular import crt

import fast_modular as fm
import jk_formula as jk


HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_OUTPUT = os.path.join(HERE, "sample_certificate_results.json")
SAMPLE_PRIMES = (1_000_003, 1_000_033, 1_000_037, 1_000_039, 1_000_081, 1_000_099, 1_000_117)


@dataclass(frozen=True)
class SampleCase:
    name: str
    invariant: fm.InvariantExp


def gamma_exp(label: Tuple[int, int], power: int = 1) -> Tuple[int, ...]:
    out = [0 for _ in jk.GAMMA_LABELS]
    out[jk.GAMMA_INDEX[label]] = power
    return tuple(out)


ZERO_GAMMA = tuple(0 for _ in jk.GAMMA_LABELS)
SAMPLES = (
    SampleCase("no_gamma_f2_24", fm.InvariantExp((0, 0, 0, 0), (24, 0, 0, 0), ZERO_GAMMA)),
    SampleCase("f3_squared_f2_20", fm.InvariantExp((0, 0, 0, 0), (20, 2, 0, 0), ZERO_GAMMA)),
    SampleCase("f4_squared_f2_18", fm.InvariantExp((0, 0, 0, 0), (18, 0, 2, 0), ZERO_GAMMA)),
    SampleCase("mixed_f3_f4_f2_19", fm.InvariantExp((0, 0, 0, 0), (19, 1, 1, 0), ZERO_GAMMA)),
    SampleCase("mixed_f3_f5_f2_18", fm.InvariantExp((0, 0, 0, 0), (18, 1, 0, 1), ZERO_GAMMA)),
    SampleCase("single_gamma22_f2_21", fm.InvariantExp((0, 0, 0, 0), (21, 0, 0, 0), gamma_exp((2, 2)))),
    SampleCase("double_gamma22_f2_18", fm.InvariantExp((0, 0, 0, 0), (18, 0, 0, 0), gamma_exp((2, 2), 2))),
)


def top_degree_of_case(case: fm.InvariantExp) -> int:
    total = 0
    for offset, exp in enumerate(case.a):
        rank = offset + 2
        total += int(exp) * 2 * rank
    for offset, exp in enumerate(case.f):
        rank = offset + 2
        total += int(exp) * (2 * rank - 2)
    for exp, (r, s) in zip(case.gamma, jk.GAMMA_LABELS):
        total += int(exp) * (2 * r + 2 * s - 2)
    return total


def rational_reconstruct(residue: int, modulus: int) -> sp.Rational:
    residue %= modulus
    bound = math.isqrt((modulus - 1) // 2)
    r0, r1 = modulus, residue
    t0, t1 = 0, 1
    while abs(r1) > bound:
        if r1 == 0:
            raise ValueError("rational reconstruction reached zero remainder")
        quotient = r0 // r1
        r0, r1 = r1, r0 - quotient * r1
        t0, t1 = t1, t0 - quotient * t1
    numerator, denominator = r1, t1
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    if denominator == 0:
        raise ValueError("rational reconstruction produced zero denominator")
    if abs(numerator) > bound or denominator > bound or math.gcd(numerator, denominator) != 1:
        raise ValueError("rational reconstruction bounds failed")
    if (denominator * residue - numerator) % modulus != 0:
        raise ValueError("rational reconstruction congruence failed")
    return sp.Rational(numerator, denominator)


def crt_reconstruct(primes: Sequence[int], residues: Sequence[int]) -> Tuple[int, int, sp.Rational]:
    value, modulus = crt(primes, residues)
    if value is None or modulus is None:
        raise ValueError("CRT failed")
    reconstructed = rational_reconstruct(int(value), int(modulus))
    return int(value), int(modulus), reconstructed


def fraction_to_string(value: sp.Rational) -> str:
    value = sp.Rational(value)
    if value.q == 1:
        return str(value.p)
    return f"{value.p}/{value.q}"


def value_matches_residues(value: sp.Rational, primes: Sequence[int], residues: Sequence[int]) -> bool:
    for prime, residue in zip(primes, residues):
        if value.q % prime == 0:
            return False
        reduced = int(value.p) % prime * fm.mod_inv(int(value.q), prime) % prime
        if reduced != residue % prime:
            return False
    return True


def expr_denominators(expr: sp.Expr) -> Set[int]:
    out: Set[int] = set()
    poly = sp.Poly(expr, *jk.Y)
    for _monom, coeff in poly.terms():
        denom = int(sp.Rational(coeff).q)
        if denom != 1:
            out.add(denom)
    return out


def denominator_factors(denominators: Iterable[int]) -> Dict[str, Dict[str, int]]:
    return {str(denom): {str(k): int(v) for k, v in sp.factorint(denom).items()} for denom in sorted(set(denominators))}


def collect_setup_denominators(case: fm.InvariantExp) -> Set[int]:
    target_delta = (case.f[1], case.f[2], case.f[3])
    denominators: Set[int] = set()
    denominators.update(expr_denominators(jk.a_monomial_factor(case.a)))
    for _delta, _deriv, expr in jk.even_kernel_terms(target_delta):
        denominators.update(expr_denominators(expr))
    if any(case.gamma):
        for r in range(2, 6):
            for s in range(2, 6):
                for _delta, expr in jk.hat_pair_delta(r, s, target_delta):
                    denominators.update(expr_denominators(expr))
        for mask, _coeff in fm.gamma_mask_expansion(case.gamma, SAMPLE_PRIMES[0]):
            pair_count = mask.bit_count() // 2
            if pair_count > 1:
                denominators.add(factorial(pair_count))
    return {denom for denom in denominators if denom != 1}


def run_case(sample: SampleCase, primes: Sequence[int]) -> Dict[str, Any]:
    residues = [fm.pairing_total_mod(sample.invariant, prime) for prime in primes]
    _value, modulus, reconstructed = crt_reconstruct(primes, residues)
    _prefix_value, prefix_modulus, prefix_reconstructed = crt_reconstruct(primes[:-1], residues[:-1])
    setup_denominators = collect_setup_denominators(sample.invariant)
    reconstructed_denominator = int(reconstructed.q)
    all_denominators = set(setup_denominators)
    all_denominators.add(reconstructed_denominator)
    prime_denominator_ok = all(denom % prime != 0 for denom in all_denominators for prime in primes)
    required = {
        "top_degree_is_48": top_degree_of_case(sample.invariant) == jk.TOP_DEGREE,
        "all_prime_residues_match_reconstruction": value_matches_residues(reconstructed, primes, residues),
        "prefix_reconstruction_stable_after_dropping_last_prime": prefix_reconstructed == reconstructed,
        "reconstructed_denominator_avoids_all_primes": prime_denominator_ok,
        "modulus_large_enough_for_reconstruction": modulus > 2 * max(abs(int(reconstructed.p)), reconstructed_denominator) ** 2,
        "prefix_modulus_large_enough_for_reconstruction": (
            prefix_modulus > 2 * max(abs(int(prefix_reconstructed.p)), int(prefix_reconstructed.q)) ** 2
        ),
    }
    return {
        "status": "passed" if all(required.values()) else "failed",
        "required": required,
        "degree": top_degree_of_case(sample.invariant),
        "a": sample.invariant.a,
        "f": sample.invariant.f,
        "gamma": sample.invariant.gamma,
        "target_delta": (sample.invariant.f[1], sample.invariant.f[2], sample.invariant.f[3]),
        "residues": dict(zip([str(prime) for prime in primes], residues)),
        "reconstructed_value": fraction_to_string(reconstructed),
        "prefix_reconstructed_value": fraction_to_string(prefix_reconstructed),
        "crt_modulus_bits": modulus.bit_length(),
        "prefix_crt_modulus_bits": prefix_modulus.bit_length(),
        "setup_denominator_count": len(setup_denominators),
        "setup_denominator_factors": denominator_factors(setup_denominators),
        "reconstructed_denominator_factorization": denominator_factors((reconstructed_denominator,)),
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


def run_certificate(primes: Sequence[int] = SAMPLE_PRIMES) -> Dict[str, Any]:
    prime_checks = {
        "all_primes_are_prime": all(sp.isprime(prime) for prime in primes),
        "all_primes_avoid_small_formula_denominators": all(prime > 100 and prime != 5 for prime in primes),
        "all_primes_are_distinct": len(set(primes)) == len(primes),
    }
    cases = {sample.name: run_case(sample, primes) for sample in SAMPLES}
    required = {
        **prime_checks,
        "all_sample_cases_pass": all(case["status"] == "passed" for case in cases.values()),
        "contains_f3_squared_sample": "f3_squared_f2_20" in cases,
        "contains_f4_squared_sample": "f4_squared_f2_18" in cases,
        "contains_mixed_delta_samples": {"mixed_f3_f4_f2_19", "mixed_f3_f5_f2_18"}.issubset(cases),
        "contains_single_and_double_gamma_samples": {
            "single_gamma22_f2_21",
            "double_gamma22_f2_18",
        }.issubset(cases),
    }
    return {
        "runner": "jk_only_sample_certificate",
        "status": "passed" if all(required.values()) else "failed",
        "primes": list(primes),
        "required": required,
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    started = time.time()
    payload = run_certificate()
    payload["elapsed_seconds"] = time.time() - started
    ready = json_ready(payload)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(ready, handle, indent=2, sort_keys=True)
    print(json.dumps(ready, indent=2, sort_keys=True))
    if payload["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
