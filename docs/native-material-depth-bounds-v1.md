# Bounds on distances to moving partner triangles

The [local-surface trial](native-pair-key-local-surfaces-v1.md) improves its
worst scalar guide while worsening some measured mesh penetrations. All 15
increased directional peak observations concern vertices already present in
the witness set. A scalar projection cannot protect full three-dimensional
distance: a step can improve its normal component and increase its tangential
component enough to increase its length.

`native_material_depth_bounds.MaterialDepthBounds` adds hard vector-norm rows
to the existing original-bound temporal problem. Each inside-vertex witness
retains its actual canonical source vertex and a convex barycentric point on
its actual target triangle. Both points follow their respective edited skins.
For source point p and target surface point q, nearest-surface distance is at
most `||p-q||`. When that tracked point is inside the target, its depth therefore
has the same upper bound. This is conditional protection for the tracked
vertices, not a certificate for new contacts, crossing counts, volume validity,
every vertex, or continuous time.

Rows are grouped by time, source actor and target actor. Each group retains the
largest reference material distance as its hard cap; it does not silently reset
to a changed proposal. In the actual trial those reference maxima must match
the independently saved directional peak depths within 1e-10 m. Fixed material
points are conservative: tangential motion or motion out of an intersection can
increase their distances, even when actual nearest-surface geometry improves.
Independent mesh checks remain necessary, and later iterations may need fresh
witnesses. No bound here changes the authored physical acceptance limits.

The helper validates actual canonical triangle identity, convex weights,
explicit row/nonzero budgets and unchanged caps. It computes only additional
material-vector derivatives. Exact native-key support intervals and independent
plane-offset variables identify structurally zero columns; numerical small
slopes are not discarded. Composition inserts these rows after the existing
hard prefix, retaining every parent row, cap, scale and soft objective.

## Source validation

The 16 new cases and 26 existing local-surface cases pass together: **42 checks
in 26.44 s**. They cover the scalar-projection counterexample, actual moving
triangle points and nearest-distance inequality, separate directional reference
groups, finite-difference agreement, both actors responding, structural zeros,
immutable caps, malformed canonical faces, explicit budgets without truncation,
and exact retention of all parent rows during composition.

The guarded local selection completes in **42.703 s**, peak sampled process-tree
RSS **143,671,296 bytes**, with all **44** resource observations replayed. It
uses the unchanged 512 MiB CPU profile and additional 600 MiB free floor. Local
records remain under ignored `reports/native-material-depth-tests-v1`.
Inventories contain **522 Python test modules / 45 Node suites**; contact/rig
contains **86 Python modules / five Node suites**. These are inventory counts,
not a full-inventory or release pass.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38729067955)
at `846f326` passes all **16 new cases on each OS**: Ubuntu **1.97 s**, Windows
**12.25 s**. This is distinct from the 42-case local selection.

## Actual temporal trial

The trial under ignored `reports/high-five-material-depth-temporal-v1` uses the
same original source epoch, original motion limits, experimental half-step
anchor and five declared guide times as its parent. The original asset remains
selected. It reuses the frozen parent affine matrix after binding its source
files, numerical methods and complete cached starting observations. The one
report-label fix is admitted only with an identical `SurfaceRows` class AST and
the independent byte-exact witness replay. The full parent Jacobian is not
recomputed.

There are **1,146** material rows in **ten** directional/time groups. The
combined problem contains **635,216** norm rows and **2,910,025** nonzeros;
**624,845** rows are hard. The original **619,662** native motion rows, three
authored-contact protections and **4,034** floor protections remain present.
The additional Jacobian takes **3.641 s**, with **77,751** nonzeros. Of 456
control columns, 336 are structurally zero and 120 require differences; the
full global control dimension is retained.
Four decoded step fractions are screened against the original native bounds,
material bounds and contact protection before floor and independent geometry
checks. Skipped downstream checks are not passing evidence. Authored failed
floor/contact conditions remain failures even when a proposal does not worsen
them. No new model inference, training, engine execution, human review or
release qualification is implied.

The primary affine solve reports **Solved in 34 iterations**. Its optional
minimum-norm phase is rejected: the first result is `AlmostSolved` without
passing the affine bounds, and the retry reports `NumericalError`. The primary
direction is retained for decoded screening only.

| Step fraction | Native failures | Material failures | Full-clock floor protection | Five-time mesh screen |
| --- | ---: | ---: | --- | --- |
| 1 | 1 | 1 | Skipped after rejection | Skipped |
| 0.5 | 0 | 1 | Skipped after rejection | Skipped |
| 0.25 | 0 | 0 | Pass | Reject: increased counts |
| 0.125 | 0 | 0 | Pass | Reject: increased counts |

Both smaller steps reduce all **ten** directional peak depths at the five
declared times. The quarter step, for example, changes A-inside-B at
1.233333349 s from **15.673294 to 15.244659 mm**. However, at that same time its
surface crossing records increase **216 to 218**, and vertices deeper than the
unchanged 5-mm threshold increase **17 to 18** in A and **131 to 133** in B. The
eighth step also increases some counts. **No step advances.** Independent
geometry acceptance retains all measures; an improved peak cannot compensate
for a rejected count. Failed baseline physical conditions remain failed.

The run completes in **523.656 s**, with peak sampled tree RSS **876,314,624
bytes**, and all **512** resource observations replayed under the unchanged
1 GiB CPU profile plus 600 MiB free floor. Cached-kernel reuse avoids rebuilding
the full parent Jacobian; this elapsed time is not a matched performance
benchmark against the parent run. Original inputs, all rejected exports and
method snapshots remain local and immutable.

## Remaining count regressions

A separate read-only diagnostic, `reports/high-five-material-depth-attribution-v1`,
freshly queries the complete canonical source-vertex population in the three
directions/times with increased deep-vertex counts. Its counts and peak depths
match the saved measurements exactly. All **six added threshold-crossing
observations** (four distinct vertices across two probes) were already tracked
inside vertices. For example, A vertex 10924 moves from **4.389942 to 5.316108
mm** at the quarter step while its group's larger peak still improves. Group
peak protection therefore leaves a demonstrated threshold gap; these count
increases do not require previously missing inside-vertex witnesses.

The diagnostic also records the added and removed triangle-pair identities for
each increased crossing count. It does not infer that threshold bounds solve
those crossing identities. The two larger steps' material violations concern
the same tracked vertex 16944 at 1.133333325 s, with distance excesses **32.245236
micrometres** and **2.887035 micrometres**; the full step also has one native-row
violation. Original acceptance remains strict.

The diagnostic completes in **28.579 s**, peak **189,739,008 bytes**, with all
**30** resource observations replayed under the 512 MiB CPU profile plus
600 MiB free floor. It creates no new poses and makes no adoption decision.
The next experiment should protect individual existing witnesses against the
declared depth threshold while retaining their deeper reference bounds and
the separate complete mesh screen. New contacts and crossing regressions still
require independent measurement. Broad action, rig, object, editing, style,
engine, held-out and human cleanup evidence remain required under the single
project-wide goal.
