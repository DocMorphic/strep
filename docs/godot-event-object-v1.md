# Runtime authored attachment and physical release

2026-09-28. Development evidence only; no release gate or motion quality approved.

Follow-up: [finite playback and release](godot-finite-events-v1.md) found and fixed a small-angle release-spin defect outside this original fixture set. Use the current consumer/new exports for integration. The original package and study snapshots remain historical evidence; the updated four-cycle regression also passes.

New `scripts/godot_event_object_body.gd` connects a cycle's explicitly bound authored event IDs to an actual `RigidBody3D`. The body follows a world-space grip offset, inherits its sampled linear/angular velocity at release, and then uses engine gravity, damping and collisions. All changes occur through the physics direct-state callback. It owns the cycle at fixed physics steps so a release uses the pose at its authored event, rather than the end of an arbitrary coarse update.

The consumer is included, opt-in, in new runtime cycle packages with `GODOT-OBJECT-EVENTS.md`. No event bindings or physical quality are inferred. Existing saved studies and exports are unchanged. Integration instructions: [object events](../integrations/godot/OBJECT-EVENTS.md).

## Frozen experiment and results

`reports/godot-event-object-v2` reuses the four frozen runtime-reverse fixtures and their exact GLBs, spanning two rig families. Copies receive explicitly test-authored attach/release markers at one-fifth and three-fifths of the period. These software fixtures do **not** establish that a waving or locomotion character convincingly grasps an object. Their purpose is runtime integration.

Pinned Godot 4.7.2 / GodotPhysics3D, 60 physics Hz, 30 fps imported cycles, manual AnimationPlayer, extracted root placement with yaw 0.4 and world translation (2,1,-1). Prop: 0.12 m cube, 2 kg, zero linear/angular damping, center of mass at its origin, a nonzero local grip offset and rotation. A static engine floor provides collision response. The engine runs headless; no rendering claim is made.

Each case attaches, releases, pauses during free flight for five callbacks, previews a held state and free state, moves backward to a parked state, resumes at the saved live cursor, then completes and replays. Arbitrary signal injection and reverse notification cause no extra commands. The 128-sample test history expires old states. Independent Python GLB sampling checks world grip transforms and release velocities; free flight is checked against gravity and semi-implicit Euler before floor proximity/contact. Engine contact reports establish floor contact, not zero penetration or settled-object accuracy.

- All four cases pass, with 1,792 recorded callbacks and 16 correctly timed actions over eight sessions.
- Maximum independently reconstructed grip matrix discrepancy: 6.924e-7. Maximum held-pose matrix discrepancy: 5.514e-7.
- Maximum release linear-velocity discrepancy: 1.266e-5 m/s; angular discrepancy: 4.080e-5 rad/s.
- 314 eligible free-flight steps checked; maximum step discrepancy 1.590e-7 in the reported position/velocity comparison.
- Pause, reverse preview, resume, replay, actual floor contact and six invalid-command/binding checks pass for every case.

Before-run v2 limits: matrix 2e-5, held matrix 1e-6, linear/angular velocity error 0.002, free-flight step error 0.0001. The first trial `godot-event-object-v1` failed its held-matrix 1e-7 check on float32 engine basis roundoff (maximum 5.514e-7). It remains saved. Only that numerical limit was revised explicitly for v2; it is not presented as a previously passing result. Python reference asset/sampler caching also removed repeated file loading without changing its calculation.

## Controls and failures retained

`reports/godot-event-object-missing-velocity-v1` deliberately replaces release linear velocity with zero in a copied consumer. The independent check rejects it with 0.480640 m/s discrepancy while event timing and transport still pass. Top-level control success means the broken behavior was detected, not that the broken clip is approved. Production source is unchanged.

`reports/godot-event-object-faults-v2` injects a changed physics step, an externally moved clock and a non-rigid grip. All three stop with an explicit reason, retain the last valid prop pose (maximum matrix discrepancy 7.451e-9), disable collisions, zero velocity and emit no extra action. The first fault study `faults-v1` failed because its checker compared against the setting-change request boundary. Godot applies the tick-rate change after one additional valid old-rate step; v2 compares against the immediately preceding valid boundary. Consumer code was unchanged. Both reports remain.

Five runtime-package tests pass, and the existing full loop-generation/package regression passes (18.31 s). The resulting real ZIP and checked embedded consumer/docs are preserved in `reports/godot-event-object-package-v1`. Completed study sources are copied and hashed; new cycle export metadata advertises the opt-in consumer.

## Supported transport and remaining work

Reverse is recorded preview, with physics and action dispatch disabled. Resume returns to the saved live boundary. Restart restores this owned actor/prop session and permits the actions again. These operations do not undo external effects or serialize collision caches and other world objects. History branching, network rollback and arbitrary moving-world resumption are not implemented.

Current limits: one prop/clock, one first-cycle attach/release, centered rigid-body mass, attachment collisions disabled, 60 Hz validated. A scene-level owner for multiple props, two hands/actors, finite clips and crossfade event ownership is still needed. Attachment approach quality, scene interpenetration and physically plausible throws remain motion/contact problems. No developer ratings or independent animator cleanup measurements have been supplied.

Reproduce with `.venv/Scripts/python.exe scripts/study_godot_event_object.py <new-output-folder>`; append `--omit-release-velocity-control` for the detection control. The fault-audit script retains a fixed immutable output name; select a new name explicitly for a new run. Do not overwrite saved evidence.

Sources: Godot's [RigidBody3D integration callback](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html#class-rigidbody3d-private-method-integrate-forces) and [direct physics state](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html), consulted 2026-09-28. Body transforms/velocities are changed through direct state; released custom integration explicitly invokes engine gravity/damping integration.
