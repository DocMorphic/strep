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
Complete-clock auditing and fitting above retain the failures. Next compare the
remaining acceleration failures before and after serialization, then validate
any correction under unchanged limits and test different rigs and actions.
These are steps toward the existing complete animation-authoring goal; neither
proposal improvement nor resumable evaluation satisfies its release gates.
