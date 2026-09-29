# Shared-pose contact diagnostic

The previous frozen-frame experiment repeated input poses but retained independent time-varying controls. The optional `fit_scene_regions.py --shared-pose` diagnostic now uses one set of bounded rotation controls and one root-height variable across every repeated key. It keeps the original source pose as the edit-budget reference. This mode is for spatial diagnosis, not animation generation or a contact-feasibility guarantee.

The entry point rejects nonconstant source/initialization tracks, moving objects, multiple actors, partner cuts, and contact windows that do not span the entire fixture. The low-level fitter also checks repeated source/reference/initialization transforms and rejects release guards. Shared controls are expanded through a one-column constant basis, including during initialization recovery; output is reconstructed from the original offsets. Rotation and root bounds, skin constraints and contact tolerances are unchanged. Protocols and recipes identify this mode, and implementation snapshots include the new helper. The Studio workflow still uses normal temporal fitting.

Sixty-four focused tests pass, covering rejection of nonstatic inputs, a known shared-control optimizer solution, source-relative initialization/budgets, both root-coordinate helpers, regional objectives, rate constraints, jobs and completion audits. In `reports/shared-pose-integration-v1`, four real five-frame runs use two stages of two iterations. Frozen/current normal legacy outputs are bit-identical, as are frozen/current physical-box outputs. All four preserve original edit bounds and native FK discrepancy below 0.3 micrometres. These are compatibility checks, not quality evidence.

## Measurement protocol

`reports/region-shared-pose-v1/method.py` runs two new diagnostic variants on the retained frame-121 fixture: shared pose without the rate objective and shared pose with the rate objective plus its 0.0005 acceleration margin fraction. Each uses six stages of 100 iterations, a 600-second ceiling, physical-box root, full sparse skinning, per-vertex object and augmented regional constraints, stage witness refresh, original source/seed and the earlier margins. The driver audits exported geometry, per-joint rates and Godot import once for each completed result. It checks that every output transform repeats exactly and that only one rotation-control frame and one root variable are recorded.

The original independently controlled five-key trials remain intact under `reports/region-frame121-static-v1`. Comparisons against those trials are developmental; the new implementation adds the shared-pose path. The new pair uses identical implementation and settings apart from the rate guard and its dependent margin. Neither experiment adds a generated action, a held-out sample, a full transition, a human rating or a release approval.

## Completed results

| Measurement | Shared pose, rate guard off | Shared pose, rate guard on |
| --- | ---: | ---: |
| Runtime / objective evaluations | 62.250 s / 1,064 | 99.235 s / 1,037 |
| Failed exported contacts / 34 | 34 | 34 |
| Failed geometry samples / 17 | 17 | 17 |
| Worst box penetration | 9.659422 mm | 9.243853 mm |
| Root lift, identical at every key | 77.570323 mm | 75.497499 mm |
| Minimum sampled skin-floor gap | 83.505788 mm | 81.432278 mm |
| Maximum original-source rotation edit | 28.025971° | 28.232573° |
| Maximum rotation change from initializer | 14.273705° | 14.567759° |

Both native outputs repeat exactly. Exported speed is below 1.1e-13 m/s and acceleration below 2.3e-11 m/s², consistent with numerical noise. Both preserve original edit bounds, but all six stages of each solve reach the iteration limit. A static result has no usable-action or transition implication. The character is lifted away from the floor: satisfying a lower clearance bound does not preserve planted support.

In both candidates, the worst native skin vertex is 16789, weighted entirely to `RightForeArm`. Thus the remaining spatial failure is still in the forearm skin; removing temporal degrees of freedom has not solved it. The unguarded candidate also misses hand-region clearance and normal limits. Penetration is smaller than in the earlier independent-key diagnostic, but all contact and geometry samples still fail. The rate objective now permits substantial pose changes in both conditions; this does not prove a unique cause for earlier optimizer behavior.

Independent Godot audits reproduce all 20 new source/candidate actor-frames and 77 joints, with maximum position discrepancy below 0.232 micrometres. `comparison.json` binds the methods, protocols, outputs and audits and retains the earlier independent-key results for context. Both new processes and audits completed; no fitting retry was used. No default algorithm or acceptance threshold was replaced.

Studio collection `shared-grasp-pose-review-v1` retains the guarded source/candidate diagnostic. Twelve file hashes and eleven permitted file routes pass offline verification; the Python provenance snapshot remains intentionally unserved. The idle Studio server was restarted to reload the implementation dependency list. No live browser or human review was performed.

Next inspect the shared spatial subproblem's remaining forearm/contact residuals and optimizer stationarity, including the lost ground support, before another full-duration solve. A larger full-clip budget is not justified by these results. All fourteen release capabilities, including broader actions, interaction, rig transfer and human cleanup evidence, remain unapproved.
