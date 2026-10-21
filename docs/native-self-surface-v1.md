# Native self-surface diagnostics

The rejected high-five hand edits expose disagreement between local signed
distance and ray/winding containment. Positive volume and consistent closed
topology do not establish a valid, non-self-intersecting character surface.
Self-surface evidence is needed before interpreting the disputed metric or
choosing another correction. The containment investigation is recorded in
[native-containment-crosscheck-v1.md](native-containment-crosscheck-v1.md).
Explicit original-axis guidance for subsequent corrections is described in
[native-self-separation-cuts-v1.md](native-self-separation-cuts-v1.md); those
proposal bounds do not replace the complete checks described here.

`scripts/native_self_surface.py` screens every unique pair of original
triangles whose numerical bounding boxes overlap, then uses the unchanged
`triangle_crossing.classify` predicate. It records transverse crossings,
coplanar/near-parallel area overlap and boundary contact between triangles
with no shared vertices. Shared vertices are counted and never suppress a
proper crossing, including a crossing away from one common vertex. Ordinary
shared-topology boundaries remain counted rather than stored as defects.
Every degenerate face is reported separately.

Input bounds are 250,000 vertices and 100,000 faces. Explicit budgets cap
candidate pairs and retained records; exhaustion raises without returning a
complete truncated report. The default budgets are two million candidate
pairs and 50,000 records, at 1e-7-m tolerance. Bounds do not guarantee peak RSS;
actual studies still use a guarded worker. Spatial boxes are streamed through
an index rather than allocating an all-pairs matrix.

Seventeen local tests cover valid box adjacencies, an analytically known
transverse crossing and rigid transform, shared-vertex crossings, folded
coplanar neighbors, nesting, degenerate faces, complete brute-force pair
comparison, exhausted budgets and malformed inputs. The guarded test run
completes in 18.234 s at 97,628,160 sampled bytes; all 20 resource observations
independently replay. Inventories contain 551 Python/45 Node suites, with
115/five in the contact subset, not full-inventory passes.

This is a sampled diagnostic API, not a solid-volume proof, continuous-time
collision certificate, animation quality decision or automatic repair. Nested
components and ambiguous contacts still need separate treatment. No old
evaluator, source clip, matrix reference or receipt is replaced.

A source-bound study compares complete self surfaces at 2 s for both original
actors and the rejected 30-degree finger-edit pose. Each completed case is
saved before the next starts. This is four complete single-pose mesh queries,
not a complete animation or a change in the selected asset.


## Actual source and rejected pose

The same seventeen tests pass on Ubuntu (0.62 s) and Windows (0.55 s), run
38976673483, source 4bd9c2c. Complete scans of each 18,056-vertex/36,108-triangle
mesh at 2 s finish as follows. These original sources are the configured scene
clips, not a claim about every raw neural output.

| Actor | Configured source crossings | Rejected 30-degree edit crossings | Retained / removed / introduced pairs |
| --- | ---: | ---: | --- |
| A | 232 | 608 | 131 / 101 / 477 |
| B | 135 | 482 | 70 / 65 / 412 |

All stored records are transverse crossings; no degenerate face or other
ambiguous record is reported in these four queries. The combined guard takes
222.860 s at 138,993,664 sampled bytes (221 observations), independently
resource-replayed. Each individual complete case remains saved.

The existing independent rational `exact_triangle_crossing_witness` method
constructs and replays a strict-interior witness for every one of the 1,457
reported triangle pairs. It proves these crossings for the represented
binary-float coordinates; it does not certify prior animation/skinning
arithmetic, unreported pairs, complete volumes or motion. Fresh source skin
reconstruction also reproduces the stored original vertex arrays exactly.
Each mesh has one connected vertex component. This replay completes in
27.282 s at 128,430,080 bytes (29 resource observations), independently
resource-replayed.

Many introduced records carry Index2/Middle2/Ring/Pinky skin weights. Other
unchanged records include head, jaw, torso/arm and toe labels. These are
summed influence descriptions, not reviewed anatomical regions. The four
unresolved A-to-B containment points lie 4.589–8.298 mm from exactly witnessed
self-crossings in B's index/middle region. Proximity does not establish the
cause of the containment disagreement, but whole-body positive volume alone
is plainly insufficient to treat this edited mesh as a valid collision solid.

The correction is rejected: it reduces partner crossing records while adding
many self-crossings. No larger edit budget is adopted. The next investigation
compares existing finger rotations and the unanimated bind mesh before choosing
explicit hand-posture/axis restrictions or repairing the source geometry.
Whole-clock self/partner checks, contact, rates, engine and human evidence
remain required; the selected source assets and release gates are unchanged.


## Bind mesh and reference-posture screen

The stored unanimated bind-position mesh is exactly shared by both actors.
Its complete scan finds 61 transverse pairs, each with an exact represented
triangle witness: head/head 32, head/jaw eight, left toe 15 and right toe six
under descriptive skin-weight labels. None touches the declared 5,892-face
right-hand region. This separates an asset-level issue from later hand edits;
it does not excuse inherited geometry or approve the character. The guard
completes in 77.234 s at 134,017,024 bytes (78 observations), resource-replayed.

A localized screen includes every original triangle incident to a vertex with
any positive right-hand-descendant weight, without a mass threshold or omitted
skin influence. It interpolates existing local source quaternions toward the
rig's stored bind quaternions while retaining source translations, scales and
zero-reference bounds. At fractions 0, 0.5, 0.85 and 1, detected hand-region
records are respectively 101/0/0/0 for A and 65/0/0/0 for B. Fractions 0.5 and
0.85 pass the declared angular/displacement permissions; fraction 1 exceeds
30-degree finger limits and is not accepted. These are localized single-pose
results, not anatomical or whole-body/motion clearance. The screen guard takes
94.469 s at 174,698,496 bytes (95 observations), resource-replayed.

## Reference fingers with arm/wrist fitting

A distinct proposal fixes the fingers at the halfway reference posture and
fits only nine arm/forearm/wrist controls per actor. It retains the original
zero epoch, prior 20-degree finger caps/30-degree Thumb1 cap, 60-mm world-joint
displacement and physical contact/geometry limits. The former conservative
whole-hand halfspace fitting guide is explicitly omitted; this changes that
proposal condition, not physical collision acceptance or any release gate.

The first integration attempt stops before fitting because its experiment
script refers to a deleted initializer. That failed output remains archived:
29.375 s, 239,833,088 bytes, 31 resource observations, independently replayed.
Its three coupled directional checks pass at 1.361493e-6 maximum absolute
normalized derivative error. A fresh corrected run retains the same check.

The corrected fit takes 13 iterations/22 observations in 19.016 s and passes
all 210 pose inequalities. Its direct marker gap is 4.997499 mm, opposing
normal error 4.997498 degrees and tangent agreement 5.100726 degrees. Both
localized hand self scans have zero records. However the complete partner
query finds 1,056 proper crossings, versus 834 in the configured source, and
reports legacy maximum signed depth 13.633041 mm. Thus the candidate is still
rejected: marker alignment and a nonfolding individual hand do not establish
contact between the complete two hand surfaces.

The corrected guard completes in 100.656 s at 267,534,336 bytes (101 resource
observations), independently replayed. Full saved worlds, vertices and all
inequalities reproduce exactly in 29.406 s at 188,112,896 bytes (31 resource
observations). Six directional frame checks stay below 1.116438e-9. These
replays do not independently rerun collision predicates. A static marked
comparison is retained at `reports/high-five-hand-diagnostic-v2/hand-comparison.png`;
its guard takes 20.219 s at 149,180,416 bytes (22 observations), replayed.

The reference posture still has curved fingers that interlock when the
selected patches meet. The next geometric experiment straightens outgoing
finger directions in an explicitly declared palm plane, clips every rotation
against the unchanged source-relative cap, and measures actual skin again.
This is an unreviewed geometric posture, not inferred anatomical limits or a
promise of collision-free contact. No clip, engine or quality is promoted.

## Native scene and character acceptance (2026-10-21)

Native scene audits now screen the complete actor triangle population for self
geometry at every declared sample. Imported-mesh audits reuse those actor
observations and additionally screen every prop. Crossings, stored ambiguous
surface relations and degenerate faces fail sampled scene acceptance and make
that target's containment unavailable, even when the other entity is far away.
Normal shared-vertex boundary contacts retain the existing treatment in the
self-surface diagnostic; shared topology never hides proper crossings.

The reports include triangle-index digests, the self-surface method version and
the complete per-sample observations. The existing geometry journal commits
these with each complete frame. Exhausted pair/record budgets produce no
complete report; interrupted frames cannot supply missing evidence to a fit.
Sampled eligibility is not a proof of a valid solid, absence of nested shells,
or continuous collision freedom. The release and self-collision certification
flags remain false.

Both direct and recoverable character fitting additionally compare self-surface
observations before accepting a step. The comparison requires identical complete
clocks, entity populations, triangle-index digests and tolerances. A new proper
crossing cannot hide behind an unchanged or lower total crossing count. A
retained pair's measured intersection interval cannot increase; this interval
is not penetration depth. Ambiguous or degenerate comparisons remain
unavailable. Existing crossings still fail whole-scene eligibility even when
this supplemental comparison finds no regression.

Each evaluated candidate retains `self-surface-regression.json`; recoverable
fitting pins it in the decision checkpoint. Existing source limits and depth
checks remain mandatory. Old source-bound jobs are not resumed under changed
implementations, and old geometry reports lack the new required self evidence.
Original and candidate audits must be regenerated together under the new
method. This does not change or relax the original motion permissions.

Validation: 139 focused integration checks and 84 geometry-journal checks pass.
They cover same-count crossing substitution, growth of an existing crossing
interval, ambiguous/degenerate cases, missing or changed evidence, self-invalid
props far from other entities, and mandatory rejection in both character
fitting paths. Recovery retains the new decision evidence. An initial Python
3.10 syntax failure is preserved separately with its original source snapshot;
the passing epochs use the repaired source.

The actual original humanoid and retained v3 research seed were each audited
under a separate explicit diagnostic clock at 0, 2.1375 and 3.9666666984558105 s.
The original policy, limits, planes, character assets and permissions were not
overwritten. At 2.1375 s the original has 114 proper self-crossing pairs and the
edit has 275, with 161 added pairs. The new comparison reports those 161
regressions and rejects the edit. Both three-frame geometry journals are kept
under ignored `reports/humanoid-self-guard-replay-v1`.

This diagnostic is not a replacement for the original 2,017-time evaluation.
The original itself remains unsuitable for claiming collision-free geometry.
No correction search was resumed and no animation, model or release gate is
approved. Next is to speed up the complete screen while retaining equivalence
evidence, then run a versioned full-clock comparison with recoverable execution.
