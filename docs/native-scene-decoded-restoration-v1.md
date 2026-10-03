# Decoded source-bound restoration

The optional restoration pass addresses measured underprediction in native scene
proposals. A first high-five step violated just one protected angular-acceleration
row by approximately 0.000048 rad/sÂ². Smaller steps introduced other Float32
rounding failures. The original source limits remain the acceptance authority.

```powershell
python scripts/native_scene_fit.py contacts.json permissions.json reports/my-restored-proposal --proposal-model storage-vector --iterations 4 --storage-cells 64 --restoration-steps 3
```

Use a fresh folder and the existing model-free/conic development dependencies.
Restoration is available only in `storage-vector` mode; its default remains zero,
preserving the preceding numerical behavior. Choose zero to four additional
restoration solves per primary iteration. This does not download models or assets,
run inference, add native keys or change the authored permissions.
Studio retains its existing defaults; this optional CLI path is not yet wired
into the authoring controls.

## What changes

Each rejected full step has actual residuals from a reloaded GLB. The pass compares
those residuals with the original affine vector-norm prediction. For every
protected edit, displacement and source-rate row, it doubles the larger of the
positive decoded overrun and positive measured underprediction, converts that
quantity through the original row scale, and accumulates a proposal reserve.
Only the affine subproblem's corresponding caps become smaller. Contact caps,
the decoded source caps, tolerances and all sampling populations stay unchanged.

Passed rows with underprediction receive margins too: repairing only failed rows
exposed different nearly active constraints in the next solve. The original
vector base, Jacobian and trust box remain fixed during the local repair. Each
new candidate is exported and decoded again. Only an improving candidate passing
every original protected row can be accepted. A failed or unavailable repair
leaves the existing storage-cell/backoff path available. All attempts and margins
remain recorded; originals stay selected even when native conditions pass.

This is a measured-error heuristic, not a global error bound, robust feasibility
certificate or continuous-time safety proof. Fixed protected conflicts, depleted
budgets and numerical solver failures remain failures. Solver status cannot
override the unchanged decoded checks. Up to three extra solves in the study
increase compute cost; equal primary iteration counts are not equal work budgets.

## Development observations

The first retained variant tightened only currently failed rows and accepted no
high-five step. Its first correction changed one failing row into three, then
nine. That unsuccessful variant and its original captures remain saved. The
revised rule includes all observed protected underpredictions.

On the same humanoid motions, contact requests, permissions, four primary
iterations and 0.02 trust fraction, the revised high-five accepts four steps
without increasing any original source limit. Hand separation decreases from
206.232573 mm to 177.976173 mm but still fails the 30 mm target. This is contact
improvement with preserved sampled motion bounds, not a completed interaction or
animator-visible quality approval. The earlier unconstrained excess-sharing vector
trial reached about 170.46 mm while failing source rates; it is a separate result.

No new training data is admitted and no checkpoint is changed. Collision,
continuous motion, actual engine behavior and human review require separate
evidence. The broad release matrix and held-out trials remain open. Detailed
local evidence lives under ignored `reports/native-scene-decoded-restore-*` and
`reports/native-scene-rotation-guard-diagnosis-v1` folders.

The sphere outcome remains unchanged: left/right position errors are approximately
2.219/2.244 mm against 2 mm, with right hold speed 10.192 mm/s against 5 mm/s.
Actual Godot observations reproduce the high-five improvement at approximately
177.930 mm in both import and native-resource manual authoring modes. Its explicit
diagnostic Y=0 plane still fails, and imported/source skin differences of
0.131–0.137 mm exceed the separate 0.1 mm limit. Sphere geometry and skin-position
conditions pass at the declared times, while contacts fail. All four combined
engine jobs fail; no original selection changes. The sparse geometry populations
remain identical to the previous study apart from the new source binding.

Independent replay reproduces 38 control vectors and 54 GLB exports byte-for-byte,
the decoded residuals, accepted protected rows and 18 restoration margin updates.
Margin arithmetic uses the recorded method's Jacobians; it is not an independent
derivative or solver implementation. All source-rate arrays match the preceding
vector baseline exactly, and final source-rate failures are zero. Independent
full-skin contact effectors agree within 4.45e-16 metres; partner/object target
interpolation remains shared. All 229 fitting-study files rehash. Separate raw
imported-slot reconstruction checks 4,134 contact point samples, all contact speeds
and 397,232 vertices at geometry times, with contact differences below 2.23e-16 m
and all 225 engine-study files rehashed. Full skin-error curves between geometry
times are not independently replayed. All 330 focused model-free tests pass.
No GPU, physics, event playback, continuous collision, human quality, training
improvement or release approval is established.
