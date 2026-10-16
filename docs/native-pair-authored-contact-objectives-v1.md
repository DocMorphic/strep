# Fit authored contacts with edit support at the target time

The [previous coverage audit](native-pair-material-recourse-v1.md) finds that
approach keys 30–48 cannot affect the authored 2-s meeting. The two world-target
position errors already satisfy their 30-mm limits, while the saved
hand-to-hand distance is 33.282370 mm. Contact fitting therefore needs explicit
temporal support and an objective at that target, rather than another earlier
surface-guide retry.

`PairKeyGuides(models, [], fit_contacts=True)` enables contact-only fitting.
The flag is a strict boolean, defaults to false and requires actual authored
contacts. It can also accompany explicitly supplied regional or surface guides.
Missing contacts reject; the mode does not invent a passing contact population.

The original native motion, protected contact and complete-clock floor rows
stay in the hard prefix. The mode appends a separate soft copy of the authored
contact norm rows, with their actual authored caps/scales and the same complete
two-actor Jacobian. A failed source contact can remain protected against
worsening while still being an objective to improve. Its protected cap never
replaces the authored acceptance limit. Contact positions and any authored
relative-rate norms retain their original meanings.

Contact-only mode produces zero regional-guide gaps, preserving complete floor
rows. Default regional/surface behavior retains the same numerical row and
Jacobian prefix. Reports separately count `contact_objective_rows`; an empty
guide list is allowed only with explicit contact fitting or existing surface
witnesses. Extra objectives do not establish physical feasibility, semantics,
continuous contact, collision clearance or human-rated quality.

## Source validation

The final selection passes **89 checks in 95.63 s**, covering the eight new
contact-objective cases and existing paired-key, surface, material-distance and
decoded-recourse behavior. Cases include a separated partner with a failed
source contact, explicit contact-only opt-in, exact unchanged default prefixes,
separate hard protective and soft authored caps, both actors contributing to
the contact Jacobian, complete floor populations, actual two-character exports
and missing/ambiguous objective declarations rejecting.

The 512 MiB CPU guard completes in **112.422 s**, peak sampled tree RSS
**149,925,888 bytes**, with all **112** resource observations replayed and the
additional 600 MiB free floor. Local results remain under ignored
`reports/native-pair-contact-objective-tests-v2`. The initial failed selection
is retained under `-v1`: it demands bitwise preview/export rate-vector identity
and observes a maximum 5.127e-12 difference. The corrected assertion uses the
existing native preview/export agreement budget (1e-9 for rate vectors, 1e-12
for contact vectors), while actual decoded acceptance still uses unchanged
original caps with no added tolerance.

Inventories contain **524 Python modules / 45 Node suites**; contact/rig contains
**88 Python modules / five Node suites**. These are inventory counts, not a
full-inventory or release pass.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38735559549)
at `dc1f73c` passes all **eight new cases per OS**: Ubuntu **4.44 s**, Windows
**31.52 s**. This is distinct from the 89-case local affected selection.

## Contact-time trial

The separate `reports/high-five-authored-contact-v1` trial uses original assets
and zero-key source bounds, with keys **50–70** editable for both right-arm
chains. This creates **504 controls** and open temporal support of approximately
**(1.633, 2.367) s**, covering all three 2-s contact requirements.
The 50-mm displacement limit, original rotation/rate limits, original endpoint
and root rules, and original floor/contact protection remain intact.

This trial recomputes its matrix; the old 456-column approach matrix is not
reused. All authored contact rows are soft objectives in addition to their
existing hard protective rows. Its fresh original-native geometry baseline
queries complete character surfaces at five native times, keys 58–62 around
the meeting. Imported-engine counts and the earlier approach pose are not
substituted for that baseline.

Each baseline/candidate geometry query starts from declared Trimesh generator
seed 137 and records its before/after state. This does not certify ambiguous
containment outcomes or whole-clock geometry. Candidate exports still need
unchanged native-motion/contact/floor protection and no regressions in the
declared complete-mesh comparison. A qualifying result would remain an internal
candidate, with the original source retained and full geometry, physical,
engine, semantic, held-out and human cleanup evidence still required.

## Fresh native baseline geometry

The baseline now measures the complete native meshes at the five declared
times. All five samples fail the existing physical screen before any new fit.
At exactly 2 s, the point-contact gap is still 33.282370 mm, yet the meshes
already have **594 crossing records**, with directional peak penetrations
**11.205837 mm** (A inside B) and **13.483237 mm** (B inside A). Original floor
depths are **8.591902 mm** and **6.466365 mm**. Meeting the authored point
distance therefore cannot establish actual surface contact or collision quality.

| Native time (s) | Crossing records | A inside B peak (mm) | B inside A peak (mm) |
| --- | ---: | ---: | ---: |
| 1.933333278 | 640 | 16.834276 | 10.842976 |
| 1.966666698 | 567 | 13.713630 | 12.986183 |
| 2.000000000 | 594 | 11.205837 | 13.483237 |
| 2.033333302 | 644 | 7.778888 | 16.701882 |
| 2.066666603 | 455 | 8.421581 | 20.590680 |

These are the original source's fresh native measurements, not a candidate
improvement, a whole-clock partner audit or a continuous collision certificate.
The retained failure baseline remains the no-regression comparator; physical
acceptance still requires its own passing evidence.

## Fitted model and completed candidate checks

The fresh matrix takes **365.234 s** and contains **623,702** norm rows with
**2,878,957** nonzeros. Its hard prefix retains **619,662** original native
motion rows, three protected-contact rows and **4,034** floor-protection rows.
The final three soft rows use authored 30-mm contact caps. Each actor supplies
**72** nonzeros to those objectives. The original failed hand contact's hard
protective cap is 33.282370 mm; it does not replace the 30-mm authored target.

The primary fit reports **Solved in 12 iterations** and zero affine contact
excess. The optional minimum-norm result is `AlmostSolved` without satisfying
its affine checks and is rejected; its retry reports `NumericalError`. Only
the primary direction is used for actual export checks.

The full exported step passes every original native motion row and all three
authored contact position rows. Its world-target distances are **15.908061 mm**
and **15.991548 mm**; the hand-to-hand distance is **29.363431 mm**. Original
floor/contact protection also passes. However, **14** selected mesh measures
regress, so the candidate is rejected. At 2 s, crossing records increase
**594 to 669** and B-inside-A peak depth increases **13.483237 to 15.165955 mm**.
No source clip is replaced.

The half step also preserves every native-motion row and the original
floor/contact protection. Its hand gap is **30.794602 mm**, still outside the
30-mm authored limit, and some mesh measures regress. It is rejected as well.
Neither a solved affine fit nor a passing point target establishes a usable
interaction.

## Preserved resource stop and remaining checks

After two complete candidate checks, free RAM falls to **584,622,080 bytes**,
below the unchanged 600 MiB floor. The original guard stops the worker during
the quarter-step check. The two complete comparisons, saved matrix/direction
and incomplete third export remain untouched. The failed run records
**1,466.484 s**, peak sampled tree RSS **766,238,720 bytes**, with all **1,429**
resource observations replayed. This is a resource stop, not a completed
four-candidate study.

The remaining quarter/eighth checks use a separate saved-fit continuation,
without loading/rebuilding the matrix or solving again. It must bind every
recorded original method/input, reconstruct the complete original starting
arrays exactly, and retain the byte-identical native geometry baseline. All
original limits, comparison measures and the 1 GiB CPU / 600 MiB free resource
profile stay unchanged. Completed full/half results are not rerun.

The first continuation attempt is interrupted before any candidate result is
saved. Its guard record remains unfinished; later absence of both recorded
processes and the missing execution handle are recorded separately, without
inventing a clean terminal resource audit. A fresh attempt under
`reports/high-five-authored-contact-resume-v2` uses identical worker/launcher
bytes. The interrupted attempt and its partial files remain preserved.

## Completed four-fraction outcome

The second continuation completes the quarter step before another RAM stop.
The [staged validation](native-contact-staged-validation-v1.md) then finishes
the exact eighth-step exports, including all original motion/floor times and
the same coupled contact and five-time native geometry checks.

| Fraction | Native failures | Hand gap (mm) | All authored contacts pass | Regressed mesh measures |
| --- | ---: | ---: | --- | ---: |
| 1 | 0 | 29.363431 | Yes | 14 |
| 0.5 | 0 | 30.794602 | No | 12 |
| 0.25 | 0 | 31.920551 | No | 11 |
| 0.125 | 0 | 32.573864 | No | 15 |

All four preserve the original floor/contact conditions, but every mesh
comparison regresses and **none qualifies**. The original clips remain
selected. The saved-report assembly accounts for all four declared fractions
without inventing completion of either interrupted guard or rerunning the
already finished comparisons.

The remaining full-task problem is joint contact and geometry correction:
enforcing authored contact targets while also proposing surface-aware changes,
with every original motion bound and independent mesh screen retained. A
passing point-distance objective alone is insufficient. Floor/grounding,
whole-clock geometry, engine/semantic/human review and the broader action,
rig, object, editing/style and held-out requirements still need evidence.
