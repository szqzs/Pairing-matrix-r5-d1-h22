#!/usr/bin/env python
"""Export the pairing columns actually computed for a verified milestone.

The rank certificates for c16/c17/c18 do not contain full pairing matrices:
they contain enough columns to certify the rank.  This helper publishes that
computed support honestly.  It refuses to write unless the final verification
artifact passed and matches the supplied manifest/reduce hashes.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from typing import Any, Dict, List


SCHEMA_VERSION = 1


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def manifest_namespace(manifest_sha256: str) -> str:
    return f"manifest_{manifest_sha256[:16]}"


def vector_digest(vector: List[int], prime: int) -> str:
    return sha256_json([int(value) % prime for value in vector])


def validate_verified_inputs(
    cdegree: int,
    manifest: Dict[str, Any],
    reduce_payload: Dict[str, Any],
    verification: Dict[str, Any],
    manifest_sha: str,
    reduce_sha: str,
) -> Dict[str, Any]:
    require(verification.get("status") == "passed", "verification artifact did not pass")
    require(reduce_payload.get("status") == "passed", "reduce artifact did not pass")
    require(verification.get("manifest_sha256") == manifest_sha, "verification manifest hash mismatch")
    require(reduce_payload.get("manifest_sha256") == manifest_sha, "reduce manifest hash mismatch")
    require(verification.get("reduce_output_sha256") == reduce_sha, "verification reduce hash mismatch")
    require(str(reduce_payload.get("prime")) == str(manifest.get("prime")), "prime mismatch")
    require(str(verification.get("prime")) == str(manifest.get("prime")), "verification prime mismatch")

    matches = [
        item for item in reduce_payload.get("results", [])
        if int(item.get("chern_degree", -1)) == cdegree
    ]
    require(len(matches) == 1, f"expected exactly one reduce result for c{cdegree}")
    result = matches[0]
    require(
        result.get("status") in {"full_rank_mod_p", "trivial_zero_rank"},
        f"reduce result for c{cdegree} is not verified rank/trivial-zero: {result.get('status')}",
    )
    require(
        any(
            int(item.get("chern_degree", -1)) == cdegree and item.get("passed") is True
            for item in verification.get("verifications", [])
        ),
        f"missing passed verification record for c{cdegree}",
    )
    require(
        all(item.get("status") != "skipped_uncertified_result" for item in verification.get("verifications", [])),
        "verification artifact contains skipped uncertified results",
    )
    return result


def read_task_bundle(
    *,
    path: str,
    manifest: Dict[str, Any],
    manifest_sha: str,
    task: Dict[str, Any],
    source_digest: str,
    w_digest: str,
    row_count: int,
    prime: int,
) -> List[Dict[str, Any]]:
    payload = load_json(path)
    require(payload.get("status") == "passed", f"task bundle did not pass: {path}")
    expected = {
        "kind": "jk_only_task_shard_bundle",
        "manifest_sha256": manifest_sha,
        "prime": manifest["prime"],
        "task_index": int(task["task_index"]),
        "chern_degree": int(task["chern_degree"]),
        "column_offset": int(task["column_offset"]),
        "wave_index": int(task["wave_index"]),
        "row_count": row_count,
        "source_file_sha256": manifest["source_file_sha256"],
        "source_basis_digest": source_digest,
        "w_basis_digest": w_digest,
        "w_indices": [int(w_idx) for w_idx in task["w_indices"]],
    }
    for key, value in expected.items():
        require(payload.get(key) == value, f"task bundle metadata mismatch for {key}: {path}")
    columns = payload.get("columns", [])
    require(len(columns) == len(task["w_indices"]), f"task bundle column count mismatch: {path}")
    expected_w_indices = {int(w_idx) for w_idx in task["w_indices"]}
    seen_w_indices = set()
    out: List[Dict[str, Any]] = []
    for column in columns:
        w_idx = int(column["w_index"])
        require(w_idx in expected_w_indices, f"task bundle contains unexpected w{w_idx}: {path}")
        require(w_idx not in seen_w_indices, f"task bundle repeats w{w_idx}: {path}")
        seen_w_indices.add(w_idx)
        vector = [int(value) % prime for value in column["column_vector_mod_p"]]
        require(len(vector) == row_count, f"column vector length mismatch for w{w_idx}: {path}")
        require(vector_digest(vector, prime) == column.get("column_vector_sha256"), f"column hash mismatch for w{w_idx}")
        out.append({
            "w_index": w_idx,
            "w_name": column["w_name"],
            "task_index": int(task["task_index"]),
            "shard_path_label": f"task bundle {int(task['task_index'])}",
            "shard_file_sha256": sha256_file(path),
            "row_count": row_count,
            "nonzero_entries": int(column.get("nonzero_entries", sum(1 for value in vector if value))),
            "column_vector_sha256": column["column_vector_sha256"],
            "column_vector_mod_p": [str(value) for value in vector],
        })
    require(seen_w_indices == expected_w_indices, f"task bundle is missing expected columns: {path}")
    return out


def source_rows_from_source_code(args: argparse.Namespace, manifest: Dict[str, Any], cdegree: int, expected_digest: str) -> List[Dict[str, Any]]:
    source_code_dir = os.path.abspath(args.source_code_dir)
    require(os.path.isdir(source_code_dir), f"source code dir does not exist: {source_code_dir}")
    old_path = list(sys.path)
    try:
        sys.path.insert(0, source_code_dir)
        for name in ("basis", "fast_modular", "jk_formula", "modular_rank_search"):
            sys.modules.pop(name, None)
        import basis  # type: ignore
        import modular_rank_search as mrs  # type: ignore

        source_by_chern, _raw_counts, _meta = basis.independent_basis_by_chern(
            5,
            int(manifest["source_degree"]),
            [cdegree],
        )
        source_basis = source_by_chern.get(cdegree, ())
        require(mrs.basis_digest(source_basis) == expected_digest, "source row basis digest mismatch")
        return [
            {"row_index": int(row_idx), "row_name": item.name}
            for row_idx, item in enumerate(source_basis)
        ]
    finally:
        sys.path[:] = old_path


def read_column_shard(
    *,
    path: str,
    manifest: Dict[str, Any],
    manifest_sha: str,
    cdegree: int,
    source_digest: str,
    w_digest: str,
    row_count: int,
    prime: int,
) -> Dict[str, Any]:
    payload = load_json(path)
    require(payload.get("status") == "passed", f"column shard did not pass: {path}")
    require(payload.get("kind") == "jk_only_column_shard", f"unexpected shard kind: {path}")
    require(payload.get("manifest_sha256") == manifest_sha, f"manifest hash mismatch: {path}")
    require(int(payload.get("chern_degree", -1)) == cdegree, f"chern degree mismatch: {path}")
    require(payload.get("source_file_sha256") == manifest["source_file_sha256"], f"source hash mismatch: {path}")
    require(payload.get("source_basis_digest") == source_digest, f"source basis digest mismatch: {path}")
    require(payload.get("w_basis_digest") == w_digest, f"W basis digest mismatch: {path}")
    vector = [int(value) % prime for value in payload["column_vector_mod_p"]]
    require(len(vector) == row_count, f"column vector length mismatch: {path}")
    require(vector_digest(vector, prime) == payload.get("column_vector_sha256"), f"column hash mismatch: {path}")
    return {
        "w_index": int(payload["w_index"]),
        "w_name": payload["w_name"],
        "task_index": None,
        "shard_path_label": f"column shard w{int(payload['w_index'])}",
        "shard_file_sha256": sha256_file(path),
        "row_count": row_count,
        "nonzero_entries": int(payload.get("nonzero_entries", sum(1 for value in vector if value))),
        "column_vector_sha256": payload["column_vector_sha256"],
        "column_vector_mod_p": [str(value) for value in vector],
    }


def collect_columns(args: argparse.Namespace) -> Dict[str, Any]:
    cdegree = int(args.chern_degree)
    manifest = load_json(args.manifest)
    reduce_payload = load_json(args.reduce)
    verification = load_json(args.verification)
    manifest_sha = sha256_file(args.manifest)
    reduce_sha = sha256_file(args.reduce)
    verification_sha = sha256_file(args.verification)
    result = validate_verified_inputs(cdegree, manifest, reduce_payload, verification, manifest_sha, reduce_sha)

    prime = int(manifest["prime"])
    row_count = int(result.get("target_rank", 0))
    source_digest = manifest.get("source_basis_digest_by_chern", {}).get(str(cdegree))
    require(result.get("source_basis_digest") == source_digest, "source basis digest mismatch")
    w_digest = manifest["w_basis_digest"]
    require(result.get("w_basis_digest") == w_digest, "W basis digest mismatch")
    source_rows = source_rows_from_source_code(args, manifest, cdegree, source_digest)
    require(len(source_rows) == row_count, "source row label count mismatch")

    namespace = manifest_namespace(manifest_sha)
    shard_root = os.path.join(os.path.abspath(args.shard_dir), namespace)
    shard_mode = manifest.get("shard_mode")
    columns: List[Dict[str, Any]] = []
    tasks = [
        task for task in manifest.get("tasks", [])
        if int(task.get("chern_degree", -1)) == cdegree
    ]
    if row_count == 0:
        tasks = []
    elif shard_mode == "task":
        for task in tasks:
            path = os.path.join(shard_root, "task_bundles", f"task{int(task['task_index'])}.json")
            if os.path.exists(path):
                columns.extend(read_task_bundle(
                    path=path,
                    manifest=manifest,
                    manifest_sha=manifest_sha,
                    task=task,
                    source_digest=source_digest,
                    w_digest=w_digest,
                    row_count=row_count,
                    prime=prime,
                ))
    elif shard_mode == "column":
        for task in tasks:
            for w_idx in task["w_indices"]:
                path = os.path.join(shard_root, f"c{cdegree}", f"w{int(w_idx)}.json")
                if os.path.exists(path):
                    columns.append(read_column_shard(
                        path=path,
                        manifest=manifest,
                        manifest_sha=manifest_sha,
                        cdegree=cdegree,
                        source_digest=source_digest,
                        w_digest=w_digest,
                        row_count=row_count,
                        prime=prime,
                    ))
    else:
        raise RuntimeError(f"unknown shard mode: {shard_mode}")

    seen = set()
    unique_columns: List[Dict[str, Any]] = []
    for column in sorted(columns, key=lambda item: int(item["w_index"])):
        w_idx = int(column["w_index"])
        require(w_idx not in seen, f"duplicate computed column w{w_idx}")
        seen.add(w_idx)
        unique_columns.append(column)

    selected_w = [int(item["w_index"]) for item in result.get("selected_columns", [])]
    selected_set = set(selected_w)
    for column in unique_columns:
        column["used_in_rank_certificate"] = int(column["w_index"]) in selected_set

    w_dim = int(manifest.get("w_basis_dimension", -1))
    payload = {
        "kind": "jk_only_computed_pairing_columns_mod_p",
        "schema_version": SCHEMA_VERSION,
        "status": "verified_support_export",
        "chern_degree": cdegree,
        "scope": "computed_shards_only",
        "note": "These are the pairing columns actually computed for the certificate, not necessarily the full pairing matrix.",
        "prime": str(prime),
        "source_dimension": row_count,
        "w_basis_dimension": w_dim,
        "source_rows": source_rows,
        "computed_column_count": len(unique_columns),
        "computed_entry_count": row_count * len(unique_columns),
        "full_w_basis_covered": len(unique_columns) == w_dim,
        "selected_certificate_column_count": len(selected_w),
        "selected_certificate_w_indices": selected_w,
        "manifest_sha256": manifest_sha,
        "reduce_output_sha256": reduce_sha,
        "verification_output_sha256": verification_sha,
        "source_file_sha256": manifest.get("source_file_sha256", {}),
        "source_basis_digest": source_digest,
        "w_basis_digest": w_digest,
        "shard_mode": shard_mode,
        "shard_namespace": namespace,
        "columns": unique_columns,
    }
    return payload


def write_payload(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    if path.endswith(".gz"):
        with gzip.open(tmp, "wt", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    else:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    os.replace(tmp, path)


def write_readme(folder: str, payload: Dict[str, Any], filename: str) -> None:
    path = os.path.join(folder, "computed_entries.README.md")
    full_text = "yes" if payload["full_w_basis_covered"] else "no"
    text = f"""# Computed Pairing Entries for c{payload['chern_degree']}

`{filename}` contains the pairing columns actually computed modulo the primary
prime for this certificate.

This is not automatically a full pairing matrix.  For this artifact:

| Field | Value |
|---|---:|
| Source rows | {payload['source_dimension']} |
| W-basis columns | {payload['w_basis_dimension']} |
| Computed columns | {payload['computed_column_count']} |
| Computed entries | {payload['computed_entry_count']} |
| Full W-basis covered | {full_text} |

The column vectors are ordered by source-row index and each column records its
`w_index`, `w_name`, vector hash, and whether it was used in the selected-minor
rank certificate.
"""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chern-degree", type=int, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--reduce", required=True)
    parser.add_argument("--verification", required=True)
    parser.add_argument("--shard-dir", required=True)
    parser.add_argument("--repo-root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    parser.add_argument(
        "--source-code-dir",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "jk_only_v5_c16_frozen")),
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    payload = collect_columns(args)
    folder = os.path.join(os.path.abspath(args.repo_root), f"c{int(args.chern_degree)}")
    output = args.output or os.path.join(folder, "computed_columns_mod_p.json.gz")
    write_payload(output, payload)
    write_readme(folder, payload, os.path.basename(output))
    print(json.dumps({
        "status": "wrote",
        "path": output,
        "computed_column_count": payload["computed_column_count"],
        "full_w_basis_covered": payload["full_w_basis_covered"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
