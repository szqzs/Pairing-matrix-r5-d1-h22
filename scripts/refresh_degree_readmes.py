#!/usr/bin/env python
"""Regenerate concise verified-degree README files from committed artifacts."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not contain a JSON object")
    return payload


def load_gzip_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not contain a JSON object")
    return payload


def bullet_names(items: Iterable[Dict[str, Any]], key: str) -> str:
    lines = [f"- `{item[key]}`" for item in items]
    return "\n".join(lines) if lines else "- none"


def command_lines(commands: Dict[str, str]) -> str:
    return "\n".join(
        f"- `{name}`: `{command}`"
        for name, command in commands.items()
    ) or "- none"


def write_verified_readme(repo: Path, cdegree: int) -> None:
    folder = repo / f"c{cdegree}"
    certificate = load_json(folder / "certificate.json")
    computed = load_gzip_json(folder / "computed_columns_mod_p.json.gz")
    computed_count = computed.get("computed_column_count") if computed else "not exported"
    computed_entries = computed.get("computed_entry_count") if computed else "not exported"
    full_w = (
        "yes" if computed and computed.get("full_w_basis_covered") else
        "no" if computed else
        "not exported"
    )
    selected_rows = bullet_names(certificate.get("selected_rows", []), "row_name")
    selected_columns = bullet_names(certificate.get("selected_columns", []), "w_name")
    commands = command_lines(certificate.get("commands", {}))
    text = f"""# Chern Degree {cdegree}

Status: verified

## What This Certifies

The committed certificate proves a full-rank modular JK pairing result for
Chern degree `{cdegree}`.  The selected `{certificate['rank']} x {certificate['rank']}`
minor has nonzero determinant modulo the primary prime, and the certificate was
checked again at the second prime recorded below.

| Field | Value |
|---|---|
| Rank | {certificate['rank']} |
| Source-side nullity | {certificate['nullity']} |
| Source dimension | {certificate['source_dimension']} |
| W-basis dimension | {certificate['w_basis_dimension']} |
| Computed W columns | {computed_count}/{certificate['w_basis_dimension']} |
| Computed entries | {computed_entries} |
| Full W-basis covered | {full_w} |
| Primary prime | {certificate['prime']} |
| Second prime | {certificate.get('second_prime') or 'not used'} |
| Selected minor size | {certificate['rank']} x {certificate['rank']} |
| Certificate | [certificate.json](certificate.json) |
| Computed-column summary | [computed_entries.README.md](computed_entries.README.md) |
| Computed columns | [computed_columns_mod_p.json.gz](computed_columns_mod_p.json.gz) |
| Manifest SHA256 | `{certificate['manifest_sha256']}` |
| Reduce SHA256 | `{certificate['reduce_output_sha256']}` |
| Verification SHA256 | `{certificate['verification_output_sha256']}` |

The full selected row and column lists, determinant, hashes, and exact command
provenance are in [certificate.json](certificate.json).  The computed-column
export records the modular columns actually computed for this certificate; it
is not a full matrix unless `Full W-basis covered` says `yes`.

<details>
<summary>Selected rows</summary>

{selected_rows}

</details>

<details>
<summary>Selected columns</summary>

{selected_columns}

</details>

<details>
<summary>Exact commands</summary>

{commands}

</details>
"""
    (folder / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("degrees", nargs="*", type=int)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    if args.all:
        degrees = [
            int(path.parent.name[1:])
            for path in sorted(repo.glob("c*/certificate.json"))
            if path.parent.name[1:].isdigit()
        ]
    else:
        degrees = args.degrees
    if not degrees:
        parser.error("supply --all or at least one Chern degree")
    for cdegree in degrees:
        write_verified_readme(repo, cdegree)
    print(json.dumps({"status": "wrote", "degrees": degrees}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
