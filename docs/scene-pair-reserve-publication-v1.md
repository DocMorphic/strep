# Measured reserve step published for local review

The full-step reserve candidate completes all declared local checks and is now available in Studio as **Paired correction with export margins**, with Before and After clips. This is a small verified correction, not a solved two-person interaction: all 37 failing collision times remain.

| Measured quantity | Result |
| --- | ---: |
| Local sampled times | 148 |
| Fresh directional mesh queries | 296 |
| Source peak penetration | 22.568796 mm |
| Candidate peak penetration | 22.554740 mm |
| Peak improvement | 0.014056 mm |
| Times exceeding 5 mm, before / after | 37 / 37 |
| Maximum per-time depth-cap excess | 0.000116 mm |
| Maximum sampled floor increase | 0 |

The depth-cap excess is below the unchanged 0.001 mm comparison tolerance. Angular, positional, preservation and original edit-budget checks pass for the selected fraction. No tolerance was relaxed. The geometry audit ended normally with exit code 0; no worker remains active for it.

## Evidence reuse and publication

`assemble_scene_pair_reserve.py` binds the completed proposal and geometry outputs, checks every source/candidate time and both directional queries, reconciles depth/floor arithmetic and summary counts, and preserves all five attempted fractions. The assembled request explicitly identifies the empirical-margin experiment. It copies existing clips and observations; it does not re-fit motion, re-query geometry or imply release approval.

For the measured candidate, the selected folder is named `candidate` so its manifest IDs match the already observed Godot cases. The source clips, candidate clips, linearization, margins and geometry retain their original bytes. An incomplete, inconsistent or rebound audit is rejected. A completed geometry failure retains the source and records the failed attempt without selecting it.

The standard Studio job adopts this assembled evidence and verifies it before publication:

- Ten attempted actor exports reconstruct exactly; all-joint positional replay covers **225,610 observations**.
- All **4,287** retained source skin witnesses match independent full-skin reconstruction within **4.44e-16 m**.
- The selected clips pass the independent angular publication check, covering **45,122 observations**.
- Existing Godot evidence is reused only for the same four clip identities and native clocks: **444 actor frames**, with maximum position error **5.366925e-7 m**.
- Native preview reconstruction differs from the exported skin by at most **3.297736e-7 m**.

Direct handler checks find the new collection and both actors; all six manifest preview/download routes resolve. Original prepared contact metadata remains available. This is source/handler and artifact verification, not a rendered-browser or human review.

Local evidence includes `scene-pair-reserve-geometry-v1`, `scene-pair-reserve-completed-v1`, `scene-pair-reserve-replay-v1`, `paired-edit-jobs/expanded-window-v1`, `scene-region-jobs/paired-expanded-window-v1`, and `scene-pair-reserve-studio-v1.json`, under ignored `reports/`.

## Software checks and next decision

The previous hosted run failed because a model-free orchestration test imported the full request/geometry stack. Request preparation imports are now deferred until needed, and the orchestration unit test isolates the fitter it mocks. In the existing minimal environment with no PyTorch, the full declared source suite passes: **326 passed, 4 skipped**. Eighteen focused assembly/geometry tests cover immutable clips, incomplete evidence, arithmetic and failed-result retention. Hosted Windows/Linux verification remains a separate check on the next commit.

The improvement remains too small to solve the interaction. The saved expanded-window Jacobian has no zero-derivative witness rows, but its 0.1-degree trust balls have an optimistic independent-row affine peak floor of **19.502267 mm**, even before other constraints are applied. The independent-row affine calculation would require at least **1.460332 degrees** to predict 5 mm at every retained witness. This is neither an attainable pose nor a valid large-step nonlinear certificate: each row gets its own best direction and all coupling is ignored. Evidence is saved in `scene-pair-expanded-trust-floor-v1.json`.

The next fitting decision should compare which coupled motion/surface constraints limit useful progress, then test a bounded cumulative correction or revised control support against the original limits. A larger trust radius alone must not be presented as a solution. No held-out prompts or human-review evidence were used; all release capabilities remain unapproved.

Follow-up: [expanded-window diagnostics and nested curves](scene-pair-expanded-limits-v1.md) now compare eight constraint variants and evaluate denser curves with equivalent solver scaling. All five new actual exports fail at least one unchanged motion check; the published reserve comparison remains unchanged.
