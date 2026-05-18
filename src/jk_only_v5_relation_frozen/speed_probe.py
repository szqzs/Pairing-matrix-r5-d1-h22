#!/usr/bin/env python
"""Lightweight speed probe for the JK-only modular pairing core."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Dict, List, Sequence

import basis
import fast_modular as fm


HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_OUTPUT = os.path.join(HERE, "speed_probe_results.json")


def parse_int_list(text: str) -> List[int]:
    out: List[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"empty component in integer list {text!r}")
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if start > end:
                raise ValueError(f"invalid descending range {part!r}")
            out.extend(range(start, end + 1))
        else:
            out.append(int(part))
    out = sorted(dict.fromkeys(out))
    if not out:
        raise ValueError(f"expected at least one integer in {text!r}")
    return out


def coarse_total_score(total: fm.InvariantExp) -> int:
    target_delta = (total.f[1], total.f[2], total.f[3])
    weighted_delta = target_delta[0] + 3 * target_delta[1] + 6 * target_delta[2]
    gamma_count = sum(total.gamma)
    weighted_a = sum((idx + 2) * int(exp) for idx, exp in enumerate(total.a))
    return 10000 * weighted_delta + 1500 * gamma_count + 80 * weighted_a + 5 * int(total.f[0])


def choose_w_indices(
    source_by_chern: Dict[int, Sequence[basis.BasisItem]],
    w_basis: Sequence[basis.BasisItem],
    chern_degrees: Sequence[int],
    count: int,
    sample_rows: int,
) -> List[int]:
    row_samples: List[basis.BasisItem] = []
    for cdegree in chern_degrees:
        row_samples.extend(list(source_by_chern.get(cdegree, ()))[:sample_rows])
    scored = []
    for idx, w_item in enumerate(w_basis):
        score = 0
        for row in row_samples:
            score += coarse_total_score(fm.add_invariant_exp(row.exp, w_item.exp))
        scored.append((score, idx))
    scored.sort()
    return [idx for _score, idx in scored[:count]]


def cache_snapshot() -> Dict[str, Any]:
    names = [
        "tau_power_mod",
        "even_kernel_terms_mod",
        "hessian_inverse_delta_mod",
        "det_ratio_delta_power_mod",
        "gamma_hat_mod",
        "b_hat_mask_mod",
        "pairing_kernel_gamma_products_mod",
        "residue_monomial_mod",
        "variable_transition_mod",
        "special_derivative_dict_mod",
        "f_factorial_scale_mod",
    ]
    out: Dict[str, Any] = {}
    for name in names:
        func = getattr(fm, name)
        info = func.cache_info()
        out[name] = {
            "hits": info.hits,
            "misses": info.misses,
            "currsize": info.currsize,
        }
    return out


def run_probe(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    chern_degrees = parse_int_list(args.chern_degrees)
    source_by_chern, _raw_counts, meta_by_chern = basis.independent_basis_by_chern(
        5,
        args.source_degree,
        chern_degrees,
    )
    w_basis, w_meta = basis.independent_invariant_basis(5, args.w_degree)
    if args.w_indices:
        w_indices = parse_int_list(args.w_indices)
    else:
        w_indices = choose_w_indices(source_by_chern, w_basis, chern_degrees, args.w_count, args.rows_per_chern)

    attempts: List[Dict[str, Any]] = []
    entry_count = 0
    nonzero_count = 0
    for cdegree in chern_degrees:
        rows = list(source_by_chern.get(cdegree, ()))[: args.rows_per_chern]
        for w_idx in w_indices:
            w_item = w_basis[w_idx]
            column_elapsed = 0.0
            column_entries = 0
            column_nonzero = 0
            for row_idx, row in enumerate(rows):
                if args.max_entries is not None and entry_count >= args.max_entries:
                    break
                total = fm.add_invariant_exp(row.exp, w_item.exp)
                t0 = time.perf_counter()
                value = fm.pairing_total_mod(total, args.prime)
                elapsed = time.perf_counter() - t0
                entry_count += 1
                column_entries += 1
                column_elapsed += elapsed
                if value:
                    nonzero_count += 1
                    column_nonzero += 1
                if args.include_entries:
                    attempts.append({
                        "chern_degree": cdegree,
                        "row_index": row_idx,
                        "row_name": row.name,
                        "w_index": w_idx,
                        "w_name": w_item.name,
                        "value_mod_p": str(value),
                        "elapsed_seconds": elapsed,
                    })
            if column_entries:
                attempts.append({
                    "chern_degree": cdegree,
                    "w_index": w_idx,
                    "w_name": w_item.name,
                    "entries": column_entries,
                    "nonzero_entries": column_nonzero,
                    "elapsed_seconds": column_elapsed,
                    "seconds_per_entry": column_elapsed / column_entries,
                })
            if args.max_entries is not None and entry_count >= args.max_entries:
                break
        if args.max_entries is not None and entry_count >= args.max_entries:
            break

    elapsed_total = time.time() - started
    requested_entries = int(args.max_entries) if args.max_entries is not None else None
    entry_count_ok = requested_entries is None or entry_count == requested_entries
    return {
        "runner": "jk_only_speed_probe",
        "status": "passed" if entry_count_ok and entry_count > 0 else "failed",
        "prime": str(args.prime),
        "parameters": {
            "source_degree": args.source_degree,
            "w_degree": args.w_degree,
            "chern_degrees": chern_degrees,
            "rows_per_chern": args.rows_per_chern,
            "w_indices": w_indices,
            "max_entries": args.max_entries,
        },
        "source_basis_dimensions_by_chern": {
            str(cdegree): len(source_by_chern.get(cdegree, ()))
            for cdegree in chern_degrees
        },
        "source_basis_meta_by_chern": meta_by_chern,
        "w_basis_dimension": len(w_basis),
        "w_basis_meta": w_meta,
        "entries_evaluated": entry_count,
        "requested_entries": requested_entries,
        "entry_count_ok": entry_count_ok,
        "nonzero_entries": nonzero_count,
        "elapsed_seconds": elapsed_total,
        "seconds_per_entry": elapsed_total / entry_count if entry_count else None,
        "cluster_recommendation": {
            "shard_mode": "task",
            "recommended_columns_per_task": [8, 16],
            "default_columns_per_task": 8,
            "reason": (
                "Task bundles amortize process startup, basis construction, and warm caches "
                "while keeping each output JSON modest enough for shared cluster filesystems."
            ),
        },
        "cache_snapshot": cache_snapshot(),
        "attempts": attempts[-args.keep_attempts :],
    }


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", type=int, default=fm.DEFAULT_PRIME)
    parser.add_argument("--source-degree", type=int, default=22)
    parser.add_argument("--w-degree", type=int, default=26)
    parser.add_argument("--chern-degrees", default="11-22")
    parser.add_argument("--rows-per-chern", type=int, default=2)
    parser.add_argument("--w-count", type=int, default=3)
    parser.add_argument("--w-indices", default="")
    parser.add_argument("--max-entries", type=int, default=48)
    parser.add_argument("--keep-attempts", type=int, default=40)
    parser.add_argument("--include-entries", action="store_true")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = run_probe(args)
    ready = json_ready(payload)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(ready, handle, indent=2, sort_keys=True)
    print(json.dumps(ready, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
