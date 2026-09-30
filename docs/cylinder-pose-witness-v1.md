# Cylinder grasp: single-pose diagnostic

The frame-96 diagnostic **did not find a passing pose**. This is a failed local search, not proof that the original request is impossible. No clip or Studio candidate was replaced, and no release capability was approved.

## Method

`scripts/regional_pose_witness.py` starts from the retained [cylinder grasp](cylinder-contact-v1.md) candidate at native frame 96, near its worst exported collision at 96.25. It retains the source-relative body/finger rotation norm limits, root-height limit, authored hand patches, 5 mm guide anchors, regional contact thresholds and full-skin floor/object clearance. All 18,056 skin vertices participate in clearance. Temporal coupling and support tracking are relaxed; even a successful pose would not establish a usable clip or realistic motion.

The optimizer fixes one distributed triangle per hand from the seed, retains separate regional constraints, and minimizes normalized squared change from that seed using SLSQP. Patch clearance uses its worst vertex, so an average cannot hide penetration. Rotation component bounds are supplemented by rotation norm inequalities. The independent acceptance path reconstructs serialized rotations and searches the complete authored patch for valid triangle witnesses.

The run is limited to 150 iterations and 180 seconds, with process memory and available-memory guards. Inputs, implementation snapshots, protocol, iteration history and output hashes are retained under ignored `reports/cylinder-pose-witness-v1`. This is a local development condition; no held-out prompt or seed is consumed and no model is trained.

## Observed result

SLSQP terminated after 38 iterations and 169 evaluations with `More than 3*n iterations in LSQ subproblem`. The experiment finished in 82.172 seconds with peak observed process RSS of 611,356,672 bytes. Its `complete` status records experiment completion; solver success and pose acceptance are both false.

| Independent native-pose measurement | Seed | Final diagnostic |
| --- | ---: | ---: |
| Full-skin object penetration | 36.356 mm | 29.713 mm |
| Left anchor error, 5 mm limit | 4.636 mm | 6.328 mm |
| Right anchor error, 5 mm limit | 8.602 mm | 11.420 mm |
| Left patch penetration | 9.349 mm | 16.158 mm |
| Right patch penetration | 8.918 mm | 2.585 mm |
| Minimum skin-floor height | 2.024 mm | 55.505 mm |
| Root lift from original source | 0.022 mm | 53.504 mm |

The final pose passes its edit bounds, with maximum local rotation change of 19.182 degrees. Both hand contacts fail. The left hand loses its distributed triangle witness. Lower object penetration therefore does not justify promoting the output.

Preflight reproduces saved seed FK within 9.310e-8, checks all geometric residual directional derivatives with maximum error 1.678e-6, and includes 88 total geometric/rotation constraints. Independent serialized-skin reconstruction agrees with the optimizer within 5.308e-8 m. Sixteen focused tests pass, including patch-maximum behavior, native audit replay, invalid-frame rejection and independent edit-bound rejection. Asset-dependent tests require the retained local development inputs; they are not part of the public model-free CI suite.

## Interpretation and reproduction

The infeasible starting pose and failed SLSQP subproblem leave static feasibility unresolved. A distinct next experiment could minimize geometric infeasibility with normalized variables while keeping edit bounds hard; any temporary solver slack must never relax final acceptance. Increasing the same iteration limit alone is not supported by this result. Whole-clip continuity, balance, naturalness and animator cleanup remain untested by this diagnostic.

With the separately acquired local assets and retained completed v14 fit:

```powershell
.venv\Scripts\python.exe scripts/regional_pose_witness.py reports/scene-region-jobs/cylinder-contact-v1/fit reports/<new-pose-study> --frame 96
.venv\Scripts\python.exe -m pytest tests/test_regional_pose_witness.py tests/test_grasp_pose_witness.py tests/test_grasp_pose_witness_bounded.py -q
```

The output directory must be new. `pose.npz` contains one diagnostic frame, not a replacement animation.
