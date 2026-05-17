# Result Folder Schema

Each Chern-degree folder is a verified milestone record, not a raw artifact
dump.

## Required Fields

`README.md` should record:

- Chern degree.
- Status: `pending`, `verified`, or `needs rerun`.
- Rank and nullity.
- Source row dimension and W-basis dimension.
- Selected row names and selected W-column names.
- Exact manifest, worker, reduce, and verification commands.
- Primary prime and optional second prime.
- Elapsed wall time for manifest, workers, reduce, and verification.
- Hashes of the manifest, reduce output, verification output, and source files.
- Hashes or labels for the raw run ledger/provenance, without committing those
  raw files.

`certificate.json` should record only compact certificate data:

```json
{
  "chern_degree": "TBD",
  "status": "TBD",
  "rank": null,
  "nullity": null,
  "prime": "TBD",
  "second_prime": "1000033",
  "selected_rows": [],
  "selected_columns": [],
  "selected_minor_determinant_mod_p": "TBD",
  "selected_minor_matrix_sha256": "TBD",
  "manifest_sha256": "TBD",
  "reduce_output_sha256": "TBD",
  "verification_output_sha256": "TBD",
  "source_file_sha256": {},
  "source_basis_digest": "TBD",
  "w_basis_digest": "TBD",
  "commands": {
    "manifest": "",
    "worker": "",
    "reduce": "",
    "verify_certificate": ""
  },
  "elapsed_seconds": {
    "manifest": null,
    "workers_total": null,
    "reduce": null,
    "verify_certificate": null
  },
  "raw_artifacts": {
    "manifest": {
      "label": "raw manifest artifact, not committed",
      "sha256": "TBD"
    },
    "reduce": {
      "label": "raw final reduce artifact, not committed",
      "sha256": "TBD"
    },
    "verification": {
      "label": "raw final verification artifact, not committed",
      "sha256": "TBD"
    },
    "run_ledger": {
      "label": "raw strict-run ledger, not committed",
      "sha256": "TBD"
    },
    "run_provenance": {
      "label": "raw strict-run provenance, not committed",
      "sha256": "TBD"
    }
  }
}
```

Raw shards, caches, complete matrices, and long logs should remain outside this
repository. Prefer generating `certificate.json` with
`scripts/extract_verified_result.py` rather than editing it by hand.

The extractor rejects non-final reduce artifacts by default. Do not publish
from an intermediate `--allow-in-progress` verification artifact.
