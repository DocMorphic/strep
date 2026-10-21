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

The first production run reached its unchanged 900-second execution limit during the first proposal's geometry audit. Its complete source audit, proposed GLB, decoded constraints, contact measurements and partial geometry archive remain saved. There is no completed proposal decision or selected candidate. The resource trace replays all 904 observations and identifies the time limit as the stop reason; peak process-tree memory was about 365.4 MiB.

The completed original audit evaluates all 2,017 declared times. All fail the floor condition, with 10.436-mm maximum depth. Character/panel geometry fails at 248 times, with 42,666 surface-intersection records and approximately 10-mm maximum vertex-containment depth. The first proposal reduces the point gap to 25.350 mm, still outside the 5-mm contact limit. Its unfinished geometry audit cannot establish nonregression or acceptance.

A separate fresh-process regression reproduced a worker setup defect: the single-thread limit was applied before the backend loaded NumPy/SciPy. The worker now loads its numerical backend inside the acquired job lock, then applies the thread limit. Queue and status imports remain lightweight. This configuration fix does not change geometry, clocks, contacts, solver settings, edit permissions or acceptance limits. See [worker thread configuration](mesh-worker-thread-configuration-v1.md) for the regression and retry scope.

The next decisions must distinguish computation limits from failed correction constraints, retain all observed intersections, and improve collision-aware editing without moving the fixed target or weakening the original acceptance limits. Broader objects, partner actions, rig transfer, engine checks and human cleanup evidence remain required by the original release contract.

## Protected source failures and edit dependencies (2026-10-21)

A metadata inspection binds the first 270 committed samples of the fresh
deterministic-containment baseline, covering 0–0.53125 seconds. It verifies the
checkpoint chain, frame receipts and geometry JSON hashes, then maps every
recorded proper-crossing triangle pair and floor witness back through the exact
source GLB's index, joint and weight accessors. The asset has one mesh primitive,
so its original triangle order matches the audited surface order. All positive
skin weights and their ancestor nodes participate; no top-K or weight cutoff is
used. The inspection does not recompute poses, collisions or observation arrays.

This prefix contains **214 distinct proper-crossing triangle pairs**, of which
**93 occur at all 270 times**. Among the 214, **162 have no editable right-arm
ancestor** under the original four-track permissions. The two recorded peak
floor witnesses are vertex 2147, weighted entirely to `LeftFoot`, and vertex
17445, weighted entirely to `RightFoot`. Neither depends on an editable arm
node. Every prefix time fails the floor condition; the largest saved depth is
9.254 mm. These are node/skin identities, not a reviewed anatomical annotation.

All 270 times also lie in the original protected interval. Therefore the
original arm-only request cannot remove these recorded source failures while
preserving its permissions and protected motion. Better point contact or another
arm-solver iteration cannot establish a whole-body geometry pass. This is a
limitation of that request, not a claim that the clip is irreparable under a
different explicitly authored request. The source mesh has not been diagnosed
in its reference pose, and recurring crossings alone do not prove a bind-shape
defect or justify ignoring any surfaces.

Continue the full 2,017-time baseline to localize the remaining failures. Before
another attempt is presented as whole-body recovery, separate source preparation
from the fixed-contact experiment: inspect whether persistent witnesses also
exist in the reference pose, then define any required asset repair, leg/root
permissions or changed protected intervals in a fresh versioned request. Preserve
the original request and raw animation for comparison; do not silently grant
those edits, move the panel, loosen collision limits or exempt intersecting
triangles. A contact-only improvement may still be studied, with existing
whole-body failures visible and no quality approval.

The complete pair, vertex, influence and per-frame attribution is retained in
`reports/humanoid-protected-witness-attribution-v1/witnesses.json` (SHA256
`5fe6abb04f52bf61800f91ed8e785f311af6fb992da07c6ea754d99f2c6f4d8f`).
Its `result.json` binds the exact source, permissions and pinned checkpoint.
The metadata-only run imported no NumPy and changed no numerical worker source,
model, animation, permission or acceptance policy. This is incomplete-prefix
diagnostic evidence, not a complete motion or release result.
