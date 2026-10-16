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
