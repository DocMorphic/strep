# Root motion cleanup in Studio

Development integration, 2026-09-28. The project-wide goal stays active and every release gate remains open.

Characters now offers **Smooth root motion** for the corrected version of a mesh-contact edit and for previous cleanup results. It saves a separate supervised job, preserves the selected input, and exposes before/candidate previews, the original contact history, an audit, the recipe and a downloadable package. A lower acceleration objective is never displayed as contact or animator approval. Failed contact checks remain visible on both versions. The retained input opens first.

The job uses the surface-preserving v3 policy from [the root dynamics study](authored-surface-dynamics-v2.md): root translation only, at most one centimetre of additional correction per operation, original contact-edit budgets, fixed boundary samples, unchanged rotations and other animation channels, per-frame root and declared-patch acceleration guards, contact targets/edges and sampled per-vertex floor guards. Chained cleanup keeps the first contact edit's baseline and targets. The centimetre radius is relative to each selected input; original total root-edit budgets remain enforced. These are sampled geometric checks, not continuous collision or physical plausibility certification.

The supported input is a finite 30fps clip of 3–900 frames with its original mesh-contact recipe. Joint/finger edits are explicitly rejected because this path does not yet preserve their separately authored targets. Periodic clips are rejected. A valid operation with no verified improvement returns its byte-identical input rather than inventing a success.

## Integration evidence

Four completed local jobs exercise API submission, actual UI submission, chaining and unchanged-input handling. Eight exported versions across CesiumMan and a 65-bone rig pass actual Godot import and all-frame joint verification: **1,082 actor-frames**. Maximum world-position error is 0.000000603m, below the unchanged 0.0001 engine threshold. Downloaded GLBs and ZIPs match their recorded hashes. Frozen inputs, source files, target definitions, contact/event/timeline sidecars, provenance and licenses are preserved; root tracks are independently decoded from each GLB.

| Job | Result | Peak root acceleration, m/s² |
| --- | --- | --- |
| `20260928-102721-c4fa17f0` | Improved head-clearance input | 13.446 → 10.668 |
| `20260928-103008-a6626ded` | Improved imported clip; contact failure retained | 17.679 → 16.652 |
| `20260928-103756-eebe5435` | Chained improvement in acceleration energy | 10.668 → 10.668 |
| `20260928-104001-895f20da` | No verified improvement; unchanged input | Unchanged |

The chained clip's acceleration energy falls 387.490 → 334.588 while its peak is effectively unchanged. Do not describe that result as a reduced peak. All three selected candidates pass a separate geometry/target/channel audit. The fourth retains every attempted fraction and its failed objective checks.

Evidence: `reports/dynamics-studio-v1/verification/completion.json`, `retained-verification/completion.json`, their engine verifications, `tests.json`, `browser-verification.json`, and `preview.png`. Four backend tests and eight result-selection tests pass. The UI shows the grey character and failed-check label, allows version switching without losing the frame, and has no observed browser errors/warnings. The API uses the existing local origin/host checks and exclusive authoring-worker lock.

Implementation: `scripts/rig_dynamics_edit.py`, `verify_dynamics_studio.py`, the `/api/rig-dynamics-edits` route and Characters UI. Each job carries its transitive worker implementation snapshot and immutable request/input hashes. `rig_studio_job.py` and the live whole-support solver dependencies are unchanged. The server was restarted only after verifying the prior process identity and no active authoring worker.

## Continuing work

Whole-support coverage is now 18/24, with 6,480 independently verified input/candidate engine actor-frames; see `reports/whole-support-breadth-interim-v18/summary.json`. Six unfinished cases remain in the denominator. The live solver continues, and its next case is `motion-061-rig-01`. No quality promotion follows from completion counts.

Next extend target-preserving cleanup to joint/finger edits without dropping their authored targets, and investigate the completed partner interaction failure with a changed formulation. The prior projected partner trial did not improve overlap and must not simply be repeated. Broad semantic evaluation, calibrated capability controls and independent animator/cleanup evidence remain necessary before release.
