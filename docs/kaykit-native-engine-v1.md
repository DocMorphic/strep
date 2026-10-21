# KayKit source-motion skin and engine agreement

The unchanged licensed Skeleton Minion GLB passes a nine-capture development
study in Godot 4.7.2. This tests eight existing asset animations, not generated
motion or held-out generalization. The source asset and acquisition details are
in [the source ledger](source-ledger.md#2026-10-21-kaykit-skeleton-minion-development-rig-acquisition).

Each capture observes every original animation-channel key and the midpoint
between adjacent keys. Running is captured both through ordinary 30-FPS import
and native-track authoring; the other seven use native-track authoring. There
are **763 total sampled poses**, including the second run capture. Source GLB
bytes and source animation selection are retained; native authoring writes a
separate engine Animation resource.

All nine captures pass the unchanged 1e-4 pose-element comparison and 0.1-mm
skin-position comparison. Maximum pose-element discrepancy is 5.821e-7 and
maximum skin discrepancy is **0.038400 mm**. Every capture establishes complete
correspondence for **4,858 vertices, 5,288 triangles and nine imported surfaces**.
The comparison retains raw imported weights, equivalent duplicate skin
functions, triangle multiplicity, and the reported global winding reversal;
it does not normalize imported weights to hide discrepancy. This checks the
actual mesh-parent/bind behavior relevant to the GLB validator's non-root-skin
warning for this asset and engine version, rather than suppressing that warning.

## Floor observations remain separate failures

The declared diagnostic floor is Y=0 with a 5-mm penetration limit. Native and
engine skin measurements closely agree, including failures. Four of the eight
source motions exceed that limit. No offset or floor correction is applied.

| Native-authoring clip | Samples | Max skin error (mm) | Engine floor depth (mm) | Floor screen |
| --- | ---: | ---: | ---: | --- |
| Running_A | 49 | 0.034746 | 55.267358 | Fail |
| Jump_Full_Long | 141 | 0.034722 | 63.955878 | Fail |
| Lie_StandUp | 141 | 0.031369 | 122.873423 | Fail |
| PickUp | 79 | 0.031316 | 0.466717 | Pass |
| Sit_Chair_Down | 49 | 0.038400 | 17.462671 | Fail |
| Cheer | 101 | 0.031345 | 0.372091 | Pass |
| Use_Item | 97 | 0.031380 | 0.372092 | Pass |
| Unarmed_Melee_Attack_Kick | 57 | 0.031140 | 0.733959 | Pass |

The ordinary-import Running_A capture adds 49 samples and also passes pose/skin
agreement while failing the floor screen at 55.267338 mm. Native source run
penetration is 55.268210 mm, so import error does not explain that floor failure.

## Retained evidence and limits

`reports/kaykit-native-engine-v1/` retains the pinned study request, unchanged
GLB copies, engine inputs and logs, raw observations, per-case results and arrays.
A separately guarded numerical replay recomputes complete skin correspondence,
all source-key/midpoint clocks, joint matrices, skin errors and both floor tracks.
Every saved array matches in dtype, shape and bytes. The capture and replay
resource traces replay 68 and 37 observations respectively. Both enforce a
512-MiB process-tree cap, 600-MiB free-RAM reserve and 900-second time limit.

This is headless engine pose capture with CPU reconstruction of actual imported
skin, not GPU/pixel or live gameplay playback. It does not evaluate continuous
collision, self-intersection, support sliding, dynamics, semantic correctness
or animator cleanup. No objects or partners are supplied: PickUp and sitting
names do not establish object/seat contact. Passing a floor screen or import
comparison does not approve motion quality. Original clips and all failures
remain available, and release capabilities remain unapproved.

## Generated-motion transfer baseline

The follow-up transfers seven existing seed-77 SOMA development clips with the
existing 18-role profile, zero authored world offset and no automatic floor lift.
It performs no new inference or training. These clips are development data;
their historical directory name does not make this a reserved release study.
Unmapped helpers and fingers retain reference transforms, and anatomical axis
and twist interpretation still require review.

All seven transfers complete across **1,020 frames**. The exporter checks source
SOMA forward kinematics and decodes each target frame. Maximum target-vertex
round-trip discrepancy is 1.492138e-7 m. A separate byte/structure check verifies
all report/source/output digests, original binary prefixes, mesh/skin/material
definitions and original accessors. Each derivative contains one transferred
animation; the original GLB and all 95 original clips remain separate and intact.

| Transferred development action | Frames | Target floor depth (mm) |
| --- | ---: | ---: |
| Jump/land | 120 | 54.077449 |
| Crawl | 120 | 327.115974 |
| Dance | 150 | 32.728972 |
| Wave | 120 | 8.907740 |
| Kick | 120 | 149.179829 |
| Get-up | 180 | 633.661003 |
| Run/roll/stand | 210 | 1129.485888 |

Every derivative exceeds the existing 5-mm floor screen. Export round-trip
agreement does not repair these failures or establish usable animation. Source
foot-contact predictions are retained, not promoted to verified target support.
The native-source engine results above do not verify these new derivatives.
Their body/support fitting, actual engine comparison, collision/transition,
semantic and human cleanup checks remain outstanding.

The first attempt records seven setup failures before transfer because this
worktree lacked the existing Kimodo skeleton-definition path. A local directory
junction connects it to the already acquired dependency; no library/model was
downloaded or modified. The fresh second attempt retains the same cases and
input hashes. Evidence is `reports/kaykit-generated-transfer-v1/` (failed setup)
and `reports/kaykit-generated-transfer-v2/` (completed exports and publication
check). Resource traces replay 70 and 61 observations. The CPU transfer worker
uses the installed Torch runtime, a 2-GiB process-tree cap, 600-MiB free-RAM
reserve and 900-second time limit. No motion or release approval follows.

## Floor attribution and mapped skin coverage

A follow-up decodes all 1,020 exported keys without editing them. At each key,
it records the lowest target vertex, primitive, positive skin influences and
nearest mapped ancestors. Its height is decomposed into the weighted scaled
source ancestor height, target-versus-source ancestor displacement, and target
surface offset from those ancestors. These terms identify where to investigate;
they are an algebraic decomposition, not independent causal experiments.

| Action | Keys deeper than 5 mm | Worst key | Dominant mapped influence | Depth (mm) |
| --- | ---: | ---: | --- | ---: |
| Jump/land | 109 / 120 | 57 | Right foot | 54.077449 |
| Crawl | 120 / 120 | 1 | Left hand | 327.115974 |
| Dance | 62 / 150 | 128 | Left toes | 32.728972 |
| Wave | 120 / 120 | 0 | Left foot | 8.907740 |
| Kick | 37 / 120 | 22 | Left foot | 149.179829 |
| Get-up | 180 / 180 | 40 | Head | 633.661003 |
| Run/roll/stand | 89 / 210 | 93 | Head | 1129.485888 |

For crawl's worst vertex, the scaled source hand anchor is -0.824 mm, target
ancestor displacement is -198.236 mm, and surface offset is -128.056 mm. The
roll's worst vertex has corresponding terms +97.198, -477.884 and -748.800 mm.
This supports investigating proportion-aware body/contact fitting, rather than
assuming a successful rotation transfer preserves surface contact. Raw source
joint centers also dip below the floor in six clips; wave's joint centers remain
above it while its target mesh fails. Joint centers are not a source body mesh,
so these observations do not measure source surface penetration or prove that
the remaining source motion is realistic.

The check also finds **467 body vertices with positive weights on joint 40,
`root`, outside every mapped joint subtree**. That joint is a parent of the
mapped pelvis and retains its reference transform in these transfers. Its
per-vertex contribution ranges from 0.000089796 to 0.165500432. The affected
vertices have other moving influences; they are not entirely frozen. Do not
discard or renormalize these weights, or assume that unmapped helpers beneath
mapped bones have the same problem.

Transfer calibration now includes `target_skin_mapping_coverage`: affected
vertex counts, primitive/joint identities, maximum outside weight, unskinned
vertex counts and an inspection flag. The diagnostic preserves motion, mapping,
weights and assets. An unmapped descendant inherits its mapped ancestor's motion;
an outside node may still move through explicitly retained animation context.
The flag is a request to inspect influence coverage, not a quality verdict.

Evidence is retained under `reports/kaykit-floor-attribution-v1/` (the initial
diagnostic stopped on an unaccounted outside influence), `-v2/` (complete
attribution), and `reports/rig-mapping-coverage-v1/` (production diagnostic check).
A separate native-time sampler reproduces all 1,020 minimum heights to within
8.89e-16 m and checks decomposition sums and failure counts. Successful capture
and replay resource traces contain 51 and 27 observations; both use a 512-MiB
tree cap, 600-MiB reserve and 900-second limit. Six focused tests cover helper
inheritance, parent/sibling weights, all eight influence slots, repeated mesh
instances, unskinned geometry, zero weights, immutability and same-rig transfer.
The production diagnostic independently reproduces the 467-vertex finding.

Next, author explicit support and auxiliary-root behavior for separate candidate
assets, beginning with the small standing foot error. Ground actions require
full-body support and proportion handling; lifting the entire animation until
it clears the floor would not establish planted hands/feet or plausible motion.
Recheck every candidate in the engine and retain source failures. No new motion
generation, training, correction, human review or release approval occurred here.

## Standing support candidate: clearance improves, motion rates regress

The next development trial actually edits the wave clip, with a separate request
allowing both thigh/shin/ankle rotation tracks across all 120 keys, including
endpoints. It preserves translations, root motion, unrelated rotations, native
times, duration and mesh/skin payloads. The original remains selected. Hard
limits are 15 degrees per local joint, 25 mm ankle displacement, 30 mm joint
and vertex displacement, and a 5 mm maximum lowest-point support gap. The target
clearance is 1 mm above Y=0. These physical limits remain identical across all
attempts; none of the failures is converted to a pass by widening them.

The first attempt rejects non-rigid input. The existing explicit roundoff
preparation changes 15 static near-unit scales within its unchanged 5e-7
eligibility limit. Maximum vertex change is 1.568743e-8 m over the reference and
701 sampled poses, below its unchanged 1e-5 m geometry budget. Mesh data, inverse
binds and animation bytes remain intact in this separate prepared input.

A direct ankle lift then exceeds the rotation bound. Subsequent constrained
rotation proposals initially fail convergence/feasibility checks. The completed
proposal uses complete affected-vertex/joint inequalities for each disjoint leg
solve, followed by all-vertex/joint validation. Internal 0.1 mm clearance and
displacement margins tighten the proposal targets. The source-relative pose
objective includes previous-key regularization, but no hard temporal rate caps.
Unmapped auxiliary-root behavior remains unresolved and unchanged.

The resulting candidate passes its sampled support/edit bounds at **701 times**
(all native keys, adjacent midpoints and uniform 120 Hz samples). An independent
sampler replay reproduces the floor track exactly. Maximum local rotation change
is 6.612393 degrees, ankle/joint displacement 24.109133 mm, and vertex displacement
29.902907 mm. Foot-region minimum heights range from 1.088604 to 1.101943 mm;
the full mesh has no sampled floor penetration.

Actual Godot native-animation captures reproduce both original and candidate at
701 times each. Original floor penetration is 8.907812 mm; candidate penetration
is zero. Maximum complete imported-skin comparison error is 0.031961 mm in both
captures, below the existing 0.1 mm limit; pose comparisons also pass. Ordinary
import remains **failed**: at sample 699, the requested 3.966666666666667 s seek
reports 3.9666666984558105 s, a 31.789 ns difference exceeding the unchanged 1 ns
actual-clock limit. The raw capture is retained; native-authoring success does
not approve ordinary import, GPU rendering or gameplay playback.

**Do not adopt the candidate:** both original-bin rate caps and absolute per-joint
peak comparisons fail on uniform 120 Hz observations. Largest peak increases
are 0.057049 m/s positional speed, 15.676850 m/s² positional acceleration,
0.336008 rad/s angular speed and 36.847076 rad/s² angular acceleration. A diagnostic
using fixed source-first-pose near-sole vertices also worsens: left maximum
horizontal excursion increases from 36.603 to 44.620 mm, right from 20.075 to
30.570 mm. These are diagnostic vertex trajectories, not verified contact labels.
Clearing the floor alone has not established planted feet or realistic motion.

Evidence: `reports/kaykit-wave-support-v1/` through `-v5/` retain all proposals
and failures; `kaykit-wave-rigid-input-v1/` retains explicit preparation;
`kaykit-wave-support-engine-v1/` retains both completed native captures and the
failed ordinary-import capture. The v5 `publication-check.json` verifies hashes,
unchanged physical limits, both native comparison passes, the import-clock
failure, and eight resource audit records. Successful proposal/replay traces
contain 65/31 observations; the engine trace contains 46 and correctly remains
failed overall. All use a 512-MiB process-tree cap and 600-MiB free-RAM reserve.

Next: optimize support across time with explicit contact targets and hard rate
constraints, then repeat serialized and engine checks. Keep this geometrically
passing but temporally rejected candidate as evidence, not as a new default.
This study does not approve self-collision, balance, continuous-time geometry,
anatomical motion, an auxiliary-root fix, animator cleanup or release readiness.

## Temporal follow-up

The first temporal trial uses one constant source-relative local rotation offset
for each of the six edited joints: 18 parameters shared across the whole wave
clip. It includes the original movement/support bounds and both original-bin and
absolute peak rate inequalities in the search. Full-weight skin evaluation is
batched by influencing joint and checked against scalar decoded geometry; no
vertices or positive influences are dropped to reduce memory.

The optimizer terminates without a feasible result. The retained candidate has
1.749524 mm sampled floor penetration and fails the support/edit conditions and
both rate comparisons. Independent scalar replay covers all 701 times, matches
the stored floor track exactly, and records every violation. The candidate stays
unselected. This is a failed local search, not proof that no correction exists
within the original bounds. Evidence is `reports/kaykit-wave-temporal-v1/`;
proposal and replay resource traces contain 78 and 31 observations.

The next, separately versioned trial in `reports/kaykit-wave-temporal-v2/`
uses three Bernstein rotation-vector controls per joint, evaluated through the
original native-key interpolation. It also declares fixed horizontal support
targets: each foot's first-pose near-sole vertex centroid is anchored to its
mean source position over the audit clock, with 3 mm horizontal tolerance.
The request retains all previous movement and rate limits. A search-only
restoration slack explores infeasible seeds; final acceptance checks the original
inequalities without slack. After 50 iterations the solver remains infeasible,
with restoration slack 1.644403. The stored candidate is retained as a failure,
not offered as a passing correction.

Independent scalar replay checks all 701 sample times, exact floor reproduction,
input/track preservation and the support targets recomputed from source geometry.
It reports 7.222016 mm floor penetration, 25.980763 degrees maximum local rotation
change, 62.607836 mm maximum joint displacement and 54.911538 mm ankle movement,
exceeding the unchanged bounds. Horizontal target error reaches 7.933220 mm left
and 7.933390 mm right, above the declared 3 mm. Both rate comparisons also fail.
There is no accepted candidate or feasibility certificate. Proposal and replay
resource traces contain 677 and 31 observations; peak proposal tree RSS is
286,027,776 bytes under the 512-MiB cap. No model training or engine rerun was
needed to reject this already-invalid candidate.

## Studio mapping feedback

Studio's verified native-transfer review now recomputes influence coverage from
the transferred character and its bound target profile, including records whose
stored reports predate the diagnostic. The editor and candidate preview display
affected mesh-point counts and request a mapping/deformation review. Missing
coverage is explicitly unknown; a contradictory or malformed coverage payload
cannot be presented as a valid review. A clean influence check still does not
approve anatomical mapping, contact or motion quality. The existing explicit
candidate-import action and original selection policy remain unchanged.

Seven guarded Python checks cover fixture transfer/verified review/import and
influence accounting. Both offline transfer-editor interaction suites pass,
including the warning, unknown and inconsistent-payload cases, and viewer
syntax checks pass. Evidence is `reports/studio-rig-coverage-v1/`. These are
software checks with an engine double, not a live-browser visual review or
additional actual-engine evidence.

## Rate localization and original root behavior

The read-only follow-up in `reports/kaykit-constraint-diagnostic-v1/` samples
the three rejected wave candidates on the same 120-Hz rate clock. All three
absolute-rate reports and original-bin pass/fail decisions reproduce their
previous independently replayed reports exactly. The per-key correction raises
the right-foot peak positional acceleration from 3.788516 to 19.465366 m/s²,
with its candidate peak at 1.866667 s. Right-upper-leg angular acceleration
also peaks there, rising from 23.316854 to 60.163929 rad/s². This localizes a
large temporal regression; it does not establish why the optimizer chose it or
prove the original constraints infeasible. The constant-offset candidate has
smaller regressions but still fails the unchanged acceptance checks. The curve
candidate likewise remains rejected, including 1,091 sample/joint pairs above
their source-bin angular-speed limits. A whole-clip peak can pass while a local
source-bin limit fails, so neither comparison substitutes for the other.

The same diagnostic inspects all native keys and adjacent midpoints for the
eight original KayKit clips used in the engine study. Their weighted auxiliary
root is essentially rotation-static in every clip and position-static in seven;
Running_A moves it by up to 50 mm from its initial position. The hips still move
relative to that root, including about 123.83 degrees of rotation in Lie_StandUp.
Thus the 467 vertices influenced by this unmapped ancestor justify inspection,
but do not establish that a fixed ancestor is a transfer bug. Automatically
making it follow the full pelvis transform is not supported by this evidence.
Any such deformation change needs a separate explicit policy and comparison.

The diagnostic completed with 30 replayed resource observations and peak process
tree RSS of 129,712,128 bytes under the unchanged 512-MiB cap and 600-MiB free-RAM
reserve. It changes no animation, weights or acceptance thresholds. Next work
is to isolate support feasibility from rate feasibility and evaluate temporally
coupled corrections; no accepted correction or release approval follows from
these measurements.
