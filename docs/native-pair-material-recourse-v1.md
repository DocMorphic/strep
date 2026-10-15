# Recenter a paired correction on actual decoded motion

The [individual-witness trial](native-material-threshold-bounds-v1.md) produces
three smaller steps that pass their affine material bounds and fail after
quaternion export. The smallest has 251 failed material rows, with 1.714591
micrometres of maximum excess, while every original native motion row passes.
This motivates a small local correction using actual decoded observations.
Original limits and the original source epoch remain the acceptance authority.

`native_pair_material_recourse.recenter` rebuilds native motion, authored
contact, complete-clock floor and local guide vectors from a decoded pose. It
requires the complete cached parent row layout, unchanged original native and
contact caps/scales, and the original zero-clearance scalar-lift offsets and
scales. Actual scalar gaps replace the old values inside that same lift; gaps
outside its domain reject. Every parent cap and scale remains byte-value exact.
The returned vectors are actual observations. Reusing a cached Jacobian does
not make its derivatives exact at the new point.

`search_reserve` tightens a separate copy of responsive material caps close to
their boundaries. It never changes the material reference object or actual
acceptance caps. A failed row with no derivative response rejects explicitly;
it is not dropped. The reserve must be finite, non-boolean and greater than zero
through 10 micrometres. No motion bound, penetration tolerance or failed
baseline physical condition becomes weaker or passing.

## Validation

All **38** selected checks pass in **27.87 s**: 13 new recourse cases and the
existing 25 material-distance cases. Tests check actual decoded native/contact
vectors, complete scalar floor/guide equivalence, exact cached-anchor replay,
independent copied caps, foreign layouts or original limits rejecting, selective
search-only tightening and failed fixed rows remaining visible.

The local 512 MiB CPU guard completes in **44.985 s**, peak sampled tree RSS
**144,629,760 bytes**, with all **46** resource observations replayed and the
additional 600 MiB free floor. Local records remain under ignored
`reports/native-pair-material-recourse-tests-v1`. Inventories contain **523
Python test modules / 45 Node suites**; contact/rig contains **87 Python modules
/ five Node suites**. These are inventory counts, not a full-inventory pass.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38733099274)
at `881b4af` passes all **13 recourse cases per OS**: Ubuntu **2.09 s**, Windows
**11.66 s**. It is distinct from the 38-case local selection.

## Actual trial and contact edit coverage

The separate `reports/high-five-material-recourse-v1` trial starts from the
previous decoded eighth-step candidate. Its individual material caps still
refer to the earlier experimental anchor, and its native limits still refer
to the original zero-control assets. It reconstructs actual parent values,
recomputes only the material derivatives with a 1e-5 difference step, retains
the frozen parent Jacobian as an approximation and uses a **0.001** control
trust limit. The search reserve is **0.2 micrometres**. Candidate exports must
pass the original native/material/contact/floor and independent mesh gates.
The original source remains selected. Any internal improvement still needs
complete geometry, physical, engine and human validation.

The read-only `reports/high-five-material-edit-support-v1` audit binds the
native clock arrays, source assets, seed declarations and authoring requests.
For each actor it confirms 120 keys, active keys 30–48, and the same four
editable nodes: `RightShoulder`, `RightArm`, `RightForeArm` and `RightHand`.
Their open temporal support is **(0.9666666389, 1.6333333254) s**. All three
authored meeting/contact requirements occur at **2 s**, outside this support
for every participating actor. The endpoints 0 and 3.9666666985 s are frozen;
the joint-displacement bound remains 50 mm.

A separate saved-observation extraction,
`reports/high-five-contact-gap-metadata-v1`, records the existing 2-s position
errors: A-to-world **19.698643 mm**, B-to-world **16.538065 mm**, and hand-to-hand
**33.282370 mm**, each against its authored **30-mm** limit. The two world-target
rows already pass that position test; the hand-to-hand row misses by about
3.282 mm. This is an extraction of saved contact vectors, not a fresh pose,
reachability or interaction-quality validation.

This is a necessary temporal-coverage audit, not a reachability or skin-response
proof. The current correction can study an earlier approach interval; it
cannot solve the full authored contact task with these permissions. Subsequent
contact work needs declared edit support covering the target time, plus actual
reachability, native-motion, geometry, floor and engine checks. Broader actions,
rigs, objects, editing/style, held-out and human cleanup evidence remain required
under the single project-wide goal.

## Recourse outcome

Rebuilding the current parent values reproduces all original caps and scales,
with zero native motion failures and no worsening of the original floor/contact
conditions. The authored contact test still fails. The material Jacobian takes
**4.421 s**; the **0.2-micrometre** search reserve tightens **294** responsive
near-boundary rows while the actual acceptance caps remain unchanged.

The **635,216**-row, **2,910,025**-nonzero local problem retains **624,845** hard
rows. At trust **0.001**, the solver reports `PrimalInfeasible` after **34
iterations**. No direction is returned and no new candidate is exported. This
is an outcome for this local affine model and tighter search caps, not proof
that the actual motion problem or all possible corrections are infeasible.

The guarded trial completes in **426.516 s**, peak sampled tree RSS
**514,990,080 bytes**, with all **418** resource observations replayed under the
unchanged 1 GiB CPU profile plus 600 MiB free floor. The original source stays
selected; no new geometry, engine, semantic or human-quality pass is implied.

The frozen follow-up `reports/high-five-material-recourse-affine-diagnostic-v1`
removes only the extra search reserve. At trust 0.001 and 0.02, the solver
reports `InsufficientProgress` after 37 and 32 iterations respectively, returning
no direction in either case. This does not establish feasibility or
infeasibility, nor isolate the reserve as the cause of the first outcome.
Original caps/scales remain exact; no pose is exported. Its guard completes in
**32.500 s**, peak **321,257,472 bytes**, with all **34** observations replayed.

Further approach-only retries do not address the uncovered authored contact.
The next full-task step is contact fitting with declared edit support covering
2 s and an explicit objective for the remaining hand-to-hand gap, retaining
original motion bounds, source provenance and independent geometry acceptance.
The present local-recourse failures remain visible and do not become approval
of a less constrained clip.
