# Half-frame floor correction across the diagnosed population

This follows the [matched backpedal pilot](half-floor-pilot-v1.md) across all nine previously diagnosed root-only correction conflicts: backpedal on rigs 02/03, beckon on rigs 01/02/03, kneel on rig 01, tie shoe on rig 01, and exhausted walk on rigs 02/03. These are five development actions and three rigs, not held-out release cases or an action whitelist.

Each pair starts from the same latest verified clip in `reports/coupled-clip-sequence-v2`. Both methods revisit the first peak window selected by the earlier whole-clip study. They get at most six iterations, the same trust bounds and safeguard fractions, the original shared edit/contact/geometry budgets, and the same whole-clip export acceptance criteria. The only proposal difference is the additional half-frame floor rows. This controls iteration limits, not elapsed compute: half-frame derivatives add work.

The original backpedal / 02 pair is reused after verifying identical request, envelope, starting GLB and parameter hashes, source files and completed export evidence. Sixteen other method/case combinations are new. Every new rig/case receives three independent directional derivative checks and an actual serialized starting-geometry check before fitting. The implementation's local import closure and resource hashes are frozen before execution.

`study_half_floor_population.py` retains the full eighteen-output denominator, including execution errors and rejected corrections. Per-pair comparison includes both methods' scores and peaks, acceptance status, failing root centers, newly introduced failing centers, and preservation outcomes. A lower score cannot silently promote a rejected output. Six tests cover missing/duplicate results, unmatched starts, unfinished results, execution failure retention, and lower-score geometry/center regressions.

## Completed comparison

All eighteen method/case results are accounted for, with zero execution failures. All independent preservation checks pass. Actual Godot checks cover 6,360 actor-frames, of which 5,760 are new and 600 are reused pilot evidence. All eight new derivative preflights pass; maximum directional error is 1.35e-7 against the unchanged 2e-4 threshold. Source, implementation, resource, completion, output and engine-input bindings are rechecked in `reports/half-floor-population-v1/verified-summary.json`.

| Action / rig | Key-only whole-clip score | Key-plus-half score | Accepted numerical correction: keys / halves |
| --- | ---: | ---: | --- |
| Backpedal / 02 | 44.543349 | 44.015960 | No / Yes |
| Backpedal / 03 | 26.307139 | 26.307139 | Yes / Yes |
| Beckon / 01 | 3.038675 | 3.038675 | No / No |
| Beckon / 02 | 0.184187 | 0.184187 | No / No |
| Beckon / 03 | 109.587738 | 109.587738 | No / No |
| Kneel / 01 | 0.967605 | 0.967605 | Yes / Yes |
| Tie shoe / 01 | 0.726666 | 0.726666 | No / No |
| Exhausted walk / 02 | 73.605386 | 73.099894 | No / Yes |
| Exhausted walk / 03 | 99.015166 | 99.015166 | No / No |

The half-floor method improves beyond key-only proposals in **2/9 cases** and reaches the same objective in seven. It passes the predeclared improvement threshold in four cases versus two for the key-only method. Small reductions in the two latter beckon cases remain below that threshold and are retained as rejected corrections. Matching scores do not imply byte-identical joint animation.

For exhausted walk / 02, the score decreases 0.687% and its root peak falls 7.186115 → 7.144472 m/s². Its forty failing centers remain. Across all nine pairs, no method adds or removes a failing root center relative to its starting clip, and **none restores the original root peak**. The result supports a targeted proposal option for demonstrated floor blockers, not a default quality fix for arbitrary motions. No acceptance tolerance was widened.

## Developer review

The immutable local package `reports/rig-jobs/half-floor-review-v1` contains all nine cases and 36 versions: raw rig transfer, the common starting clip, key-only attempt and half-floor attempt. Rejected corrections stay visible and labeled; the default preview is the common starting clip. Each case includes a correction-window shortcut, root/contact sidecars, method audits, engine evidence, source attribution and a ZIP. All 256 packaged file hashes, nine archive contents and local route mappings pass verification.

In Studio, open **Characters → Review corrected motions → Floor constraint comparison**. Compare the versions at normal speed, then at the same frame. Existing developer feedback binds notes to the catalog, clip hash and frame range; no ratings are prefilled. Live browser validation was unavailable, so it is not claimed. Package and source checks do not establish visual quality.

Adding the menu entry exposed source-template drift: a rebuild would have removed previously shipped scene-region controls and grip picking. Restoring those source sections from the existing page preserves their behavior. The rebuilt page now differs from the prior page only by the new review option and catalog mapping, after normalizing line endings. A build/source equality regression and explicit scene-feature preservation check were added. Twenty-two focused Python tests pass, along with offline Node checks for geometry, grip picking, region editing and developer feedback. The existing numerical implementation is unchanged from the verified pilot.

Further isolated root-score tuning is not a substitute for evaluating the animation workflow. The next work should use this reviewable evidence alongside the outstanding scene/object/partner failures and broader authoring requirements. Human review, continuous-time geometry, held-out validation and all fourteen release capabilities remain open.

## Reproduction

With the provisioned runtime and retained parent/pilot artifacts available, choose a fresh output directory:

```powershell
.venv\Scripts\python.exe scripts/study_half_floor_population.py prepare reports/half-floor-population-new --parent reports/coupled-clip-sequence-v2 --pilot reports/half-floor-pilot-v1
.venv\Scripts\python.exe scripts/study_half_floor_population.py run reports/half-floor-population-new
```

The runner refuses to overwrite a previous attempt. Starting motion, solver proposals, all exported outputs, independent audits and actual engine results remain local under ignored `reports/`. No human, held-out or release approval follows from this experiment; full-project capability statuses remain unchanged.
