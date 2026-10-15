# Public correction from original inputs and saved controls

The [affine-aware temporal model](native-affine-temporal-v1.md) can reconstruct a corrected seed without repeating pose optimization. The existing restoration command now accepts that explicit source form, evaluates bounded repeated proposals, exports complete native controls, and supports the existing fresh replay and verified continuation commands. This is a development correction workflow; it does not select an animation for release.

## Recipe and commands

`strep-native-key-interval-restoration-v1` recipes must contain exactly one source form: the existing `producer` declaration or this new `seed` declaration:

```json
{
  "schema": "strep-native-key-interval-restoration-v1",
  "seed": {
    "contacts": {"path": "contacts.json", "sha256": "<exact SHA-256>"},
    "geometry": {"path": "geometry.json", "sha256": "<exact SHA-256>"},
    "request": {"path": "original-authoring.json", "sha256": "<exact SHA-256>"},
    "controls": {"path": "native-controls.npz", "sha256": "<exact SHA-256>"}
  },
  "active_keys": [11, 12, 13],
  "iterations": 1,
  "trust": 0.01,
  "difference_step": 0.001,
  "backoffs": 4,
  "maximum_seconds": 600
}
```

Paths resolve relative to the recipe. Replace each digest placeholder with the actual lowercase 64-character SHA-256. The contacts file must still name the original source animation; a corrected seed does not become a replacement motion-rate reference. The request retains the original root, rotation permissions, edit window, frozen/boundary declarations and explicit pose/orientation settings. The NPZ must contain the original complete `times_s` and bounded finite `controls`. Unknown, missing, ambiguous or mistyped source declarations reject.

```powershell
python scripts/native_key_interval_restoration.py recipe.json fresh-job
python scripts/audit_native_key_restoration.py fresh-job fresh-replay --expected-result-sha256 <result-digest> --expected-request-sha256 <request-digest>
```

The command reconstructs and checks the native seed under `fresh-job/seed`, then runs the same complete edit/contact/geometry/rate checks and per-condition retention rules used by initializer-based jobs. Only a strictly improved proposal with no individual rate/floor/geometry regression and a passing decoded prefix may be retained. All trial clips, failed proposals and selection history remain archived; the original animation remains selected.

Seeded jobs also write `fresh-job/key-controls.npz`, containing the complete original native clock and final full controls, including all inactive keys and tracks. The standard fresh auditor reconstructs and checks this archive against the selected controls and original seed, in addition to every returned clip, complete observation arrays and retention decisions. The result/request schema and original initializer-based source form remain available. A successful numerical fixture is not animation-quality evidence.

After a complete matching replay, `native_key_continuation_job.py` can continue a seeded parent through its existing parent/result/request/replay declaration. The loader reconstructs original source inputs again and checks the saved final state without rebasing motion caps. Its historical `original_initializer` receipt field identifies the parent's canonical seed directory for seeded sources; fresh reconstruction directories do not change lineage. No new Studio selector is claimed.

The frozen continuation runtime also recognizes seeded parents. It verifies all four original input digests and freezes the parent's recorded methods, while initializer-based parents retain the existing initializer/archive reconciliation. Report containment and runtime/input/source validation remain unchanged. This makes the new source form usable by the existing frozen execution adapter without claiming new Studio controls.

The affine system and Jacobian are released before decoded candidate evaluation; saved copies remain on disk. This reduces overlapping temporary memory without removing solver conditions or changing acceptance. Existing limits remain at most four iterations, ten backoffs, 768 scalar controls, trust at most 0.02 and the declared finite time budget. No action-name whitelist is introduced.

## Validation and actual wider trial

The main batch passes **36 checks in 270.85 seconds**, covering the seeded public command, complete fresh replay, full control archive, verified public continuation/replay, changed input hashes, changed final controls and compatibility with the initializer-based workflow. Its guard completes in 287.250 seconds, peak sampled process-tree RSS 142,905,344 bytes; all 284 resource observations replay. Frozen runtime integration is added afterward and passes all **20 checks in 10.16 seconds**, including exact seeded-input binding and rejection of changed seed bytes. Its guard completes in 26.438 seconds, peak sampled RSS 90,284,032 bytes, with all 28 observations replayed. Numerical command methods are unchanged by that adapter addition. The source inventories validate at 509 Python/45 Node files and 73 Python/5 Node files in the focused suite; inventory validation is not execution of every listed file.

The real trial begins from the previously retained crawl half step, reconstructing complete controls against the unchanged original transfer. It expands the active interval to keys 4–19, all sixteen permitted tracks and the full existing 768-control budget. It performs one bounded public-command iteration with trust 0.02, difference step 0.001, at most four decoded backoffs and a 750-second proposal budget. The initial GLB matches the previously retained bytes exactly, and all four original rate-cap arrays match the prior reference.

The wider CPU study explicitly estimates and caps process-tree RSS at 768 MiB, with the same additional 600 MiB free-RAM floor and 15-second admission stability; its supervisor limit is 1,200 seconds. This larger profile is declared before execution because the control count expands from 144 to 768. Other CPU studies and model/full-body policies are unchanged. Exceeding a guard stops the owned process; it does not relax animation checks.

The complete affine system retains 482,068 norm rows with a 355,609-row protected prefix, all 123,630 original rate rows and all 2,829 floor times. The 768-column sparse Jacobian has 1,242,798 nonzeros. The primary solve reports `Solved` after 23 iterations; its optional smaller-norm proposal is not selected. Fixed and conservatively affine-box-passing conditions are accounted for separately; 8,635 active cones go to the solver, and every decoded condition still participates in evaluation and retention.

| Returned clip | Rate failures | Floor failures | Contact/edit/root checks | Worst normalized violation | Retained? |
| --- | ---: | ---: | --- | ---: | --- |
| Start | 377 | 8 | Pass | 372.604304 | Initial research seed |
| Full step | 391 | 5 | Fail | 349.450566 | No |
| Half step | 377 | 7 | Pass | 360.892750 | Research proposal only |
| Final | 377 | 7 | Pass | 360.892750 | Same half-step bytes |

The full step's three fewer failed floor samples cannot excuse its higher rate-failure count or its 5.002582-mm touch error against the unchanged 5-mm tolerance. The retained half step repairs **one previously failed floor sample**, preserves every individual rate/floor/geometry condition against worsening, and keeps contact at 4.868693 mm. Peak floor depth improves from 5.364233 to 5.273719 mm; squared positive violation decreases from 822,539.025 to 773,847.978. The other seven floor samples and 377 rate rows still fail, so the clip remains **rejected**, with the original selected and all approval flags false.

Production completes in 551.172 seconds with peak sampled RSS 498,225,152 bytes; all 542 resource observations replay with their archived bindings. The retained final GLB SHA-256 is `c85885035f68be5a1045d02b15ad39d66f344e61b4a88b4b77b10c95994de944`. Complete final native controls are archived for later source-bound correction. The separate standard fresh replay verifies all four returned exports, exact clip bytes, complete arrays/contact/geometry reports, both selection decisions and the full final control archive. It completes in 274.375 seconds with peak sampled RSS 566,280,192 bytes; all 272 resource observations replay. It uses the same declared 768 MiB CPU cap to retain all returned observations and reruns no optimization or Jacobian. Shared reader/curve/skin/audit methods are not an independent physical implementation.

## Hosted portability follow-up

The local passing batches do not establish complete hosted success. At source commit `13bac79`, the hosted Ubuntu contact/rig shard reports one failure in `test_explicit_polar_recipe_exports_without_repairing_the_stored_affine_rig` (653 other checks pass, plus ten subtests). That vertical-root orientation test is separate from the seeded crawl command; its cause is not yet established. The failure remains open and is not waived. See the [hosted regression run](https://github.com/DocMorphic/strep/actions/runs/38658558748).

The test now includes the actual export acceptance flags, rate/floor counts, vertical/horizontal displacement and dependency versions in its failure diagnostics without changing any expected result or acceptance rule. A manual `Focused source diagnostics` workflow runs selected fixed source suites on Ubuntu and Windows with the same pinned CPU dependencies and offline environment. Test paths are fixed choices passed through a quoted environment variable. It provides a short reproducible route to diagnose this cross-platform failure while the complete workflows continue.

All nine orientation checks pass locally on Windows in 7.20 seconds with the diagnostic output added. The measured export has zero rate/floor failures, 4.500020-mm peak floor depth, zero minimum vertical shift and 0.000017-mm maximum horizontal drift. The guard completes in 24.281 seconds with all 26 resource observations replayed. This local result does not resolve the hosted Ubuntu failure.

Generated evidence remains local under ignored `reports/native-seed-restoration-validation-v1`, `reports/native-seed-restoration-validation-v2`, `reports/crawl-public-seed-restoration-v1` and `reports/crawl-public-seed-restoration-replay-v1`. No new generation, training, held-out, engine, independent animator or cleanup evidence is claimed. Next work is further temporal/contact correction under original limits and broader scene/partner/style/rig/engine/release evaluation. All fourteen capability/calibration gates remain unapproved and the entire-project goal remains active.
