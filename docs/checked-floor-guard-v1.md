# Full-mesh floor preservation during checked contact fitting

The previous tolerance-scaled pin fit reduced contact error but drove a toe area 83.25 mm into the floor. Its existing fitting subset already saw 82.41 mm penetration. Increasing mesh samples alone could not address that tradeoff, because the soft collision cost permitted a large known violation.

An optional `export_floor_guard` now adds one augmented floor inequality at every quarter-frame of the clip. It computes the minimum height over the **full mesh with all skin influences**, using the same differentiable native-export interpolation as the rate objectives. Each time retains its original source depth; a clear source sample allows zero penetration. This is a per-time reference, so new penetration cannot hide below a larger original peak elsewhere in the clip.

The signed height violation is divided by 5 mm for numerical scaling, with initial penalty 10 and the existing factor-four outer update. The 5 mm value is not an allowed floor-depth increase. No extra depth allowance is added. World-Y sparse skin evaluation runs in time chunks to avoid constructing full eight-influence XYZ tensors. The source floor bounds and accepted-stage diagnostics are recorded. Augmented objectives remain best-effort; independent export audits determine whether the candidate actually preserves the floor.

## Matched retained result

The same source get-up clip, fixed left-foot point, interval 90–110, held window 20–159, rate ceilings, tolerance-scaled contact objective and hard edit bounds are retained. The trial uses the same two stages of at most 60 iterations. The earlier candidate is a comparison, never the initializer.

| Export measurement | Without new floor guard | With floor guard |
| --- | ---: | ---: |
| Maximum full-mesh floor penetration | 83.2522 mm | 2.19759 mm |
| Maximum requested pin error | 5.28119 mm | 5.36849 mm |
| Pin samples exceeding 5 mm | 6 / 81 | 8 / 81 |
| Approach acceleration excess | 2.33660 m/s² | 0 |
| Hold acceleration excess | 0 | 5.55196 m/s² |
| Release speed excess | 0.00817944 m/s | 0.0124789 m/s |

The guarded candidate has **zero measured added depth at all 717 decoded export times**, compared with the source at each corresponding time. The source's maximum depth is 2.33564 mm. The audit records raw excess and separately counts values exceeding a 1 micrometre export-precision budget; this result is zero even before that classification budget.

The candidate still fails contact accuracy, release acceleration (excess 0.398817 m/s²), hold acceleration, several inferred-support checks, and the existing pose-change screen. It remains unapproved. Both stages reach their iteration limit, with 139 objective evaluations and about 188 seconds for fitting and evaluation on the development machine. Default Studio behavior is unchanged; the new floor option is not automatically enabled or presented as a quality fix.

All 160 outside-window samples preserve the source within numerical tolerance. The floor proxy agrees with independently decoded full-mesh minimum heights to 1.36e-7 m for the source and 1.45e-7 m for the candidate. Actual headless Godot playback passes 407 pose observations, two requested-boundary markers, forward/reverse playback, four callback-mutation rejections and unloading; maximum actor matrix component error is 1.41e-6. Four download routes resolve through direct handler verification. No HTTP/browser rendering or human review was performed.

Thirty-eight focused Python tests pass, covering between-key penetration, per-time source-depth preservation, gradients, multi-interval export audit, clock mismatch, existing checked-plan/API behavior and character mesh tampering. Saved timing checks now bind the mesh hash explicitly during guarded-job validation and before/after execution, closing a provenance gap that recomputing a single point's rate reference alone could miss.

```powershell
.venv\Scripts\python.exe scripts/study_checked_point_scaling.py guarded-fit-check-v1 reports/contact-jobs/studio-floor-guard-v1 reports/contact-jobs/studio-point-scaling-v1 --floor-guard
```

Use a new output directory for reproduction. Local numerical, export, comparison and engine evidence remains under `reports/contact-jobs/studio-floor-guard-v1` and `reports/studio-floor-guard-v1`. Both earlier failed controls remain immutable.

Next address the remaining point/rate conflicts while retaining this per-time floor constraint. Point positions are currently fitted at native keys while the audit and rate/floor objectives cover quarter-frames; the contact sampling must agree before interpreting a near-threshold native fit as sufficient. No release capability is approved, and finite sampling does not certify continuous collision avoidance, anatomy, balance or naturalness.
