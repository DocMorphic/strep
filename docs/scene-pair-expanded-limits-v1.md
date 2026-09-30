# Expanded-window limits and denser curves

The eight matched diagnostics show that removing motion limits does not produce a useful clearance solution. A denser curve improves the affine prediction while preserving the original limits, but all five actual exports still fail at least one motion check. The published reserve candidate remains unchanged.

## Constraint comparisons

The original 72-control, 148-time system is reproduced exactly: maximum control difference is zero. All comparisons use the unchanged saved geometry/Jacobians and the 5-degree source-relative edit budget. Default trust is 0.1 degree per three-vector control. Omitted conditions are diagnostic only and remain mandatory for acceptance.

| Diagnostic | Predicted peak, mm | Violations when rechecked against original conditions |
| --- | ---: | --- |
| Original | 22.554817 | None |
| Tenfold trust | 22.468335 | Exceeds original trust; no other affine violations |
| Without angular limits | 22.550534 | 46 angular rows |
| Without positional limits | 22.534327 | 216 positional rows |
| Without either motion family | 22.527298 | 642 motion rows |
| Without surface-distance norms | 22.554658 | 11 surface rows |
| Without local surface caps or distance norms | 22.404142 | 26 surface rows; 1.036395 mm per-time cap regression |
| Trust and edit budget only | 22.333198 | 231 motion rows, 24 surface rows; 1.023530 mm cap regression |

Increasing trust tenfold helps little, and no diagnostic predicts clearance. These are affine proposals; none is exported or accepted. The comparison does not establish which limits are perceptually necessary or prove global infeasibility.

## Nested curve refinement

The next experiment expands five to nine knots and 72 to 168 controls. It retains the exact source clips, native editable keys, protected contact, source witnesses, sample clock, original positional and angular row populations, original knot-span caps and edit budget. Coarse curves remain representable inside the refined basis. Angular policies are captured before replacing the control model, so adding knots does not change acceptance bins or caps.

The source vectors and radii match the original system. The largest projected derivative difference is 3.517187e-5 in row units per control radian; its effect at the declared trust lies below the existing comparison threshold. The independent surface direction error is 2.787142e-12 m; independent angular acceleration direction error is at most 2.833e-10 rad/s².

The default solve predicts **22.476399 mm**, but reports AlmostSolved and fails one hard norm check: maximum excess **1.214570e-6**, above the unchanged **1e-6** motion comparison tolerance. It returns no usable step and produces no animation.

## Equivalent numerical scaling

Two retries reuse identical matrices and preserve the physical objective. The solver minimizes `peak / scale + regularizer * ||step / trust||²`; keeping `scale * regularizer = 5e-7` preserves that objective up to a positive scalar. Constraints, edit budget, trust and acceptance tolerances remain fixed.

| Distance scale | Regularizer | Status | Maximum norm excess | Hard-check result |
| --- | ---: | --- | ---: | --- |
| 0.005, original | 0.0001 | AlmostSolved | 1.214570e-6 | Fail |
| 0.001 | 0.0005 | AlmostSolved | 4.410293e-7 | Pass |
| 0.025 | 0.00002 | Solved | 7.267124e-7 | Pass |

Both retries predict essentially the same 22.476399 mm peak. Their passing numerical checks do not establish nonlinear feasibility. The `Solved` variant is selected for actual GLB decoding.

## Actual exports

The refined export audit now checks angular as well as positional motion against the original bins. The geometry-entry guard requires passing angular evidence for this refined format and independently replays it before an expensive mesh audit.

| Fraction | Positional failures | Angular exceedances |
| --- | ---: | ---: |
| 1 | 4 | 7 |
| 1/2 | 1 | 0 |
| 1/4 | 3 | 1 |
| 1/8 | 1 | 2 |
| 1/16 | 2 | 1 |

No fraction passes all preliminary checks. No fresh candidate mesh queries, engine run, publication or quality approval follows these failed exports. The next experiment should measure margins on this exact refined representation and assess them using the unchanged original limits; margins from a different control basis cannot be assumed sufficient.

All workers in this sequence are terminal. Local evidence is preserved under `reports/scene-pair-expanded-limits-v1`, `scene-pair-expanded-refinement-v1`, `scene-pair-refined-scaling-v1` and `scene-pair-expanded-refinement-export-v1`. No held-out prompt or human-review evidence is consumed, and all release capabilities remain unapproved.

The full declared source suite passes in the minimal environment without PyTorch: **334 passed, 4 optional skips**. The preceding publication commit `b8249be` also passed [hosted Windows and Linux checks](https://github.com/DocMorphic/strep/actions/runs/36706869386); that hosted result does not cover these newer changes.
