# Finger parameter scaling experiment

The floor-valid sphere experiment left most available finger movement unused and retained about 32 mm of skin/object penetration. This experiment changes optimizer coordinates while preserving the reachable poses and objective. It does not enlarge edit limits or change the acceptance thresholds.

V9 maps a dimensionless finger control `u` to rotation vector `L*u/sqrt(1 + ||u||²)`, where `L` is that joint's edit limit in radians. Its derivative at zero scales with `L`. V10 instead uses physical-angle control `a` and applies the same map to `u=a/L`. Its finger derivative at zero is the identity. Body controls retain the original mapping. The transformation is an invertible coordinate scaling before the bound, so allowable rotations, physical pose regularization and constraints remain identical.

Tests verify equivalent rotations under corresponding coordinates, unchanged body behavior, the analytic origin Jacobian and finite bounded rotations. A frozen plan records the completed V9 control, the exact source scene, implementation hashes and comparison method before starting V10. The comparison independently requires identical limb/body-preprocessed arrays, compiled contact specifications, scene context and shared objective/budget settings.

Both runs use the same six-second development actor, floor-valid object path, material grip points, 38 finger controls, body controls, sampled collision vertices, three outer stages and 100 iterations per stage. Different line-search behavior can change objective evaluations and runtime; equal iteration limits do not imply equal computational work. This remains one previously studied example, not a new independent action or held-out test.

## Result

The matched-input checks pass, including exact equality of all saved preprocessed motion arrays. V10 completed 323 objective evaluations in 168.8 seconds with approximately 1.062 GiB peak process-tree RSS. Its independent exported-skin audit samples 717 poses, including 244 samples per hand across `[60,121)`.

| Dense/exported measurement | V9 control | V10 scaled fingers |
| --- | --- | --- |
| Largest finger edit | 0.806 degrees | 8.662 degrees |
| Left grip maximum error | 24.186 mm | 20.102 mm |
| Right grip maximum error | 24.964 mm | 17.797 mm |
| Each hand within 30 mm | 244/244 | 244/244 |
| Each hand within 5 mm | 0/244 | 0/244 |
| Maximum skin/object penetration | 31.703 mm | 18.444 mm |
| Left palm maximum normal error | 12.281 degrees | 10.759 degrees |
| Right palm maximum normal error | 14.341 degrees | 9.335 degrees |
| Left palm peak speed near release | 0.372 m/s | 0.298 m/s |
| Right palm peak speed near release | 0.606 m/s | 0.556 m/s |
| Peak sampled joint acceleration | 46.388 m/s² | 44.579 m/s² |

All 38 finger edit bounds and the ten fixed fingertip rotations pass independent GLB checks. No sampled actor/floor penetration appears, and the authored object retains its floor clearance. A new Godot import passes all 360 actor-frame observations for input and V10 candidate, across all 77 bones; maximum position error is below 0.41 micrometres. The V9 comparison reuses its existing import evidence rather than rerunning it.

The experiment supports parameter scaling as one contributor to the earlier weak use of finger controls. It does not solve grasp quality: both hands still miss the 5 mm point target throughout the sampled contact interval, and 18.444 mm penetration exceeds the unchanged 10 mm clearance screen. Both hands' maximum dense point errors occur at frame 120.75, between the final contact key and release event. The left normal still exceeds the solver's 10-degree target. Release speeds improve relative to V9 but remain above the unchanged input's approximately 0.139/0.146 m/s peaks.

Next work should address joint feasibility of contact and full-hand clearance, plus the whole release interval. Do not interpret improved optimization or passed edit budgets as anatomical validity, force balance, self-collision clearance, naturalness or release approval. V10 remains an experimental CLI option, with no Studio default change.

## Evidence

Local artifacts are `reports/sphere-finger-scaling-plan-v1`, `reports/sphere-floor-fit-v10`, its `-audit` and `-engine` directories, and `reports/sphere-finger-scaling-comparison-v1`. The comparison binds source, preprocessing, configurations, compiled constraints, dense audit, engine output and exported joint budgets. Fifteen focused software tests pass. Source and implementation snapshots are retained locally; generated payloads are excluded from Git.

No new checkpoint, training data, held-out trials or human-review observations were introduced. All project release capabilities remain unapproved.
