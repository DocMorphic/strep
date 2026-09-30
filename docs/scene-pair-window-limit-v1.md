# A fixed native-key window prevents complete clearance

The first paired request cannot clear its known collisions, regardless of more iterations or denser curves. Four source samples exceed 5 mm while **neither actor has any editable native quaternion-key support**. The worst fixed sample is 20.462726 mm. This is a lower bound on the remaining sampled peak for that request, not an optimizer failure.

| Fixed time, seconds | Original penetration, mm |
| --- | ---: |
| 1.608333333 | 11.188582 |
| 1.616666667 | 18.493961 |
| 1.625000000 | 20.462726 |
| 1.633333333 | 20.210362 |

The requested window starts at 1.591722595 seconds, but key eligibility and boundary preservation leave the first editable interpolation support starting at **1.640715957 seconds** for all four selected joints on both actors. No allowable control value changes their earlier poses. Increasing an iteration count or loosening a trust radius cannot affect those samples.

`paired_window_feasibility.py` derives movable times from eligible native keys and nonzero curve weights, using the open interpolation support between adjacent keys. It marks a sample fixed only when neither actor can move. The audit binds this to complete, existing source geometry. It finds 23 fixed samples, four failing the 5 mm screen. A lack of fixed failures would not prove reachability: other geometric, timing, contact or motion constraints can still prevent correction.

## Completed refined and angular experiments

The earlier quarter-step refinement completes all **126 sampled times and 252 directional queries**, with no per-time depth-cap or sampled floor regression. Peak depth decreases from 22.568796 to 22.560278 mm, an improvement of only **0.008518 mm**. All **37 failing times remain**. Its four clips pass 444 Godot actor-frame observations. The earlier angular audit still records rotation-rate increases; the result has not replaced the Studio comparison.

The subsequent angular-constrained solve preserves all existing constraints and adds **11,872 angular rows**, for 26,959 total norm rows. It returns AlmostSolved after 43 iterations and 13.40 seconds, with no affine hard-check failures. Its predicted peak is 22.539005 mm. Independent directional errors are at most 2.77e-12 rad/s and 3.60e-10 rad/s².

Actual exports demonstrate why solving is not acceptance:

| Fraction | Positional-rate failures, both actors | Angular-rate exceedances, both actors |
| --- | ---: | ---: |
| 1 | 28 | 3 |
| 1/2 | 0 | 1 |
| 1/4 | 25 | 25 |
| 1/8 | 30 | 53 |
| 1/16 | 48 | 56 |

The half step passes positional and retained-surface screens, but B has one angular-acceleration increase of 0.0000716725 rad/s² beyond its original span maximum, above the declared 1e-5 comparison tolerance. No tested fraction passes both motion screens. These small numerical increases are not themselves a naturalness judgment. No costly new mesh audit is run for these failed exports, and no acceptance tolerance is changed.

The export loader now permits additional parent-evidence bindings while requiring every original source binding and verifying every additional file. This supports the angular proposal without dropping its provenance. Changed, missing or rebound evidence is rejected.

## Prepared next request

Follow-up: this request has now been evaluated. The full source population has no fixed failures, but all five exports fail motion guards. See [expanded-window results](scene-pair-expanded-fit-v1.md). The preparation details below describe the evidence available before that run.

The new immutable request uses the same original actors, placements, joints and 5-degree edit budget. Its start moves to **1.408333333 seconds**, giving 0.2 seconds before the first known fixed collision; its end remains 2.591722595 seconds. The exact protected contact stays at 2.091722595 seconds. The wider local sampling clock contains 148 times.

The request is saved as `reports/scene-pair-expanded-window-v1-request.json` and prepared under `reports/paired-edit-jobs/expanded-window-v1`. Its source-bound plan is `reports/scene-pair-expanded-window-v1-plan.json`. On the previously measured time population, the new control support has **zero fixed failing samples**. This removes the demonstrated obstruction but does not establish a feasible correction. Earlier newly included times still need geometry and motion evaluation.

The next experiment should evaluate this wider request, retaining reusable geometry only when the exact clip bytes, placement, time and extraction method agree. It must preserve the protected contact and document any changed motion-cap population. Continuing the old narrow-window search cannot meet complete clearance.

Local evidence: `scene-pair-refinement-geometry-v1`, `scene-pair-angular-fit-v1`, `scene-pair-angular-export-v1`, `scene-pair-angular-replay-v1`, and `scene-pair-window-feasibility-v1`, all under ignored `reports/`. Both previously live workers and both export replays are terminal. No new release approval, held-out action or human quality rating is claimed.
