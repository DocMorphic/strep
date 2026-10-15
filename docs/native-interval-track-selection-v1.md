# Longer correction intervals with explicit variable joints

The public coupled correction recipe can now choose which already-permitted rotation tracks are variables. This lets the same 768-control budget span more native keys: all sixteen permitted tracks allow sixteen keys, while four selected tracks allow sixty-four. It changes the optimization variables, not the original animation permissions or the conditions used to accept a clip.

## Authoring contract

Add an optional `active_nodes` list to the existing `strep-native-key-interval-restoration-v1` recipe:

```json
{
  "active_keys": [0, 1, 2, 3],
  "active_nodes": [62, 61, 60, 59]
}
```

These values are examples; node IDs must come from that actor's original permitted `rotations` declaration. The list must contain distinct integer node IDs and cannot be empty, Boolean, negative or null. Unknown or unpermitted nodes reject. The list's explicit order determines the flattened control order. Omitting it preserves the previous behavior of varying all permitted tracks. The Python constructors expose the same optional `active_nodes` keyword; their `None` default means all tracks.

This selector belongs to the restoration recipe, not to the original initializer authoring file. Active native keys still form a contiguous interval within the original edit window, subject to the original frozen and boundary declarations. The product of active keys, selected tracks and three rotation components must fit the unchanged 768-control limit. No variable is silently discarded to fit that limit.

Every nonselected track retains its complete seed controls, including keys inside the active interval. Selected tracks retain every inactive key. The full exported native-control archive still contains all permitted tracks and every original key. Nonselected local rotation channels remain unchanged; their descendants' world poses may move when an edited ancestor rotates. All original rotation/displacement, point/contact, joint-rate, floor/geometry and root conditions continue to cover those descendants and all other joints.

Every permitted track still participates in decoded edit checks, and all four original source-rate arrays retain the original reference. Complete physical condition counts remain unchanged. Only the Jacobian's variable columns are reduced. Equivalent floor cones may use different constant offsets because their affine trust-box bounds depend on which variables can move; their physical scalar residuals remain equivalent. Complete decoded checks and per-condition retention remain the acceptance authority.

The existing command, standard fresh replay and verified continuation share the same source/model loader, so the selection remains bound to the original recipe and replayed control order. The reconstructed seed receipt records the selected nodes. No new Studio control or action-name whitelist is introduced.

## Validation

The first batch passes 49 checks and fails one test assertion that incorrectly requires identical floor-cone coefficients after changing the variable set. That failure and its 219.328-second/218-observation resource trace are retained. The corrected comparison checks identical complete physical rows, original caps, hard-row/time/witness populations, corresponding Jacobian columns and equivalent floor residuals at matching steps. No production acceptance tolerance changes. The supplemental case passes in 14.88 seconds; its 31.375-second guard and all 33 observations replay.

Coverage includes actual native export agreement with a fixed nonselected track, fixed inactive keys, reversed node ordering, invalid/unpermitted selections, the public seeded command, complete final controls, standard fresh replay and verified continuation of a selected-track parent. All **229 combined compatibility/shared-runtime checks pass in 161.58 seconds**; the 179.516-second guard and all 179 resource observations replay. Existing default all-track behavior remains covered. Inventories validate at 511 Python/45 Node files and 75 Python/5 Node files in the focused suite; inventory validation is not execution of every listed test.

## Development trial

The next bounded trial starts from the previous public crawl job's complete final controls and original source files. It chooses the four already-permitted right-leg rotation tracks (nodes 62, 61, 60 and 59), including the two skin influences of the authored calf-surface touch and their foot/toe descendants. It varies native keys 0–63 under the original explicitly editable-start/preserved-end declaration. This is an author-selected kinematic subset, not inferred anatomy, balance or naturalness.

The trial keeps the same 768 variables, trust 0.02, difference step 0.001, one iteration, at most four decoded backoffs and original source limits. The existing 768 MiB CPU profile, extra 600 MiB free-RAM floor, 15-second admission stability and 1,200-second supervisor limit remain declared. The initial GLB and all four original cap arrays must match the prior retained job exactly. Full inactive controls and actual nonselected rotation channel bytes must remain unchanged. Every rejected probe is retained.

Local evidence remains under ignored `reports/native-interval-track-validation-v1`, `reports/native-interval-track-validation-v2`, `reports/native-shared-solver-and-track-validation-v1` and `reports/crawl-selected-leg-interval-v1`. No generation, training, held-out, engine or human-quality evidence is added. All fourteen capability/calibration gates remain unapproved and the full-project goal remains active.
