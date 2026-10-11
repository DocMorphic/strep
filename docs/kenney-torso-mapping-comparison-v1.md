# One torso mapping change: development comparison

Changing the target `Chest` role from `UpperChest` to `Chest` does **not** repair
this transfer. Keep the existing baseline profile. The alternative has 307
floor-failing keys versus 266 for the baseline, with 41 new failures and no
previous failures repaired at the declared Y=0 plane / 5-mm screen.

The study retained the original Kenney derivative, seven original SOMA clips,
seed 77, 30 FPS and all 1,020 original keys. Only one mapped target node changed;
root offset, model/checkpoint, motions, other roles and the leg scale were fixed.
This is a development counterfactual, not a newly approved anatomical mapping
or a held-out trial. Original baseline exports and raw motions were retained.

| Motion | Baseline peak depth (mm) | Alternative peak depth (mm) | Baseline failing keys | Alternative failing keys |
| --- | ---: | ---: | ---: | ---: |
| Jump/land | 0 | 0 | 0/120 | 0/120 |
| Crawl | 263.015 | 313.642 | 120/120 | 120/120 |
| Dance | 0 | 0 | 0/150 | 0/150 |
| Wave | 0 | 0 | 0/120 | 0/120 |
| Kick | 49.728 | 49.655 | 14/120 | 14/120 |
| Get-up | 662.041 | 641.670 | 105/180 | 144/180 |
| Run/roll/stand | 978.276 | 1,069.175 | 27/210 | 29/210 |

The alternative reduces the synthetic neutral chest mismatch from about 643 mm
to 343 mm. It leaves the head/hand mismatch at about 648–663 mm. A lower get-up
peak therefore accompanies **39 more** failing keys; peak depth alone would be
an inadequate decision metric. The roll gains two failures and a larger peak.

Seven exports complete. A separate replay checks all original keys, both
baseline/alternative whole-mesh floor traces, preserved original mesh/material/
skin payloads and the alternative root sidecar. It uses row-wise skin products
instead of the exporter's skin einsum, but shares the GLB reader and animation
sampler. Maximum alternative serialized vertex error is approximately
**0.569 micrometres**. Source/model FK, contact intent, physical balance,
continuous time, engine playback and human quality are not independently
verified by this replay. Producer and replay resource records pass independent
recorded-policy replay with the unchanged admission limits.

To reproduce with retained inputs, copy the explicit baseline profile and change
only `mapping.Chest` to `Chest`; retain the original `character_sha256`. Export
each original motion into a fresh folder using `scripts/retarget_rig.py transfer`
with `--fps 30`. Compare baseline/alternative GLBs with
`scripts/rig_floor_comparison.py` at the original float32 export keys, declaring
`--floor-y 0 --tolerance 0.005`. Treat its `source` field as the baseline target
character in this paired experiment, not as the original SOMA body.

Local outputs are retained in `reports/kenney-torso-mapping-comparison-v1` and
`reports/kenney-torso-mapping-comparison-replay-v1`, with guarded job/resource
records under `reports/central-hand-physical-v1`. Generated/downloaded payloads
remain excluded from Git. The alternative is **not promoted**. The
[reference diagnosis](kenney-reference-diagnostics-v1.md) and
[original source/target floor failures](kenney-source-target-floor-v1.md) remain
the basis for the next work: explicit whole-body support targets, bounded joint
and root corrections, and comparisons that also measure contact loss, motion
changes and cleanup time. No release threshold or approval changes.
