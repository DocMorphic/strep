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
