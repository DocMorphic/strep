# Exact-key surface proposals

The contact-only high-five study reaches the authored hand targets at its full
step, but that clip worsens 14 selected mesh measurements. It remains rejected.
The next experiment holds contact targets hard while guiding the same bounded
native motion with local surface rows. Full decoded mesh evaluation remains the
acceptance authority; a surface-row objective does not certify separation.

`scripts/native_surface_key_jacobian.py` computes a sparse derivative of every
declared fixed material row at an exact existing quaternion key. It uses the
actual affine skin chain, including scale, all skin influences and actor
placement. Before accepting a derivative, it checks every canonical vertex
against the unchanged native decoder to an absolute 1e-12-metre coordinate
budget. Controls retain actor order, active-key order, node order and XYZ axes.
Rows at inactive keys remain present with zero derivatives.

The implementation rejects interpolated times, mismatched rotation clocks,
endpoint edits, minimum-envelope rows, incomplete actor layouts, invalid
material weights and exhausted sparse budgets. It returns no truncated subset.
The default linearizes the original zero-control epoch. An explicit `value`
now permits a complete, finite current control point inside the original edit
box, while retaining the source-zero canonical-vertex check and original
control layout. This does not replace full interval rates, decoded Float32
export, or mesh acceptance.

The current-point extension passes 18 tests, including complete central finite
differences at a nonzero point, exact default/explicit-zero agreement and invalid
control rejection. Local execution takes 12.62 seconds; its guarded run takes
29.344 seconds, peaks at 136,638,464 process-tree bytes, and independently replays
31 resource observations. At commit `499fea0`,
[hosted run 38898614845](https://github.com/DocMorphic/strep/actions/runs/38898614845)
passes all 18 cases on Ubuntu (1.86 seconds) and Windows (15.09 seconds).

Twelve tests compare the complete surface Jacobian with the existing native
interval model's continuous finite differences, using both actors, different
placements, convex material points, a world plane and inactive keys. They also
exercise invalid inputs and forced disagreement with the native vertices.
All pass locally in 9.60 seconds. The 512-MiB guarded run takes 26.391 seconds
including admission, peaks at 136,450,048 process-tree bytes, and independently
replays all 28 recorded resource observations. The additional free-memory floor
remains 600 MiB.

At commit `c1c260e`, [focused hosted run 38886349438](https://github.com/DocMorphic/strep/actions/runs/38886349438)
passes all 12 tests on Ubuntu (1.18 seconds) and Windows (15.84 seconds).
These are source checks, not animation-quality or full-inventory approval.
The declared inventories now contain 526 Python modules and 45 Node suites;
the contact/rig subset contains 90 Python modules and five Node suites.

The development experiment reuses the prior 504-column source-zero native and
floor matrix only after matching its saved inputs, implementation, complete
native vectors/caps/scales and coupled source contacts. All 619,662 native rows
and 4,034 original floor-protection rows remain hard. The three contact caps
become the authored 30 mm minus the already declared 0.5-mm search reserve;
actual decoded acceptance still uses the authored 30 mm. Every surface row is
a soft proposal objective. The original motion stays selected until separate
decoded native, floor, contact and independent geometry checks qualify a clip.

The first coupled fit completes under the unchanged 1-GiB process-tree limit
and additional 600-MiB free-memory floor. Its 156.672-second guarded run peaks
at 847,675,392 bytes; all 155 resource observations replay independently.
There are 29,378 surface rows and 705,072 analytic derivative entries. The
complete source canonical vertices agree with the native decoder to
6.661338147750939e-16 metres. The combined system has 653,080 norm rows,
3,584,029 nonzero entries and the same 623,699-row hard prefix. Clarabel reports
`Solved` after 40 iterations. Its optional minimum-norm phase is rejected by
the unchanged post-solve checks, so the primary direction is retained.

The first actual exported candidate meets all three authored 30-mm contacts:
29.113903, 6.588837 and 29.496371 mm. This is a decoded contact measurement,
not a native-motion or geometry pass. Independent actor and scene validation
is performed separately, without holding both full interval models in memory.

Actor A's independent stage passes all 309,831 original native rows and
preserves the original floor bound at all 2,017 declared times. All 2,017
physical floor failures remain; protection is not grounding clearance. It
retains complete canonical meshes at the five comparison times. The guard
completes in 152.156 seconds at a 268,525,568-byte peak, with all 151 resource
observations replayed. Actor B also passes all 309,831 original native rows,
preserves all 2,017 floor bounds and retains all 2,017 physical floor failures.
Its guard completes in 142.906 seconds at a 273,436,672-byte peak; all 142
resource observations replay.

The separate coupled scene stage independently recomputes all 619,662 saved
native residuals against the exact original caps/scales, replays every cached
vertex and face against the actual exports, freshly evaluates both actors'
contacts, and calls the unchanged direct native geometry evaluator. The same
per-query random seed, baseline and selected times are retained; cached
vertices are not substituted into the final geometry call. This stage completes
in 104.094 seconds at a 356,978,688-byte peak; all 104 resource observations
replay.

Of 35 selected mesh measurements, 20 improve, four regress and 11 are unchanged.
All ten directional penetration-depth peaks decrease. The largest falls from
20.590680 to 17.690345 mm, which still exceeds the 5-mm screen. Three triangle
intersection counts increase, and A's count of vertices deeper than 5 mm inside
B increases from 17 to 19 at the last selected time. The candidate is rejected
and the original remains selected. Contact success and lower maximum depth do
not override the failed acceptance conditions.

| Native time (s) | Source intersections | Candidate intersections | New triangle pairs | Resolved triangle pairs |
| --- | ---: | ---: | ---: | ---: |
| 1.933333278 | 640 | 639 | 401 | 402 |
| 1.966666698 | 567 | 580 | 530 | 517 |
| 2.000000000 | 594 | 639 | 508 | 463 |
| 2.033333302 | 644 | 596 | 508 | 556 |
| 2.066666603 | 455 | 585 | 579 | 449 |

These pair counts come from an exact canonical triangle-ID set comparison of
the retained direct reports, without new geometry queries. Most candidate
crossings involve pairs absent from the source crossing set. The next local
experiment should account explicitly for these new pairs and newly deep
vertices, preserving the original motion epoch and authored contact limits.
Refreshing witnesses must not reset the reference native caps or accept a clip
from its surrogate score. A fixed-axis separation cut may need all nine vertex
pair inequalities; its actual decoded mesh result still requires a fresh query.

The five selected contact-near mesh times do not establish full-clock geometry,
grounding, engine behavior, semantic success, held-out generality, animator
ratings or cleanup time. The entire-project goal and all release gates remain
open.
