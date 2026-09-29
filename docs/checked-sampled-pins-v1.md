# Contact fitting on the export sampling clock

Stationary material-point positions can now be fitted at every quarter-frame, matching the independent export audit and the existing rate/floor objectives. The previous method fitted position only at native keys. A regression test demonstrates why this matters: root translation can cancel a rotating point's displacement at both keys while the interpolated point misses the target by more than 12 cm.

The optional `export_point_position_guard` replaces the native point merit, without double-counting it. It retains the 5 mm tolerance, fixed material vertices, inclusive intervals, all skin influences, equal weighting between regions, and averaging across each region's samples. Every disjoint interval is represented, including repeated use of one vertex. Multipliers and diagnostic errors use the new sample clock. Regional surface fitting and compiled release guards are explicitly excluded from this option rather than silently losing their constraints. Default Studio behavior remains unchanged.

## Matched result: sampling alone is insufficient

The same checked get-up source, pin, window, floor bounds, rate ceilings, edit limits, two stages and 60 iterations per stage are retained. The previous candidate is a comparison, not the initializer.

| Export measurement | Native-key pin objective | Quarter-frame pin objective |
| --- | ---: | ---: |
| Maximum requested pin error | 5.36849 mm | 5.78466 mm |
| Samples exceeding 5 mm | 8 / 81 | 15 / 81 |
| Maximum floor depth | 2.19759 mm | 2.19082 mm |
| Per-time added floor depth | 0 | 0 |
| Hold acceleration excess | 5.55196 m/s² | 5.07631 m/s² |
| Release speed excess | 0.0124789 m/s | 0.0135039 m/s |
| Release acceleration excess | 0.398817 m/s² | 0 |

The sampled objective removes the clock mismatch but does not improve the overall contact result at this budget. The candidate remains unapproved, with contact, rate and inferred-support failures. Both stages stop at their iteration limit; final projected gradient infinity norm is about 532. The second stage's fitted maximum pin error is 5.78470 mm, agreeing with the decoded export to within 4.90e-8 m. The residual failure is therefore visible to the fitter itself, not hidden by export sampling.

All 717 decoded floor samples preserve the source's per-time depths, and all 160 outside-window samples preserve the source within numerical tolerance. The source/candidate floor proxies agree with decoded full-skin heights within 1.36e-7 m. Actual Godot playback passes 407 pose observations, two requested-boundary markers, forward/reverse playback, four callback-mutation rejections and unloading. Maximum actor matrix component error is 1.39e-6. Four download routes resolve through direct handler checks; no HTTP/browser rendering or human review was performed.

Twenty-nine distinct focused Python tests pass. These cover rotation arcs between correct endpoints, multiple pin intervals, position gradients and multiplier updates, fixed-parameter integration without duplicate penalties, unchanged defaults, floor/rate objectives, immutable inputs and mesh binding, export audits, and rejection of invalid budgets before job creation.

```powershell
.venv\Scripts\python.exe scripts/study_checked_point_scaling.py guarded-fit-check-v1 reports/contact-jobs/studio-sampled-pins-v1 reports/contact-jobs/studio-floor-guard-v1 --floor-guard --sampled-pins
```

Use a fresh output directory. Completed evidence is retained under `reports/contact-jobs/studio-sampled-pins-v1` and `reports/studio-sampled-pins-v1`.

## Completed convergence study

With position, rate and floor sampling now aligned, a separate experiment tests a larger numerical budget: four stages, at most 120 iterations each. It starts from the original checked source and retains every physical/contact threshold. This is motivated by the measured iteration-limit stops and large residual gradients; it is not assumed to fix feasibility.

```powershell
.venv\Scripts\python.exe scripts/study_checked_point_scaling.py guarded-fit-check-v1 reports/contact-jobs/studio-sampled-pins-convergence-v1 reports/contact-jobs/studio-sampled-pins-v1 --floor-guard --sampled-pins --stages 4 --iterations 120
```

The selected stage/iteration counts are validated and written into the study protocol and fitting options. The [longer run has now completed](checked-contact-convergence-v1.md): it reduces pin failures from 15 to 1 but retains a 1.65 micrometre point violation and a small release-speed violation. Full-floor and engine checks pass; the candidate remains unapproved. No release capability has been approved.
