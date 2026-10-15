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

The bounded Quaternius crawl trial starts from the previous public crawl job's complete final controls and original source files. It chooses the four already-permitted right-leg rotation tracks (nodes 62, 61, 60 and 59), including the two skin influences of the authored calf-surface touch and their foot/toe descendants. It varies native keys 0–63 under the original explicitly editable-start/preserved-end declaration. This is an author-selected kinematic subset, not inferred anatomy, balance or naturalness. It is separate from the earlier Kenney developer-review packet.

The trial keeps the same 768 variables, trust 0.02, difference step 0.001, one iteration, at most four decoded backoffs and original source limits. The existing 768 MiB CPU profile, extra 600 MiB free-RAM floor, 15-second admission stability and 1,200-second supervisor limit remain declared. The initial GLB matches the prior retained job byte-for-byte, and all four original cap arrays match exactly. Full inactive controls and actual nonselected local rotation channel bytes remain unchanged. Every rejected probe is retained.

The 482,068-row affine model has 355,609 protected rows, 123,630 original rate rows and 2,829 complete floor times, with 315,930 nonzero Jacobian entries. The primary solver reports `Solved` after 28 iterations. Its separate minimum-norm phase fails the affine hard-row recheck and is not selected. The archived solver reports 332 fixed failed rows for this linearization; this is local derivative evidence, not nonlinear infeasibility.

| Decoded clip | Original rate failures | Failed floor times | Authored touch error | Retained |
| --- | ---: | ---: | ---: | --- |
| Start | 377 | 7 | 4.868693 mm | Baseline |
| Full step | 377 | 5 | 5.002457 mm | No: exceeds the original 5-mm contact limit |
| Half step / final | 377 | 5 | 4.934020 mm | Research continuation only |

The half step passes complete decoded prefix and per-condition no-worsening retention. Maximum normalized excess falls from 360.892750 to 345.953947; summed squared positive excess falls from 773,847.978279 to 715,406.124497. Peak sampled floor depth decreases from 5.273719 to 5.258764 mm, which still fails the original 5-mm floor limit. Root error remains exactly zero. Retention is not motion, geometry or release approval: all 377 original-rate failures and five floor failures remain visible. The final GLB SHA-256 is `b092a1910a87690a0fa0434c31606d0740684dc8cb0792019cbbce9a3a181433`.

The production guard completes in 609.938 seconds with peak sampled process-tree RSS 494,202,880 bytes. All 599 recorded resource observations and archived bindings replay. The separate standard replay verifies all four returned exports byte-for-byte, complete observations, contact/geometry reports, both retention decisions and final native controls without rerunning optimization. Its guard completes in 314.906 seconds with peak sampled RSS 566,382,592 bytes; all 310 resource observations replay under the same 768 MiB CPU profile. This uses shared reader/curve/skin/audit code, not an independent physical implementation.

## Localizing the remaining failures

A read-only diagnostic verifies the retained request/result bindings, original input pins, archived methods and complete observations. It maps every rate row to its actual metric, joint and derivative support interval, using the saved original cap arrays and exact stored Jacobian. Protected and soft copies of each rate derivative agree exactly. The diagnostic guard completes in 20.328 seconds with peak sampled RSS 78,163,968 bytes; all 22 resource observations replay under the 512 MiB CPU profile. No new optimization or export runs.

All 377 failures remain in both start and final: 89 speed, 85 acceleration, 120 angular-speed and 83 angular-acceleration conditions. None has a zero original source cap. Forty-five failures have nonzero recorded affine response, all within 0.083333–0.116667 seconds around the touch. The other 332 occur at 0.725–0.941667 seconds, outside the selected keys' complete 0–0.533333361-second interpolation support. Sixty-six also belong to the unselected left-leg hierarchy; these populations overlap and must not be added. The late failures' largest normalized excess is 24.960087, whereas the remaining early excess is 345.953947. The five failed floor samples remain around 0.095833–0.104167 seconds, all with vertex 4576 as the worst floor witness.

This changes the next experiment: repeating the early interval cannot alter the late key channels. A later interval must include both legs, and the proposal objective must allow progress when another interval's fixed soft failure is larger. A zero derivative alone is not proof of nonlinear infeasibility; the actual local key support and kinematic hierarchy provide additional context. Complete decoded per-condition retention, original caps and every release gate remain unchanged.

Local evidence remains under ignored `reports/native-interval-track-validation-v1`, `reports/native-interval-track-validation-v2`, `reports/native-shared-solver-and-track-validation-v1`, `reports/crawl-selected-leg-interval-v1`, `reports/crawl-selected-leg-interval-replay-v1` and `reports/crawl-selected-leg-diagnosis-v1`. No generation, training, held-out, engine or human-quality evidence is added. All fourteen capability/calibration gates remain unapproved and the full-project goal remains active.
