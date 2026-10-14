# Separate generation and rig-transfer floor diagnostics

Seven existing development actions show floor errors in both the original SOMA mesh and the transferred Kenney character. Transfer substantially increases the measured errors in ground movement, getting up and rolling. The next correction work must examine target anatomy/reference axes and body-contact-aware retargeting, alongside the original model's ground-contact errors.

`scripts/native_key_floor_comparison.py` provides a reusable read-only comparison. It checks every triangle-referenced vertex at every original native key, requires exact shared clip clocks and explicit animation selections, records deepest vertices and dominant skin influences, and keeps the unchanged ground Y=0 / 5-mm diagnostic. The caller supplies the source-to-target leg/unit scale; it is reported separately from native source depth.

```powershell
python scripts/native_key_floor_comparison.py source.glb target.glb fresh-output --source-index 0 --target-index 0 --scale 1.3262414266628333
```

Different meshes, body proportions and mappings prevent causal isolation from this comparison alone. A larger transferred depth does not prove one particular mapping is wrong. Dominant skin influences are software identities, not reviewed anatomical patches. Native-key measurements are not the denser 2,017-time correction screen, continuous collision certification, engine playback or human realism ratings.

## Seven-action source/target evidence

Both populations contain all 1,020 native keys across seven unchanged seed-77 development clips. No generation or training is run; reserved release cases are unused.

| Action | Keys | Source peak depth (mm) | Scaled source peak (mm) | Target peak depth (mm) | Target deepest influence |
| --- | ---: | ---: | ---: | ---: | --- |
| Jump and land | 120 | 18.839 | 24.985 | 0 | — |
| Crawl | 120 | 89.508 | 118.710 | 263.015 | RightHandIndex3 |
| Dance | 150 | 14.428 | 19.135 | 0 | — |
| Wave | 120 | 11.617 | 15.407 | 0 | — |
| Kick | 120 | 8.867 | 11.759 | 49.728 | LeftFoot |
| Get up | 180 | 146.983 | 194.935 | 662.041 | Head |
| Run, roll and stand | 210 | 70.498 | 93.497 | 978.276 | Head |

Peak source and target depths may occur at different times. The complete per-time arrays remain available. At the target roll peak, scaled source penetration is zero; maximum same-time target-minus-scaled-source depth is 978.276 mm. For getting up that maximum is 488.298 mm. The source kick's deepest influence is RightToeBase, while the target peak is LeftFoot. These are concrete differences to investigate, not proof that generation or transfer alone causes every failure.

The first comparison finishes in 32.407 seconds with 50 resource observations. A fresh execution through the public helper reproduces every summary, native clock, minimum height, vertex identity and dominant joint array exactly: 22.250 seconds/40 observations, with no additional generation or engine runs. Both resource-policy traces replay. Fifty-two related checks pass, including ten new shared-clock, animation-index, scale, complete-population and immutable-input checks. The existing explicit-plane/clock API and all its tests remain intact. Final validation takes 8.078 seconds/26 resource observations, all replayed. The final distinct native-key result schema passes all ten new checks in 5.079 seconds/23 observations, and its fresh seven-action replay remains exact.

## Kick continuation and its limit

A separate original-bound surface continuation tests the existing paired component repair on the stored-feasible kick. It preserves the root and endpoints, four left-leg rotation permissions, 72 controls, original source-rate arrays, 107,527 native rows, one-neighbor/64-component envelope, 30-degree track bounds and 220-mm joint displacement cap.

One surface iteration checks six proposal fractions, with at most four repair stages and sixteen probes per stage. The accepted fraction is 1/32, with 24 scalar corrections rather than the original 18. Intended and saved motion pass every original condition. Complete 2,017-time floor clearance improves from 47.353661 to 47.229222 mm: **only 0.124439 mm**, with 232 failing times unchanged. This is a reproducible small step, not a usable floor correction. The original remains selected.

The study takes 575.000 seconds/585 resource observations. Fresh reconstruction reproduces all eight returned GLBs and complete controls/worlds/residual/cap/scale/clock arrays exactly. A new complete final floor query matches every saved sample: 45.625 seconds/63 observations. Internal motion-only storage neighbors are not separately geometry-replayed. The initial clock-mismatch pilot and replay API-call error are retained, with 28 and 24 resource observations respectively.

## Hosted compatibility and retained records

At `471f5a6`, both OS pass contact/rig and game-package jobs, but both lineage jobs fail because two deliberately mocked package reports omit the newly required `active_policy` artifact. Their fixtures now include the actual producer's explicit policy field; runtime policy checks stay intact. All 35 lineage checks pass locally in 352.735 seconds/366 resource observations, with a complete resource-policy replay. This source change requires its own hosted outcome.

Local immutable records remain under ignored `reports/kick-component-surface-v1`, `v2`, `reports/kick-component-surface-replay-v1`, `v2`, `reports/source-target-floor-attribution-v1`, `v2`, `reports/native-key-floor-validation-v1`, `reports/native-key-floor-replay-v2` and `reports/lineage-active-policy-validation-v1`. The attribution's first worker fails on an unused import before computation; its 19-observation trace is retained and replayed.

No model/checkpoint, training admission, reserved evaluation, human cleanup result or release requirement changes. The entire-project goal remains active; four raw target floor failures and all fourteen capability approvals remain unresolved.
