# Rejecting incompatible captured-pose targets

Completed 2026-10-11. The [captured-reference transfer](acclaim-rig-transfer-v1.md)
preserves motion and target assets, but both complete clips fail the native-key
floor check. Before running positional correction, this study determines whether
the uniformly scaled capture points can fit the unchanged target skeleton.

At every original frame, mapped target edge lengths and capture edge lengths
are compared separately from their directions. For the mapped Spine2-to-Chest
edge, the target length is 0.592284 m, while scaled capture lengths are
0.177109 m for crawl and 0.161129 m for get-up. This edge's transferred direction
already agrees within approximately `1.5e-6` degrees. Rotating it cannot resolve
the distance difference while its translations and intermediate helpers stay
unchanged. Other edges, including the pelvis/spine branch, do have direction
errors; the diagnostic does not claim that all correspondence errors arise from
lengths or establish which anatomical mapping an animator should choose.

The new [pose preflight](../scripts/pose_length_preflight.py) tests every target
pair whose distance is invariant under the declared rotation edits. Common
ancestor rotations move both endpoints rigidly; rotating an endpoint does not
change its distance to the other endpoint. An editable third pivot affecting
only one endpoint makes the pair unassessed. With fixed distance `L` and desired
distance `D`, the triangle inequality requires:

```text
endpoint_error_a + endpoint_error_b >= abs(L - D)
```

If this exceeds the sum of the two reporting tolerances plus the numerical
guard, that pair excludes the requested targets. Input drift beyond the strict
rigid-rotation tolerance is unassessed. The guard depends on precision, hierarchy
size, coordinate magnitude and measured drift. **Non-exclusion is not proof of
feasibility.** This is a conditional numerical test, not an anatomy, contact,
motion-cap or global-optimality certificate.

[Box](../scripts/bounded_pose_ik.py), [norm-budget](../scripts/bounded_pose_ball_ik.py)
and [continuation](../scripts/bounded_pose_continuation.py) fitters now skip
nonlinear optimization for excluded targets. Box/norm fitting retains the source
pose; continuation retains its existing projected previous-pose fallback. Neither
changes translations, reporting tolerances or edit caps. Reports preserve target
residuals, tested pairs, exclusions and zero optimization evaluations. Solver
budget validation still runs before exclusion; rejected source copies also
preserve signed-zero storage.

All **48 focused checks pass**, including 25 new tests and 23 existing fitter
checks. They exercise editable/common/endpoint pivots, every edit subset of a
forked hierarchy, variable-distance exclusions, roundoff, nonrigid drift,
duplicate-node conflicts, genuine reachable optimization, norm refinement and
continuation fallback. The first run's list/array bug and failed logs remain
archived; corrected intermediate and final source/test versions are hash-bound.

The [frozen fitter protocol](../benchmarks/cmu-pose-fit-preflight-v1.json) runs
all 2,422 native captured poses with 19 mapped rotation permissions, 25-degree
caps, fixed translations/helpers and the same 3-cm point reporting tolerance.
These tolerances are development diagnostics, not new release gates.

| Clip | Poses excluded | Nonlinear evaluations | Worst unavoidable maximum endpoint error |
|---|---:|---:|---:|
| Crawl 111/03 | 1,524 / 1,524 | 0 | 0.207587 m |
| Get-up 140/08 | 898 / 898 | 0 | 0.215577 m |

Every source local pose is retained byte-for-byte at the fitter boundary; source
clip files are unchanged. All pair rows and original residuals stay in local
reports. A separate replay checks **58,128 assessed pairs across all 2,422
poses**, compares maximum bounds to the earlier direct edge decomposition at
every frame within `6.107e-16 m`, and reconstructs retained locals through a
different linear solve within `1.555e-15`. It does not call a fitter. Shared
recorded transforms, reference parsing and goal construction remain explicit.

The final source checks complete in 3.063 seconds at 152,707,072-byte peak RSS;
21 resource observations replay. The actual fitter study completes in 10.156
seconds at 147,406,848-byte peak RSS, with 28 observations replayed. Independent
replay completes in 1.032 seconds at 73,404,416-byte peak RSS, with 19
observations replayed. The original diagnostic and failed/intermediate test
resource traces are retained with their actual statuses.

No corrected animation, contact, physics, engine or human quality follows from
these exclusions. Raw references retain their [existing rights and admission
scope](cmu-ground-reference-v1.md); training admission remains false. Next work
must construct targets that account for the supplied rig's proportions and
use separate explicit supports/contact geometry. Rotational IK against the
same impossible coordinates is insufficient. All release requirements remain
unchanged.
