# Object dynamics diagnostic

2026-09-27. This extends the same full-project goal beyond joint/contact accuracy. It adds a reusable sampled rigid-body diagnostic and evaluates existing exported box interactions. It does not train a model or alter the preserved animation.

`scripts/object_dynamics.py` accepts center-of-mass world positions, body-to-world quaternions, sample rate, mass, inertia tensor, gravity and explicit support phases. It estimates the non-gravity net force `m(a-g)` and the torque about the center of mass. The rotational calculation includes angular acceleration and the gyroscopic term. These are standard Newton–Euler quantities; see Lynch and Park's [Modern Robotics, section 8.2](https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-2-dynamics-of-a-single-rigid-body-part-1-of-2/). The result describes a required net wrench, not whether hands, ground or friction can supply it.

Translation uses central second differences. Rotation uses adjacent SO(3) interval logs expressed in world coordinates. There is no smoothing. Endpoints have no derivative estimate; samples crossing a declared phase boundary are retained but excluded from phase aggregates. Near-180-degree rotation steps are rejected; faster-than-sample motion can still alias. Mass/inertia/clock/rotation/phase validation prevents silently inventing missing support. A released object is not automatically labeled free flight.

## Existing attachment experiment

`reports/object-dynamics-v1/protocol.json` freezes source hashes, assumptions, implementation and metrics before this diagnostic run. It is exploratory reuse of two known failed fixtures, not a held-out quality study. The full tracks remain in the report. Three hypothetical masses (1, 5 and 20 kg), a uniform-density solid box with its center at the geometry origin, and Y-up gravity of 9.81 m/s² are explicitly assumed. Actual mass, inertia, contact forces and grip capacity are unknown.

The original attachment runs grasp at frame 60 and release at frame 121 of 180 samples. Both released boxes remain stationary for all remaining 59 samples. Their lowest corners stay **39.86 cm** (seed 11) and **37.42 cm** (seed 22) above the Y=0 floor. Under the stated assumptions that track requires a constant upward non-gravity force of **9.81, 49.05 or 196.2 N**, depending on assumed mass. The floor cannot supply that force across the gap; an additional support or a different post-release trajectory would be needed. Other environmental contacts are not measured by this diagnostic.

For the 5 kg sensitivity case, peak net force while attached is 57.46 N / 61.79 N and peak COM torque is 0.984 Nm / 2.630 Nm for seeds 11 / 22. These are requirements, not measured forces or a strength rating. Adjacent interval velocities change by 0.0649 / 0.2795 m/s at release. Those secant differences are diagnostic values, not impulse measurements or exact derivative continuity tests.

## Verification and limitations

Fourteen focused tests pass, covering analytic stationary support and ballistic trajectories, nonprincipal-axis gyroscopic torque, coordinate invariance, quaternion sign changes, phase boundaries and invalid assumptions. The initial run had one exact floating-point equality assertion fail; it was changed to a 1e-12 analytic comparison. The failed and final logs are retained.

`verify_object_dynamics.py` independently checks translation second differences, linear mass sensitivity, all original input hashes and 360 samples from the existing exported GLBs. Exported object positions differ by less than 3e-8 m. Differentiation amplifies export precision: at 1 kg, maximum force-component differences are 8.54e-5 N and torque-component differences reach 2.79e-6 Nm. Original and decoded diagnostic reports are both retained. This is not a new engine simulation or engine-import claim.

No hand-force allocation, friction cone, self/partner collision, articulated-body dynamics, impact response, balance or naturalness is certified. Human ratings and cleanup time remain missing. Existing point/orientation/collision failures are unchanged.

## Next implementation

Add an explicitly selected dynamic-release policy: preserve the authored track through release, carry incoming linear/angular velocity into an offline rigid-body simulation, and bake the simulated object track. Record mass, inertia, gravity, collision geometry, friction, restitution and timestep assumptions. Handle floor impact explicitly instead of clamping a falling object or silently freezing it. Keep the original authored-tail version and independently recheck hand/object collisions, event timing, exported trajectories and actual engine playback. This can address release behavior without pretending to solve grasp, two-hand lifting or character balance.

Reproduction uses a new output directory for a fresh study; `study_object_dynamics.py prepare` refuses to overwrite the existing one. The current study can be audited again with `.venv/Scripts/python.exe scripts/verify_object_dynamics.py`.

The existing local Godot runtime is the first candidate for offline baking. Its official [RigidBody3D documentation](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html), checked 2026-09-27, provides mass/inertia, linear/angular velocity, collision shapes, damping and a force-integration callback. Initial state and observed transforms should be captured through [PhysicsDirectBodyState3D](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html). Avoid repeatedly setting transforms during simulation. Pin and record the actual installed engine/backend, step size and material settings; test sample-clock alignment against an analytic free-fall control before running the attachment fixtures. This simulation adapter is not yet implemented.

Full integration suite after the diagnostic: **494 passed**, five existing warnings, 134.97 seconds. Evidence: `reports/object-dynamics-full-tests.log` and `reports/object-dynamics-v1/test-results.json`.
