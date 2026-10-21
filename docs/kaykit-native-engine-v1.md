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

## Fixed-target conflict and reusable preflight

The geometry-only follow-up (`reports/kaykit-wave-contact-feasibility-v1/`)
retains the temporal trial's fixed targets and all movement limits while
excluding rates from proposal search. It tries up to three deterministic starts
per pose/leg: previous solution, the retained floor candidate, and source pose.
Of 240 native-key leg solves, 24 remain unresolved. The serialized derivative
also fails the 701-time geometry and rate replay and remains unselected. The
proposal/replay resource traces contain 149/31 observations. These solver
failures alone do not prove infeasibility.

A separate necessary bound does identify a target conflict. When every selected
vertex may move at most D, their arithmetic centroid may move at most D by the
triangle inequality. The centroid must reach both the planar target disk and
the clearance half-space. Its distance to that intersection is therefore a
necessary movement bound, even if all skeleton, joint-angle and temporal
constraints are relaxed. Individual selected vertices must also reach the
clearance half-space; the larger of these bounds is retained.

On the existing target definitions, the left-foot condition conflicts at 41 of
701 audit times. At 3.566666603088379 seconds, its four selected vertices require
at least 32.687260 mm maximum movement, versus the authored 30 mm limit. The
tangential and normal components of the centroid bound are 31.219244 mm and
9.685853 mm. No right-foot conflict is established by this relaxation. There
may still be joint, geometry or temporal conflicts there; absence of a witness
is not a feasibility result. The bound uses a conservative floating comparison
reserve and is not a formal interval-arithmetic certificate.

`scripts/native_support_preflight.py` exposes this check as a read-only command:

```powershell
python scripts/native_support_preflight.py character.glb support-preflight.json reports/support-preflight-new
```

The output directory must be fresh. This command takes the shared numerical
worker lock; scheduled work should still use the resource-guard launcher. It
does not run an optimizer, alter an asset, change a target, or select a candidate.
It is currently a CLI/API preflight, not integrated into Studio's controls.

The input has this exact structure; replace the hash, vertex indices, interval
and target with values bound to the actual single-animation GLB:

```json
{
  "schema": "strep-native-support-preflight-v1",
  "glb_sha256": "ACTUAL_SHA256",
  "animation_index": 0,
  "supports": [{
    "id": "left-foot",
    "vertex_ids": [12, 13, 14],
    "interval_s": [0.0, 1.0],
    "target_xyz_m": [0.2, 0.0, 0.03],
    "plane": {"normal_xyz": [0.0, 1.0, 0.0], "offset_m": 0.0},
    "clearance_m": 0.001,
    "horizontal_tolerance_m": 0.003,
    "maximum_vertex_displacement_m": 0.03
  }]
}
```

Vertex IDs index the complete decoded mesh population in primitive order. Every
selected vertex is required to clear the plane; the arithmetic centroid's
tangential projection must reach the target within the stated radius. The
target's normal coordinate does not add a height constraint. The plane is
`dot(unit_normal, point) = offset_m`, with clearance on its positive side.
The command supports finite single clips up to 30 seconds, one to 64 intervals,
at most 20,000 distinct vertices per support and at most 20,000 audit times. It
includes exact interval boundaries, every native key/midpoint and a 120-Hz grid;
it rejects oversized populations instead of truncating them.

Thirty-one checks cover combined bounds, a constructive relaxed-bound witness,
individual clearance, rotated/translated planes, equality/roundoff, malformed
inputs, complete populations, exact fractional intervals and source binding.
The actual KayKit preflight independently reproduces all 1,402 contact/time
bounds within 1.39e-17 m and all 41 decisions, and recomputes target identities
and anchors from the source. Evidence is `reports/support-preflight-v1/`;
35 resource observations replay, peak RSS 117,673,984 bytes. No motion quality
or release gate is approved. Next: propose a different, explicit anchor under
the unchanged edit limits, retain this impossible request, and only then test
articulated and temporal feasibility.

## Anchor selection and articulated follow-up

The next proposal changes only the two fixed anchor coordinates, retaining the
30 mm mesh/joint limit, 25 mm ankle limit, 15-degree local rotation limit,
1–5 mm support-height interval and 3 mm horizontal tolerance. Each sampled
centroid supplies a necessary planar disk: its radius is the horizontal
tolerance plus the remaining horizontal movement after the required vertical
clearance is accounted for. A conic proposal maximizes the shared radial slack
inside all 701 disks for each foot. This relaxes articulated constraints and
does not establish reachable foot poses or a globally certified optimum.

The initial harness in `reports/kaykit-wave-anchor-proposal-v1/` rejects at its
strict solver-status assertion and is retained, with 21 resource observations.
The second version records both `AlmostSolved` statuses and checks the proposed
coordinates against every necessary disk and the original displacement preflight. Its anchors move by
7.658426 mm left and 6.213337 mm right, leaving minimum necessary-disk slack of
4.689377 mm and 12.609713 mm respectively. Fresh decoded-mesh preflight finds
zero necessary-bound conflicts, with all source centroids and clocks unchanged.
The proposal uses 27 resource observations and peak RSS 95,166,464 bytes.
Evidence is `reports/kaykit-wave-anchor-proposal-v2/`. No asset or limit changes.

Actual leg fitting with those anchors is still unsuccessful. In
`reports/kaykit-wave-contact-feasibility-v2/`, 70 of 240 native-key leg solves
remain unresolved: 61 left poses at frames 23–83 and nine right poses at frames
104–112. Independent replay covers all 701 times and matches the floor track
exactly. The candidate reaches 16.233378 degrees local rotation change,
30.597925 mm joint movement and 26.440083 mm ankle movement, exceeding the
unchanged limits. It records 1,485 violations and fails both rate gates. The
candidate remains unselected. Proposal/replay traces contain 165/31 resource
observations; peak proposal RSS is 139,304,960 bytes. This demonstrates why
passing a necessary geometric relaxation is insufficient for motion approval.

`reports/kaykit-wave-articulated-anchors-v1/` then couples an anchor with leg
rotations at measured conflict and endpoint poses, while retaining the complete
necessary-disk population. Left frames 0, 28, 107 and 119 remain unresolved; the
local solver's "Inequality constraints incompatible" message is not a global
infeasibility certificate. Right frames 0, 108 and 119 meet the selected-leg
geometry checks at a different proposed anchor. This is only a three-pose
initialization, not a full clip or whole-body floor result. All rate and release
gates remain unapproved. The trace contains 38 observations and peak RSS
113,614,848 bytes.

An independent replay in `reports/kaykit-anchor-replay-v1/` applies the saved
rotations as world-space pivot transforms, instead of the proposal's local-FK
assembly. It reproduces the left failure and the right selected-pose geometry
result and verifies that unrelated local transforms and every local translation
stay fixed. It also measures the left-minus-right sole-centroid track diameter:
87.418328 mm, witnessed at 1.5333333015441895 and 3.5999999046325684 seconds.
The original interpretation assumed exact cancellation of a common root shift.
The stored floating-point skin responses differ slightly, so the claim about
unrestricted translation is superseded by the bounded calculation below. This
does not rule out a combined pelvis-and-leg edit, root rotation or different
contact intent; it is not a formal interval proof.

Next work should compare a separately declared pelvis-and-leg edit under
explicit root-track permissions, with full mesh, contact and rate validation.
The original frozen-root requests and rejected candidates must remain intact;
an expanded authoring policy must not be reported as passing the old policy.

## Pelvis-and-leg authoring variant

This separately versioned experiment permits mapped pelvis node 21 translation
and the same six leg rotation tracks, including endpoint keys. All other tracks,
clocks, geometry and weights remain unchanged. It adds an explicit 30 mm root
movement limit and retains the previous 30 mm mesh/joint, 25 mm ankle,
15-degree rotation, 1–5 mm support height and 3 mm horizontal-target limits.
It is not a successful result under the original frozen-root permission.

The first attempt (`reports/kaykit-wave-pelvis-legs-v1/`) stops before producing
a clip because its assumed unit upper bound on non-leg skin response is too
strict. Float32 weight normalization can leave a small stored residual. The
second attempt uses `translation_coefficients` from the existing root-contact
implementation, including each inverse-bind homogeneous response. The largest
non-leg coefficient is 1.0000000894069672. Its search root radius is tightened
to 29.899997326732 mm, retaining the 0.1 mm internal displacement margin rather
than widening any authored limit. Every proposal checks the actual displacement
of every non-leg vertex against the predicted response; all leg influences
remain explicit in the constrained solve.

`reports/kaykit-wave-pelvis-legs-v2/` solves all 120 native keys and exports a
complete clip. Independent replay covers 701 times, reproduces the floor track
exactly and verifies the permitted track changes and original asset payload.
There is no sampled floor penetration. Maximum mesh movement is 28.938021 mm,
joint movement 25.175523 mm, ankle movement 18.939291 mm, pelvis movement
10.603836 mm and local rotation change 2.322080 degrees. Horizontal target errors
reach 2.904033 mm left and 2.902264 mm right. Four right-foot samples around
1.10–1.13333 s exceed the 5 mm maximum gap by about 11–12 nanometres after export;
the strict upper limit is retained, so the geometry gate remains failed.

Both motion-rate comparisons also fail. The largest peak increases are
0.021079 m/s positional speed, 6.080876 m/s² positional acceleration,
0.128342 rad/s angular speed and 12.743592 rad/s² angular acceleration. Fixed
source near-sole vertices have smaller excursions (6.014005/4.955827 mm left/right)
than the source, but this does not establish planted-foot naturalness. The
candidate stays unselected and has no new engine or human approval. Proposal
and replay resource traces contain 105/31 observations; proposal peak RSS is
146,333,696 bytes. The earlier failed setup has 24 observations.

Fifteen root-contact tests now include two regressions for stored weight
residuals: a response exceeding one, and unequal responses for two centroids
within the same root subtree. Six independent actual-rig translation checks
match the response model within 5.47e-16 m. The measured sole centroid responses
are 1.000000011175871 left and 1.0000000018626451 right. For root offsets bounded
by 30 mm, their difference can add at most 5.58794e-10 m to the allowed
two-time relative motion. The corrected diameter allowance is therefore
0.012000000558793545 m, still far below the measured 0.08741832819400956 m.
Translation alone remains ruled out within this explicit budget. The old
unrestricted-translation claim is not retained. Corrected evidence and the
unchanged source witnesses are in `reports/root-response-verification-v1/`;
26 resource observations replay. Earlier evidence is preserved as historical.

A full-clip temporal follow-up was launched in
`reports/kaykit-wave-pelvis-temporal-v1/`. It uses three Bernstein controls per
permitted rotation vector and root translation component, evaluated through
native-key interpolation, with the unchanged rate gates included in the solve.
The upper support-gap search limit is tightened by 0.1 mm to leave export room.
Per-joint/metric minimum reductions retain all 155,964 original sampled rate
inequalities in 328 equivalent constraints, including the original time-varying
four-bin caps. A nonnegative restoration slack is a search device only; final
acceptance requires independent exported-file checks without slack. No result
or quality approval is inferred from launch or intermediate solver progress.

### Temporal checkpoint replay and developer comparison

The temporal follow-up stopped at its 900-second execution guard, after 49
completed callback iterations and 3,200 evaluations. Its 903 recorded resource
observations replay successfully; peak process-tree RSS was 245,895,168 bytes.
This is an interrupted search, not optimizer convergence or a proof that the
contact problem is infeasible. The original checkpoint and failed run remain
unchanged.

`reports/kaykit-wave-pelvis-checkpoint-v1/` reconstructs that checkpoint's 63
controls into a separate GLB without restarting the optimizer. A separate
readback checks all 701 audit times, preserved asset payload and unchanged
tracks. The candidate fails the geometry and both motion-rate gates: maximum
mesh/joint/ankle/pelvis changes are 64.755936/51.692780/44.839737/42.487755 mm,
and maximum local rotation change is 25.980762 degrees. Horizontal support
errors reach 6.265735/6.265280 mm. There are 5,884 failed sampled conditions;
every sampled pose exceeds the mesh, joint, root and angle budgets. Maximum
sampled floor penetration is 4.701968 mm. Export and replay each have 34
resource observations, with every floor observation reproduced exactly.

The search's restoration slack allowed violations while searching; it does
not relax the final limits. Although positional/angular acceleration peak
increases are smaller than the per-key candidate's, increases remain
0.180693 m/s² and 1.848711 rad/s², respectively. Positional/angular speed peak
increases are 0.024084 m/s and 0.247389 rad/s. No correction is selected. A
useful next experiment must keep authored edit budgets hard during search and
measure whether the temporal basis can represent the needed correction before
spending another full solve on the same representation.

The non-blind developer packet in `reports/kaykit-wave-developer-review-v1/`
contains the prepared original wave, the per-key candidate and this interrupted
temporal candidate. It retains native GLB bytes and labels both correction
failures. It includes local viewer dependencies and asset/helper attribution;
it contains no model weights, automatic scores, cleanup measurements or
independent animator evidence. Its archive is checked against every inventory
entry. Browser rendering and engine import of these two new candidates remain
untested, and packaging does not confer quality or release approval.

To review on Windows:

1. Open `reports/kaykit-wave-developer-review-v1/` in the recovery checkout and
   extract `kaykit-wave-developer-review.zip` with **Extract All**.
2. Open the extracted folder and double-click **Start Review.cmd**. Keep its
   command window open. The launcher opens `http://127.0.0.1:8771/viewer.html`.
   Python 3 and a WebGL-capable browser are required; no model download is needed.
3. Choose **original-wave**, press **Play**, and watch the entire clip at normal
   speed. Use **Front**, **Side**, **Fit clip**, and the ground grid as needed.
4. Repeat for **per-key-pelvis-wave** and **temporal-pelvis-wave**. Compare foot
   drift or hovering, knee twists/pops, body bounce, hand-wave timing and the
   start/end poses. Both candidates are diagnostic failures, not recommended
   replacements for the original.
5. Enter your own reviewer name and ratings, save each review, then click
   **Export saved reviews**. Include clip/time and a short description for any
   visible defect. Mark cleanup as not performed unless you actually edited the
   downloaded asset; viewing time is not cleanup time.
6. Keep the exported JSON. Press **Ctrl+C** in the command window when finished.

No review server was started by the packaging job. The existing crawl packet
remains available separately; this wave comparison does not replace it.

### Temporal representation diagnostic

`reports/kaykit-wave-basis-density-v1/` compares least-squares fits to the same
per-key pelvis/leg candidate. The variants use three quadratic Bernstein
controls, 5/9/17/33 uniformly spaced clamped cubic B-spline controls, or an
identity basis over all 120 native keys. All six retain the original key clock
and native interpolation. Each is exported and read back independently at 701
times with unchanged contact, edit and rate gates. This is approximation of
one rejected candidate, not a constrained solve or an infeasibility proof.

| Controls per component | Maximum rotation fit error (degrees) | Maximum pelvis fit error (mm) | Left/right contact error (mm) | Failed sampled conditions |
| --- | ---: | ---: | --- | ---: |
| 3 | 1.520559 | 1.693842 | 19.062408 / 10.050232 | 1,280 |
| 5 | 0.850151 | 1.567751 | 11.858052 / 9.226300 | 1,050 |
| 9 | 0.497866 | 1.172429 | 8.185409 / 9.062760 | 963 |
| 17 | 0.312899 | 0.799139 | 5.121410 / 6.493307 | 926 |
| 33 | 0.231200 | 0.332439 | 3.561380 / 3.452718 | 393 |
| 120 (native-key identity) | 0 | 0 | 2.904033 / 2.902264 | 4 |

Every variant fails both rate comparisons. The identity fit retains the four
strict support-gap failures of the per-key candidate. The three-control fit
also exceeds the mesh displacement budget at 17 samples; the other fits' listed
geometry failures concern support height and horizontal contact. More controls
improve approximation here, but neither a denser fit nor a smaller fitting
residual establishes realistic motion or solves the rate/contact tradeoff.

Independent verification reconstructs the source/reference offsets and every
basis, checks the least-squares normal residuals below 1e-12, and replays all
12 completed resource traces (435 observations). Its own guarded run has 46
observations. The identity export differs from the per-key reference's maximum
mesh-displacement observations by at most 5.95e-9 m; floor, pelvis-displacement
and angle observations are identical. The release acceptance contract remains
unchanged.

A separate follow-up in `reports/kaykit-wave-pelvis-temporal-hard-v1/` uses 17
controls per component (357 parameters) as an intermediate-cost experiment.
It leaves root, mesh, joint, ankle and rotation budgets outside the restoration
slack. Initial controls are reduced toward zero if needed to satisfy those
hard budgets. The solver may still evaluate infeasible trial points; only a
saved hard-feasible iterate is eligible for export. Contact and rate limits
remain unchanged and must pass a separate exported-file replay. A 0.01-degree
internal rotation margin provides export room without widening the 15-degree
authored limit. No feasibility, convergence, engine or quality result is
inferred from preparing or launching this experiment.

### Hard-budget checkpoint result

The 17-control follow-up reaches its 900-second execution guard after six
completed callback iterations. It preserves iteration 4 as the best saved
hard-feasible iterate; iterations 1, 2 and 6 fail internal edit-budget rows and
are not selected for export. The initial fit already satisfies those rows,
without shrinking. A direct partition check confirms that all 2,947 hard rows
are unchanged when restoration slack changes; only the 5,235 contact/rate rows
receive that search slack. The failed run retains 898 resource observations
and a 356,200,448-byte peak process-tree RSS.

`reports/kaykit-wave-pelvis-hard-checkpoint-v1/` exports the saved best controls
and independently replays all 701 times. All authored edit budgets pass:
maximum mesh/joint/ankle/pelvis displacement is
29.347632/25.924743/20.383238/10.727363 mm and maximum local rotation change is
2.726027 degrees. No sampled floor penetration remains. Contact still fails:
left/right horizontal errors reach 4.026356/3.545980 mm, with 126 horizontal
and 116 support-height failures. Both rate comparisons fail. Largest peak
increases are 0.006339 m/s positional speed, 0.119698 m/s² positional
acceleration and 0.015386 rad/s angular speed; angular acceleration has no
regressing joints. Export/replay resource traces have 34/37 observations.
The candidate remains unselected, without convergence, engine, human-review
or quality approval. Hard-budget selection now survives actual file readback;
the remaining contact/rate problem is unresolved.

### Ankle limits are not mesh-point limits

Studio's native-support draft limits ankle movement, while
`native_support_preflight` requires a bound on every selected mesh point.
Using the ankle number as that mesh bound would incorrectly reject requests:
rotation can move a foot point farther than the ankle. The existing Studio
adapter is therefore not silently connected to that preflight.

`scripts/rigid_support_point_bounds.py` supplies a conditional bound for the
compatible case. If a point transforms as
`p' = Q (p - c a) + c a'`, the pivot moves at most `D`, and the world rotation
angle of `Q` is at most `theta`, then its movement is bounded by
`abs(c) D + 2 norm(p - c a) sin(theta / 2)`. Here `c` is the actual homogeneous
skin response, which may differ slightly from one. The helper includes a
numerical reserve and explicitly does not claim a formal interval certificate
or establish its own applicability.

The caller must establish a rigid pivot, unchanged relative child transforms,
and that every positive influence belongs to the affected subtree. All changed
ancestors, including the pivot, must be included in a composed angle limit.
Local-key limits cannot be applied to interpolated times without an additional
bound. Partial outside influences, scale/shear and arbitrary interpolation are
not covered by this helper. It is not yet a Studio precheck or solver change.

Ten unit tests cover tight rotation/translation alignment, signed and nonunit
responses, coordinate shifts, malformed limits, a false rejection from reusing
the ankle budget, and 200 fixed-seed rigid transforms. Actual-rig verification
in `reports/native-ankle-preflight-bound-v1/` checks 96 transformed poses across
107 left-foot and 105 right-foot vertices: all 10,176 point observations stay
inside the conditional bound. The rigid skin identity matches decoded points
within 3.34e-16 m. This validates the stated fully owned vertex case, not all
possible rigs, an animation correction or the missing Studio integration.
