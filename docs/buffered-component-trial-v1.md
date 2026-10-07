# Prepared buffered complete-clock trial

The [empirical material margins](empirical-material-margins-v1.md) now have a concrete full-trial runner. Its numerical branch is prepared but has not run. The real launch stops before scientific work because storage is below the unchanged reserve.

## Explicit archived inputs and preflight

`buffered_component_trial_preflight.py` accepts a `strep-buffered-component-trial-request-v1` JSON request with `sources` and a fresh `output` path. Source roles are `model`, `model_reader`, `trial`, `trial_reader`, `calibration` and `calibration_reader`; each contains an explicit `path` and lowercase `sha256`. Paths resolve relative to the request. These are the complete-clock model, original trial and empirical calibration, each paired with its completed reader. Their declared schemas, unapproved status, original-source selection and required complete-replay flags must match.

The output parent must exist, and a prior trial directory is never overwritten. Check the output filesystem for strictly more than 1 GiB reserve plus the original 650 MiB output estimate: 1,755,316,224 bytes. Insufficient storage returns exit code 2 without scientific imports, solver/native/skin/collision calls or a trial directory. If sufficient, authenticate every declared archived input/output file and reject missing, changed, escaping or conflicting members. A ready preflight means ready for numerical validation; it is not a numerical or release pass.

Receipts may be up to 64 MiB each and 128 MiB together; the request is limited to 128 KiB. Retain the first real pre-output failure: the complete prior trial receipt is 29,332,307 bytes, exceeding an initial 16 MiB metadata ceiling. The corrected bound reads the whole receipt. No scientific resource reserve, source population or numerical tolerance changes.

## Prepared numerical branch

`run_buffered_component_trajectory_trial.py` repeats preflight under the existing worker lock. It checks original bound implementation hashes, exact job/anchor identity and material-model identity before using the empirical policy. Reuse the independently replayed 180 same-pose stencils, complete 1,673-time trajectory and 11-time material/full-mesh models; do not reuse derivatives after a pose change.

The prepared runner preserves all three solver families, original comparison fractions, all native caps/scales/clocks, edit/trust box, contact/reference bounds and equality rows. Record actual parameter residuals as well as actual scalar/vector native, material, mesh and positive-component results. Each export retains complete arrays. Every actual gate must pass before a changed export can enter full original scene assessment. Empirical affine bounds are proposal diagnostics and cannot replace actual acceptance. Preserve solver statuses and all failed outputs; nothing is promoted to a production source or release approval.

Run with the existing scientific Python environment:

```text
python scripts/run_buffered_component_trajectory_trial.py --request <pinned-request.json> --preflight-only --receipt <fresh-receipt.json>
python scripts/run_buffered_component_trajectory_trial.py --request <pinned-request.json> --receipt <fresh-launch-receipt.json>
```

Do not use optimized Python: the runner refuses scientific execution with assertions disabled. No dependencies are installed or models downloaded by this command. This fixture runner requires its archived development data and is not a portable installer.

## Evidence and outstanding work

All 47 new tests and 70 margin/solver tests pass without skips. Checks cover source role/schema/hash/reader integrity, complete member containment, metadata budgets, storage boundaries, repeated lock-held preflight, retained receipts, optimized-Python rejection and every independent actual acceptance condition. The workflow registers the new tests; hosted CI success is unverified. These tests do not exercise the new full numerical branch.

A complete saved-data audit reproduces all eight prior export eligibility masks, including every 30,450 scalar/vector native row, contact row identity, 1,710 material rows, 3,636 mesh rows, 107,072 component observations, all 6,336 positive rows, controls and equality conditions. References and decoded GLB provenance are bound to the completed original reader rather than recomputed here. No producer numerical runner is called, no new animation is generated, and all eight exports remain rejected.

The real full-launch attempt exits 2 with 915,828,736 bytes free. Its receipt records `scientific_work_started: false` and `numerical_validation_complete: false`; the trial directory does not exist. Next supply sufficient space and run this unchanged request, then independently replay every new numerical result before considering source promotion. Keep prior failures, immutable science and the earlier lower-depth branch. All fourteen release evidence arrays remain empty and the full-project goal stays active.


## Completed follow-up on 2026-10-07

The storage-blocked state above records the earlier preparation and failed launch. Storage later became available and the unchanged pinned request completed. See [the full buffered trial results](buffered-component-trial-results-v1.md) and [the finite native correction and full scene assessment](buffered-native-storage-results-v1.md). All original acceptance limits remain unchanged; neither experiment approves an animation or release.
