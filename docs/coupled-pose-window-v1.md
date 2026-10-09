# Coordinate adjacent contact frames

`guarded_window_restoration.py` repairs two to five consecutive native contact keys together. Each key retains the original point, surface-normal, complete skin/prop/floor, rotation/root and all-reference position limits. Internal added-speed constraints depend on both edited keys; available exterior keys stay fixed. Neither timing nor the original raw, limb or previous reference is rebased. This is an experimental contact-window backend, not a full-clip or release certificate.

`CoupledPoseWindow` assembles complete scalar and vector populations from the existing native pose derivatives. Internal velocity vectors include both control blocks. Reference maxima retain all ties. Per-frame row identities remain unique, and returned vector arrays cannot mutate the derivative cache. Complete nonlinear replay and exact tangent retention protect every row; initialization remains proposal-only. The native runner streams complete reports, binds inputs/methods, validates individual resumed pose histories, preserves rejected queries and refuses overlapping source/resume/output directories.

## Verification

A fresh source-only fixture passes 371 focused tests across fifteen modules. New coverage compares every coupled derivative with dense evaluation, checks all vector/reference populations, fixed exterior keys, clip endpoints, cache isolation, invalid requests and runner lifecycle. A coordinated ramp passes the original speed limit while the same central edit with frozen neighbors fails; contact/geometry approval remains separate. Both new modules are added to the Windows/Linux CPU-native CI job. The separate model-free inventory remains 406 Python modules and 39 Node suites; hosted verification is not inferred from local tests.

The native V1 study jointly edits frames 97–99 of the unchanged authored-height box lift, resuming only frame 98 from fully verified V25. There are 525 controls, 1,068 scalar rows and 2,265 vector records. All 18,056 skin vertices and eight influences are retained per frame. Three outer steps use trust `.03`, ten inner iterations, a 300-second local limit, explicit preservation of every row and the existing separate proposal margins.

At the actual seed, dense and assembled values match exactly; the maximum derivative difference is `5.329e-15`. Dense evaluation takes 46.047 seconds and assembly 3.438 seconds at that seed. This is a local derivative comparison, not a full-clip speed claim.

| Frame | Seed → final grip distances, mm | Seed → final normal errors, degrees | Seed → final box penetration, mm |
| --- | --- | --- | --- |
| 97 | 4.572 / 4.809 → 4.575 / 4.807 | 20.194 / 16.668 → 20.189 / 16.659 | 14.079 → 13.885 |
| 98 | 4.983 / 4.972 → 4.984 / 4.973 | 19.836 / 19.585 → 19.835 / 19.571 | 7.215 → 7.201 |
| 99 | 4.583 / 5.131 → 4.559 / 5.111 | 19.656 / 15.070 → 19.648 / 15.069 | 16.556 → 16.282 |

Three corrections are retained: one optimized 1/32 step and two geometry-start 1/64 steps. Local solve time is 150.813 seconds, with 51 measurements, 22 unretained queries and 28 backoffs. The supervisor exits 0 after 288.156 seconds; peak tree RSS is 1,412,829,184 bytes. The 3,600-second / 7 GiB tree-RSS / 600 MiB available-RAM guards remain unchanged. Maximum normalized violation decreases `1.656687 → 1.629311`; squared violation decreases `57.899648 → 56.265482`.

All three poses remain failed. Normals exceed 10 degrees; raw-reference displacement remains 221.592 / 221.876 / 221.571 mm against 220 mm; frame 99's right grip still fails 4.99 mm; penetration remains failed. Raw adjacent added speeds are 0.134/0.578, 0.578/0.533 and 0.533/0.295 m/s, within 1.5 m/s. No semantic, anatomical or animation-quality rating is inferred.

Independent NumPy replay verifies all 52 saved windows (156 native poses), three retained decisions, 18 proposal archive files and original/method/output bindings. It reconstructs both the float64 solver population and the saved float32/projected motion. Solver rows agree within `9.24e-14`; the largest normalized row difference from saved representation is `1.03e-5`. All three accepted saved-motion corrections also preserve every conservative margin row. Recorded epigraphs, vector balls, cuts and tangent/nonlinear decisions replay; LP optimality and full derivative correctness at every later proposal are not independently certified.

## Reproduction and next work

Use separately acquired native inputs and an owned supervisor:

```powershell
.venv/Scripts/python.exe scripts/guarded_window_restoration.py reports/box-lift-authored-height-v1 reports/my-new-window --frames 97 98 99 --iterations 3 --trust .03 --seconds 300 --solve-iterations 10 --row-chunk 16 --resume 98 reports/box-lift-guarded-restoration-v25/frame-98
```

Current resume accepts fully bound individual pose studies; window-to-window continuation is not implemented yet. Preserve the V1 terminal output and add verified window continuation before extending correction. Next improve finite-step curvature handling and expand useful repair across the contact interval, then perform full temporal/surface/engine and diverse action/rig/object/partner checks. No source clip, preview, generation/training, engine import or human evidence is replaced or added. All fourteen capabilities of the broad animation-authoring goal remain unapproved.
