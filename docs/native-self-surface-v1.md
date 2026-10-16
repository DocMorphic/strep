# Native self-surface diagnostics

The rejected high-five hand edits expose disagreement between local signed
distance and ray/winding containment. Positive volume and consistent closed
topology do not establish a valid, non-self-intersecting character surface.
Self-surface evidence is needed before interpreting the disputed metric or
choosing another correction. The containment investigation is recorded in
[native-containment-crosscheck-v1.md](native-containment-crosscheck-v1.md).

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
