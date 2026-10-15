# Individual partner witnesses retain the declared depth threshold

The [group-distance trial](native-material-depth-bounds-v1.md) reduces all ten
selected peak depths but lets some tracked shallow vertices exceed the
declared 5-mm penetration threshold. A fresh full-vertex query attributes all
six increased-threshold observations to four already tracked vertices. The
next proposal must preserve those individual threshold conditions as well as
the group peak.

`MaterialDepthBounds(..., penetration_limit_m=limit)` explicitly enables this
policy. Each existing witness receives a distance cap equal to
`min(group_reference_maximum, max(individual_reference_distance, limit))`.
Existing deeper distances therefore cannot increase, shallower witnesses
cannot exceed the declared threshold, and no row can exceed its group peak.
The reference pose remains feasible. The original group policy remains the
default when no threshold is declared. The limit must be finite, numeric,
non-boolean and in the existing geometry policy's 0–0.1 m range.

These are upper bounds on distance to fixed material points on moving target
triangles. Their conservatism remains explicit: they can reject tangential or
outward motion that improves true nearest-surface geometry. Their guarantee
applies only to the declared tracked points and times, assuming the stated
surface/inside interpretation. They do not bound new contacts, crossing counts,
self-intersection, volume validity or continuous time. The independent mesh
screen and original physical acceptance limits remain necessary.

The cap policy does not change vector definitions, derivative columns, native
motion limits, original source epoch, or the reference skeleton/skin. Tests
compare both policies' vectors and complete Jacobians exactly. The derivative
report records the policy and declared threshold; the original full Jacobian
does not need rebuilding merely because these caps tighten.

## Source validation

The final selection passes **51 checks in 33.99 s**: all 25 material-distance
cases (nine new threshold cases) and the 26 existing local-surface cases. The
new cases reproduce a shallow-witness threshold crossing permitted by the group
peak, retain the group ceiling even with a larger threshold, allow zero
threshold with exact reference feasibility, compare complete derivative
matrices across policies, record the explicit policy and reject malformed
thresholds.

The 512 MiB CPU guard completes in **51.938 s**, peak sampled tree RSS
**146,661,376 bytes**, with all **52** resource observations replayed and the
additional 600 MiB free floor. Records remain under ignored
`reports/native-material-threshold-tests-v2`. The initial selection is preserved
under `-v1`: three new fixture cases accidentally bind the second actor's scene
instance and correctly reject. Fixing that fixture to use the exact original
pair scene changes no production scene-binding rule.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38730235623)
at `0a8ce1c` passes all **25 material-distance cases per OS**, including the nine
new threshold cases: Ubuntu **3.33 s**, Windows **14.45 s**. This is separate
from the 51-case local selection, not a full source-inventory pass. Inventory
counts remain 522 Python modules / 45 Node suites, with 86 Python modules /
five Node suites in contact/rig.

The actual trial is recorded separately under
`reports/high-five-material-threshold-temporal-v1`. It retains the original
zero-control source epoch, prior experimental anchor, native motion bounds,
floor/contact protection, five declared guide times and four-probe budget.
The declared geometry policy supplies the threshold; it is not tuned against
candidate outputs. The original source animation remains selected. Complete
physical, engine, semantic, human and release evidence remain separate.

## Guarded solve and separate validation

The original-bound affine problem retains **635,216** norm rows, **2,910,025**
nonzeros and **624,845** hard rows, including all **619,662** original native
motion conditions. The additional 1,146-row material Jacobian takes **3.828 s**.
The primary fit reports **Solved in 33 iterations**. Both optional minimum-norm
attempts report `NumericalError` and are rejected; their output is not selected.

After the direction is saved, external free RAM drops to **514,048,000 bytes**,
below the unchanged 600 MiB floor. The guard stops the worker before any decoded
probe result is completed. The retained failed attempt records **260.546 s**,
peak sampled tree RSS **876,609,536 bytes**, and all **256** resource observations
replay. This is a resource stop, not motion acceptance or a numerical
infeasibility result. Its partial `probe-00` remains untouched.

A separate run, `reports/high-five-material-threshold-probes-v1`, resumes only
the saved direction. It must verify all original method and input hashes,
reconstruct the source-bound models and reproduce the starting controls and
material vectors/caps/scales exactly. The full affine matrix and solver are
not loaded. Each candidate is freshly exported and checked under the same
four-fraction protocol and unchanged original acceptance rules. The resumed
run retains the same 1 GiB CPU admission/peak profile and 600 MiB free floor;
avoiding a repeated solve does not weaken either resource guard.

The separate validation completes in **403.547 s**, peak sampled tree RSS
**477,294,592 bytes**, with all **395** resource observations replayed. Its
binding receipt confirms exact reconstruction and reuse of the saved direction;
the original partial export is never reused. All four fresh decoded candidates
pass every original native-motion row and contact-protection row. They fail
**288, 279, 264 and 251** individual material-distance rows at fractions 1,
0.5, 0.25 and 0.125 respectively. No candidate advances. Floor and independent
mesh checks are skipped after these material rejections, so this trial supplies
no new passing floor, threshold-count or crossing evidence.

## Actual versus affine distance residuals

The read-only `reports/high-five-material-threshold-residuals-v1` diagnostic
compares saved actual vectors with the material Jacobian's predictions, retaining
the original caps. All **1,146** reference vectors, group caps and the complete
sparse material Jacobian match the previous group-policy trial exactly. Of the
witnesses, **472** have reference distance at or below 5 mm and **674** are deeper.

| Fraction | Actual failed rows | Failed shallow rows | Maximum actual excess | Maximum vector prediction error |
| --- | ---: | ---: | ---: | ---: |
| 1 | 288 | 1 | 108.806998 micrometres | 138.836019 micrometres |
| 0.5 | 279 | 0 | 27.206836 micrometres | 34.453587 micrometres |
| 0.25 | 264 | 0 | 6.786421 micrometres | 8.454076 micrometres |
| 0.125 | 251 | 0 | 1.714591 micrometres | 2.064030 micrometres |

All three smaller fractions pass the affine material bounds exactly but fail
after actual quaternion export/decoding. The full step also has eight affine
material residuals above zero, with maximum excess only 2.303e-11 m. Thus the
decoded discrepancies cannot be explained by that tiny primary affine excess
alone. Their reduction with step size is evidence for revising the local
approximation and checking a bounded correction from a decoded candidate;
it is not a reason to inflate acceptance tolerances.

Most rejections concern deeper witnesses. A hypothetical threshold-plus-group
search guard, retaining the shallow threshold and deeper group ceiling instead
of each deeper vertex's exact reference distance, still has **6, 4, 3 and 3**
violations. That guard is only calculated in the diagnostic; it is not applied,
does not remove all discrepancies and establishes no geometry approval.

The diagnostic finishes in **17.250 s**, peak **61,407,232 bytes**, with all
**19** resource observations replayed under the 512 MiB CPU profile plus
600 MiB free floor. It changes no pose, solve, cap or acceptance decision.
The next experiment is bounded local recourse with measured actual residuals,
preserving the original source epoch and every original motion/material cap.
The present approach window does not include the authored 2-s meeting, and its
arm-only permissions do not repair the failed source floor. Complete interaction
authoring, appropriate declared edit support, broader actions/rigs/objects,
editing/style, engine, held-out and human cleanup evidence remain required.
