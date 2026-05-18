#!/usr/bin/env python
"""Selected-minor c12 relation candidate extractor.

This script is deliberately weaker than ``strict_relation_runner.py``.  It
does not try to prove that the candidate annihilates the full W26 basis.
Instead it implements the theorem-assisted identification argument:

* external theorem: the relevant c12 relation space is a nonzero line;
* computation: a selected JK submatrix has rank 43 inside the 44-dimensional
  c12 source space;
* conclusion: the theorem-guaranteed full relation line is the selected
  one-dimensional left kernel.

The output JSON therefore calls itself a candidate/selected-minor certificate,
not a full-W annihilation certificate.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cluster_rank_driver as crd
import modular_rank_search as mrs


DEFAULT_RUN_ROOT = Path("/Users/siqingzhang/Documents/Playground/jk_v5_runs")
DEFAULT_C12_RUN = DEFAULT_RUN_ROOT / "c12_relation_20260518T023317Z" / "c12"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def atomic_json_dump(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.{time.time_ns()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(mrs.json_ready(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def parse_int_list(text: str) -> List[int]:
    return mrs.parse_int_list(text)


def signed_residue(value: int, p: int) -> int:
    value %= p
    return value - p if value > p // 2 else value


def rational_reconstruct(residue: int, modulus: int) -> Fraction:
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
    return Fraction(numerator, denominator)


def fraction_string(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def rational_reconstruction_payload(
    kernel: Sequence[int],
    source_basis: Sequence[Any],
    p: int,
) -> Dict[str, Any]:
    bound = math.isqrt((p - 1) // 2)
    coefficients: List[Dict[str, Any]] = []
    values: List[Fraction] = []
    failures: List[Dict[str, Any]] = []
    for row_idx, residue in enumerate(kernel):
        try:
            value = rational_reconstruct(int(residue), p)
            values.append(value)
            reduced = (value.numerator % p) * mrs.fm.mod_inv(value.denominator, p) % p
            coefficients.append({
                "row_index": int(row_idx),
                "row_name": source_basis[row_idx].name,
                "coefficient": fraction_string(value),
                "numerator": str(value.numerator),
                "denominator": str(value.denominator),
                "coefficient_mod_p": str(int(residue) % p),
                "residue_check_passed": reduced == int(residue) % p,
            })
        except Exception as exc:
            failures.append({
                "row_index": int(row_idx),
                "row_name": source_basis[row_idx].name,
                "coefficient_mod_p": str(int(residue) % p),
                "error": repr(exc),
            })
    if failures:
        return {
            "status": "failed",
            "method": "single_prime_rational_reconstruction",
            "prime": str(p),
            "uniqueness_bound": str(bound),
            "failure_records": failures,
            "mathematical_note": (
                "Single-prime rational reconstruction is unique only under the recorded numerator/denominator bound."
            ),
        }
    common_denominator = 1
    for value in values:
        common_denominator = math.lcm(common_denominator, value.denominator)
    integer_values = [int(value * common_denominator) for value in values]
    gcd_value = 0
    for value in integer_values:
        gcd_value = math.gcd(gcd_value, abs(value))
    if gcd_value:
        primitive_values = [value // gcd_value for value in integer_values]
        primitive_denominator_scale = common_denominator // gcd_value
    else:
        primitive_values = integer_values
        primitive_denominator_scale = common_denominator
    for coeff, primitive in zip(coefficients, primitive_values):
        coeff["primitive_integer_coefficient"] = str(primitive)
    return {
        "status": "passed",
        "method": "single_prime_rational_reconstruction",
        "prime": str(p),
        "uniqueness_bound": str(bound),
        "all_residue_checks_passed": all(item["residue_check_passed"] for item in coefficients),
        "common_denominator_before_primitive_gcd": str(common_denominator),
        "primitive_gcd": str(gcd_value),
        "primitive_denominator_scale": str(primitive_denominator_scale),
        "max_abs_primitive_integer_coefficient": str(max((abs(value) for value in primitive_values), default=0)),
        "nonzero_primitive_integer_coefficient_count": sum(1 for value in primitive_values if value),
        "coefficients": coefficients,
        "mathematical_note": (
            "This is the unique small rational lift of the selected-minor modular kernel under the "
            "standard rational reconstruction bound for the recorded prime.  A second-prime or exact "
            "selected-column check is still recommended before treating it as the final Q-vector."
        ),
    }


def rational_coefficients_mod(reconstruction: Dict[str, Any], p: int) -> Optional[List[int]]:
    if reconstruction.get("status") != "passed":
        return None
    out: List[int] = []
    for coeff in reconstruction.get("coefficients", []):
        numerator = int(coeff["numerator"])
        denominator = int(coeff["denominator"])
        if denominator % p == 0:
            return None
        out.append(numerator % p * mrs.fm.mod_inv(denominator, p) % p)
    return out


def kernel_payload(
    kernel: Sequence[int],
    source_basis: Sequence[Any],
    p: int,
) -> List[Dict[str, Any]]:
    return [
        {
            "row_index": int(row_idx),
            "row_name": source_basis[row_idx].name,
            "coefficient_mod_p": str(int(coeff) % p),
            "signed_representative": str(signed_residue(int(coeff), p)),
        }
        for row_idx, coeff in enumerate(kernel)
    ]


def task_sort_key(task: Dict[str, Any]) -> Tuple[int, int, int]:
    return (
        int(task.get("wave_index", 0)),
        int(task.get("column_offset", 0)),
        int(task.get("task_index", 0)),
    )


def task_w_count(task: Dict[str, Any]) -> int:
    return len([int(w_idx) for w_idx in task.get("w_indices", [])])


def load_task_records(
    *,
    manifest: Dict[str, Any],
    manifest_sha256: str,
    shard_dir: str,
    task: Dict[str, Any],
    row_count: int,
    w_basis: Sequence[Any],
    shard_mode: str,
) -> Optional[Dict[int, Dict[str, Any]]]:
    if shard_mode == "task":
        return crd.load_task_shard_bundle(
            manifest,
            manifest_sha256,
            shard_dir,
            task,
            row_count,
            w_basis,
        )
    records: Dict[int, Dict[str, Any]] = {}
    cdegree = int(task["chern_degree"])
    for raw_w_idx in task["w_indices"]:
        w_idx = int(raw_w_idx)
        record = crd.load_column_shard_record(
            manifest,
            manifest_sha256,
            shard_dir,
            cdegree,
            w_idx,
            row_count,
            w_basis[w_idx].name,
        )
        if record is None:
            return None
        record["task_index"] = int(task["task_index"])
        records[w_idx] = record
    return records


def selected_rows_payload(rows: Sequence[int], source_basis: Sequence[Any]) -> List[Dict[str, Any]]:
    return [
        {"row_index": int(row_idx), "row_name": source_basis[int(row_idx)].name}
        for row_idx in rows
    ]


def selected_columns_payload(columns: Sequence[int], w_basis: Sequence[Any]) -> List[Dict[str, Any]]:
    return [
        {"w_index": int(w_idx), "w_name": w_basis[int(w_idx)].name}
        for w_idx in columns
    ]


def column_certificate_payload(
    columns: Sequence[int],
    shard_records: Dict[int, Dict[str, Any]],
    w_basis: Sequence[Any],
) -> List[Dict[str, Any]]:
    out = []
    for w_idx in columns:
        record = shard_records[int(w_idx)]
        payload = record["payload"]
        out.append({
            "w_index": int(w_idx),
            "w_name": w_basis[int(w_idx)].name,
            "task_index": record.get("task_index"),
            "shard_path": record.get("path"),
            "shard_file_sha256": record.get("file_sha256"),
            "column_vector_sha256": payload.get("column_vector_sha256"),
        })
    return out


def find_selected_minor_candidate(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    manifest_path = Path(args.manifest).expanduser().resolve()
    shard_dir = str(Path(args.shard_dir).expanduser().resolve())
    manifest = crd.load_json(str(manifest_path))
    crd.assert_manifest_current(manifest)
    manifest_sha256 = mrs.sha256_file(str(manifest_path))
    require(manifest.get("manifest_sha256", manifest_sha256) in {manifest_sha256, None}, "manifest hash mismatch")
    p = int(manifest["prime"])
    chern_degree = int(args.chern_degree)
    require(chern_degree in [int(item) for item in manifest["chern_degrees"]], "manifest does not contain requested c-degree")
    shard_mode = crd.resolve_shard_mode(args, manifest)

    source_by_chern, _raw_counts, _meta_by_chern, w_basis, _w_meta = crd.basis_layers(
        int(manifest["source_degree"]),
        int(manifest["w_degree"]),
        [chern_degree],
    )
    source_basis = source_by_chern.get(chern_degree, ())
    source_dim = len(source_basis)
    expected_kernel_dimension = int(args.expected_kernel_dimension)
    expected_rank = source_dim - expected_kernel_dimension
    require(source_dim == int(args.expected_source_dimension), f"expected source dimension {args.expected_source_dimension}, got {source_dim}")
    require(expected_rank == int(args.expected_rank), f"expected rank {args.expected_rank}, got {expected_rank}")
    require(expected_kernel_dimension == 1, "this selected-minor extractor currently handles only kernel dimension one")

    tasks = [
        task for task in manifest.get("tasks", [])
        if int(task.get("chern_degree", -1)) == chern_degree
    ]
    tasks = sorted(tasks, key=task_sort_key)
    require(tasks, "no tasks for requested c-degree")
    all_task_indices = [int(task["task_index"]) for task in tasks]

    max_tasks = int(args.max_tasks) if args.max_tasks is not None else None
    pivots: Dict[int, List[int]] = {}
    selected_rows: List[int] = []
    selected_columns: List[int] = []
    selected_at: Optional[Dict[str, Any]] = None
    column_vectors: Dict[int, List[int]] = {}
    shard_records: Dict[int, Dict[str, Any]] = {}
    loaded_task_indices: List[int] = []
    missing_task_indices: List[int] = []
    rank_events: List[Dict[str, Any]] = []
    loaded_column_order: List[int] = []
    skipped_columns_after_rank = 0

    stop_after_rank = not bool(args.check_all_loaded)
    for task in tasks:
        task_index = int(task["task_index"])
        if max_tasks is not None and task_index >= max_tasks:
            missing_task_indices.append(task_index)
            continue
        records = load_task_records(
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            shard_dir=shard_dir,
            task=task,
            row_count=source_dim,
            w_basis=w_basis,
            shard_mode=shard_mode,
        )
        if records is None:
            missing_task_indices.append(task_index)
            if stop_after_rank and len(selected_columns) >= expected_rank:
                break
            continue
        loaded_task_indices.append(task_index)
        for raw_w_idx in task["w_indices"]:
            w_idx = int(raw_w_idx)
            record = records[w_idx]
            vector = record["vector"]
            if len(vector) != source_dim:
                raise RuntimeError(f"column w{w_idx} length mismatch")
            column_vectors[w_idx] = vector
            shard_records[w_idx] = record
            loaded_column_order.append(w_idx)
            if len(selected_columns) >= expected_rank:
                skipped_columns_after_rank += 1
                if stop_after_rank:
                    break
                continue
            pivot_row, normalized = mrs.reduce_column(vector, pivots, p)
            if pivot_row is not None:
                pivots[int(pivot_row)] = normalized
                selected_rows.append(int(pivot_row))
                selected_columns.append(w_idx)
                rank_events.append({
                    "rank_after": len(selected_columns),
                    "w_index": w_idx,
                    "w_name": w_basis[w_idx].name,
                    "pivot_row": int(pivot_row),
                    "pivot_row_name": source_basis[int(pivot_row)].name,
                    "loaded_column_count_at_event": len(loaded_column_order),
                    "task_index": task_index,
                })
                if len(selected_columns) == expected_rank:
                    selected_at = {
                        "loaded_column_count": len(loaded_column_order),
                        "task_index": task_index,
                        "w_index": w_idx,
                        "w_name": w_basis[w_idx].name,
                    }
                    if stop_after_rank:
                        break
        if stop_after_rank and len(selected_columns) >= expected_rank:
            break

    status = "candidate_identified_mod_p" if len(selected_columns) == expected_rank else "insufficient_rank"
    payload: Dict[str, Any] = {
        "runner": "jk_only_theorem_assisted_c12_candidate",
        "kind": "jk_only_theorem_assisted_selected_minor_relation_candidate",
        "schema_version": 1,
        "status": status,
        "claim_type": "theorem_assisted_selected_jk_minor_identifies_relation_line",
        "chern_degree": chern_degree,
        "ordinary_source_degree": int(manifest["source_degree"]),
        "ordinary_w_degree": int(manifest["w_degree"]),
        "source_dimension": source_dim,
        "w_basis_dimension": len(w_basis),
        "expected_kernel_dimension": expected_kernel_dimension,
        "expected_rank": expected_rank,
        "rank_mod_p_from_loaded_columns": len(selected_columns),
        "prime": str(p),
        "prime_validation": manifest["prime_validation"],
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "shard_dir": shard_dir,
        "shard_mode": shard_mode,
        "shard_namespace": crd.manifest_namespace(manifest_sha256),
        "source_file_sha256": manifest["source_file_sha256"],
        "postprocessor_file_sha256": {
            Path(__file__).name: mrs.sha256_file(__file__),
        },
        "source_basis_digest": manifest["source_basis_digest_by_chern"][str(chern_degree)],
        "w_basis_digest": manifest["w_basis_digest"],
        "loaded_task_indices": loaded_task_indices,
        "loaded_task_range": crd.compressed_int_ranges(loaded_task_indices),
        "missing_or_unloaded_task_indices": sorted(set(missing_task_indices).union(
            set(all_task_indices) - set(loaded_task_indices)
        )),
        "missing_or_unloaded_task_range": crd.compressed_int_ranges(sorted(set(missing_task_indices).union(
            set(all_task_indices) - set(loaded_task_indices)
        ))),
        "loaded_column_count": len(column_vectors),
        "loaded_column_order_prefix": loaded_column_order[: min(len(loaded_column_order), int(args.record_column_order_limit))],
        "loaded_column_order_truncated": len(loaded_column_order) > int(args.record_column_order_limit),
        "selected_at": selected_at,
        "rank_events": rank_events,
        "command": " ".join(shlex.quote(part) for part in sys.argv),
        "elapsed_seconds": time.time() - started,
        "mathematical_scope_note": (
            "This artifact does not certify annihilation against the full W basis. "
            "It identifies the c12 relation line only together with an external theorem "
            "asserting existence and uniqueness of the invariant Chern-homogeneous c12 relation. "
            "The full JK left kernel is contained in the selected-column left kernel; "
            "when both are nonzero lines, they are the same line."
        ),
        "theorem_assumptions_required": [
            "The relevant c12 relation space is nonzero and one-dimensional.",
            "The relation lies in the recorded 44-dimensional Sp-invariant, Chern-homogeneous source basis.",
            "Genuine relations pair to zero under the Jeffrey-Kirwan pairing against every W26 test class.",
            "No hidden sector outside this c12 source space contributes to the relation being identified.",
        ],
    }
    if status != "candidate_identified_mod_p":
        atomic_json_dump(Path(args.output), payload)
        return payload

    selected_minor = mrs.selected_minor_matrix(selected_rows, selected_columns, column_vectors)
    selected_det = mrs.determinant_mod(selected_minor, p)
    require(selected_det % p, "selected minor unexpectedly singular")
    kernel, kernel_norm = mrs.left_kernel_vector_from_selected_minor(
        row_count=source_dim,
        selected_rows=selected_rows,
        selected_columns=selected_columns,
        column_vectors=column_vectors,
        p=p,
        normalization_row=args.normalization_row,
    )
    selected_dot_failures = []
    loaded_dot_failures = []
    for w_idx in selected_columns:
        dot = mrs.dot_mod(kernel, column_vectors[w_idx], p)
        if dot:
            selected_dot_failures.append({"w_index": int(w_idx), "w_name": w_basis[w_idx].name, "dot_mod_p": str(dot)})
    for w_idx in loaded_column_order:
        dot = mrs.dot_mod(kernel, column_vectors[w_idx], p)
        if dot:
            loaded_dot_failures.append({"w_index": int(w_idx), "w_name": w_basis[w_idx].name, "dot_mod_p": str(dot)})
            if len(loaded_dot_failures) >= int(args.max_failure_records):
                break

    selected_set = set(selected_columns)
    rational_reconstruction = rational_reconstruction_payload(kernel, source_basis, p)
    payload.update({
        "rank_mod_p_from_loaded_columns": expected_rank,
        "partial_left_kernel_dimension_mod_p": source_dim - expected_rank,
        "selected_rows": selected_rows_payload(selected_rows, source_basis),
        "selected_columns": selected_columns_payload(selected_columns, w_basis),
        "selected_shard_certificates": column_certificate_payload(selected_columns, shard_records, w_basis),
        "selected_minor_determinant_mod_p": str(selected_det % p),
        "selected_minor_matrix_sha256": mrs.matrix_digest(selected_minor, p),
        "kernel_vector_mod_p": kernel_payload(kernel, source_basis, p),
        "kernel_vector_sha256": mrs.vector_digest(kernel, p),
        "kernel_normalization": kernel_norm,
        "rational_reconstruction": rational_reconstruction,
        "primary_selected_column_check": {
            "selected_column_count": len(selected_columns),
            "zero_dot_count": len(selected_columns) - len(selected_dot_failures),
            "nonzero_dot_count": len(selected_dot_failures),
            "failure_records": selected_dot_failures,
            "passed": not selected_dot_failures,
        },
        "primary_loaded_column_check": {
            "scope": "all loaded columns if --check-all-loaded was supplied; otherwise the columns loaded before stopping at rank 43",
            "loaded_column_count": len(loaded_column_order),
            "selected_column_count": len(selected_columns),
            "nonselected_loaded_column_count": sum(1 for w_idx in loaded_column_order if w_idx not in selected_set),
            "zero_dot_count": len(loaded_column_order) - len(loaded_dot_failures),
            "nonzero_dot_count": len(loaded_dot_failures),
            "failure_records": loaded_dot_failures,
            "passed": not loaded_dot_failures,
        },
    })

    if int(args.second_prime):
        payload["second_prime_selected_minor_check"] = second_prime_selected_minor_check(
            p2=int(args.second_prime),
            source_basis=source_basis,
            w_basis=w_basis,
            selected_rows=selected_rows,
            selected_columns=selected_columns,
            normalization_row=int(kernel_norm["normalization_index"]),
            rational_reconstruction=rational_reconstruction,
        )

    atomic_json_dump(Path(args.output), payload)
    return payload


def second_prime_selected_minor_check(
    *,
    p2: int,
    source_basis: Sequence[Any],
    w_basis: Sequence[Any],
    selected_rows: Sequence[int],
    selected_columns: Sequence[int],
    normalization_row: int,
    rational_reconstruction: Dict[str, Any],
) -> Dict[str, Any]:
    started = time.time()
    prime_validation = mrs.validate_prime(p2)
    column_vectors = {
        int(w_idx): mrs.compute_column_vector(source_basis, w_basis[int(w_idx)], p2)
        for w_idx in selected_columns
    }
    matrix = mrs.selected_minor_matrix(selected_rows, selected_columns, column_vectors)
    det = mrs.determinant_mod(matrix, p2)
    result: Dict[str, Any] = {
        "prime": str(p2),
        "prime_validation": prime_validation,
        "selected_column_count": len(selected_columns),
        "selected_row_count": len(selected_rows),
        "selected_minor_determinant_mod_p": str(det % p2),
        "nonzero_selected_minor": bool(det % p2),
        "selected_minor_matrix_sha256": mrs.matrix_digest(matrix, p2),
        "elapsed_seconds": time.time() - started,
    }
    if det % p2:
        kernel, kernel_norm = mrs.left_kernel_vector_from_selected_minor(
            row_count=len(source_basis),
            selected_rows=selected_rows,
            selected_columns=selected_columns,
            column_vectors=column_vectors,
            p=p2,
            normalization_row=normalization_row,
        )
        failures = []
        for w_idx in selected_columns:
            dot = mrs.dot_mod(kernel, column_vectors[int(w_idx)], p2)
            if dot:
                failures.append({"w_index": int(w_idx), "w_name": w_basis[int(w_idx)].name, "dot_mod_p": str(dot)})
        reconstructed_mod = rational_coefficients_mod(rational_reconstruction, p2)
        reconstructed_failures = []
        reconstructed_matches_kernel = reconstructed_mod == [int(value) % p2 for value in kernel]
        if reconstructed_mod is not None:
            for w_idx in selected_columns:
                dot = mrs.dot_mod(reconstructed_mod, column_vectors[int(w_idx)], p2)
                if dot:
                    reconstructed_failures.append({
                        "w_index": int(w_idx),
                        "w_name": w_basis[int(w_idx)].name,
                        "dot_mod_p": str(dot),
                    })
        result.update({
            "kernel_vector_mod_p": kernel_payload(kernel, source_basis, p2),
            "kernel_vector_sha256": mrs.vector_digest(kernel, p2),
            "kernel_normalization": kernel_norm,
            "reconstructed_rational_vector_comparison": {
                "available": reconstructed_mod is not None,
                "matches_second_prime_kernel": bool(reconstructed_matches_kernel),
                "vector_sha256_mod_second_prime": (
                    mrs.vector_digest(reconstructed_mod, p2) if reconstructed_mod is not None else None
                ),
                "second_prime_kernel_sha256": mrs.vector_digest(kernel, p2),
                "selected_column_zero_dot_count": (
                    len(selected_columns) - len(reconstructed_failures)
                    if reconstructed_mod is not None else None
                ),
                "selected_column_nonzero_dot_count": (
                    len(reconstructed_failures)
                    if reconstructed_mod is not None else None
                ),
                "failure_records": reconstructed_failures,
                "passed": bool(
                    reconstructed_mod is not None
                    and reconstructed_matches_kernel
                    and not reconstructed_failures
                ),
            },
            "selected_column_check": {
                "zero_dot_count": len(selected_columns) - len(failures),
                "nonzero_dot_count": len(failures),
                "failure_records": failures,
                "passed": not failures,
            },
            "elapsed_seconds": time.time() - started,
        })
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_C12_RUN / "manifest.json"))
    parser.add_argument("--shard-dir", default=str(DEFAULT_C12_RUN / "shards"))
    parser.add_argument("--shard-mode", choices=["auto", "column", "task"], default="auto")
    parser.add_argument("--chern-degree", type=int, default=12)
    parser.add_argument("--expected-source-dimension", type=int, default=44)
    parser.add_argument("--expected-rank", type=int, default=43)
    parser.add_argument("--expected-kernel-dimension", type=int, default=1)
    parser.add_argument("--normalization-row", type=int, default=None)
    parser.add_argument("--second-prime", type=int, default=0)
    parser.add_argument("--check-all-loaded", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=None, help="Ignore task indices >= this value; useful for reproducing an early partial certificate.")
    parser.add_argument("--max-failure-records", type=int, default=5)
    parser.add_argument("--record-column-order-limit", type=int, default=120)
    parser.add_argument("--output", default=str(DEFAULT_C12_RUN / "theorem_assisted_c12_candidate.json"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = find_selected_minor_candidate(args)
    print(json.dumps(mrs.json_ready({
        "status": payload.get("status"),
        "output": str(Path(args.output).expanduser().resolve()),
        "rank_mod_p_from_loaded_columns": payload.get("rank_mod_p_from_loaded_columns"),
        "loaded_column_count": payload.get("loaded_column_count"),
        "selected_column_count": len(payload.get("selected_columns", [])),
        "selected_minor_determinant_mod_p": payload.get("selected_minor_determinant_mod_p"),
        "primary_loaded_column_check_passed": (payload.get("primary_loaded_column_check") or {}).get("passed"),
        "second_prime_checked": "second_prime_selected_minor_check" in payload,
    }), indent=2, sort_keys=True))
    return 0 if payload.get("status") == "candidate_identified_mod_p" else 2


if __name__ == "__main__":
    raise SystemExit(main())
