# Whole-clip storage search and articulated clearance proposal

Two separate experiments retain the original source, 63 controls, 22 cm joint
displacement and root translation bounds, 30-degree arm limits, clocks, rate
caps and 5 mm floor gate. They do not replace one another's acceptance checks.

## Wider stored-component prefix

The paired search continues from the freshly replayed 40-failure anchor with
eight stages and up to 64 probes per stage. It uses all eight stages, exports
45 complete native probes and tests 44 changed neighbors. Partial best reaches
38 failures, repairing nine initially failed rows but introducing seven new
failures. Root acceleration stays passing; worst normalized excess decreases
to 3.3691370687498273e-6 and secondary merit to 5.043187335476182e-11. The returned
asset remains the byte-identical 40-failure seed. All 2,017 best floor samples
still fail at 257.398701 mm peak.

The worker completes at 286.375 seconds, with all 300 resource observations
replayed. Separate fresh returned/best reconstruction matches every payload,
world matrix, native row, cap, scale, control, clock and typed continuation;
original caps rebuild identically and every best floor sample reproduces.
All 45 raw probe/array/asset hashes match; other neighbors are not numerically
replayed. This replay shares repository arithmetic, completes at 57.703 seconds
and all 75 resource observations replay. Counts alone conceal the seven new
failures, and no partial anchor is admitted as a repair.

## One-clock articulated pose

At 0.03333333333333333 seconds, the root and the same six arm channels are
optimized against all 1,029 referenced surface vertices, original per-track
norm bounds and all-joint 22 cm displacement bounds. A 4.5 mm proposal target
provides inward room while final acceptance remains 5 mm. SLSQP uses 32
iterations / 1,399 evaluations. Its unscaled result exceeds the displacement
bound by about 2.47e-13 m and is rejected under the strict original gate.

Scaling by 0.999999 yields a valid single pose at **4.500272 mm** floor depth
and **219.999778 mm** maximum joint displacement. Root translation magnitude is
103.901149 mm; the largest local arm rotation is about 14.62 degrees. The
proposal uses permitted channels rather than a frozen-leg or root-bound
infeasibility assumption. Solver success alone does not determine acceptance.
The study completes at 19.187 seconds; all 37 resource observations replay.

Constant source-relative offsets across the clip reproduce this one pose with
maximum world-matrix element discrepancy 1.069e-15. However, the complete
107,895-row intended-curve audit finds **499 failures**. The pose is not a
temporal feasibility certificate.

## Actual serialized clip

The first clip study freshly verifies the pose and intended rows and writes a
GLB, but fails on an incorrect `value` argument to the boundary audit API.
Its worker, failed guard and export are retained; all 35 observations replay.
The next phase uses the correct API, reconstructs the export byte-for-byte,
passes its native authoring/protection audit, rechecks original cap arrays and
freshly measures every decoded native row and original floor sample. It does
not repeat pose optimization. The saved intended rows are bound to the pose and
preceding fresh replay, not newly recomputed again in this resumed phase.

| Complete sampled result | Stored-component anchor | Articulated proposal |
| --- | ---: | ---: |
| Native failures | 38 (partial best) | 503 |
| Intended failures | 0 | 499 |
| Failed floor times | 2,017 / 2,017 | 174 / 2,017 |
| Peak floor penetration | 257.398701 mm | 27.783575 mm |

All original authoring bounds/protection checks pass for the proposal export,
but native and geometry acceptance both fail. It remains a rejected proposal.
The resumed phase completes at 27.454 seconds; all 45 observations replay.
Full floor checks include original triangle topology and sampled degeneracy;
self-collision, continuous collision, engine fidelity, support/dynamics and
human motion quality remain unverified.

Passive complete-row inspection distinguishes the remaining work:

| Condition group | Intended failures | Serialized failures |
| --- | ---: | ---: |
| Track bounds | 0 | 0 |
| Joint displacement | 356 | 356 |
| Position speed | 102 | 102 |
| Position acceleration | 27 | 27 |
| Angular speed | 10 | 10 |
| Angular acceleration | 4 | 8 |

This requires temporal correction of the intended curve before treating it as
a stored-component problem. The maximum intended joint displacement excess is
13.710240% of the 22 cm bound. No original cap or floor criterion is relaxed.

Raw evidence remains under `reports/crawl-paired-wide-v1`,
`reports/crawl-paired-wide-replay-v1`, `reports/crawl-articulated-pose-v1`,
`reports/crawl-articulated-clip-v1`, `reports/crawl-articulated-clip-v2` and
`reports/articulated-failure-groups-v1`. No new model or training run is involved.

## Hosted verification and next decision

The complete focused workflow at `2c998a2` passes all eight jobs on Windows and
Linux: 451 + 401 contact tests, 35 lineage and 32 packaging tests, totaling
919 Python checks per OS, 33 subtests and offline editor checks. Windows contact
shards finish in 424.69 and 103.20 seconds instead of the preceding timeout.
The larger full-source workflow remains separate; no full-suite pass is inferred.

Next restore the articulated intended curve's joint/rate conditions while
preserving improved clearance, then verify serialization and all original floor
times. Other arbitrary actions, scene/partner constraints, rig transfer,
style/editing, transitions/imports, semantics and human cleanup/release evidence
remain required under the same whole-project goal. These are development
failure/proposal studies, not reserved held-out or human approval evidence.
