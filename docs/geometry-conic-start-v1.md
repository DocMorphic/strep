# Direct norm-cone proposal search

The retained 117–119 box-lift window stops at `linear_start_unavailable` after one accepted step. Inspection of its bound proposal records narrows the cause: the second iteration's first two margin attempts each exhaust **64 supporting-plane iterations**, while a third attempt runs out of the shared twenty-second budget. Every recorded primary and secondary LP reports success. The returned linear candidates still miss complete vector-distance checks. This is a search-limit result, not a certificate that the nonlinear pose is infeasible.

The first full-margin attempt ends with minimum normalized vector slack −6.697e−5; the quarter-margin attempt ends at −1.128e−6. Both fail the unchanged −1e−8 proposal check. The third attempt records 26 cuts before its time guard. No zero-margin attempt occurs. An earlier first iteration does find a checked start after 34 cuts. The inspection preserves all archived rows and arrays, without rerunning the native fitter.

## Isolated alternative

`scripts/geometry_conic_start.py` adds an optional standalone proposal helper using the already pinned Clarabel 0.11.1 dependency. It supplies every original affine distance vector directly as a norm cone, alongside all scalar preservation rows and control bounds. No vector or duplicate row is screened out. Both distance and squared-distance representations retain their original cap transformations and full measured-envelope checks.

Worst-first search retains the original scalar worst-violation objective, checked negative squared-violation slope, and 1e−6 epigraph tie allowance. A second phase minimizes that slope within the primary allowance. Every proposed phase is independently evaluated against the original scalar population, every norm ball and clipped bounds. A failed or expired secondary phase can return only its already checked primary proposal. Neither solver status nor its reduced accuracy substitutes for replay. Reports always say `retained=false`, `quality_approved=false` and `release_approved=false`.

The helper **does not replace the default LP fitter**, enter Studio's repair workflow, or retain any pose. A future integration must archive its implementation and proposal decisions and pass the complete nonlinear, tangent, saved-representation, interval and source-preservation gates. Those decisions cannot be inferred from an affine start.

The matrix/sign/cone construction follows Clarabel's [official Python problem format](https://clarabel.org/stable/python/getting_started_py/). Project-specific caps, merit and proposal checks follow the existing fitter; no physical tolerance or resource policy changes.

## Saved native problem evidence

Two fresh guarded workers evaluate the **same full-margin saved problems**, each with 525 controls, 1,068 scalar rows and **2,265 norm vectors**, using the same twenty-second proposal budget. A small derived-finiteness validation added after the first study is checked by a second study; primary and selected controls match exactly across both studies. The completed first implementation is preserved byte-for-byte against its recorded source hash.

| Saved outer iteration | Earlier supporting-plane outcome | Final isolated conic outcome | Measured proposal time |
| --- | --- | --- | --- |
| 1 | Checked start after 34 cuts | Checked primary and secondary | 1.031 s |
| 2 | Two 64-cut limits, then shared time limit | Checked primary and secondary at full margin | 1.266 s |

For iteration two, the selected proposal has minimum scalar slack 2.549e−13, minimum vector slack −1.282e−9, squared-violation slope −105.591 and predicted worst scalar violation 1.291799. These pass the original affine checks. A **separate NoTorch process**, importing no conic helper, reconstructs every primary and selected point with separate NumPy norm/matrix calculations. All bounds and 1,068/2,265 populations pass, including duplicate vector constraints.

The final proposal guard exits zero after 7.281 seconds, with 147,017,728 bytes sampled peak RSS. Its independent replay guard exits zero after 5.188 seconds, with 86,974,464 bytes peak. Independent resource audits verify all nine and seven observations respectively. The isolated numerical jobs use explicit 512/256 MiB estimates plus the existing 600 MiB reserve. **Full native fit/audit estimates remain 2 GiB plus 600 MiB.** These small archived problems do not establish whole-fit speed, memory or motion quality.

## Software checks and outstanding work

**125 checks pass without Torch**: 33 new conic-start tests, 82 existing guarded solver tests and ten callback tests. Coverage includes real small cones, conflicting scalar rows, duplicate vector checks, malformed/mismatched populations, nonfinite derived math, false solver success, clipping, epigraph preservation and shared-budget exhaustion. The suite is included in the explicit source inventory, now **415 Python modules / 41 Node suites**. The test guard and independent resource replay verify eight observations and source bindings.

The second full V8 geometric audit attempt still defers without starting a child: 61 independently verified samples over 60.719 seconds fail the unchanged 2,776,629,248-byte admission requirement. **V7 remains the latest verified retained motion.** The new proposals use V8's saved numerical models as isolated diagnostics; they are not adopted motion states. Complete physical/keyed passes remain 0/62, thirteen windows remain unattempted, and all fourteen release capabilities remain unapproved. Original clips and previews, human-review evidence and held-out data remain unchanged. The full-project goal stays active.

Inputs, inspected traces, both study implementations, proposals, independent calculations, test logs and resource records remain in ignored `reports/geometry-start-diagnosis-v1/` and `v2/`. Final study SHA-256: `565ada9ec4de900e1d4d6d587e94bad8ef22d7fb924f10214511804de9b5df24`. Independent affine replay: `9bde7cdb04f214a162fca2e0077e2a521a48138afc57d8c5e240daa2cfda427e`. Validation summary: `2596f46d2987e6408ef83df5d6fefb9e7098a33803c45e80024011b07cfc4da5`. Continue full native replay when admitted, then test a bound integration through unchanged physical retention gates while broad scene/partner/rig/edit/style/transition/engine and actual developer-review work continues.
