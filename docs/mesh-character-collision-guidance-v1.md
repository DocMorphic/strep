# Collision guidance for character corrections

Research and implementation direction, 2026-10-21. No new collision-guided
character solver has been implemented or validated by this document.

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

## Proposed character integration

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

Before larger trials, finish validating the frame journal and save optimizer
state so repeated execution limits do not discard expensive completed audits.
These are steps toward the existing complete animation-authoring goal; neither
proposal improvement nor resumable evaluation satisfies its release gates.
