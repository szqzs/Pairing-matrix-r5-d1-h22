#!/usr/bin/env python
"""JK-only modular rank search for the rank-5, genus-2 pairing.

Rows are JK-only Sp-invariant source basis elements in ordinary degree 22,
grouped by Chern degree.  Columns are the JK-only Sp-invariant W26 test basis.
Each entry is the paper-level Jeffrey-Kirwan pairing computed by
`fast_modular.pairing_total_mod` modulo a prime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import basis
import fast_modular as fm


HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_OUTPUT = os.path.join(HERE, "modular_rank_search_results.json")
COLUMN_CACHE_SCHEMA_VERSION = 4
DEFAULT_COLUMN_CACHE_DIR = os.path.join(HERE, f"modular_column_cache_v{COLUMN_CACHE_SCHEMA_VERSION}")
RECENT_ATTEMPT_LIMIT = 30
MILLER_RABIN_64_BASES = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
SOURCE_PROVENANCE_FILES = (
    "JK_THEOREM_9_6_RANK5_G2.md",
    "GAMMA_CONVENTION.md",
    "jk_formula.py",
    "fast_modular.py",
    "basis.py",
    "modular_rank_search.py",
    "cluster_rank_driver.py",
)


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


def atomic_json_dump(path: str, payload: Dict[str, Any]) -> None:
    abs_path = os.path.abspath(path)
    directory = os.path.dirname(abs_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp = f"{abs_path}.{os.getpid()}.{time.time_ns()}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(json_ready(payload), handle, indent=2, sort_keys=True)
    os.replace(tmp, abs_path)


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


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(json_ready(value), sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def source_file_hashes() -> Dict[str, str]:
    return {
        relpath: sha256_file(os.path.join(HERE, relpath))
        for relpath in SOURCE_PROVENANCE_FILES
    }


def invariant_exp_payload(exp: fm.InvariantExp) -> Dict[str, Any]:
    return {
        "a": list(exp.a),
        "f": list(exp.f),
        "gamma": list(exp.gamma),
    }


def basis_item_payload(item: basis.BasisItem) -> Dict[str, Any]:
    return {
        "name": item.name,
        "ordinary_degree": item.ordinary_degree,
        "chern_degree": item.chern_degree,
        "exp": invariant_exp_payload(item.exp),
        "vector": [
            {
                "a": list(raw_key[0]),
                "f": list(raw_key[1]),
                "b_mask": raw_key[2],
                "coeff": str(coeff),
            }
            for raw_key, coeff in item.vector
        ],
    }


def basis_digest(items: Sequence[basis.BasisItem]) -> str:
    return sha256_json([basis_item_payload(item) for item in items])


def vector_digest(vector: Sequence[int], p: int) -> str:
    return sha256_json([int(value) % p for value in vector])


def matrix_digest(matrix: Sequence[Sequence[int]], p: int) -> str:
    return sha256_json([[int(value) % p for value in row] for row in matrix])


def is_prime_64(n: int) -> bool:
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small_primes:
        if n == prime:
            return True
        if n % prime == 0:
            return False
    if n >= 1 << 64:
        raise ValueError("prime validation currently supports integers below 2^64")
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in MILLER_RABIN_64_BASES:
        if base % n == 0:
            continue
        x = pow(base, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def validate_prime(p: int) -> Dict[str, Any]:
    if p <= 100:
        raise ValueError(f"prime {p} is too small for certificate use; choose a large prime")
    if not is_prime_64(p):
        raise ValueError(f"modulus {p} is not certified prime")
    return {
        "prime": int(p),
        "prime_verified": True,
        "method": "deterministic Miller-Rabin for n < 2^64",
        "bases": list(MILLER_RABIN_64_BASES),
        "small_prime_floor": 100,
    }


def column_cache_path(cdegree: int, p: int, args: argparse.Namespace) -> str:
    return os.path.join(args.column_cache_dir, f"columns_c{cdegree}_p{p}.pkl")


def expected_cache_metadata(
    cdegree: int,
    p: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    return {
        "kind": "jk_only_modular_columns",
        "schema_version": COLUMN_CACHE_SCHEMA_VERSION,
        "prime": int(p),
        "prime_validation": validate_prime(p),
        "rank": 5,
        "chern_degree": int(cdegree),
        "source_ordinary_degree": int(args.source_degree),
        "w_ordinary_degree": int(args.w_degree),
        "source_file_sha256": source_file_hashes(),
        "source_basis_names": [item.name for item in source_basis],
        "w_basis_names": [item.name for item in w_basis],
        "source_basis_digest": basis_digest(source_basis),
        "w_basis_digest": basis_digest(w_basis),
    }


def load_column_cache(
    path: str,
    cdegree: int,
    p: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    args: argparse.Namespace,
) -> Dict[int, List[int]]:
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as handle:
        payload = pickle.load(handle)
    expected = expected_cache_metadata(cdegree, p, source_basis, w_basis, args)
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"column cache metadata mismatch for {key!r}: {path}")
    row_count = len(source_basis)
    out: Dict[int, List[int]] = {}
    for raw_key, vector in payload.get("columns", {}).items():
        w_idx = int(raw_key)
        if w_idx < 0 or w_idx >= len(w_basis):
            raise RuntimeError(f"cached column index out of range: w[{w_idx}] in {path}")
        values = [int(item) % p for item in vector]
        if len(values) != row_count:
            raise RuntimeError(f"cached column w[{w_idx}] has length {len(values)}, expected {row_count}")
        out[w_idx] = values
    return out


def save_column_cache(
    path: str,
    cdegree: int,
    p: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    args: argparse.Namespace,
    columns: Dict[int, List[int]],
) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = expected_cache_metadata(cdegree, p, source_basis, w_basis, args)
    payload["columns"] = {int(key): [int(value) % p for value in vector] for key, vector in columns.items()}
    tmp = f"{path}.{os.getpid()}.{time.time_ns()}.tmp"
    with open(tmp, "wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


def sample_row_indices(row_count: int, sample_size: int) -> List[int]:
    if row_count <= 0:
        return []
    if row_count <= sample_size:
        return list(range(row_count))
    if sample_size <= 1:
        return [0]
    return sorted({round(idx * (row_count - 1) / (sample_size - 1)) for idx in range(sample_size)})


def cheap_workload_score(total: fm.InvariantExp) -> int:
    target_delta = (total.f[1], total.f[2], total.f[3])
    weighted_delta = target_delta[0] + 3 * target_delta[1] + 6 * target_delta[2]
    gamma_count = sum(total.gamma)
    weighted_a = sum((idx + 2) * int(exp) for idx, exp in enumerate(total.a))
    return 10000 * weighted_delta + 1500 * gamma_count + 80 * weighted_a + 5 * int(total.f[0])


def cheap_column_scores(
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    args: argparse.Namespace,
) -> Tuple[List[Tuple[int, int]], Dict[str, Any]]:
    rows = sample_row_indices(len(source_basis), args.planner_sample_rows)
    scored = []
    started = time.perf_counter()
    for w_idx, w_item in enumerate(w_basis):
        score = 0
        for row_idx in rows:
            score += cheap_workload_score(fm.add_invariant_exp(source_basis[row_idx].exp, w_item.exp))
        scored.append((score, w_idx))
    scored.sort()
    return scored, {
        "sample_rows": rows,
        "elapsed_seconds": time.perf_counter() - started,
        "top_candidates": [
            {"w_index": int(w_idx), "w_name": w_basis[w_idx].name, "cheap_score": int(score)}
            for score, w_idx in scored[:25]
        ],
    }


def column_order(
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    p: int,
    args: argparse.Namespace,
) -> Tuple[List[int], Dict[str, Any]]:
    if args.column_order == "natural":
        return list(range(len(w_basis))), {"mode": "natural"}
    if args.column_order not in {"cheap", "cheap-probe", "rank-sampled"}:
        raise ValueError(f"unknown column order: {args.column_order}")

    scored, diagnostics = cheap_column_scores(source_basis, w_basis, args)
    if args.column_order == "cheap":
        diagnostics["mode"] = "cheap"
        return [w_idx for _score, w_idx in scored], diagnostics
    if args.column_order == "rank-sampled":
        return rank_sampled_column_order(source_basis, w_basis, p, args, scored, diagnostics)

    probe_rows = sample_row_indices(len(source_basis), args.probe_planner_sample_rows)
    pool = scored[: args.probe_planner_pool_size]
    rest = scored[args.probe_planner_pool_size :]
    probe_started = time.perf_counter()
    probed = []
    planner_sample_values_by_w: Dict[str, Dict[str, str]] = {}
    for cheap_score, w_idx in pool:
        sample_values = fm.pairing_totals_mod([
            fm.add_invariant_exp(source_basis[row_idx].exp, w_basis[w_idx].exp)
            for row_idx in probe_rows
        ], p)
        planner_sample_values_by_w[str(int(w_idx))] = {
            str(row_idx): str(value % p)
            for row_idx, value in zip(probe_rows, sample_values)
        }
        nonzero = sum(1 for value in sample_values if value % p)
        zero_penalty = 1 if nonzero == 0 else 0
        probed.append((
            (zero_penalty, -nonzero, cheap_score, w_idx),
            w_idx,
            {
                "w_index": int(w_idx),
                "w_name": w_basis[w_idx].name,
                "cheap_score": int(cheap_score),
                "sample_nonzero_rows": int(nonzero),
                "sample_values_mod_p": [str(value % p) for value in sample_values],
                "sample_row_values_mod_p": planner_sample_values_by_w[str(int(w_idx))],
            },
        ))
    probed.sort(key=lambda item: item[0])
    diagnostics.update({
        "mode": "cheap-probe",
        "probe_sample_rows": probe_rows,
        "probe_pool_size": len(pool),
        "probe_elapsed_seconds": time.perf_counter() - probe_started,
        "probe_top_candidates": [diag for _key, _w_idx, diag in probed[:25]],
        "planner_sample_values_by_w": planner_sample_values_by_w,
    })
    return [w_idx for _key, w_idx, _diag in probed] + [w_idx for _score, w_idx in rest], diagnostics


def unique_preserving_order(indices: Sequence[int]) -> List[int]:
    seen = set()
    out = []
    for idx in indices:
        if idx in seen:
            continue
        seen.add(idx)
        out.append(int(idx))
    return out


def rank_sampled_column_order(
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    p: int,
    args: argparse.Namespace,
    scored: Sequence[Tuple[int, int]],
    diagnostics: Dict[str, Any],
) -> Tuple[List[int], Dict[str, Any]]:
    sample_rows = sample_row_indices(len(source_basis), args.rank_planner_sample_rows)
    pool = list(scored[: args.rank_planner_pool_size])
    rest = [w_idx for _score, w_idx in scored[args.rank_planner_pool_size :]]
    pivots: Dict[int, List[int]] = {}
    selected: List[int] = []
    dependent: List[int] = []
    attempt_diags: List[Dict[str, Any]] = []
    started = time.perf_counter()
    target_sample_rank = len(sample_rows)
    probed = 0

    for cheap_score, w_idx in pool:
        values = fm.pairing_totals_mod([
            fm.add_invariant_exp(source_basis[row_idx].exp, w_basis[w_idx].exp)
            for row_idx in sample_rows
        ], p)
        pivot_row, normalized = reduce_column(values, pivots, p)
        increased = pivot_row is not None
        if increased:
            pivots[int(pivot_row)] = normalized
            selected.append(int(w_idx))
        else:
            dependent.append(int(w_idx))
        probed += 1
        attempt_diags.append({
            "w_index": int(w_idx),
            "w_name": w_basis[w_idx].name,
            "cheap_score": int(cheap_score),
            "sample_nonzero_rows": int(sum(1 for value in values if value % p)),
            "sample_row_values_mod_p": {
                str(row_idx): str(value % p)
                for row_idx, value in zip(sample_rows, values)
            },
            "increased_sample_rank": bool(increased),
            "sample_rank_after": len(selected),
            "pivot_sample_row": int(pivot_row) if pivot_row is not None else None,
        })
        if len(selected) == target_sample_rank:
            break

    unprobed_pool = [w_idx for _score, w_idx in pool[probed:]]
    order = unique_preserving_order(selected + dependent + unprobed_pool + rest)
    diagnostics.update({
        "mode": "rank-sampled",
        "rank_sample_rows": sample_rows,
        "rank_planner_pool_size": len(pool),
        "rank_planner_probed_columns": probed,
        "rank_planner_sample_rank": len(selected),
        "rank_planner_elapsed_seconds": time.perf_counter() - started,
        "rank_planner_selected_columns": [
            {"w_index": int(w_idx), "w_name": w_basis[w_idx].name}
            for w_idx in selected
        ],
        "rank_planner_attempts": attempt_diags[:50],
        "planner_sample_values_by_w": {
            str(item["w_index"]): item["sample_row_values_mod_p"]
            for item in attempt_diags
        },
    })
    return order, diagnostics


def prioritize_cached_columns(order: Sequence[int], cached_columns: Dict[int, List[int]]) -> List[int]:
    if not cached_columns:
        return list(order)
    cached = set(cached_columns)
    return [idx for idx in order if idx in cached] + [idx for idx in order if idx not in cached]


def reduce_column(
    vector: Sequence[int],
    pivots: Dict[int, List[int]],
    p: int,
) -> Tuple[Optional[int], List[int]]:
    work = [int(value) % p for value in vector]
    for pivot_row in sorted(pivots):
        coeff = work[pivot_row]
        if not coeff:
            continue
        pivot_vec = pivots[pivot_row]
        for idx, value in enumerate(pivot_vec):
            if value:
                work[idx] = (work[idx] - coeff * value) % p
    for idx, value in enumerate(work):
        if value:
            inv = fm.mod_inv(value, p)
            return idx, [(item * inv) % p for item in work]
    return None, work


def determinant_mod(matrix: Sequence[Sequence[int]], p: int) -> int:
    n = len(matrix)
    if n == 0:
        return 1
    work = [[int(value) % p for value in row] for row in matrix]
    det = 1
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if work[row][col]:
                pivot = row
                break
        if pivot is None:
            return 0
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
            det = (-det) % p
        pivot_value = work[col][col]
        det = det * pivot_value % p
        inv = fm.mod_inv(pivot_value, p)
        for row in range(col + 1, n):
            coeff = work[row][col] * inv % p
            if not coeff:
                continue
            for idx in range(col, n):
                work[row][idx] = (work[row][idx] - coeff * work[col][idx]) % p
    return det % p


def selected_minor_matrix(
    selected_rows: Sequence[int],
    selected_columns: Sequence[int],
    column_vectors: Dict[int, List[int]],
) -> List[List[int]]:
    return [
        [column_vectors[w_idx][row_idx] for w_idx in selected_columns]
        for row_idx in selected_rows
    ]


def compute_column_vector(
    source_basis: Sequence[basis.BasisItem],
    w_item: basis.BasisItem,
    p: int,
    precomputed_values: Optional[Dict[int, int]] = None,
) -> List[int]:
    precomputed = {
        int(row_idx): int(value) % p
        for row_idx, value in (precomputed_values or {}).items()
    }
    vector: List[Optional[int]] = [None for _ in source_basis]
    for row_idx, value in precomputed.items():
        if row_idx < 0 or row_idx >= len(source_basis):
            raise ValueError(f"precomputed row index out of range: {row_idx}")
        vector[row_idx] = value
    missing = [idx for idx, value in enumerate(vector) if value is None]
    missing_values = fm.pairing_totals_mod([
        fm.add_invariant_exp(source_basis[row_idx].exp, w_item.exp)
        for row_idx in missing
    ], p)
    if len(missing_values) != len(missing):
        raise RuntimeError(
            f"batched pairing length mismatch: got {len(missing_values)}, expected {len(missing)}"
        )
    for row_idx, value in zip(missing, missing_values):
        vector[row_idx] = value
    if any(value is None for value in vector):
        raise RuntimeError("column vector still has missing entries after batched evaluation")
    out = [int(value) % p for value in vector if value is not None]
    if len(out) != len(source_basis):
        raise RuntimeError(f"column vector length mismatch: got {len(out)}, expected {len(source_basis)}")
    return out


def compute_pairing_entry(
    source_item: basis.BasisItem,
    w_item: basis.BasisItem,
    p: int,
) -> int:
    return fm.pairing_total_mod(fm.add_invariant_exp(source_item.exp, w_item.exp), p)


def planner_precomputed_values(planner: Dict[str, Any], w_idx: int, p: int) -> Dict[int, int]:
    raw = planner.get("planner_sample_values_by_w", {}).get(str(int(w_idx)), {})
    return {int(row_idx): int(value) % p for row_idx, value in raw.items()}


def solve_square_mod(matrix: Sequence[Sequence[int]], rhs: Sequence[int], p: int) -> List[int]:
    n = len(matrix)
    if n == 0:
        return []
    work = [
        [int(matrix[row][col]) % p for col in range(n)] + [int(rhs[row]) % p]
        for row in range(n)
    ]
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if work[row][col]:
                pivot = row
                break
        if pivot is None:
            raise ZeroDivisionError("selected minor is singular during adaptive solve")
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
        inv = fm.mod_inv(work[col][col], p)
        work[col] = [value * inv % p for value in work[col]]
        for row in range(n):
            if row == col:
                continue
            coeff = work[row][col]
            if coeff:
                work[row] = [
                    (work[row][idx] - coeff * work[col][idx]) % p
                    for idx in range(n + 1)
                ]
    return [work[row][-1] % p for row in range(n)]


def adaptive_partial_rank_search(
    cdegree: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    p: int,
    cache_path: str,
    column_vectors: Dict[int, List[int]],
    order: Sequence[int],
    full_order: Sequence[int],
    planner: Dict[str, Any],
    args: argparse.Namespace,
    started: float,
) -> Dict[str, Any]:
    target_rank = len(source_basis)
    selected_rows: List[int] = []
    selected_columns: List[int] = []
    attempts: List[Dict[str, Any]] = []
    partial_values: Dict[int, Dict[int, int]] = {
        int(w_idx): dict(planner_precomputed_values(planner, int(w_idx), p))
        for w_idx in order
        if planner_precomputed_values(planner, int(w_idx), p)
    }
    entry_evaluations = 0
    new_columns = 0
    stop_reason = "in_progress"

    def get_value(w_idx: int, row_idx: int) -> Tuple[int, bool]:
        nonlocal entry_evaluations
        if w_idx in column_vectors:
            return column_vectors[w_idx][row_idx] % p, False
        values = partial_values.setdefault(int(w_idx), {})
        if row_idx in values:
            return values[row_idx] % p, False
        value = compute_pairing_entry(source_basis[row_idx], w_basis[w_idx], p)
        values[row_idx] = value
        entry_evaluations += 1
        return value, True

    for attempt_no, w_idx in enumerate(order, start=1):
        if args.max_seconds is not None and time.time() - started >= args.max_seconds:
            stop_reason = "max_seconds_reached"
            break
        if args.max_new_columns is not None and new_columns >= args.max_new_columns:
            stop_reason = "max_new_columns_reached"
            break
        col_started = time.perf_counter()
        w_idx = int(w_idx)
        from_cache = w_idx in column_vectors
        evaluated_before = entry_evaluations

        current_selected_values = [get_value(w_idx, row_idx)[0] for row_idx in selected_rows]
        if selected_columns:
            selected_matrix = [
                [get_value(col_idx, row_idx)[0] for col_idx in selected_columns]
                for row_idx in selected_rows
            ]
            coeffs = solve_square_mod(selected_matrix, current_selected_values, p)
        else:
            coeffs = []

        pivot_row: Optional[int] = None
        for row_idx in range(target_rank):
            if row_idx in selected_rows:
                continue
            candidate_value = get_value(w_idx, row_idx)[0]
            span_value = 0
            if selected_columns:
                selected_row_values = [
                    get_value(col_idx, row_idx)[0]
                    for col_idx in selected_columns
                ]
                span_value = sum(coeff * value for coeff, value in zip(coeffs, selected_row_values)) % p
            residual = (candidate_value - span_value) % p
            if residual:
                pivot_row = row_idx
                break

        increased = pivot_row is not None
        if increased:
            selected_rows.append(int(pivot_row))
            selected_columns.append(w_idx)
        if not from_cache:
            new_columns += 1
        elapsed = time.perf_counter() - col_started
        attempts.append({
            "attempt": attempt_no,
            "w_index": w_idx,
            "w_name": w_basis[w_idx].name,
            "rank_after": len(selected_columns),
            "increased_rank": bool(increased),
            "pivot_row": int(pivot_row) if pivot_row is not None else None,
            "pivot_row_name": source_basis[pivot_row].name if pivot_row is not None else None,
            "nonzero_entries": None,
            "elapsed_seconds": elapsed,
            "from_column_cache": bool(from_cache),
            "adaptive_partial": True,
            "evaluated_entries": entry_evaluations - evaluated_before,
        })

        if args.verbose:
            print(
                f"c={cdegree} adaptive attempt {attempt_no}: w[{w_idx}] {w_basis[w_idx].name!r} "
                f"rank={len(selected_columns)}/{target_rank} "
                f"{'pivot row ' + str(pivot_row) if increased else 'dependent'} "
                f"entries={entry_evaluations - evaluated_before} time={elapsed:.3f}s",
                flush=True,
            )

        if len(selected_columns) == target_rank:
            stop_reason = "full_rank_reached"
            break
    else:
        stop_reason = "adaptive_partial_exhausted_w_basis" if len(order) == len(full_order) else "max_columns_reached"

    for w_idx in selected_columns:
        if w_idx not in column_vectors:
            column_vectors[w_idx] = compute_column_vector(
                source_basis,
                w_basis[w_idx],
                p,
                partial_values.get(w_idx, {}),
            )

    if column_vectors:
        save_column_cache(cache_path, cdegree, p, source_basis, w_basis, args, column_vectors)

    planner["evaluation_mode"] = "adaptive-partial"
    planner["adaptive_entry_evaluations"] = entry_evaluations
    planner["adaptive_partial_value_columns"] = len(partial_values)
    result = build_chern_result(
        cdegree,
        source_basis,
        w_basis,
        p,
        cache_path,
        column_vectors,
        selected_rows,
        selected_columns,
        attempts,
        planner,
        compute_determinant=True,
        stop_reason=stop_reason,
    )
    result["adaptive_partial_mode"] = True
    result["adaptive_partial_entries_evaluated"] = entry_evaluations
    return result


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
        "pairing_total_mod",
    ]
    out: Dict[str, Any] = {}
    for name in names:
        func = getattr(fm, name)
        info = func.cache_info()
        out[name] = {"hits": info.hits, "misses": info.misses, "currsize": info.currsize}
    return out


def build_chern_result(
    cdegree: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    p: int,
    cache_path: str,
    column_vectors: Dict[int, List[int]],
    selected_rows: Sequence[int],
    selected_columns: Sequence[int],
    attempts: Sequence[Dict[str, Any]],
    planner: Dict[str, Any],
    *,
    compute_determinant: bool,
    stop_reason: str,
) -> Dict[str, Any]:
    rank = len(selected_columns)
    target_rank = len(source_basis)
    det: Optional[int] = None
    matrix: List[List[int]] = []
    if compute_determinant:
        matrix = selected_minor_matrix(selected_rows, selected_columns, column_vectors)
        det = determinant_mod(matrix, p)

    full_rank = rank == target_rank
    determinant_ok = det is not None and det % p != 0
    certificate_complete = bool(compute_determinant and (rank == 0 or determinant_ok))
    if not compute_determinant:
        certificate_status = "provisional_checkpoint"
    elif rank == 0:
        certificate_status = "zero_rank_certified"
    elif determinant_ok:
        certificate_status = "selected_minor_certified"
    else:
        certificate_status = "selected_minor_singular"
    if not compute_determinant:
        status = "checkpoint_full_rank_unverified" if full_rank else "checkpoint_pending"
    elif rank and not determinant_ok:
        status = "rank_reached_but_selected_minor_singular"
    elif full_rank:
        status = "full_rank_mod_p"
    elif stop_reason in {"exhausted_w_basis", "adaptive_partial_exhausted_w_basis"}:
        status = "exhausted_w_basis"
    elif stop_reason in {"max_columns_reached", "max_new_columns_reached", "max_seconds_reached", "missing_shards"}:
        status = stop_reason
    else:
        status = "in_progress"

    selected_column_payload = []
    for w_idx in selected_columns:
        vector = column_vectors[w_idx]
        selected_column_payload.append({
            "w_index": int(w_idx),
            "w_name": w_basis[w_idx].name,
            "column_vector_sha256": vector_digest(vector, p),
            "selected_row_values_mod_p": [
                str(vector[row_idx] % p)
                for row_idx in selected_rows
            ],
        })

    return {
        "chern_degree": int(cdegree),
        "status": status,
        "prime": str(p),
        "prime_validation": validate_prime(p),
        "source_file_sha256": source_file_hashes(),
        "source_basis_digest": basis_digest(source_basis),
        "w_basis_digest": basis_digest(w_basis),
        "target_rank": target_rank,
        "rank_mod_p": rank,
        "row_reduction_rank_lower_bound": rank,
        "certified_rank_lower_bound": rank if compute_determinant and (rank == 0 or determinant_ok) else 0,
        "full_rank_mod_p": bool(full_rank and compute_determinant and determinant_ok),
        "certificate_complete": certificate_complete,
        "certificate_status": certificate_status,
        "stop_reason": stop_reason,
        "attempted_columns": len(attempts),
        "new_columns_computed": sum(1 for item in attempts if not item["from_column_cache"]),
        "column_cache_path": cache_path,
        "column_cache_entries": len(column_vectors),
        "selected_rows": [
            {"row_index": int(row_idx), "row_name": source_basis[row_idx].name}
            for row_idx in selected_rows
        ],
        "selected_columns": [
            {"w_index": int(w_idx), "w_name": w_basis[w_idx].name}
            for w_idx in selected_columns
        ],
        "selected_column_certificates": selected_column_payload,
        "selected_minor_determinant_mod_p": str(det % p) if det is not None else None,
        "selected_minor_matrix_mod_p": [
            [str(value % p) for value in row]
            for row in matrix
        ] if compute_determinant else None,
        "selected_minor_matrix_sha256": matrix_digest(matrix, p) if compute_determinant else None,
        "nonzero_selected_minor_certifies_rank_lower_bound": (
            bool(determinant_ok) if compute_determinant and rank else None
        ),
        "nonzero_selected_minor_certifies_full_row_rank": (
            bool(full_rank and determinant_ok) if compute_determinant and rank else None
        ),
        "planner": planner,
        "recent_attempts": list(attempts[-RECENT_ATTEMPT_LIMIT:]),
        "elapsed_seconds_in_column_loop": sum(float(item["elapsed_seconds"]) for item in attempts),
    }


def trivial_zero_chern_result(
    cdegree: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    p: int,
    *,
    stop_reason: str = "no_source_rows",
) -> Dict[str, Any]:
    return {
        "chern_degree": int(cdegree),
        "status": "trivial_zero_rank",
        "prime": str(p),
        "prime_validation": validate_prime(p),
        "source_file_sha256": source_file_hashes(),
        "source_basis_digest": basis_digest(source_basis),
        "w_basis_digest": basis_digest(w_basis),
        "target_rank": 0,
        "rank_mod_p": 0,
        "row_reduction_rank_lower_bound": 0,
        "certified_rank_lower_bound": 0,
        "full_rank_mod_p": True,
        "certificate_complete": True,
        "certificate_status": "zero_rank_certified",
        "stop_reason": stop_reason,
        "attempted_columns": 0,
        "new_columns_computed": 0,
        "column_cache_path": None,
        "column_cache_entries": 0,
        "selected_rows": [],
        "selected_columns": [],
        "selected_column_certificates": [],
        "selected_minor_determinant_mod_p": "1",
        "selected_minor_matrix_mod_p": [],
        "selected_minor_matrix_sha256": matrix_digest([], p),
        "nonzero_selected_minor_certifies_rank_lower_bound": None,
        "nonzero_selected_minor_certifies_full_row_rank": None,
        "planner": {"mode": "no_source_rows"},
        "recent_attempts": [],
        "elapsed_seconds_in_column_loop": 0.0,
    }


def write_checkpoint(
    cdegree: int,
    result: Dict[str, Any],
    args: argparse.Namespace,
    started: float,
) -> None:
    if not args.checkpoint_output:
        return
    if args.checkpoint_output == "auto":
        root, ext = os.path.splitext(os.path.abspath(args.output))
        path = f"{root}.c{cdegree}.checkpoint{ext or '.json'}"
    elif "{c}" in args.checkpoint_output:
        path = os.path.abspath(args.checkpoint_output.format(c=cdegree))
    else:
        root, ext = os.path.splitext(os.path.abspath(args.checkpoint_output))
        path = f"{root}.c{cdegree}{ext or '.json'}"
    atomic_json_dump(path, {
        "runner": "jk_only_modular_rank_search_checkpoint",
        "status": result["status"],
        "certificate_status": result.get("certificate_status", "unknown"),
        "prime": str(args.prime),
        "parameters": vars(args),
        "elapsed_seconds": time.time() - started,
        "result": result,
        "cache_snapshot": cache_snapshot(),
    })


def run_one_chern(
    cdegree: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    args: argparse.Namespace,
    started: float,
) -> Dict[str, Any]:
    p = int(args.prime)
    validate_prime(p)
    target_rank = len(source_basis)
    cache_path = column_cache_path(cdegree, p, args)
    column_vectors = load_column_cache(cache_path, cdegree, p, source_basis, w_basis, args)
    full_order, planner = column_order(source_basis, w_basis, p, args)
    planner["cached_columns_loaded"] = len(column_vectors)
    if args.cache_first:
        full_order = prioritize_cached_columns(full_order, column_vectors)
        planner["cache_first"] = True
    else:
        planner["cache_first"] = False
    order = list(full_order)
    if args.max_columns is not None:
        order = order[: args.max_columns]
        planner["configured_column_count"] = len(order)
        planner["full_w_basis_column_count"] = len(full_order)

    if getattr(args, "evaluation_mode", "full-column") == "adaptive-partial":
        result = adaptive_partial_rank_search(
            cdegree,
            source_basis,
            w_basis,
            p,
            cache_path,
            column_vectors,
            order,
            full_order,
            planner,
            args,
            started,
        )
        write_checkpoint(cdegree, result, args, started)
        return result

    pivots: Dict[int, List[int]] = {}
    selected_rows: List[int] = []
    selected_columns: List[int] = []
    attempts: List[Dict[str, Any]] = []
    new_columns = 0
    stop_reason = "in_progress"

    for attempt_no, w_idx in enumerate(order, start=1):
        if args.max_seconds is not None and time.time() - started >= args.max_seconds:
            stop_reason = "max_seconds_reached"
            break
        col_started = time.perf_counter()
        from_cache = w_idx in column_vectors
        if from_cache:
            vector = column_vectors[w_idx]
        else:
            if args.max_new_columns is not None and new_columns >= args.max_new_columns:
                stop_reason = "max_new_columns_reached"
                break
            vector = compute_column_vector(
                source_basis,
                w_basis[w_idx],
                p,
                planner_precomputed_values(planner, w_idx, p),
            )
            column_vectors[w_idx] = vector
            new_columns += 1
            if args.save_column_cache_every and new_columns % args.save_column_cache_every == 0:
                save_column_cache(cache_path, cdegree, p, source_basis, w_basis, args, column_vectors)

        pivot_row, normalized = reduce_column(vector, pivots, p)
        increased = pivot_row is not None
        if increased:
            pivots[int(pivot_row)] = normalized
            selected_rows.append(int(pivot_row))
            selected_columns.append(int(w_idx))
        elapsed = time.perf_counter() - col_started
        attempts.append({
            "attempt": attempt_no,
            "w_index": int(w_idx),
            "w_name": w_basis[w_idx].name,
            "rank_after": len(selected_columns),
            "increased_rank": bool(increased),
            "pivot_row": int(pivot_row) if pivot_row is not None else None,
            "pivot_row_name": source_basis[pivot_row].name if pivot_row is not None else None,
            "nonzero_entries": sum(1 for value in vector if value % p),
            "elapsed_seconds": elapsed,
            "from_column_cache": bool(from_cache),
        })

        if args.verbose:
            print(
                f"c={cdegree} attempt {attempt_no}: w[{w_idx}] {w_basis[w_idx].name!r} "
                f"rank={len(selected_columns)}/{target_rank} "
                f"{'pivot row ' + str(pivot_row) if increased else 'dependent'} "
                f"{'cache ' if from_cache else ''}time={elapsed:.3f}s",
                flush=True,
            )

        if args.checkpoint_every and attempt_no % args.checkpoint_every == 0:
            result = build_chern_result(
                cdegree,
                source_basis,
                w_basis,
                p,
                cache_path,
                column_vectors,
                selected_rows,
                selected_columns,
                attempts,
                planner,
                compute_determinant=False,
                stop_reason="checkpoint_pending",
            )
            write_checkpoint(cdegree, result, args, started)

        if len(selected_columns) == target_rank:
            stop_reason = "full_rank_reached"
            break
    else:
        stop_reason = "exhausted_w_basis" if len(order) == len(full_order) else "max_columns_reached"

    if column_vectors:
        save_column_cache(cache_path, cdegree, p, source_basis, w_basis, args, column_vectors)

    result = build_chern_result(
        cdegree,
        source_basis,
        w_basis,
        p,
        cache_path,
        column_vectors,
        selected_rows,
        selected_columns,
        attempts,
        planner,
        compute_determinant=True,
        stop_reason=stop_reason,
    )
    write_checkpoint(cdegree, result, args, started)
    return result


def run_search(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    prime_validation = validate_prime(int(args.prime))
    chern_degrees = parse_int_list(args.chern_degrees)
    source_by_chern, raw_counts, meta_by_chern = basis.independent_basis_by_chern(
        5,
        args.source_degree,
        chern_degrees,
    )
    w_basis, w_meta = basis.independent_invariant_basis(5, args.w_degree)
    results = []
    for cdegree in chern_degrees:
        if cdegree not in source_by_chern:
            results.append(trivial_zero_chern_result(cdegree, (), w_basis, int(args.prime)))
            continue
        result = run_one_chern(cdegree, source_by_chern[cdegree], w_basis, args, started)
        results.append(result)
        completed_all_requested = len(results) == len(chern_degrees)
        passed_so_far = all(item["status"] in {"full_rank_mod_p", "trivial_zero_rank"} for item in results)
        payload = {
            "runner": "jk_only_modular_rank_search",
            "status": "passed" if completed_all_requested and passed_so_far else "in_progress",
            "prime": str(args.prime),
            "prime_validation": prime_validation,
            "parameters": vars(args),
            "elapsed_seconds": time.time() - started,
            "requested_chern_degrees": chern_degrees,
            "completed_chern_degrees": [int(item["chern_degree"]) for item in results],
            "missing_chern_degrees": [int(c) for c in chern_degrees if c not in {int(item["chern_degree"]) for item in results}],
            "source_file_sha256": source_file_hashes(),
            "source_basis_dimensions_by_chern": {
                str(c): len(source_by_chern.get(c, ()))
                for c in chern_degrees
            },
            "source_raw_product_counts_by_chern": raw_counts,
            "source_basis_meta_by_chern": meta_by_chern,
            "w_basis_dimension": len(w_basis),
            "w_basis_meta": w_meta,
            "results": results,
            "cache_snapshot": cache_snapshot(),
        }
        atomic_json_dump(args.output, payload)
        if args.max_seconds is not None and time.time() - started >= args.max_seconds:
            break
    completed_all_requested = len(results) == len(chern_degrees)
    passed = completed_all_requested and all(item["status"] in {"full_rank_mod_p", "trivial_zero_rank"} for item in results)
    return {
        "runner": "jk_only_modular_rank_search",
        "status": "passed" if passed else "in_progress",
        "prime": str(args.prime),
        "prime_validation": prime_validation,
        "parameters": vars(args),
        "elapsed_seconds": time.time() - started,
        "requested_chern_degrees": chern_degrees,
        "completed_chern_degrees": [int(item["chern_degree"]) for item in results],
        "missing_chern_degrees": [int(c) for c in chern_degrees if c not in {int(item["chern_degree"]) for item in results}],
        "source_file_sha256": source_file_hashes(),
        "source_basis_dimensions_by_chern": {
            str(c): len(source_by_chern.get(c, ()))
            for c in chern_degrees
        },
        "source_raw_product_counts_by_chern": raw_counts,
        "source_basis_meta_by_chern": meta_by_chern,
        "w_basis_dimension": len(w_basis),
        "w_basis_meta": w_meta,
        "results": results,
        "cache_snapshot": cache_snapshot(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", type=int, default=fm.DEFAULT_PRIME)
    parser.add_argument("--source-degree", type=int, default=22)
    parser.add_argument("--w-degree", type=int, default=26)
    parser.add_argument("--chern-degrees", default="11-22")
    parser.add_argument("--column-order", choices=["cheap", "cheap-probe", "rank-sampled", "natural"], default="cheap")
    parser.add_argument("--planner-sample-rows", type=int, default=8)
    parser.add_argument("--probe-planner-sample-rows", type=int, default=2)
    parser.add_argument("--probe-planner-pool-size", type=int, default=10)
    parser.add_argument("--rank-planner-sample-rows", type=int, default=8)
    parser.add_argument("--rank-planner-pool-size", type=int, default=80)
    parser.add_argument("--evaluation-mode", choices=["full-column", "adaptive-partial"], default="full-column")
    parser.add_argument("--max-columns", type=int, default=None)
    parser.add_argument("--max-new-columns", type=int, default=None)
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument("--column-cache-dir", default=DEFAULT_COLUMN_CACHE_DIR)
    parser.add_argument("--save-column-cache-every", type=int, default=10)
    parser.add_argument("--cache-first", dest="cache_first", action="store_true", default=True)
    parser.add_argument("--no-cache-first", dest="cache_first", action="store_false")
    parser.add_argument("--checkpoint-output", default="auto")
    parser.add_argument("--checkpoint-every", type=int, default=5)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = run_search(args)
    atomic_json_dump(args.output, payload)
    print(json.dumps(json_ready(payload), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
