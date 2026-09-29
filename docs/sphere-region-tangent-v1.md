# Endpoint-rate matching: rejected release variants

Matching the arm's incoming rotation rate reduces the endpoint discontinuity but does not solve the grasp release. The unconstrained return exceeds the existing rotation budgets. A bounded variant passes the budgets but fails sphere clearance and worsens whole-motion dynamics. The earlier [spatial return](sphere-region-spatial-v1.md) remains the geometry-passing reference; neither it nor these new variants is release-approved.

## Method and source check

`rotation_return.py` constructs a cubic Hermite curve in the rotation logarithm relative to the starting pose. Endpoint body rates are estimated from the adjacent source keys (120→121 and 145→146). The terminal body rate is mapped through the inverse SO(3) right Jacobian before interpolation. Without correction or resampling, the curve matches those endpoint rates. The endpoint poses, release time, clip length and original rotation limits remain unchanged.

SciPy's official [rotation spline source](https://github.com/scipy/scipy/blob/main/scipy/spatial/transform/_rotation_spline.py) documents the distinction between rotation-vector derivatives and angular rates. The installed SciPy 1.15.3 implementation was inspected as well. This experiment uses an explicit two-endpoint Hermite curve, not `RotationSpline`; its behavior after bounded correction and 30 fps baking must be measured separately. No dependency, model or training-data change was made.

Tests verify noncommuting endpoint rates, small/zero relative angles, a near-pi rotation, endpoint poses and invalid input handling. The independent trajectory auditor uses SciPy `CubicHermiteSpline` and solves the forward right-Jacobian system, rather than calling the writer's inverse-Jacobian expression. It then verifies proposed parameters, optional norm projection, native replay and the actual exported clip.

## Unbounded proposal failure

`reports/sphere-region-tangent-v1` terminates at frame 122 because the arm solver refuses an initial pose outside its rotation budgets. The failure, protocol and source snapshots are retained; no complete motion was produced. A subsequent diagnostic measures violations over frames 122–128. The maximum proposed right-arm edit is 42.962343 degrees against the existing 40 degree limit; the right shoulder also exceeds its limit.

There is a more direct discrete constraint conflict: continuing exactly the previous right-arm local rotation increment into frame 122 would require a 40.797848 degree edit relative to that frame's original reference. Thus that exact next-key continuation cannot satisfy the unchanged 40 degree budget while preserving the preceding keys. This is not proof that every continuous path or coordinated whole-body solution is infeasible.

The writer now saves a structured failure record before rejecting this invalid seed domain. This reporting change happened after the failed run; the original run's traceback and separately recorded failure metadata remain immutable.

## Bounded variant

`reports/sphere-region-tangent-v2` radially projects each proposed arm rotation-vector edit inside the original norm ball, with a 0.001 radian interior reserve. This reserve tightens the proposal and does not enlarge acceptance limits. Raw proposed parameters are retained; the uncorrected native file contains the bounded path before radial skin-clearance fitting. Non-arm edits, root and all 157 protected frames remain exact to the previous release input.

Five keys (122–126) need arm fitting after that projection. All five hit the 100-evaluation limit without convergence, taking 117.969 seconds in total. Complete output was retained for rejection analysis rather than treating optimizer completion as feasibility.

| Measurement | Earlier spatial return | Bounded tangent return |
| --- | ---: | ---: |
| Grasp samples passing | 245/245 | 245/245 |
| Full-clip geometry failures | 0/717 | 15/717 |
| Original edit-budget failures | 0/717 | 0/717 |
| Peak joint speed | 1.364917 m/s | 1.513351 m/s |
| Peak joint acceleration | 40.041065 m/s² | 82.077569 m/s² |
| Largest arm rate-step difference at frame 121 | 1.351084 rad/s | 0.565534 rad/s |
| Largest arm rate-step difference at frame 145 | 0.365702 rad/s | 0.209436 rad/s |

The 15 geometry failures occur from frame 122.5 through 126.0. Minimum release sphere clearance is 1.283893 mm, below the unchanged 2 mm requirement; it is a clearance deficit, not penetration. Maximum decoded joint edit is 39.946151 degrees. Floor height and the preserved grasp remain passing.

The rate-step measurements come from independently decoded local rotation increments at integer keys. They diagnose boundary continuity; their difference is not a claim of inertial angular acceleration. Lower endpoint jumps do not compensate for failed clearance or worse global dynamics. The candidate is rejected and no Studio default changes.

## Next decision and verification

Holding the final grasp poses fixed while matching their incoming motion collides with the original edit budget. The next trajectory solve should include the last grasp frames and the release together, preserving the authored contact region, timing and collision requirements while allowing the arm to decelerate before release. It must revalidate the full grasp population; prior passing samples cannot be assumed unchanged if those poses change.

Thirty-three focused tests pass, including ten new rotation-path/projection tests. The dense audit verifies preserved native arrays, projected proposals, original edit limits and all 717 export samples. No engine or human approval is inferred from these rejected variants. Existing geometry-passing exports remain intact.

Local evidence: `reports/sphere-region-tangent-v1/failure.json`, its `bounds-diagnostic.json`, `reports/sphere-region-tangent-v2`, `reports/sphere-region-tangent-v2-audit` and `reports/sphere-region-tangent-boundaries-v1/diagnosis.json`. The developer comparison question for the earlier spatial return remains unanswered; no human rating or cleanup time is fabricated. All 14 release capabilities remain unapproved, including broad action/rig/object/partner validation.

## Reproduction

Existing local fixtures and licensed dependencies are required. Use fresh output directories. This command reproduces an experimental candidate, not a validated correction.

```powershell
.venv\Scripts\python.exe scripts/spatial_release.py reports/sphere-region-release-v1 reports/new-tangent --path-profile tangent-cubic --bound-path
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-tangent-audit --approach-patch reports/sphere-region-approach-v1 --floor-patch reports/sphere-region-floor-v1 --release-patch reports/sphere-region-release-v1 --spatial-patch reports/new-tangent
```

Follow-up: [coupled grasp and release fitting](sphere-region-coupled-v1.md) reduces the boundary angular jump while retaining all sampled contact/geometry checks; hand-speed tradeoffs remain.
