# Contact and temporal fitting experiment, 2026-09-27

This experiment fits explicit mesh support targets, surface clearance and actual motion acceleration together. It is separate from Studio defaults. The previous clearance fitter controls changes in edit parameters and preserves existing horizontal foot trajectories; those choices cannot remove existing sliding and can still worsen the final animation's joint steps.

## Method

`rig_trajectory_fit.py` extends the established mesh/Jacobian adapter. Each support target declares a foot-region vertex set, start/end frame, world position and provenance. The initial implementation accepts one patch per foot at a time. Targets can be supplied explicitly; this study uses visibly unconfirmed drafts from the original model's foot/toe prediction union. It selects the lowest 3 mm of the weighted foot region at interval start, a median horizontal target and a 1.5 mm ground height. These targets are not independently confirmed contacts or gameplay annotations.

The objective combines the original minimum-foot-height and all-vertex floor terms with root/rotation edit priors, support centroid position and adjacent velocity, horizontal preservation for unsupported feet, actual root second differences and local rotation-matrix second differences. Each block update includes all neighboring acceleration centers affected by that frame. Residuals use saved, fixed weights at 30 fps; rotation-matrix acceleration is a smooth optimization surrogate, not a dynamics model. Independent reporting additionally measures parent-frame angular-velocity differences in rad/s² and root acceleration in m/s².

The optimizer retains the original envelope-scaled root/joint edit bounds, 15 mm adjacent root-edit bound and 5 degree adjacent rotation-edit bound. It additionally constrains each edited joint's actual adjacent local rotation to its input value plus at most 0.5 degrees. The trace inequality has an analytic derivative. Bounded least squares uses constrained SLSQP when needed, followed by a feasible step and backtracking. A small update or six sweeps is a stopping rule, never a proof of optimality. Original frozen frames remain fixed.

## Matched study and validation

`study_trajectory_fit.py` uses source-context-preserving, previously pose-fitted jump 204 and dance 203 inputs. The unchanged clearance fitter and new trajectory fitter receive identical GLBs and height targets. No new model inference, training or raw-output changes. These are development failures, not held-out evaluation. The jump has very few predicted support steps, so its sliding statistics have limited support.

Initial checks: 15 clearance/trajectory tests passed in 23.44 seconds. A later independent whole-trajectory scalar-energy gradient check was added; the final nine trajectory tests passed in 29.29 seconds. Coverage includes derivatives at first/interior/last frames, support validation, preservation, bounded edits and actual rotation steps on a synthetic drifting footprint. No full-suite rerun is claimed for this isolated experimental module.

`verify_trajectory_fit.py` decodes actual GLBs independently of the optimizer. It checks all skin vertices at integer/half frames, preservation and edit bounds, actual adjacent joint-step regression, explicit support errors/speeds, acceleration and the full scalar objective with each temporal term counted once. It also reports conflicts with frozen support frames and a lower bound on incompatible desired foot-height/support-height errors. A lower objective or successful import is not motion-quality approval.

## Verified results; study complete

The jump's trajectory fit improves measured support error and acceleration, but leaves 23.44 mm editable floor penetration. It is not approved for production. Both corrected versions still preserve frozen source penetration of 24.06 mm.

| Jump 204 diagnostic | Input | Clearance | Support + trajectory |
|---|---:|---:|---:|
| Editable floor depth | 75.38 mm | 0.62 mm | 23.44 mm |
| Editable half-frame floor depth | 75.33 mm | 1.94 mm | 18.13 mm |
| Right predicted whole-foot speed p95 | 23.3 cm/s | 23.3 cm/s | 11.0 cm/s |
| Right draft patch speed p95, frames 24–32 | 18.0 cm/s | 18.0 cm/s | 7.2 cm/s |
| Maximum draft support error | 65.44 mm | 60.38 mm | 24.29 mm |
| Editable angular acceleration p95 | 178.7 rad/s² | 186.2 rad/s² | 147.4 rad/s² |
| Editable root acceleration p95 | 16.0 m/s² | 19.8 m/s² | 12.7 m/s² |

The two speed measures use different vertex groups and sample sets; they must not be substituted for each other. The left draft has only one adjacent step. Maximum per-edge joint-step regression is 4.4553 degrees for clearance versus 0.500006 degrees for trajectory (within export tolerance of the declared 0.5-degree bound). Both fits reach six sweeps; clearance has ten unsuccessful subproblems and trajectory fifteen. The independent whole-trajectory energy decreases from 109.4756 to 5.9506 for trajectory, but that weighted objective permits the observed floor failure. The worst editable penetration is at frame 24 with a full edit envelope, so frozen context alone does not explain it. No infeasibility or optimality claim is made.

Dance 203 reaches 2.95 mm editable floor depth (2.63 mm between frames), compared with 2.36/2.37 mm for clearance alone. Left/right predicted whole-foot speed p95 decreases from 24.4/25.3 cm/s to 8.5/8.4 cm/s; clearance alone leaves these speeds essentially unchanged. Maximum draft support error decreases from 62.72 to 15.18 mm. Angular acceleration p95 decreases from 58.52 to 40.49 rad/s² and root acceleration from 5.75 to 3.82 m/s². Maximum per-edge joint-step regression is 0.500005 degrees, within export tolerance. The trajectory solver reaches six sweeps with six unsuccessful subproblems; clearance stops after five sweeps with a zero update. Neither result proves optimality.

The [completed comparison](http://127.0.0.1:8767/reports/trajectory-fit-v1/viewer.html) includes both cases. Orange markers show draft targets and blue markers show measured patch centers. Same-frame stage switching and the grey character were checked in the browser. All eight GLBs have zero validation errors (inherited source warnings remain), pass actual Godot playback across 724 frames, and match downloaded hashes. Maximum Godot joint-position error is 4.62e-7 m. Copied diagnostic metadata was normalized against decoded geometry without changing motion bytes; original metadata and implementation snapshots remain saved.

Decision: experimental, not promoted. Jump floor penetration still fails, both cases use unconfirmed support targets, contact-speed proxies remain above release targets, and action quality has not received animator approval. Later full-suite profile validation includes this solver: 378 tests pass with four existing Torch warnings.

## Evaluation-cost refactor

After the running study had snapshotted its original implementation, `ClearanceFitter.objective_from_surface` was factored out so the composite trajectory objective reuses its already computed mesh positions and Jacobian. `benchmark_trajectory_evaluation.py` loads the preserved original modules separately and compares both implementations at three jump frames. Residuals and Jacobians are exactly equal. Twelve alternating measurements per implementation/frame give median evaluation times of 19.83→10.21, 22.13→14.19 and 20.56→10.08 ms. These are concurrent single-thread microbenchmarks, not full-solver runtime claims. The completed study used its original loaded code and snapshots. Sixteen focused tests pass after the refactor in 19.14 seconds.

Broad action and rig evaluation must follow this bounded test; these two cases cannot establish general animation quality.
