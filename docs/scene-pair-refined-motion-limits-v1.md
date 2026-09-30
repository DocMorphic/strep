# Motion restrictions and a fresh peak measurement

The refined fixed-witness model still predicts substantial overlap when motion restrictions are removed. A fresh mesh query confirms that its prediction differs from actual mesh depth, but the tested proposal remains colliding and violates the original acceptance conditions. It is a rejected diagnostic, not an animation improvement for publication.

## Matched affine comparison

Reference: `trust_5_weaker_penalty` in `reports/scene-pair-refined-trust-v1`. All variants retain 168 controls, a five-degree native edit budget, a five-degree trust radius, protected keys, scale 0.025 and regularizer 0.000005. The baseline is reused only after independently rechecking its controls against the bound tightened conditions; its recorded solver duration belongs to the earlier solve.

| Conditions omitted | Predicted peak, mm | Original speed failures | Acceleration | Angular speed | Angular acceleration | Surface distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| None | 22.231453 | 0 | 0 | 0 | 0 | 0 |
| Positional rates | 22.200974 | 345 | 297 | 0 | 0 | 0 |
| Angular rates | 22.198506 | 0 | 0 | 584 | 112 | 0 |
| All motion rates | 22.140516 | 262 | 287 | 687 | 206 | 0 |
| Motion rates, local plane caps and distance bounds | 21.822817 | 1494 | 548 | 1027 | 418 | 406 |

Every new solve passes its declared diagnostic subset's numerical checks. None passes all original conditions. The last variant retains a global source-peak plane cap and exceeds the original local plane caps by up to 11.391412 mm. Native edit-budget failures remain zero. Removing these conditions does not establish nonlinear infeasibility, nor justify weakening animation acceptance.

## Fresh geometry at one time

The final, deliberately rejected proposal was exported and measured at source sample 34, time 1.675 s. Both directional full-mesh vertex queries were performed with fresh nearest-surface evaluation.

| Measurement at that time | Peak depth, mm |
| --- | ---: |
| Original source mesh | 22.568796 |
| Affine retained-witness prediction | 21.822817 |
| Decoded nonlinear retained witnesses | 23.801354 |
| Fresh decoded mesh queries | 20.917717 |

The fresh depth decreases by 1.651080 mm at this time, but remains above the 5 mm screen. Retained witnesses and affine approximation both differ from fresh geometry. This supports checking updated geometry in further proposals; it does not show that doing so will solve the interaction.

The decoded exports have 1,139 and 771 positional-rate failures for actors A and B. Their original local plane-cap excess reaches 12.411906 mm, and retained surface-distance excess reaches 34.213802 mm. Original-bin angular checks are also retained in `decoded.json`. No full-timeline fresh geometry, engine validation, publication or quality approval was performed for this candidate. The full animation's collision maximum cannot be inferred from one sample.

## Reproduction and evidence

```powershell
.venv/Scripts/python.exe scripts/study_refined_surface_limits.py reports/scene-pair-refined-trust-v1 reports/scene-pair-refined-motion-limits-v1 --variant trust_5_weaker_penalty --profile motion
.venv/Scripts/python.exe scripts/audit_refined_peak_prediction.py reports/scene-pair-refined-motion-limits-v1 reports/scene-pair-refined-peak-v1 --variant edit_and_global_peak_only
```

Both workers completed. Inputs, parent evidence, controls, exports and implementation snapshots remain bound locally under ignored `reports/`. Twenty-four focused tests pass, covering declared omissions, cached-reference validation and changed/incomplete diagnostic evidence. The peak result explicitly records `full_timeline_geometry_checked: false`, `accepted_for_publication: false` and `quality_approved: false`.

Next compare proposals using refreshed nonlinear geometry or a changed approach path while retaining original contact, edit and motion acceptance checks. All 14 release capabilities remain unapproved.
