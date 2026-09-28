# Moving scene boxes in offline release bakes

Studio's **Simulate object release → Floor + moving scene boxes (Jolt)** follows the saved trajectories of every other scene box. The selected prop becomes a dynamic rigid body; the other boxes retain their authored motion and have infinite effective mass. They do not react to impact. Actors remain animated and are not collision bodies. This is a release component, not a solved lifting, carrying, balancing or two-person interaction system.

The existing floor-only and static modes keep GodotPhysics3D. Moving mode explicitly selects **Jolt Physics** in the pinned Godot 4.7.2 executable. Runtime verification checks the actual direct-state class, not just the requested project setting. Both modes remain offline: exported GLBs contain baked animation and require no runtime physics.

## Clock, geometry and verification

`moving_release_colliders.py` samples the same integer-frame object poses used by export, with linear position interpolation and quaternion SLERP at 240 Hz. One sample before release establishes incoming kinematic velocity. Each physics callback records the actual collider state before setting the next target, avoiding a one-tick shift. Geometry, materials, position, rotation and estimated velocity are verified at every physics step. Pose limits are 1e-6 metres/matrix element; linear and angular velocity limits are 2e-4 m/s and rad/s. Large coordinates or extreme motion can fail these fixed precision screens; failed outputs stay on disk.

Jolt uses explicit 1 mm penetration slop and zero collision-margin fraction, so the collision boxes have sharp corners matching the exported boxes. Static-mode contact settings are not silently treated as Jolt settings. Mass, inertia, initial velocity, gravity, zero damping and disabled sleeping are audited. CCD is enabled, but the numerical collision screens are discrete and do not establish continuous collision correctness.

The collision audit checks 15-axis oriented-box separation at the simulation rate, reported contact IDs, and final relative linear/angular motion against each observed supporting collider. Relative linear motion compares both rigid motions at the released body's centre of mass. A platform carrying a prop can have nonzero world speed and still meet the settling screen. Geometry/contact and naturalness judgments remain separate. Contact records have the existing 16-contact buffer limit.

## Evidence and limitations

The frozen fixture in `reports/moving-collider-v1` places a 20 cm crate above a translating/rotating platform. An existing actor clip is preserved at a distance solely to check shared-clock export; no grip or new human interaction is claimed. Studio job `20260927-132952-35ac417f` releases the 2 kg crate at frame 2, friction 0.6 and bounce 0. The authored platform advances at 0.12 m/s horizontally, 0.05 m/s upward and 0.2 rad/s in yaw after release.

- All 1,417 simulation samples passed runtime/clock checks. Maximum crate/platform penetration was 4.965e-7 m; first reported contact was at source frame 5.75. Final relative linear speed was 2.146e-6 m/s and angular speed 5.906e-7 rad/s. These tiny values describe this gentle fixture, not a general accuracy guarantee.
- Independent eight-corner SAT matched the production centre/radius SAT. The 359 whole/half-frame decoded samples had maximum penetration 4.552e-7 m, with no authored-prefix overlap.
- Inputs, actor motion, platform track, release prefix, events and portable paths were preserved. Five served artifacts matched saved hashes; three GLBs had zero validator errors or warnings.
- The relocated ZIP imported into Godot with separate actor/object GLBs on one clock. All 180 frames, all 77 actor bones and both objects passed the existing precision screens. Maximum object rotation-element error was 9.287e-8; actor position error was 2.980e-7 m.
- Actual browser checks covered static-mode rejection, moving-mode submission, completion, rediscovery after reload, playback and final framing. A stale contact label when loading a scene with no targets was fixed. No console errors were observed.

Earlier probe evidence remains in place. Native Godot Physics had maximum angular-velocity error 0.034375 rad/s for a prescribed 0.2 rad/s small-step rotation. The first attempted Jolt comparison used an invalid backend label (`JoltPhysics3D`) and is **not valid Jolt evidence**. The corrected `moving-collider-clock-jolt-v2` run reports `JoltPhysicsDirectBodyState3D`, with maximum angular error 4.312e-5 rad/s. Tests also cover other rotation axes, stationary geometry, 480 Hz, free fall, floor impact, tampered records, malformed requests and the immutable scene worker.

The full-project goal and all release gates remain open. No model was trained, no held-out motion coverage was added, and no independent animator rating or cleanup time was collected. Next work includes actor collision representation/interaction response, broader action and rig evaluation, offline product packaging, and independent review.

## Primary references

- [Godot: AnimatableBody3D](https://docs.godotengine.org/en/stable/classes/class_animatablebody3d.html): prescribed motion and estimated velocities.
- [Godot: Using Jolt Physics](https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html): exact backend setting and behavior differences.
- [Godot ProjectSettings](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html): Jolt penetration slop and collision-margin fraction.
- [Pinned native kinematic integration](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/godot_physics_3d/godot_body_3d.cpp) and [basis axis-angle conversion](https://github.com/godotengine/godot/blob/4.7.2-stable/core/math/basis.cpp): inspected to diagnose small-angle velocity precision. The attribution to float axis-angle estimation is a source-based diagnosis, not an engine patch.

Run `python scripts/verify_moving_release.py` to repeat the independent artifact check without rerunning simulation. See `reports/moving-collider-v1/tests.json` for the exact test snapshot and logs.
