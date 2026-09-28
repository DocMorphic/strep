# Moving-object geometry gap

Update: subsequent scene/solver/export integration is recorded in [primitive scenes](primitive-scenes-v1.md). The remainder describes this original snapshot.

A code inspection during release-fixture preparation found a current restriction that prevents treating the broad reserved object scenarios as runnable release fixtures.

- `scene_constraints.sample_object` accepts only `shape: box` with `size_m`; its existing actor/object penetration path calls box-vertex depth.
- `scene_object_export.export_objects` generates animated box nodes and box meshes.
- `scene_release_job` validates box dimensions, serializes `size_m`, checks box separation at release and derives box bottom height for floor checks.
- `object_dynamics.uniform_box_inertia` provides the existing box mass/inertia model.

These are connected assumptions. Adding a sphere mesh only to the viewer would leave collision and dynamics inconsistent. Static terrain and convex collider support are separate paths; they do not establish general moving-prop support.

The release prompt reservations include balls, handles, tools, a pitcher/cup, furniture and hanging supports. Do not stand in five differently sized boxes for this coverage or label the reserved scenes complete. Five geometry instances alone would not establish shape, grip, articulation or partner-contact diversity.

The next geometry extension needs one explicit versioned object-shape contract used by trajectory sampling, contact transforms, signed-distance/intersection queries, inertia/release behavior and mesh export. Begin with exact sphere and existing oriented-box behavior, keep unsupported articulated/deformable objects explicit, then add measured mesh/convex support with consistent grip targets. Validation must include rotated/translating objects, inside/outside/tangent collision controls, exported shape dimensions and actual engine release behavior. Preserve existing box outputs and compare against them; do not change live contact-study dependencies.

This records an unresolved implementation requirement. No shape support was added here, no reserved motion was run, and no release gate was promoted.
