# Stored-key scene proposals

The optional `storage-vector` model addresses two measured limitations in native
scene proposals: Float32 key boundaries disturb numerical differences, and a
minimax step can trade a source-rate violation for a smaller contact error.
It retains all existing permissions, contact clocks and acceptance limits.

```powershell
python scripts/native_scene_fit.py contacts.json permissions.json reports/my-storage-proposal --proposal-model storage-vector --iterations 8 --trust .02 --storage-cells 64
```

Use a fresh output directory and the development dependencies in
`requirements-ci.txt` and `requirements-scene-proposals.txt`. This command does
not acquire models or characters. The scalar and existing vector modes retain
their numerical defaults. The new mode is not yet connected to Studio.

## Proposal calculation

The vector model keeps its actual stored-key residual as the base. Its Jacobian
uses continuous track values before Float32 serialization, avoiding derivatives
dominated by isolated rounding transitions. Continuous interpolation describes
the proposal only; every accepted probe is exported, loaded again and checked
against the complete original native conditions.

The affine conic subproblem treats the edit, all-joint displacement and all source
rate rows as hard constraints. Contact excess remains the minimax objective.
Protected rows cannot share the contact excess variable. A fixed failed protected
row makes that affine direction unavailable. All protected decoded rows must
also pass before accepting a step. Solver success alone is insufficient.

If the full step is rejected, a finite neighboring storage-cell search can probe
its translation direction before ordinary backoff. Each native translation
component is affine along that direction. The midpoints between adjacent
Float32 values give its rounding boundaries; intersecting the component intervals
identifies a local stored-key cell. An interior representative is checked against
actual `SceneEdits.values` before exporting it. The search walks toward smaller
step fractions and records the visited bounds, budget and whether zero was
reached. A Float64 reserve moves off ties; very narrow intervals may be skipped.
These are numerical probes, not outward-rounded interval certificates or an
exhaustive discrete feasibility search.

No native key, control degree of freedom, skin weight or timing population is
added. A direction that changes rotations makes the affine cell search explicitly
unavailable; the continuous vector proposal and decoded protected backoff still
operate. Unsupported or numerically ambiguous cell calculations are recorded.
The solver's existing control, sparse resource and iteration limits remain.

## Evidence and limits

On the existing six-bone synthetic body contact fixture, a supplied two-millimetre
triangle direction previously failed the original rate checks after serialization.
The cell search finds a nearby serialized candidate passing all original native
conditions. This direction experiment establishes the storage mechanism; it is
separate from the automatic solver trial.

The automatic solver initially used protected acceptance with a soft affine
subproblem. It preserved source limits but still failed contact after four
iterations. That failed attempt remains saved. Making the corresponding affine
rows hard resolves this tradeoff: the matched four-iteration trial still fails
by approximately 0.192 micrometres, while the extended eight-iteration budget
passes after five executed iterations. The hold's maximum error is approximately
0.999953 mm against 1 mm. This is a synthetic native correction, with no animator
or general humanoid quality claim. Both budgets remain documented; an increased
budget is not presented as a matched four-iteration success.

The final synthetic proposal also passes actual Godot 4.7.2 imported contact and
declared geometry conditions in both ordinary import and native-resource manual
authoring modes. Each mode observes 196 engine times; contact error is 0.999953 mm
and maximum held speed is 1.258851 mm/s against 5 mm/s. Maximum imported/native
skin differences are 89.47 and 59.68 nanometres. Geometry uses five declared times
and an explicit diagnostic Y=-2 plane; it is not a calibrated environment or
continuous collision test. Engine source-rate, GPU, physics and event playback
are not established by this observation.

Same-input humanoid trials use the preceding four-iteration budget. Sphere grip
still fails: left/right errors are 2.219262/2.244020 mm against 2 mm; right hold
speed is 10.192061 mm/s against 5 mm/s. Its rotation directions explicitly lack
the affine translation-cell search. The high-five retains 206.232573 mm hand
separation against 30 mm and accepts no source-safe step, despite affine solver
statuses reporting solved/almost solved. Hard bounds reveal this limitation;
they do not demonstrate that the request is impossible or that other permitted
degrees of freedom or algorithms cannot solve it.

The source rate arrays match the preceding vector baseline exactly. Original
inputs remain selected, including when native constraints pass. Geometry, actual
engine skin, playback and human quality are separate requirements. Detailed
local trials and verification are under ignored `reports/native-scene-storage-*`
folders; concise results are published here instead of character payloads or
generated motion libraries. No training is admitted and no model weights change.

Independent replay reproduces all 125 saved control vectors and
167 GLB exports byte-for-byte, their decoded merits, accepted
protected rows and passing final source-rate arrays. Final contact effectors are
checked through independent full-skin accumulation; partner target and object
interpolation still use the shared scene audit. All 559 fitting-study files rehash.
A separate imported-slot replay checks both synthetic engine contact/speed
reports and every full-skin clock sample, including 1176 vertices across the two modes;
all 383 engine-study files rehash. All 314 focused model-free tests pass.
These observations do not admit training data or satisfy the broad release matrix.
