# Local grasp projection and moving-guide transfer

A small constrained right-arm correction resolves the remaining static grasp failures without moving the feet or root. Its decoded export passes all 34 hand-contact, 17 geometry and 34 source-support samples. Transferring only the repaired hand/finger frames to the moving clip does not preserve that result: 465 of 490 hand-contact samples fail and body-box penetration remains 34.874 mm. Static feasibility is therefore demonstrated for this pose, while a usable moving grasp remains unresolved.

## Local correction

`scripts/study_local_region_projection.py` is an explicit five-key static diagnostic. It starts from the retained `region-clearance-buffer-v1/clearance_buffer` candidate and keeps the original source as the edit reference. It only changes `RightArm`, `RightForeArm`, `RightHand` and four right-pinky joints, with a component trust box of plus/minus 0.5 degrees. Separate nonlinear constraints enforce the original source-relative rotation norm limits. Root, other local rotations and original bone offsets remain fixed.

SLSQP minimizes squared local edits subject to all authored hand-region inequalities, the recorded contact triangles, and individual clearance constraints on vertices initially within 5 mm of each object or floor. The regional inequalities receive a 0.001 normalized solver interior offset; body clearance targets 2.01 mm. These are solver buffers, not relaxed audit tolerances. Full exported skin is checked independently, including vertices outside the local solve's selection. A sampled pass is not continuous collision, anatomy, balance or dynamics certification.

The first prototype failed its derivative preflight before optimization: assigning perturbed matrices into a float32 local-rotation array quantized the finite differences. The failed method and diagnosis remain under `reports/region-local-projection-v1`. The corrected float64 method is retained under `region-local-projection-v2`. Its directional finite-difference discrepancy is below 1.31e-8 in the normalized constraint units. The source-controlled runner independently reproduces every output motion array and GLB byte under `region-local-projection-runner-v1`.

The solve has 21 coordinates and 704 inequalities. Four SLSQP iterations find a feasible correction whose largest component edit is about 0.091137 degrees; it is not a 0.091-degree cap on each joint's rotation norm. The reconstructed foot surface changes by zero within the double-precision computation. Independent export checks establish:

| Measurement | Projected static pose |
| --- | ---: |
| Failed hand-contact samples | 0 / 34 |
| Failed geometry samples | 0 / 17 |
| Minimum box clearance | 2.009988 mm |
| Minimum floor gap | 11.006799 mm |
| Failed source-support samples | 0 / 34 |
| Maximum source-support drift | 4.988552 mm |

Support drift remains close to its 5 mm limit; the projection preserves the preceding candidate's support instead of restoring a perfect planted foot. Original edit bounds pass. Each of the prototype and source-runner checks imports ten source/candidate actor-frames into Godot with joint position discrepancy below 0.202 micrometres. The second run is a reproduction, not an independent action or seed. The approximately 0.91-second source-runner result time excludes preparation and subsequent audit work.

## Moving transfer exposes a limitation

The now-qualified static guide is supplied to `run_object_grip_seed.py` at original frame 121. The full 180-frame scene, original edit reference, earlier full-pose initializer, 100-iteration budget and object-relative hand/finger fitting method remain unchanged. Guide pose and reference frame differ from the older frame-60 guide, so this is a transfer test rather than a one-variable comparison against that older study.

The initializer completes in 12.532 seconds and retains the original edit bounds, but the exported quarter-frame audit reports 465/490 failed hand contacts, 357/717 failed geometry samples and 34.874050 mm maximum box penetration. Whole-clip joint speed and acceleration peaks are 1.283916 m/s and 36.765938 m/s², below their source peaks; nevertheless 34 per-joint speed peaks, 41 acceleration peaks and named grasp/boundary windows increase. Global peaks do not erase local regressions. All 360 Godot source/candidate actor-frames pass with position discrepancy below 0.317 micrometres.

The initializer targets hand/finger joint frames and does not constrain the repaired forearm surface path, distributed skin contacts or foot support. Its failed result is retained under `region-projected-guide-transfer-v1` and independently audited under `region-projected-guide-transfer-v1-completion`. It is not selected as a usable animation or an improvement over the older near-contact seed. Next carry surface contact and arm placement through the moving grasp with original edit limits and temporal checks, rather than assuming a valid static guide transfers automatically.

## Reproduction and review

```powershell
.venv\Scripts\python.exe scripts/study_local_region_projection.py reports/region-clearance-buffer-v1/clearance_buffer reports/fresh-local-projection
```

The runner requires existing locally retained input motion and mesh; these are excluded from the public source repository. Its captured inputs, implementation, derivative preflight, iteration history and independent audits identify the method and outcomes. The failed float32 preflight is preserved separately.

Studio collections `local-projection-review-v1` and `projected-guide-transfer-review-v1` expose the static pass and moving failure with their original source comparisons. Offline checks verify respectively 13/12 file hashes and 12/11 permitted routes; Python snapshots remain unserved. No live browser or human review occurred. Every result remains quality-unapproved, and all fourteen project release capabilities remain open.
