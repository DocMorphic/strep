# Previous-pose continuation and contact interpolation

[`bounded_pose_continuation.solve`](../scripts/bounded_pose_continuation.py) adds a reusable source-capped rigid-node fit that favors the previous local pose. It preserves current source translations and all nonselected local transforms, projects the previous rotations inside the current source caps, and reports unmatched target residuals. This is an optional numerical helper; the existing independent-pose fitter and Studio behavior stay unchanged. A passing node target is not a passing skin contact or motion.

## API

```python
from bounded_pose_continuation import solve

candidate, report = solve(
    source_local, parents, targets, edit_limits_degrees, previous_local,
    max_evaluations=200, source_weight=0.002, continuation_weight=0.02,
)
```

Provide complete proper rigid local matrices of shape `(nodes, 4, 4)`, one acyclic parent index per node, explicit integer edited-node indices/caps, and targets with `node`, `world_matrix`, `position_tolerance_m` and `rotation_tolerance_degrees`. Caps are source-relative rotation-vector norms, up to 90 degrees. The previous pose must use the same node population. Its translations are not copied. Rotation weights are explicit finite values in [0, 1]; they are numerical regularization settings, not calibrated fitness or strength values.

The objective weights world translation residuals by 100, world rotation-vector residuals by 2, source edits by `source_weight` and selected local rotation changes from the previous pose by `continuation_weight`. Target tolerances report success; they are not hard target constraints. SLSQP constrains every selected source-relative rotation-vector norm. The established 1e-8-radian numerical cap allowance remains explicit. The previous rotation initialization is radially projected to 0.999999 times the source cap when necessary. A nonfinite, out-of-cap or worse-cost optimizer candidate falls back to that projected initialization; target errors remain visible. `max_evaluations` follows existing helper naming and limits SLSQP **iterations**, not total objective calls. The report retains actual evaluation/iteration counts and never grants quality or release approval.

All **23 focused checks** pass across the existing bounded/ball-fit modules and nineteen new continuation cases: a redundant chain retains its previous rotational choice, unreachable targets keep residuals within source caps, previous translations cannot replace the current source, protected nodes/input arrays stay unchanged, invalid optimizer candidates fall back, and malformed populations/hierarchies/caps/weights/targets/improper transforms fail. These are numerical software fixtures, not human animation ratings. The source API reproduces frozen real-rig calls at predeclared frames 61, 90 and 121 with **zero local-matrix difference**; this comparison shares the numerical solver and is not an independent global-optimality proof. Source coverage now declares 438 Python test modules / 41 Node suites. Both existing bounded-pose files were missing from the prior inventory and are now explicitly registered; the new tests extend the ball-fit file. The initial publication check exposed this registration gap; its failed record is retained.

## Why the previous contact clip slides

The [central hand-material clip](central-hand-contact-v1.md) has nearly constant object-local contact errors at its saved native keys: maximum native error rates are 0.00544 / 0.00281 / 0.00628 / 0.00378 mm/s for left center, right center, left neighbors and right neighbors. Exported joint interpolation nevertheless displaces those contacts from the native-error chord by up to 0.08510 / 0.23356 / 0.08651 / 0.23487 mm. At the tested rate/phase clocks it exceeds the original 5-mm/s speed limit.

Independent scalar replay decomposes all **16,960** point velocity pairs into native-error chord and interpolation-residual vectors. The original four tracks contain 14 / 30 / 54 / 118 failing actual pairs; their chord counterfactual has zero failing pairs. A chord in contact-error space is a diagnostic, not a realizable joint curve. The producer also observes a 5.2923-degree adjacent torso-joint change; that joint-angle diagnostic is outside this separate scalar replay. Receipt: `e5d6e364d61696b6e2eec29fbd75780e85430eea09952516d95f292b9f412699`.

## Complete continuation experiment remains rejected

Keep frame 60's previously replayed candidate exactly. For each following original hold key, initialize from the preceding final local rotations converted into the current original source coordinates. Use the helper's 0.002 source and 0.02 previous-local weights, unchanged eight 45-degree arm caps plus three 15-degree torso caps, the original targets and contact acceptance thresholds, and 200 maximum iterations. All translations, fingers, other locals and feet remain source-preserved.

All **62 native poses** pass actual skin position/opposition/side conditions and eleven caps. Independent candidate/skin replay checks **682 caps and 620 correspondences**. A separate trace-angle/Rodrigues replay checks all 61 continuation initializations and 61 objective pairs; the first pose remains exactly its original saved candidate. Neither audit certifies a global optimum or anatomy. Body-contact receipt: `4b282550854734abee39282d0bfa3de333b1496962406c68fa1078c9a8634358`. Continuation receipt: `83e7bd2679a12a2b34abd622ca1e6a320b2e5e8604da9a941b29190a9c13a7a7`.

The actual source-preserving GLB export still fails all four contact tracks at the full original clocks:

| Contact | Worst position | Worst speed | Worst opposition | Minimum side | Surface samples passing |
| --- | --- | --- | --- | --- | --- |
| Left center | 2.1841 mm | 12.2230 mm/s | 8.2519 degrees | +0.2422 mm | 1033/1033 |
| Right center | 2.8775 mm | 8.2666 mm/s | 8.8528 degrees | +0.1503 mm | 1033/1033 |
| Left neighbors | 3.5106 mm | 12.2544 mm/s | 15.0012 degrees | -0.5505 mm | 688/1033 |
| Right neighbors | 3.5967 mm | 8.4028 mm/s | 14.9949 degrees | -0.5536 mm | 886/1033 |

Right-hand sliding decreases while left-hand sliding increases. Both neighbor rows still fail contact side, and left neighbors also exceed the original 15-degree normal threshold. Do not count this as an accepted temporal correction. Independent export/clock replay preserves **1,033 times per contact, 10,330 normal correspondences and 16,960 point velocity pairs**. Receipt: `63282aca9faaef42cdf48b2e50804a71487eac33ff2049072669a84f9219ff79`. No full-body geometry, force, model guidance, engine, human or release approval follows.

## Frozen next key-insertion experiment

Replay every failing original-clock position/opposition/side observation and every failing velocity pair. Include every native interval with positive-duration overlap of a failing pair, rather than assigning a cross-key pair to only one interval. This identifies **45 complete failing native intervals**. Predeclare three interior quarter keys for each, quantized to glTF float32 times: **135 proposed added keys**, within the explicit 192-added/512-total-key budgets. No key has been fitted or exported by this selection.

The pilot selects the three highest normalized-error intervals, then ascending frame for ties: **79–80, 78–79 and 80–81**. Fit their nine inserted keys first, preserving all existing native keys. Original acceptance limits remain unchanged. If the pilot preserves existing passing conditions and improves the selected interpolated intervals, assess the complete 135-key proposal and full original/added clock before geometry/force/model comparisons. Selection replay independently reconstructs all 16,960 velocity pairs, complete failure events, overlapping intervals, ranking and key quantization. Receipt: `f706655d4fc86952e39db3fcaef10c21f78b15f05f91586db47b619e19a73cee`.

The first selector fails before creating a numeric plan because its filename `select.py` shadows Python's standard module. Preserve its source/supervisor failure; an identically coded renamed worker completes. Six failure resource observations and seven successful selection observations replay; six independent selection-audit observations replay. This is a naming repair, not a numeric-policy change.

## Evidence and scope

Ignored studies retain immutable inputs, candidates, exports, method snapshots, numerical receipts and resource traces under `reports/central-hand-temporal-diagnosis-v1`, `central-hand-continuation-v1`, `central-hand-continuation-clock-v1`, `pose-continuation-source-checks-v1`, `pose-continuation-real-replay-v1` and `central-hand-densification-v1`.

The complete pose producer/audit take **281.938 / 7.563 seconds**, with **268 / 13** independently replayed resource observations. Export/clock producer/audit take **23.047 / 5.453 seconds**, with **26 / 11** observations. Focused source checks take 13.250 supervised execution seconds with eighteen observations; the three public API replays take 16.234 seconds with twenty-one. All traces replay. Scoped real-rig/incident-surface jobs retain 1,024 MiB + 600 MiB reserve; pure saved-array/scalar/test fixtures use 512 MiB + 600 MiB. Complete body/geometry audits retain 2,048 MiB + 600 MiB. Sampled resource policy does not certify motion or available RAM between observations.

The single full-project goal remains active across arbitrary actions, scenes/partners, rigs, editing/styles, transitions, engines and genuine developer/animator ratings and cleanup. The unchanged checkpoint is still the baseline; no model training or clean-motion admission is justified by these contact experiments.
