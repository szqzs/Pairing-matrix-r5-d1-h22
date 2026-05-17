#!/usr/bin/env python
"""Extract a compact verified Chern-degree publication record.

This script is intentionally strict. It refuses to write cXX/certificate.json
unless:

* the reduce artifact has final status "passed";
* the verification artifact has status "passed";
* the verification artifact matches the supplied manifest and reduce hashes;
* the requested Chern degree has a verified full-rank or trivial-zero result;
* the reduce result, verification record, and manifest agree on hashes, prime,
  rank, selected rows/columns, and basis provenance;
* a second-prime nonvanishing check is present unless explicitly relaxed.

It writes only compact publication records, not raw shards or full logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json_dump(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def one_by_cdegree(items: List[Dict[str, Any]], cdegree: int, label: str) -> Dict[str, Any]:
    matches = [item for item in items if int(item.get("chern_degree", -1)) == cdegree]
    require(len(matches) == 1, f"expected exactly one {label} record for c{cdegree}, got {len(matches)}")
    return matches[0]


def selected_indices(items: List[Dict[str, Any]], key: str) -> List[int]:
    return [int(item[key]) for item in items]


def validate_and_extract(args: argparse.Namespace) -> Dict[str, Any]:
    cdegree = int(args.chern_degree)
    folder_name = f"c{cdegree}"
    require(11 <= cdegree <= 22, "--chern-degree must be between 11 and 22")

    manifest = load_json(args.manifest)
    reduce_payload = load_json(args.reduce)
    verification = load_json(args.verification)
    manifest_sha = sha256_file(args.manifest)
    reduce_sha = sha256_file(args.reduce)
    verification_sha = sha256_file(args.verification)

    require(verification.get("status") == "passed", "verification artifact did not pass")
    require(verification.get("manifest_sha256") == manifest_sha, "verification manifest hash mismatch")
    require(reduce_payload.get("manifest_sha256") == manifest_sha, "reduce manifest hash mismatch")
    if args.require_final_reduce:
        require(reduce_payload.get("status") == "passed", "reduce artifact is not final/passed")
    else:
        require(reduce_payload.get("status") in {"passed", "in_progress"}, "unexpected reduce status")
    require(verification.get("reduce_output_sha256") == reduce_sha, "verification reduce hash mismatch")
    require(str(reduce_payload.get("prime")) == str(manifest.get("prime")), "prime mismatch")
    require(str(verification.get("prime")) == str(manifest.get("prime")), "verification prime mismatch")

    if args.require_second_prime:
        require(verification.get("second_prime") not in {None, "", "0"}, "missing second-prime verification")

    manifest_cdegrees = [int(item) for item in manifest.get("chern_degrees", [])]
    require(cdegree in manifest_cdegrees, f"manifest does not contain c{cdegree}")
    require(len(manifest_cdegrees) == len(set(manifest_cdegrees)), "manifest cdegrees are not unique")

    reduce_result = one_by_cdegree(reduce_payload.get("results", []), cdegree, "reduce")
    verification_item = one_by_cdegree(verification.get("verifications", []), cdegree, "verification")
    require(verification_item.get("passed") is True, f"verification record for c{cdegree} did not pass")
    require(
        all(item.get("status") != "skipped_uncertified_result" for item in verification.get("verifications", [])),
        "verification artifact contains skipped uncertified results",
    )

    target_rank = int(reduce_result.get("target_rank", -1))
    rank = int(reduce_result.get("rank_mod_p", -1))
    nullity = target_rank - rank
    require(target_rank >= 0 and rank >= 0 and nullity >= 0, "invalid rank/nullity values")

    if reduce_result.get("status") == "full_rank_mod_p":
        require(verification_item.get("status") == "verified_full_rank_certificate", "full-rank verification status mismatch")
        require(reduce_result.get("certificate_status") == "selected_minor_certified", "certificate status mismatch")
        require(reduce_result.get("certificate_complete") is True, "certificate is incomplete")
        require(reduce_result.get("full_rank_mod_p") is True, "full_rank_mod_p is not true")
        require(rank == target_rank, "full-rank result has rank != target_rank")
        require(verification_item.get("expected_matrix_sha256") == reduce_result.get("selected_minor_matrix_sha256"), "minor hash mismatch")
        require(
            str(verification_item.get("expected_determinant_mod_p")) == str(reduce_result.get("selected_minor_determinant_mod_p")),
            "minor determinant mismatch",
        )
        if args.require_second_prime:
            second = verification_item.get("second_prime_check")
            require(isinstance(second, dict) and second.get("nonzero") is True, "second-prime selected minor is zero or missing")
    elif reduce_result.get("status") == "trivial_zero_rank":
        require(verification_item.get("status") == "verified_trivial_zero", "trivial-zero verification status mismatch")
        require(target_rank == 0 and rank == 0 and nullity == 0, "trivial-zero rank/nullity mismatch")
    else:
        raise RuntimeError(f"c{cdegree} is not a verified publishable result: {reduce_result.get('status')}")

    selected_rows = reduce_result.get("selected_rows", [])
    selected_columns = reduce_result.get("selected_columns", [])
    require(len(selected_rows) == rank, "selected row count does not match rank")
    require(len(selected_columns) == rank, "selected column count does not match rank")
    require(
        selected_indices(selected_rows, "row_index") == verification_item.get("selected_rows", []),
        "selected rows disagree with verification",
    )
    require(
        selected_indices(selected_columns, "w_index") == verification_item.get("selected_columns", []),
        "selected columns disagree with verification",
    )

    source_digest_by_chern = manifest.get("source_basis_digest_by_chern", {})
    source_digest = reduce_result.get("source_basis_digest")
    require(source_digest == source_digest_by_chern.get(str(cdegree)), "source basis digest mismatch")
    require(reduce_result.get("w_basis_digest") == manifest.get("w_basis_digest"), "W basis digest mismatch")

    commands = {
        "manifest": args.manifest_command,
        "worker": args.worker_command,
        "reduce": args.reduce_command,
        "verify_certificate": args.verify_command,
    }
    require(all(commands.values()), "all exact command strings are required")

    raw_artifacts = {
        "manifest": {
            "label": args.manifest_label,
            "sha256": manifest_sha,
        },
        "reduce": {
            "label": args.reduce_label,
            "sha256": reduce_sha,
        },
        "verification": {
            "label": args.verification_label,
            "sha256": verification_sha,
        },
    }
    if args.run_ledger:
        raw_artifacts["run_ledger"] = {
            "label": args.run_ledger_label,
            "sha256": sha256_file(args.run_ledger),
        }
    if args.run_provenance:
        raw_artifacts["run_provenance"] = {
            "label": args.run_provenance_label,
            "sha256": sha256_file(args.run_provenance),
        }

    certificate = {
        "chern_degree": cdegree,
        "status": "verified",
        "rank": rank,
        "nullity": nullity,
        "target_rank": target_rank,
        "prime": str(manifest["prime"]),
        "second_prime": verification.get("second_prime"),
        "source_dimension": target_rank,
        "w_basis_dimension": int(manifest.get("w_basis_dimension", -1)),
        "selected_rows": selected_rows,
        "selected_columns": selected_columns,
        "selected_minor_determinant_mod_p": reduce_result.get("selected_minor_determinant_mod_p"),
        "selected_minor_matrix_sha256": reduce_result.get("selected_minor_matrix_sha256"),
        "manifest_sha256": manifest_sha,
        "reduce_output_sha256": reduce_sha,
        "verification_output_sha256": verification_sha,
        "source_file_sha256": manifest.get("source_file_sha256", {}),
        "source_basis_digest": source_digest,
        "w_basis_digest": manifest.get("w_basis_digest"),
        "shard_mode": manifest.get("shard_mode"),
        "commands": commands,
        "raw_artifacts": raw_artifacts,
        "elapsed_seconds": {
            "manifest": manifest.get("elapsed_seconds"),
            "workers_total": args.workers_elapsed_seconds,
            "reduce": reduce_payload.get("elapsed_seconds"),
            "verify_certificate": verification.get("elapsed_seconds"),
        },
    }
    if args.include_absolute_artifact_paths:
        certificate["artifact_paths"] = {
            "manifest": os.path.abspath(args.manifest),
            "reduce": os.path.abspath(args.reduce),
            "verification": os.path.abspath(args.verification),
        }
    return certificate


def write_result_readme(folder: str, certificate: Dict[str, Any]) -> None:
    rows = ", ".join(item["row_name"] for item in certificate["selected_rows"]) or "(none)"
    cols = ", ".join(item["w_name"] for item in certificate["selected_columns"]) or "(none)"
    command_lines = "\n".join(
        f"- `{name}`: `{command}`"
        for name, command in certificate["commands"].items()
    )
    text = f"""# Chern Degree {certificate['chern_degree']}

Status: verified

| Field | Value |
|---|---|
| Rank | {certificate['rank']} |
| Nullity | {certificate['nullity']} |
| Source dimension | {certificate['source_dimension']} |
| W-basis dimension | {certificate['w_basis_dimension']} |
| Primary prime | {certificate['prime']} |
| Second prime | {certificate.get('second_prime') or 'not used'} |
| Selected rows | {rows} |
| Selected columns | {cols} |
| Certificate | [certificate.json](certificate.json) |
| Manifest SHA256 | `{certificate['manifest_sha256']}` |
| Reduce SHA256 | `{certificate['reduce_output_sha256']}` |
| Verification SHA256 | `{certificate['verification_output_sha256']}` |

## Exact Commands

{command_lines}
"""
    with open(os.path.join(folder, "README.md"), "w", encoding="utf-8") as handle:
        handle.write(text)


def update_root_status(repo_root: str, certificate: Dict[str, Any]) -> None:
    path = os.path.join(repo_root, "README.md")
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    cdegree = int(certificate["chern_degree"])
    prefix = f"| {cdegree} |"
    replacement = (
        f"| {cdegree} | [c{cdegree}](c{cdegree}/) | verified | "
        f"{certificate['rank']} | {certificate['nullity']} | "
        f"[certificate.json](c{cdegree}/certificate.json) |\n"
    )
    replaced = False
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            lines[idx] = replacement
            replaced = True
            break
    require(replaced, f"could not find c{cdegree} row in root README")
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chern-degree", type=int, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--reduce", required=True)
    parser.add_argument("--verification", required=True)
    parser.add_argument("--repo-root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    parser.add_argument("--manifest-command", required=True)
    parser.add_argument("--worker-command", required=True)
    parser.add_argument("--reduce-command", required=True)
    parser.add_argument("--verify-command", required=True)
    parser.add_argument("--workers-elapsed-seconds", type=float, default=None)
    parser.add_argument("--require-second-prime", dest="require_second_prime", action="store_true", default=True)
    parser.add_argument("--no-require-second-prime", dest="require_second_prime", action="store_false")
    parser.add_argument("--require-final-reduce", dest="require_final_reduce", action="store_true", default=True)
    parser.add_argument("--allow-in-progress-reduce", dest="require_final_reduce", action="store_false")
    parser.add_argument("--manifest-label", default="raw manifest artifact, not committed")
    parser.add_argument("--reduce-label", default="raw reduce artifact, not committed")
    parser.add_argument("--verification-label", default="raw verification artifact, not committed")
    parser.add_argument("--run-ledger", default="")
    parser.add_argument("--run-ledger-label", default="raw run ledger, not committed")
    parser.add_argument("--run-provenance", default="")
    parser.add_argument("--run-provenance-label", default="raw run provenance, not committed")
    parser.add_argument("--include-absolute-artifact-paths", action="store_true")
    parser.add_argument("--no-update-root-readme", dest="update_root_readme", action="store_false", default=True)
    args = parser.parse_args()

    certificate = validate_and_extract(args)
    folder = os.path.join(os.path.abspath(args.repo_root), f"c{int(args.chern_degree)}")
    os.makedirs(folder, exist_ok=True)
    certificate_path = os.path.join(folder, "certificate.json")
    atomic_json_dump(certificate_path, certificate)
    write_result_readme(folder, certificate)
    if args.update_root_readme:
        update_root_status(os.path.abspath(args.repo_root), certificate)
    print(json.dumps({"status": "wrote", "certificate": certificate_path}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
