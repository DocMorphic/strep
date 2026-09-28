# Release against static scene geometry

Studio's release panel now offers **Floor only** and **Floor + static scene boxes**. The second mode uses every other saved box as an oriented, immovable collider during the released tail. It preserves actor motion, earlier object animation and the other objects' tracks. Objects that move after the chosen release are rejected rather than silently frozen. A release pose penetrating an included box by more than 1 mm is rejected before starting a worker. Actors still have no simulated collision response.

This supports authored platforms, tables, walls and other geometry represented by boxes; it does not establish general mesh collision, movable props, articulated bodies or a scene-aware motion model. An object may move before release and then become static; the static test covers the entire released interval. Current scene limits remain 1–4 native humanoids, 1–8 boxes and 4–900 frames at 30 fps.

## Simulation and checks

Each collider has a stable ID, position, quaternion, size, friction and restitution. Studio currently applies the requested material values to both the released box and included surfaces. The worker freezes these values with the source revision. Godot's actual installed geometry/materials are reported back and checked, together with clock, gravity, inertia and the initial state. Each observed contact identifies its collider. Floor contact timing therefore cannot accidentally refer to a table impact.

The independent geometric screen uses all 15 oriented-box separating axes. Negative signed separation is the minimum escape depth; positive values are projected separation, not Euclidean closest-point distance. It samples every physics observation. Final settling requires reported contact, a geometric gap/depth within 10 mm, speed at most 0.1 m/s and angular speed at most 0.1 rad/s. All simulated box/floor depths must remain within 10 mm. These numerical screens are not continuous collision certification, force balance or naturalness approval. The test rate is retained in every request.

The original floor-proximity result remains in the record. Studio treats it as informational in static-scene mode: an object resting on a platform is expected to remain above the floor. No quality gate is promoted by this change.

Godot's [static bodies](https://docs.godotengine.org/en/stable/classes/class_staticbody3d.html) supply the immovable geometry, and [PhysicsDirectBodyState3D](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html#class-physicsdirectbodystate3d-method-get-contact-collider-object) exposes the observed collider object. The implementation pins the existing local Godot 4.7.2 runtime.

## Recorded comparison

The protocol in `reports/static-collider-v1/protocol.json` freezes one existing seed-22 actor/box clip and an explicitly authored platform. Both requests use frame 121, 3 kg, friction 0.4, restitution 0.2 and 240 Hz. The floor-only baseline was submitted through the API; the static candidate was submitted using the actual Studio controls.

| Measurement | Floor-only baseline | Static-scene candidate |
| --- | ---: | ---: |
| Maximum box/platform penetration after release | 234.14 mm | 4.45 mm |
| Final reported contact | Floor | Platform |
| First platform contact, source frame | Not simulated | 127.5 |
| Final box distance from floor | 0.11 mm | 224.91 mm |
| Final box/platform signed gap | Not an included collider | −0.087 mm |

The candidate meets the simulated collision/settling screens. An independent verifier projects all eight world-space corners onto the separating axes and checks the decoded GLBs at whole and half frames. The old actor/box contact and orientation failures remain. The authored platform also introduces **225 mm** peak overlap with the earlier, preserved box motion. This is explicitly a release-component comparison, **not** a clean complete pickup or an approved interaction.

The actual jobs are `20260927-125838-1d36e34a` (baseline) and `20260927-125931-ab3c88a7` (candidate). Both packages preserve actors, contacts, earlier events and the authored object prefix. The candidate's relocated ZIP imports separate actor and object GLBs together: all 180 frames of the 77-bone actor and both box nodes pass the existing precision screens. Six GLBs across the two packages have zero validator errors or warnings. Original data, simulator observations and failed checks remain saved.

## Demonstrated limit

A fixed hard-drop regression releases a 20 cm box from centre height 2 m onto a yaw-rotated tabletop at height 1 m. At 240 Hz, peak table penetration is **12.19 mm** and correctly fails the 10 mm screen despite eventually settling. At 480 Hz, it is **7.81 mm** and passes. Both engine records are retained in `hard-drop-regression/`. This is regression evidence, not held-out evaluation. The low-level simulator supports 120/240/480 Hz; Studio still uses 240 Hz, so harder impacts can remain rejected.

The focused collision/worker tests pass (35 tests). The full suite passes **530 tests**, with five existing warnings. A subsequent build consistency check found stale UI source files that would have omitted working controls and duplicated module imports on rebuild. Those source files now reproduce the served Studio byte-for-byte; its dedicated regression test also passes. Logs and the original failed build diff are retained.

## Remaining work

Moving scene colliders and actor collision proxies, arbitrary geometry, authored-prefix collision correction, robust contact/grasp planning and partner response remain necessary. Explicit authoring and deterministic corrections do not replace a model that understands these interactions. Broad held-out motion/rig evaluation, meaningful character-stat calibration, offline installation and independent animator/cleanup-time evidence remain required by the same active full-project goal.
