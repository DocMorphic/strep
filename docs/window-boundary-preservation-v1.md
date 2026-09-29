# Preserve animation outside local edits

The [larger-range study](expanded-window-surface-fit-v1.md) retained every native key outside its selected range, but changed adjoining exported samples by 2.015 mm. An editable root key at the start or end of the range participates in interpolation outside that range. Native-key preservation alone was insufficient.

The localized fitting mask now also holds the selected endpoint wherever it adjoins unchanged motion. The rotation control null space uses those held keys, and the existing root mask applies the same restriction. A range touching the first or final clip key does not unnecessarily hold that edge; a whole-clip range retains all controls. Ranges with no remaining spline freedom are rejected before fitting. Studio explains the held boundary poses.

The geometry planner reads the executed policy from the hash-bound fitting recipe. For fits using held boundaries, it counts immutable failures at the endpoints and adjoining segments and includes an extra key of room in its suggested range, clipped to the clip limits. Older fits retain their recorded native-key-only interpretation. Range suggestions do not alter user scope or imply solvability. The review display exposes the immutable count.

## Actual fitting and export regression

`reports/region-window-boundary-v1` uses the original 180-frame scene and the same arm-guide initializer as the preceding studies. A short **one-stage, 20-iteration** solve runs the actual region fitter, physical root parameters, full object skin, support constraints and export-rate guard with range 23–133. This is an integration regression, not a matched quality comparison against the six-stage studies.

The resulting skin moves by as much as **12.647132 mm inside the range**, confirming nontrivial edits. At 120 Hz, all **276 outside samples** preserve skin position within **0.129 µm**; the six adjoining boundary samples stay within **0.065 µm**. Root endpoint preservation and the selected boundary keys are recorded in the recipe. The original edit budgets pass. All **360 Godot actor-frame checks** pass, maximum position discrepancy below **0.396 µm**.

The motion remains unsuitable for approval: **473/490 contact samples** and **364/717 geometry samples** fail. Selected foot support has zero threshold failures in 1398 measured samples, but thirty-six vertex-identity gaps remain; support is not certified. The short fit takes 85.860 seconds, with one optimizer stage reaching its iteration limit. It does not establish contact convergence or human-perceived quality.

The retained review collection `scene-region-jobs/window-boundary-review-v1` has fifteen verified file hashes and fourteen allowed data/download routes. Failed quality checks remain visible. No HTTP, browser or human-review claim is made.

Sixty Python checks cover local controls, an actual small IK solve, dense fractional root/quaternion sampling, the original endpoint counterexample, invalid windows, bound recipes, planner scope, exported-window audits, review validation and Studio worker forwarding. Two Node checks cover displayed boundary evidence and the contact editor. Four desktop build checks pass. All fourteen project release capabilities remain unapproved.
