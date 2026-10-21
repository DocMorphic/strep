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
touch time, as demonstrated here. The current arm-only diagnostic still has
ground failures; correcting support is a separate required part of producing
a usable clip, not something this hand-contact experiment establishes.

Frame and optimizer journals are implemented and independently tested; see
`native-mesh-geometry-recovery-v1.md`. This new guidance still needs its witness
banks integrated into that optimizer protocol before larger resumable fits.
The export diagnostic and combined experiment above resolve the demonstrated
source-rounding barrier on one generated case. Next test the other obstacle
placement and real humanoid, preserving every original source/edit/contact and
geometry limit, then integrate validated proposal state with recovery and
continue different rigs/actions, partner, engine and human-review evaluation.
These are steps toward the existing complete animation-authoring goal; neither
proposal improvement nor resumable evaluation satisfies its release gates.
