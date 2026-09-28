# Bounded two-hand region pose

Follow-up: the [moving grasp trajectory](sphere-region-track-v1.md) passes dense contact checks through the grasp interval, while retaining an unsafe approach and motion regressions. The single-pose evidence below remains unchanged.

One development pose now passes the declared two-region contact, original joint-edit limits, floor and full-skin object-clearance checks. This is a new authored contact condition, not a success on the original fixed-point fixture and not a complete animation. No release capability is approved.

## Why the condition changed

The [contact-calibration probes](grasp-contact-calibration-v2.md) retained failures for the original tiny point-normal neighborhood and an alternate fixed vertex. Their region probe instead requires three separated surface vertices near each world-space grip target, with a minimum contact area and a region-averaged normal. The world-space targets, original 5 mm point/10 degree normal limits and original joint-edit budgets remain. Surface bindings and normal definitions explicitly change; they still need anatomical review.

The first right-hand region ring had two full-hand-clear placements but no sufficiently distributed contact. At azimuth zero its largest eligible triangle covered 18.537114 square millimetres, and at 315 degrees 13.379048 square millimetres; both were below the 25 square millimetre requirement and the 6 mm spacing requirement. A follow-up development probe tested the midpoint, 337.5 degrees, at the same 9.5-degree tilt. It did not relax any gate. Across the centered and midpoint orientations, 378 placements produced six full-hand-clear candidates and three passing region candidates. This adaptive follow-up is development evidence, not held-out evaluation.

## Actual arm projection

`project_sphere_region.py` fits each selected rigid hand target onto the original shoulder, upper arm, forearm and wrist chain. The four rotation vectors use the existing hard norm-bound mapping relative to the original reference motion. Fingers, the other arm, torso, legs and root parameters remain exactly equal to the restoration seed. The objective fits the actual skinned anchor, area-weighted region normal and wrist-to-knuckle tangent. Selected tilted normals are reconstructed from the saved rotation, rather than mistakenly using the untilted authored normal.

The left projection took seven evaluations and the right ten. Their target position errors are below 0.045 micrometres. Directional derivative errors are below 6e-8 in scaled residual units; Torch and independent NumPy skin agree within 0.056 micrometres. Optimizer convergence alone is not an acceptance criterion.

Each single-arm projection still fails the full pose because the untouched opposite hand intersects the sphere. `combine_sphere_regions.py` combines only the two disjoint arm parameter blocks from the same original seed. It then reconstructs and measures the complete 18,056-vertex skin, all scene objects and the floor.

| Combined-pose measure | Measured | Requirement |
| --- | ---: | ---: |
| Minimum skin clearance from sphere | 2.004918 mm | at least 2 mm, existing 1 micrometre numerical allowance |
| Minimum skin height above floor | 6.153928 mm | at least 2 mm |
| Left / right anchor error | 2.100032 / 2.099989 mm | at most 5 mm |
| Left / right region normal error | 9.500003 / 9.499992 degrees | at most 10 degrees |
| Left / right contact centroid error | 2.779665 / 2.806848 mm | at most 5 mm |
| Left / right contact triangle area | 32.966966 / 33.261768 square millimetres | at least 25 square millimetres |
| Left / right minimum contact spacing | 7.595048 / 7.623427 mm | at least 6 mm |

All per-joint original rotation budgets pass; the largest edit across the complete pose is 24.195754 degrees. Root lift remains exactly 4.082323 mm. The second object remains 3.575118 m away. All selected contact vertices lie in the required 2–3 mm sphere gap interval. The remaining clearance margin is small, so this pose must not be assumed safe under interpolation or later rig transfer.

The combined pose deliberately also records evaluation under the original fixed-point/local-normal condition. That condition fails: original point errors are 31.285038 and 31.896195 mm, and original normal errors are 13.284504 and 11.563416 degrees. Preserve this distinction in every downstream comparison; never report this as a solve of the unchanged fixture.

## Verification and retained failures

`audit_sphere_region.py` reconstructs the seed independently, uses SciPy alignment and scalar contact-triangle enumeration, verifies every saved placement and selected candidate, and checks projected native pose arrays, original norm bounds, frozen parameters and targets. It verified the earlier 191-, 1,719- and 1,701-placement studies plus the new 378-placement right-hand probe. A first audit attempt failed on the legacy centered-only protocol's missing `orientations` field; the failure and auditor snapshot remain under `reports/sphere-region-audit-preflight-v1`. Explicit legacy schema support repaired the auditor without changing any study result.

`audit_combined_sphere_regions.py` independently rebuilds the combined parameters from the two source deltas, checks disjoint chains, verifies every saved pose array, and recalculates original-condition and region-condition acceptance. The full-skin combined audit passes the new pose condition and rejects the original condition. Fourteen focused tests pass, including independent triangle selection/rejection and explicit orientation validation.

Local evidence:

- `reports/sphere-region-projection-v1` and `reports/sphere-region-projection-v1-audit`
- `reports/sphere-region-support-right-v2`, `reports/sphere-region-projection-right-v1` and its `-audit` sibling
- `reports/sphere-region-pose-v1` and `reports/sphere-region-pose-v1-audit`

These generated assets remain excluded from Git. No model training, checkpoint change, engine validation, Studio default change or reserved release trial occurred. This work does not establish anatomy, self-collision, balance, continuous collision safety, clip timing, temporal smoothness or animator quality. All 14 release capabilities remain unapproved.

## Reproduction and next work

Existing local fixtures, earlier region reports and licensed skin dependencies are required. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/project_sphere_region.py reports/sphere-region-support-v3 reports/grasp-pose-restoration-v2 reports/new-left-projection
.venv\Scripts\python.exe scripts/probe_sphere_region_support.py reports/sphere-floor-fit-v13 reports/grasp-pose-restoration-v2 reports/new-right-region --tilt-ring-degrees 9.5 --hand RightHand --azimuth-degrees 337.5
.venv\Scripts\python.exe scripts/project_sphere_region.py reports/new-right-region reports/grasp-pose-restoration-v2 reports/new-right-projection
.venv\Scripts\python.exe scripts/combine_sphere_regions.py reports/new-left-projection reports/new-right-projection reports/new-combined-pose
.venv\Scripts\python.exe scripts/audit_combined_sphere_regions.py reports/new-combined-pose reports/new-combined-audit
```

Next, test these explicit region definitions over the grasp interval and into attachment/release, with spatial and temporal post-validation. Preserve this single-pose result as a reference and retain every failed frame. Region-aware authoring and reviewed palm calibration must precede default adoption. Then broaden objects, actions, rigs and partners; this sphere development pose cannot stand in for that coverage.
