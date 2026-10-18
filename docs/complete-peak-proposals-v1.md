# Complete peak proposals and rejected motion

Development evidence, 2026-10-18. `scripts/conic_peak_step.py` generates bounded
linear proposals using every model row. It adds one shared peak variable and
one absolute-movement variable per control, instead of a deficit variable for
every row. It does not select animation or certify nonlinear feasibility.

The objective is the largest positive normalized linear deficit plus an L1
movement penalty. Original boxes, mandatory affine cuts and all three-vector
norm cones are retained. Search interiors are explicit; admission uses the
original, unshrunk bounds strictly. A solver status alone cannot admit a
direction. The auxiliary peak is recomputed from the proposed direction,
without clipping or otherwise modifying control values. No optimality
certificate is claimed.

Input validation accepts bounded finite real values up to Float64, including
integer inputs. Direct lower/upper comparisons reject the minimum signed
integer without overflowing an absolute-value operation. Sparse duplicates
are summed on owned copies. Complete input ownership, canonicalization,
triplets, CSC storage and bounded construction scratch must fit the 64 MiB
assembly allowance. Solver factorization is separately covered by the process
tree memory guard. An oversized problem is rejected before output allocation;
rows and control columns are not removed to make it fit.

The focused source suite passes **405 local cases, zero skipped**: the previous
358 plus 47 proposal tests. Both source-check workflows include the new tests.
Coverage includes analytic repair, complete last-row/column handling, sparse
duplicate ownership, fake solver success rejected by strict original bounds,
assembly refusal and signed integer overflow boundaries.
The same 405 cases also pass on Windows and Ubuntu at source commit
`369d9e136caa5bd13d9baccdfe564af264b61d3e` in
[hosted run 39159162922](https://github.com/DocMorphic/strep/actions/runs/39159162922).

## Full model experiment

The experiment retains **6,984 rows, 216 controls, 499 mandatory cuts and 155
norm cones**, including all selected point rows, original author limits and
separate step limits. Selected-joint changes remain capped at five degrees;
constant root offsets remain capped at two centimetres. Protected animation
frames and the original physical checks are unchanged.

The first normalized joint radius, 0.0625, yields a strictly admitted linear
direction. The model has 433 variables, 956,302 sparse entries and a declared
complete assembly estimate of 55,738,536 bytes. The initial run takes 8.219
worker seconds, with sampled process tree peak 201,539,584 bytes under 512 MiB.
These are sampled observations on this machine, not portable performance
guarantees. The 600 MiB free-memory reserve remains in force.

This differs from the [previous hinge experiment](temporal-complete-hinge-v1.md):
it minimizes peak deficit without that experiment's fixed normalized peak
ceiling of five. It is **not an equivalent-problem speed comparison**. The
peak improves from 5.422634 to 5.233729, while the sum of positive deficits
gets worse, from 7,438.378614 to 7,689.239477. Neither normalized quantity is a
physical contact tolerance. The model remains centered at the earlier qualified
pose; the latest retained pose is an acceptance reference, not a refreshed
linearization center.

## Actual motion checks

Four predefined fractions are applied to the complete proposed control vector.
Actual poses, global contact conditions and original mesh geometry are checked.
Rejection stops only after a concrete required or protected condition fails.

| Fraction | Concrete failure | Geometry evaluated |
| ---: | --- | --- |
| 1 | Hand-to-hand contact | None; rejected by global check |
| 0.5 | Partner penetration, frame 55, B into A | Frames 0 through 55 |
| 0.25 | Partner penetration, frame 55, B into A | Frames 0 through 55 |
| 0.125 | Partner penetration, frame 55, B into A | Frames 0 through 55 |

**No step is retained.** These are partial evaluations with decisive failing
witnesses, not complete-clock successes. A retained step would require all 496
conditions and both the current and original benchmark guards. No rejected
candidate is exported or promoted to Studio, and the existing accepted
diagnostic motion remains unchanged. Passing a local affine model does not
establish realistic motion or interaction quality.

Local evidence is preserved in `reports/temporal-complete-peak-v1` and
`reports/temporal-peak-validation-v1`. The implementation before the signed
integer boundary fix and its tests are archived in
`reports/conic-peak-tests-v2/implementation`; those original studies retain
their original source bindings. Current-source tests and numerical replay
are recorded separately rather than rewriting those studies.

Next refresh the model at the latest retained pose and incorporate the actual
rejected contact witnesses. Keep every mandatory condition and the original
author limits. Do not solve disagreement by relaxing physical thresholds or
by accepting smaller steps that still fail. Broad action coverage, rig transfer,
editing, game-engine checks, offline packaging and genuine human review remain
part of the active whole-project goal.
