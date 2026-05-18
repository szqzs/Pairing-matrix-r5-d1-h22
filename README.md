# Rank 5, Genus 2 JK Pairing Records in Ordinary Degree 22

This repository is the clean public record for Jeffrey-Kirwan pairing
computations in ordinary degree 22 for rank 5, genus 2, determinant degree 1.

Rows are Sp-invariant source classes of fixed Chern degree.  Columns are the
Sp-invariant `W26` test basis.  Entries are Jeffrey-Kirwan pairings.  For the
full-rank degrees, the proof object is a verified nonzero selected minor modulo
the recorded prime, with a second-prime consistency check.  For `c12`, the
target object is different: a corank-one modular relation certificate, followed
later by exact rational reconstruction.

For a guided reading path, see [How to read this repository](docs/HOW_TO_READ.md).

## Status

In this table, `verified` means a verified modular certificate over the
recorded prime(s), and `Nullity` means source-side/left nullity.  `Full W?`
refers to the committed matrix-column export, not to whether the rank
certificate is complete.

| Chern degree | Folder | Status | Rank | Nullity | Computed W columns | Full W? | Certificate |
|---:|---|---|---:|---:|---:|:---:|---|
| 11 | [c11](c11/) | verified | 7 | 0 | 8/1039 | no | [certificate.json](c11/certificate.json) |
| 12 | [c12](c12/) | pending relation | TBD | TBD | TBD | TBD | pending |
| 13 | [c13](c13/) | pending | TBD | TBD | TBD | TBD | pending |
| 14 | [c14](c14/) | pending | TBD | TBD | TBD | TBD | pending |
| 15 | [c15](c15/) | pending | TBD | TBD | TBD | TBD | pending |
| 16 | [c16](c16/) | verified | 53 | 0 | 128/1039 | no | [certificate.json](c16/certificate.json) |
| 17 | [c17](c17/) | verified | 28 | 0 | 64/1039 | no | [certificate.json](c17/certificate.json) |
| 18 | [c18](c18/) | verified | 16 | 0 | 64/1039 | no | [certificate.json](c18/certificate.json) |
| 19 | [c19](c19/) | verified | 7 | 0 | 8/1039 | no | [certificate.json](c19/certificate.json) |
| 20 | [c20](c20/) | verified | 4 | 0 | 8/1039 | no | [certificate.json](c20/certificate.json) |
| 21 | [c21](c21/) | verified | 1 | 0 | 8/1039 | no | [certificate.json](c21/certificate.json) |
| 22 | [c22](c22/) | verified | 1 | 0 | 8/1039 | no | [certificate.json](c22/certificate.json) |

`Computed W columns` records the committed modular columns, not necessarily the
full pairing matrix.  For full-rank certificates, `Full W? = no` is not a
defect: a verified nonzero selected minor is enough to certify the displayed
rank.  The machine-readable version of this table is [summary.json](summary.json).

## Mathematical Scope

The code evaluates the Jeffrey-Kirwan pairing directly from the JK formula,
using the JK variables and conventions recorded in the source documents.  For
each Chern degree `c`, the source rows are the Sp-invariant ordinary-degree-22
classes of Chern degree `c`, and the columns are the Sp-invariant `W26` test
basis.  A matrix entry is the JK pairing of one source row with one test
column.

For full-rank degrees, the certificate is a selected square minor with nonzero
determinant modulo a certified prime, then a direct recomputation of that minor
from the JK evaluator.  A second prime is used as an additional guard against
bad-prime accidents or arithmetic mistakes.

For `c12`, the expected object is different: a corank-one relation line.  The
planned modular certificate will record a nonzero rank-43 minor, a normalized
left kernel vector, and a direct verification that this vector annihilates
every `W26` column modulo the recorded prime.  The separate Higgs-moduli theorem
should be stated separately: it reduces the Higgs relation in `H^22` to the
corresponding invariant Chern-degree-12 candidate line.  Publishing literal
rational coefficients requires an additional reconstruction/exact-verification
artifact.

## Source Code

- [`src/jk_only_v5_c16_frozen`](src/jk_only_v5_c16_frozen/) is the frozen
  source copy used for the verified `c16`, `c17`, and `c18` milestones.
- [`src/jk_only_v5_relation_frozen`](src/jk_only_v5_relation_frozen/) is the
  relation-capable source copy used for the verified `c11`, `c19`, `c20`,
  `c21`, and `c22` milestones, and prepared for the `c12` corank-one
  certificate.

The frozen source folders are intended to be runnable snapshots as well as hash
references.  A reader may either run from the original workspace layout or copy
one frozen folder into a local source tree and run the same scripts there.

## Computed Entries

The files named `computed_columns_mod_p.json.gz` contain the pairing columns
actually computed for a certificate.  They are not automatically full pairing
matrices.  Each degree folder states whether the full `W26` basis was covered.

## Reproduce Locally

To validate the committed publication files without recomputing JK entries:

```bash
python scripts/validate_publication.py --all
```

To recompute a certificate, run from the workspace containing this repository
and the v5 source tree, or from a copy of the appropriate frozen source folder:

```bash
RUN_ROOT="/absolute/path/to/jk_v5_runs/$(date -u +%Y%m%dT%H%M%SZ)"

python sp_invariant_fast_algorithm_v5/jk_only/strict_degree_runner.py run-degree \
  --chern-degree 18 \
  --run-root "$RUN_ROOT" \
  --column-order cheap-probe \
  --columns-per-task 16 \
  --wave-size 64 \
  --task-batch-size 4 \
  --second-prime 1000033 \
  --extract-publication
```

For the c12 relation certificate, use the relation runner after the source has
been reviewed:

```bash
python sp_invariant_fast_algorithm_v5/jk_only/strict_relation_runner.py run-relation \
  --chern-degree 12 \
  --run-root "$RUN_ROOT" \
  --column-order cheap-probe \
  --columns-per-task 16 \
  --wave-size 64 \
  --task-batch-size 4 \
  --second-prime 1000033 \
  --extract-publication
```

## More Details

- [How to read this repository](docs/HOW_TO_READ.md)
- [Result schema](docs/RESULT_SCHEMA.md)
- [Relation verification notes](docs/RELATION_CERTIFICATE.md)
- [Cluster reproduction notes](docs/CLUSTER.md)

## Provenance Notes

Committed certificates preserve the exact commands from the original run, so
some command strings contain absolute local paths.  Use those commands as
provenance records and replace the roots when reproducing on another machine.

The c16/c17/c18 certificates were extracted before the later relation-specific
publication helpers were added.  Their computational source is frozen in
`src/jk_only_v5_c16_frozen/`; later extractor script changes do not change the
recorded selected-minor certificates.
