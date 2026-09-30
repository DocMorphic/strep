# Cylinders in authored scenes

Strep now carries a closed cylinder through scene sampling, analytic skin collision measurements, surface-normal constraints, v8 clearance fitting, regional contact residuals, grip picking, previews, GLB export and shared Godot playback. This broadens prop geometry beyond boxes and spheres. It does not establish a successful generated cylinder grasp or cylinder physics release.

## Geometry contract

```json
{
  "geometry": {
    "schema": "strep-object-geometry-v1",
    "shape": "cylinder",
    "radius_m": 0.23,
    "height_m": 0.7
  },
  "keyframes": [
    {"frame": 0, "translation_m": [0, 0.35, 0], "rotation_xyzw": [0, 0, 0, 1]}
  ]
}
```

The origin is the center of mass of the assumed uniform solid. Local Y is the cylinder axis; `height_m` is the full height. Radius and height must be finite positive numbers. Legacy dimensions cannot accompany a versioned descriptor. Older box/sphere-only readers reject the new shape; no fallback shape is substituted.

Signed distances use radial distance in local XZ and distance to the two caps. Gradients transform back to world space. The exact rim has no unique surface normal, so grip authoring rejects it. The axis is ambiguous only when the nearest boundary is the side; the center of a cap has a valid normal. Frontend and backend use the same existing 1 micrometre surface tolerance.

For a world cylinder axis `a`, radius `r` and height `h`, the AABB half extents are `r sqrt(1-a²) + h abs(a)/2`. Floor placement uses this extent and the enclosing radius `sqrt(r²+(h/2)²)` to bound intermediate SLERP orientations, not just the keys. Uniform inertia is diagonal: transverse components `m(3r²+h²)/12`, axial component `mr²/2`. These mass properties are mathematical helpers, not a validated dynamics bake.

Cylinder clearance uses Euclidean signed distance in both the legacy v8 solver and the regional objective. Historical box face-inflation and sphere behavior are preserved. The historical sphere-specific regional-track experiment explicitly rejects cylinders; the general scene region compiler, residual and measurement paths handle them.

## Preview and export

Both the Three.js preview and exported mesh have closed caps and a matching radius/full height. Side shading is radial; cap normals are axial. Segment counts increase until the radial inset bound `r(1-cos(pi/n))` is at most 1 mm, with a resource limit of 256 segments. A request exceeding that limit fails explicitly. Contact picking intersects the analytic cylinder rather than its inscribed render triangles.

The GLB stores the geometry descriptor and mesh approximation alongside full translation, quaternion and unit-scale tracks. The cylinder fixture with radius 0.23 m and height 0.7 m uses 64 segments, 256 triangles and a 0.277045 mm inset bound. The analytic primitive remains authoritative for collision measurements.

## Verified results, 2026-09-30

- **138 distinct focused Python tests pass**, covering geometry, finite-difference and autograd agreement, independent volume-inertia quadrature, dense bounds, continuous floor placement, mesh winding/closure, real skin collision measurements, regional penetration rejection, export clocks, existing release paths and the Studio build. The main regression command passed 132 tests; two additional cylinder tests and four build tests also passed.
- **453 frontend/backend grip cases pass**: 450 transformed box/sphere/cylinder hits plus three near-surface tolerance cases. Side/cap hits, tangent rays, inside-out rays, misses, rim rejection and picker lifecycle are exercised with actual Three.js, without a browser or network. Separate mesh checks cover three cylinder aspect ratios and invalid inputs.
- **`reports/cylinder-primitive-import-v1/verification.json`** passes actual Godot 4.7.2 import of box, sphere and cylinder tracks, 31 frames each (**93 object-frame observations**). Cylinder vertex surface error is 9.55e-9 m; attached material-point error is 6.09e-8 m. Imported vertex coordinates reproduce exported coordinates within floating-point precision. These are vertex/transform errors, distinct from planar mesh inset.
- **`reports/cylinder-scene-runtime-v1/verification.json`** passes **405 actual engine pose observations** with one existing actor and an authored cylinder track. Maximum object matrix-element error is 7.32e-7; actor error is 8.16e-7. Forward/reverse event order, automatic transport, callback mutation rejection and unload pass. The old box trajectory is reused only as an authored playback fixture; its old contact claims are removed. No cylinder dynamics are inferred from it.

The engine executable is checked against its recorded acquisition hash. Both studies retain method snapshots, input/output hashes, engine logs and failed-check behavior. The runtime verifier compares engine output with independently decoded GLB transforms. Raw reports and assets stay local and ignored; this document and the methods are public.

Reproduce on the configured development machine:

```powershell
.venv\Scripts\python.exe scripts/verify_primitive_scene.py reports/<new-import-folder>
.venv\Scripts\python.exe scripts/study_primitive_scene_runtime.py reports/<new-playback-folder> --shape cylinder
```

The second command requires the retained development actor/scene assets. These commands are not a self-contained public installer. The model-free public CI exercises primitive mesh closure/inset and strict JavaScript geometry parsing; it does not substitute for local Torch, character or engine checks.

## Remaining work

Cylinder physics release, including use as a static or moving release collider, is explicitly rejected before simulation. Godot's official documentation warns of known cylinder collision bugs; the next dynamics study must test the actual chosen backend and collision geometry, preserving failures rather than silently switching to a box or capsule. [Godot CylinderShape3D documentation](https://docs.godotengine.org/en/stable/classes/class_cylindershape3d.html).

Next measure real cylinder contact fitting and manipulation, including different orientations and grasp locations, then qualify release against floor/props/actor proxies. Handles, arbitrary meshes, articulated props, joint actor-object response and force/balance constraints remain open. No held-out reservations were consumed, no checkpoint was changed, and no release capability was approved. Human review and timed cleanup evidence are still missing.
