# Export margins on refined paired curves

The previous nine-knot proposals passed affine checks but every exported fraction failed an original motion limit. This experiment measures export error on that same refined representation, then tightens proposal radii. Final acceptance limits remain unchanged.

## Reproduction and evidence

Run from the project root with the existing local assets and completed parent studies:

```powershell
.venv/Scripts/python.exe scripts/study_scene_pair_export_reserve.py reports/scene-pair-expanded-fit-v1 reports/scene-pair-refined-reserve-v1 --refined-audit reports/scene-pair-expanded-refinement-export-v1
.venv/Scripts/python.exe scripts/audit_refined_pair_geometry.py reports/scene-pair-refined-reserve-v1 reports/scene-pair-refined-reserve-geometry-v1 --trial 1
```

Outputs require fresh destinations. Both commands are complete; the second is a separate full-mesh and engine audit. Results are local ignored artifacts, not included in the public source snapshot.

The runner binds the completed refined export audit, proposal, original study, method snapshots and source assets. It reconstructs the nested nine-knot/168-control layout, checks native key eligibility and original quaternion samples, and retains the original positional and angular policies. Original five-knot bins remain the acceptance bins. Changed actor order, control counts, knots, limits, constraint kinds or physical objective scaling are rejected.

Per-row reserves equal twice the largest positive decoded-norm minus affine-norm error across the five previous refined exports. Edit budgets are not tightened. This is an empirical proposal margin, not a certified bound for unseen directions. The inherited scale 0.025 and regularizer 0.00002 keep the original physical objective unchanged.

| Motion row | Maximum reserve |
| --- | ---: |
| Speed | 0.000039324 m/s |
| Acceleration | 0.003184353 m/s² |
| Angular speed | 0.000085712 rad/s |
| Angular acceleration | 0.007991584 rad/s² |

The solve completes in 48 iterations / 26.67 seconds, with no affine hard-check failures. Predicted full-step peak penetration is 22.476548 mm, versus 22.568796 mm initially. These are affine predictions, not the full-mesh result.

## Decoded exports

| Fraction | Positional failures | Angular exceedances | Retained surface checks | Preliminary result |
| --- | ---: | ---: | --- | --- |
| 1 | 0 | 0 | Fail | Reject |
| 1/2 | 0 | 0 | Pass | Proceed to full audit |
| 1/4 | 1 | 0 | Pass | Reject |
| 1/8 | 1 | 0 | Pass | Reject |
| 1/16 | 2 | 1 | Pass | Reject |

The full step exceeds retained depth and distance caps by 1.376819 and 1.639803 micrometres, respectively, above the unchanged one-micrometre comparison tolerance. The half step stays below eight nanometres of retained-cap excess. Shrinking a fraction still does not guarantee a passing float32 export.

The half step reconstructs both reviewed GLBs exactly. Independent scalar quaternion replay checks 45,122 angular observations against original bins with no exceedances. Godot 4.7.2 imports four original/candidate clips, checking 444 actor frames and 77 bones per actor; maximum position error is 5.366925e-7 m and maximum basis-element error is 6.565566e-7. Neither engine import nor retained witnesses prove collision clearance.

The separate audit evaluates full partner meshes and floors at all 148 original sample times. Its completed result and the subsequent separate Studio comparison are described below. This experiment has not consumed held-out prompts, supplied human review, or approved any release capability.

## Packaging preparation

`assemble_scene_pair_reserve.py` now retains the bound refined matrix and curve descriptions instead of substituting the original coarse matrix. It checks unchanged source rows, caps and constraint kinds, and rejects solver controls that do not match the refined width. An optional `--prepared` points to a byte-identical prepared request copy for a separate review job; changed request bytes are rejected. Earlier comparisons remain intact.

The packaging change alone did not publish a candidate: completed mesh evidence and independent refined-layout replay were still required. Twenty-eight assembly and geometry-summary tests pass, including complete synthetic refined assembly and malformed evidence cases. [Windows and Linux source checks](https://github.com/DocMorphic/strep/actions/runs/36709523306) passed for the preceding export-margin commit `c16fc42`; that hosted result does not cover this subsequent packaging change.

The separate immutable review input is prepared with:

```powershell
.venv/Scripts/python.exe scripts/copy_prepared_pair_review.py reports/paired-edit-jobs/expanded-window-v1 reports/paired-edit-jobs/refined-reserve-v1
```

This copies only the declared request, prepared state, scene, two actors and implementation snapshots. It verifies their hashes and all declared original inputs before and after copying. It rejects existing destinations, changed evidence and paths outside the source. Solver outputs, prior reviews and publication state are not inherited. `review-origin.json` records the copied identities without implying approval.

The real copy reloads both actors successfully under the original 72-control request, which remains byte-identical. The nine-knot/168-control refinement is applied separately from the bound proposal metadata. The earlier review still reports complete. Eight copy integrity tests pass; [hosted source checks](https://github.com/DocMorphic/strep/actions/runs/36709983220) passed for packaging commit `7af6def`, before this copy helper was added.

## Completed full-mesh audit and publication

The worker finished with exit 0 after all 148 times and 296 directional full-mesh queries. Peak penetration changes from **22.568796 to 22.522270 mm**, an improvement of **0.046526 mm**. The same 37 sample times still exceed 5 mm. Maximum per-time cap excess is 7.537666e-9 m; floor increase is zero. The unchanged local checks pass, but the result is nowhere near collision clearance.

Independent all-trial replay now reconstructs the explicitly bound refined layout while retaining the original five-knot rate bins. It rejects incomplete, extra, nonfinite or incorrectly ordered controls. A model-free integration fixture checks real refined GLB reconstruction and original-bin rate reports; it makes no mesh-quality claim. Development occurred in an isolated checkout, with integration into the active checkout only after the geometry worker exited.

The completed evidence was assembled with the byte-identical new review request, then passed through the ordinary Studio job:

```powershell
.venv/Scripts/python.exe scripts/assemble_scene_pair_reserve.py reports/scene-pair-refined-reserve-v1 reports/scene-pair-refined-reserve-geometry-v1 reports/scene-pair-refined-reserve-completed-v1 --prepared reports/paired-edit-jobs/refined-reserve-v1/request.json
.venv/Scripts/python.exe scripts/scene_pair_job.py reports/paired-edit-jobs/refined-reserve-v1 --completed-study reports/scene-pair-refined-reserve-completed-v1 --completed-engine reports/scene-pair-refined-reserve-geometry-v1/engine --label "Paired correction with refined curves"
```

The job completes with ten exact export reconstructions, 225,610 positional observations, 4,287 source skin witnesses, passing independent selected-clip angular replay, and reuse of the four exact Godot-imported clips. Native preview skin error is at most 3.297651e-7 m. The new collection is `scene-region-jobs/paired-refined-reserve-v1`, labelled **Paired correction with refined curves · Before / After**. The earlier two publications and their bound files remain intact.

Direct discovery/source handlers and all six scene/GLB routes return the expected data and bytes. Evidence is retained in `reports/scene-pair-refined-reserve-studio-v1.json`. This is not HTTP or rendered-browser testing. The full minimal source suite passes **373 tests with four optional skips**. No release capability is approved.

The next correction study needs materially larger clearance gains with source-relative motion/contact protections and updated partner geometry. Further tiny local steps must not be mistaken for a solved interaction.

## Source validation

The minimal dependency suite passed 345 tests with four optional skips after adding the reserve input checks. A subsequent focused run covering geometry reconstruction and refined input policies passed 34 tests, including three new cases for original models and refined curves. No browser rendering or animator approval is claimed.
