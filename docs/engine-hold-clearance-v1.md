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
The first aligned two-wrist trial finishes after **8** full evaluations and
exhausts its declared **600-second fitting budget** before producing a candidate.
Its initial complete evaluation takes approximately **71 seconds**; total guarded
execution is **679.172 seconds**, because time is checked between evaluations.
All **682** resource observations replay. No candidate is exported or accepted.

A new trial uses active triangle witnesses to guide the solve, then evaluates
every **11,784** affected triangle at all **2,426** original times against both
props and both skin models before candidate admission. A newly failing complete
check adds witnesses for another solve; at most three proposed-candidate rounds
run under the original global evaluation/time bounds. Every contact normal,
side and reliability clock is still evaluated. Taking the minimum over each
clock's inequality rows expresses their exact conjunction; it does not omit
samples or replace the original limits.

Five checks execute the actual admission statements with controlled synthetic
solver/oracle failures. They verify rejection of guided-only success, discovery
and addition of a new witness, rejection after either guided-solve or complete-
check budget interruption, and rejection after three failed complete rounds.
All **18** recorded resource observations replay. These test acceptance logic;
they do not establish triangle correctness or actual solver/rig performance.
The real trial completes **259** evaluations and a full candidate check, then
rejects export. The solver reports incompatible inequalities; this is a local
solver outcome, not a proof that the action is infeasible. The native candidate
normal reaches **15.000902714671598 degrees**, and modeled engine skin puts a
contact **0.5107946698700836 mm** behind its target. Both exceed original limits;
geometry also misses the additional fitting reserve. All **267** resource
observations replay. Its controls, full checks and failure remain preserved.

A separate trial expands only the per-component correction search from **0.001**
to **0.004 radians** for the same two wrists. This is an optimizer search setting,
not a change to the original **45-degree** cumulative motion cap, **15-degree**
normal limit, **0.5-mm** side allowance or **5-mm** penetration limit. All original
times, contacts, props and affected triangles remain in the complete admission
check. Five actual-source admission checks pass again and all **18** resource
observations replay before the new real fit starts. That trial exhausts its
300-evaluation cap before returning a candidate; no partial cache authorizes
export, and all **240** resource observations replay.

A fresh scheduling trial permits **600 evaluations**, with **18 iterations per
round**, under the same 600-second fitting time bound and unchanged memory profile.
It finishes after **475 evaluations** and returns a completely checked proposal.
Both skins meet the original contact/surface limits and every affected triangle
meets the 50-micrometre geometry fitting reserve. The extra surface-side fitting
reserve misses its 1-micrometre target by approximately **6.94 nanometres**:
actual clearance within the original allowance is approximately **0.993 micrometres**.
Strict reserve-based admission exports nothing. All **392** resource observations
replay; the failed reserve result remains immutable.

A separate acceptance recheck uses the same retained controls and evaluates the
complete population from scratch. It uses the original surface limits for
candidate acceptance while retaining extra surface reserves as optimization
targets; the original physical criteria never change. The geometry fitting
reserve remains required. Six actual-source admission checks pass, including an
already completely checked initial proposal. An earlier test-harness attempt
misses a newly required input and is preserved as failed; it runs no real fit.
The complete recheck passes and exports a candidate, with all **147** resource
observations replayed.

Fresh serialized verification confirms the exact two-wrist controls, unchanged
other **152 channels**, static rig/skin and source binary prefix, protected key
support, all **48,520 true-raw cap conditions**, all original position/speed and
**11,590 surface samples per skin**, and every affected triangle against both
props in both skins. The serialized verification's complete resource trace
replays. Fresh complete-body production now passes all **2,426 sampled times**
with zero failed times on this new clip. The largest depth upper diagnostic is
**4.940173 mm** against the unchanged **5-mm** limit, using all **36,108 faces**
and both original sphere props. The full-body resource trace also replays.
Independent geometry replay also passes all **175,196,016 triangle/object
comparisons**, including all **14,557 saved arrays** (7,007,860,048 logical bytes).
Maximum depth-bracket reconstruction difference is **1.67e-16 m**, closest-witness
difference **2.22e-16 m**, and signed-center diagnostic difference **8.88e-16 m**.
The same independent method uses 83 decimal refinements for ambiguous edge ties.
Its complete resource trace replays. Fresh force production is running; actual
engine checks remain pending. No prior body, force, held-pose or engine approval
is inherited.
Partial caches cannot authorize an export. This replay does not replace fresh
force or actual engine evidence. The earlier engine pose error does not bound a
future export.

No continuous collision, self-collision, dynamics/balance, GPU/runtime/event
playback, animator quality, training admission or release approval follows from
the proposal. All broader action, object, partner, rig, editing/style, held-out
and cleanup-review requirements remain under the same full-project goal.

The latest candidate/checks are under `reports/engine-hold-clearance-v10`; earlier
trials remain under their original version folders. Dependency,
failed-attempt and resource evidence is under `reports/central-hand-physical-v1`.
The full-body resource profile is unchanged. Downloaded assets and bulky study
outputs remain excluded from the public source snapshot.

The current validation sequence attached to the verified body worker by
PID, creation time and protocol/source hashes. It completed that owned job;
expired observation never restarts it. Subsequent stages run sequentially under
the same full-body resource profile: independent complete-body replay, fresh
contact forces, independent force/contact replay, then native-resource and glTF
import studies. Original 59 supported force samples must pass the combined
sampled conditions before engine preparation. Unknown-support samples and
uncalibrated body parameters remain explicit. A failed or deferred prerequisite
stops the sequence and preserves its evidence. Execution completion never
approves engine result flags or replaces independent engine replay, human
review, broader held-out evaluation or the full-project release criteria.
