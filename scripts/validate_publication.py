#!/usr/bin/env python
"""Lightweight validation for committed publication artifacts.

This script checks the public record: root status table, ``summary.json``,
compact certificates, and committed computed-column exports.  It intentionally
does not recompute JK pairings.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


TABLE_RE = re.compile(
    r"^\|\s*(?P<c>\d+)\s*\|\s*\[(?P<label>c\d+)\]\((?P<folder>c\d+/)\)\s*\|"
    r"\s*(?P<status>[^|]+?)\s*\|\s*(?P<rank>[^|]+?)\s*\|\s*(?P<nullity>[^|]+?)\s*\|"
    r"\s*(?P<computed>[^|]+?)\s*\|\s*(?P<certificate>[^|]+?)\s*\|"
)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not contain a JSON object")
    return payload


def load_gzip_json(path: Path) -> Dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not contain a JSON object")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_readme_table(readme: Path) -> Dict[int, Dict[str, str]]:
    rows: Dict[int, Dict[str, str]] = {}
    for line in readme.read_text(encoding="utf-8").splitlines():
        match = TABLE_RE.match(line)
        if not match:
            continue
        data = {key: value.strip() for key, value in match.groupdict().items()}
        cdegree = int(data["c"])
        require(cdegree not in rows, f"duplicate root README row for c{cdegree}")
        rows[cdegree] = data
    return rows


def expected_table_values(item: Dict[str, Any]) -> Dict[str, str]:
    cdegree = int(item["chern_degree"])
    rank = "TBD" if item.get("rank") is None else str(item["rank"])
    nullity = "TBD" if item.get("nullity") is None else str(item["nullity"])
    if item.get("computed_w_columns") is None:
        computed = "TBD"
    else:
        computed = f"{int(item['computed_w_columns'])}/{int(item['w_basis_dimension'])}"
    if item.get("certificate"):
        cert_path = str(item["certificate"])
        certificate = f"[{Path(cert_path).name}]({cert_path})"
    else:
        certificate = "pending"
    return {
        "status": str(item["status"]),
        "rank": rank,
        "nullity": nullity,
        "computed": computed,
        "certificate": certificate,
    }


def validate_certificate(repo: Path, item: Dict[str, Any]) -> None:
    cdegree = int(item["chern_degree"])
    cert_path = repo / str(item["certificate"])
    require(cert_path.exists(), f"missing certificate for c{cdegree}: {cert_path}")
    cert = load_json(cert_path)
    require(cert.get("status") == "verified", f"certificate for c{cdegree} is not verified")
    for key in ("rank", "nullity", "source_dimension", "w_basis_dimension"):
        require(int(cert[key]) == int(item[key]), f"c{cdegree} certificate {key} mismatch")
    require(str(cert.get("prime")) == str(item["primary_prime"]), f"c{cdegree} primary prime mismatch")
    require(str(cert.get("second_prime")) == str(item["second_prime"]), f"c{cdegree} second prime mismatch")
    require(len(cert.get("selected_rows", [])) == int(item["rank"]), f"c{cdegree} selected row count mismatch")
    require(len(cert.get("selected_columns", [])) == int(item["rank"]), f"c{cdegree} selected column count mismatch")
    snapshot = item.get("source_snapshot")
    if snapshot:
        snapshot_dir = repo / str(snapshot)
        require(snapshot_dir.is_dir(), f"c{cdegree} source snapshot is missing: {snapshot}")
        source_hashes = cert.get("source_file_sha256")
        require(isinstance(source_hashes, dict), f"c{cdegree} source_file_sha256 must be an object")
        for rel_path, expected_hash in source_hashes.items():
            source_path = snapshot_dir / str(rel_path)
            require(source_path.exists(), f"c{cdegree} source snapshot file is missing: {source_path}")
            require(sha256_file(source_path) == expected_hash, f"c{cdegree} source snapshot hash mismatch for {rel_path}")


def validate_computed_columns(repo: Path, item: Dict[str, Any]) -> None:
    cdegree = int(item["chern_degree"])
    path = repo / str(item["computed_columns"])
    require(path.exists(), f"missing computed-column export for c{cdegree}: {path}")
    payload = load_gzip_json(path)
    require(payload.get("status") == "verified_support_export", f"c{cdegree} computed export status mismatch")
    require(int(payload["chern_degree"]) == cdegree, f"c{cdegree} computed export cdegree mismatch")
    require(int(payload["source_dimension"]) == int(item["source_dimension"]), f"c{cdegree} computed export source dimension mismatch")
    require(int(payload["w_basis_dimension"]) == int(item["w_basis_dimension"]), f"c{cdegree} computed export W dimension mismatch")
    require(int(payload["computed_column_count"]) == int(item["computed_w_columns"]), f"c{cdegree} computed column count mismatch")
    require(bool(payload["full_w_basis_covered"]) == bool(item["full_w_basis_covered"]), f"c{cdegree} full-W flag mismatch")
    expected_entries = int(item["source_dimension"]) * int(item["computed_w_columns"])
    require(int(payload["computed_entry_count"]) == expected_entries, f"c{cdegree} computed entry count mismatch")
    require(len(payload.get("columns", [])) == int(item["computed_w_columns"]), f"c{cdegree} column list count mismatch")


def validate_theorem_assisted_candidate(repo: Path, item: Dict[str, Any]) -> None:
    cdegree = int(item["chern_degree"])
    require(cdegree == 12, "theorem-assisted candidate validation is currently only defined for c12")
    path = repo / str(item["certificate"])
    require(path.exists(), f"missing c12 candidate artifact: {path}")
    payload = load_json(path)
    require(payload.get("kind") == "jk_only_theorem_assisted_c12_candidate", "c12 candidate kind mismatch")
    require(payload.get("status") == "theorem_assisted_candidate", "c12 candidate status mismatch")
    require(payload.get("not_full_relation_certificate") is True, "c12 candidate must explicitly say it is not a full certificate")
    for key in ("chern_degree", "rank", "nullity", "source_dimension", "w_basis_dimension"):
        require(int(payload[key]) == int(item[key]), f"c12 candidate {key} mismatch")
    require(str(payload.get("primary_prime")) == str(item["primary_prime"]), "c12 candidate primary prime mismatch")
    require(str(payload.get("second_prime")) == str(item["second_prime"]), "c12 candidate second prime mismatch")
    require(int(payload["loaded_column_check"]["loaded_column_count"]) == int(item["computed_w_columns"]), "c12 loaded column count mismatch")
    require(bool(item["full_w_basis_covered"]) is False, "c12 should not claim full W-basis coverage")
    require(len(payload.get("selected_rows", [])) == int(item["rank"]), "c12 selected row count mismatch")
    require(len(payload.get("selected_columns", [])) == int(item["rank"]), "c12 selected column count mismatch")
    require(len(payload.get("kernel_vector_mod_p", [])) == int(item["source_dimension"]), "c12 kernel vector length mismatch")
    require(payload.get("loaded_column_check", {}).get("passed") is True, "c12 loaded-column check did not pass")
    require(payload.get("rational_reconstruction", {}).get("status") == "passed", "c12 rational reconstruction did not pass")
    hashes = payload.get("hashes", {})
    run_postprocessor_hash = hashes.get("postprocessor_file_sha256")
    if isinstance(run_postprocessor_hash, dict):
        run_postprocessor_hash = run_postprocessor_hash.get("theorem_assisted_c12_candidate.py")
    require(
        hashes.get("frozen_postprocessor_file_sha256") == run_postprocessor_hash,
        "c12 frozen postprocessor hash does not match recorded run postprocessor hash",
    )
    second = payload.get("second_prime_selected_minor_check", {})
    require(second.get("nonzero_selected_minor") is True, "c12 second-prime selected minor was not nonzero")
    comparison = second.get("reconstructed_rational_vector_comparison", {})
    require(comparison.get("passed") is True, "c12 second-prime rational vector comparison did not pass")
    require(payload.get("theorem_assumptions_required"), "c12 theorem assumptions must be recorded")


def validate_degree_readme(repo: Path, item: Dict[str, Any]) -> None:
    cdegree = int(item["chern_degree"])
    readme = repo / f"c{cdegree}" / "README.md"
    require(readme.exists(), f"missing c{cdegree} README")
    text = readme.read_text(encoding="utf-8")
    require(f"# Chern Degree {cdegree}" in text, f"c{cdegree} README title mismatch")
    require(f"Status: {item['status']}" in text, f"c{cdegree} README status mismatch")
    if item.get("source_dimension") is not None:
        require(
            f"| Source dimension | {item['source_dimension']} |" in text,
            f"c{cdegree} README source dimension mismatch",
        )
    if item.get("w_basis_dimension") is not None:
        require(
            f"| W-basis dimension | {item['w_basis_dimension']} |" in text,
            f"c{cdegree} README W dimension mismatch",
        )
    if item.get("status") == "verified":
        require("What This Certifies" in text, f"c{cdegree} README lacks certification summary")
        require("certificate.json" in text, f"c{cdegree} README does not link certificate")
        require("computed_entries.README.md" in text, f"c{cdegree} README does not link computed-column summary")


def validate(repo: Path) -> Dict[str, Any]:
    summary = load_json(repo / "summary.json")
    degrees = summary.get("degrees")
    require(isinstance(degrees, list), "summary.json degrees must be a list")
    require([int(item["chern_degree"]) for item in degrees] == list(range(11, 23)), "summary cdegrees must be exactly 11..22")

    table = parse_readme_table(repo / "README.md")
    require(sorted(table) == list(range(11, 23)), "root README status table must contain exactly c11..c22")

    verified_count = 0
    for item in degrees:
        cdegree = int(item["chern_degree"])
        table_row = table[cdegree]
        expected = expected_table_values(item)
        for key, value in expected.items():
            require(table_row[key] == value, f"root README c{cdegree} {key} mismatch: {table_row[key]!r} != {value!r}")
        validate_degree_readme(repo, item)
        if item.get("status") == "verified":
            verified_count += 1
            validate_certificate(repo, item)
            validate_computed_columns(repo, item)
        elif item.get("certificate_type") == "theorem_assisted_candidate":
            validate_theorem_assisted_candidate(repo, item)
        else:
            if item.get("source_snapshot"):
                require((repo / str(item["source_snapshot"])).is_dir(), f"c{cdegree} listed source snapshot is missing")
            if item.get("certificate"):
                require((repo / str(item["certificate"])).exists(), f"listed certificate for c{cdegree} is missing")

    return {
        "status": "passed",
        "verified_degrees": verified_count,
        "degree_count": len(degrees),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="validate all committed publication artifacts")
    parser.add_argument("--repo-root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    args = parser.parse_args()
    if not args.all:
        parser.error("currently only --all is supported")
    repo = Path(args.repo_root).resolve()
    payload = validate(repo)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
