# Separate geometry bounds in native surface proposals

`surface-vector` fitting now protects its baseline worst geometry-proxy error
separately from the contact objective. This follows a retained continuation
where contact improvements repeatedly worsened full mesh penetration. Original
source motion/contact limits, surface policy and geometry policy remain fixed.

## Observed tradeoff

Four further primary iterations resume the individually guarded 37-iteration
clip. All four retain no step; their final exports exactly equal the starting
exports. Replay checks all 52 control vectors and 104 byte-exact exports,
original cap arrays, the complete 459,121-row native population and all contact/
geometry decisions. Independent scalar incident-face accumulation verifies all
52 saved contact samples. The replay rehashes 937 bound files.

Candidate `2-restore-2` passes all original native constraints and improves all
three contact conditions. Crossings drop 482 -> 458 and deep vertices 389 -> 378,
but maximum penetration grows 20.4945 -> 20.8548 mm. It is correctly rejected.
Evaluating all 6,901 baseline fixed witnesses on this decoded candidate shows
geometry-proxy maximum growing 4.19889 -> 4.38235, while the contact maximum
falls 4.67541 -> 4.38218. The combined worst objective improves despite worsening
geometry. This diagnosis evaluates actual exports and fixed proxies; it does
not independently replay the affine solver.

Read-only rig-region classification of the starting audit places 455 of its
482 crossings within both declared left-hand subtrees and 27 in one subtree
with another region. The forearm/blended seam also contributes triangle
witnesses. Both deepest vertices lie in these hand subtrees; the authored
source contact vertex is the deepest A vertex. All six plane failures occur at
foot-weighted vertices. These are hierarchy/weight labels, not anatomical palm
annotations. Full meshes remain included in correction and acceptance.

## Proposal bound and decoded checks

`scripts/native_geometry_norms.py` duplicates the complete geometry block into
the protected proposal prefix, after the original native rows and any contact
guards. Each separate guard cap is its original proxy cap plus the baseline
worst positive geometry residual times its scale. This preserves the maximum
proxy error independently of a larger contact objective. Passing geometry uses
its existing caps. The original geometry rows remain in the soft objective;
no authored cap, source epoch or final quality threshold is replaced.

Base witnesses use decoded poses. Continuous differences guide proposals only.
Restoration reconstructs the same fixed-axis vectors from the actual exported
poses and may tighten proposal margins after an overrun. Norm encoding and its
stored offsets are retained to avoid comparing differently rounded scalar
expressions at an active bound. Probe records include
`maximum_geometry_proxy_guard_excess`; optimizer metadata includes
`worst_geometry_proxy_bounded_in_proposal`.

These guards are local search guidance. Witnesses and their axes change with
motion; passing them is not a collision certificate. Actual acceptance still
requires every original point/motion condition, each individual contact guard,
aggregate contact checks and the complete decoded geometry score. Geometry
counts can still trade against reduced maximum depth under that existing score.
Full object correction remains unsupported by this mode.

## Retained correction after the bound

Two fresh iterations resume the exact unchanged clip retained by the failed
four-iteration continuation. Both retain restored full steps: the first needs
three restoration attempts and the second one. Unrestored proposals violate
native conditions and the new proxy bound and remain rejected. The initial
proxy bound is 4.19889 with 6,901 geometry rows; the second iteration uses
4.17049 with 6,885 rows. Source caps, point references, scene placement and
three geometry clocks remain unchanged.

| Measurement | Start | After two retained steps |
| --- | ---: | ---: |
| Contact point separation | 24.8464 mm | 24.2313 mm |
| Maximum partner containment depth | 20.4945 mm | 20.3363 mm |
| Proper surface crossings | 482 | 471 |
| Vertices deeper than 5 mm | 389 | 396 |
| Failed sampled geometry conditions | 7 | 7 |
| Normal opposition error | 39.1568 degrees | 38.6099 degrees |
| Source facing-side projection | -23.8770 mm | -23.0875 mm |
| Target facing-side projection | -20.8896 mm | -20.8030 mm |
| Maximum positive surface residual | 4.67541 | 4.51750 |
| Squared positive surface residual sum | 40.94513 | 39.24582 |

All original point/motion conditions and individual contact guards pass.
Surface policy and full geometry still fail; originals remain selected.
Increased deep-vertex population remains visible. Cumulative primary count 43
includes the four rejected iterations and does not mean 43 accepted steps.
No stage rise, weight conditioning, new generated seed or training is applied.
The result establishes bounded development progress on one interaction, not
realistic motion, continuous collision freedom, engine playback or human approval.

Local evidence is retained under
`reports/native-oriented-surface-fit-development-v3/`,
`reports/native-oriented-surface-fit-development-v4/`,
`reports/native-surface-regions-development-v2/` and
`reports/native-geometry-tradeoff-development-v1/`. Bulk character/model/study
payloads remain excluded from GitHub. Broad action, object/partner, rig, editing,
style, transition and release validation requirements remain open.

The guarded replay checks all eight saved control vectors and sixteen byte-exact
exports, original cap arrays, complete contact/native/geometry results, and every
acceptance decision. It reconstructs both proxy models and all six recorded
decoded overruns, independently checks eight scalar normal/side/error samples,
and rehashes 559 files. Shared pose and geometry implementations remain used.
All 468 focused model-free regressions pass, including 14 new geometry-bound,
direction, restoration and full-mesh-authority cases. Public CI includes them on
Linux and Windows. Local test receipts remain under
`reports/native-geometry-guards-validation-v1/`. No release gate or formal
held-out trial changes.
