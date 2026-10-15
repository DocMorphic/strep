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

The real trial begins from the previously retained crawl half step, reconstructing complete controls against the unchanged original transfer. It expands the active interval to keys 4–19, all sixteen permitted tracks and the full existing 768-control budget. It performs one bounded public-command iteration with trust 0.02, difference step 0.001, at most four decoded backoffs and a 750-second proposal budget. The initial GLB must match the previously retained bytes exactly, and all four original rate-cap arrays must match the prior reference.

The wider CPU study explicitly estimates and caps process-tree RSS at 768 MiB, with the same additional 600 MiB free-RAM floor and 15-second admission stability; its supervisor limit is 1,200 seconds. This larger profile is declared before execution because the control count expands from 144 to 768. Other CPU studies and model/full-body policies are unchanged. Exceeding a guard stops the owned process; it does not relax animation checks.

Generated evidence remains local under ignored `reports/native-seed-restoration-validation-v1` and `reports/crawl-public-seed-restoration-v1`. No new generation, training, held-out, engine, independent animator or cleanup evidence is claimed. All fourteen capability/calibration gates remain unapproved and the entire-project goal remains active.
