# Sphere release development study

Offline object release now supports canonical boxes and spheres, alongside legacy `size_m` box records. The same geometry drives mass/inertia, initial overlap guards, actual engine collision shapes, floor and collider audits, and baked scene export. Sphere release defaults to Jolt Physics at 240 Hz; legacy box defaults remain unchanged. Prescribed scene props retain their authored motion and do not react to impacts. Actor collision envelopes remain an optional approximation with no actor response.

Sphere/sphere and sphere/box checks use analytic signed distances. Sphere/convex checks include triangle faces, edges and vertices; box/convex checks retain separating-axis calculations. The legacy report key `final_signed_axis_gap_m` is retained for compatibility: sphere rows contain a Euclidean signed surface gap, while box rows use the existing axis-separation measure. These are discrete simulation-time checks, not continuous collision guarantees.

## Backend comparison and retained failure

A development drop fixture uses a uniform solid sphere of radius 0.2 m, initially 1.5 m above the origin, with zero initial velocity. The original GodotPhysics3D/240 Hz run failed the unchanged 10 mm maximum-penetration screen. The matched comparison retained all four outputs:

| Backend | Physics rate | Maximum floor penetration | Collision/settling screen |
| --- | --- | --- | --- |
| GodotPhysics3D | 240 Hz | 19.921 mm | Failed |
| GodotPhysics3D | 480 Hz | 4.083 mm | Passed |
| Jolt Physics | 240 Hz | 0 mm reported | Passed |
| Jolt Physics | 480 Hz | 0 mm reported | Passed |

This motivates the sphere default, but does not establish reliability across arbitrary speeds, scales, shapes or actions. Explicit backend selection remains available. The report checks the active engine backend, installed shape and dimensions, inverse inertia, clock, and prescribed collider motion.

## Saved scene and actual import

The reproducible study script is `scripts/study_sphere_scene_release.py`. It requires the existing local development actor and trajectory; it is not a clean-clone example. It replaces an existing box with a 0.25 m sphere, projects grip targets onto its surface, and retains the original actor and authored object trajectory up to release at frame 121. A second, distant 0.2 m sphere follows a prescribed trajectory. This is an authored development fixture, not sphere-conditioned model generation.

The completed job preserves the actor, authored prefix, contacts and previous events. An independent file audit checks provenance hashes, package contents, portable paths, and decoded full-key and half-frame object transforms. A relocated ZIP is then imported into Godot: all 180 actor frames across 77 bones and 360 object-frame observations pass. The actor's maximum position error is approximately 0.36 micrometres. HTTP delivery and browser rendering were not verified.

Successful import retains these quality failures:

- Left grip maximum error: 25.034 mm; 61/61 contact samples within 30 mm.
- Right grip maximum error: 112.082 mm; only 3/61 samples within 30 mm.
- Maximum actor/sphere skin-vertex penetration: 107.549 mm.
- Release floor penetration: 0.112 mm. Final linear speed: 0.0498 m/s; angular speed: 0.2570 rad/s.

The floor proximity/linear-speed screen passes, but the stricter collision-and-settling screen fails because angular speed exceeds 0.1 rad/s. Settling is not the right acceptance criterion for every rolling or bouncing action; this experiment retains its existing failure rather than changing the criterion after observing it. The distant sphere has no impact in this scene; a separate engine test checks a moving sphere pushing the released sphere.

## Verification and scope

Seventy targeted Python tests pass, including actual Godot/Jolt free flight and spin, installed sphere geometry, sphere-on-floor/box/sphere contacts, box-on-sphere contact, prescribed moving-sphere impact, and saved box/sphere jobs in static and moving modes. These checks require the provisioned engine and development fixtures.

Local evidence is retained under `reports/sphere-release-backend-v1`, `reports/scene-release-jobs/sphere-development-v1`, and `reports/sphere-release-integration-v1`; generated outputs are excluded from the public source repository. The backend comparison binds simulation reports by hash, and the saved job retains implementation snapshots.

No complete sphere grasp fit, new checkpoint training, held-out release trial, or human approval occurred in this study. A subsequent [measured sphere grasp fit](sphere-contact-fit-v1.md) retains contact, finger-penetration and temporal failures and identifies pre-release object/floor intersection in the copied trajectory. Arbitrary prop meshes, responsive actors/partners, and reliable generated interactions remain open. All project release capabilities remain unapproved.
