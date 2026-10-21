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
