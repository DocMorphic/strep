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
