# Offline object release and animation baking

2026-09-27. Strep can now simulate a released rigid box locally, preserve the authored motion through release, and bake the remaining object track into a scene GLB. Studio exposes original/candidate comparisons and packages. This is an experimental development workflow, not a solved lift or a release-approved product feature. The single full-project goal remains active.

## Implementation

`object_release.py` validates the source track and explicit physical settings, estimates incoming linear and angular velocities using causal backward differences, and runs the already-installed Godot 4.7.2 executable with the GodotPhysics3D backend. The executable and scripts are hashed. The initial pose and velocities are set once in `RigidBody3D._integrate_forces`; subsequent movement and floor impact come from the physics engine. Every 240Hz state is retained, including contacts, gravity, inertia and damping. Every eighth state is baked to the original 30fps clock. The release sample and entire preceding track remain unchanged.

The engine API and callback timing follow the official [RigidBody3D](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html) and [PhysicsDirectBodyState3D](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html) documentation. The analytic control confirms the engine's fixed-step free-fall integration and constant spin. Halving the step halves the pre-impact position error. An independent floor-drop control verifies actual contact response and settling. No object is clamped or silently frozen after impact.

The present simulation assumes a centered, uniform-density solid box, 5 kg mass, friction 0.6, restitution 0, gravity 9.81 m/s² and an infinite Y=0 floor. These are hypothetical settings, not measured material properties. Sleeping and damping are disabled and CCD is enabled. Character and scene-object colliders are not implemented in this adapter; their omission is shown in Studio and the provenance.

## Preserved experiment and revised contact tolerance

Both studies reuse the already-seen failed attachment fixtures, seeds 11 and 22. They are not held-out trials. Protocols, inputs, scripts and engine hashes were frozen before each run. Original actor animation, hand attachment up to release, contact goals and authored grasp/release events are preserved. Only object samples after frame 121 change.

`reports/object-release-v1` retains the first run with the engine's 0.01 m contact tolerance. It falls and settles, but reaches 13.07 / 12.62 mm floor penetration and fails the unchanged 10 mm screen. Godot documents this [contact tolerance setting](https://docs.godotengine.org/en/4.6/classes/class_projectsettings.html#class-projectsettings-property-physics-3d-solver-contact-max-allowed-penetration). The second study, `reports/object-release-v2`, explicitly sets it to 0.001 m and reads the effective value back from the physics space. No acceptance threshold changed.

| Second-study measurement | Seed 11 | Seed 22 |
|---|---:|---:|
| Original suspended box's floor gap | 398.56 mm | 374.19 mm |
| First simulated floor contact, source-frame time | 129.625 | 130.500 |
| Maximum box/floor depth across all 240Hz samples | 6.10 mm | 7.50 mm |
| Maximum depth at exported frames and half frames | 3.39 mm | 5.66 mm |
| Final absolute floor distance | 1.00 mm | 0.98 mm |
| Final linear speed | 0.000060 m/s | 0.000058 m/s |

Both second-study candidates pass these floor/settling screens. They do **not** pass whole-interaction quality: existing peak body/box penetration remains 7.28 / 10.08 cm, with missed secondary-hand contacts and orientation failures. The dynamics does not react to the actor. This is useful release behavior, not a physical certification of the action.

## Export and engine evidence

Independent verification confirms unchanged actor matrices at all original frames and half frames, the preserved object prefix, event bytes and contact goals. All six GLBs (two actor assets and four original/candidate combined scenes) validate with zero errors and warnings. Dynamic scene ZIPs include the GLB, events, attachment recipe, source/evaluation data, license, release audit, simulation request/provenance and every simulation observation. Their bytes and served downloads are checked.

Actual Godot import verifies 720 actor frames with 77 bones each. A separate audit checks all 720 box poses. Positions agree within 6e-16 m; three scenes pass the 1e-5 rotation-matrix precision screen. **Seed 22's dynamic scene fails that rotation screen**, with 6.80e-5 maximum element error (about 0.005° in the inspected frame). The importer retains all 180 rotation keys accurately; the discrepancy occurs in playback, and its cause remains unresolved. The original failed verifier output is saved; the complete report retains the failure without loosening the threshold. Studio labels this candidate accordingly and links the engine audit.

Eleven focused tests pass, including real engine execution, analytical timing/spin, floor impact, timestep refinement, preserved prefixes and rejected invalid requests/tampered clocks. The full suite passes **505 tests**, five existing warnings, in 123.73 seconds. Logs and frozen source snapshots are retained. No independent animator ratings or cleanup-time data were collected.

## Use and next work

In Studio's **Scene interactions**, choose the original or dynamic candidate under `object-release-v2`. Inspect release and landing on the shared timeline. Floor metrics, retained interaction failures, simulation omissions and download links appear below the viewer. This is currently a prepared experimental comparison; arbitrary release authoring in the UI still needs a supervised request path and controls.

Next: integrate explicit release settings into scene authoring; add actor/environment collision representation; investigate the engine rotation discrepancy; and test non-cube geometry, moving releases and different physical assumptions. Preserve both raw and simulated tracks, carry simulation/event metadata through packages, and continue broader partner, rig, style, offline-install and held-out quality work. No release gate is approved by this study.
