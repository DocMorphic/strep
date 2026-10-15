# Local surface guidance for jointly edited native clips

The [previous joint temporal trial](native-pair-key-guides-v1.md) finds a decoded
motion that respects its original motion limits, but region-plane improvement
does not establish improved pair geometry. A matched saved comparison even has
one increased penetration-depth measure. This extension connects actual local
triangle and barycentric surface witnesses to that same original-bound native
model. It is a proposal mechanism for arbitrary declared actions, not an
action-name whitelist or geometry approval.

`native_partner_surface_rows.build` keeps its complete-clock, original-pose
default. Optional `sample_indices` explicitly select sorted, unique original
clock indices for guidance. Each selected time still queries the complete
original triangle populations and referenced-vertex containment where volume
topology permits it; unavailable containment remains explicit. The report
records the original clock size, selected indices and whether time coverage is
complete. Partial guidance never changes the original acceptance clock.
Booleans, duplicates, unsorted or out-of-range indices reject.

An optional `actor_vertices` callback supplies complete finite world-space
vertices in canonical source order, allowing witnesses to follow a separately
decoded proposal while the motion limits stay anchored to the original files.
It does not move the source scene or replace its animation. The supplied domain
is explicit in the report. `include_world_planes=False` excludes only plane
guidance; complete original floor protection and final geometry acceptance
remain separate. The default still includes planes.

`PairKeyGuides(..., surface_rows=rows)` requires the exact original interval
scene instance, validates every actor, time, unit normal, finite constant,
canonical vertex and convex weight population, and copies the witnesses.
Triangle-pair, inside-vertex, primitive-triangle, primitive-enclosure and declared
world-plane row types are supported. Empty regional guides are allowed when
local witnesses exist. Every local gap uses both edited actors through their
actual source skins; fixed normals and barycentric coordinates are local guides
and must be rebuilt as motion changes. A passing guide is never a full-mesh or
continuous collision certificate.

Scenes with no authored contacts now retain **zero contact rows** and return
`None` for that optional norm population. They receive no invented passing
contact condition. All original rotation, displacement and motion-rate rows
remain hard. Complete floor and any authored contact conditions retain their
separate protection and unchanged acceptance rules.

## Validation

The final affected selection passes **60 checks in 26.32 s**, including **26 new
cases**, the previous paired-key model and existing partner/mixed-cone helpers.
Cases cover:

- Local material gaps respond to both edited characters, retain the complete
  hard original native/floor prefix and copy caller-owned witnesses.
- Contact-free scenes keep zero authored contact rows without fabricated evidence.
- Every triangle remains present at selected times, while partial time scope is
  explicit; supplied poses can move an actor without mutating its source scene.
- Invalid or foreign surface contexts, times, actors, weights, vertices, normals,
  constants and proposal-clock indices reject, including mixed boolean tuples.
- Default and last-frame clock labels cannot alias canonical vertex indices.

The final 512 MiB CPU guard completes in **42.656 s**, peak sampled tree RSS
**145,567,744 bytes**, with all **44** resource observations replayed and the
additional 600 MiB free floor. Records remain under ignored
`reports/native-pair-surface-guidance-tests-v3`. Initial 57-case and 24-case
checks remain preserved under `-v1` and `-v2`; they had not covered the clock-label
alias found by the real study. The two added regression cases fail against the
preserved pre-fix source in **3.16 s**. Their failed guard completes in
**20.282 s**, peak **128,851,968 bytes**, with all **22** observations replayed,
under `reports/native-pair-local-surface-clock-regression-20261015-v1`.
Inventories now contain **521 Python test modules / 45 Node suites**;
contact/rig contains **85 Python modules / five Node suites**. This is not a
full-inventory or release pass.

A separate default-caller selection passes **54 checks in 14.74 s** across the
existing surface/recentered models, primitive-object rows and pair-surface
model. Together with the 60-case selection this is **114 distinct affected
checks across two current-code runs**, not one 114-pass invocation. Its 512 MiB
guard completes in **31.438 s**, peak sampled tree RSS **136,560,640 bytes**, with
all **33** resource observations replayed. Local results remain under
`reports/native-pair-local-surface-legacy-checks-20261015-v1`.

## Actual temporal study

The source-native trial under ignored `reports/high-five-local-surface-temporal-v1`
starts from the independently verified earlier half-step while keeping both
interval seeds at the **original zero-control source epoch**. Existing native
keys 30–48 remain editable for both actors, with all original motion caps and
the full floor/contact protection. Five declared guide times retain both
18,056-vertex, 36,108-triangle source surfaces. The builder produces **10,371
local rows**; this is not a complete geometry-clock audit.

The trial snapshots Trimesh 5.1.0's shared default generator state, initializes
it with seed 137 and saves its state after witness and geometry queries. This
does not retroactively seed earlier saved geometry measurements or establish
independent cold numerical replay; those stronger checks remain separate.

The earlier candidate's saved five-time geometry serves as the comparison
baseline only after binding its input files and unchanged registered geometry
methods. Original source-floor/meeting failures remain failures. New serialized
probes must pass every original native bound, preserve floor/contact conditions,
improve the local objective and avoid regression in all compared saved per-time
surface counts, inside-depth/count measures and plane depths before an internal
proposal can advance. Meaningful improvement is also required. Original clip
adoption, complete geometry, engine and human approval remain separate.

The actual run completes under a **1 GiB CPU guard plus 600 MiB free floor**.
The sparse-entry budget remains
6,000,000; the execution guard is explicitly 1,800 seconds for witness building,
one joint step and up to four decoded/geometry probes. Neither change relaxes
any motion, contact or collision criterion. Its matrix has **2,832,274 nonzero
entries** and **634,070 norm rows**, including the same **623,699-row hard
original-motion/contact/floor prefix**. The primary conic phase reports `Solved`
after **34 iterations**. The optional minimum-control-norm phase is not selected:
its `AlmostSolved` candidate exceeds the permitted affine objective bound, and
its retry reports `NumericalError`. The primary direction is retained. No new
engine or model is run.

All four decoded probes, at fractions **1, 0.5, 0.25 and 0.125**, pass every
original native motion row and retain complete floor/contact protection. Each
improves the worst local-witness deficit, but **each regresses some independently
measured geometry conditions at the selected times**, so **none advances**.
The original remains selected. For example, the full step changes A-inside-B
maximum depth at 1.2333333492279053 s from **15.673294 to 18.780123 mm**, even
though the worst local guide deficit decreases from **33.030843 to 30.900322 mm**.
Its per-time source/candidate comparison is preserved, including all regressions.
The guard completes in **1,086.157 s**, peak sampled tree RSS **885,977,088 bytes**,
with all **1,069** resource observations replayed. No repaired interaction,
whole-clock geometry, engine, human or release approval follows.

## Clock-label fix and fresh witness replay

The real report exposed an index-name collision: its initial time-index variable
was later reused for vertex indices. The query loop had retained the correct
five-time iterator, and all numerical witness times were correct, but the report
listed 204 vertex IDs as sample indices. The original report and frozen study
source remain intact. The fix separates the outer sample-index variable from
inner vertex selections; it does not change the numerical query operations.

A fresh process uses the original source files, the same serialized anchor,
and captured Trimesh default-generator state with the corrected helper. All
**10,371 row bytes match exactly**, as does the post-query generator state.
Every other report field matches, with correct clock indices now
**[575, 592, 610, 627, 643]**. Both queries leave the shared generator unchanged,
so this particular fixture does not exercise randomly resolved ambiguous rays
or qualify older unseeded geometry captures. No temporal optimization is rerun.

The fresh witness query completes in **57.844 s** under a 512 MiB CPU guard, peak
sampled tree RSS **280,682,496 bytes**, with all **59** observations replayed
and the additional free floor. Corrected report, immutable original bindings,
row comparison and generator states remain under ignored
`reports/high-five-local-surface-clock-replay-v1`.

The next optimization needs explicit regional depth protection instead of
allowing one actor/time to worsen while another dominates the minimax objective.
That does not replace the existing physical acceptance or justify weakening the
geometry comparison. The full-project goal retains broader motions, rigs,
objects, controls, held-out testing and human cleanup evidence.
