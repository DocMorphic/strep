# Engine-aware held-contact correction proposal

The prior native-resource export fails sampled geometry despite passing pose,
contact and vertex-position tolerances. Complete independent geometry replay and
the full-vertex diagnostic are described in
[scene engine replay](native-scene-engine-replay-v1.md). The observed engine skin
is now available to correction calculations without rewriting source rig weights.

## Failure population and control support

`engine-clearance-support-v1.json` replays every original full-face upper-depth
array: **4,852 arrays, 36,108 faces each, 2,426 times and both original spheres**.
Each array's numerical hash and maximum agree with the completed independent
geometry evidence. There are **10,240 failed face/time observations**, covering
eight left-hand triangles at all 1,280 failed times. Their positive observed
influences are LeftHand, Thumb1/2, Index1, Middle1 and Ring1. Ancestor mapping
identifies potential controls; it does not prove a correction feasible.

There are 1,278 failed held-contact times and two after the hold. The other sphere
has no failed faces. The old departure study fixed the successful native held pose
exactly. Its clip and proofs remain immutable; a separate trial now permits a
small wrist change during the held interval while retaining the authored targets,
contact limits and cumulative original-reference rotation budget. The fixture's
object named `box` remains a sphere, not the rectangular-box benchmark.

## Bounded proposal and serialized checks

The trial edits only **LeftHand/node 15**, with six control components at the
two interior knots of the original entry/hold/exit support. Each component's
increment is bounded to 0.001 radians. The original **45-degree cumulative
reference budget** and original **5-mm contact/penetration limits** remain intact.
Both native and observed engine skin at native FK constrain the fit at every
original time, against both props and every declared contact sample. The eight
currently failed triangles guide the search. An internal **50-micrometre fitting
reserve** seeks clearance inside the unchanged acceptance limit.

The first attempt stops before optimization because its batched object-center
subtraction lacks a triangle-axis dimension. Its failed guard/log/resource record
is preserved. Version 2 corrects that implementation error without changing the
constraints: SLSQP finishes in **six iterations and 80 evaluations**. The guard
completes in **64.11 seconds**, with **81** resource observations replayed and
1,346,760,704-byte peak process-tree RSS under the full 2048+600-MiB profile.

The exported candidate is `reports/engine-hold-clearance-v2/candidate.glb`, SHA-256
`0504d0c08b7a54ab4ba16298253aa61356318dd7e4d68c57191fe1585c19e08a`.
`serialized-check-v1.json` confirms:

- The source binary prefix, static skin arrays, node hierarchy, meshes and skins
  remain intact. The other **153 animation channels** and all original key clocks
  are identical. Edited quaternions exactly match serialized declared controls;
  keys outside the allowed interpolation support stay unchanged.
- All **48,520 finite true-raw rotation-cap conditions** pass, using the original
  artist bounds and existing 1e-5-degree serialization allowance. The wrist change
  relative to the previous development clip peaks at **0.058404104993536786 degrees**.
- Every declared contact sample still passes in both skin models. Serialized
  guide depths peak at **4.939592029179346 mm** for native skin and
  **4.950000115964831 mm** for modeled engine skin. The tiny rounding change in
  the latter does not change the original 5-mm acceptance limit.
- Targets, prop tracks, geometry clocks, policy limits and source rig weights are
  unchanged. The held wrist pose changes; old exact-held-FK and contact-force
  proofs are not inherited.

The serialized guard completes in **43.796 seconds**, with all **61** resource
observations independently replayed. Guide distance arithmetic is reused; scalar
raw-quaternion interpolation is shared. This is not independent complete geometry.

## Remaining acceptance work

Fresh complete native-body geometry finishes for all **18,056 vertices,
36,108 triangles, 2,426 times and both props**, retaining the original containment
and policy limits. All sampled conditions pass with **zero failed times**. The
complete mesh peaks at **4.978540079358131 mm**, leaving approximately
**21.46 micrometres** inside the original 5-mm limit. This maximum comes from
the complete body; eight guide triangles did not establish it.

The producer records **175,196,016 triangle/object queries** and **14,557 numeric
archive arrays** (7,007,860,048 logical bytes). Execution finishes in
**2,076.297 seconds**; all **2,057** resource observations independently replay
under the unchanged 2048+600-MiB admission profile. Source/body prerequisite
hashes match the serialized-stage record.

Independent replay subsequently confirms every sampled decision and archive
array, with maximum depth-bracket/witness differences of
**1.94e-16/2.22e-16 m** and **78** exact-input edge-tie refinements. All **547**
resource observations replay. This establishes sampled native geometry for this
development fixture; actual new engine observations remain pending.

Fresh contact-force testing **rejects the combined result**. All **59** supported
object-force samples satisfy the declared hypothetical rigid-body equations,
but **0/59** pass the combined contact/force conditions. Every point-position
and speed row still passes. One left-hand neighbouring point exceeds the original
**15-degree** normal-opposition limit at all **1,159** contact times, peaking at
**15.037935491376311 degrees**. Surface-side and reliability limits remain
unchanged. The **119** unknown-support samples and two unestimated endpoints are
still explicit; the object assumptions do not establish measured strength or
whole-body dynamics.

Separate replay confirms all **11,590** original-clock and **1,800** force-clock
normal observations, contact stencils and failed combined decisions. The fresh
force and independent replay guards finish in **207.890/67.313 seconds**, with
all **221/84** resource observations replayed. A force-only success is therefore
not accepted as a usable grasp.

The next wrist proposal adds all original normal, side and reliability constraints
in native and observed-engine skin models. An initial setup applies extra inner
reserves to the untouched right hand; its owned worker is explicitly stopped
after source/PID/creation-time verification, and its failed guard, source, plan
and stop reason remain preserved. A fresh version applies optional reserves only
to edit-dependent rows while checking uneditable rows against every original
limit. Fitting, exported verification, full-body checks, fresh forces and actual
new engine observations remain required for a later candidate. That restricted
trial then stops before optimization on an original uneditable condition:
modeled engine skin at native FK puts a right-hand contact **0.5162859599086694 mm**
behind its target, beyond the original **0.5-mm** allowance. Native skin passes
that condition. Its failed result, initial measurements and all **63** resource
observations are preserved; no future engine arithmetic is inferred.

The next declared trial edits both **LeftHand/RightHand (nodes 15/43)** within
their existing **45-degree original-reference budgets** and the same local
increment bounds. It includes every triangle affected by either wrist or its
descendants in either skin, both props and all original clocks. Geometry uses
32-frame chunks to control memory; this changes neither times nor population.
All original position, speed, normal, side and reliability conditions still
apply. Both wrists changing means new exported, complete-body, force and engine
evidence is required; earlier exact held-pose or right-hand results are not
inherited.

The first two-wrist setup stops before fitting because the right-hand working
track has **315** native keys and its original reference has **180**. A fresh
reference samples the true raw right-hand motion at the unchanged working key
times and verifies the serialized values. The candidate, left reference and all
other reference rotations stay unchanged. All **19** alignment-resource
observations replay; the failed setup and its **40** observations remain saved.
The fitting reference's float32 resampling does not grant extra edit budget:
all **48,520** true-raw full-clock cap conditions remain required after export.
The new two-wrist fit is running. The earlier engine pose error does not bound
a future export.

No continuous collision, self-collision, dynamics/balance, GPU/runtime/event
playback, animator quality, training admission or release approval follows from
the proposal. All broader action, object, partner, rig, editing/style, held-out
and cleanup-review requirements remain under the same full-project goal.

Local plans/results are under `reports/engine-hold-clearance-v2`; dependency,
failed-attempt and resource evidence is under `reports/central-hand-physical-v1`.
The full-body resource profile is unchanged. Downloaded assets and bulky study
outputs remain excluded from the public source snapshot.
