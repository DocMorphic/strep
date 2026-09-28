# Acceptance on exported poses

The first individually guarded release trial passed its unencoded constraints but failed two frozen envelopes after GLB export. Centroid coordinate changes of about1.27e-7m were amplified by velocity and acceleration differences. The acceptance tolerances remain unchanged.

`scripts/serialized_pose.py` evaluates this project's existing encoder in memory: localize world transforms, store animated translations and quaternions as float32, normalize rotations as the loader does, restore static-node transforms, and compose the hierarchy. Animated scales are reset to one exactly as `prepare_animated_node` does. Half-frame sampling uses the encoder's float32 key times and the loader's interpolation convention. This models `rig_loop.encode`, not every possible glTF encoder or asset layout.

`reports/serialized-pose-proof-v1` compares against four retained actual exports: the three stationary-gesture refits on distinct rigs and the previous guarded backpedal correction. It checks all600 integer poses,596 half-frame poses, every node matrix and every skinned vertex. Maximum matrix error is8.89e-16, skinned coordinate error1.56e-15m, and foot-acceleration norm error1.13e-12m/s². All satisfy the predeclared reproduction tolerances. Inputs, implementation snapshots and results are hash-bound. This is an export-reproduction proof, not evidence that the motions are realistic.

The guarded-release solver now has an optional serialized-evaluation mode. Objective and constraint values use those stored poses. Every accepted coordinate update also checks serialized half-frame floor clearance and local rotation against its neighbors. The analytic unquantized skin Jacobian remains a proposal approximation; it is explicitly not claimed to differentiate float quantization. Final GLB decoding and actual engine import still run independently.

Fifteen focused tests pass across the solver/acceleration and export-evaluator suites, including both the original smooth mode and the serialized mode on an avoidable synthetic acceleration spike. The latter recomputes final energy from quantized poses and verifies that half-frame acceptance ran beyond initialization. Additional edge tests independently compare a179°→−179° transition with SciPy SLERP at the actual stored key times, verify static matrices and encoder scale behavior, and reject invalid inputs. The old trial and its implementation snapshot remain intact.

A separate three-sweep trial, `reports/guarded-release-serialized-v1`, starts from the same held parameters with the same budgets and acceptance limits. Its protocol binds the completed pose-reproduction proof. It completed normally, preserving every output and unsuccessful solver status.

## Completed serialized trial

The independent `reports/guarded-release-serialized-audit-v1.json` freshly decodes300 integer poses and298 half-frame skins and checks450 actual Godot actor-frames. All eight frozen-envelope checks pass: acceleration, support speed, hover, held root preservation, protected joint, full/half-frame floor, local rotation and no new release failures. Maximum decoded acceleration-envelope excess is2.53e-13m/s² and speed excess1.89e-10m/s, both within the original audit tolerances. No tolerance was widened.

| Measure | Held | Serialized evaluation trial |
| --- | ---: | ---: |
| Acceleration excess energy |225.4282|135.8997|
| Integer floor peak (mm) |2.349|3.958|
| Half-frame floor peak (mm) |2.031|2.534|
| Root acceleration peak (m/s²) |4.478535|4.478535|
| Local rotation peak (degrees/frame) |19.959219|19.959219|
| Failing release windows |3|1|

Only `Right_every_release_acceleration_no_worse` still fails the original full comparison. Right release19 is5.066627m/s² against its3.468900 limit, improved from held7.445875 but worse than the unencoded trial's3.561474. Both methods resolve releases86 and109 without new failing release windows. The serialized method also passes the original global foot-acceleration checks. Different numerical trajectories produce different tradeoffs; this is not a claim that every metric improved over the previous method.

All450 coordinate visits remain recorded:358 optimizer successes,68 line-search failures and24 iteration limits;391 updates passed the separate acceptance checks. The last-sweep parameter change is0.045602, so convergence is not established. The smooth Jacobian is an approximation to a quantized objective; unsuccessful statuses must not be hidden.

The demonstrated export-precision failure is resolved for this measured fixture. The motion itself is not approved. The next useful correction is a coupled update across neighboring frames around release19, retaining the same exported-pose checks; repeated single-frame updates may be constrained by their fixed neighbors. That is a method hypothesis to test, not a diagnosis of an optimum or proof of infeasibility. Final engine import, broad held-out action/rig evaluation, animator review and cleanup-time evidence remain separate requirements.
