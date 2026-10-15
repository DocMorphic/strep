# Optional bounded native recourse

The native interval correction and verified continuation commands accept an optional `native_recourse` recipe member. It attempts a small cached-Jacobian repair when an ordinary decoded backoff violates a bounded number of native no-worsening conditions. The [measured crawl pilot](native-cached-repair-pilot-v1.md) motivates this path. It is a proposal mechanism, not a new acceptance tolerance or animation-quality approval.

```json
"native_recourse": {
  "attempts_per_iteration": 1,
  "trust": 0.00001,
  "normalized_reserve": 0.0001,
  "maximum_failed_rows": 1
}
```

Omitting this member preserves ordinary backoff behavior and its history shape. The maximum is four attempts per outer iteration, one attempt per rejected primary backoff. Trust must lie between 0.000001 and the smaller of 0.001 and primary trust. A recipe may target at most 64 violated native rows; larger populations skip recourse and continue ordinary search. None of these limits removes a condition from acceptance.

Each repair anchors the cached native-row Jacobian at the rejected clip's actually decoded vectors. All edit, displacement and authored contact caps remain original. Every rate row is protected by the larger of its original cap plus existing tolerance and its value at the current accepted outer-iteration start. Source-rate arrays are unchanged. Every native row is hard in the repair model, including fixed rows. Only violated search targets receive an additional reserve: `normalized_reserve * row_scale`. This is dimensionless and respects each row's units; the reserve does not alter decoded acceptance.

The repair uses the original iteration's Jacobian columns and permitted native controls, without new finite differences. Its returned delta is clipped to the configured trust and original variable box. Both raw and applied deltas are archived. Floor/scene cones are not part of this cached native subproblem. Every returned clip must still pass the full decoded edit/contact/root prefix, every original rate and geometry no-worsening condition, unchanged degenerate-face populations, and the existing strict improvement test. A failed full geometry check rejects the repair even when the conic solver reports success. Numerical retention is not semantic, dynamics, engine or animator approval.

The original rejected probe stays rejected in history. Each optional attempt separately records its anchor, source candidate, violated rows, tightened search caps, solver status and archive hashes. Returned repairs receive distinct `iteration-backoff-repair` labels. Each iteration records its selected label so a repaired half step cannot be confused with an accepted ordinary half step. Failed solver attempts and rejected decoded repairs remain archived; both count toward the repair budget.

Both standard and continuation auditors reconstruct all returned exports and observations, then replay ordinary and repair choices without rerunning optimization. They check the complete native row population, original cap/scale agreement, search limits, source labels, raw/applied deltas, trust bounds, budgets and selected clip. Existing frozen runtimes preserve their recorded implementation bytes; newly recorded runtimes include the repair module with all other root Python sources. Old studies are not silently migrated to current methods.

This is optional correction infrastructure. It does not broaden the declared supported motion families or satisfy the project's outstanding release gates. Generated study evidence stays under ignored `reports/`.

## Validation on 2026-10-15

The initial 104-check group passes across interval correction, explicit seeds, selected tracks, standard/continuation replay and frozen execution. Its guard completes in 375.454 seconds, with 370 resource observations replayed and peak sampled process-tree RSS 158,679,040 bytes. After adding the raw-delta audit guard and four targeted checks, the final repair suite passes all 35 checks in 37.30 seconds; its guard completes in 53.953 seconds, with all 55 observations replayed and peak 132,685,824 bytes. Both use a 512 MiB process budget plus the unchanged additional 600 MiB free-memory floor.

The tests cover mixed-unit search margins, all-hard native-row solving, bounded effort, contained labels, rejected primary versus repaired selection, tampered histories/controls/limits, preservation of a failed fixed-row solve without an invented export, rejection after a successful solve introduces a geometry failure, and ordinary backoff continuation after a failed repair. A passing real native clip still exports and replays without inventing a repair. The [focused hosted workflow](https://github.com/DocMorphic/strep/actions/runs/38677453591) passes all 35 checks on both Ubuntu and Windows at `d6def8bc03b56676a295dc1b6f5a89b8a7674d9f`. Broader contact/rig and full-source workflows remain separate.

## Public retained-case experiment

The public interval command repeats the pilot's separate plateau-seed research branch with the example configuration above. All original assets, authored touch/geometry intent, source-cap arrays, root, 85 native keys and three active tracks remain unchanged. The complete 765-control primary proposal is reproduced; the start, full step and half step are byte-identical to their earlier exports. This is a retained development case, not held-out evidence.

| Returned clip | Rate failures | Failed floor times | Squared positive excess | Retention |
| --- | ---: | ---: | ---: | --- |
| Start | 499 | 0 | 4,087.873910 | Reference |
| Ordinary full step | 503 | 0 | 3,707.573624 | Rejected |
| Ordinary half step | 485 | 0 | 3,879.506160 | Rejected |
| Repaired half step / final | 485 | 0 | 3,879.500998 | Retained against this seed |

Only native row 294,926 violates the half step's no-worsening bound. The dimensionless reserve of 0.0001 gives this angular-speed row a search reserve of 0.000060518293 rad/s, tightening its search cap to 0.911824724879 rad/s. Its actual acceptance bound remains unchanged. All 352,780 native rows remain hard. The repair solver reports `Solved` after ten iterations, with maximum returned control step 0.0000055732543; the secondary minimum-norm point fails its hard-row check and is not selected.

Full decoded retention succeeds with zero root error, no edit failures, authored touch error 4.958739842 mm and peak sampled floor depth 4.799615264 mm. The original 5-mm touch/floor limits, complete original source-cap arrays and inactive controls are preserved. Final GLB SHA-256: `97866025ee03316abb60c728833e31dde9a0dab8a0b25ee749df4a698e6a9d6c`. The primary half step remains explicitly rejected; history selects `1-1-repair`.

Production completes in 612.562 seconds, with all 604 resource observations replayed and peak sampled process-tree RSS 515,473,408 bytes. A separate full cold replay verifies all five GLBs byte-for-byte, complete observation arrays/contact/geometry reports, native controls and both primary rejections plus repaired selection without rerunning the optimizer. It completes in 351.469 seconds, with all 346 resource observations replayed and peak sampled process-tree RSS 633,040,896 bytes. Both use a declared 768 MiB process cap, the unchanged extra 600 MiB available-memory floor, 15-second admission stability and 1,200-second supervisor limit. The replay shares the original mathematical readers and geometry methods; it is not independent physical or engine validation.

A fresh continuation load reproduces the repaired final GLB and every saved array from the verified lineage, retaining original caps and the same 485 rate failures. The public frozen-runtime builder successfully captures the complete recorded source, including `native_key_cached_recourse.py`, from this actual repaired parent. This check completes in 119.813 seconds, with all 120 resource observations replayed and peak sampled process-tree RSS 419,561,472 bytes under a 512 MiB cap plus the unchanged 600 MiB free-memory floor. It does not run another continuation optimization or execute the newly frozen runtime; those outcomes are not inferred from successful freezing. Evidence stays local under `reports/public-cached-native-recourse-continuation-v1`.

The 485 remaining original-rate failures keep the clip rejected as a game asset. This branch remains ineligible against the earlier 351-rate/five-floor comparison; no selected asset changes. No new inference, training, engine, semantic, animator or cleanup evidence is claimed. All fourteen capability entries and the release calibration gates remain unapproved. Generated evidence stays local in `reports/public-cached-native-recourse-v1` and `reports/public-cached-native-recourse-replay-v1`.
