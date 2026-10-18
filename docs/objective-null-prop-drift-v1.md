# Geometry rejection and unnecessary prop drift

The 49-control temporal proposal repaired ten source-rate rows but fails scene
nonregression. Complete meshes were checked at the four predeclared critical
times, including the authored box touch. The other three samples pass; the touch
regresses. An independent process reproduces all four body/partner/floor samples,
all 20 complete mesh pairs, world arrays and physical decisions without the new
producer, fit, profile, factor or solver modules. It shares the existing geometry
libraries and is not independent physics.

| Box-touch observation | Qualified reference | Fitted proposal | Original-prop-control diagnostic |
| --- | ---: | ---: | ---: |
| Surface crossing records | 113 | 123 | 117 |
| Maximum penetration | 23.475561 mm | 43.094892 mm | 23.083920 mm |
| Actor vertices deeper than 5 mm | 374 | 498 | 369 |
| New failed condition identities | — | 0 | 0 |
| Geometry nonregression | Reference | Rejected | Rejected |

The existing failed pair stays failed, so unchanged pass/fail counts alone would
hide the regression. Original componentwise metric comparisons reject the fitted
proposal. Restoring the prop controls improves depth but still increases crossing
records; that diagnostic is also rejected. No tolerance, metric, topology,
permission, body motion or original condition has been removed to retain either.
The remaining 218 planned times are unqueried after this decisive failure; the
complete 222-time plan remains saved, not falsely reported complete.

## Causal diagnostic

The fitted prop rotates **13.542260 degrees** and its selected-key position moves
**38.060885 mm** relative to the qualified reference. All four prop columns are
exactly zero in the complete 6,050-row primary motion-rate Jacobian and the
33,594-row world guard matrix. Those variables still affect prop constraints and
geometry. A weak secondary L1 term and approximate solver status can therefore
leave prop movement with no primary benefit; the existing model has no local
mesh barrier preventing this collision.

The diagnostic keeps all 45 body inputs and actual character files unchanged and
sets only the four explicit prop deltas to their original origin. All **68,900**
original local norm and physical-radius conditions, all world guards and the
original control box still pass strictly. Primary predictions are unchanged;
L1 decreases from 4.697141775957195 to 4.580958283558672. Actual native prop
permissions, all **2,017** original sampled permissions and every declared contact
are recomputed and pass. Body motion evidence is explicitly inherited by exact
payload/input identity; no new 944,562-check body run is claimed.

This isolates unnecessary prop drift as a major contributor to the extra
penetration. It does not solve the remaining mesh collision or establish that
four prop variables alone can solve the complete request. Both variants retain
the same ten numerical motion repairs but neither becomes a qualified asset.

## Checked secondary proposal helper

`scripts/native_objective_null_reset.py` offers an optional origin proposal for
explicitly named **exactly zero primary affine columns**. It retains the full
control domain and all original rows. The initial proposal must already satisfy
every original norm, hard row and box bound; this cannot rescue an invalid point
by clipping it. The optional point is returned only if primary affine values
remain identical, L1 strictly decreases and every original condition passes
again with zero added tolerance. Resetting a variable needed by another
constraint is rejected, as is an origin outside the original box.

Tiny nonzero primary coefficients remain nonzero. The helper does not infer
controls, change author permissions, remove variables, claim a solver optimum or
prove nonlinear invariance. A zero affine derivative alone is insufficient to
inherit motion; callers need separate input/payload identity or full nonlinear
checks. Scene geometry and contacts always remain separate gates. In this study,
the helper's locally accepted point is the geometry-rejected causal diagnostic.
It is not automatically applied to Studio or the selected animation.

The local suite passes **101 tests**: 24 new helper cases and 77 existing sparse
solver regressions. Cases include all 68,900 original norms, 9,000 hard rows,
required constraint-dependent variables, tiny nonzero coefficients, original
boundary values, invalid initial points, no-op rejection, input ownership,
sparse layouts and whole-model budget rejection. Resource replay passes at
33.672 s / 156,479,488 bytes / 35 observations. No synthetic case is a human
rating or scene-quality approval.

The next correction needs explicit mesh-aware guidance and complete physical
postchecks. Exact crossing identities and represented-triangle witnesses are
being retained for that purpose. Qualified reference and Studio selection stay
unchanged: 72 protected repairs, 6,050 rate failures, two scene failures and all
previously disclosed body/dynamics/engine/human-review gaps. All release
capabilities remain unapproved under the same full-project goal.
