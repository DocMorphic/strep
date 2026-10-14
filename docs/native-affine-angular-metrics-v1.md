# Explicit orientation measurement for affine rig transforms

Native correction can now measure orientation separately from a joint's stored affine transform. This addresses a measured input mismatch: the existing rig reader admits near-rigid local transforms at its `1e-5` import tolerance, while the old angular evaluator requires world rotation blocks to be proper at `1e-6`. The actual transferred Quaternius clips exceed the latter after hierarchy composition, including moving, weighted joints. Neither ignoring an unused ancestor nor dividing all matrices by a scalar solves that mismatch.

## Metric choice and geometry preservation

The existing `strict` mode remains the default and its rejection criteria are unchanged. A caller must explicitly add:

```json
"orientation_mode": "right-polar-v1"
```

to a checksum-bound `strep-native-vertical-root-v1` recipe to use the new metric. Unknown values reject. This is a separate declared angular measurement epoch, not a waiver of old strict failures or evidence that a rejected clip has become realistic. Positional source samples, key times, four original duration bins, per-joint maxima, `1e-5` rate tolerance, floor tolerance, displacement bounds and frozen keys remain unchanged.

For each original linear transform A, the metric derives the right polar factors A = QH. Q supplies orientation for angular speed/acceleration; H retains symmetric stretch and shear in the measurement archive. The implementation uses batched SVD and verifies reconstruction and proper Q. This follows the decomposition documented by [SciPy 1.15.3](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.linalg.polar.html). Choosing it as an animation metric is a project decision; glTF does not prescribe this motion-quality metric. The [glTF transformation specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#transformations) defines the original stored transform semantics, including T·R·S composition, which the decoder and export continue to preserve.

No source node, quaternion, matrix, inverse bind or vertex is normalized to Q. Positional measurements use the original affine world origins. The exporter still appends only a root translation animation and retains original rig/animation payload. Both source and exported observations derive their orientation from the same explicit metric. Source/candidate stretch and singular values, metric names, implementation hashes and reconstruction summaries are archived. Every original joint remains in rate evaluation.

The new primitive rejects nonfinite transforms, nonpositive determinants/reflections, singular values below `1e-12`, condition number over `1e8`, relative reconstruction error over `1e-10`, or orientation orthogonality/determinant error over `1e-12`. Those are decomposition validity checks, not animation-quality limits. General negative-scale/reflection import remains unsupported. The existing rig reader's source restrictions are not broadened by this metric.

Every exported root-only proposal now additionally requires **exact equality of all stored world linear transform blocks** at the complete edit clock. That protects the original rotations, scale and shear rather than approving a different geometry after orthonormalization. Frozen and other tracks, unaffected world matrices, original positional/angular caps, full-mesh sampled floor checks and the existing horizontal readback tolerance still apply. No contact, continuous collision, semantic, engine or human approval follows from a numerical pass.

## Validation and development study

All **43 targeted checks pass in 46.05 seconds**. Analytic tests recover a known rotating frame through changing symmetric stretch/shear, verify its known angular speed and zero angular acceleration, retain original inputs/positions, and compare every factor with SciPy's implementation. Reflection, singularity, ill conditioning, nonfinite inputs and unknown modes reject. A real generated-rig GLB with explicitly stored near-unit nonuniform scale still fails strict angular extraction; an independently requested polar proposal passes its full sampled export checks while every source node and linear transform remains intact. This is software geometry evidence, not production anatomy or human-quality evidence. Existing strict correction and floor/contact preflight tests remain included.

The validation guard completes in 63.219 seconds, peak recorded RSS 121,479,168 bytes, with all 64 resource observations replayed. These CPU jobs use the declared 512 MiB estimate and stricter 512 MiB runtime tree cap, with unchanged 600 MiB free-RAM floor, 15-second stability and 900-second execution bound. Model/full-body worker policy is unchanged.

The first real development protocol includes all three retained angular-extraction failures: male crawl, female get-up and female run/roll/stand, on their unchanged source clips and original floor clocks. With the new explicit angular metric, all three reach a later storage restriction: `float32-axis-grid` requires an exactly signed unit local root direction, which these roots do not supply. No optimizer or candidate is produced. These failures remain under ignored `reports/native-vertical-root-polar-population-v1`; the guard completes in 23.328 seconds with all 25 observations replayed. No axis is rounded or rig transformed to bypass the storage precondition.

A separate continuous-key protocol retains exactly the same three source cases, the explicit polar metric and the original positional/floor/frozen/displacement constraints. All three produce exports, but **none passes all conditions**:

| Source/target | Full sampled floor times | Speed / acceleration failures | Angular failures | Peak depth | Maximum displacement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Male crawl | 2,829 passing | 6 / 18 | 0 / 0 | 4.500013 mm | 16.146421 mm |
| Female get-up | 4,292 passing | 27 / 46 | 0 / 0 | 4.500009 mm | 219.582252 mm |
| Female run/roll/stand | 5,024 passing | 16 / 13 | 0 / 0 | 4.500022 mm | 217.427209 mm |

Every linear transform, unaffected joint world matrix, frozen ending key and other track is preserved. Horizontal joint drift is zero in all three. The 234.766-second guard (218.610 seconds execution) records peak RSS 340,176,896 bytes; all 232 resource observations replay. The two previously measured over-budget male actions and earlier terminal Cesium trials are not rerun. These are reused development clips/rigs, not held-out release evidence.

Fresh replay reconstructs all 12,145 source/export pose times and rechecks all 526,890 original rate conditions, floor observations, complete original payload and frozen/other tracks. All observations and failures reproduce exactly. An independently implemented inverse-Newton iteration verifies the source orientation factors on every joint/time, using matrix inversion instead of SVD; it converges in two steps. Maximum orientation agreement error is 5.857e-15 and angular-cap discrepancy is 1.153e-10. Agreement tolerances for that numerical comparison do not change motion acceptance. The 249.859-second replay guard records peak RSS 352,071,680 bytes and all 246 resource observations replay. No optimizer is rerun for this replay.

## Storage coordinates retain the actual axis coefficient

The three original storage rejections all have the same axis `[0, 0, 1.0000000000000002]`. The direction is axis-aligned; requiring its coefficient to equal exactly one was unnecessary. The Float32 grid now uses the actual finite nonzero coefficient a: world-offset spacing is native Float32 spacing divided by |a|, and its intercept is (native anchor − original coordinate) / a. No axis coefficient, rig transform or source geometry is rounded to satisfy the solver.

The method still requires exactly one nonzero local component and still rechecks the actual exported file. It remains a sufficient grid rather than all possible Float32 values. The existing strict floor, displacement, frozen-key, full-rate and horizontal readback limits are unchanged. Six signed/neighboring-unit coefficient cases verify known native Float32 coordinates, and a generated-rig export with the real neighboring-unit coefficient passes all sampled checks without changing any linear transform.

The final expanded batch passes **50 tests in 51.44 seconds**, with a 68.235-second guard, peak recorded RSS 123,482,112 bytes and all 69 resource observations replayed. The complete/focused source inventories validate as 505 Python/45 Node and 68 Python/5 Node files respectively; this is inventory validation, not a rerun of every suite.

The separate corrected-grid protocol preserves the first rejected attempts and the continuous exports. All three now reach optimization, but no candidate is produced: crawl and roll reach their 60-second solver limit with no feasible primal solution, while get-up returns status 2 (infeasible in this restricted grid/model). Neither timeout nor this sufficient-grid result proves that the full motion problem is impossible. The 157.062-second guard records 140.891 seconds execution and peak RSS 220,745,728 bytes; all 156 resource observations replay.

A final binding audit rehashes original inputs and complete artifact inventories for both continuous and corrected-grid cohorts. All 63 reference arrays (4,406,168 entries), all sparse constraint matrices and source cap/clock/world observations match byte-for-byte; the only implementation difference is the scalar storage-coordinate helper. Grid coordinates reproduce with the original coefficient retained. The audit takes 18.234 seconds and all 20 resource observations replay. It does not rerun optimization or mesh geometry. These records separate the orientation fix from the still-unsolved stored motion-rate problem.

The model/checkpoint, original asset selection and every release capability/calibration gate remain unchanged. The full-project goal stays active, including support-aware correction, object/partner interactions, editing/style, engine integration, held-out evaluation and animator cleanup review.
