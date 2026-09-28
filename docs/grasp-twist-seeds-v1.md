# Alternate hand orientations and fixed-shape clearance

Five predeclared left-hand twist targets are reachable within the original arm edit limits, but none improves clearance. The sphere's rotational symmetry makes these twists geometrically equivalent for the fixed hand shape. A separate analytic rigid-patch diagnostic shows why finger articulation is the next relevant variable.

This is one development pose at frame 60, using the unchanged model and existing licensed rig. All failures remain retained. No full animation, reserved evaluation, engine approval or release capability is established.

## Target construction and projection

The seed is `reports/grasp-pose-restoration-v2`. Targets use twists of -20, -10, 0, +10 and +20 degrees. First align the measured skinned palm normal with the authored normal, then rotate the palm tangent by the selected angle about that normal. The tangent follows the existing hand fitter's definition: wrist to average index/middle/ring/pinky second joints, projected into the palm plane. The point target remains the original authored skin contact point.

Only LeftShoulder, LeftArm, LeftForeArm and LeftHand change. Their original 40-degree rotation-norm edit budgets remain enforced by the existing bounded map. Fingers, right arm, torso, legs and root are fixed exactly in parameter space. The older paired-hand fitter uses different limits and component bounds, so it is not substituted for this matched pose model.

The projection optimizes actual skinned point, mesh normal and tangent rather than assuming the palm point belongs rigidly to the wrist alone. It targets the center of the original contact tolerances: exact authored point and normal. This is more restrictive than merely staying within 5 mm and 10 degrees. The source pose uses almost all that tolerance, so forcing centered contact can worsen overlap even before adding a twist. The zero-twist trial records this effect.

All five reach the declared 0.1 mm point and 0.1-degree direction projection checks. In fact, maximum point error is below 0.059 micrometres, normal error below 0.000041 degrees and tangent error below 0.000041 degrees. All original protected gates and joint/root bounds pass. The five solves use 10, 9, 8, 11 and 23 evaluations respectively, totaling 7.234 seconds of recorded trial time, with about 569 MiB sampled peak RSS. Directional derivative discrepancy is 3.48e-7 in normalized residual units; independent skin discrepancy is below 0.055 micrometres.

Every trial has approximately 13.953 mm sphere penetration, much worse than the preceding 0.395 mm pose. These are rejected seeds, not improvements. The report's raw minimum happens at -10 degrees, but differences are below numerical significance and do not justify selecting that pose for more correction.

## Why twisting does not change this clearance

The authored contact is on the sphere surface and its normal points directly toward the sphere center. Its twist axis therefore passes through that center. Rigid rotation about this axis preserves each vertex's distance from the center.

All positive skin influences of the contact patch and its normal-defining triangles lie within the left-hand subtree. With fingers fixed, the five reconstructed poses confirm the expected near-rigid behavior: the largest per-vertex sphere-distance spread across 2,735 hand-subtree vertices is only 0.036 micrometres. Full-skin clearance results are also numerically tied within the declared 2-micrometre comparison allowance. More pure twist seeds would duplicate this geometric experiment.

## Analytic rigid-patch diagnostic

`rigid_grasp_bound.py` bounds clearance for **rigid transforms of the measured fixed hand patch**. It allows every twist, any contact-point displacement within the original point tolerance and any normal tilt within the original normal cone. This goes beyond the five sampled twists, but it remains a conditional geometric model. It does not permit finger deformation and does not certify exact equivalence to finite-precision LBS under arbitrary skeleton transforms.

For a vertex offset `r` from the measured contact point, its angle `gamma` to the measured normal remains fixed under rigid motion. Let `D` be the distance from authored contact to sphere center, `alpha` the angle between that radial vector and authored normal, and `epsilon` the allowed normal tilt. The smallest possible radial angle for that vertex is:

`theta = max(0, alpha - epsilon - gamma, gamma - alpha - epsilon)`

Thus its greatest possible distance from the sphere center is at most:

`sqrt(D² + |r|² + 2 D |r| cos(theta)) + point_tolerance`

Subtracting the sphere radius bounds signed clearance. A single vertex whose upper bound still fails is enough to reject this fixed-shape rigid model; maxima for different vertices need not share one attainable transform.

The calculation includes the existing numerical contact tolerances plus a 2-micrometre distance allowance. Vertex 1427 has at most **0.525 mm signed clearance**, below the required **1.999 mm** after the clearance audit's numerical tolerance. Twenty-one patch vertices have such obstructions. Vertex 1427 is primarily weighted to LeftHandPinky1. This is a rigid-patch obstruction, not a proof that the full articulated hand or original optimization problem is infeasible.

Tests include an exactly attainable single-vertex extremum, random constrained rigid transforms, a contact at the sphere center, antiparallel normal alignment and signed twist preservation. The random checks supplement the closed-form derivation; they are not its proof.

## Verification and next work

`audit_grasp_twists.py` verifies source/input/protocol hashes, each target frame, exact frozen parameters, original nonlinear gates and exact saved pose arrays for all five trials. It checks the radial symmetry prerequisite, reports the numerical tie and records the rigid-patch scope separately. Local reports are `reports/grasp-twist-seeds-v1` and `reports/grasp-twist-seeds-v1-audit-final`; the earlier audit is retained.

```powershell
.venv\Scripts\python.exe scripts/study_grasp_twists.py reports/sphere-floor-fit-v13 reports/grasp-pose-restoration-v2 reports/new-twist-seeds
.venv\Scripts\python.exe scripts/audit_grasp_twists.py reports/new-twist-seeds reports/grasp-pose-restoration-v2 reports/new-twist-audit
```

Reproduction requires the earlier local studies and separately acquired licensed asset. Raw outputs remain excluded from Git. The next search should vary finger shape within the original budgets, using the rigid bound only as a necessary-condition diagnostic before full articulated projection and clearance checks. Passing an upper bound would not establish a valid grasp. No original tolerance or budget is relaxed, and all 14 release capabilities remain unapproved.
