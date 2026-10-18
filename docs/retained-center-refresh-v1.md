# Rebuild contact derivatives at the retained pose

Development experiment, 2026-10-18. The
[previous complete peak proposals](complete-peak-proposals-v1.md) all fail
actual required contact checks. Their model is still centered on an earlier
qualified pose. This study refreshes the model at the latest retained raw
Float64 pose, without changing the original animation or author limits.

The geometric model evaluates both complete 18,056-vertex character meshes and
their original 36,108-face topology at every original frame. It keeps the union
of every previously selected point, every currently failing soft point and
every positive minimum-depth point in a currently protected condition. A point
is not removed because it stopped violating at the new center. The baseline
auditor margins and strict pass masks must agree with the saved retained pose.

Every selected point is checked in the declared feasible control direction at
both 1e-6 and 1e-7 finite-difference steps. Near-boundary control groups use a
tangent-projected direction and both perturbed controls must remain inside the
original balls. The 0.001 relative derivative threshold is technical evidence;
it does not relax any physical depth or contact condition. Failure remains a
failure pending separate diagnosis.

## Query optimization with preserved evidence

The first two batches finish frames 0 through 36 using complete-source queries
for finite differences. Their raw results and source bindings are retained.
The coordinator is then deliberately stopped during admission of the next
batch, before its numerical worker starts. The unfinished admission record is
preserved with a separate stop receipt; it is not relabeled as a completed
resource audit.

A separate comparison uses all 340 selected frame-35 points, both interaction
directions, both finite-difference step sizes and both signs. All eight directed
queries reproduce the complete-source result byte for byte for depths, source
gradients, triangle indices, barycentric features and auditor depths. The
target remains the complete original mesh in every query.

The new version reuses the completed batches and continues at frame 37. Only
finite-difference verification queries use the selected source point array;
every selected row is still tested. Baseline mesh linearization still considers
every original source vertex, and actual candidate acceptance still requires
the complete geometry population. This optimization is not a reduced physical
test, a different tolerance or a new claim about continuous collision.

Local records: `reports/retained-center-surface-model-v1`,
`reports/retained-center-fd-selection-v1` and
`reports/retained-center-surface-model-v2`. Source animations, weights, rig,
scene placements, five-degree joint permissions, constant two-centimetre root
limits, protected frames and the original release contract remain unchanged.
Derivative construction is not motion quality, human-review or release approval.
