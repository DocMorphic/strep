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

## Protected-suffix memory estimate

After frames 0 through 109 finish, the final batch waits for the original
1,536 MiB preflight estimate despite much lower observed usage. The coordinator
is stopped before the suffix worker starts; the raw admission record and a
separate stop receipt remain unchanged. Completed numerical work is reused.

A guarded calibration checks all six completed batches and their resource
traces. The two batches using the same worker bytes with zero selected point
rows peak at most at 794,529,792 bytes. The suffix has no previously selected
points, and its saved retained-pose partner margins are exactly one, meaning
zero observed penetration. It therefore adds no point-verification rows.
Its joint frames are already protected by the existing permissions.

Only this suffix's **preflight expectation** changes to 1,024 MiB, more than
25 percent above the observed analogous peak. This is an empirical estimate,
not a certified future memory upper bound. The live 2,048 MiB process tree
limit, 600 MiB available-memory reserve, 15-second stability period and
300-second execution limit remain enforced. The worker and geometry code are
byte-identical to the preceding version. Every remaining frame, source vertex,
target face and derivative column is still evaluated. There is no change to
motion permissions, physical thresholds or model-selection rules.

Records are `reports/retained-center-memory-calibration-v1` and
`reports/retained-center-surface-model-v3`. This expectation is not applied to
inference, training or a differently shaped numerical workload.

The suffix completes at sampled peak 806,674,432 bytes. The joined geometric
model covers all 120 frames and 480 aggregate rows, plus 6,893 selected point
rows: every previous 6,488 point and 405 additional points. All selected-row
directional checks pass at both declared step sizes. Baseline auditor margins
agree with the saved retained pose to 8.3711e-14 in normalized units, with
identical strict pass masks. This is a successful derivative-model rebuild;
it does not turn the retained animation's existing physical failures into passes.

## Global constraints and finite-difference diagnosis

The global model refreshes all 16 scalar rows and 33 vector components through
216 temporal controls. Full original joint and skin motion populations are
scanned. The first attempt stops on duplicate thread-runtime initialization;
the next version reuses the original loaded tracks for its separate dense
reference. Baseline scalar and vector values, selected motion-peak identities
and strict masks then match that reference exactly.

All 16 scalar derivative checks pass at 1e-6 and 1e-7. One acceleration-vector
component fails at 1e-6 and two fail at 1e-7. Those failures remain recorded in
`reports/retained-center-temporal-model-v2`; its overall derivative flag is
still false. It is not rewritten as a passing run.

A separate six-step diagnostic finds all scalar and vector components passing
the same 0.001 relative threshold at both predeclared qualification steps,
3e-5 and 1e-5. All original motion-peak identities remain unchanged. Independent
forward-mode pose derivatives and a separate skin chain compare every one of
the 216 columns for both problematic cones. Maximum component differences are
2.99e-16 and 3.17e-16, with exact primal vectors. Together with worsening
finite-difference errors as the step shrinks, this supports numerical
cancellation rather than a changed peak or an incorrect analytic derivative.

This qualification retains every row and vector component. It changes neither
the derivative threshold nor physical criteria. The first diagnostic admission
defers without starting a worker; a fresh version uses a longer admission
window with the same 1,536 MiB expectation and enforced limits. Evidence is
`reports/retained-center-global-diagnosis-v2`. A solver proposal still needs
actual complete-clock motion validation before any step can be retained.

## Complete refreshed proposal

The complete model has 7,389 rows, 216 controls, 517 mandatory cuts and 155
norm cones. The peak formulation still uses 433 variables. Its complete
assembly estimate is 59,034,576 bytes within the existing 64 MiB allowance;
sampled process tree peak is 229,834,752 bytes under 512 MiB.

At normalized joint step radius 0.03125, Clarabel reports **AlmostSolved**.
The raw direction independently satisfies every original box, author ball,
step ball, physical affine norm and mandatory linear cut strictly. No
optimality certificate is claimed. Within this refreshed model, peak deficit
decreases from 5.261024 to 5.218507 and summed positive deficits from
7,250.925037 to 7,084.818332. Those sums use the same new point population;
they are not compared with a differently populated older model as a quality
improvement. The proposed macro working peak also decreases. These normalized
linear predictions are not physical contact approval or measured motion.

The proposal is saved in `reports/retained-center-peak-v1`. The existing
accepted diagnostic motion remains unchanged until actual validation passes.

## Actual validation outcome

The full step fails actual hand-to-hand contact and is rejected before geometry
evaluation. The half-step then completes all 120 frames and all 496 conditions.
Fresh replay of both the current and original benchmark guards accepts it:
all 449 explicitly required conditions and all 456 previously passing conditions
remain valid. Two existing failures are repaired, reducing failed conditions
from 40 to 38. The working peak decreases from 5.281024 to 5.260118.

This remains a small **raw diagnostic improvement**. Worst partner depth changes
from 31.305121 mm to 31.200592 mm and still fails the unchanged 5 mm screen.
The palm gap is 29.991889 mm against the development 30 mm screen; this is not
physical touch, and the small margin needs fresh serialization/import checks.
No new candidate has been exported, selected in Studio, made a clean training
target or approved for quality or release. Original references and native
assets remain unchanged.

The separate stored-model audit replays all point identities, complete column
mapping and resource bindings. Frame-local lifting has zero component
difference, and all global derivative arrays are preserved byte for byte.
A further outcome reader recomputes the complete 496-row decisions from stored
raw arrays and replays both guards. These readers do not rerun all geometry or
substitute for visual review. Records are `reports/retained-center-model-audit-v1`,
`reports/retained-center-validation-v1` and `reports/retained-center-outcome-v1`.
Next export the retained 216-control motion and check original-clock native,
saved and actual engine behavior before promoting any asset.
