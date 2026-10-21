# Collision guidance for character corrections

Research and experimental implementation, 2026-10-21. Optional actor/prop
triangle guidance is available in the direct character fitter. It is off by
default and is not yet exposed by Studio or its recoverable optimizer. The
generated fixtures below do not establish a solved humanoid interaction.

## Measured trigger

The fixed-panel diagnostic uses the existing humanoid clip, an authored hand
vertex and an unchanged panel. Its first character correction passes the
original editing caps and improves the point-contact error from 30 mm to
25.350371 mm, still outside the 5 mm target. Its complete 2,017-time geometry
audit fails acceptance:

| Measurement | Original | First proposal |
| --- | ---: | ---: |
| Failed condition identities | 4,282 | 4,283 |
| Failed times | 2,017 | 2,017 |
| Recorded surface outcomes | 42,666 | 55,461 |
| Maximum measured depth | 10.436307 mm | 10.436307 mm |

Two actor/panel conditions change from passing to failing, at 1.69375 s and
1.6958333333333333 s. One earlier failure resolves at 2.183333333333333 s.
The worst increase in recorded surface outcomes occurs around 1.86667 s,
before the authored 2 s touch. All six completed proposals are rejected:

| Step fraction | Point error (mm) | Surface records | Newly failing condition identities |
| --- | ---: | ---: | ---: |
| 1 | 25.350371 | 55,461 | 2 |
| 1/2 | 27.365740 | 49,004 | 1 |
| 1/4 | 28.615619 | 45,837 | 1 |
| 1/8 | 29.292192 | 44,196 | 0 |
| 1/16 | 29.642338 | 43,443 | 0 |
| 1/32 | 29.820265 | 43,043 | 0 |

All retain the editing/contact protections and improve point merit, but every
one increases surface records over the original. The trial stopped at the
3,600-second execution guard during its seventh proposal audit. Peak process-tree
memory was 475,213,824 bytes, below the unchanged 512 MiB cap. No complete fit
result was produced. The unfinished archive remains separate from completed
reports; it supplies no geometry decision.

The first comparison was independently reduced from the completed geometry
reports using the archived producer's condition/metric functions, without new
geometry queries. Input digests and the comparison remain under ignored
`reports/humanoid-mesh-proposal-analysis-v1` in the primary checkout. The terminal
six-proposal reduction and the replay of 3,559 resource observations are retained
under `reports/humanoid-mesh-correction-v3` and the original job folder. These
reductions read saved reports; they do not recompute geometry or replay numeric
arrays. All completed proposals remain rejected; no replacement was accepted.
Times are from a
nonuniform population; counts are not duration percentages. Surface records are
triangle-pair outcomes, not distinct physical collision events or penetration
volume.

## Research and existing implementation

TrajOpt uses sequential convex optimization for trajectory constraints. Its
documented collision evaluator linearizes contact signed distances with respect
to configuration variables. This is relevant precedent for adding collision
information to Strep's proposal model, not evidence that a deforming character
mesh is already handled by the robot implementation.
[Official overview](https://rll.berkeley.edu/trajopt/doc/sphinx_build/html/),
[collision evaluator](https://rll.berkeley.edu/trajopt/doc/dox_build/structtrajopt_1_1_single_timestep_collision_evaluator.html).

Its documentation distinguishes checks at discrete times from swept-volume
checks and explains that discrete checks can miss motion through thin obstacles.
Strep's current full declared clock remains a sampled audit; collision guidance
must not introduce a continuous-time safety claim.
[Official collision-cost documentation](https://rll.berkeley.edu/trajopt/doc/sphinx_build/html/misc.html).

The repository already contains useful pieces:

- `native_mesh_floor_guard.py` rebuilds floor witnesses and adds their affine
  constraints to the bounded character proposal. Complete decoded geometry
  remains the acceptance authority.
- `native_mesh_prop_scene_fit_v2.py` uses sampled signed-distance pair guards
  for authorized prop-pose changes. Those controls and permissions do not apply
  to character joints automatically.
- `native_pair_clearance_guides.py` differentiates explicitly selected partner
  points at declared native times. These are guidance objectives, not complete
  collision checks.
- `native_mesh_prop_crossing_witness.py` verifies represented-triangle crossing
  witnesses for a completed prop-fitting producer. Its producer requirements
  and 4,096-record bound do not directly accept this character trial.

## Experimental character integration

`native_mesh_character_fit.py --surface-guidance` retains every reported
actor/prop triangle identity and time from complete current and rejected
geometry audits. At each iteration, `native_mesh_character_surface.py` rebuilds
oriented triangle projection directions at the current decoded controls. All
nine vertex comparisons for each triangle pair enter the affine proposal as
hard constraints. The derivatives use every selected vertex's skin influences,
original actor placement and the prop pose at that time. Existing negative
directional gaps may not worsen affinely; passing directions retain zero
separation. These projections are not signed distances or collision certificates.

New floor vertices exposed by rejected trials are also retained. The floor
depth caps remain the current accepted geometry's measured caps. If a rejected
trial supplies new witnesses, the fitter can use the next already authorized
iteration to rebuild its proposal. The iteration, backtracking, edit, source
and contact limits remain unchanged. All decoded geometry conditions and
metrics still decide acceptance. No raw animation or prop is overwritten, and
the original remains selected even when a candidate passes sampled checks.

The implementation rejects oversized complete populations rather than dropping
rows: at most 500,000 surface rows, 100,000 floor rows and 16 million derivative
elements per model. Surface direction queries are batched without reducing the
retained population. This is contact-correction guidance, not a collision-only
cleanup tool: an already satisfied contact objective does not trigger a search
to remove unrelated collisions. Partner, self-collision and containment-only
guidance remain unimplemented.

### Measured generated fixtures

The paired studies use the same generated skinned character, point target,
unchanged cube props and author permissions for each baseline/guided pair.
The fit's geometry policy declares three times, 0, 1 and 2 seconds; its source
and contact checks retain their existing native/frame clocks. No three-time
result is a full-clock geometry result. All raw candidates and failures remain
under ignored `reports/character-surface-guidance-study-v1` through `v4`.

With translation controls only and four iterations, the guidance initially
made final contact error worse: 5.469 and 5.313 mm versus the baseline's 5.040 mm
in the two obstacle placements. The unobstructed case produced the same final
GLB bytes as the baseline. A separate attempted rotation fixture was correctly
refused because its source had no native rotation channel; that failure remains
in study v2. Later fixtures author a fresh explicit constant rotation channel
before either method runs, retaining the existing-channel requirement.

With an authorized 3-degree root rotation, 20 mm translation/displacement caps,
16 iterations, trust fraction 0.25 and four backtracks:

| Fixture | Baseline error | Triangle guidance | With retained floor vertices |
| --- | ---: | ---: | ---: |
| Blocked rotation | 10.000 mm | 3.629 mm | 2.530 mm |
| Flank rotation | 10.000 mm | 3.427 mm | 3.136 mm |

**Every obstacle case still fails the 2 mm target.** The retained-floor version
accepts 15 and 8 steps respectively; the first exhausts the bounded iteration
budget, while the second cannot find a decoded nonregressing step. The earlier
version stopped when newly exposed corners dipped below the floor. Retaining
those vertices improves the result without allowing extra floor depth. The
final flank proposals instead fail original native source checks and remain
rejected. These are small generated fixtures, not evidence of animation quality,
humanoid scalability, engine compatibility or a solved grasp/high-five.

The final fit study completed in 65.015 seconds including admission, with a
131,235,840-byte peak process tree and 66 replayed resource observations. The
512 MiB process cap and 600 MiB free-memory reserve were unchanged.

### Independent full-clock check rejects both saved candidates

Fresh policies expand only the audit clock to the original native/frame
population, retaining the same source assets, planes and thresholds. Each
original/candidate pair has exactly 969 times and matching condition identities.
The original has zero measured penetration. The saved blocked/flank candidates
have maximum depth **2.597331 / 2.600975 mm** between the three fitting times.
All Boolean conditions still pass the authored 5 mm penetration limit, but both
fail the fitter's stricter **no-worsening metric rule**. They must not be promoted
as full-clock admissible candidates.

All four complete audits and observation receipts are retained in
`reports/character-surface-full-clock-v1`. The study completed in 46.781 seconds
including admission, with a 163,627,008-byte peak and 48 replayed resource
observations. This negative result requires full-clock geometry during fitting;
adding more witness vertices at only three times is insufficient.

The subsequent paired fit in `reports/character-surface-full-clock-fit-v1`
includes all 969 times from the outset, with the same original blocked-rotation
fixture and 16-iteration/four-backtrack limits. **Neither method accepts a
candidate; contact error remains 10 mm.** The guided method retains all 9,690
triangle/time pairs and 1,938 floor vertex/time witnesses exposed by rejected
trials. Its first full step introduces collisions; its half step has 0.769428 mm
floor depth versus the original zero. Both are rejected. After rebuilding with
those witnesses, all four second-iteration proposals fail native source checks,
so they receive no geometry acceptance. A 16-iteration budget is an upper bound;
it does not override the no-admissible-step stop condition.

The paired fit finishes in 95.516 seconds including admission, with a
358,301,696-byte peak and 96 replayed resource observations. This is a completed
failed fitting experiment, not a time/memory interruption. Surface guidance has
not demonstrated a successful full-clock correction in this fixture.

A fresh decode of the ten retained source-rejected probes reproduces their
archived residual arrays exactly (`reports/character-source-row-diagnostic-v1`).
All failed source rows are positional acceleration: 6–12 rows per final
three-time flank proposal and 6–24 per full-clock blocked proposal. For example,
one full-clock row measures 0.000142514606 m/s² against an original source cap
0.000070989077 m/s² plus the unchanged 0.00001 tolerance. Other failures occur
against nonzero caps near 3.60009 m/s². These are actual decoded failures, not
proof that the authoring problem is globally infeasible. Comparing continuous
and serialized proposals is the next diagnostic; this study does not yet
attribute the discrepancy to quantization or justify changing source limits.

### Export rounding diagnostic

`reports/character-storage-diagnostic-v1` compares each of those ten proposals
with continuous values, the normal Float32-key preview and an independently
decoded GLB. **All ten continuous proposals pass every native source row.**
Rounding to Float32 introduces the same 6–24 positional-acceleration failures
seen in the GLBs. Preview versus decode differs by at most 6.395e-9 in normalized
residual; the source failures are already present in the stored-key preview.
No key times, permissions or acceptance limits change in this diagnostic.

An initial finite translation-grid experiment rounds only the existing knot
controls to nearby power-of-two increments, leaving rotations unchanged.
Twelve distinct candidates survive the original control/trust box checks; all
twelve fail decoded source checks. The rejected prototype and every candidate
are archived in `reports/character-translation-grid-study-v1`, rather than
enabled in the fitter. Aligning knot offsets does not guarantee rate-preserving
serialized keys after interpolation and changes of floating-point exponent.

### Nearby authorized control refinement

The next diagnostic varies a single existing translation control, or one axis
of all editable knots on an existing track, by small fractions of the track's
Float32 spacing. Its complete first stage records 120 exported candidates.
Some pass all original source checks, but their complete geometry audits still
show about 0.423 mm of new floor depth. They remain rejected. The second stage
was explicitly stopped after its native-only objective had already reached
zero; its completed 136 probes and an unfinished audit are retained under
`reports/character-control-neighborhood-v1`, with an operator-stop record and
the guard's failed exit. This is not a completed fitting success.

`native_control_neighborhood.py` implements a single finite pass of that search
as an optional proposal step. `native_mesh_character_fit.py --refine-storage`
uses it after an otherwise useful exported proposal fails source checks. Every
evaluated preview preserves its controls and full residual array. The first
preview that passes the original source/contact checks is exported through the
normal writer and independently checked again. Full decoded geometry can still
reject it, and surface guidance can learn new floor/triangle witnesses from it.

The original bounds, trust box, editable tracks, knot basis, frozen keys, native
key times, source rates and contacts remain in force. The search uses ten signed
step multipliers per control direction and rejects populations above 1,536
probes rather than silently dropping directions. This is not an exhaustive
search. It changes no individual stored key outside the existing control basis
and does not enable a new storage-adjustment permission. Both experimental
flags remain off by default and are not yet part of Studio optimizer recovery.

All 26 targeted checks pass: the retained rounding regression now passes after
independent export, frozen keys and control/trust boxes remain intact, invalid
option values are rejected, and existing native/surface protections and both
default recoverable-optimizer equivalence cases still pass. The final test run
uses unchanged source throughout, peaks at 138,493,952 bytes and replays all 264
resource observations. The test artifact is
`reports/character-control-refinement-tests-v1`; the original limits and release
gates remain unchanged.

### Completed combined full-clock experiment

On the **same original blocked-rotation fixture and permissions** as the failed
full-clock comparison above, enabling both `--surface-guidance` and
`--refine-storage` completes with a sampled admissible candidate. The run keeps
the 16-iteration limit, four backtracks, 0.25 trust fraction and all 969 native/
frame geometry times. Five steps are accepted among 24 exported proposals.

| Method | Final contact error | Accepted steps | Full-clock candidate passes |
| --- | ---: | ---: | --- |
| Unchanged baseline | 10.000000 mm | 0 | No |
| Surface/floor guidance only | 10.000000 mm | 0 | No |
| Guidance plus nearby control refinement | 1.999557 mm | 5 | Yes, sampled checks only |

The final candidate passes all original native source/contact rows and strict
exported edit bounds. Its complete geometry report has zero failed conditions,
zero failed times, zero surface records and zero maximum measured penetration.
The 2 mm contact threshold is unchanged. The solver retains 9,690 triangle/time
witnesses and 2,907 floor vertex/time witnesses. The original remains selected;
neither human quality nor engine/release approval is inferred.

The run completes in 283.703 seconds including admission, peaks at 463,126,528
bytes and replays all 281 resource observations under the original 512 MiB cap.
Evidence is in `reports/character-control-refinement-fit-v1`. This establishes a
successful correction on one generated fixture, not humanoid scalability,
natural animation, continuous collision freedom, a solved interaction or broad
action coverage. The flank fixture and real humanoid remain separate pending
validation.

The separate verifier in `reports/character-control-refinement-publication-v1`
reloads the final GLB and reproduces the archived constraint residual array
exactly, rechecks every strict track bound, and independently reproduces the
point-contact report and observation arrays. It verifies the complete geometry
observation receipt, all 969 condition identities, source/permission equality
with the previous comparison and the five accepted-step decisions. It reduces
the saved geometry report without rerunning triangle queries. All 31 verifier
resource observations replay; quality and release approval remain false.

To reconstruct the generated fixture, use `prepared` from
`tests/test_native_mesh_character_fit.py`, author the explicit root rotation
channel with `rotation_source` from `tests/test_native_mesh_character_surface.py`,
and permit its existing 3-degree root rotation in addition to the original
20 mm translation/displacement limits. Add a copy of the existing cube prop
whose center is the original actor vertex 2 at 1 s plus
`[-0.105, -0.2, 0.2]` metres, retaining the original contact/grip target. Bind
the resulting source hashes before either method runs. Set the geometry clock
to `native-and-frame-populations`, retaining explicit times `[0, 1, 2]` and all
original limits/planes. The comparison changes proposal methods only.

### Validation

The final guarded test run passes all 21 cases: complete pair/time collection,
wrong-binding/incomplete-report rejection, independent full-skin derivatives
with moving props and rotated placement, bounded one-sided derivatives, complete
population limits, retained floor vertices without relaxed caps, baseline byte
equality in the clear scene, failed obstacle retention, existing native fitting
protections and both recoverable optimizer equivalence cases. Source hashes
remain unchanged throughout the run. Peak process-tree memory is 158,474,240
bytes; 270 resource observations replay successfully. Earlier wrong-placement
test fixtures and their failing run remain archived separately.

### Second placement and full humanoid population (2026-10-21)

The full-clock flank-placement comparison retains the same source, 20 mm
translation/displacement limits, 3-degree root rotation permission, 969 geometry
times, 16 iterations, 0.25 trust fraction and four backtracks. Unchanged proposals
accept zero of four exports; guidance plus nearby-control refinement accepts
zero of 12. The latter retains 9,690 triangle/time pairs and 2,907 floor witnesses.
Four later eligible exports still worsen the originally zero floor penetration
by approximately 0.422260, 0.213558, 0.107384 and 0.053884 mm. They are rejected;
the 10 mm contact error remains. The following local direction solve stops with
`InsufficientProgress`. This is a failed local search, not proof of infeasibility.
Evidence: `reports/character-flank-baseline-v1` and
`reports/character-flank-refinement-v1`.

The actual humanoid study in `reports/humanoid-surface-direction-v1` verifies
the original geometry receipts, source inputs and producer methods, then builds
the complete affine model: 2,017 geometry times, 36 controls, 42,666 triangle/time
pairs, 383,994 surface rows and 2,017 floor witnesses. Its saved model has 569,384
norm rows (569,383 protected) and 10,574,466 nonzero derivatives. No time, pair,
vertex or control is discarded to fit the budget. Construction succeeds, but
solver assembly crosses the unchanged 512 MiB process-tree limit; the sampled
peak is 910,102,528 bytes before termination. No direction or candidate exists
from that attempt. The complete matrix and original producer implementation
remain saved for explicitly bound consumer studies.

### Compact representation for one-axis affine norms

`native_scene_conic.direction` now offers `linear_axis_rows=False` by default.
When enabled, a norm with exactly one supported vector axis becomes signed
linear inequalities with its original cap, scale and minimax slack. Both signs
remain unless a conservative bound over the unchanged trust box certifies one
sign. Any nonzero perpendicular component, however small, retains the complete
vector norm. Existing fixed-row and whole-box certificates are unchanged, and
every original affine norm is reevaluated after solving. This changes numerical
representation, not the feasible set, objective, edit permissions or decoded
acceptance limits.

Character fitting requires the additional explicit `--linear-axis-rows` option
(and `--surface-guidance`), and only enables it once its surface witness bank is
nonempty. Existing defaults, including surface guidance without the new option,
retain the previous representation. A clear scene retains byte-identical
baseline output. The initial broader test run caught differing clear-scene GLB
bytes when this condition was missing: 58 cases passed and one failed. That
failure is retained in `reports/axis-linear-tests-v1`; the corrected run and the
subsequent bounded-allocation implementation each pass all 22 targeted cases.
The initial run also passed both default optimizer-recovery equivalence cases.
Seven new cases compare compiled inequalities against independent norms across
all three axes, hard/soft rows, scales, both signs and tiny perpendicular terms,
and check real solver outputs and explicit boolean validation.
The final guarded run in `reports/axis-linear-tests-v4` passes all 28 targeted
cases, including both explicit character-fitting choices, unchanged clear-scene
bytes, accepted-step protections and invalid/missing-guidance rejection. It
preserves the exact conic implementation used by the two full-clock studies.

Radius calculation and scalar derivative scaling use bounded temporary chunks;
redundant sparse assembly matrices are released before later solver stages.
Every row remains in the model or has the same preexisting fixed/whole-box
certificate. This allocation change does not imply the full humanoid solve fits
the memory budget. The first separately bound consumer attempt in
`reports/humanoid-axis-direction-v1` still hit the process-tree guard at a sampled
547,782,656 bytes, before the allocation changes. It produces no candidate.

The subsequent consumer in `reports/humanoid-axis-direction-v2` pins the same
complete saved matrix and original producer separately from its new solver.
Line-level process memory observations reach the solver call at 406,450,176
bytes after bounded assembly. The solver call then crosses the limit, with a
sampled process-tree peak of 1,354,084,352 bytes before termination. No direction
or geometry candidate is produced. The watchdog samples periodically; these
peaks are observed overshoots before termination, not new allowed budgets.
This isolates a remaining backend allocation problem and does not establish
memory-safe humanoid fitting. All three resource failures remain archived.

### Mixed full-clock outcomes; experimental option stays off

The two generated comparisons use the same original inputs, complete 969-time
clock and edit/contact/iteration budgets as their predecessors. Only proposal
representation changes. These runs pin an archived draft that automatically
enabled compact rows after surface witnesses appeared; the published fitter
requires the additional explicit option. The conic implementation is identical.

| Placement | Previous guidance plus storage refinement | Compact representation |
| --- | --- | --- |
| Blocked | 5 accepted steps; 1.999557 mm contact error; passes 2 mm target | 6 accepted steps among 25 exports; 3.663002 mm; stops without another nonregressing step; fails target |
| Flank | 0 accepted steps; 10 mm contact error | 8 complete accepted steps among 35 recorded exports; 4.050580 mm; memory guard stops the run; fails target |

The last accepted exports in both compact runs have zero failed geometry
conditions, failed samples, surface records and measured penetration over all
969 times. Native source protections and strict edit caps pass, but contact
accuracy remains insufficient. The flank attempt has no final optimizer result;
its last complete accepted diagnostic is `probe-034`, not a completed fit.
Its sampled process-tree peak is 558,735,360 bytes. The blocked run completes
under the cap at 434,343,936 bytes; its last accepted diagnostic is `probe-020`.
Evidence is in `reports/character-flank-axis-linear-v1` and
`reports/character-blocked-axis-linear-v1`. The old successful blocked output
is preserved. Numerical equivalence of feasible sets does not guarantee the
same local nonlinear search path, so this experiment does not replace the
previous default method.

`reports/axis-linear-publication-v1` independently reloads both last accepted
GLBs, reproduces the stored native constraint arrays and contact reports/arrays
exactly, and verifies strict per-track edit bounds. It verifies every completed
geometry observation receipt, full 969-time identity and saved metric reduction
in the two studies, plus identical source/permission hashes and byte-identical
relocated policy copies. It does not rerun triangle queries. All eleven study
resource traces replay, and final test sources match the tested implementation.
The verifier itself completes with 53 resource observations and a 158,543,872-byte
peak. Original and experimental producer snapshots remain distinct; the decoded
problem class and conic implementation match the saved producers exactly.

The flank history file reached 72,075,888 bytes. Its last completed decision is
saved while the corresponding history entry is absent; the memory spike is
consistent with serializing the growing history. This is a separate diagnostic
lead from the traced full-humanoid backend allocation failure. Investigate
streamed atomic JSON serialization and bounded history retention without
discarding evidence, then continue solving the full-model memory problem.

### Streaming atomic history reports (2026-10-21)

`strep.save` now writes JSON incrementally to its existing temporary file before
the same atomic replacement and bounded Windows sharing-violation retries.
It no longer builds the entire encoded document and intermediate string list
in memory. Indentation, strict finite-number handling, escaping, newline behavior
and published bytes remain unchanged. An encoding or disk-write failure leaves
the previous published report intact; a later successful write replaces the
partial temporary file completely.

All 42 targeted tests pass in `reports/stream-json-tests-v1`, including 14 atomic
writer cases and the 28 existing compact-constraint/character/storage cases.
New cases compare old-format bytes across nested data, Unicode and floating-point
values, reject invalid values without publishing partial JSON, and simulate a
mid-write disk error. Existing Windows retry and permanent-denial checks remain.

One paired measurement rewrites the actual 72,075,888-byte retained flank history
in fresh guarded workers. The legacy writer is loaded from the pinned `cadf2b4`
source. Both copies exactly match the original file hash, without changing it.

| Writer | Sampled process-tree peak | Write time |
| --- | ---: | ---: |
| Previous whole-document writer | 328,728,576 bytes | 2.149 s |
| Streaming writer | 153,509,888 bytes | 2.696 s |

Evidence: `reports/legacy-json-memory-v1` and `reports/stream-json-memory-v1`.
Both retain the same 512 MiB maximum, 600 MiB free-memory reserve and 900-second
execution limit. This is a measured memory reduction for report writing, with a
small time cost; it is not a full-humanoid solver-memory or animation-quality claim.

The fresh full-clock run in `reports/character-flank-stream-json-v1` keeps all
original permissions, 969 geometry times, 16-iteration/four-backtrack limits and
the explicit experimental representation. It completes in 257.109 seconds at
a 370,212,864-byte sampled process-tree peak, under the same 512 MiB cap that
stopped the previous attempt at 558,735,360 bytes. It retains eight accepted
steps among 39 exports and stops with `no_decoded_nonregressing_step`. The last
accepted candidate remains `probe-034`: 4.050580 mm contact error, failing the
2 mm target, with zero failed geometry conditions/samples/surface records and
zero measured penetration across all 969 times. Successful completion here
means the bounded search finished and recorded its failure; it is not a passing
animation, a global infeasibility proof or permission to replace the original.

All four selected recovery regressions also pass: abrupt process exit during
geometry, original/proposal optimizer recovery in fresh processes, and an
interrupted export retaining its orphan while retrying the same direction.
The verifier in `reports/stream-json-publication-v1` confirms all 35 earlier
GLBs, native arrays and decisions exactly match the preserved interrupted run.
It verifies every completed geometry receipt and full-clock metric reduction,
then independently reproduces the final GLB constraints, strict edit bounds,
contact report and contact arrays. All five study resource traces replay; the
verifier finishes with 47 observations and a 150,380,544-byte sampled peak.
Neither the old stopped attempt nor its pinned implementation is modified or
silently resumed with new methods.

### Full humanoid solve with separately admitted headroom (2026-10-21)

The laptop reports 15.3 GiB physical RAM and about 5.3 GiB available before this
trial. The repository-wide resource ceiling is 7 GiB, with a minimum 600 MiB
free reserve; 512 MiB was the earlier study/CLI budget. A separate solve-only
consumer therefore declares a 2 GiB estimate and maximum, a stricter 1 GiB free
reserve, 15 seconds of stable admission, a 900-second execution limit and 0.1 s
resource sampling. It requires 3 GiB available before starting. This does not
change earlier protocols, default CLI budgets or numerical acceptance limits,
and does not establish support for this full model under 512 MiB.

`reports/humanoid-axis-direction-2g-v2` consumes the identical saved model and
solver implementation from the preceding 512 MiB attempt: all 569,384 norm rows,
569,383 hard rows, 10,574,466 derivative nonzeros, 36 controls and the original
0.02 trust fraction. Saved producer hashes remain pinned separately from the
new consumer. The decoder class and input-reading/hashing functions match the
producer; only the declared orchestration and already-verified streamed writer
changes are allowed. No derivative, pair, time or control is regenerated or
silently omitted to meet the new budget.

The full solve reaches `Solved` after 31 primary iterations at a sampled
1,374,687,232-byte process-tree peak. Existing fixed/whole-box certificates omit
already-satisfied rows from solver storage; 370,502 scalar inequalities and 848
vector cones remain active. The maximum returned control movement is only
1.7801652352340958e-12. Predicted target excess stays approximately 5, and strict
full affine reevaluation still has a maximum hard excess of 3.1086244689504383e-13.
Neither the initial nor retried minimum-norm solution passes the existing
selection checks. No tolerance is enlarged to call this a successful correction.

The saved computational result is complete, but this experiment's runner exits
with an error in its final status message: duplicate approval-field keywords
after `result.json` and the direction arrays were saved. Its failed status is
preserved, along with an earlier Windows path-key setup failure in
`humanoid-axis-direction-2g-v1`. Neither is reported as a clean worker completion.
All 663 resource observations for v2 replay; the stop is not a memory guard.

### Independent verification and surface-row diagnostic

`reports/humanoid-surface-blocker-v1` verifies the saved full solve, source hashes,
solver identity and failed-run resource record independently. It recreates the
original bounds and complete native clock, exports only the full-model step as
an unaccepted diagnostic, and checks its decoded source/contact rows and edit
caps. Source rows, strict edits and contact nonregression pass, but merit does
not improve. The hand remains 30 mm from its target, failing the unchanged
5 mm requirement. No candidate geometry audit or animation-quality approval is
claimed. The complete saved affine residual array is reproduced exactly.

To isolate the local search barrier, a separate diagnostic solve removes only
the 383,994 frozen surface-guidance rows while retaining all 183,371 native rows,
one contact-protection row, 2,017 floor rows, the original target and control box.
The resulting step reaches the unchanged 0.02 trust bound and reduces predicted
target excess from approximately 5 to 4.050486. Reevaluation against the **full**
original model finds zero native/contact/floor failures but 167,080 surface-row
violations, with a maximum normalized excess of 2.307416. This ablated step is
never exported or accepted. Its predicted improvement is not actual collision
or contact success, and the failed directional bounds do not prove whole-mesh
infeasibility.

The diagnostic worker completes under 512 MiB with a 336,535,552-byte peak and
47 replayed resource observations. This evidence identifies frozen surface
guidance as a local barrier on this model. Further work should revise the
proposal model or search over alternative geometry directions while retaining
the complete decoded geometry, original permissions and final acceptance rules.
More memory alone does not resolve the demonstrated contact failure.

### Alternative direction and penalty proposals (2026-10-21)

Two research-only experiments probe the frozen-direction barrier. The
[TrajOpt initialization notes](https://rll.berkeley.edu/trajopt/doc/sphinx_build/html/tips.html)
motivate changing initialization before imposing collision costs; the
[original paper](https://rll.berkeley.edu/trajopt/ijrr/2013-IJRR-TRAJOPT.pdf)
describes increasing collision penalties. These experiments implement neither
TrajOpt nor its continuous-time collision formulation. Full decoded acceptance
remains the existing sampled-clock audit, with all original conditions retained.

First, a bounded contact-improving preview selects projection directions while
keeping the original pose as the cap and derivative anchor. All 42,666 observed
triangle/time pairs, their nine vertex comparisons, all 36 controls and all
569,384 model rows remain. The preview changes 25,046 directions. Thirty-four
prototype checks pass, including independently recomputed derivatives and
invalid-preview rejection. However, the full solve reaches its 30-second limit
after 54 iterations. A separately declared 60-second attempt reaches the
unchanged 100-iteration limit. Neither produces a direction or candidate.
Their sampled process-tree peaks are 1,376,141,312 and 1,357,516,800 bytes under
the separately admitted 2 GiB protocol. The helper and its tests are archived
in `reports/surface-preview-prototype-v1`; production source is restored.
Passing those prototype tests is not evidence of a useful full-model solve.

Second, `reports/humanoid-surface-penalty-v1` retains the original directions
and all rows, but treats the 383,994 surface-worsening rows as weighted proposal
costs. The 185,389 native/contact/floor rows stay hard. Predeclared weights are
1, 10 and 100, with the original control box, 0.02 trust fraction, 100-iteration
limit and 30-second per-solve limit. This is a weighted maximum objective,
not TrajOpt's summed hinge objective. Relaxing a proposal constraint does not
relax final whole-mesh acceptance.

Weight 1 produces a primary solution after 40 iterations; both secondary
minimum-norm solves time out. All eight exported backoffs pass decoded native
constraints, strict authoring edit limits and contact nonregression. The largest
step reduces actual point-contact error from 30 mm to 25.350371 mm, still failing
the original 5 mm requirement. The approximate primary step exceeds the nominal
local trust fraction by about 5.8e-15; strict authoring bounds pass, but exact
local-box membership is not claimed. Weights 10 and 100 reach their solve-time
limits without a direction. None of these exports is byte-identical to an older
proposal, so previous geometry audits cannot be reused. The study completes at
a sampled 1,424,543,744-byte peak. All outputs remain diagnostic and the original
animation stays selected; the complete geometry check below rejects the best
contact-improving proposal.

`reports/humanoid-penalty-geometry-v1` independently decodes the best exported
proposal and starts the unchanged 2,017-time geometry audit under 512 MiB,
with the original 600 MiB free reserve. Its 900-second execution guard stops
after 1,715 completed samples; all 902 resource observations replay and the
stop is a time limit, not insufficient RAM. The explicit continuation in
`humanoid-penalty-geometry-resume-v1` pins that checkpoint and its SHA-256,
verifies the completed prefix, and resumes the same journal under the same
resource limits. Neither incomplete evidence nor an interrupted attempt is
reported as a geometry pass.

The continuation checks the remaining 302 poses and assembles all 2,017 original
sample times in 353.235 seconds of observed execution. Original and continuation sampled peaks are 254,435,328
and 246,239,232 bytes. The final comparison is:

| Geometry metric | Original | Weight-1 full step |
| --- | ---: | ---: |
| Failed conditions | 4,282 | 4,281 |
| Failed sampled poses | 2,017 | 2,017 |
| Surface records | 42,666 | 53,064 |
| Maximum depth | 10.436307 mm | 10.436307 mm |

No previously passing condition becomes failed, but the surface-record count
worsens by 10,398. These records include the query's separate crossing,
boundary, near and coplanar classifications; the count is not a penetration
depth or a count of unique physical contacts. The unchanged requirement that
no geometry metric worsen therefore rejects the diagnostic step. A reduction
of one failed condition cannot compensate for another metric becoming worse.
The point contact also still fails 5 mm. This is a measured negative result,
not a corrected animation, and the seven smaller exported backoffs have not
received complete geometry audits.

The independent verifier in `reports/surface-proposal-publication-v1` checks
the complete frame journal, observation-index and report hashes, original
sample-clock equality, reduced conditions/metrics, source bindings, archived
prototype test inputs and every study's resource trace. Prototype failures and
the first geometry attempt's time stop remain visible. No production solver,
default resource budget or release gate is changed by these experiments.

### Stronger penalties and failure localization (2026-10-21)

`reports/humanoid-surface-penalty-60s-v1` retries only the previously timed-out
weights 10 and 100. Each solve has an explicitly declared 60-second budget;
the 100-iteration ceiling, solver tolerances, original 569,384 rows, 185,389
native/contact/floor hard rows, 36 controls and 0.02 trust fraction remain.
The original 30-second attempts are preserved. The process completes under
the same 2 GiB admission policy, with a 1,438,789,632-byte sampled peak and
2,497 replayed resource observations.

Weight 10 reaches `Solved` after 59 primary iterations; both minimum-norm
attempts time out. Its full exported step fails a decoded native constraint,
despite passing the affine native/contact/floor checks. Seven smaller backoffs
pass the native, strict edit and contact-nonregression checks. The best is the
half step, with 28.633975 mm actual hand error against the unchanged 5 mm target.
Weight 100 stops with `InsufficientProgress` after 54 iterations; more solve
time does not establish feasibility or provide a candidate for that weight.
All eight weight-10 exports are independently decoded and their saved
constraints, contacts and contact arrays reproduced in
`reports/surface-penalty-60s-verification-v1`. Geometry acceptance remains
separate; passing these checks does not make the seven candidates usable.

`reports/surface-penalty-diagnosis-v1` localizes the earlier rejected weight-1
proposal using its complete retained geometry, without rerunning or relaxing
the queries. All 42,666 original and 53,064 candidate surface records are
classified as proper crossings. Across 248 changed actor/prop sample times
from 1.697916667 to 2.183333333 seconds, 34,978 original triangle/time crossings
disappear and 45,376 new ones appear. The aggregate increase is therefore not
caused by ambiguous near-contact classifications.

Containment depth also increases in 174 time/direction measurements. The
largest increase is 3.438311 mm at 1.785416667 seconds, in the panel-to-actor
query, from an original zero. The global maximum remains 10.436307 mm because
another existing failure dominates it. This demonstrates why a whole-clip
maximum alone cannot establish local depth nonregression. The candidate was
already rejected by the existing surface-record metric; this analysis does
not retroactively change its decision or prove an accepted candidate unsafe.

The next full-clock audit, `reports/humanoid-weight10-geometry-v1`, targets the
best eligible weight-10 half step. It retains the original acceptance checks
and additionally records per-time/per-direction containment increases, with
any such increase disqualifying this research candidate. This stricter
diagnostic initially leaves production acceptance policy unchanged. The first attempt
stops at its execution-time guard after 1,836 samples; an explicitly pinned
continuation finishes the remaining 181 and assembles the complete report.
Their sampled peaks are 253,632,512 and 250,503,168 bytes under the same 512 MiB
protocol. The continuation completes in 298.656 seconds of observed execution.

The half step is rejected. Proper-crossing records increase from 42,666 to
43,615; failed conditions remain 4,282, and all 2,017 sampled poses still have
geometry failures. The whole-clip maximum remains 10.436307 mm. There are 118
local containment-depth increases, with the largest at 2.18125 seconds in the
actor-to-panel query: 2.552408 mm becomes 3.462966 mm, an increase of 0.910558 mm.
The hand still misses the original 5 mm target. This result retains the original
animation and proves neither feasibility nor infeasibility of a different
correction. Complete frame/source bindings, metrics and local increases are
checked by `reports/weight10-geometry-verification-v1` before changing the
production implementation.

### Local depth acceptance for character corrections

The character fitter and resumable optimizer now require a supplementary
per-time/query depth comparison in `native_mesh_depth_regression.py`. The
existing condition and aggregate-metric requirements remain mandatory. A
contact improvement cannot buy an increase in a smaller local penetration
hidden by another query's larger maximum.

The comparison includes actor and prop floor-plane depths, actor and prop
primitive-query upper depth bounds, and both containment directions for actor
partners, actor/prop pairs and prop/prop pairs. Complete clocks, limits,
participant topology counts and query identities must agree. It introduces
no depth slack; unavailable comparisons fail rather than asserting that an
unknown depth did not worsen. This is deliberately conservative, including
for tiny floating-point changes. Primitive bounds are compared as measured
bounds, not presented as exact physical penetration distances.

Every evaluated proposal saves `local-depth-regression.json`. Decision records
include the local pass flag, regression/unavailable counts and maximum increase.
The resumable optimizer writes the same report immutably and pins its hash
before committing the decision. The new helper belongs to the implementation
snapshot, so an old interrupted optimizer cannot silently resume under changed
acceptance code. Its original implementation and evidence remain preserved.

Validation covers 61 distinct targeted cases. The first run has 60 passes and
one new test-harness failure: the recovery helper was called without its
checkpoint hash argument. That failure and the original test are retained.
After correcting only that call, all 31 cases in the new test module pass;
production implementation hashes remain identical across both runs. Coverage
includes regressions hidden by a larger peak in each of the seven query
families, unknown/malformed/incomplete reports, rejection in both correction
paths, matching fresh/resumed results, stage-publication interruptions,
modified saved records, fresh-process hard exits and interrupted exports.
The new module is included in the source-test inventories and focused workflow;
these local results do not claim completion of the full cross-platform suite.

`reports/local-depth-guard-replay-v1` independently verifies that evidence and
applies the new consumer to both retained humanoid reports without rebasing
their producers. It checks 8,068 local observations per case, reproducing all
174 weight-1 and 118 weight-10 containment increases exactly, including their
original/candidate values. Comparing the original report with itself passes.
Both corrected candidates still fail; no earlier decision is retroactively
promoted and no new animation is selected.

This guard improves acceptance evidence; it does not generate better motion,
resolve the retained hand-contact failures, or certify whole-mesh, self-collision,
continuous-time, dynamics, game-engine or human-quality requirements.

### Separating temporal and spatial failures on the retained humanoid

`reports/humanoid-rate-blocker-v1` attributes the saved weight-10 full and half
steps without changing their clips, source caps or decisions. It freshly
decodes both exports and independently reconstructs all 183,371 native residual
rows exactly. The full step has one failed row: angular acceleration of
RightHandThumbEnd over 1.991667, 2.0 and 2.008333 seconds. Its measured value is
124.633565469 rad/s² against the original bin cap of 124.623880090 rad/s² and
the unchanged 0.00001 tolerance. Excess is 0.009675379 rad/s². No zero-cap row
causes this rejection. The half step passes every native row but retains its
previously measured geometry failures. This evidence does not justify loosening
the temporal caps to address collision failures.

The diagnostic explicitly records the two changed producer modules introduced
by the local-depth guard. It verifies the decoder problem class against the
archived original class and retains the other original implementation bindings;
it does not rebase an old producer onto new acceptance code. All 78 resource
observations replay, with a sampled peak of 188,645,376 bytes and 61.843 seconds
of execution under the existing 512 MiB protocol.

`reports/humanoid-pose-seed-v1` then isolates the spatial problem at the existing
2-second contact. Twelve components on the four original tracks' middle knot
are optimized using SLSQP, with at most 160 iterations and ftol 1e-12. The
20-degree rotation and 0.15-m displacement bounds remain. A point-only objective
is compared with point error plus a squared opposed-winding-normal term weighted
by (0.02 m)²; both include a 1e-10 control regularizer. These are pose proposals,
not a replacement for full motion acceptance. Each is exported through the
existing native edit path, freshly decoded on the complete clock, and checked
against every original temporal cap. Geometry checks at the original contact
sample retain all imported triangles and both containment directions; they do
not claim full-clip coverage.

The original contact point lies 30 mm along the selected panel face's winding
normal, and the incident palm winding normal already opposes it (dot product
−1). The panel passes the existing closed, consistently wound, positive-volume
screen; self-intersection and contact suitability are not certified. The point
trial converges in 16 iterations to 0.000361 mm error, while the orientation
trial converges in 41 iterations to 0.000092 mm error. Both preserve strict edit
bounds but fail 102 and 271 native rows respectively. At the contact sample,
surface records rise from 103 to 470 and 457, and the original 9.781777-mm
maximum measured depth rises to 9.974399 and 9.984755 mm. Both proposals are
rejected. Accurate point placement and palm orientation alone do not solve
this interaction. All 84 resource observations replay; neither trial changes
the original selected animation or any quality/release gate.

`reports/humanoid-pose-depth-seed-v1` adds an interior-depth objective for this
specific convex panel. Every imported face plane is retained, and every panel
vertex is checked against every outward face halfspace. For actor vertices
inside this closed convex surface, the minimum face-plane distance supplies
the proposal depth. This is derived from the actual panel triangles, not an
inserted box or hull proxy. Every actor vertex contributes to the squared depth
sum, weighted by 10 alongside squared contact error. This one-direction proposal
objective does not replace triangle crossings or reverse containment checks.

Starting from the original controls and from the point-only seed converges in
126 and 93 iterations. Both reduce contact-time surface records from 103 to 46
and maximum measured depth from 9.781777 to 8.591902 mm. However, their contact
errors are 10.643164 and 10.645598 mm, outside the unchanged 5-mm limit; they
fail 1,503 and 1,509 native rows. Neither passes the strict continuous proposal
constraint comparison, and the second also fails the final strict edit-cap
comparison. Solver success is not treated as satisfaction of these checks.
Both remain rejected; the original remains selected. This weighted tradeoff
motivates a hard contact constraint in the next pose proposal, followed by
unchanged native/geometry evaluation rather than adopting the weighted result.

`reports/humanoid-pose-seed-verification-v1` independently replays all three
studies' resource traces, verifies retained input/implementation hashes,
recomputes native failure counts from saved complete-clock arrays, and checks
contact errors, edit decisions and single-time geometry reductions. It does
not repeat the optimizations or claim full-clip geometry coverage.

`reports/humanoid-pose-hard-contact-v1` makes the proposal's contact radius a
hard 4.9-mm constraint while minimizing the squared interior-depth sum. Actual
contact acceptance remains 5 mm. A 1e-6 normalized reserve tightens the proposal
rotation bound; it does not loosen the original 20-degree edit limit. The two
initializations are the previous depth-guided and point-only seeds. The original
four tracks, middle knot, displacement bound and temporal caps remain unchanged.

Both solves report success, after 110 and 128 iterations. Fresh exports have
4.899991-mm point error and pass strict edit bounds. However, neither passes
the strict continuous proposal constraint comparison, and their native failure
counts are 1,498 and 1,510. Contact-time surface records increase from 103 to
240 and 151. Although maximum measured depth decreases to 8.591902 and
9.600001 mm, this does not outweigh the crossing failures. Neither candidate
is accepted, and neither receives a full-clip geometry evaluation. The second
also fails the existing full residual merit-improvement test despite improved
point error. These results isolate a spatial collision problem as well as the
temporal fitting problem; reaching a point within tolerance does not solve
the interaction.

The independent hard-contact verifier checks saved arrays, decisions and source
bindings, replays the resource trace, and recomputes all 18,056 actor vertices'
interior depths against the original panel face planes at 2 seconds. The maximum
depths match the complete triangle-based containment measurements within 1e-12 m,
and counts over 5 mm match exactly. Dominant skin weights attribute the original
71 over-limit vertices to RightHandPinky3/4. The depth-seeded hard-contact result
has 16: nine on RightHandThumb1, six on RightHand and one on RightHandPinky1.
The point-seeded result has 35, concentrated on the pinky base, ring base and
palm. These are region attributions, not proof that a particular joint edit
will resolve the collision.

This motivates a separate, explicitly declared seven-track experiment adding
RightHandThumb1, RightHandRing1 and RightHandPinky1 rotation controls, each bounded
by 20 degrees. It retains the source clip, original four arm tracks, edit window,
knot clock, displacement bound, source temporal caps, target and geometry policy.
The original four-track permissions and all their failed outputs stay intact.
This tests the role of finger articulation; it is not a claim that the original
fixed-finger task was solved or that the added angular budgets are anatomical
calibration.

The seven-track experiment, `reports/humanoid-finger-contact-v1`, preserves both
starting-point outcomes. Starting from the original stops at the 160-iteration
limit: contact error is 4.900006 mm, strict edit bounds fail, 1,213 native rows
fail and surface records increase to 150. Starting from the prior hard-contact
arm seed converges in 58 iterations. It passes the continuous proposal and
strict serialized edit bounds, reaches 4.899999 mm, and reduces surface records
to eight, all classified as boundary-or-near-contact rather than proper
crossings. Actor-to-panel vertex depth is 8.425e-9 m with no vertices over 5 mm;
reverse containment is zero. The unchanged geometry policy still rejects the
eight surface records. The complete exported motion fails 1,060 native rows.
This is an improved spatial seed, not an accepted animation or a solution to
the original four-track task.

`reports/humanoid-finger-contact-verification-v1` independently confirms that
only the three declared tracks were added, reconstructs the native row count
for the larger permission set, and checks saved complete-clock residuals,
contact observations, edit bounds, single-time triangle metrics and resource
traces. A follow-up uses the successful seed with a declared 0.1-mm outward
face-plane margin in its proposal penalty; actual geometry retains the original
triangles and tolerances. This aims to avoid the numerical boundary contacts
before attempting temporal fitting.

`reports/humanoid-finger-clearance-v1` completes that follow-up in 33 SLSQP
iterations. Its 0.1-mm margin only changes the proposal objective; the original
geometry policy is evaluated unchanged. The freshly exported pose passes the
continuous proposal and strict edit bounds, reaches 4.899997 mm point error,
and has zero panel surface records at 2 seconds. The scene's maximum measured
depth is still 8.591902 mm because the existing floor failure remains; two
conditions still fail at that sample. The complete clip fails 1,047 native rows,
so this is retained solely as a spatial seed for temporal fitting. No full-clip
geometry, continuous collision, motion-quality or release approval follows.
The clearance verifier confirms unchanged seven-track permissions, source and
implementation bindings, complete-clock residual counts, contact observations,
strict edit decisions, single-time geometry metrics and resource replay.

### Timing the retained finger contact pose

`reports/humanoid-finger-timing-v1` keeps the seven-track permission set and
middle-knot controls unchanged, varying only the two existing side knots. All
five profiles decode to exactly the same world matrices at 2 seconds. The study
freshly reconstructs every one of the 183,512 native residual rows, including
all original speed/acceleration caps; no failed row has a zero source cap.
All profiles pass strict edit bounds, but none passes all native conditions.

| Side/middle/side multipliers | Failed native rows | Worst normalized native excess |
| --- | ---: | ---: |
| Retained: 0, 1, 0 | 1,047 | 2.963387 |
| Broad triangle: 0.5, 1, 0.5 | 639 | 1.423411 |
| Plateau: 1, 1, 1 | 151 | 1.423280 |
| Early: 1, 1, 0.5 | 636 | 0.690336 |
| Late: 0.5, 1, 1 | 153 | 1.423280 |

Failure count alone would choose the plateau even though its worst overrun is
larger. The next proposal starts from the early profile, selected by minimum
worst normalized residual, with failure count as a tie-breaker. The temporal
search keeps all 21 middle-knot components fixed and adjusts the 42 side-knot
components. Its 183,513 norm rows retain all native constraints and the point
contact. The 37,058 edit/displacement rows are hard in the affine solve; the
146,454 source-rate residuals guide a minimax research step. Actual decoded
rate caps remain unchanged and mandatory. A partially improved research iterate
is never treated as an accepted animation.

The two recorded steps use a 0.1 normalized trust box, 0.001 central-difference
stencils where both sides fit the control box, and recorded one-sided stencils
otherwise. The contact derivative with respect to all free columns is exactly
zero. Each step saves its complete affine rows and sparse derivative, solves
with the existing 30-second/100-iteration settings, and exports four step sizes.
Every export is freshly decoded on all 2,017 times, its strict edit bounds are
checked, and its contact-time world matrices must exactly equal the seed's.

`reports/humanoid-finger-temporal-direction-v1` converges in 29 solver iterations;
the best full step has 426 native failures, with residual merit changing from
(0.690335928, 7.838403026) to (0.104154324, 0.910499895). Merit is the maximum
positive normalized residual followed by the sum of squared positive residuals.
The second step, `reports/humanoid-finger-temporal-direction-v2`, converges in
26 iterations and reduces this to 173 failures and (0.099466045, 0.419727286).
Both preserve the exact contact pose and pass hard edit/displacement and strict
serialized edit checks. Neither is eligible for full geometry evaluation.

The timing comparison uses the existing 512 MiB protocol. The affine fitting
steps explicitly use a 2 GiB process-tree budget with a 1 GiB available-memory
reserve and 0.1-second resource polling. Their observed memory use does not
establish support under the smaller protocol. Source-rate caps, edit bounds,
clock coverage and the geometry policy are unchanged throughout.

`reports/humanoid-finger-temporal-verification-v1` independently decodes all
13 retained profile/probe exports, reconstructs the saved affine origins, cap
arrays and steps, verifies edit/contact observations and replays resource
traces. Its physical-row diagnosis locates the largest remaining positional
speed excess on RightArm over 2.125–2.133333 seconds: 0.206788731 m/s against
the source cap of 0.188071958 m/s plus the unchanged 1e-5 tolerance. Other
near-active failures include shoulder angular speed immediately after contact
and arm/finger acceleration at the 2.8-second exit. This is evidence about
this local search, not global infeasibility.

`reports/humanoid-finger-timing-refinement-v1` declares an additional control
knot at 2.2 seconds, increasing the control representation from 63 to 84
components while holding the 21 contact components fixed. The original
seven-track permissions are preserved separately. Only the control basis is
refined: source animation key times, editable window, protected spans,
rotation/displacement limits, target, source-rate cap arrays and geometry policy
remain unchanged. Interpolating the previous controls into the new basis
preserves every stored native key and produces a byte-identical seed GLB.
Residual bookkeeping is not claimed byte-identical: edit-control arithmetic
can differ, while the native motion itself remains identical.

The first 63-free-component step converges in 25 solver iterations. Its best
export retains the contact pose, passes hard and strict edit checks, and has
124 native failures with merit (0.065940496, 0.158173057). The actual improvement
is 98.903643% of the affine prediction. A separately recorded continuation,
`reports/humanoid-finger-timing-refinement-v2`, therefore doubles the proposal
trust box from 0.1 to 0.2; authored cumulative limits remain unchanged. Its best
export has 116 failures and merit (0.064892500, 0.157293684). Neither step is an
accepted animation or eligible for full-clip geometry evaluation.

The diminishing improvement motivates joint pose-and-timing restoration under
the actual contact and collision requirements. Exact preservation of the chosen
spatial seed was an experimental restriction, not a requirement to freeze that
particular arm/finger pose forever. Any joint search must still retain the
declared source-rate and edit limits, test the supplied rig and actual prop
triangles, and undergo complete-clock geometry and the remaining release checks.

`reports/humanoid-finger-refinement-verification-v1` independently decodes all
eight refined-step exports, reconstructs their affine origins and steps, and
confirms that original native cap/scale arrays are unchanged. The basis-transfer
seed GLB is byte-identical to its predecessor; every non-edit residual is also
identical. The best remaining failures comprise 25 positional-speed, four
positional-acceleration, 77 angular-speed and ten angular-acceleration rows,
with no zero-cap failures. This verifier and the preceding 13-export verifier
retain their source bindings and resource replays.

Before a joint search, `reports/humanoid-contact-pose-halfspaces-v1` checks all
36,108 original actor triangles against all 12 original convex panel face
planes at the retained contact pose. Every actor triangle has a panel face
plane placing all three vertices outside with at least the declared 0.05-mm
proposal clearance; the smallest measured gap is 0.099998402 mm. Thus 108,324
scalar vertex/plane rows can guard this pose proposal without dropping actor
triangles. This establishes a feasible starting assignment for the next local
model, not a fitted animation, whole-scene certificate or continuous collision
guarantee. Actual triangle/containment checks remain authoritative.

### Joint contact pose and timing

`reports/humanoid-joint-contact-timing-v1` releases the experimental lock on
the 21 middle-knot components. All 84 components of the declared seven-track,
six-knot variant can move within the original cumulative edit bounds. Source
animation keys, protected spans, motion caps, contact target and geometry
policy remain unchanged. The original four-track baseline is still separate.

Every original actor triangle contributes three vertex/plane constraints at
the contact time, using the previously verified assignment to actual convex
panel faces. The 108,324 scalar gaps are lifted into exact affine norm rows
within the declared trust box, with 0.05-mm proposal clearance. The combined
model contains 291,837 norm rows: 37,058 edit/displacement rows, one contact
row and 108,324 triangle guards form the hard prefix; all 146,454 source-rate
rows remain in the minimax objective. The actual exported clip must pass the
unchanged source-rate limits. No small derivatives or original triangle rows
are dropped. All 63 side-column contact/geometry derivatives are verified
exactly zero; the 21 middle components can change the pose.

Each step exports four fractions and independently decodes all 2,017 native
times. Research progress requires strict serialized edit bounds, hard native
edit/displacement and actual contact limits, plus a fresh full-scene geometry
query at 2 seconds. That single-time query includes original triangles,
bidirectional containment and floor checks. Previously passing conditions
must remain passing, the actor/panel pair must pass, and no measured local
depth may increase relative to the retained contact pose. These are explicitly
partial geometry reports, never presented as complete-clock certificates.

| Study | Proposal trust | Selected fraction | Native failures | Worst normalized excess | Hand error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Joint v1 | 0.1 | 0.5 | 69 | 0.032164314 | 4.982072 mm |
| Joint v2 | 0.05 | 1 | 4 | 0.001152387 | 4.945804 mm |
| Joint v3 | 0.025 | 1 | 0 | 0 | 4.835319 mm |

The first step's full fraction reaches 21 native failures but misses the
contact limit at 5.186218 mm and is rejected. The next two steps halve the
trust box and use a stricter 4.9-mm proposal contact radius to leave room for
nonlinearity and serialization; the authored acceptance radius remains 5 mm.
All three solves retain the existing solver time and iteration limits and
the explicit 2-GiB process-tree budget with a 1-GiB available-memory reserve.
The third step's full, half and quarter fractions pass every native row and
the contact-time geometry requirements. The one-eighth fraction still fails
three native rows. All outputs and rejected decisions are retained.

`reports/humanoid-joint-contact-verification-v1` freshly decodes all 12 exports
and recomputes their native/edit/contact decisions, contact observations and
single-time full-scene geometry, including saved observation arrays. It
reconstructs original cap arrays, actual panel planes, affine origins, scalar
gap lifting and the saved solver-step residuals. Saved derivatives are bound
by provenance and structurally checked; they are not independently
re-differentiated. The selected full-step candidate is eligible for complete
geometry evaluation, not animation adoption or quality approval. The original
floor failure of 8.591902 mm remains at the contact time.

### Remaining integration and evaluation

Keep the exact original source, editing limits, frozen tracks and complete
acceptance clock. Add collision guidance to the character proposal rather than
changing the target panel, relaxing failure counts or admitting a closer hand
with worse geometry. Construct guidance from identified source mesh features
and explicit actor/prop identities; preserve unavailable or ambiguous signed
distance outcomes as unresolved. A selected witness or local affine distance
must never replace full triangle checks.

Rebuild guidance after an accepted decoded step. Preserve previously passing
conditions and retain existing failed-condition measurements. Measure whether
the guidance can reduce failed contacts without worsening geometry; retain
no-direction and no-improvement results. If guidance cannot fit its resource
budget, report the unsupported population instead of silently dropping rows.

Compare unchanged proposals, deterministic guidance and full decoded acceptance
on moving props, multiple obstacles, thin surfaces, rotated placements, partner
contacts and different rigs/actions. Include failures away from the requested
touch time, as demonstrated here. Both the arm-only and finger-enabled diagnostics retain
ground failures; correcting support is a separate required part of producing
a usable clip, not something this hand-contact experiment establishes.

Frame and optimizer journals are implemented and independently tested; see
`native-mesh-geometry-recovery-v1.md`. This new guidance still needs its witness
banks integrated into that optimizer protocol before larger resumable fits.
The export diagnostic and combined experiment above resolve the demonstrated
source-rounding barrier on one generated case. Both obstacle placements and the
real humanoid now expose additional local-search limits. Joint pose and timing
now pass the native limits on one declared seven-track candidate. Next evaluate
its complete geometry clock against the original source, then extend guidance
to any newly demonstrated failures. Preserve the separate four-track
baseline and all failed trials. Complete-clock geometry, support and every
other acceptance requirement remain mandatory. Then integrate validated proposal state with recovery and
continue different rigs/actions, partner, engine and human-review evaluation.
These are steps toward the existing complete animation-authoring goal; neither
proposal improvement nor resumable evaluation satisfies its release gates.
