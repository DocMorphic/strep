# Finite actions, terminal release and continuing physics

2026-09-28. Development evidence, not motion or release approval.

Finite target-rig exports now include `runtime-finite.json`, `godot_finite_adapter.gd`, its base adapter, the opt-in prop consumer and setup instructions. `rig_studio_job.py` writes these for non-cycle transfer/corrected variants. Unsupported assets keep their animation and receive an explicit runtime-unavailable reason. Existing immutable exports are unchanged. The legacy method-track scene adapter is also unchanged; the new finite clock is a separate path.

The new clock holds the final pose while simulation time continues, so a released prop can finish falling after an action ends. Confirmed authored markers dispatch only when crossed, including markers on the last sample. Completion occurs after one terminal-sample interval. Silent seeks and reverse notifications never execute forward gameplay actions. Raw coarse clock steps remain event notifications, not retroactive physics; the prop consumer owns fixed 60 Hz steps. See [finite setup](../integrations/godot/FINITE.md) and [object setup](../integrations/godot/OBJECT-EVENTS.md).

## Experiment

`reports/godot-finite-events-v4` contains three preserved finite actions on three rigs: backpedal/check/stop (`motion-036-rig-01`, 150 samples), dance (`motion-011-rig-02`, 210), and jab/cross/retreat (`motion-006-rig-03`, 150). Combat is additionally tested with release on the terminal sample. Each is evaluated with root extraction enabled and disabled: **eight scenarios**. These clips have explicitly test-authored event bindings; they are not claimed to perform plausible grasps or throws.

Pinned Godot 4.7.2 GodotPhysics3D, headless, 60 Hz physics, 30 fps GLBs. Prop geometry, mass, placement, gravity and offset follow the preceding object study. Independent Python GLB interpolation reconstructs the hand/prop-center transform, including actor placement. The actual engine executes attachment, release, pause, recorded forward/backward preview, resume and restart, and reports floor contacts. A separate clock traversal checks initial/terminal events, coarse forward movement, reverse ordering, silent seeks, completion, invalid-input rejection and all-bone terminal pose hold. Source, implementation, request and output hashes are retained.

All eight pass:

- 9,176 recorded callbacks and 32 attach/release actions.
- 584 eligible free-flight step comparisons, plus actual floor contacts in all scenarios.
- Maximum independently checked grip matrix error: 3.816e-6; release linear velocity: 2.864e-5 m/s; angular velocity: 8.007e-5 rad/s.
- Maximum recorded preview-pose roundtrip error: 1.193e-7; maximum terminal all-bone matrix drift: 4.769e-7.
- 476–477 post-clip physics callbacks per scenario, with no repeating markers. Terminal release passes in both root modes.

Fixed v4 limits: grip/bone matrix 2e-5, held/preview matrix 1e-6, release linear/angular velocity 0.002, free-flight step error 0.0001. No human or semantic limit is inferred from these numerical tolerances.

## Bugs and retained attempts

The first finite trial found a real small-angle angular-velocity defect in the shared prop consumer. Terminal release had 0.155798 rad/s error despite correct event timing and linear velocity. Its quaternion axis helper returned a non-unit small vector near identity; multiplying that by the angle suppressed spin. The replacement computes a shortest-arc rotation vector with `2*atan2(length(q.xyz), q.w)`, preserving small rotations. Official [Godot quaternion implementation](https://github.com/godotengine/godot/blob/master/core/math/quaternion.cpp) corroborates the near-identity branch; the actual engine comparison establishes the observed defect and fix. The local consumer is fixed; upstream engine code is unchanged.

`godot-finite-events-v1` remains failed. Its event checker also used exact equality after JSON's decimal roundtrip; v2 compares event IDs/order exactly and timestamps within 1e-12 seconds. V2 passes all four extracted-root scenarios, with terminal spin error reduced to 1.554e-5 rad/s. `godot-event-object-small-angle-v1` reruns all four earlier cycle fixtures with the revised consumer and passes.

V3 adds skeleton-root mode and retains a failure on one preview basis: 1.192093e-7 roundoff exceeds the previous implicit 1e-7 comparison. V4 explicitly records a 1e-6 preview-matrix tolerance, matching the held-pose criterion; code, source motions and other limits are unchanged. Both reports remain, and the measured error is reported rather than described as exact restoration.

The first export test assumed an old corrected variant had a separate report; that fixture stores its report in the transfer variant. The event-edit test was corrected to use the actual transfer source. This also exposed an export gap: legacy finite contact candidates were skipped. Their runtime metadata now requires matching original/corrected GLB hashes and unchanged frame count/rate from the correction audit, then retains authored timing from that verified source. It does not inherit quality approval.

Final **13 tests pass in 7.75 seconds**, including a complete Studio event-edit job, unchanged GLB hash, terminal marker preservation, runtime metadata, ZIP CRC, embedded adapter/document bytes, the legacy corrected path and mismatched-source rejection. A real generated export is retained at `reports/godot-finite-package-v2/character-animation.zip`; the earlier 11-test package remains separately under v1.

## Limits and next work

Only the current target-rig finite export path is covered. Multi-actor scene GLBs and their attached objects are separate. One prop still owns one clock; multiple props, shared actor clocks, crossfade attachment ownership and coordinated two-handed/two-actor interactions need scene-level ownership. Preview resumes the saved live state; it does not roll back arbitrary external gameplay or solver caches. Held props disable collisions. No new model inference/training or action-quality approval occurred.

The broader support study and developer review continue independently. These engine checks do not resolve existing foot sliding, quarter-frame penetration, partner overlap, semantic accuracy, held-out validation or animator cleanup-time gates.

Reproduce using `.venv/Scripts/python.exe scripts/study_godot_finite_events.py <new-output-folder>`. Preserve earlier reports. Current source evaluates all eight scenarios; prior four-case sources are saved under each completed study's implementation directory.
