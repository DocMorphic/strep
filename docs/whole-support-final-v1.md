# Completed broad support-correction study

The original whole-support worker completed on 2026-09-28 with exit code 0. All 24 declared cases finished: eight different actions on three existing rigs. Every input and candidate passed the actual Godot import/pose comparison, totaling 8,640 actor-frames. The fixed study used one generation seed (1301); it is development evidence, not held-out release validation.

The final population, sources, implementation, exports, traces and engine results are verified in `reports/whole-support-breadth-final-v1/summary.json`. Earlier partial summaries remain unchanged. Actions include backpedaling, grapevine dance, beckoning, a broad jump, kneeling and rising, tying a shoe, an exhausted walk, and a jab/cross/retreat combination. Swimming, stairs, object and partner actions were explicitly excluded from this flat-floor study and remain requirements elsewhere in the project.

The results do not establish realistic motion. The independent descriptive analysis in `reports/whole-support-regressions-final-v1` finds:

- 18 of 24 cases increase the root-acceleration peak by more than 0.0036 m/s².
- 13 of 24 cases increase at least one predicted-support foot-speed peak by more than 0.001 m/s.
- 19 increased foot peaks lie within two frames of a predicted support boundary.

Those values are reporting bins, not newly introduced acceptance thresholds. Contacts are model predictions rather than confirmed ground truth; boundary proximity alone does not establish causation or incorrect motion. A planted foot may intentionally pivot, and action correctness still requires review.

The first rig's relatively large initial floor depths decrease, but other rigs can acquire small penetrations. For example, exhausted walking on rig 02 changes floor depth from 0 to 0.080 mm while root acceleration rises from 3.447 to 7.286 m/s² and the right support-speed peak rises from 0.1372 to 0.2665 m/s. A clean import or lower contact percentile cannot override these failures.

The root-cleanup evaluation completed on the full population in `reports/support-temporal-cleanup-v2`: 18 candidates retained numerical improvements, six retained their input, and none failed execution. All 48 input/selected clips passed 8,640 actual Godot actor-frame checks. The method preserves original edit budgets and achieved floor, support, boundary-speed and acceleration bounds; rejected proposals retain their input. The sum of squared root acceleration decreases by 0.807–14.697 percent among accepted candidates, but 15 cases still exceed the original raw root-peak reporting comparison and 13 retain a foot-peak regression. These improvements do not resolve the quality failures.

`reports/support-temporal-extension-v1.json` verifies that the earlier 19 selected outputs reproduce byte-for-byte, with identical selection outcomes. All source files, policy and solver bindings match. The recursively collected implementation snapshots differ only in `rig_runtime_cycle.py`: its later prop-export metadata and copied instructions are disclosed with the exact diff. That writer is not called by the root-translation exporter. No claim of identical whole snapshots is made. Of the five newly available cases, exhausted-walk rigs 02/03 and combat rigs 02/03 retain improvements; combat rig 01 retains its input.

`reports/midpoint-support-boundaries-v2` freezes the complete 24-row population and targets all 13 remaining foot-peak cases with the existing coupled leg/root method and midpoint floor constraints. It retains the same three-step limit, trust radii, backtracking fractions, two twelve-frame blocks and preservation tolerances as the earlier study. Its pipeline and completion record determine execution status; preparation is not evidence of a successful correction. The study/report code now derives population counts rather than retaining the earlier hard-coded 19/24 and 11-target labels.

The earlier 19-case developer-review package remains available and unchanged. The next completed comparison needs its own quarter-frame diagnostic and immutable review package. No human ratings, cleanup timings, held-out passes or release approvals have been inferred.
