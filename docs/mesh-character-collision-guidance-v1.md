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
