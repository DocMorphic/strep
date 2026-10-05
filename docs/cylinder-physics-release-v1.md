# Cylinder release and measured engine limits

Saved-scene release now accepts versioned box, sphere and cylinder geometry. Cylinder release installs `CylinderShape3D`, its radius and full height, and the exact uniform-solid inertia already defined by `Geometry.uniform_inertia`. The engine receipt checks those installed dimensions, inverse inertia, mass, zero damping, initial pose/velocities, backend and every physics tick. An authored 30 Hz prefix stays unchanged through the release sample; the remaining motion becomes an editable baked track and GLB.

The existing static and prescribed moving prop routes use the same geometry. Cylinder-versus-box/cylinder checks use the [nested-prism penetration bounds](cylinder-collision-bounds-v1.md); sphere offsets remain analytic. Cylinder-versus-convex actor-envelope checks include the entire supplied hull, every hull triangle edge and every nonzero edge-cross axis. Planar triangulation diagonals add redundant valid axes; no near-parallel cutoff, rounded direction deduplication or selected subset removes a real edge. Complete 4–128-vertex convex geometry and the cylinder's 4–128-segment budget retain explicit resource rejection.

Each cylinder collision audit retains a lower/upper penetration value, approximation errors, arithmetic pad and every simulation tick. Its acceptance calculation uses the upper value. Release-start guards reject depths above **1 mm**, including an analytic floor guard now applied to every primitive. The collision/settling screen keeps **10 mm** penetration and final projection-gap limits and **0.1 m/s / 0.1 rad/s** motion relative to reported supports. Proximity without observed engine contact never establishes support. A positive projection gap is not Euclidean distance. Float64 padding is not certified interval arithmetic or continuous collision certification.

Jolt is the default when the released body or a static support is a cylinder; sphere release keeps its existing Jolt default. Box-only releases retain their previous default. An explicit backend remains available for reproducible comparisons, and moving props still require Jolt. Collision margin fraction stays zero and solver slop stays 1 mm in the study. No damping was introduced to force settling. Actor envelopes are prescribed kinematic geometry with infinite effective mass: their motion does not respond to the released prop. This is one released dynamic body, not simultaneous dynamic ownership of multiple props or a solved grip.

## Reproduction and retained results

Use an existing project Python environment with the CPU dependencies and the pinned Godot 4.7.2 console executable. This experiment generates tiny primitive fixtures, not model motion or downloaded characters. Run from the repository with a **fresh** local report path:

```powershell
python scripts/study_cylinder_release.py --output reports/my-cylinder-release-study
```

The command owns the production-worker lock and executes cases serially. It saves source tracks, geometry/inertia requests, method snapshots and hashes, engine logs and all ticks, bakes, CPU GLB sample comparisons, complete collision bounds and every failure. It does not overwrite an earlier report. Successful execution records a result even when the collision/settling screen fails.

The retained first study completed **19 fixtures / 9,139 physics ticks** at 240 Hz. Both backends received the same freeflight, upright/tilted floor drop, static box/cylinder/sphere support, and box/sphere-on-cylinder cases. Three additional Jolt cases use translating, rotating prescribed box, cylinder and noncentral convex supports. All 17 contact fixtures reported the intended support; 12 passed the combined collision/settling screen. Freeflight intentionally has no final support and is evaluated separately.

| Retained failure | Maximum depth | Final settling issue |
| --- | ---: | --- |
| GodotPhysics3D upright cylinder on floor | 16.031 mm | Penetration exceeds 10 mm |
| GodotPhysics3D tilted cylinder on floor | 10.961 mm | Penetration exceeds 10 mm |
| GodotPhysics3D box on cylinder | 16.398 mm | Penetration exceeds 10 mm |
| GodotPhysics3D sphere on cylinder | 16.398 mm | Penetration exceeds 10 mm |
| Jolt tilted cylinder on floor | 0.062 mm | Still rolling at 0.142 rad/s after 3 s |

The last case fails the stated resting screen; this does not establish that rolling is an invalid game action. Its final speed is 0.028 m/s. Jolt passes the upright cylinder drop, all five static-support fixtures and all three prescribed-support fixtures. These finite fixtures motivate the cylinder-world default; they do not guarantee arbitrary geometry, initial velocity, impact, timestep or stability. The original failures remain saved.

All 19 bakes preserve their authored prefix. CPU sampling of every exported GLB frame stays within the original 1e-6 position/rotation-element checks; observed maximum position discrepancy is 4.468e-7 m. Both freeflight trajectories match their discrete integration reference within 1.239e-6 m. This verifies the source export clock, not Godot GLB import or GPU playback.

The final frozen public-source check passes **165 tests in 14.32 s**, with 21 engine cases explicitly skipped in the isolated copy. It includes eleven independent full-Minkowski-hull comparisons for cylinder/convex bounds, 32/64/128-vertex irregular hulls, rigid invariance/refinement, preserved near-parallel axes, all primitive release entries, whole-world backend selection, floor/static/moving/actor-proxy start guards, contact ownership and unchanged Studio build output. A separate current-source serial engine regression passes **95 tests in 19.01 s**, including 25 actual simulations / 11,905 ticks and the previously supported box/sphere/moving/convex paths. It checks the cylinder freeflight spin, installed inertia and shape, preserved prefix, rejection of altered receipts and default mixed-shape support contacts.

Two intermediate validation failures remain saved locally: the first isolated checker tried to collect an older Torch-dependent geometry suite in the model-free environment; its release-entry check now belongs to the independent release suite. The first actual regression passed 94 checks and failed decimal dictionary equality for Godot's Float32 cylinder dimensions. The corrected assertion uses the existing 1e-6 installation tolerance; no physics/contact limit changes. The fresh complete checks above bind the final source. The 19-case study retains its original method snapshot; later default selection and request-helper refactoring are separately covered by the current-source regression.

Godot's [CylinderShape3D documentation](https://docs.godotengine.org/en/stable/classes/class_cylindershape3d.html) documents the shape properties and notes known collision bugs. Its [Jolt integration documentation](https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html) describes the backend and collision-margin behavior. Those primary references inform the experiment; the local measurements above establish its outcomes.

## Evidence boundaries

The scene validator and immutable source snapshots now connect cylinder bounds to both prop and optional actor-envelope routes. Studio's built source lists the available shapes and preserves existing release controls. Live Studio, HTTP endpoints, complete production actor jobs and browser interactions were not exercised. The engine fixtures contain no reconstructed or generated character, animator review, anatomical region selection, partner response, learned editing, training, rendered/GPU evidence or held-out action/object/rig release evidence. Every quality/release approval remains false and all fourteen release-matrix evidence arrays remain empty.

Next work must address the broader authoring path: simultaneous hands/props, physical ownership transitions, object and partner response, shared scene import/playback, held-out rigs/actions/objects and the developer review chosen by the user. Cylinder integration supplies geometry needed by those actions; it does not complete their motion semantics or quality criteria.

Local immutable receipts: study SHA256 `8f42cba910d2130836d87f540cd65b8024fd71036963abef302acba1f77e8484`; final source-check SHA256 `e91d86c8651b7ca0f496bab6a2c5488c06630407a858a6fb74884867dd538d2d`; current engine-regression SHA256 `68ddc9aed816b7db5d415b356a7dabaa7c625a047265756071262910ee183798`. Reports remain ignored local artifacts rather than public character/model payloads.
