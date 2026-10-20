# Real humanoid mesh-contact trial

This development trial takes Studio's imported-object contact correction beyond the generated closed-mesh fixtures. It uses an existing native Kimodo humanoid clip, unchanged character bytes, a self-created panel, and the production saved-scene and correction workers. It is a fixed-panel touch diagnostic, not a successful high-five or a new motion-generation experiment. No training or new inference is involved.

## Fixed request

The source is the existing `native-scene-envelope-pilot-v1/high-five-A` clip: 77 joints, 18,056 vertices, 36,108 triangles, up to eight skin influences, 120 source keys and approximately 3.967 seconds. Its GLB SHA256 is `fe1920f9b93c17bd76984cf379a69902c14c27575a8fda660eeec390f4781eca`.

The geometry-derived hand marker uses canonical vertex reference `[0, 0, 16974]`; its anatomical interpretation still needs review. At two seconds, a fixed grip is placed 30 mm along the marker's incident-triangle normal. The closed panel measures 120 by 120 by 20 mm. Its grip comes from an actual imported triangle and barycentric coordinates. The target, panel trajectory and original clip are saved before correction and remain fixed.

The contact limit is 5 mm. The existing geometry policy keeps all 2,017 native and frame-population times, a floor at zero, a 5-mm penetration limit, 1-micrometre depth resolution and 10-nanometre surface tolerance. Neither a sparse diagnostic nor a successful point contact establishes complete collision clearance.

Only the right shoulder, upper arm, forearm and hand rotation tracks are editable. Each has a 20-degree change cap and a 150-mm joint-displacement cap. The edit window is 1.2–2.8 seconds, with protected intervals 0–1.1 and 2.9–clip end. Five control times produce 36 controls. Both clip boundaries stay protected. The production request uses eight iterations, the existing 0.02 trust fraction and eight backtracks. No finger, root, leg or object edits are silently added.

## Preflight failures

The saved source scene and its contact measurement complete successfully. A one-time geometry preflight at the actual touch time finds 103 surface-intersection records from 7,598 candidate triangle pairs. The source also penetrates the floor by approximately 8.592 mm, exceeding the unchanged 5-mm limit. The grip remains 30 mm away. These are simultaneous failures: moving a hand marker toward its target does not establish a usable hand/panel interaction. Arm-only permissions cannot repair the feet.

The source volume passes the available watertightness, winding and outward-volume checks. That does not establish anatomical validity or absence of self-intersection. Original selection and engine, motion-quality and release approval remain unchanged.

## Exact collision-query optimization

Profiling exposed redundant spatial-index queries: a small panel can overlap the character's overall bounds while most character triangles lie far outside the panel. The triangle audit now computes each expanded left-triangle box once and skips its index query only when it is strictly separated from the envelope containing every indexed right-triangle box. It preserves boundary equality, the original tolerance, exact classifier, pair order, degeneracy reporting and progress callbacks. It does not remove triangles or substitute bounding-box collision decisions.

All 102 focused tests pass, including six new checks against exhaustive box-pair enumeration, multiple scales and large translations, one-ULP boundary neighbors, and retained degeneracy/progress reporting. The new suite is included in the hosted source-test manifest.

On nine fixed diagnostic times from this real clip, legacy and optimized implementations produce exactly equal reports and byte-identical observation arrays. Two runs per implementation average 4.304 and 2.369 seconds respectively, about 1.82 times faster for this measured workload. This is not a whole-job speed claim or a replacement for the 2,017-time acceptance clock. The former implementation and every run remain archived locally.

## Evidence and remaining work

Local evidence is retained in `reports/humanoid-mesh-contact-prepare-v1`, `reports/humanoid-mesh-contact-source-v1`, `reports/humanoid-mesh-geometry-profile-v1`, `reports/triangle-query-tests-v1`, and `reports/humanoid-mesh-geometry-compare-v1`. The full production correction is tracked separately in `reports/humanoid-mesh-correction-v1`; its terminal result must be inspected before claiming any candidate outcome.

The next decisions depend on that full run: distinguish computation limits from failed correction constraints, retain all observed intersections, and improve collision-aware editing without moving the fixed target or weakening the original acceptance limits. Broader objects, partner actions, rig transfer, engine checks and human cleanup evidence remain required by the original release contract.
