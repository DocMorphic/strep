# Sparse joint targets on existing rig clips

Status (2026-09-27): worker, supervised Studio API, persistent UI target drafts, decoded audits and packages are implemented. Both development requests reach their joint targets but remain rejected by floor/support screens. No quality or release promotion.

`scripts/rig_joint_recipe.py` accepts a hash-bound source job/version and one to eight joint/frame targets, with world positions and unit XYZW quaternions. The editable window spans 6–120 frames in a finite 30fps clip. Two samples at each edge, and all surrounding frames, remain fixed. It rejects stale versions, malformed values, duplicate targets, targets on fixed frames, non-descendant joints and periodic input. It uses actual imported-rig joint ancestry, with existing hard edit bounds; action names are not part of the schema.

The preparation step retains the original character, motion, rig profile, licensing files, clip, root track, contact annotations, events and review metadata. It snapshots source local/world matrices, the fitting spec, targets, envelope, and hashes. Existing authored patch targets retain their world positions and intervals; the parent spec is retained separately when rebound to a corrected clip. Unconfirmed model contact predictions are not silently converted into authored support. Moving/oriented contact formats are rejected rather than dropped. Weighted foot geometry currently requires sufficient mapped foot/toe skin vertices, with an explicit error if the rig cannot provide them.

Thirteen tests passed in 4.25 seconds, including compilation against an actual imported rig's original and corrected versions, source immutability, contact provenance, world-target accuracy through the existing fitter, and invalid requests. An initial function/local-variable name collision failed two tests; it was fixed and all thirteen were rerun successfully. Logs are `reports/rig-joint-recipe-tests.log` and `reports/rig-joint-recipe-tests-final.log`.

In Characters, select a result/version, choose **Edit timing and pose**, and expand **World-space joint targets**. Select a bone and frame, sample its current world pose, change position/orientation, add targets, and fit over the selected source-frame window. Drafts survive closing the editor. Input and candidate remain separately selectable; recipe and audit links accompany the result.

`rig_joint_edit.py` performs target feasibility then guarded refinement, retaining input, target-fitting output and candidate. Independent decoded checks cover target error, fixed context, untouched chains, local translations, joint/root bounds, motion steps, floor depth at frames and half frames, and inherited authored support. Numerical failures retain rejected candidates; hard context/motion failures prevent successful completion. Solver failure is not proof of global infeasibility. Timing, annotations, licenses, inputs and code snapshots are retained. Packages include optimization history and all stages.

Both real requests used the normal 60/40 iteration budgets, the original imported CesiumMan clip, frame 30, window 15–45 and unchanged requested orientation:

| Development request | Position error | Orientation error | Whole-clip floor depth | Result |
|---|---:|---:|---:|---|
| Right hand +2 cm world X, API | 4.97494 mm | 0.75644° | 25.88495 mm | Rejected |
| Left hand +2 cm world Y, Studio | 4.97243 mm | 0.66987° | 24.06125 mm | Rejected |

Both meet the 5 mm / 5° target screen and hard motion/context checks, but fail floor and authored support screens. API decoded support guard excess reaches 4.04e-8 m (`exact_caps_met: false`); Studio's decoded guards pass exactly. No cap was silently loosened. These checks do not certify balance, forces, action correctness or naturalness.

`reports/rig-joint-studio-v1/verification.json` independently verifies target offsets, decoded audits, immutable inputs, annotations, packages and HTTP bytes. Six GLBs have zero validator errors and one pre-existing skinned-mesh-root warning each. Actual Godot import checks all 366 frames, 19 bones each, with maximum position error 2.30e-7 m. These are development observations, not held-out release trials.

Full suite: **480 passed**, five existing warnings, 130.32 seconds. A later served-module route indentation error was fixed and its API test passed in 3.88 seconds. Frontend syntax passes. Browser checks cover draft persistence, duplicate-target rejection, real submission/completion, explicit failed checks, input/candidate switching, frame 30, playback, full grey character visibility and recipe/audit links, with no console errors. No independent ratings or cleanup-time records exist.

Next: broader scene/partner reliability and dynamics diagnostics under the same project-wide goal; avoid repeated tuning of this small fixture.
