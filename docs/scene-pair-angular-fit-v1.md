# Matched angular-constrained paired fitting

The [angular review](scene-pair-angular-v1.md) found changes that positional motion checks did not cover. A fitting experiment now appends angular speed and acceleration norm constraints to the existing refined-curve problem. The real fixture solve and exported comparisons have since completed; see the [result and fixed-window obstruction](scene-pair-window-limit-v1.md). None of the five exported fractions passes both motion screens.

## What remains matched

The experiment consumes the completed `scene-pair-refinement-v1` linearization and verifies its source and implementation bindings. It retains the same 168 controls, 0.1-degree trust radius, surface gaps and Jacobians, depth caps, original-reference edit limits, and positional motion rows. Array-equality checks verify every previous constraint is still present in the original order.

Each actor's angular policy is constructed from the immutable original model **before** replacing its five-knot edit curve with the refined nine-knot curve. This preserves the original sampling clock, knot-span maxima and native editable-key eligibility. Only the derivative columns expand to the refined layout. Actor-specific derivatives are placed in the appropriate block of paired controls; unequal actor widths are supported.

The added cones constrain the norms of world-frame interval angular velocity and its sampled time difference. They include an edited joint's own rotation and descendants. A separate native-motion direction checks the derivative prediction before solving. Source angular rows must already respect their own caps within the declared numerical check. Solver proposals still require exact export replay, both kinds of motion checks, fresh complete mesh/floor queries and engine validation.

## Verification so far

Nine new local tests pass, including one small solve using the pinned real conic solver. In that fixture, a positional-only problem reduces a 10 mm gap to approximately 9 mm by rotating a stationary joint. Adding a zero-angular-motion cone prevents that rotation and leaves the 10 mm gap. This verifies that the new cone changes the feasible set; it is not evidence that the development high-five can be corrected.

Other tests verify unchanged preexisting rows, actor-column separation, unequal actor layouts, directional predictions and rejection of malformed angular rows. Combined with the earlier angular-row and rotation-rate tests, **22 focused tests pass**. Eight new tests join model-free Windows/Linux CI; the pinned-solver test is skipped when its local bootstrap is absent.

## Execution and next decision

```powershell
.venv\Scripts\python.exe scripts/study_scene_pair_angular_refinement.py reports/scene-pair-refinement-v1 reports/<new-angular-proposal> --wait-seconds 7200
```

The optional bounded wait acquires the existing OS worker lock before loading the real fixture and running the solve. It does not start a competing heavy job, recreate an existing destination or restart the geometry audit. It stops waiting after the declared timeout. The current destination is `reports/scene-pair-angular-fit-v1`; a historical process observation is saved separately in `reports/scene-pair-angular-fit-v1-queue.json`. Process identity and the command handle, not that record alone, establish whether it is still waiting or running.

The previous quarter-step geometry audit and the new solve are both terminal. Every attempted angular-constrained export is retained and independently checked. After the original worker finished, the export loader was updated to verify and retain extra parent-evidence bindings without dropping required original inputs. The result above documents the remaining failures.

Production paired fitting, the published Studio candidate and all release approvals remain unchanged. These angular caps are a source-relative engineering constraint, not a validated naturalness criterion. No held-out actions, new training or human quality ratings are involved.
