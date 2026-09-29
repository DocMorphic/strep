# Individual contact-point rates and impossible transition timing

The new optional material-point guard avoids the large right-foot rate regression in the [previous two fits](carrier-support-v1.md), but does **not** solve the authored contacts. The trial exposes incompatible requirements: the held frame-20 right-foot pose cannot reach the frame-30 target within 5 mm at the original approach-speed ceiling. Two release constraints also fail a necessary endpoint-distance check. All candidates remain unapproved.

`ExportPointRateObjective` uses the native export interpolation at 120 Hz, including global rotations and all eight skin influences, to measure the selected fixed material points. Each authored stationary contact has separate source speed and acceleration maxima for approach, hold and release. Finite-difference stencils are assigned by their centers, including stencils crossing phase boundaries. Augmented inequalities discourage exceeding those individual maxima; they do not guarantee feasibility. The original whole-body rate guard can remain enabled independently.

This option requires explicit, fixed vertex IDs with stationary world targets and nonempty intervals inside the edit window. Moving targets and automatic vertex selection are rejected. It does not add angular-rate constraints, sole orientation, anatomy or force/balance modeling. Existing callers retain their previous behavior because the option defaults off.

The opt-in experiment and diagnostic are reproducible with the previously retained local fixture:

```powershell
.venv\Scripts\python.exe scripts/study_carrier_support.py reports/scene-carrier-v1/input reports/carrier-support-point-rate-v1 --rate-guard --point-rate-guard
.venv\Scripts\python.exe scripts/point_rate_reachability.py reports/carrier-support-point-rate-v1 reports/carrier-support-point-rate-v1/reachability.json
```

Use fresh output paths; these already exist in the development checkout. Model/mesh/fixture payloads are not bundled in the public repository.

## Measurements

The same original source, frame-90 material points, inclusive pin interval 30–149, editable window 20–159, 40-degree rotation and 0–220 mm lift budgets are retained. Both the whole-body and new point guards are enabled. Two stages of 60 iterations use 338 evaluations / 127.91 seconds of fitting. Both stages stop at their iteration limit without convergence. Maximum edits are only 0.129 degrees and 0.348 mm of root lift.

| Exported measurement | Original | Global guard only | Global + point guards |
|---|---:|---:|---:|
| Left foot maximum target error | 17.698 mm | 5.487 mm | 17.209 mm |
| Right foot maximum target error | 32.061 mm | 17.571 mm | 32.153 mm |
| Samples outside 5 mm, left + right | 622 / 954 | 110 / 954 | 620 / 954 |
| Right foot maximum contact-interval point speed | 0.06835 m/s | 0.24667 m/s | 0.06638 m/s |
| Right foot joint angular-acceleration peak | 10.162 rad/s² | 89.247 rad/s² | 10.162 rad/s² |

The new candidate stays close to the source, retaining substantial target misses. Independent decoded platform-coordinate measurements still find small rate increases: left hold speed +0.000050 m/s, left release speed +0.000018 m/s, and release acceleration +0.000866 / +0.000587 m/s² for left/right. These remain recorded violations, not a passing rate certificate.

The source proxy was independently compared to the GLB at 717 times for both material points: maximum position difference 0.108 micrometres, speed discrepancy 0.00000367 m/s and acceleration discrepancy 0.000602 m/s². Export quantization is excluded from the differentiable proxy, so actual export verification remains necessary. The initial standalone proxy-check script failed due to an incorrect metadata argument before numerical evaluation; it and the failure are retained, and the corrected check completed.

Full-mesh export checks preserve all 160 outside-window times within 0.081 micrometres. Ground and platform vertex depth remain zero at sampled times. Actual Godot verification passes 407 pose observations, two authored events, four callback mutation rejections, automatic/reverse playback and unload. Maximum actor component discrepancy is 8.21e-7. These validate transport and preservation, not motion quality.

## Constraint diagnosis

`point_rate_reachability.py` checks a necessary condition: a held boundary pose must be within `speed_limit × duration` of the target's tolerance ball. The diagnostic explicitly allows a 1-micrometre boundary-position error budget, separately from the unchanged 5 mm target tolerance. It records source/protocol/recipe hashes, and never changes the window, target or speed limit.

| Transition | Minimum travel | Travel available at source ceiling | Deficit |
|---|---:|---:|---:|
| Right approach, frames 20–30 | 42.207 mm | 22.239 mm | 19.968 mm |
| Left release, frames 149–159 | 3.789 mm | 3.226 mm | 0.563 mm |
| Right release, frames 149–159 | 4.080 mm | 3.726 mm | 0.355 mm |

These positive deficits rule out meeting all specified endpoint and speed conditions together, regardless of solver iteration count. Passing this distance check would not prove feasible acceleration, rig motion, collision avoidance or physical support. The diagnostic is currently a CLI study tool, not yet an automatic Studio warning.

Evidence lives in `reports/carrier-support-point-rate-v1` and `reports/carrier-point-rate-proxy-v1`. Thirty-one focused tests cover individual-point regression hidden by a faster body part, translation derivatives, rotation-dependent skin motion, static references, interpolation compatibility, malformed constraints, endpoint bounds and between-key audit failures. No browser/HTTP or human review was performed.

Next, expose this conflict during contact authoring and calculate an explicit edit-window proposal that passes the necessary travel checks, before another frozen fit. Do not silently relax target accuracy, increase permitted speed, change the held poses or describe an expanded window as the same experiment. The broader action, interaction, rig-transfer and release requirements remain open; all fourteen release capabilities are unapproved.
