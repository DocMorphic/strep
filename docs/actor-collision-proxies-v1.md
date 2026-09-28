# Experimental animated-body collision

The release engine now accepts moving convex solids and can compile 21 body regions from the native SOMA mesh. A paired prop-drop experiment demonstrates collision response from an animated head, shoulder and arm. **This experiment is not qualified for general interaction authoring:** body envelopes extend beyond the visible skin, the final prop does not meet the existing settling screen, and the actor does not react to the collision.

The normal Studio release controls keep their existing behavior. The experimental worker/API field is `actor_collision_mode: "convex_skin"`; its default is `"none"`. Saved experimental results can be inspected in Studio with a **Body collision proxies** overlay. It is off by default and leaves the grey character visible. Actor response, active balance, catching and grasp forces remain unimplemented by this mechanism.

## Geometry and clock

`actor_collision_proxies.py` groups mesh vertices by dominant skin-weight region, merging finger/toe/face bones into hand/foot/head regions. Fitting uses the actual exported mesh with all eight skin influences. Each region is enclosed by 26 bone-local support planes across the clip, plus a fixed 1 mm margin. Their intersection gives a 48-vertex convex envelope. These are rigid per-bone shapes; a deforming skin cannot generally be matched exactly by one rigid envelope.

Collider motion samples the exported GLB's local translation/rotation tracks and composes the actual hierarchy, rather than linearly interpolating global joint positions. The scene's world placement and each proxy's local centre offset are included. There is one incoming physics sample before release, followed by 240 Hz prescribed motion. The scene worker rejects initial prop/proxy penetration above 1 mm, snapshots geometry/calibration/source files, and preserves the actor motion, original prop prefix, events and failures.

The generic moving collider limit is 96, accommodating four native actors with 21 regions each plus scene objects. Convex input accepts 4–128 unique hull vertices with finite volume. The production box/convex test uses face normals and true polyhedron-edge cross products. An initial unit check caught triangulation diagonals being treated as edges; removing those restored equivalence with the existing box SAT. The failed log is retained.

## Two audit failures retained and corrected

The first actor simulation failed the existing 2e-4 m/s velocity check. The engine's velocity is at the convex solid's centre of mass, while the initial audit differentiated the node origin. Accounting for the independently calculated volume centroid reduced the largest discrepancy to 1.048e-4 m/s on that retained output.

An instrumented second run then failed the 1e-6 m COM check: Jolt's automatically computed centroid differed by about 25 micrometres for the first failing region. Inspection of the pinned engine source shows that Jolt builds its internal convex hull with a default 1 mm hull tolerance; the registered point array is not proof of identical internal hull geometry. The third version explicitly supplies the uniform-solid centroid through `PhysicsServer3D.BODY_PARAM_CENTER_OF_MASS`, records the runtime COM, and verifies velocity against the moving COM trajectory. The original pose, velocity and COM limits remain unchanged. An asymmetric tetrahedron and an irregular convex hull are now engine regressions.

Collision geometry still has Jolt's internal hull approximation. It is **not** certified exact merely because the COM is now explicit. Contact and penetration are screened independently against the requested convex geometry and the exported skin.

## Paired experiment and evidence

`reports/actor-proxy-release-v1` freezes an existing seed-22 actor and a 20 cm, 2 kg unheld crate positioned above the head at release frame 121. Both variants use Jolt, 240 Hz, friction 0.6, bounce zero and the same floor. The actor is unchanged. This is an authored physics component experiment, not a newly generated human interaction or held-out motion study.

| Measurement | No body colliders | Body proxy candidate |
|---|---:|---:|
| Sampled skin penetration, integer frames | 86.91 mm | 0 mm |
| Decoded skin penetration, whole and half frames | 97.02 mm | 0 mm |
| Whole/half samples over 10 mm | 8 | 0 |
| Maximum requested proxy penetration | Not simulated | 5.07 mm |
| Final floor-relative speed | Settling screen passed | 0.123 m/s |
| Final floor-relative angular speed | Settling screen passed | 0.604 rad/s |
| Existing combined collision/settling screen | Passed for floor only | **Failed** |

First recorded body contact is the head at source frame 126.125, followed by the left shoulder, upper arm and forearm. The candidate ultimately contacts the floor. The last-frame speed limits remain 0.1 m/s and 0.1 rad/s; no duration extension or threshold adjustment was used to turn the failure green.

The fitting study covers all 18,056 assigned skin vertices and reports no support-plane violation at 359 whole/half-frame samples. That does not establish coverage of all triangles or continuous time. The unsigned proxy-vertex/skin-vertex distance reaches 96.21 mm and includes interior points. Signed triangle-distance checks at each region's unsigned worst frame found actual outward excess up to 79.68 mm. This selected-frame diagnostic is not an exhaustive maximum and plainly fails a 10 mm geometry-fidelity screen. Broad proxy fitting must improve before this becomes a reliable contact tool.

Both exported scene ZIPs preserve their sources, prefixes, actors, events and paths; served downloads match saved hashes. Six GLBs have zero validator errors or warnings. Both relocated packages pass actual Godot playback at all 180 frames, including all 77 actor bones and the crate. Separately, the actual engine bone transforms plus proxy offsets match the recorded physics collider poses at all 59 shared integer frames: maximum position error 4.227e-7 m and rotation-element error 7.611e-7. Skin/box checks use vertices, not a complete triangle-intersection or continuous collision proof.

Jobs are `actor-proxy-v1-baseline` and `actor-proxy-v3-candidate`. Failed `actor-proxy-v1-candidate` and `actor-proxy-v2-candidate` remain intact. The full suite passes **556 tests**, with five existing warnings. No model was trained and no animator rating or cleanup-time observation was collected. All project release gates remain open.

## Reproduction and next work

`python scripts/verify_actor_proxy_release.py` rechecks decoded skin and the actual engine/proxy clock without rerunning physics. `study_actor_proxy_release.py` preserves the original v1 experiment, including its audit failure; the two revision protocols record the later instrumentation and COM change. Do not overwrite completed runs.

Next work must reduce outward envelope errors and measure response against the visible surface. More segments, phase-specific geometry or a different collision representation need comparison against these retained failures. Human reaction and balance require a separate motion-editing/scene-aware solution; one-way kinematic deflection cannot substitute for them. Broader action, rig, style, offline installation and independent-review work remains part of the same full-project goal.

Primary sources: [Godot convex shapes](https://docs.godotengine.org/en/stable/classes/class_convexpolygonshape3d.html), [collision-shape tradeoffs](https://docs.godotengine.org/en/stable/tutorials/physics/collision_shapes_3d.html), [direct body state and COM](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html), [pinned convex-shape construction](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/jolt_physics/shapes/jolt_convex_polygon_shape_3d.cpp), and [pinned Jolt hull settings](https://github.com/godotengine/godot/blob/4.7.2-stable/thirdparty/jolt_physics/Jolt/Physics/Collision/Shape/ConvexHullShape.h).
