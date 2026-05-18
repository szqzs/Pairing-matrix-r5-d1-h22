#!/usr/bin/env python
"""Strict runner for a corank-one JK relation certificate.

This is the c12-oriented companion to ``strict_degree_runner.py``.  Unlike the
full-rank runner, it does not stop when enough columns certify a rank lower
bound.  It computes every W-column in the manifest, then asks
``cluster_rank_driver.py relation-reduce`` to prove:

* a nonzero rank-43 selected minor, and
* a normalized left-kernel vector annihilating every W26 column modulo p.

The final verifier recomputes the selected minor and the full annihilation
check directly from the JK evaluator, optionally also at a second prime.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

import strict_degree_runner as sdr


HERE = Path(__file__).resolve().parent
DRIVER = HERE / "cluster_rank_driver.py"


def relation_paths(args: argparse.Namespace) -> Dict[str, Path]:
    paths = sdr.build_run_paths(args)
    paths["relation_reduce_final"] = paths["degree_dir"] / "relation_reduce_final.json"
    paths["relation_verification_final"] = paths["degree_dir"] / "relation_verification_final.json"
    return paths


def run_relation_reduce(args: argparse.Namespace, paths: Dict[str, Path]) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(DRIVER),
        "relation-reduce",
        "--manifest",
        str(paths["manifest"]),
        "--shard-dir",
        str(paths["shards"]),
        "--shard-mode",
        "task",
        "--chern-degrees",
        str(int(args.chern_degree)),
        "--expected-kernel-dimension",
        str(int(args.expected_kernel_dimension)),
        "--output",
        str(paths["relation_reduce_final"]),
    ]
    if args.normalization_row is not None:
        cmd.extend(["--normalization-row", str(int(args.normalization_row))])
    sdr.run_command(
        label="relation_reduce_final",
        cmd=cmd,
        cwd=sdr.PLAYGROUND,
        log_path=paths["logs"] / "relation_reduce_final.log",
        ledger_path=paths["ledger"],
        expected_outputs=[paths["relation_reduce_final"]],
    )
    payload = sdr.load_json(paths["relation_reduce_final"])
    sdr.require(payload.get("status") == "passed", "relation reduce did not pass")
    return payload


def run_relation_verification(args: argparse.Namespace, paths: Dict[str, Path]) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(DRIVER),
        "verify-relation-certificate",
        "--manifest",
        str(paths["manifest"]),
        "--relation-reduce-output",
        str(paths["relation_reduce_final"]),
        "--second-prime",
        str(int(args.second_prime)),
        "--output",
        str(paths["relation_verification_final"]),
    ]
    sdr.run_command(
        label="relation_verification_final",
        cmd=cmd,
        cwd=sdr.PLAYGROUND,
        log_path=paths["logs"] / "relation_verification_final.log",
        ledger_path=paths["ledger"],
        expected_outputs=[paths["relation_verification_final"]],
    )
    payload = sdr.load_json(paths["relation_verification_final"])
    sdr.require(payload.get("status") == "passed", "relation verification did not pass")
    sdr.require(str(payload.get("second_prime")) == str(int(args.second_prime)), "relation verification used the wrong second prime")
    for item in payload.get("verifications", []):
        sdr.require(item.get("status") == "verified_relation_kernel_certificate", "relation verification did not certify the kernel")
        second = item.get("second_prime_check")
        sdr.require(isinstance(second, dict) and second.get("nonzero_selected_minor") is True, "second-prime relation minor is zero/missing")
        second_ann = second.get("annihilation_certificate")
        sdr.require(isinstance(second_ann, dict) and second_ann.get("all_w_columns_verified") is True, "second-prime annihilation check failed")
    return payload


def run_publication_extract(
    args: argparse.Namespace,
    paths: Dict[str, Path],
    commands: Dict[str, str],
) -> None:
    publication_repo = Path(args.publication_repo).expanduser().resolve()
    extractor = publication_repo / "scripts" / "extract_relation_certificate.py"
    sdr.require(extractor.exists(), f"missing relation publication extractor: {extractor}")
    cmd = [
        sys.executable,
        str(extractor),
        "--chern-degree",
        str(int(args.chern_degree)),
        "--manifest",
        str(paths["manifest"]),
        "--relation-reduce",
        str(paths["relation_reduce_final"]),
        "--verification",
        str(paths["relation_verification_final"]),
        "--repo-root",
        str(publication_repo),
        "--manifest-command",
        commands["manifest"],
        "--worker-command",
        commands["worker"],
        "--relation-reduce-command",
        commands["relation_reduce"],
        "--verify-command",
        commands["verify_relation_certificate"],
        "--run-ledger",
        str(paths["ledger_snapshot"]),
        "--run-provenance",
        str(paths["provenance"]),
    ]
    sdr.run_command(
        label="relation_publication_extract",
        cmd=cmd,
        cwd=publication_repo,
        log_path=paths["logs"] / "relation_publication_extract.log",
        ledger_path=paths["ledger"],
        expected_outputs=[publication_repo / f"c{int(args.chern_degree)}" / "relation_certificate.json"],
    )


def run_relation(args: argparse.Namespace) -> Dict[str, Any]:
    sdr.require(11 <= int(args.chern_degree) <= 22, "--chern-degree must be between 11 and 22")
    sdr.require(int(args.expected_kernel_dimension) == 1, "only corank-one certificates are currently implemented")
    sdr.require(int(args.task_batch_size) >= 1, "--task-batch-size must be positive")
    sdr.require(int(args.second_prime) > 0, "--second-prime must be supplied")
    paths = relation_paths(args)
    paths["degree_dir"].mkdir(parents=True, exist_ok=True)
    for key in ("shards", "waves", "workers", "reductions", "verifications", "logs"):
        paths[key].mkdir(parents=True, exist_ok=True)

    args.provenance_runner = "jk_only_strict_relation_runner"
    sdr.create_provenance(args, paths)
    if args.preflight:
        sdr.run_preflight(args, paths)

    manifest_cmd = sdr.run_manifest(args, paths)
    manifest = sdr.load_json(paths["manifest"])
    sdr.validate_strict_manifest(args, manifest)
    source_dim = int(manifest.get("source_basis_dimensions_by_chern", {}).get(str(int(args.chern_degree)), 0))
    sdr.require(source_dim == int(args.expected_source_dimension), f"expected source dimension {args.expected_source_dimension}, got {source_dim}")
    sdr.require(source_dim - int(args.expected_kernel_dimension) == int(args.expected_rank), "expected rank/source/kernel dimensions are inconsistent")

    max_wave = sdr.max_wave_index(manifest, int(args.chern_degree))
    if args.max_waves is not None:
        max_wave = min(max_wave, int(args.max_waves) - 1)
    worker_command_template = (
        f"{sdr.command_string([sys.executable, str(DRIVER), 'worker', '--manifest', str(paths['manifest']), '--task-index', '<task_index_spec>', '--shard-dir', str(paths['shards']), '--shard-mode', 'task', '--no-repair-existing', '--output', '<per-batch-worker-summary.json>'])}; "
        "exact per-batch commands are recorded in the raw strict-run ledger"
    )

    for wave_index in range(max_wave + 1):
        wave = sdr.run_wave_plan(args, paths, wave_index, previous_reduce=None, previous_verification=None)
        sdr.require(wave.get("status") == "wave_planned", f"unexpected wave status: {wave.get('status')}")
        task_indices = [int(item) for item in wave.get("task_indices", [])]
        sdr.require(task_indices, f"wave {wave_index} has no tasks")
        for batch_index, batch in enumerate(sdr.chunks(task_indices, int(args.task_batch_size))):
            sdr.run_worker_batch(args, paths, wave_index, batch_index, batch)
            sdr.append_ledger(paths["ledger"], {
                "event": "relation_wave_batch_completed",
                "wave_index": wave_index,
                "batch_index": batch_index,
                "task_index_spec": sdr.compressed_int_ranges(batch),
            })

    relation_reduce = run_relation_reduce(args, paths)
    relation_verification = run_relation_verification(args, paths)
    relation_reduce_command = [
        sys.executable,
        str(DRIVER),
        "relation-reduce",
        "--manifest",
        str(paths["manifest"]),
        "--shard-dir",
        str(paths["shards"]),
        "--shard-mode",
        "task",
        "--chern-degrees",
        str(int(args.chern_degree)),
        "--expected-kernel-dimension",
        str(int(args.expected_kernel_dimension)),
        "--output",
        str(paths["relation_reduce_final"]),
    ]
    if args.normalization_row is not None:
        relation_reduce_command.extend(["--normalization-row", str(int(args.normalization_row))])
    commands = {
        "manifest": sdr.command_string(manifest_cmd),
        "worker": worker_command_template,
        "relation_reduce": sdr.command_string(relation_reduce_command),
        "verify_relation_certificate": sdr.command_string([
            sys.executable,
            str(DRIVER),
            "verify-relation-certificate",
            "--manifest",
            str(paths["manifest"]),
            "--relation-reduce-output",
            str(paths["relation_reduce_final"]),
            "--second-prime",
            str(int(args.second_prime)),
            "--output",
            str(paths["relation_verification_final"]),
        ]),
    }
    final_result = {
        "runner": "jk_only_strict_relation_runner",
        "status": "verified_relation",
        "chern_degree": int(args.chern_degree),
        "run_root": str(paths["run_root"]),
        "degree_dir": str(paths["degree_dir"]),
        "manifest": str(paths["manifest"]),
        "manifest_sha256": sdr.sha256_file(paths["manifest"]),
        "relation_reduce_final": str(paths["relation_reduce_final"]),
        "relation_reduce_final_sha256": sdr.sha256_file(paths["relation_reduce_final"]),
        "relation_verification_final": str(paths["relation_verification_final"]),
        "relation_verification_final_sha256": sdr.sha256_file(paths["relation_verification_final"]),
        "ledger": str(paths["ledger"]),
        "ledger_sha256": sdr.sha256_file(paths["ledger"]),
        "provenance": str(paths["provenance"]),
        "provenance_sha256": sdr.sha256_file(paths["provenance"]),
        "commands": commands,
        "relation_reduce_status": relation_reduce.get("status"),
        "relation_verification_status": relation_verification.get("status"),
    }
    sdr.json_dump(paths["final_result"], final_result)
    sdr.append_ledger(paths["ledger"], {
        "event": "relation_degree_verified",
        "final_result": str(paths["final_result"]),
        "final_result_sha256": sdr.sha256_file(paths["final_result"]),
    })
    if args.extract_publication:
        sdr.seal_ledger_snapshot(paths)
        run_publication_extract(args, paths, commands)
    return final_result


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chern-degree", type=int, required=True)
    parser.add_argument("--run-root", default="")
    parser.add_argument("--publication-repo", default=str(sdr.DEFAULT_PUBLICATION_REPO))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-relation")
    add_common_args(run)
    run.add_argument("--source-degree", type=int, default=22)
    run.add_argument("--w-degree", type=int, default=26)
    run.add_argument("--prime", type=int, default=0)
    run.add_argument("--column-order", choices=["cheap", "cheap-probe", "rank-sampled", "natural"], default="cheap-probe")
    run.add_argument("--columns-per-task", type=int, default=16)
    run.add_argument("--wave-size", type=int, default=64)
    run.add_argument("--task-batch-size", type=int, default=4)
    run.add_argument("--second-prime", type=int, default=1000033)
    run.add_argument("--expected-source-dimension", type=int, default=44)
    run.add_argument("--expected-rank", type=int, default=43)
    run.add_argument("--expected-kernel-dimension", type=int, default=1)
    run.add_argument("--normalization-row", type=int, default=None)
    run.add_argument("--max-waves", type=int, default=None)
    run.add_argument("--preflight", action="store_true")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--force", action="store_true")
    run.add_argument("--extract-publication", action="store_true")

    args = parser.parse_args()
    if args.command == "run-relation":
        payload = run_relation(args)
    else:
        raise ValueError(args.command)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
