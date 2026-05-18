#!/usr/bin/env python
"""Cluster-friendly shard tools for the JK-only modular rank search.

The three subcommands are intentionally filesystem-simple:

* manifest: build an immutable task list.
* worker: compute per-column shards or task-bundle shards for SLURM arrays.
* reduce: read completed shards and certify the rank lower bound.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import basis
import fast_modular as fm
import modular_rank_search as mrs


HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_MANIFEST = os.path.join(HERE, "cluster_manifest.json")
DEFAULT_SHARD_DIR = os.path.join(HERE, "cluster_column_shards")
DEFAULT_REDUCE_OUTPUT = os.path.join(HERE, "cluster_reduce_results.json")
MANIFEST_SCHEMA_VERSION = 3
SHARD_SCHEMA_VERSION = 3
REDUCE_SCHEMA_VERSION = 1
VERIFY_SCHEMA_VERSION = 1
RELATION_REDUCE_SCHEMA_VERSION = 1
RELATION_VERIFY_SCHEMA_VERSION = 1


def diagnostics_snapshot(started: float) -> Dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "elapsed_seconds": time.time() - started,
        "pid": os.getpid(),
        "platform": platform.platform(),
        "maxrss_kb": int(usage.ru_maxrss),
        "user_cpu_seconds": float(usage.ru_utime),
        "system_cpu_seconds": float(usage.ru_stime),
    }


def atomic_json_dump(path: str, payload: Dict[str, Any]) -> None:
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    tmp = f"{abs_path}.{os.getpid()}.{time.time_ns()}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(mrs.json_ready(payload), handle, indent=2, sort_keys=True)
    os.replace(tmp, abs_path)


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def chunks(values: Sequence[int], size: int) -> Iterable[List[int]]:
    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def manifest_namespace(manifest_sha256: str) -> str:
    return f"manifest_{manifest_sha256[:16]}"


def shard_path(shard_dir: str, cdegree: int, w_idx: int, manifest_sha256: Optional[str] = None) -> str:
    parts = [os.path.abspath(shard_dir)]
    if manifest_sha256:
        parts.append(manifest_namespace(manifest_sha256))
    parts.extend((f"c{cdegree}", f"w{w_idx}.json"))
    return os.path.join(*parts)


def task_bundle_path(shard_dir: str, task_index: int, manifest_sha256: Optional[str] = None) -> str:
    parts = [os.path.abspath(shard_dir)]
    if manifest_sha256:
        parts.append(manifest_namespace(manifest_sha256))
    parts.extend(("task_bundles", f"task{int(task_index)}.json"))
    return os.path.join(*parts)


def compressed_int_ranges(values: Sequence[int]) -> str:
    values = sorted(dict.fromkeys(int(value) for value in values))
    if not values:
        return ""
    ranges: List[str] = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = value
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(ranges)


def basis_layers(source_degree: int, w_degree: int, chern_degrees: Sequence[int]):
    source_by_chern, raw_counts, meta_by_chern = basis.independent_basis_by_chern(
        5,
        source_degree,
        chern_degrees,
    )
    w_basis, w_meta = basis.independent_invariant_basis(5, w_degree)
    return source_by_chern, raw_counts, meta_by_chern, w_basis, w_meta


def current_signature(
    source_by_chern: Dict[int, Tuple[basis.BasisItem, ...]],
    w_basis: Sequence[basis.BasisItem],
    chern_degrees: Sequence[int],
) -> Dict[str, Any]:
    return {
        "source_file_sha256": mrs.source_file_hashes(),
        "source_basis_digest_by_chern": {
            str(cdegree): mrs.basis_digest(source_by_chern.get(cdegree, ()))
            for cdegree in chern_degrees
        },
        "w_basis_digest": mrs.basis_digest(w_basis),
    }


def validate_manifest_structure(
    manifest: Dict[str, Any],
    w_basis: Sequence[basis.BasisItem],
    source_by_chern: Optional[Dict[int, Tuple[basis.BasisItem, ...]]] = None,
) -> None:
    if manifest.get("kind") != "jk_only_column_shard_manifest":
        raise RuntimeError("manifest kind mismatch")
    if int(manifest.get("schema_version", -1)) != MANIFEST_SCHEMA_VERSION:
        raise RuntimeError("manifest schema version mismatch")

    p = int(manifest.get("prime", -1))
    if manifest.get("prime_validation") != mrs.validate_prime(p):
        raise RuntimeError("manifest prime validation mismatch")

    source_degree = int(manifest.get("source_degree", -1))
    chern_degrees = [int(item) for item in manifest.get("chern_degrees", [])]
    if not chern_degrees:
        raise RuntimeError("manifest has no chern degrees")
    if len(chern_degrees) != len(set(chern_degrees)):
        raise RuntimeError("manifest chern degrees are not unique")
    for cdegree in chern_degrees:
        if cdegree < 0 or cdegree > source_degree:
            raise RuntimeError(f"manifest chern degree out of range: {cdegree}")

    columns_per_task = int(manifest.get("columns_per_task", 0))
    if columns_per_task < 1:
        raise RuntimeError("manifest columns_per_task must be positive")
    if int(manifest.get("wave_size", -1)) < 0:
        raise RuntimeError("manifest wave_size must be nonnegative")
    shard_mode = manifest.get("shard_mode")
    if shard_mode not in {"column", "task"}:
        raise RuntimeError("manifest shard_mode must be 'column' or 'task'")
    if int(manifest.get("w_basis_dimension", -1)) != len(w_basis):
        raise RuntimeError("manifest w_basis_dimension mismatch")

    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        raise RuntimeError("manifest tasks must be a list")
    if int(manifest.get("task_count", -1)) != len(tasks):
        raise RuntimeError("manifest task_count does not match tasks")

    effective_wave = {
        int(cdegree): int(size)
        for cdegree, size in manifest.get("effective_wave_size_by_chern", {}).items()
    }
    task_ids = [int(task.get("task_index", -1)) for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise RuntimeError("manifest task ids are not unique")
    if sorted(task_ids) != list(range(len(tasks))):
        raise RuntimeError("manifest task ids must be contiguous from zero")

    valid_cdegrees = set(chern_degrees)
    seen_w_by_chern: Dict[int, set[int]] = {cdegree: set() for cdegree in chern_degrees}
    running_offsets: Dict[int, int] = {cdegree: 0 for cdegree in chern_degrees}
    for task in sorted(tasks, key=lambda item: int(item["task_index"])):
        cdegree = int(task.get("chern_degree", -1))
        if cdegree not in valid_cdegrees:
            raise RuntimeError(f"task has chern degree outside manifest list: {cdegree}")
        w_indices = [int(w_idx) for w_idx in task.get("w_indices", [])]
        if not w_indices:
            raise RuntimeError(f"task {task.get('task_index')} has no w_indices")
        if len(w_indices) > columns_per_task:
            raise RuntimeError(f"task {task.get('task_index')} exceeds columns_per_task")
        if len(w_indices) != len(set(w_indices)):
            raise RuntimeError(f"task {task.get('task_index')} repeats a w_index")
        for w_idx in w_indices:
            if w_idx < 0 or w_idx >= len(w_basis):
                raise RuntimeError(f"task {task.get('task_index')} has invalid w_index {w_idx}")
            if w_idx in seen_w_by_chern[cdegree]:
                raise RuntimeError(f"chern degree {cdegree} repeats w_index {w_idx}")
            seen_w_by_chern[cdegree].add(w_idx)

        column_offset = int(task.get("column_offset", -1))
        if column_offset != running_offsets[cdegree]:
            raise RuntimeError(f"task {task.get('task_index')} has inconsistent column_offset")
        running_offsets[cdegree] += len(w_indices)

        wave_size = effective_wave.get(cdegree)
        if wave_size is None or wave_size < 1:
            raise RuntimeError(f"missing positive effective wave size for chern degree {cdegree}")
        expected_wave = column_offset // wave_size
        if int(task.get("wave_index", -1)) != expected_wave:
            raise RuntimeError(f"task {task.get('task_index')} has inconsistent wave_index")

    full_w_set = set(range(len(w_basis)))
    source_dims = {
        int(cdegree): int(dim)
        for cdegree, dim in manifest.get("source_basis_dimensions_by_chern", {}).items()
    }
    if source_by_chern is not None:
        for cdegree in chern_degrees:
            current_dim = len(source_by_chern.get(cdegree, ()))
            if source_dims.get(cdegree) != current_dim:
                raise RuntimeError(f"manifest source dimension mismatch for chern degree {cdegree}")
    for cdegree in chern_degrees:
        dim = source_dims.get(cdegree, 0)
        if dim:
            if seen_w_by_chern[cdegree] != full_w_set:
                raise RuntimeError(f"manifest does not cover the full W basis for chern degree {cdegree}")
            if running_offsets[cdegree] != len(w_basis):
                raise RuntimeError(f"manifest final column offset mismatch for chern degree {cdegree}")
        elif seen_w_by_chern[cdegree]:
            raise RuntimeError(f"manifest has tasks for zero-row chern degree {cdegree}")


def assert_manifest_current(manifest: Dict[str, Any]) -> None:
    chern_degrees = [int(item) for item in manifest["chern_degrees"]]
    source_by_chern, _raw_counts, _meta, w_basis, _w_meta = basis_layers(
        int(manifest["source_degree"]),
        int(manifest["w_degree"]),
        chern_degrees,
    )
    validate_manifest_structure(manifest, w_basis, source_by_chern)
    sig = current_signature(source_by_chern, w_basis, chern_degrees)
    for key, value in sig.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"manifest no longer matches current code/basis for {key}")


def build_manifest(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    p = int(args.prime)
    prime_validation = mrs.validate_prime(p)
    chern_degrees = mrs.parse_int_list(args.chern_degrees)
    if int(args.columns_per_task) < 1:
        raise ValueError("--columns-per-task must be at least 1")
    if int(args.wave_size) < 0:
        raise ValueError("--wave-size must be nonnegative")
    if args.shard_mode not in {"column", "task"}:
        raise ValueError("--shard-mode must be 'column' or 'task'")
    source_by_chern, raw_counts, meta_by_chern, w_basis, w_meta = basis_layers(
        args.source_degree,
        args.w_degree,
        chern_degrees,
    )

    tasks: List[Dict[str, Any]] = []
    planners: Dict[str, Any] = {}
    effective_wave_size_by_chern: Dict[str, int] = {}
    task_index = 0
    for cdegree in chern_degrees:
        source_basis = source_by_chern.get(cdegree, ())
        if not source_basis:
            planners[str(cdegree)] = {"mode": "no_source_rows"}
            continue
        order, planner = mrs.column_order(source_basis, w_basis, p, args)
        planners[str(cdegree)] = planner
        wave_size = int(args.wave_size) or len(order) or 1
        effective_wave_size_by_chern[str(cdegree)] = int(wave_size)
        for column_offset in range(0, len(order), args.columns_per_task):
            w_indices = list(order[column_offset : column_offset + args.columns_per_task])
            tasks.append({
                "task_index": int(task_index),
                "chern_degree": int(cdegree),
                "column_offset": int(column_offset),
                "wave_index": int(column_offset // wave_size),
                "w_indices": [int(w_idx) for w_idx in w_indices],
            })
            task_index += 1

    sig = current_signature(source_by_chern, w_basis, chern_degrees)
    payload = {
        "runner": "jk_only_cluster_manifest",
        "kind": "jk_only_column_shard_manifest",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "status": "manifest_created",
        "prime": str(p),
        "prime_validation": prime_validation,
        "source_degree": int(args.source_degree),
        "w_degree": int(args.w_degree),
        "chern_degrees": [int(c) for c in chern_degrees],
        "columns_per_task": int(args.columns_per_task),
        "wave_size": int(args.wave_size),
        "shard_mode": args.shard_mode,
        "effective_wave_size_by_chern": effective_wave_size_by_chern,
        "parameters": vars(args),
        "elapsed_seconds": time.time() - started,
        "source_basis_dimensions_by_chern": {
            str(c): len(source_by_chern.get(c, ()))
            for c in chern_degrees
        },
        "source_raw_product_counts_by_chern": raw_counts,
        "source_basis_meta_by_chern": meta_by_chern,
        "w_basis_dimension": len(w_basis),
        "w_basis_meta": w_meta,
        "planner_by_chern": planners,
        "task_count": len(tasks),
        "tasks": tasks,
        **sig,
    }
    atomic_json_dump(args.output, payload)
    return payload


def select_tasks(
    manifest: Dict[str, Any],
    task_spec: str,
    *,
    wave_index: Optional[int] = None,
    cdegrees: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    tasks = manifest["tasks"]
    if task_spec == "all":
        selected = list(tasks)
    else:
        wanted = set(mrs.parse_int_list(task_spec))
        available = {int(task["task_index"]) for task in tasks}
        missing = sorted(wanted - available)
        if missing:
            raise ValueError(f"task indices not in manifest: {compressed_int_ranges(missing)}")
        selected = [task for task in tasks if int(task["task_index"]) in wanted]
    if wave_index is not None:
        selected = [task for task in selected if int(task.get("wave_index", 0)) == int(wave_index)]
    if cdegrees is not None:
        wanted_c = {int(cdegree) for cdegree in cdegrees}
        selected = [task for task in selected if int(task["chern_degree"]) in wanted_c]
    if not selected:
        raise ValueError("task selection is empty")
    return selected


def resolve_worker_task_spec(args: argparse.Namespace) -> str:
    all_tasks = bool(getattr(args, "all_tasks", False))
    task_index = getattr(args, "task_index", None)
    if all_tasks and task_index:
        raise ValueError("use either --all-tasks or --task-index, not both")
    if all_tasks:
        return "all"
    if task_index is None or str(task_index).strip() == "":
        raise ValueError("worker requires --task-index, SLURM_ARRAY_TASK_ID, or explicit --all-tasks")
    return str(task_index)


def resolve_shard_mode(args: argparse.Namespace, manifest: Dict[str, Any]) -> str:
    requested = getattr(args, "shard_mode", "auto")
    manifest_mode = manifest.get("shard_mode", "task")
    if manifest_mode not in {"column", "task"}:
        raise RuntimeError("manifest shard_mode must be 'column' or 'task'")
    if requested in (None, "", "auto"):
        return str(manifest_mode)
    if requested not in {"column", "task"}:
        raise ValueError("--shard-mode must be 'auto', 'column', or 'task'")
    if requested != manifest_mode:
        raise RuntimeError(f"requested shard mode {requested!r} does not match manifest shard_mode {manifest_mode!r}")
    return str(requested)


def validate_reduce_output(
    payload: Dict[str, Any],
    expected_manifest_sha256: str,
    manifest: Dict[str, Any],
    *,
    require_certificates: bool = False,
) -> None:
    if payload.get("runner") != "jk_only_cluster_reduce":
        raise RuntimeError("reduce output runner mismatch")
    if payload.get("kind") != "jk_only_cluster_reduce_result":
        raise RuntimeError("reduce output kind mismatch")
    if int(payload.get("schema_version", -1)) != REDUCE_SCHEMA_VERSION:
        raise RuntimeError("reduce output schema version mismatch")
    if payload.get("manifest_sha256") != expected_manifest_sha256:
        raise RuntimeError("reduce output manifest hash mismatch")
    if str(payload.get("prime")) != str(manifest["prime"]):
        raise RuntimeError("reduce output prime mismatch")
    expected_namespace = manifest_namespace(expected_manifest_sha256)
    if payload.get("shard_namespace") != expected_namespace:
        raise RuntimeError("reduce output shard namespace mismatch")
    if payload.get("shard_mode") != manifest.get("shard_mode"):
        raise RuntimeError("reduce output shard mode mismatch")
    if payload.get("source_file_sha256") != manifest.get("source_file_sha256"):
        raise RuntimeError("reduce output source hash mismatch")
    if payload.get("source_basis_digest_by_chern") != manifest.get("source_basis_digest_by_chern"):
        raise RuntimeError("reduce output source basis digest mismatch")
    if payload.get("w_basis_digest") != manifest.get("w_basis_digest"):
        raise RuntimeError("reduce output W basis digest mismatch")
    if payload.get("status") not in {"passed", "in_progress"}:
        raise RuntimeError("reduce output status mismatch")

    manifest_cdegrees = [int(item) for item in manifest["chern_degrees"]]
    reduce_cdegrees = [int(item) for item in payload.get("chern_degrees", [])]
    if reduce_cdegrees != manifest_cdegrees:
        raise RuntimeError("reduce output chern degree list mismatch")
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("reduce output results must be a list")
    result_cdegrees = [int(result.get("chern_degree", -1)) for result in results]
    if sorted(result_cdegrees) != sorted(manifest_cdegrees) or len(result_cdegrees) != len(set(result_cdegrees)):
        raise RuntimeError("reduce output result cdegree coverage mismatch")

    source_dims = {
        int(cdegree): int(dim)
        for cdegree, dim in manifest.get("source_basis_dimensions_by_chern", {}).items()
    }
    for result in results:
        cdegree = int(result["chern_degree"])
        target_rank = int(result.get("target_rank", -1))
        if target_rank != source_dims.get(cdegree, 0):
            raise RuntimeError(f"reduce result target rank mismatch for c={cdegree}")
        if result.get("prime") != manifest["prime"]:
            raise RuntimeError(f"reduce result prime mismatch for c={cdegree}")
        if result.get("source_file_sha256") != manifest["source_file_sha256"]:
            raise RuntimeError(f"reduce result source hash mismatch for c={cdegree}")
        if result.get("source_basis_digest") != manifest["source_basis_digest_by_chern"][str(cdegree)]:
            raise RuntimeError(f"reduce result source basis digest mismatch for c={cdegree}")
        if result.get("w_basis_digest") != manifest["w_basis_digest"]:
            raise RuntimeError(f"reduce result W basis digest mismatch for c={cdegree}")
        if result.get("manifest_sha256") not in {None, expected_manifest_sha256}:
            raise RuntimeError(f"reduce result manifest hash mismatch for c={cdegree}")
        if result.get("shard_namespace") not in {None, expected_namespace}:
            raise RuntimeError(f"reduce result shard namespace mismatch for c={cdegree}")
        if result.get("shard_mode") not in {None, manifest.get("shard_mode")}:
            raise RuntimeError(f"reduce result shard mode mismatch for c={cdegree}")
        status = result.get("status")
        if status == "full_rank_mod_p":
            if not result.get("full_rank_mod_p"):
                raise RuntimeError(f"full-rank result lacks full_rank_mod_p for c={cdegree}")
            if not result.get("certificate_complete"):
                raise RuntimeError(f"full-rank result lacks complete certificate for c={cdegree}")
            if result.get("certificate_status") != "selected_minor_certified":
                raise RuntimeError(f"full-rank result certificate status mismatch for c={cdegree}")
            if int(result.get("certified_rank_lower_bound", -1)) != target_rank:
                raise RuntimeError(f"full-rank result lower bound mismatch for c={cdegree}")
            if not result.get("selected_minor_matrix_sha256"):
                raise RuntimeError(f"full-rank result missing minor hash for c={cdegree}")
            if int(result.get("selected_minor_determinant_mod_p", "0")) % int(manifest["prime"]) == 0:
                raise RuntimeError(f"full-rank result has zero determinant for c={cdegree}")
            if len(result.get("selected_rows", [])) != target_rank or len(result.get("selected_columns", [])) != target_rank:
                raise RuntimeError(f"full-rank result selected minor shape mismatch for c={cdegree}")
            if len(result.get("selected_shard_certificates", [])) != target_rank:
                raise RuntimeError(f"full-rank result shard certificate count mismatch for c={cdegree}")
        elif status == "trivial_zero_rank":
            if target_rank != 0 or not result.get("full_rank_mod_p"):
                raise RuntimeError(f"trivial-zero result mismatch for c={cdegree}")
        elif require_certificates:
            raise RuntimeError(f"uncertified reduce result for c={cdegree}: {status}")


def validate_verification_output(
    payload: Dict[str, Any],
    *,
    expected_manifest_sha256: str,
    expected_reduce_sha256: str,
    manifest: Dict[str, Any],
) -> None:
    if payload.get("runner") != "jk_only_cluster_verify_certificate":
        raise RuntimeError("verification output runner mismatch")
    if payload.get("kind") != "jk_only_cluster_certificate_verification":
        raise RuntimeError("verification output kind mismatch")
    if int(payload.get("schema_version", -1)) != VERIFY_SCHEMA_VERSION:
        raise RuntimeError("verification output schema version mismatch")
    if payload.get("status") != "passed":
        raise RuntimeError("verification output did not pass")
    if payload.get("manifest_sha256") != expected_manifest_sha256:
        raise RuntimeError("verification output manifest hash mismatch")
    if payload.get("reduce_output_sha256") != expected_reduce_sha256:
        raise RuntimeError("verification output reduce hash mismatch")
    if str(payload.get("prime")) != str(manifest["prime"]):
        raise RuntimeError("verification output prime mismatch")
    verifications = payload.get("verifications")
    if not isinstance(verifications, list):
        raise RuntimeError("verification output verifications must be a list")
    manifest_cdegrees = {int(item) for item in manifest["chern_degrees"]}
    verified_cdegree_list = [int(item.get("chern_degree", -1)) for item in verifications]
    verified_cdegrees = set(verified_cdegree_list)
    if len(verified_cdegree_list) != len(verified_cdegrees):
        raise RuntimeError("verification output has duplicate cdegree records")
    if verified_cdegrees != manifest_cdegrees:
        raise RuntimeError("verification output cdegree coverage mismatch")
    for item in verifications:
        cdegree = int(item["chern_degree"])
        if not item.get("passed"):
            raise RuntimeError(f"verification output has failed cdegree {cdegree}")
        second = item.get("second_prime_check")
        if payload.get("second_prime") is not None and item.get("status") == "verified_full_rank_certificate":
            if not second or not second.get("nonzero"):
                raise RuntimeError(f"verification output second-prime check failed for c={cdegree}")


def cdegrees_from_reduce(
    path: str,
    expected_manifest_sha256: str,
    manifest: Dict[str, Any],
    verification_path: str,
) -> List[int]:
    payload = load_json(path)
    validate_reduce_output(payload, expected_manifest_sha256, manifest)
    if not verification_path:
        raise RuntimeError("--previous-reduce requires a matching --previous-verification artifact")
    verification_payload = load_json(verification_path)
    validate_verification_output(
        verification_payload,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_reduce_sha256=mrs.sha256_file(path),
        manifest=manifest,
    )
    out = []
    for result in payload.get("results", []):
        if result.get("status") not in {"full_rank_mod_p", "trivial_zero_rank"}:
            out.append(int(result["chern_degree"]))
    return sorted(dict.fromkeys(out))


def plan_wave(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    if int(args.wave_index) < 0:
        raise ValueError("--wave-index must be nonnegative")
    manifest = load_json(args.manifest)
    assert_manifest_current(manifest)
    manifest_sha256 = mrs.sha256_file(args.manifest)
    if args.previous_reduce:
        cdegrees = cdegrees_from_reduce(
            args.previous_reduce,
            manifest_sha256,
            manifest,
            args.previous_verification,
        )
    elif args.chern_degrees:
        cdegrees = mrs.parse_int_list(args.chern_degrees)
    else:
        cdegrees = [int(item) for item in manifest["chern_degrees"]]
    if not cdegrees:
        payload = {
            "runner": "jk_only_cluster_wave_plan",
            "status": "no_unresolved_chern_degrees",
            "manifest": os.path.abspath(args.manifest),
            "manifest_sha256": manifest_sha256,
            "wave_index": int(args.wave_index),
            "chern_degrees": [],
            "task_count": 0,
            "task_indices": [],
            "task_index_spec": "",
            "slurm_array_hint": "",
            "elapsed_seconds": time.time() - started,
        }
        if args.output:
            atomic_json_dump(args.output, payload)
        return payload
    task_spec = "all"
    tasks = select_tasks(manifest, task_spec, wave_index=args.wave_index, cdegrees=cdegrees)
    task_indices = [int(task["task_index"]) for task in tasks]
    payload = {
        "runner": "jk_only_cluster_wave_plan",
        "status": "wave_planned",
        "manifest": os.path.abspath(args.manifest),
        "manifest_sha256": manifest_sha256,
        "wave_index": int(args.wave_index),
        "chern_degrees": cdegrees,
        "task_count": len(tasks),
        "task_indices": task_indices,
        "task_index_spec": compressed_int_ranges(task_indices),
        "slurm_array_hint": f"--array={compressed_int_ranges(task_indices)}",
        "elapsed_seconds": time.time() - started,
    }
    if args.output:
        atomic_json_dump(args.output, payload)
    return payload


def compute_worker(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    manifest = load_json(args.manifest)
    assert_manifest_current(manifest)
    p = int(manifest["prime"])
    shard_mode = resolve_shard_mode(args, manifest)
    task_spec = resolve_worker_task_spec(args)
    manifest_sha256 = mrs.sha256_file(args.manifest)
    chern_degrees = [int(item) for item in manifest["chern_degrees"]]
    source_by_chern, _raw_counts, _meta, w_basis, _w_meta = basis_layers(
        int(manifest["source_degree"]),
        int(manifest["w_degree"]),
        chern_degrees,
    )
    wave_index = getattr(args, "wave_index", None)
    if wave_index is not None and int(wave_index) < 0:
        raise ValueError("--wave-index must be nonnegative")
    selected_tasks = select_tasks(manifest, task_spec, wave_index=wave_index)
    outputs: List[Dict[str, Any]] = []

    for task in selected_tasks:
        cdegree = int(task["chern_degree"])
        source_basis = source_by_chern[cdegree]
        planner = manifest["planner_by_chern"].get(str(cdegree), {})
        if shard_mode == "task":
            path = task_bundle_path(args.shard_dir, int(task["task_index"]), manifest_sha256)
            if args.skip_existing and os.path.exists(path):
                try:
                    load_task_shard_bundle(
                        manifest,
                        manifest_sha256,
                        args.shard_dir,
                        task,
                        len(source_basis),
                        w_basis,
                    )
                except RuntimeError:
                    if not args.repair_existing:
                        raise
                else:
                    outputs.append({
                        "chern_degree": cdegree,
                        "task_index": int(task["task_index"]),
                        "w_indices": [int(w_idx) for w_idx in task["w_indices"]],
                        "path": path,
                        "status": "skipped_existing_valid",
                    })
                    continue
                outputs.append({
                    "chern_degree": cdegree,
                    "task_index": int(task["task_index"]),
                    "w_indices": [int(w_idx) for w_idx in task["w_indices"]],
                    "path": path,
                    "status": "recomputed_invalid_existing",
                })
            bundle_t0 = time.perf_counter()
            columns = []
            precomputed_entries = 0
            for w_idx in task["w_indices"]:
                w_idx = int(w_idx)
                t0 = time.perf_counter()
                precomputed = mrs.planner_precomputed_values(planner, w_idx, p)
                precomputed_entries += len(precomputed)
                vector = mrs.compute_column_vector(source_basis, w_basis[w_idx], p, precomputed)
                columns.append({
                    "w_index": w_idx,
                    "w_name": w_basis[w_idx].name,
                    "row_count": len(source_basis),
                    "nonzero_entries": sum(1 for value in vector if value % p),
                    "precomputed_entries_used": len(precomputed),
                    "column_vector_mod_p": [str(value % p) for value in vector],
                    "column_vector_sha256": mrs.vector_digest(vector, p),
                    "elapsed_seconds": time.perf_counter() - t0,
                })
            payload = {
                "runner": "jk_only_cluster_task_worker",
                "kind": "jk_only_task_shard_bundle",
                "schema_version": SHARD_SCHEMA_VERSION,
                "status": "passed",
                "manifest_path": os.path.abspath(args.manifest),
                "manifest_sha256": manifest_sha256,
                "source_file_sha256": manifest["source_file_sha256"],
                "source_basis_digest": manifest["source_basis_digest_by_chern"][str(cdegree)],
                "w_basis_digest": manifest["w_basis_digest"],
                "prime": str(p),
                "task_index": int(task["task_index"]),
                "chern_degree": cdegree,
                "column_offset": int(task["column_offset"]),
                "wave_index": int(task["wave_index"]),
                "row_count": len(source_basis),
                "w_indices": [int(w_idx) for w_idx in task["w_indices"]],
                "columns": columns,
                "column_count": len(columns),
                "entry_count": len(source_basis) * len(columns),
                "precomputed_entries_used": precomputed_entries,
                "elapsed_seconds": time.perf_counter() - bundle_t0,
                "diagnostics": diagnostics_snapshot(started),
            }
            atomic_json_dump(path, payload)
            outputs.append({
                "chern_degree": cdegree,
                "task_index": int(task["task_index"]),
                "w_indices": [int(w_idx) for w_idx in task["w_indices"]],
                "path": path,
                "status": "computed_task_bundle",
                "column_count": len(columns),
                "entry_count": len(source_basis) * len(columns),
                "precomputed_entries_used": precomputed_entries,
                "elapsed_seconds": payload["elapsed_seconds"],
            })
            continue

        for w_idx in task["w_indices"]:
            w_idx = int(w_idx)
            path = shard_path(args.shard_dir, cdegree, w_idx, manifest_sha256)
            if args.skip_existing and os.path.exists(path):
                try:
                    load_column_shard_record(
                        manifest,
                        manifest_sha256,
                        args.shard_dir,
                        cdegree,
                        w_idx,
                        len(source_basis),
                        w_basis[w_idx].name,
                    )
                except RuntimeError:
                    if not args.repair_existing:
                        raise
                else:
                    outputs.append({
                        "chern_degree": cdegree,
                        "w_index": w_idx,
                        "path": path,
                        "status": "skipped_existing_valid",
                    })
                    continue
                outputs.append({
                    "chern_degree": cdegree,
                    "w_index": w_idx,
                    "path": path,
                    "status": "recomputed_invalid_existing",
                })
            t0 = time.perf_counter()
            precomputed = mrs.planner_precomputed_values(planner, w_idx, p)
            vector = mrs.compute_column_vector(source_basis, w_basis[w_idx], p, precomputed)
            payload = {
                "runner": "jk_only_cluster_column_worker",
                "kind": "jk_only_column_shard",
                "schema_version": SHARD_SCHEMA_VERSION,
                "status": "passed",
                "manifest_path": os.path.abspath(args.manifest),
                "manifest_sha256": manifest_sha256,
                "source_file_sha256": manifest["source_file_sha256"],
                "source_basis_digest": manifest["source_basis_digest_by_chern"][str(cdegree)],
                "w_basis_digest": manifest["w_basis_digest"],
                "prime": str(p),
                "chern_degree": cdegree,
                "w_index": w_idx,
                "w_name": w_basis[w_idx].name,
                "row_count": len(source_basis),
                "nonzero_entries": sum(1 for value in vector if value % p),
                "precomputed_entries_used": len(precomputed),
                "column_vector_mod_p": [str(value % p) for value in vector],
                "column_vector_sha256": mrs.vector_digest(vector, p),
                "elapsed_seconds": time.perf_counter() - t0,
                "diagnostics": diagnostics_snapshot(started),
            }
            atomic_json_dump(path, payload)
            outputs.append({
                "chern_degree": cdegree,
                "w_index": w_idx,
                "path": path,
                "status": "computed",
                "entry_count": len(source_basis),
                "precomputed_entries_used": len(precomputed),
                "elapsed_seconds": payload["elapsed_seconds"],
            })

    result = {
        "runner": "jk_only_cluster_worker_summary",
        "status": "worker_completed",
        "manifest": os.path.abspath(args.manifest),
        "task_index": task_spec,
        "wave_index": wave_index,
        "manifest_sha256": manifest_sha256,
        "shard_dir": os.path.abspath(args.shard_dir),
        "shard_mode": shard_mode,
        "shard_namespace": manifest_namespace(manifest_sha256),
        "elapsed_seconds": time.time() - started,
        "diagnostics": diagnostics_snapshot(started),
        "cache_snapshot": mrs.cache_snapshot(),
        "outputs": outputs,
    }
    if args.output:
        atomic_json_dump(args.output, result)
    return result


def load_column_shard_record(
    manifest: Dict[str, Any],
    manifest_sha256: str,
    shard_dir: str,
    cdegree: int,
    w_idx: int,
    row_count: int,
    w_name: str,
) -> Dict[str, Any] | None:
    path = shard_path(shard_dir, cdegree, w_idx, manifest_sha256)
    if not os.path.exists(path):
        return None
    file_sha256 = mrs.sha256_file(path)
    payload = load_json(path)
    if payload.get("status") != "passed":
        raise RuntimeError(f"column shard did not pass: {path}")
    expected = {
        "kind": "jk_only_column_shard",
        "schema_version": SHARD_SCHEMA_VERSION,
        "manifest_sha256": manifest_sha256,
        "prime": manifest["prime"],
        "chern_degree": cdegree,
        "w_index": w_idx,
        "w_name": w_name,
        "row_count": row_count,
        "source_file_sha256": manifest["source_file_sha256"],
        "source_basis_digest": manifest["source_basis_digest_by_chern"][str(cdegree)],
        "w_basis_digest": manifest["w_basis_digest"],
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"column shard metadata mismatch for {key!r}: {path}")
    vector = [int(value) for value in payload["column_vector_mod_p"]]
    if len(vector) != row_count:
        raise RuntimeError(f"column shard row count mismatch: {path}")
    if mrs.vector_digest(vector, int(manifest["prime"])) != payload.get("column_vector_sha256"):
        raise RuntimeError(f"column shard vector hash mismatch: {path}")
    return {
        "path": path,
        "file_sha256": file_sha256,
        "payload": payload,
        "vector": vector,
    }


def load_task_shard_bundle(
    manifest: Dict[str, Any],
    manifest_sha256: str,
    shard_dir: str,
    task: Dict[str, Any],
    row_count: int,
    w_basis: Sequence[basis.BasisItem],
) -> Dict[int, Dict[str, Any]] | None:
    task_index = int(task["task_index"])
    cdegree = int(task["chern_degree"])
    path = task_bundle_path(shard_dir, task_index, manifest_sha256)
    if not os.path.exists(path):
        return None
    file_sha256 = mrs.sha256_file(path)
    payload = load_json(path)
    if payload.get("status") != "passed":
        raise RuntimeError(f"task shard bundle did not pass: {path}")
    expected_w_indices = [int(w_idx) for w_idx in task["w_indices"]]
    expected = {
        "kind": "jk_only_task_shard_bundle",
        "schema_version": SHARD_SCHEMA_VERSION,
        "manifest_sha256": manifest_sha256,
        "prime": manifest["prime"],
        "task_index": task_index,
        "chern_degree": cdegree,
        "column_offset": int(task["column_offset"]),
        "wave_index": int(task["wave_index"]),
        "row_count": row_count,
        "source_file_sha256": manifest["source_file_sha256"],
        "source_basis_digest": manifest["source_basis_digest_by_chern"][str(cdegree)],
        "w_basis_digest": manifest["w_basis_digest"],
        "w_indices": expected_w_indices,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"task shard bundle metadata mismatch for {key!r}: {path}")
    columns = payload.get("columns", [])
    if not isinstance(columns, list) or len(columns) != len(expected_w_indices):
        raise RuntimeError(f"task shard bundle has wrong number of columns: {path}")
    if int(payload.get("column_count", -1)) != len(expected_w_indices):
        raise RuntimeError(f"task shard bundle column_count mismatch: {path}")
    if int(payload.get("entry_count", -1)) != row_count * len(expected_w_indices):
        raise RuntimeError(f"task shard bundle entry_count mismatch: {path}")

    records: Dict[int, Dict[str, Any]] = {}
    expected_set = set(expected_w_indices)
    for column in columns:
        w_idx = int(column.get("w_index", -1))
        if w_idx not in expected_set:
            raise RuntimeError(f"task shard bundle contains unexpected w_index {w_idx}: {path}")
        if w_idx in records:
            raise RuntimeError(f"task shard bundle repeats w_index {w_idx}: {path}")
        if column.get("w_name") != w_basis[w_idx].name:
            raise RuntimeError(f"task shard bundle w_name mismatch for w_index {w_idx}: {path}")
        if int(column.get("row_count", -1)) != row_count:
            raise RuntimeError(f"task shard bundle column row_count mismatch for w_index {w_idx}: {path}")
        vector = [int(value) for value in column["column_vector_mod_p"]]
        if len(vector) != row_count:
            raise RuntimeError(f"task shard bundle row count mismatch for w_index {w_idx}: {path}")
        if mrs.vector_digest(vector, int(manifest["prime"])) != column.get("column_vector_sha256"):
            raise RuntimeError(f"task shard bundle vector hash mismatch for w_index {w_idx}: {path}")
        records[w_idx] = {
            "path": path,
            "file_sha256": file_sha256,
            "payload": column,
            "bundle_payload": payload,
            "task_index": task_index,
            "vector": vector,
        }
    if set(records) != expected_set:
        raise RuntimeError(f"task shard bundle is missing expected columns: {path}")
    return records


def reduce_shards(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    manifest = load_json(args.manifest)
    assert_manifest_current(manifest)
    p = int(manifest["prime"])
    shard_mode = resolve_shard_mode(args, manifest)
    manifest_sha256 = mrs.sha256_file(args.manifest)
    chern_degrees = [int(item) for item in manifest["chern_degrees"]]
    source_by_chern, raw_counts, meta_by_chern, w_basis, w_meta = basis_layers(
        int(manifest["source_degree"]),
        int(manifest["w_degree"]),
        chern_degrees,
    )
    order_by_chern: Dict[int, List[int]] = {cdegree: [] for cdegree in chern_degrees}
    tasks_by_chern: Dict[int, List[Dict[str, Any]]] = {cdegree: [] for cdegree in chern_degrees}
    for task in manifest["tasks"]:
        cdegree = int(task["chern_degree"])
        tasks_by_chern[cdegree].append(task)
        order_by_chern[cdegree].extend(int(w_idx) for w_idx in task["w_indices"])

    results = []
    reduction_log: List[Dict[str, Any]] = []
    for cdegree in chern_degrees:
        c_started = time.perf_counter()
        source_basis = source_by_chern.get(cdegree, ())
        if not source_basis:
            results.append({
                "chern_degree": cdegree,
                "status": "trivial_zero_rank",
                "prime": manifest["prime"],
                "prime_validation": manifest["prime_validation"],
                "source_file_sha256": manifest["source_file_sha256"],
                "source_basis_digest": manifest["source_basis_digest_by_chern"][str(cdegree)],
                "w_basis_digest": manifest["w_basis_digest"],
                "target_rank": 0,
                "rank_mod_p": 0,
                "row_reduction_rank_lower_bound": 0,
                "certified_rank_lower_bound": 0,
                "full_rank_mod_p": True,
                "certificate_complete": True,
                "certificate_status": "zero_rank_certified",
                "stop_reason": "no_source_rows",
                "selected_rows": [],
                "selected_columns": [],
                "selected_column_certificates": [],
                "selected_minor_determinant_mod_p": "1",
                "selected_minor_matrix_mod_p": [],
                "selected_minor_matrix_sha256": mrs.matrix_digest([], p),
                "manifest_sha256": manifest_sha256,
                "shard_namespace": manifest_namespace(manifest_sha256),
                "shard_mode": shard_mode,
                "selected_shard_certificates": [],
            })
            reduction_log.append({
                "chern_degree": cdegree,
                "status": "trivial_zero_rank",
                "elapsed_seconds": time.perf_counter() - c_started,
            })
            continue

        column_vectors: Dict[int, List[int]] = {}
        pivots: Dict[int, List[int]] = {}
        selected_rows: List[int] = []
        selected_columns: List[int] = []
        attempts: List[Dict[str, Any]] = []
        shard_records: Dict[int, Dict[str, Any]] = {}
        missing_columns = 0
        loaded_shard_files: Dict[str, str] = {}

        def consume_record(attempt_no: int, w_idx: int, record: Dict[str, Any]) -> bool:
            vector = record["vector"]
            shard_records[w_idx] = record
            loaded_shard_files[record["path"]] = record["file_sha256"]
            column_vectors[w_idx] = vector
            pivot_row, normalized = mrs.reduce_column(vector, pivots, p)
            increased = pivot_row is not None
            if increased:
                pivots[int(pivot_row)] = normalized
                selected_rows.append(int(pivot_row))
                selected_columns.append(int(w_idx))
            attempts.append({
                "attempt": attempt_no,
                "w_index": int(w_idx),
                "w_name": w_basis[w_idx].name,
                "rank_after": len(selected_columns),
                "increased_rank": bool(increased),
                "pivot_row": int(pivot_row) if pivot_row is not None else None,
                "pivot_row_name": source_basis[pivot_row].name if pivot_row is not None else None,
                "nonzero_entries": sum(1 for value in vector if value % p),
                "elapsed_seconds": 0.0,
                "from_column_cache": False,
                "from_cluster_shard": True,
                "shard_path": record["path"],
                "shard_sha256": record["file_sha256"],
                "task_index": record.get("task_index"),
            })
            return len(selected_columns) == len(source_basis)

        attempt_no = 0
        if shard_mode == "task":
            full_rank_reached = False
            for task in tasks_by_chern[cdegree]:
                bundle_records = load_task_shard_bundle(
                    manifest,
                    manifest_sha256,
                    args.shard_dir,
                    task,
                    len(source_basis),
                    w_basis,
                )
                if bundle_records is None:
                    missing_columns += len(task["w_indices"])
                    continue
                for w_idx in task["w_indices"]:
                    attempt_no += 1
                    w_idx = int(w_idx)
                    record = bundle_records.get(w_idx)
                    if record is None:
                        missing_columns += 1
                        continue
                    if consume_record(attempt_no, w_idx, record):
                        full_rank_reached = True
                        break
                if full_rank_reached:
                    break
        else:
            for w_idx in order_by_chern[cdegree]:
                attempt_no += 1
                record = load_column_shard_record(
                    manifest,
                    manifest_sha256,
                    args.shard_dir,
                    cdegree,
                    w_idx,
                    len(source_basis),
                    w_basis[w_idx].name,
                )
                if record is None:
                    missing_columns += 1
                    continue
                if consume_record(attempt_no, w_idx, record):
                    break

        if len(selected_columns) == len(source_basis):
            stop_reason = "full_rank_reached"
        elif missing_columns:
            stop_reason = "missing_shards"
        else:
            stop_reason = "exhausted_w_basis"
        planner = dict(manifest["planner_by_chern"].get(str(cdegree), {}))
        planner["cluster_reduce_missing_columns"] = missing_columns
        planner["cluster_reduce_loaded_columns"] = len(column_vectors)
        planner["cluster_reduce_attempted_columns"] = len(attempts)
        result = mrs.build_chern_result(
            cdegree,
            source_basis,
            w_basis,
            p,
            os.path.abspath(args.shard_dir),
            column_vectors,
            selected_rows,
            selected_columns,
            attempts,
            planner,
            compute_determinant=True,
            stop_reason=stop_reason,
        )
        result["manifest_sha256"] = manifest_sha256
        result["shard_namespace"] = manifest_namespace(manifest_sha256)
        result["shard_mode"] = shard_mode
        result["cluster_reduce_loaded_shard_count"] = len(loaded_shard_files)
        result["cluster_reduce_missing_columns"] = missing_columns
        result["all_manifest_columns_accounted_for"] = (
            missing_columns == 0 and len(column_vectors) == len(order_by_chern[cdegree])
        )
        result["selected_shard_certificates"] = [
            {
                "w_index": int(w_idx),
                "w_name": w_basis[w_idx].name,
                "shard_path": shard_records[w_idx]["path"],
                "shard_file_sha256": shard_records[w_idx]["file_sha256"],
                "column_vector_sha256": shard_records[w_idx]["payload"]["column_vector_sha256"],
                "manifest_sha256": manifest_sha256,
                "task_index": shard_records[w_idx].get("task_index"),
                "bundle_sha256": shard_records[w_idx].get("file_sha256"),
            }
            for w_idx in selected_columns
            if w_idx in shard_records
        ]
        result["publication_certificate"] = {
            "chern_degree": cdegree,
            "prime": manifest["prime"],
            "manifest_sha256": manifest_sha256,
            "source_file_sha256": manifest["source_file_sha256"],
            "source_basis_digest": manifest["source_basis_digest_by_chern"][str(cdegree)],
            "w_basis_digest": manifest["w_basis_digest"],
            "selected_rows": result["selected_rows"],
            "selected_columns": result["selected_columns"],
            "selected_minor_determinant_mod_p": result["selected_minor_determinant_mod_p"],
            "selected_minor_matrix_sha256": result["selected_minor_matrix_sha256"],
            "selected_shard_certificates": result["selected_shard_certificates"],
        }
        results.append(result)
        reduction_log.append({
            "chern_degree": cdegree,
            "status": result["status"],
            "rank_mod_p": result["rank_mod_p"],
            "target_rank": result["target_rank"],
            "loaded_columns": len(column_vectors),
            "missing_columns": missing_columns,
            "selected_columns": [int(w_idx) for w_idx in selected_columns],
            "selected_rows": [int(row_idx) for row_idx in selected_rows],
            "determinant_mod_p": result["selected_minor_determinant_mod_p"],
            "elapsed_seconds": time.perf_counter() - c_started,
        })

    passed = all(item["status"] in {"full_rank_mod_p", "trivial_zero_rank"} for item in results)
    payload = {
        "runner": "jk_only_cluster_reduce",
        "kind": "jk_only_cluster_reduce_result",
        "schema_version": REDUCE_SCHEMA_VERSION,
        "status": "passed" if passed else "in_progress",
        "manifest": os.path.abspath(args.manifest),
        "manifest_sha256": manifest_sha256,
        "manifest_file_sha256": manifest_sha256,
        "shard_dir": os.path.abspath(args.shard_dir),
        "shard_mode": shard_mode,
        "shard_namespace": manifest_namespace(manifest_sha256),
        "prime": manifest["prime"],
        "prime_validation": manifest["prime_validation"],
        "elapsed_seconds": time.time() - started,
        "diagnostics": diagnostics_snapshot(started),
        "chern_degrees": chern_degrees,
        "source_file_sha256": manifest["source_file_sha256"],
        "source_basis_digest_by_chern": manifest["source_basis_digest_by_chern"],
        "w_basis_digest": manifest["w_basis_digest"],
        "source_basis_dimensions_by_chern": {
            str(c): len(source_by_chern.get(c, ()))
            for c in chern_degrees
        },
        "source_raw_product_counts_by_chern": raw_counts,
        "source_basis_meta_by_chern": meta_by_chern,
        "w_basis_dimension": len(w_basis),
        "w_basis_meta": w_meta,
        "reduction_log": reduction_log,
        "results": results,
        "cache_snapshot": mrs.cache_snapshot(),
    }
    atomic_json_dump(args.output, payload)
    return payload


def selected_row_indices(result: Dict[str, Any]) -> List[int]:
    return [int(item["row_index"]) for item in result.get("selected_rows", [])]


def selected_column_indices(result: Dict[str, Any]) -> List[int]:
    return [int(item["w_index"]) for item in result.get("selected_columns", [])]


def recompute_selected_minor(
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    rows: Sequence[int],
    columns: Sequence[int],
    p: int,
) -> List[List[int]]:
    return [
        [
            mrs.compute_pairing_entry(source_basis[row_idx], w_basis[w_idx], p)
            for w_idx in columns
        ]
        for row_idx in rows
    ]


def load_all_manifest_columns_for_cdegree(
    manifest: Dict[str, Any],
    manifest_sha256: str,
    shard_dir: str,
    cdegree: int,
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    shard_mode: str,
) -> Tuple[List[int], Dict[int, List[int]], Dict[int, Dict[str, Any]], int, Dict[str, str]]:
    tasks = [
        task for task in manifest.get("tasks", [])
        if int(task.get("chern_degree", -1)) == int(cdegree)
    ]
    order: List[int] = []
    column_vectors: Dict[int, List[int]] = {}
    shard_records: Dict[int, Dict[str, Any]] = {}
    loaded_shard_files: Dict[str, str] = {}
    missing_columns = 0

    if shard_mode == "task":
        for task in tasks:
            w_indices = [int(w_idx) for w_idx in task["w_indices"]]
            order.extend(w_indices)
            bundle_records = load_task_shard_bundle(
                manifest,
                manifest_sha256,
                shard_dir,
                task,
                len(source_basis),
                w_basis,
            )
            if bundle_records is None:
                missing_columns += len(w_indices)
                continue
            for w_idx in w_indices:
                record = bundle_records.get(w_idx)
                if record is None:
                    missing_columns += 1
                    continue
                shard_records[w_idx] = record
                loaded_shard_files[record["path"]] = record["file_sha256"]
                column_vectors[w_idx] = record["vector"]
        return order, column_vectors, shard_records, missing_columns, loaded_shard_files

    for task in tasks:
        for raw_w_idx in task["w_indices"]:
            w_idx = int(raw_w_idx)
            order.append(w_idx)
            record = load_column_shard_record(
                manifest,
                manifest_sha256,
                shard_dir,
                cdegree,
                w_idx,
                len(source_basis),
                w_basis[w_idx].name,
            )
            if record is None:
                missing_columns += 1
                continue
            shard_records[w_idx] = record
            loaded_shard_files[record["path"]] = record["file_sha256"]
            column_vectors[w_idx] = record["vector"]
    return order, column_vectors, shard_records, missing_columns, loaded_shard_files


def kernel_vector_payload(
    vector: Sequence[int],
    source_basis: Sequence[basis.BasisItem],
    p: int,
) -> List[Dict[str, Any]]:
    return [
        {
            "row_index": int(row_idx),
            "row_name": source_basis[row_idx].name,
            "coefficient_mod_p": str(int(coeff) % p),
        }
        for row_idx, coeff in enumerate(vector)
    ]


def relation_reduce(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    manifest = load_json(args.manifest)
    assert_manifest_current(manifest)
    p = int(manifest["prime"])
    shard_mode = resolve_shard_mode(args, manifest)
    manifest_sha256 = mrs.sha256_file(args.manifest)
    manifest_cdegrees = [int(item) for item in manifest["chern_degrees"]]
    if args.chern_degrees:
        wanted = set(mrs.parse_int_list(args.chern_degrees))
        chern_degrees = [cdegree for cdegree in manifest_cdegrees if cdegree in wanted]
        if sorted(wanted) != sorted(chern_degrees):
            raise ValueError("--chern-degrees must be a subset of the manifest c-degrees")
    else:
        chern_degrees = manifest_cdegrees
    source_by_chern, raw_counts, meta_by_chern, w_basis, w_meta = basis_layers(
        int(manifest["source_degree"]),
        int(manifest["w_degree"]),
        manifest_cdegrees,
    )
    expected_kernel_dimension = int(args.expected_kernel_dimension)
    if expected_kernel_dimension < 1:
        raise ValueError("--expected-kernel-dimension must be positive for relation-reduce")

    results = []
    reduction_log: List[Dict[str, Any]] = []
    for cdegree in chern_degrees:
        c_started = time.perf_counter()
        source_basis = source_by_chern.get(cdegree, ())
        source_dim = len(source_basis)
        expected_rank = source_dim - expected_kernel_dimension
        if expected_rank < 0:
            raise ValueError(f"expected kernel dimension exceeds source dimension for c={cdegree}")

        order, column_vectors, shard_records, missing_columns, loaded_shard_files = load_all_manifest_columns_for_cdegree(
            manifest,
            manifest_sha256,
            args.shard_dir,
            cdegree,
            source_basis,
            w_basis,
            shard_mode,
        )

        pivots: Dict[int, List[int]] = {}
        selected_rows: List[int] = []
        selected_columns: List[int] = []
        attempts: List[Dict[str, Any]] = []
        for attempt_no, w_idx in enumerate(order, start=1):
            if w_idx not in column_vectors:
                attempts.append({
                    "attempt": attempt_no,
                    "w_index": int(w_idx),
                    "w_name": w_basis[w_idx].name,
                    "status": "missing_shard",
                    "rank_after": len(selected_columns),
                })
                continue
            vector = column_vectors[w_idx]
            pivot_row, normalized = mrs.reduce_column(vector, pivots, p)
            increased = pivot_row is not None
            if increased:
                pivots[int(pivot_row)] = normalized
                selected_rows.append(int(pivot_row))
                selected_columns.append(int(w_idx))
            attempts.append({
                "attempt": attempt_no,
                "w_index": int(w_idx),
                "w_name": w_basis[w_idx].name,
                "status": "loaded",
                "rank_after": len(selected_columns),
                "increased_rank": bool(increased),
                "pivot_row": int(pivot_row) if pivot_row is not None else None,
                "pivot_row_name": source_basis[pivot_row].name if pivot_row is not None else None,
                "nonzero_entries": sum(1 for value in vector if value % p),
                "from_cluster_shard": True,
                "shard_path": shard_records[w_idx]["path"] if w_idx in shard_records else None,
                "shard_sha256": shard_records[w_idx]["file_sha256"] if w_idx in shard_records else None,
                "task_index": shard_records[w_idx].get("task_index") if w_idx in shard_records else None,
            })

        rank = len(selected_columns)
        status = "relation_kernel_mod_p"
        stop_reason = "all_manifest_columns_loaded"
        kernel_vector: Optional[List[int]] = None
        kernel_norm: Optional[Dict[str, Any]] = None
        annihilation_failures: List[Dict[str, Any]] = []
        selected_minor_matrix: List[List[int]] = []
        selected_minor_det: Optional[int] = None
        if missing_columns:
            status = "missing_shards"
            stop_reason = "missing_shards"
        elif rank < expected_rank:
            status = "rank_below_expected_mod_p"
            stop_reason = "exhausted_w_basis"
        elif rank > expected_rank:
            status = "rank_above_expected_mod_p"
            stop_reason = "rank_exceeds_expected_relation_rank"
        elif source_dim != expected_rank + 1:
            status = "unsupported_kernel_dimension"
            stop_reason = "only_corank_one_relation_certificates_are_implemented"
        else:
            selected_minor_matrix = mrs.selected_minor_matrix(selected_rows, selected_columns, column_vectors)
            selected_minor_det = mrs.determinant_mod(selected_minor_matrix, p)
            if selected_minor_det % p == 0:
                status = "selected_minor_singular"
                stop_reason = "selected_minor_singular"
            else:
                kernel_vector, kernel_norm = mrs.left_kernel_vector_from_selected_minor(
                    row_count=source_dim,
                    selected_rows=selected_rows,
                    selected_columns=selected_columns,
                    column_vectors=column_vectors,
                    p=p,
                    normalization_row=args.normalization_row,
                )
                for w_idx in order:
                    if w_idx not in column_vectors:
                        continue
                    dot = mrs.dot_mod(kernel_vector, column_vectors[w_idx], p)
                    if dot:
                        annihilation_failures.append({
                            "w_index": int(w_idx),
                            "w_name": w_basis[w_idx].name,
                            "dot_mod_p": str(dot),
                        })
                        if len(annihilation_failures) >= int(args.max_failure_records):
                            break
                if annihilation_failures:
                    status = "kernel_annihilation_failed"
                    stop_reason = "kernel_annihilation_failed"

        result = {
            "chern_degree": cdegree,
            "claim_type": "jk_left_kernel_line",
            "status": status,
            "prime": manifest["prime"],
            "prime_validation": manifest["prime_validation"],
            "source_file_sha256": manifest["source_file_sha256"],
            "source_basis_digest": manifest["source_basis_digest_by_chern"][str(cdegree)],
            "w_basis_digest": manifest["w_basis_digest"],
            "source_dimension": source_dim,
            "w_basis_dimension": len(w_basis),
            "expected_kernel_dimension": expected_kernel_dimension,
            "expected_rank": expected_rank,
            "rank_mod_p": rank,
            "nullity_mod_p": source_dim - rank,
            "certified_rank_lower_bound": expected_rank if status == "relation_kernel_mod_p" else 0,
            "selected_rows": [
                {"row_index": int(row_idx), "row_name": source_basis[row_idx].name}
                for row_idx in selected_rows
            ],
            "selected_columns": [
                {"w_index": int(w_idx), "w_name": w_basis[w_idx].name}
                for w_idx in selected_columns
            ],
            "selected_minor_determinant_mod_p": str(selected_minor_det % p) if selected_minor_det is not None else None,
            "selected_minor_matrix_mod_p": [
                [str(value % p) for value in row]
                for row in selected_minor_matrix
            ] if selected_minor_matrix else None,
            "selected_minor_matrix_sha256": (
                mrs.matrix_digest(selected_minor_matrix, p) if selected_minor_matrix else None
            ),
            "nonzero_selected_minor_certifies_rank_lower_bound": bool(
                selected_minor_det is not None and selected_minor_det % p
            ),
            "kernel_vector_mod_p": (
                kernel_vector_payload(kernel_vector, source_basis, p) if kernel_vector is not None else None
            ),
            "kernel_vector_sha256": mrs.vector_digest(kernel_vector, p) if kernel_vector is not None else None,
            "kernel_normalization": kernel_norm,
            "annihilation_certificate": {
                "all_w_columns_verified": bool(status == "relation_kernel_mod_p"),
                "verified_column_count": len(column_vectors),
                "expected_w_column_count": len(w_basis),
                "zero_dot_count": len(column_vectors) if status == "relation_kernel_mod_p" else len(column_vectors) - len(annihilation_failures),
                "nonzero_dot_count": len(annihilation_failures),
                "failure_records": annihilation_failures,
            },
            "manifest_sha256": manifest_sha256,
            "shard_namespace": manifest_namespace(manifest_sha256),
            "shard_mode": shard_mode,
            "cluster_reduce_loaded_shard_count": len(loaded_shard_files),
            "cluster_reduce_missing_columns": missing_columns,
            "all_manifest_columns_accounted_for": (
                missing_columns == 0 and len(column_vectors) == len(order) == len(w_basis)
            ),
            "selected_shard_certificates": [
                {
                    "w_index": int(w_idx),
                    "w_name": w_basis[w_idx].name,
                    "shard_path": shard_records[w_idx]["path"],
                    "shard_file_sha256": shard_records[w_idx]["file_sha256"],
                    "column_vector_sha256": shard_records[w_idx]["payload"]["column_vector_sha256"],
                    "manifest_sha256": manifest_sha256,
                    "task_index": shard_records[w_idx].get("task_index"),
                    "bundle_sha256": shard_records[w_idx].get("file_sha256"),
                }
                for w_idx in selected_columns
                if w_idx in shard_records
            ],
            "stop_reason": stop_reason,
            "attempted_columns": len(attempts),
            "loaded_columns": len(column_vectors),
            "recent_attempts": attempts[-mrs.RECENT_ATTEMPT_LIMIT:],
            "elapsed_seconds": time.perf_counter() - c_started,
        }
        results.append(result)
        reduction_log.append({
            "chern_degree": cdegree,
            "status": status,
            "rank_mod_p": rank,
            "expected_rank": expected_rank,
            "nullity_mod_p": source_dim - rank,
            "loaded_columns": len(column_vectors),
            "missing_columns": missing_columns,
            "selected_columns": [int(w_idx) for w_idx in selected_columns],
            "selected_rows": [int(row_idx) for row_idx in selected_rows],
            "determinant_mod_p": result["selected_minor_determinant_mod_p"],
            "annihilation_failures": len(annihilation_failures),
            "elapsed_seconds": time.perf_counter() - c_started,
        })

    passed = all(item["status"] == "relation_kernel_mod_p" for item in results)
    failed = any(item["status"] not in {"relation_kernel_mod_p", "missing_shards"} for item in results)
    payload = {
        "runner": "jk_only_cluster_relation_reduce",
        "kind": "jk_only_cluster_relation_reduce_result",
        "schema_version": RELATION_REDUCE_SCHEMA_VERSION,
        "status": "passed" if passed else "failed" if failed else "in_progress",
        "manifest": os.path.abspath(args.manifest),
        "manifest_sha256": manifest_sha256,
        "manifest_file_sha256": manifest_sha256,
        "shard_dir": os.path.abspath(args.shard_dir),
        "shard_mode": shard_mode,
        "shard_namespace": manifest_namespace(manifest_sha256),
        "prime": manifest["prime"],
        "prime_validation": manifest["prime_validation"],
        "expected_kernel_dimension": expected_kernel_dimension,
        "elapsed_seconds": time.time() - started,
        "diagnostics": diagnostics_snapshot(started),
        "chern_degrees": chern_degrees,
        "source_file_sha256": manifest["source_file_sha256"],
        "source_basis_digest_by_chern": manifest["source_basis_digest_by_chern"],
        "w_basis_digest": manifest["w_basis_digest"],
        "source_basis_dimensions_by_chern": {
            str(c): len(source_by_chern.get(c, ()))
            for c in chern_degrees
        },
        "source_raw_product_counts_by_chern": raw_counts,
        "source_basis_meta_by_chern": meta_by_chern,
        "w_basis_dimension": len(w_basis),
        "w_basis_meta": w_meta,
        "reduction_log": reduction_log,
        "results": results,
        "cache_snapshot": mrs.cache_snapshot(),
    }
    atomic_json_dump(args.output, payload)
    return payload


def selected_kernel_vector(
    result: Dict[str, Any],
    p: int,
    source_basis: Optional[Sequence[basis.BasisItem]] = None,
) -> List[int]:
    vector_payload = result.get("kernel_vector_mod_p")
    if not isinstance(vector_payload, list):
        raise RuntimeError("relation result has no kernel_vector_mod_p")
    indexed = sorted(vector_payload, key=lambda item: int(item["row_index"]))
    if source_basis is not None and len(indexed) != len(source_basis):
        raise RuntimeError("kernel vector length does not match source dimension")
    for expected, item in enumerate(indexed):
        if int(item["row_index"]) != expected:
            raise RuntimeError("kernel vector row indices are not contiguous")
        if source_basis is not None and item.get("row_name") != source_basis[expected].name:
            raise RuntimeError("kernel vector row name mismatch")
    return [int(item["coefficient_mod_p"]) % p for item in indexed]


def kernel_vector_contract(
    result: Dict[str, Any],
    source_basis: Sequence[basis.BasisItem],
    kernel_vector: Sequence[int],
    p: int,
) -> Dict[str, Any]:
    normalization = result.get("kernel_normalization") or {}
    norm_idx_raw = normalization.get("normalization_index")
    norm_idx = int(norm_idx_raw) if norm_idx_raw is not None else None
    norm_valid = norm_idx is not None and 0 <= norm_idx < len(kernel_vector)
    vector_hash = mrs.vector_digest(kernel_vector, p)
    expected_hash = result.get("kernel_vector_sha256")
    nonzero = any(int(value) % p for value in kernel_vector)
    normalized_to_one = bool(norm_valid and int(kernel_vector[norm_idx]) % p == 1)
    passed = (
        len(kernel_vector) == len(source_basis)
        and nonzero
        and normalized_to_one
        and vector_hash == expected_hash
    )
    return {
        "length": len(kernel_vector),
        "expected_length": len(source_basis),
        "length_matches_source_dimension": len(kernel_vector) == len(source_basis),
        "nonzero": bool(nonzero),
        "normalization_index": norm_idx,
        "normalization_index_valid": bool(norm_valid),
        "normalization_coefficient_is_one": normalized_to_one,
        "kernel_vector_sha256": vector_hash,
        "expected_kernel_vector_sha256": expected_hash,
        "kernel_vector_hash_matches": vector_hash == expected_hash,
        "passed": bool(passed),
    }


def verify_kernel_annihilation_direct(
    source_basis: Sequence[basis.BasisItem],
    w_basis: Sequence[basis.BasisItem],
    kernel_vector: Sequence[int],
    p: int,
    *,
    max_failure_records: int,
) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    for w_idx, w_item in enumerate(w_basis):
        vector = mrs.compute_column_vector(source_basis, w_item, p)
        dot = mrs.dot_mod(kernel_vector, vector, p)
        if dot:
            failures.append({
                "w_index": int(w_idx),
                "w_name": w_item.name,
                "dot_mod_p": str(dot),
            })
            if len(failures) >= max_failure_records:
                break
    return {
        "all_w_columns_verified": not failures,
        "verified_column_count": len(w_basis) if not failures else None,
        "expected_w_column_count": len(w_basis),
        "zero_dot_count": len(w_basis) if not failures else None,
        "nonzero_dot_count": len(failures),
        "failure_records": failures,
    }


def verify_relation_certificate(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    manifest = load_json(args.manifest)
    assert_manifest_current(manifest)
    manifest_sha256 = mrs.sha256_file(args.manifest)
    relation_payload = load_json(args.relation_reduce_output)
    relation_sha256 = mrs.sha256_file(args.relation_reduce_output)
    if relation_payload.get("runner") != "jk_only_cluster_relation_reduce":
        raise RuntimeError("relation reduce runner mismatch")
    if relation_payload.get("kind") != "jk_only_cluster_relation_reduce_result":
        raise RuntimeError("relation reduce kind mismatch")
    if int(relation_payload.get("schema_version", -1)) != RELATION_REDUCE_SCHEMA_VERSION:
        raise RuntimeError("relation reduce schema version mismatch")
    if relation_payload.get("manifest_sha256") != manifest_sha256:
        raise RuntimeError("relation reduce manifest hash mismatch")
    if not args.allow_in_progress and relation_payload.get("status") != "passed":
        raise RuntimeError("relation verification requires a passed relation-reduce artifact")

    p = int(manifest["prime"])
    second_prime = int(args.second_prime) if int(args.second_prime) else None
    if second_prime is not None:
        mrs.validate_prime(second_prime)
        if second_prime == p:
            raise ValueError("--second-prime must differ from the primary prime")

    chern_degrees = [int(item) for item in manifest["chern_degrees"]]
    source_by_chern, _raw_counts, _meta, w_basis, _w_meta = basis_layers(
        int(manifest["source_degree"]),
        int(manifest["w_degree"]),
        chern_degrees,
    )

    relation_cdegrees = [int(item) for item in relation_payload.get("chern_degrees", [])]
    if not relation_cdegrees:
        raise RuntimeError("relation reduce artifact has no chern degrees")
    if len(relation_cdegrees) != len(set(relation_cdegrees)):
        raise RuntimeError("relation reduce artifact has duplicate cdegrees")
    if not set(relation_cdegrees).issubset(set(chern_degrees)):
        raise RuntimeError("relation reduce cdegrees are not contained in the manifest")
    relation_results = relation_payload.get("results")
    if not isinstance(relation_results, list):
        raise RuntimeError("relation reduce results must be a list")
    result_cdegrees = [int(item.get("chern_degree", -1)) for item in relation_results]
    if len(result_cdegrees) != len(set(result_cdegrees)) or sorted(result_cdegrees) != sorted(relation_cdegrees):
        raise RuntimeError("relation reduce result cdegree coverage mismatch")

    verifications = []
    for result in relation_results:
        cdegree = int(result["chern_degree"])
        source_basis = source_by_chern.get(cdegree, ())
        if result.get("status") != "relation_kernel_mod_p":
            verifications.append({
                "chern_degree": cdegree,
                "status": "skipped_uncertified_relation_result",
                "passed": bool(args.allow_in_progress),
                "result_status": result.get("status"),
            })
            continue
        rows = selected_row_indices(result)
        columns = selected_column_indices(result)
        expected_rank = len(source_basis) - 1
        structural_ok = (
            int(result.get("source_dimension", -1)) == len(source_basis)
            and int(result.get("rank_mod_p", -1)) == expected_rank
            and int(result.get("nullity_mod_p", -1)) == 1
            and len(rows) == expected_rank
            and len(columns) == expected_rank
            and int(result.get("expected_kernel_dimension", -1)) == 1
        )
        primary_matrix = recompute_selected_minor(source_basis, w_basis, rows, columns, p)
        primary_det = mrs.determinant_mod(primary_matrix, p)
        primary_sha = mrs.matrix_digest(primary_matrix, p)
        expected_det = int(result["selected_minor_determinant_mod_p"]) % p
        kernel_vector = selected_kernel_vector(result, p, source_basis)
        kernel_contract = kernel_vector_contract(result, source_basis, kernel_vector, p)
        primary_annihilation = verify_kernel_annihilation_direct(
            source_basis,
            w_basis,
            kernel_vector,
            p,
            max_failure_records=int(args.max_failure_records),
        )
        primary_ok = (
            primary_det % p == expected_det
            and primary_det % p != 0
            and primary_sha == result["selected_minor_matrix_sha256"]
            and structural_ok
            and kernel_contract["passed"]
            and primary_annihilation["all_w_columns_verified"]
        )

        second_prime_payload = None
        second_prime_ok = True
        if second_prime is not None:
            second_columns = {
                int(w_idx): mrs.compute_column_vector(source_basis, w_basis[int(w_idx)], second_prime)
                for w_idx in columns
            }
            second_matrix = mrs.selected_minor_matrix(rows, columns, second_columns)
            second_det = mrs.determinant_mod(second_matrix, second_prime)
            second_prime_ok = bool(second_det % second_prime)
            second_kernel = None
            second_norm = None
            second_annihilation = None
            if second_prime_ok:
                normalization = result.get("kernel_normalization") or {}
                normalization_row = normalization.get("normalization_index")
                second_kernel, second_norm = mrs.left_kernel_vector_from_selected_minor(
                    row_count=len(source_basis),
                    selected_rows=rows,
                    selected_columns=columns,
                    column_vectors=second_columns,
                    p=second_prime,
                    normalization_row=int(normalization_row) if normalization_row is not None else None,
                )
                second_annihilation = verify_kernel_annihilation_direct(
                    source_basis,
                    w_basis,
                    second_kernel,
                    second_prime,
                    max_failure_records=int(args.max_failure_records),
                )
                second_prime_ok = bool(second_annihilation["all_w_columns_verified"])
            second_kernel_contract = (
                kernel_vector_contract(
                    {
                        "kernel_vector_sha256": mrs.vector_digest(second_kernel, second_prime),
                        "kernel_normalization": second_norm,
                    },
                    source_basis,
                    second_kernel,
                    second_prime,
                )
                if second_kernel is not None else None
            )
            second_prime_payload = {
                "prime": str(second_prime),
                "prime_validation": mrs.validate_prime(second_prime),
                "selected_minor_determinant_mod_p": str(second_det % second_prime),
                "nonzero_selected_minor": bool(second_det % second_prime),
                "selected_minor_matrix_sha256": mrs.matrix_digest(second_matrix, second_prime),
                "kernel_vector_mod_p": (
                    kernel_vector_payload(second_kernel, source_basis, second_prime)
                    if second_kernel is not None else None
                ),
                "kernel_vector_sha256": (
                    mrs.vector_digest(second_kernel, second_prime)
                    if second_kernel is not None else None
                ),
                "kernel_normalization": second_norm,
                "kernel_vector_contract": second_kernel_contract,
                "annihilation_certificate": second_annihilation,
            }

        item_passed = primary_ok and second_prime_ok
        verifications.append({
            "chern_degree": cdegree,
            "status": (
                "verified_relation_kernel_certificate"
                if item_passed else
                "failed_second_prime_relation_certificate"
                if primary_ok and not second_prime_ok else
                "failed_relation_kernel_certificate"
            ),
            "passed": item_passed,
            "rows_recomputed": len(rows),
            "columns_recomputed_for_minor": len(columns),
            "annihilation_columns_recomputed": len(w_basis),
            "selected_rows": rows,
            "selected_columns": columns,
            "structural_contract": {
                "source_dimension": int(result.get("source_dimension", -1)),
                "expected_source_dimension": len(source_basis),
                "rank_mod_p": int(result.get("rank_mod_p", -1)),
                "expected_rank": expected_rank,
                "nullity_mod_p": int(result.get("nullity_mod_p", -1)),
                "selected_row_count": len(rows),
                "selected_column_count": len(columns),
                "passed": bool(structural_ok),
            },
            "recomputed_determinant_mod_p": str(primary_det % p),
            "expected_determinant_mod_p": str(expected_det),
            "recomputed_matrix_sha256": primary_sha,
            "expected_matrix_sha256": result["selected_minor_matrix_sha256"],
            "kernel_vector_contract": kernel_contract,
            "kernel_vector_sha256": kernel_contract["kernel_vector_sha256"],
            "expected_kernel_vector_sha256": kernel_contract["expected_kernel_vector_sha256"],
            "annihilation_certificate": primary_annihilation,
            "second_prime_check": second_prime_payload,
        })

    verified_cdegrees = [int(item.get("chern_degree", -1)) for item in verifications]
    if len(verified_cdegrees) != len(set(verified_cdegrees)) or sorted(verified_cdegrees) != sorted(relation_cdegrees):
        raise RuntimeError("relation verification cdegree coverage mismatch")
    passed = bool(verifications) and all(item["passed"] for item in verifications)
    payload = {
        "runner": "jk_only_cluster_verify_relation_certificate",
        "kind": "jk_only_cluster_relation_certificate_verification",
        "schema_version": RELATION_VERIFY_SCHEMA_VERSION,
        "status": "passed" if passed else "failed",
        "manifest": os.path.abspath(args.manifest),
        "manifest_sha256": manifest_sha256,
        "relation_reduce_output": os.path.abspath(args.relation_reduce_output),
        "relation_reduce_output_sha256": relation_sha256,
        "prime": manifest["prime"],
        "prime_validation": manifest["prime_validation"],
        "second_prime": str(second_prime) if second_prime is not None else None,
        "elapsed_seconds": time.time() - started,
        "diagnostics": diagnostics_snapshot(started),
        "verifications": verifications,
    }
    if args.output:
        atomic_json_dump(args.output, payload)
    return payload


def verify_certificate(args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    manifest = load_json(args.manifest)
    assert_manifest_current(manifest)
    manifest_sha256 = mrs.sha256_file(args.manifest)
    reduce_payload = load_json(args.reduce_output)
    validate_reduce_output(
        reduce_payload,
        manifest_sha256,
        manifest,
        require_certificates=not bool(args.allow_in_progress),
    )
    if not args.allow_in_progress and reduce_payload.get("status") != "passed":
        raise RuntimeError("verify-certificate without --allow-in-progress requires reduce status 'passed'")
    p = int(manifest["prime"])
    second_prime = int(args.second_prime) if int(args.second_prime) else None
    if second_prime is not None:
        mrs.validate_prime(second_prime)
    chern_degrees = [int(item) for item in manifest["chern_degrees"]]
    source_by_chern, _raw_counts, _meta, w_basis, _w_meta = basis_layers(
        int(manifest["source_degree"]),
        int(manifest["w_degree"]),
        chern_degrees,
    )

    verifications = []
    for result in reduce_payload["results"]:
        cdegree = int(result["chern_degree"])
        source_basis = source_by_chern.get(cdegree, ())
        if result["status"] == "trivial_zero_rank":
            ok = len(source_basis) == 0 and int(result["target_rank"]) == 0
            verifications.append({
                "chern_degree": cdegree,
                "status": "verified_trivial_zero" if ok else "failed_trivial_zero",
                "passed": ok,
            })
            continue
        if result["status"] != "full_rank_mod_p":
            verifications.append({
                "chern_degree": cdegree,
                "status": "skipped_uncertified_result",
                "passed": bool(args.allow_in_progress),
                "result_status": result["status"],
            })
            continue
        rows = selected_row_indices(result)
        columns = selected_column_indices(result)
        matrix = recompute_selected_minor(source_basis, w_basis, rows, columns, p)
        det = mrs.determinant_mod(matrix, p)
        matrix_sha = mrs.matrix_digest(matrix, p)
        expected_det = int(result["selected_minor_determinant_mod_p"]) % p
        primary_ok = (
            det % p == expected_det
            and det % p != 0
            and matrix_sha == result["selected_minor_matrix_sha256"]
        )
        second_prime_payload = None
        second_prime_ok = True
        if second_prime is not None:
            second_matrix = recompute_selected_minor(source_basis, w_basis, rows, columns, second_prime)
            second_det = mrs.determinant_mod(second_matrix, second_prime)
            second_prime_ok = bool(second_det % second_prime)
            second_prime_payload = {
                "prime": str(second_prime),
                "prime_validation": mrs.validate_prime(second_prime),
                "selected_minor_determinant_mod_p": str(second_det % second_prime),
                "nonzero": second_prime_ok,
                "selected_minor_matrix_sha256": mrs.matrix_digest(second_matrix, second_prime),
            }
        item_passed = primary_ok and second_prime_ok
        verifications.append({
            "chern_degree": cdegree,
            "status": (
                "verified_full_rank_certificate"
                if item_passed else
                "failed_second_prime_certificate"
                if primary_ok and not second_prime_ok else
                "failed_full_rank_certificate"
            ),
            "passed": item_passed,
            "rows_recomputed": len(rows),
            "columns_recomputed": len(columns),
            "entries_recomputed": len(rows) * len(columns),
            "selected_rows": rows,
            "selected_columns": columns,
            "recomputed_determinant_mod_p": str(det % p),
            "expected_determinant_mod_p": str(expected_det),
            "recomputed_matrix_sha256": matrix_sha,
            "expected_matrix_sha256": result["selected_minor_matrix_sha256"],
            "second_prime_check": second_prime_payload,
        })

    passed = all(item["passed"] for item in verifications)
    payload = {
        "runner": "jk_only_cluster_verify_certificate",
        "kind": "jk_only_cluster_certificate_verification",
        "schema_version": VERIFY_SCHEMA_VERSION,
        "status": "passed" if passed else "failed",
        "manifest": os.path.abspath(args.manifest),
        "manifest_sha256": manifest_sha256,
        "reduce_output": os.path.abspath(args.reduce_output),
        "reduce_output_sha256": mrs.sha256_file(args.reduce_output),
        "prime": manifest["prime"],
        "prime_validation": manifest["prime_validation"],
        "second_prime": str(second_prime) if second_prime is not None else None,
        "elapsed_seconds": time.time() - started,
        "diagnostics": diagnostics_snapshot(started),
        "verifications": verifications,
    }
    if args.output:
        atomic_json_dump(args.output, payload)
    return payload


def add_shared_basis_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prime", type=int, default=fm.DEFAULT_PRIME)
    parser.add_argument("--source-degree", type=int, default=22)
    parser.add_argument("--w-degree", type=int, default=26)
    parser.add_argument("--chern-degrees", default="11-22")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    manifest_parser = sub.add_parser("manifest")
    add_shared_basis_args(manifest_parser)
    manifest_parser.add_argument("--column-order", choices=["cheap", "cheap-probe", "rank-sampled", "natural"], default="cheap")
    manifest_parser.add_argument("--planner-sample-rows", type=int, default=8)
    manifest_parser.add_argument("--probe-planner-sample-rows", type=int, default=2)
    manifest_parser.add_argument("--probe-planner-pool-size", type=int, default=10)
    manifest_parser.add_argument("--rank-planner-sample-rows", type=int, default=8)
    manifest_parser.add_argument("--rank-planner-pool-size", type=int, default=80)
    manifest_parser.add_argument("--columns-per-task", type=int, default=8)
    manifest_parser.add_argument("--wave-size", type=int, default=50)
    manifest_parser.add_argument("--shard-mode", choices=["column", "task"], default="task")
    manifest_parser.add_argument("--output", default=DEFAULT_MANIFEST)

    wave_parser = sub.add_parser("wave")
    wave_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    wave_parser.add_argument("--wave-index", type=int, required=True)
    wave_parser.add_argument("--chern-degrees", default="")
    wave_parser.add_argument("--previous-reduce", default="")
    wave_parser.add_argument("--previous-verification", default="")
    wave_parser.add_argument("--output", default="")

    worker_parser = sub.add_parser("worker")
    worker_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    worker_parser.add_argument("--task-index", default=os.environ.get("SLURM_ARRAY_TASK_ID"))
    worker_parser.add_argument("--all-tasks", action="store_true")
    worker_parser.add_argument("--wave-index", type=int, default=None)
    worker_parser.add_argument("--shard-dir", default=DEFAULT_SHARD_DIR)
    worker_parser.add_argument("--shard-mode", choices=["auto", "column", "task"], default="auto")
    worker_parser.add_argument("--skip-existing", action="store_true", default=True)
    worker_parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    worker_parser.add_argument("--repair-existing", action="store_true", default=True)
    worker_parser.add_argument("--no-repair-existing", dest="repair_existing", action="store_false")
    worker_parser.add_argument("--output", default="")

    reduce_parser = sub.add_parser("reduce")
    reduce_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    reduce_parser.add_argument("--shard-dir", default=DEFAULT_SHARD_DIR)
    reduce_parser.add_argument("--shard-mode", choices=["auto", "column", "task"], default="auto")
    reduce_parser.add_argument("--output", default=DEFAULT_REDUCE_OUTPUT)

    verify_parser = sub.add_parser("verify-certificate")
    verify_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    verify_parser.add_argument("--reduce-output", default=DEFAULT_REDUCE_OUTPUT)
    verify_parser.add_argument("--second-prime", type=int, default=0)
    verify_parser.add_argument("--allow-in-progress", action="store_true")
    verify_parser.add_argument("--output", default=os.path.join(HERE, "cluster_certificate_verification.json"))

    relation_reduce_parser = sub.add_parser("relation-reduce")
    relation_reduce_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    relation_reduce_parser.add_argument("--shard-dir", default=DEFAULT_SHARD_DIR)
    relation_reduce_parser.add_argument("--shard-mode", choices=["auto", "column", "task"], default="auto")
    relation_reduce_parser.add_argument("--chern-degrees", default="")
    relation_reduce_parser.add_argument("--expected-kernel-dimension", type=int, default=1)
    relation_reduce_parser.add_argument("--normalization-row", type=int, default=None)
    relation_reduce_parser.add_argument("--max-failure-records", type=int, default=5)
    relation_reduce_parser.add_argument("--output", default=os.path.join(HERE, "cluster_relation_reduce_results.json"))

    relation_verify_parser = sub.add_parser("verify-relation-certificate")
    relation_verify_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    relation_verify_parser.add_argument("--relation-reduce-output", default=os.path.join(HERE, "cluster_relation_reduce_results.json"))
    relation_verify_parser.add_argument("--second-prime", type=int, default=0)
    relation_verify_parser.add_argument("--allow-in-progress", action="store_true")
    relation_verify_parser.add_argument("--max-failure-records", type=int, default=5)
    relation_verify_parser.add_argument("--output", default=os.path.join(HERE, "cluster_relation_certificate_verification.json"))

    args = parser.parse_args()
    if args.command == "manifest":
        payload = build_manifest(args)
    elif args.command == "wave":
        payload = plan_wave(args)
    elif args.command == "worker":
        payload = compute_worker(args)
    elif args.command == "reduce":
        payload = reduce_shards(args)
    elif args.command == "verify-certificate":
        payload = verify_certificate(args)
    elif args.command == "relation-reduce":
        payload = relation_reduce(args)
    elif args.command == "verify-relation-certificate":
        payload = verify_relation_certificate(args)
    else:
        raise ValueError(args.command)
    print(json.dumps(mrs.json_ready(payload), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
