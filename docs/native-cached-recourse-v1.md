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

The tests cover mixed-unit search margins, all-hard native-row solving, bounded effort, contained labels, rejected primary versus repaired selection, tampered histories/controls/limits, preservation of a failed fixed-row solve without an invented export, rejection after a successful solve introduces a geometry failure, and ordinary backoff continuation after a failed repair. A passing real native clip still exports and replays without inventing a repair. The separate retained crawl experiment is in progress; unit/fixture checks alone do not establish its outcome or broader motion quality.
