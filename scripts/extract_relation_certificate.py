#!/usr/bin/env python
"""Extract a compact c12-style relation certificate.

This is stricter than the rank extractor because the claim is different:
the computation must exhibit a one-dimensional left kernel of the JK pairing
matrix in the requested Chern degree.  The extractor refuses to write unless
the relation verifier passed, the hashes match, the selected minor is nonzero,
and the published kernel vector annihilates the full W basis in the verifier.
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
    require(11 <= cdegree <= 22, "--chern-degree must be between 11 and 22")

    manifest = load_json(args.manifest)
    relation_reduce = load_json(args.relation_reduce)
    verification = load_json(args.verification)
    manifest_sha = sha256_file(args.manifest)
    relation_reduce_sha = sha256_file(args.relation_reduce)
    verification_sha = sha256_file(args.verification)

    require(relation_reduce.get("status") == "passed", "relation reduce did not pass")
    require(verification.get("status") == "passed", "relation verification did not pass")
    require(relation_reduce.get("manifest_sha256") == manifest_sha, "relation reduce manifest hash mismatch")
    require(verification.get("manifest_sha256") == manifest_sha, "verification manifest hash mismatch")
    require(
        verification.get("relation_reduce_output_sha256") == relation_reduce_sha,
        "verification relation-reduce hash mismatch",
    )
    require(str(relation_reduce.get("prime")) == str(manifest.get("prime")), "primary prime mismatch")
    require(str(verification.get("prime")) == str(manifest.get("prime")), "verification prime mismatch")
    if args.require_second_prime:
        require(verification.get("second_prime") not in {None, "", "0"}, "missing second-prime relation verification")

    manifest_cdegrees = [int(item) for item in manifest.get("chern_degrees", [])]
    require(cdegree in manifest_cdegrees, f"manifest does not contain c{cdegree}")

    result = one_by_cdegree(relation_reduce.get("results", []), cdegree, "relation reduce")
    verification_item = one_by_cdegree(verification.get("verifications", []), cdegree, "verification")
    require(result.get("status") == "relation_kernel_mod_p", "relation reduce did not certify a kernel line")
    require(verification_item.get("status") == "verified_relation_kernel_certificate", "relation verification status mismatch")
    require(verification_item.get("passed") is True, "relation verification record did not pass")

    source_dimension = int(result.get("source_dimension", -1))
    rank = int(result.get("rank_mod_p", -1))
    nullity = int(result.get("nullity_mod_p", -1))
    expected_kernel_dimension = int(result.get("expected_kernel_dimension", -1))
    require(source_dimension >= 0 and rank >= 0 and nullity >= 0, "invalid rank/nullity values")
    require(nullity == expected_kernel_dimension == 1, "this extractor expects a one-dimensional kernel")
    require(rank == source_dimension - 1, "rank/source dimension do not give corank one")
    require(result.get("nonzero_selected_minor_certifies_rank_lower_bound") is True, "rank minor is not certified nonzero")

    kernel_vector = result.get("kernel_vector_mod_p")
    require(isinstance(kernel_vector, list), "missing kernel vector")
    require(len(kernel_vector) == source_dimension, "kernel vector length does not match source dimension")
    coeffs = [int(item.get("coefficient_mod_p", "0")) for item in kernel_vector]
    require(any(coeffs), "kernel vector is zero")
    normalization = result.get("kernel_normalization")
    require(isinstance(normalization, dict), "missing kernel normalization")
    norm_idx = int(normalization.get("normalization_index", -1))
    require(0 <= norm_idx < source_dimension, "kernel normalization index is invalid")
    require(coeffs[norm_idx] == 1, "kernel normalization coefficient is not 1")

    ann = result.get("annihilation_certificate")
    require(isinstance(ann, dict), "missing annihilation certificate")
    require(ann.get("all_w_columns_verified") is True, "relation reduce did not verify all W columns")
    require(int(ann.get("verified_column_count", -1)) == int(result.get("w_basis_dimension", -2)), "annihilation coverage mismatch")
    require(int(ann.get("nonzero_dot_count", -1)) == 0, "nonzero annihilation dots recorded")

    ver_ann = verification_item.get("annihilation_certificate")
    require(isinstance(ver_ann, dict), "missing direct verifier annihilation certificate")
    require(ver_ann.get("all_w_columns_verified") is True, "direct verifier did not verify all W columns")
    require(int(ver_ann.get("nonzero_dot_count", -1)) == 0, "direct verifier found nonzero annihilation dots")
    require(int(ver_ann.get("verified_column_count", -1)) == int(result.get("w_basis_dimension", -2)), "direct verifier coverage mismatch")

    require(
        verification_item.get("expected_matrix_sha256") == result.get("selected_minor_matrix_sha256"),
        "selected minor hash mismatch",
    )
    require(
        verification_item.get("recomputed_matrix_sha256") == result.get("selected_minor_matrix_sha256"),
        "recomputed selected minor hash mismatch",
    )
    require(
        str(verification_item.get("expected_determinant_mod_p")) == str(result.get("selected_minor_determinant_mod_p")),
        "selected minor determinant mismatch",
    )
    require(
        str(verification_item.get("recomputed_determinant_mod_p")) == str(result.get("selected_minor_determinant_mod_p")),
        "recomputed selected minor determinant mismatch",
    )
    require(
        verification_item.get("expected_kernel_vector_sha256") == result.get("kernel_vector_sha256"),
        "kernel vector hash mismatch",
    )
    require(
        verification_item.get("kernel_vector_sha256") == result.get("kernel_vector_sha256"),
        "recomputed kernel vector hash mismatch",
    )
    structural_contract = verification_item.get("structural_contract")
    require(isinstance(structural_contract, dict), "missing verifier structural contract")
    require(structural_contract.get("passed") is True, "verifier structural contract did not pass")
    verifier_contract = verification_item.get("kernel_vector_contract")
    require(isinstance(verifier_contract, dict), "missing verifier kernel vector contract")
    require(verifier_contract.get("passed") is True, "verifier kernel vector contract did not pass")
    if args.require_second_prime:
        second = verification_item.get("second_prime_check")
        require(isinstance(second, dict), "missing second-prime check")
        require(second.get("nonzero_selected_minor") is True, "second-prime selected minor is zero/missing")
        second_contract = second.get("kernel_vector_contract")
        require(isinstance(second_contract, dict), "missing second-prime kernel vector contract")
        require(second_contract.get("passed") is True, "second-prime kernel vector contract did not pass")
        second_ann = second.get("annihilation_certificate")
        require(isinstance(second_ann, dict), "missing second-prime annihilation certificate")
        require(second_ann.get("all_w_columns_verified") is True, "second-prime annihilation failed")

    selected_rows = result.get("selected_rows", [])
    selected_columns = result.get("selected_columns", [])
    require(len(selected_rows) == rank, "selected row count does not match rank")
    require(len(selected_columns) == rank, "selected column count does not match rank")
    require(selected_indices(selected_rows, "row_index") == verification_item.get("selected_rows", []), "selected rows disagree with verification")
    require(selected_indices(selected_columns, "w_index") == verification_item.get("selected_columns", []), "selected columns disagree with verification")

    source_digest_by_chern = manifest.get("source_basis_digest_by_chern", {})
    source_digest = result.get("source_basis_digest")
    require(source_digest == source_digest_by_chern.get(str(cdegree)), "source basis digest mismatch")
    require(result.get("w_basis_digest") == manifest.get("w_basis_digest"), "W basis digest mismatch")

    commands = {
        "manifest": args.manifest_command,
        "worker": args.worker_command,
        "relation_reduce": args.relation_reduce_command,
        "verify_relation_certificate": args.verify_command,
    }
    require(all(commands.values()), "all exact command strings are required")

    raw_artifacts = {
        "manifest": {"label": args.manifest_label, "sha256": manifest_sha},
        "relation_reduce": {"label": args.relation_reduce_label, "sha256": relation_reduce_sha},
        "verification": {"label": args.verification_label, "sha256": verification_sha},
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
        "status": "verified_relation_kernel_modular",
        "claim_type": "jk_left_kernel_line",
        "rank": rank,
        "nullity": nullity,
        "source_dimension": source_dimension,
        "w_basis_dimension": int(result.get("w_basis_dimension", -1)),
        "prime": str(manifest["prime"]),
        "second_prime": verification.get("second_prime"),
        "selected_rows": selected_rows,
        "selected_columns": selected_columns,
        "selected_minor_determinant_mod_p": result.get("selected_minor_determinant_mod_p"),
        "selected_minor_matrix_sha256": result.get("selected_minor_matrix_sha256"),
        "kernel_vector_mod_p": result.get("kernel_vector_mod_p"),
        "kernel_vector_sha256": result.get("kernel_vector_sha256"),
        "kernel_normalization": result.get("kernel_normalization"),
        "annihilation_certificate": ann,
        "second_prime_check": verification_item.get("second_prime_check"),
        "manifest_sha256": manifest_sha,
        "relation_reduce_output_sha256": relation_reduce_sha,
        "verification_output_sha256": verification_sha,
        "source_file_sha256": manifest.get("source_file_sha256", {}),
        "source_basis_digest": source_digest,
        "w_basis_digest": manifest.get("w_basis_digest"),
        "shard_mode": manifest.get("shard_mode"),
        "commands": commands,
        "raw_artifacts": raw_artifacts,
        "mathematical_scope_note": (
            "This certificate proves the corank-one JK pairing statement modulo the recorded prime(s). "
            "An exact rational relation should be published with a separate reconstruction/exact-verification artifact."
        ),
        "elapsed_seconds": {
            "manifest": manifest.get("elapsed_seconds"),
            "relation_reduce": relation_reduce.get("elapsed_seconds"),
            "verify_relation_certificate": verification.get("elapsed_seconds"),
        },
    }
    if args.include_absolute_artifact_paths:
        certificate["artifact_paths"] = {
            "manifest": os.path.abspath(args.manifest),
            "relation_reduce": os.path.abspath(args.relation_reduce),
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

Status: verified modular JK relation certificate

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
| Relation certificate | [relation_certificate.json](relation_certificate.json) |
| Manifest SHA256 | `{certificate['manifest_sha256']}` |
| Relation reduce SHA256 | `{certificate['relation_reduce_output_sha256']}` |
| Verification SHA256 | `{certificate['verification_output_sha256']}` |

The kernel vector is recorded modulo the primary prime.  Publish an exact
rational relation only after adding a reconstruction/exact-verification
artifact.

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
        f"| {cdegree} | [c{cdegree}](c{cdegree}/) | verified relation | "
        f"{certificate['rank']} | {certificate['nullity']} | "
        "TBD | TBD | "
        f"[relation_certificate.json](c{cdegree}/relation_certificate.json) |\n"
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
    parser.add_argument("--relation-reduce", required=True)
    parser.add_argument("--verification", required=True)
    parser.add_argument("--repo-root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    parser.add_argument("--manifest-command", required=True)
    parser.add_argument("--worker-command", required=True)
    parser.add_argument("--relation-reduce-command", required=True)
    parser.add_argument("--verify-command", required=True)
    parser.add_argument("--require-second-prime", dest="require_second_prime", action="store_true", default=True)
    parser.add_argument("--no-require-second-prime", dest="require_second_prime", action="store_false")
    parser.add_argument("--manifest-label", default="raw manifest artifact, not committed")
    parser.add_argument("--relation-reduce-label", default="raw relation reduce artifact, not committed")
    parser.add_argument("--verification-label", default="raw relation verification artifact, not committed")
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
    certificate_path = os.path.join(folder, "relation_certificate.json")
    atomic_json_dump(certificate_path, certificate)
    write_result_readme(folder, certificate)
    if args.update_root_readme:
        update_root_status(os.path.abspath(args.repo_root), certificate)
    print(json.dumps({"status": "wrote", "certificate": certificate_path}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
