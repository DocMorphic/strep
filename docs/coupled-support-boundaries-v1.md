# Coupled leg and root correction at support boundaries

Development work, 2026-09-28. The single project-wide goal remains active; this does not approve animation quality.

The completed root-only cleanup left foot-speed regressions in all 11 previously affected cases. This follow-up allows the original editable leg joints and root to move together. It targets the supported-foot speed excess above each foot's raw-motion peak. That target is a diagnostic reference, not a physical definition of realistic motion.

The method considers all 11 affected cases in the existing 24-row population, starting from the selected outcome of the root cleanup. Cases without the measured regression and unfinished source rows remain in the population accounting. Selection depends on measured speed excess, not the action name. For each case it selects at most two disjoint groups of 12 adjacent frames, with the first and last two clip frames preserved. Each group receives at most three accepted conic steps, three fixed trust radii, and four fixed backtracking fractions.

`scripts/coupled_support_block.py` builds sparse constraints for actual skinned geometry, root and foot trajectories, and local joint rotations. It retains the original raw-motion coordinate system and total edit budgets instead of resetting the allowance after cleanup. Sparse placement keeps each vertex derivative local to its frame while temporal constraints couple neighboring poses. The objective targets actual supported-foot movement, not curvature of correction offsets.

The proposal preserves achieved floor depth per vertex, drafted anchors, support height, root/foot accelerations, local rotation steps, and foot speed during support, entry/release, and adjacent edges. Nonlinear acceptance recomputes serialized geometry and midpoint floor depth. The supported-height constraint uses a fixed source vertex as a witness: keeping that vertex at or below the original minimum guarantees that the patch minimum cannot rise beyond its allowance. This avoids differentiating a switching minimum on a flat sole.

`scripts/verify_coupled_support.py` independently decodes each complete exported GLB. It first checks the original root/joint budgets and unselected transforms against the raw input, then checks preservation against the selected corrected input. It checks all relevant frames, including outside the edited groups, and requires a meaningful reduction in the whole-clip supported-speed excess objective. Rejected exports remain available, while the input stays selected. Real Godot checks cover each evaluated input and selected result; contact and root sidecars retain their provenance and unapproved status.

## Preflight and implementation failures

Initial derivative checks passed on two of three rigs. The exhausted-walk rig exposed a changing minimum-foot vertex: its hover derivative error was 0.004465 while the other constraint families were below the 0.0002 threshold. The fixed-witness formulation resolves that mismatch. The original failure remains in `reports/coupled-support-preflight-v1.json`.

The first population attempt, `reports/coupled-support-boundaries-v1`, encountered a NumPy boolean serialization error while saving solver history. Its exact worker was terminated after confirming the error; its partial failures and termination record remain. No quality result is inferred from that aborted attempt.

The logging fix explicitly converts scalar decisions to built-in booleans. Five tests pass in 24.51 seconds, including an actual conic step with a NumPy objective and JSON history, sparse frame isolation, and real derivative/source-feasibility checks on three rigs and three action families. The fresh finite study is `reports/coupled-support-boundaries-v2`; its source files, protocol, selected clips and implementation snapshots are frozen. Read its pipeline and completion records for actual progress and results.

This is still a development comparison with predicted, unconfirmed contacts. It does not establish correct action semantics, balance, continuous-time collision freedom, animator quality, or generalization to objects and partners.

## Completed result and developer review

The v2 study completed all 11 targeted cases: six retained numerical improvements and five kept their inputs. Eight other completed cases were not targeted; five source-unfinished rows remain in this frozen 24-case population. All 22 input/selected GLBs pass 3,960 actual Godot actor-frame checks. The supported-speed excess energy reduction ranges from 0.960 to 73.435 percent among accepted results. All 11 targeted cases still have at least one foot-peak regression against raw motion. These are partial improvements, not solved contacts.

Results: `reports/coupled-support-summary-v2/summary.json` and `comparison.md`. Backpedal rig-02's left peak improves from 0.265806 to 0.211946 m/s, still above its raw 0.209040 m/s reference. Its right peak remains 0.199999 m/s versus raw 0.143373 m/s. Exhausted-walk rig-01's right peak improves from 0.190239 to 0.184378 m/s but remains far above raw 0.061934 m/s.

The user chose to perform a developer review first. Studio → Characters → Review corrected motions → Support and transitions contains all 19 completed source cases, with raw transfer, before leg/root correction, and selected result versions (57 clips total). Unchanged results and remaining failures stay visible. Each case includes a downloadable comparison, root tracks, predicted contacts, audit and attribution. Report the case, version, frame range, and what looks wrong; compare at normal speed before scrubbing. Developer feedback does not replace independent animator review and timed cleanup for release.

The immutable package is `reports/rig-jobs/support-boundary-review-v1`. Its 312 file hashes verify; six representative served files match their saved hashes. Browser testing verified 19/5-case study switching, same-frame version comparison, playback to the final frame, keyboard scrubbing, real pointer disclosure activation, a visible grey character, and no captured console errors. Evidence: `reports/support-developer-review-ui-v1/verification.json` and `review.png`. No human ratings have been collected or prefilled.

The original whole-support worker subsequently reached 20 complete cases. `reports/whole-support-breadth-interim-v20` records that new population state; it does not alter this frozen 19-case review set. Four original rows are unfinished (one running, three pending).
