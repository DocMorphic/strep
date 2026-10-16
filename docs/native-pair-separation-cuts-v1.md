# Source-axis cuts for newly intersecting triangle pairs

The first joint contact/surface fit passes all original native motion checks
and authored contacts, and lowers all ten selected penetration-depth peaks.
It still regresses four mesh measurements. An exact canonical triangle-pair
comparison shows that most candidate crossings involve pairs absent from the
source crossing witnesses. The source and rejected candidate remain immutable.

`scripts/native_pair_separation_cuts.py` builds all nine vertex-pair
inequalities for each explicitly supplied triangle pair, using its separating
axis in the supplied original scene. Every requested pair is retained. Invalid
identities, duplicates including reversed pairs, incomplete vertex populations,
degenerate triangles and exhausted row budgets reject the request.

The lower search bound is `min(requested_clearance, original_axis_gap)`.
Negative or zero original gaps remain explicitly unresolved; absence from a
tolerance-based crossing report is not treated as proof of source separation.
The returned material rows respond to both actors. These are local search
constraints, with no claim of complete collision discovery, nonlinear pose
feasibility, continuous separation or animation quality.

Fifteen new tests exercise complete nine-row construction, both moving actors,
positive separation, unresolved source overlaps, canonical identities and
invalid inputs. Together with the twelve existing exact-key derivative tests,
all 27 affected tests pass locally in 10.38 seconds. The guarded run takes
27.406 seconds including admission, peaks at 136,859,648 process-tree bytes,
and independently replays all 29 resource observations.

At `fdf8f68`, [focused hosted run 38888385636](https://github.com/DocMorphic/strep/actions/runs/38888385636)
passes all 15 new cases on Ubuntu (0.71 seconds) and Windows (1.27 seconds).
Inventories contain 527 Python modules and 45 Node suites; the contact/rig
subset contains 91 Python modules and five Node suites. This is not a claim
that the full inventory or release criteria pass.

The measured high-five case contains 2,526 new triangle pairs across the five
declared contact-near native keys. All have strictly positive source-axis gaps;
the smallest is 3.369338e-7 metres. Complete construction yields 22,734 scalar
rows and 545,616 analytic nonzeros over the same 504 original controls.
Canonical source vertices still match the unchanged native decoder to
6.661338e-16 metres. The previously rejected candidate violates 10,528 of the
new scalar search bounds. This check does not rerun mesh collision discovery.

The cut-building guard completes in 30.454 seconds at a 214,585,344-byte peak,
with all 32 resource observations replayed. The 512-MiB process limit and
additional 600-MiB free-memory floor remain unchanged.

The first solve adds every new-pair inequality as a hard source-axis bound,
retaining all 619,662 native, three contact and 4,034 original floor-protection
rows. Contact search caps remain 29.5 mm, with actual acceptance still 30 mm.
The original 29,378 surface rows remain soft. The combined matrix has 675,814
norm rows, 4,129,645 nonzeros and 646,433 hard rows. Clarabel reports
`PrimalInfeasible` after 32 iterations. No direction or clip is produced.
This is local affine infeasibility with these controls, cuts and trust box,
not proof that the animation task or original nonlinear problem is impossible.

The solve finishes in 51.906 guarded seconds at an 885,723,136-byte peak,
with all 53 resource observations replayed. The 1-GiB process-tree limit and
additional 600-MiB free-memory floor remain unchanged. No model inference,
training or engine execution occurs.

Forbidding every new pair is stricter than the actual no-regression comparison
of mesh counts. The next proposal therefore prioritises the new-pair deficits
while keeping the previous affine surface merit as an additional hard search
budget. The recorded prior direction must first reproduce its complete saved
affine residuals exactly and satisfy this budget. All original native, contact
and floor caps stay unchanged. The budget applies to a local proposal surrogate,
not to actual penetration-depth or intersection acceptance thresholds. A fresh
decoded native/floor/contact/mesh comparison is still required for any clip.

The first priority solve returns `AlmostSolved` after 37 iterations; both
minimum-norm attempts time out. The caller rejects it before export. A fresh
frozen-model diagnostic replay saves the proposed controls and every affine
residual before rejection. All 619,662 original native, three contact-search,
4,034 floor and three duplicate contact rows pass strictly. Only two additional
surface-merit budget rows fail the caller's unchanged 1e-8 normalized comparison;
the largest excess is 2.494152e-8. No native/contact/floor cap is responsible for
this particular affine rejection, and no decoded motion pass is inferred.

The interrupted-on-assert attempt retains its failed resource receipt:
117.110 seconds, 960,081,920-byte peak, all 117 observations replayed. The
completed diagnostic replay takes 120.953 seconds at a 960,708,608-byte peak,
with all 121 observations replayed. Both stay within the same 1-GiB/600-MiB
resource policy. The original failed attempt is not overwritten or relabelled.

The existing `native_affine_surface_restore.restore` routine can search the
segment between the verified feasible reference and this saved proposal. This
keeps every original norm and additional search-budget row, checking the full
hard population at every probe with zero affine tolerance. Convex norm sublevels
along a segment form an interval containing the feasible reference. The
routine remains only an affine proposal tool; any resulting export still needs
independent decoded validation.

The segment stage first reproduces all 675,814 saved affine residuals exactly.
It clips the proposed controls to the exact original trust box and searches
32 segment probes. A fraction of 0.07735409354791045 toward the priority proposal
passes all 653,080 hard rows with zero affine tolerance. No cap or tolerance is
relaxed and no new conic solve runs. The resource guard completes in 43.671
seconds at a 360,026,112-byte peak; all 45 observations replay.

The actual exported clips meet all three authored contacts at 29.105544,
6.419751 and 29.428919 mm. These contact measurements alone do not qualify
the candidate; independent full native/floor and direct mesh checks remain
required.

The worst new-pair surrogate deficit changes from 6.685649876 to
6.685649711 normalized units along this segment: approximately 1.65e-10 metres
at the declared 1-mm scale. This is too small to infer meaningful physical
improvement. The segment's useful result is strict affine feasibility; its
actual mesh result must be measured separately. A maximum-deficit objective
can be dominated by one nearly invariant pair while other pairs change.

Independent actor validation passes all 619,662 original native rows and
preserves the original floor bound at all 2,017 times per actor. Every physical
floor failure remains. Actor A completes in 147.406 guarded seconds at a
273,424,384-byte peak (147 replayed observations); B completes in 132.953
seconds at 272,084,992 bytes (133 observations).

The final separate scene stage replays both full saved native populations and
all selected cached vertices against the actual exports, freshly rechecks the
coupled contacts, and calls the unchanged direct mesh evaluator with the same
seed and baseline. It completes in 98.719 seconds at 339,509,248 bytes, with all
99 resource observations replayed. No cached-vertex substitution is used for
the final geometry call.

The new candidate improves 21 selected measurements, regresses four and leaves
ten unchanged. It is rejected; the original remains selected. Nine directional
depth peaks improve, but the B-inside-A peak at 2 seconds worsens. The largest
remaining depth is 17.690345 mm, still over the 5-mm screen. This is not an
improvement in the number of acceptance failures over the previous candidate.

| Time (s) | Regressing measurement | Source | Candidate |
| --- | --- | ---: | ---: |
| 2.000000000 | Triangle intersections | 594 | 635 |
| 2.000000000 | B inside A peak depth (mm) | 13.483237 | 13.757294 |
| 2.066666603 | Triangle intersections | 455 | 585 |
| 2.066666603 | A inside B vertices deeper than 5 mm | 17 | 19 |

Static source-skin attribution adds useful evidence about the first rejected
candidate's new-pair witnesses. A has 986 unique vertices across 1,099 triangles;
982 vertices have a finger joint as their dominant influence. B has 1,080
vertices across 1,223 triangles, with 1,071 dominated by finger joints. Every
dominant influence has the editable wrist (node 43) as its nearest editable
ancestor. The current four-node control set edits shoulder, arm, forearm and
wrist, with no independent finger control. This is ownership evidence, not a
causal or pose-sensitivity certificate.

Next, inspect the existing finger tracks and original rate bounds before
choosing additional controls. Also distinguish the 0.1 local trust radius from
the full authored control boxes: the current solve explores only a fraction of
the allowed rotation range. A larger trust experiment must preserve original
native caps and verify any scalar-lift positivity certificate over its full new
box before using the cached model. An aggregate per-pair deficit objective may
address the observed maximum-deficit plateau; it would still be a proposal
heuristic subject to the same actual acceptance checks. None of these next
experiments may silently reset source caps or infer success from a surrogate.

All release capabilities remain unapproved. The selected-time study does not
establish full-clock geometry, grounding, self-collision, engine behavior,
semantic success, held-out generality, animator ratings or cleanup time.
