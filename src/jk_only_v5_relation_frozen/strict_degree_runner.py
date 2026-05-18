#!/usr/bin/env python
"""Strict per-degree runner for publication-grade JK-only rank searches.

This wrapper is deliberately conservative. It expands every artifact path to
an absolute path, records every command in a JSONL ledger, reduces/verifies
after small task batches, and only treats a result as publishable after a final
non-``--allow-in-progress`` certificate verification with a second prime.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


HERE = Path(__file__).resolve().parent
PLAYGROUND = HERE.parents[1]
DEFAULT_RUN_PARENT = PLAYGROUND / "jk_v5_runs"
DEFAULT_PUBLICATION_REPO = PLAYGROUND / "Pairing-matrix-r5-d1-h22"
DRIVER = HERE / "cluster_rank_driver.py"


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_text(cmd: Sequence[str], cwd: Path) -> str:
    result = subprocess.run(
        list(cmd),
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.stdout.strip()


def git_info(path: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {"path": str(path)}
    if not path.exists():
        info["exists"] = False
        return info
    info["exists"] = True
    info["top_level"] = run_text(["git", "-C", str(path), "rev-parse", "--show-toplevel"], path)
    info["head"] = run_text(["git", "-C", str(path), "rev-parse", "--verify", "HEAD"], path)
    info["branch"] = run_text(["git", "-C", str(path), "branch", "--show-current"], path)
    info["status_short"] = run_text(["git", "-C", str(path), "status", "--short"], path)
    return info


def python_environment() -> Dict[str, Any]:
    packages: Dict[str, Optional[str]] = {}
    for name in ("sympy",):
        try:
            module = __import__(name)
        except Exception:
            packages[name] = None
        else:
            packages[name] = str(getattr(module, "__version__", "unknown"))
    return {
        "executable": sys.executable,
        "version": sys.version,
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "packages": packages,
    }


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


def chunks(values: Sequence[int], size: int) -> Iterable[List[int]]:
    require(size >= 1, "chunk size must be positive")
    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def append_ledger(ledger_path: Path, event: Dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload.setdefault("timestamp_utc", now_iso())
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


def command_string(cmd: Sequence[str]) -> str:
    return shlex.join([str(part) for part in cmd])


def run_command(
    *,
    label: str,
    cmd: Sequence[str],
    cwd: Path,
    log_path: Path,
    ledger_path: Path,
    expected_outputs: Sequence[Path] = (),
) -> Dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    started_iso = now_iso()
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"$ {command_string(cmd)}\n\n")
        log.flush()
        result = subprocess.run(
            [str(part) for part in cmd],
            cwd=str(cwd),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    elapsed = time.time() - started
    output_hashes = {
        str(path): sha256_file(path)
        for path in expected_outputs
        if path.exists()
    }
    event = {
        "event": "command_finished",
        "label": label,
        "command": command_string(cmd),
        "cwd": str(cwd),
        "started_utc": started_iso,
        "elapsed_seconds": elapsed,
        "returncode": result.returncode,
        "log_path": str(log_path),
        "log_sha256": sha256_file(log_path),
        "expected_outputs": [str(path) for path in expected_outputs],
        "output_sha256": output_hashes,
    }
    append_ledger(ledger_path, event)
    if result.returncode:
        raise RuntimeError(f"{label} failed; see {log_path}")
    for path in expected_outputs:
        require(path.exists(), f"{label} did not create expected output: {path}")
    return event


def build_run_paths(args: argparse.Namespace) -> Dict[str, Path]:
    run_root = Path(args.run_root).expanduser().resolve() if args.run_root else (
        DEFAULT_RUN_PARENT / utc_stamp()
    ).resolve()
    degree_dir = (run_root / f"c{int(args.chern_degree)}").resolve()
    return {
        "run_root": run_root,
        "degree_dir": degree_dir,
        "manifest": degree_dir / "manifest.json",
        "shards": degree_dir / "shards",
        "waves": degree_dir / "waves",
        "workers": degree_dir / "worker_summaries",
        "reductions": degree_dir / "reductions",
        "verifications": degree_dir / "verifications",
        "logs": degree_dir / "logs",
        "ledger": degree_dir / "ledger.jsonl",
        "ledger_snapshot": degree_dir / "ledger_publication_snapshot.jsonl",
        "provenance": degree_dir / "provenance.json",
        "final_reduce": degree_dir / "reduce_final.json",
        "final_verification": degree_dir / "verification_final.json",
        "final_result": degree_dir / "final_result.json",
    }


def create_provenance(args: argparse.Namespace, paths: Dict[str, Path]) -> None:
    publication_repo = Path(args.publication_repo).expanduser().resolve()
    payload = {
        "runner": getattr(args, "provenance_runner", "jk_only_strict_degree_runner"),
        "status": "created",
        "created_utc": now_iso(),
        "chern_degree": int(args.chern_degree),
        "run_root": str(paths["run_root"]),
        "degree_dir": str(paths["degree_dir"]),
        "python": python_environment(),
        "paths": {key: str(value) for key, value in paths.items()},
        "source_hashes": {
            "strict_degree_runner.py": sha256_file(Path(__file__).resolve()),
            "cluster_rank_driver.py": sha256_file(DRIVER),
        },
        "git": {
            "playground": git_info(PLAYGROUND),
            "publication_repo": git_info(publication_repo),
        },
        "publication_repo": str(publication_repo),
        "parameters": vars(args),
    }
    extractor = publication_repo / "scripts" / "extract_verified_result.py"
    if extractor.exists():
        payload["source_hashes"]["extract_verified_result.py"] = sha256_file(extractor)
    relation_runner = HERE / "strict_relation_runner.py"
    if relation_runner.exists():
        payload["source_hashes"]["strict_relation_runner.py"] = sha256_file(relation_runner)
    relation_extractor = publication_repo / "scripts" / "extract_relation_certificate.py"
    if relation_extractor.exists():
        payload["source_hashes"]["extract_relation_certificate.py"] = sha256_file(relation_extractor)
    json_dump(paths["provenance"], payload)
    append_ledger(paths["ledger"], {
        "event": "provenance_created",
        "provenance": str(paths["provenance"]),
        "provenance_sha256": sha256_file(paths["provenance"]),
    })


def seal_ledger_snapshot(paths: Dict[str, Path]) -> Path:
    require(paths["ledger"].exists(), "cannot seal missing ledger")
    data = paths["ledger"].read_bytes()
    paths["ledger_snapshot"].write_bytes(data)
    append_ledger(paths["ledger"], {
        "event": "ledger_publication_snapshot_created",
        "ledger_snapshot": str(paths["ledger_snapshot"]),
        "ledger_snapshot_sha256": sha256_file(paths["ledger_snapshot"]),
    })
    return paths["ledger_snapshot"]


def validate_strict_manifest(args: argparse.Namespace, manifest: Dict[str, Any]) -> None:
    cdegree = int(args.chern_degree)
    chern_degrees = [int(item) for item in manifest.get("chern_degrees", [])]
    require(chern_degrees == [cdegree], f"strict run expected manifest chern degrees [{cdegree}], got {chern_degrees}")
    require(int(manifest.get("source_degree", -1)) == int(args.source_degree), "manifest source degree mismatch")
    require(int(manifest.get("w_degree", -1)) == int(args.w_degree), "manifest W degree mismatch")
    require(int(manifest.get("columns_per_task", -1)) == int(args.columns_per_task), "manifest columns_per_task mismatch")
    require(int(manifest.get("wave_size", -1)) == int(args.wave_size), "manifest wave_size mismatch")
    require(manifest.get("shard_mode") == "task", "strict runner requires task shard mode")
    if args.prime:
        require(int(manifest.get("prime", -1)) == int(args.prime), "manifest prime mismatch")
    require(str(cdegree) in manifest.get("source_basis_dimensions_by_chern", {}), "manifest missing requested source dimension")
    require(int(args.second_prime) != int(manifest["prime"]), "second prime must be distinct from primary manifest prime")


def read_reduce_status(path: Path) -> str:
    return str(load_json(path).get("status"))


def assert_final_verification(path: Path, second_prime: int) -> Dict[str, Any]:
    payload = load_json(path)
    require(payload.get("status") == "passed", "final verification did not pass")
    require(str(payload.get("second_prime")) == str(second_prime), "final verification used the wrong second prime")
    for item in payload.get("verifications", []):
        require(item.get("status") != "skipped_uncertified_result", "final verification skipped an uncertified result")
        if item.get("status") == "verified_full_rank_certificate":
            second = item.get("second_prime_check")
            require(isinstance(second, dict) and second.get("nonzero") is True, "second-prime determinant is zero/missing")
    return payload


def run_preflight(args: argparse.Namespace, paths: Dict[str, Path]) -> None:
    py_compile_log = paths["logs"] / "preflight_py_compile.log"
    run_command(
        label="preflight_py_compile",
        cmd=[sys.executable, "-m", "py_compile", *[str(path) for path in sorted(HERE.glob("*.py"))]],
        cwd=PLAYGROUND,
        log_path=py_compile_log,
        ledger_path=paths["ledger"],
    )
    checks_output = paths["degree_dir"] / "jk_only_check_results.json"
    run_command(
        label="preflight_run_checks",
        cmd=[
            sys.executable,
            str(HERE / "run_checks.py"),
            "--output",
            str(checks_output),
        ],
        cwd=PLAYGROUND,
        log_path=paths["logs"] / "preflight_run_checks.log",
        ledger_path=paths["ledger"],
        expected_outputs=[checks_output],
    )


def manifest_command(args: argparse.Namespace, manifest: Path) -> List[str]:
    cmd = [
        sys.executable,
        str(DRIVER),
        "manifest",
        "--chern-degrees",
        str(int(args.chern_degree)),
        "--column-order",
        args.column_order,
        "--columns-per-task",
        str(int(args.columns_per_task)),
        "--wave-size",
        str(int(args.wave_size)),
        "--shard-mode",
        "task",
        "--source-degree",
        str(int(args.source_degree)),
        "--w-degree",
        str(int(args.w_degree)),
        "--output",
        str(manifest),
    ]
    if args.prime:
        cmd.extend(["--prime", str(int(args.prime))])
    return cmd


def run_manifest(args: argparse.Namespace, paths: Dict[str, Path]) -> List[str]:
    cmd = manifest_command(args, paths["manifest"])
    if paths["manifest"].exists() and args.resume:
        append_ledger(paths["ledger"], {
            "event": "manifest_reused",
            "manifest": str(paths["manifest"]),
            "manifest_sha256": sha256_file(paths["manifest"]),
            "command": command_string(cmd),
        })
        return cmd
    require(not paths["manifest"].exists() or args.force, f"manifest exists; pass --resume or --force: {paths['manifest']}")
    run_command(
        label="manifest",
        cmd=cmd,
        cwd=PLAYGROUND,
        log_path=paths["logs"] / "manifest.log",
        ledger_path=paths["ledger"],
        expected_outputs=[paths["manifest"]],
    )
    return cmd


def run_wave_plan(
    args: argparse.Namespace,
    paths: Dict[str, Path],
    wave_index: int,
    previous_reduce: Optional[Path],
    previous_verification: Optional[Path],
) -> Dict[str, Any]:
    output = paths["waves"] / f"wave_{wave_index:03d}.json"
    cmd = [
        sys.executable,
        str(DRIVER),
        "wave",
        "--manifest",
        str(paths["manifest"]),
        "--wave-index",
        str(wave_index),
        "--output",
        str(output),
    ]
    if previous_reduce is not None:
        require(previous_verification is not None, "previous reduce requires previous verification")
        cmd.extend([
            "--previous-reduce",
            str(previous_reduce),
            "--previous-verification",
            str(previous_verification),
        ])
    else:
        cmd.extend(["--chern-degrees", str(int(args.chern_degree))])
    run_command(
        label=f"wave_{wave_index:03d}",
        cmd=cmd,
        cwd=PLAYGROUND,
        log_path=paths["logs"] / f"wave_{wave_index:03d}.log",
        ledger_path=paths["ledger"],
        expected_outputs=[output],
    )
    return load_json(output)


def run_worker_batch(
    args: argparse.Namespace,
    paths: Dict[str, Path],
    wave_index: int,
    batch_index: int,
    task_indices: Sequence[int],
) -> Dict[str, Any]:
    task_spec = compressed_int_ranges(task_indices)
    output = paths["workers"] / f"worker_wave{wave_index:03d}_batch{batch_index:03d}.json"
    cmd = [
        sys.executable,
        str(DRIVER),
        "worker",
        "--manifest",
        str(paths["manifest"]),
        "--task-index",
        task_spec,
        "--shard-dir",
        str(paths["shards"]),
        "--shard-mode",
        "task",
        "--no-repair-existing",
        "--output",
        str(output),
    ]
    run_command(
        label=f"worker_wave{wave_index:03d}_batch{batch_index:03d}",
        cmd=cmd,
        cwd=PLAYGROUND,
        log_path=paths["logs"] / f"worker_wave{wave_index:03d}_batch{batch_index:03d}.log",
        ledger_path=paths["ledger"],
        expected_outputs=[output],
    )
    payload = load_json(output)
    bad = [item for item in payload.get("outputs", []) if item.get("status") == "recomputed_invalid_existing"]
    require(not bad, "worker recomputed invalid existing shards; stop and document before continuing")
    return payload


def run_reduce(args: argparse.Namespace, paths: Dict[str, Path], label: str, output: Path) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(DRIVER),
        "reduce",
        "--manifest",
        str(paths["manifest"]),
        "--shard-dir",
        str(paths["shards"]),
        "--shard-mode",
        "task",
        "--output",
        str(output),
    ]
    run_command(
        label=label,
        cmd=cmd,
        cwd=PLAYGROUND,
        log_path=paths["logs"] / f"{label}.log",
        ledger_path=paths["ledger"],
        expected_outputs=[output],
    )
    return load_json(output)


def run_verification(
    args: argparse.Namespace,
    paths: Dict[str, Path],
    *,
    label: str,
    reduce_output: Path,
    output: Path,
    final: bool,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(DRIVER),
        "verify-certificate",
        "--manifest",
        str(paths["manifest"]),
        "--reduce-output",
        str(reduce_output),
        "--output",
        str(output),
    ]
    if final:
        cmd.extend(["--second-prime", str(int(args.second_prime))])
    else:
        cmd.append("--allow-in-progress")
    run_command(
        label=label,
        cmd=cmd,
        cwd=PLAYGROUND,
        log_path=paths["logs"] / f"{label}.log",
        ledger_path=paths["ledger"],
        expected_outputs=[output],
    )
    payload = load_json(output)
    require(payload.get("status") == "passed", f"{label} did not pass")
    if final:
        assert_final_verification(output, int(args.second_prime))
    return payload


def max_wave_index(manifest: Dict[str, Any], cdegree: int) -> int:
    waves = [
        int(task["wave_index"])
        for task in manifest.get("tasks", [])
        if int(task.get("chern_degree", -1)) == cdegree
    ]
    return max(waves) if waves else 0


def run_publication_extract(
    args: argparse.Namespace,
    paths: Dict[str, Path],
    commands: Dict[str, str],
) -> None:
    publication_repo = Path(args.publication_repo).expanduser().resolve()
    extractor = publication_repo / "scripts" / "extract_verified_result.py"
    require(extractor.exists(), f"missing publication extractor: {extractor}")
    cmd = [
        sys.executable,
        str(extractor),
        "--chern-degree",
        str(int(args.chern_degree)),
        "--manifest",
        str(paths["manifest"]),
        "--reduce",
        str(paths["final_reduce"]),
        "--verification",
        str(paths["final_verification"]),
        "--repo-root",
        str(publication_repo),
        "--manifest-command",
        commands["manifest"],
        "--worker-command",
        commands["worker"],
        "--reduce-command",
        commands["reduce"],
        "--verify-command",
        commands["verify_certificate"],
        "--require-final-reduce",
        "--run-ledger",
        str(paths["ledger_snapshot"]),
        "--run-provenance",
        str(paths["provenance"]),
        "--manifest-label",
        f"raw c{int(args.chern_degree)} manifest artifact, not committed",
        "--reduce-label",
        f"raw c{int(args.chern_degree)} final reduce artifact, not committed",
        "--verification-label",
        f"raw c{int(args.chern_degree)} final verification artifact, not committed",
        "--run-ledger-label",
        f"raw c{int(args.chern_degree)} strict-run ledger publication snapshot, not committed",
        "--run-provenance-label",
        f"raw c{int(args.chern_degree)} strict-run provenance, not committed",
    ]
    run_command(
        label="publication_extract",
        cmd=cmd,
        cwd=publication_repo,
        log_path=paths["logs"] / "publication_extract.log",
        ledger_path=paths["ledger"],
        expected_outputs=[publication_repo / f"c{int(args.chern_degree)}" / "certificate.json"],
    )


def run_degree(args: argparse.Namespace) -> Dict[str, Any]:
    require(11 <= int(args.chern_degree) <= 22, "--chern-degree must be between 11 and 22")
    require(int(args.task_batch_size) >= 1, "--task-batch-size must be positive")
    require(int(args.second_prime) > 0, "--second-prime must be supplied for strict final verification")
    paths = build_run_paths(args)
    paths["degree_dir"].mkdir(parents=True, exist_ok=True)
    for key in ("shards", "waves", "workers", "reductions", "verifications", "logs"):
        paths[key].mkdir(parents=True, exist_ok=True)
    create_provenance(args, paths)
    if args.preflight:
        run_preflight(args, paths)
    manifest_cmd = run_manifest(args, paths)
    manifest = load_json(paths["manifest"])
    validate_strict_manifest(args, manifest)
    max_wave = max_wave_index(manifest, int(args.chern_degree))
    if args.max_waves is not None:
        max_wave = min(max_wave, int(args.max_waves) - 1)
    require(max_wave >= 0, "no waves are available")

    previous_reduce: Optional[Path] = None
    previous_verification: Optional[Path] = None
    worker_command_template = (
        f"{command_string([sys.executable, str(DRIVER), 'worker', '--manifest', str(paths['manifest']), '--task-index', '<task_index_spec>', '--shard-dir', str(paths['shards']), '--shard-mode', 'task', '--no-repair-existing', '--output', '<per-batch-worker-summary.json>'])}; "
        "exact per-batch commands are recorded in the raw strict-run ledger"
    )

    source_dim = int(manifest.get("source_basis_dimensions_by_chern", {}).get(str(int(args.chern_degree)), 0))
    if source_dim == 0:
        final_reduce_payload = run_reduce(args, paths, "reduce_final", paths["final_reduce"])
        require(final_reduce_payload.get("status") == "passed", "zero-row final reduce did not pass")
        run_verification(
            args,
            paths,
            label="verification_final",
            reduce_output=paths["final_reduce"],
            output=paths["final_verification"],
            final=True,
        )
        commands = {
            "manifest": command_string(manifest_cmd),
            "worker": "no worker command: c-degree has zero source rows",
            "reduce": command_string([
                sys.executable,
                str(DRIVER),
                "reduce",
                "--manifest",
                str(paths["manifest"]),
                "--shard-dir",
                str(paths["shards"]),
                "--shard-mode",
                "task",
                "--output",
                str(paths["final_reduce"]),
            ]),
            "verify_certificate": command_string([
                sys.executable,
                str(DRIVER),
                "verify-certificate",
                "--manifest",
                str(paths["manifest"]),
                "--reduce-output",
                str(paths["final_reduce"]),
                "--second-prime",
                str(int(args.second_prime)),
                "--output",
                str(paths["final_verification"]),
            ]),
        }
        final_result = {
            "runner": "jk_only_strict_degree_runner",
            "status": "verified",
            "chern_degree": int(args.chern_degree),
            "run_root": str(paths["run_root"]),
            "degree_dir": str(paths["degree_dir"]),
            "manifest": str(paths["manifest"]),
            "manifest_sha256": sha256_file(paths["manifest"]),
            "reduce_final": str(paths["final_reduce"]),
            "reduce_final_sha256": sha256_file(paths["final_reduce"]),
            "verification_final": str(paths["final_verification"]),
            "verification_final_sha256": sha256_file(paths["final_verification"]),
            "ledger": str(paths["ledger"]),
            "ledger_sha256": sha256_file(paths["ledger"]),
            "provenance": str(paths["provenance"]),
            "provenance_sha256": sha256_file(paths["provenance"]),
            "commands": commands,
        }
        json_dump(paths["final_result"], final_result)
        append_ledger(paths["ledger"], {
            "event": "degree_verified",
            "final_result": str(paths["final_result"]),
            "final_result_sha256": sha256_file(paths["final_result"]),
        })
        if args.extract_publication:
            seal_ledger_snapshot(paths)
            run_publication_extract(args, paths, commands)
        return final_result

    for wave_index in range(max_wave + 1):
        wave = run_wave_plan(args, paths, wave_index, previous_reduce, previous_verification)
        if wave.get("status") == "no_unresolved_chern_degrees":
            break
        require(wave.get("status") == "wave_planned", f"unexpected wave status: {wave.get('status')}")
        task_indices = [int(item) for item in wave.get("task_indices", [])]
        require(task_indices, f"wave {wave_index} has no tasks")
        for batch_index, batch in enumerate(chunks(task_indices, int(args.task_batch_size))):
            run_worker_batch(args, paths, wave_index, batch_index, batch)
            reduce_output = paths["reductions"] / f"reduce_wave{wave_index:03d}_batch{batch_index:03d}.json"
            reduce_payload = run_reduce(args, paths, f"reduce_wave{wave_index:03d}_batch{batch_index:03d}", reduce_output)
            if reduce_payload.get("status") == "passed":
                final_reduce_payload = run_reduce(args, paths, "reduce_final", paths["final_reduce"])
                require(final_reduce_payload.get("status") == "passed", "final reduce did not pass")
                run_verification(
                    args,
                    paths,
                    label="verification_final",
                    reduce_output=paths["final_reduce"],
                    output=paths["final_verification"],
                    final=True,
                )
                commands = {
                    "manifest": command_string(manifest_cmd),
                    "worker": worker_command_template,
                    "reduce": command_string([
                        sys.executable,
                        str(DRIVER),
                        "reduce",
                        "--manifest",
                        str(paths["manifest"]),
                        "--shard-dir",
                        str(paths["shards"]),
                        "--shard-mode",
                        "task",
                        "--output",
                        str(paths["final_reduce"]),
                    ]),
                    "verify_certificate": command_string([
                        sys.executable,
                        str(DRIVER),
                        "verify-certificate",
                        "--manifest",
                        str(paths["manifest"]),
                        "--reduce-output",
                        str(paths["final_reduce"]),
                        "--second-prime",
                        str(int(args.second_prime)),
                        "--output",
                        str(paths["final_verification"]),
                    ]),
                }
                final_result = {
                    "runner": "jk_only_strict_degree_runner",
                    "status": "verified",
                    "chern_degree": int(args.chern_degree),
                    "run_root": str(paths["run_root"]),
                    "degree_dir": str(paths["degree_dir"]),
                    "manifest": str(paths["manifest"]),
                    "manifest_sha256": sha256_file(paths["manifest"]),
                    "reduce_final": str(paths["final_reduce"]),
                    "reduce_final_sha256": sha256_file(paths["final_reduce"]),
                    "verification_final": str(paths["final_verification"]),
                    "verification_final_sha256": sha256_file(paths["final_verification"]),
                    "ledger": str(paths["ledger"]),
                    "ledger_sha256": sha256_file(paths["ledger"]),
                    "provenance": str(paths["provenance"]),
                    "provenance_sha256": sha256_file(paths["provenance"]),
                    "commands": commands,
                }
                json_dump(paths["final_result"], final_result)
                append_ledger(paths["ledger"], {
                    "event": "degree_verified",
                    "final_result": str(paths["final_result"]),
                    "final_result_sha256": sha256_file(paths["final_result"]),
                })
                if args.extract_publication:
                    seal_ledger_snapshot(paths)
                    run_publication_extract(args, paths, commands)
                return final_result

            verification_output = paths["verifications"] / f"verification_wave{wave_index:03d}_batch{batch_index:03d}.json"
            run_verification(
                args,
                paths,
                label=f"verification_wave{wave_index:03d}_batch{batch_index:03d}",
                reduce_output=reduce_output,
                output=verification_output,
                final=False,
            )
            previous_reduce = reduce_output
            previous_verification = verification_output
            append_ledger(paths["ledger"], {
                "event": "wave_batch_completed",
                "wave_index": wave_index,
                "batch_index": batch_index,
                "task_index_spec": compressed_int_ranges(batch),
                "reduce": str(reduce_output),
                "reduce_sha256": sha256_file(reduce_output),
                "verification": str(verification_output),
                "verification_sha256": sha256_file(verification_output),
                "reduce_status": read_reduce_status(reduce_output),
            })
    raise RuntimeError(f"exhausted waves 0..{max_wave} without final verified result")


def preflight_only(args: argparse.Namespace) -> Dict[str, Any]:
    args.chern_degree = int(args.chern_degree)
    paths = build_run_paths(args)
    paths["degree_dir"].mkdir(parents=True, exist_ok=True)
    paths["logs"].mkdir(parents=True, exist_ok=True)
    create_provenance(args, paths)
    run_preflight(args, paths)
    result = {
        "runner": "jk_only_strict_degree_runner",
        "status": "preflight_passed",
        "chern_degree": int(args.chern_degree),
        "run_root": str(paths["run_root"]),
        "ledger": str(paths["ledger"]),
        "ledger_sha256": sha256_file(paths["ledger"]),
        "provenance": str(paths["provenance"]),
        "provenance_sha256": sha256_file(paths["provenance"]),
    }
    json_dump(paths["degree_dir"] / "preflight_result.json", result)
    return result


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chern-degree", type=int, required=True)
    parser.add_argument("--run-root", default="")
    parser.add_argument("--publication-repo", default=str(DEFAULT_PUBLICATION_REPO))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight")
    add_common_args(preflight)

    run = sub.add_parser("run-degree")
    add_common_args(run)
    run.add_argument("--source-degree", type=int, default=22)
    run.add_argument("--w-degree", type=int, default=26)
    run.add_argument("--prime", type=int, default=0)
    run.add_argument("--column-order", choices=["cheap", "cheap-probe", "rank-sampled", "natural"], default="cheap-probe")
    run.add_argument("--columns-per-task", type=int, default=16)
    run.add_argument("--wave-size", type=int, default=64)
    run.add_argument("--task-batch-size", type=int, default=4)
    run.add_argument("--second-prime", type=int, default=1000033)
    run.add_argument("--max-waves", type=int, default=None)
    run.add_argument("--preflight", action="store_true")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--force", action="store_true")
    run.add_argument("--extract-publication", action="store_true")

    args = parser.parse_args()
    if args.command == "preflight":
        payload = preflight_only(args)
    elif args.command == "run-degree":
        payload = run_degree(args)
    else:
        raise ValueError(args.command)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
