# Contact residual scaling comparison

The saved checked-contact fitter misses a fixed left-foot pin by 99.58 mm despite passing necessary endpoint travel checks. Its numerical point violation and the exported error agree. The original source reaches 144.25 mm from the pin at native keys, so this request requires a substantial motion change. Both retained default stages reach their 60-iteration limit.

The fitter measures explicit point violations in metres, while exported point-rate inequalities use dimensionless source-relative residuals. This experiment divides the signed point violation by its unchanged 5 mm tolerance in both the augmented objective and multiplier updates. This preserves the feasible set but **changes the relative objective weighting**: at the first stage, squared point penalties increase by 40,000. It is an experiment in priorities, not a claim that normalization alone repairs the solver.

`authored_point_scaling="tolerance"` is opt-in. The default remains `"metres"`, including Studio's saved-check action and the legacy Apply method. The option, source snapshots, saved check revision, solver settings and implementation are recorded. The source, held window, material vertex, target, rate ceilings, hard edit budgets, two stages and 60 iterations per stage match the retained control. No candidate becomes the next initializer.

## Measured outcome

| Decoded export measurement | Metre residual | Tolerance residual |
| --- | ---: | ---: |
| Maximum requested pin error | 99.5805 mm | 5.28119 mm |
| Contact samples exceeding 5 mm | 81 / 81 | 6 / 81 |
| Maximum full-mesh floor penetration | 10.3989 mm | 83.2522 mm |
| Hold acceleration excess | 0.0450445 m/s² | 0 |
| Approach acceleration excess | 0 | 2.33660 m/s² |
| Release speed excess | 0.00132512 m/s | 0.00817944 m/s |
| Objective evaluations | 307 | 133 |

The new candidate also exceeds approach speed by 0.0142309 m/s and release acceleration by 0.0174169 m/s². Both stages reach their iteration limit. Floor penetration in the unchanged source is 2.33564 mm. The improved pin position does not compensate for these regressions, and the candidate remains rejected.

The new floor peak occurs at frame 84, before the pin starts: vertex 8844, dominated by `LeftToeBase`, moves from 38.0316 mm above the floor to 83.2522 mm below it. That vertex is absent from the 610-point fitting subset, but the subset already measures 82.4112 mm penetration at the same frame. Missing mesh coverage is therefore not the main explanation for this large regression: the existing soft collision term permits an almost equally large observed violation. The control's floor peak is at frame 90 on a vertex dominated by `LeftLeg`.

The audit decodes 717 quarter-frame times using all eight skin influences. All 160 outside-window samples remain unchanged within numerical tolerance, with maximum skin difference 8.94e-8 m. Actual headless Godot playback passes 407 pose observations, two requested-contact markers, forward/reverse playback, four callback-mutation rejections and unloading. Maximum actor matrix component error is 1.30e-6. These establish export fidelity only.

Nineteen focused Python tests pass. They include an actual fitter-closure test with fixed parameters, verifying unchanged default behavior and consistent scaling through both multiplier stages. Tests also cover invalid options, per-point rates, immutable checked plans, inferred support handling and the decoded multi-interval audit. No browser rendering or human review was performed.

Run the comparison against a retained default job with:

```powershell
.venv\Scripts\python.exe scripts/study_checked_point_scaling.py guarded-fit-check-v1 reports/contact-jobs/studio-point-scaling-v1 reports/contact-jobs/studio-checked-fit-v1
```

The output folder must be new; the command does not overwrite prior trials. Local evidence is retained under `reports/contact-jobs/studio-point-scaling-v1` and `reports/studio-point-scaling-v1`. The engine ran successfully on the first attempt; report verification initially lacked the verifier's required `request.json` filename. The original failed finisher and engine outputs remain intact. A separate resume script supplied the matching request and verified those existing engine results without regenerating motion or rerunning the engine.

**Decision:** retain the default and this failed comparison. Contact weighting alone is insufficient. The next correction must preserve floor geometry and rate limits while reducing pin error; it must retain and audit failed proposals rather than trade them silently. No release capability is approved by this study.
