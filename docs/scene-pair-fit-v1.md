# Scene-derived paired fitting

`scripts/scene_pair_problem.py` connects immutable paired editing requests to coupled surface, rotation-budget and motion constraints. Actor IDs, joint selections, actual animation clocks, placements and contact guards come from the prepared scene. No high-five frame numbers or development asset paths are embedded in the fitting model. Each actor may have a different number of controls and a different triangle topology.

The prepared actor GLBs are the original references for a new request. Source keys outside the edit supports and at protected contact times stay fixed. A descendant-aware mask identifies every joint-position speed and acceleration stencil that can change. Per-joint source maxima are fixed separately in knot spans, including boundary stencils, on the saved 120 Hz sample clock. These are source-relative positional motion limits; angular-rate, force and balance qualification remain separate unresolved requirements.

Both the source vertex and target barycentric surface point move in each fitting row. Their Jacobians are assembled in the two actors' actual control order. Each sampled time keeps a depth ceiling of the larger of its original maximum penetration and 5 mm; already-clear times therefore retain the 5 mm screen. Initially penetrating witnesses also receive full separation-vector norm bounds. Norm and rotation limits are checked again after float32 GLB export rather than inferred from the affine proposal.

## Executable study

Run an immutable prepared request with:

```powershell
.venv\Scripts\python.exe scripts/study_scene_pair_fit.py reports/paired-edit-jobs/curve-controls-trimmed-v1 reports/scene-pair-fit-v1
```

The runner preserves source geometry samples, hashes, implementation snapshots, the linearization, solver results and every attempted export. It checks all source vertices for penetration using conservative broad-phase exclusion at each requested time, retaining at most 64 fitting witnesses per direction/time. Full candidate vertex-depth queries run only after exported motion, edit, preservation and retained-surface checks pass. A local step additionally requires at least 1 micrometre of peak-depth improvement without exceeding per-time caps or worsening sampled floor depth. This local acceptance is not release approval.

The first invocation is running against the saved, retimed-then-trimmed 111-frame development scene, using 126 local time samples and 72 controls. Early source samples confirm penetration above 20 mm. No completed fit, accepted candidate or engine result is claimed yet. Original reports and failures remain under ignored `reports/`.

After it reaches a terminal result, independently replay it with:

```powershell
.venv\Scripts\python.exe scripts/verify_scene_pair_fit.py reports/scene-pair-fit-v1 reports/scene-pair-fit-review-v1
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/scene-pair-fit-v1 --output reports/scene-pair-fit-engine-v1
```

The independent replay reconstructs each attempted GLB exactly, checks all joints and all motion stencils without reusing the fitter's active-row selection, and verifies every retained source witness with complete CPU skinning. It verifies geometry-report identities and arithmetic; it does not claim a second signed-distance implementation. Godot import must be verified separately.

## Source validation and limits

Thirty-eight focused Python tests pass, including unequal actor control counts, moving surfaces in both directions, authored placements, complete affected-stencil coverage, irregular clocks, contact guards, saved request reconstruction and independent detection of motion regressions. Synthetic model and replay tests are included in model-free CI; saved-asset tests skip when those ignored fixtures are absent.

This worker is not yet exposed as a Studio fitting action. It still requires two native actors, linear rotation channels, a single skinned primitive per actor and a bounded local edit window. The underlying motion generator is unchanged. Local sampled vertex checks do not certify continuous triangle collisions, self-collision, full-clip dynamics or naturalness. All 14 release capabilities remain unapproved.
