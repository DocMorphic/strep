# Native hand and foot target authoring

Status: experimental workflow verified; no realism, contact or release approval. The same full-project goal remains active.

Studio now lets a developer capture a pose, select one hand or foot, offset its target in world XYZ, inspect a bounded candidate, and use the accepted pose as guidance for a new arbitrary action. Original files and rejected candidates remain saved. A ghost original, grey candidate and orange target provide local comparison. The target sphere is drawn above the character so it remains visible. The source/derived NPZ hashes bind subsequent generation to the exact selected pose.

The solver optimizes two proximal joints and compensates terminal orientation while preserving root and unrelated chains. Each changed local rotation, including terminal compensation, obeys the requested relative edit budget. This is not anatomical range-of-motion enforcement or collision correction. Position error must be within5mm before the UI offers Use this target. Offsets are limited to0.5m, budgets1–90degrees. Failed solves stay inspectable and cannot replace the guide. Static targets use two identical samples to satisfy the motion container; contact channels are explicitly unannotated.

## Observed results

| Trial | Target | Static residual | Maximum edit | Decision |
|---|---|---:|---:|---|
| Right hand, wave301/frame60 | +8cm Y,45degree budget | <0.001mm |14.449degrees| Reached |
| Follow-on right hand | +50cm Y,1degree budget |493.021mm|1.000degree| Rejected; prior guide kept |
| Right foot, kick303/frame37 | +6cm Y,45degree budget |<0.001mm|5.436degrees| Reached |

Independent decoded-GLB checks verify terminal orientation, unchanged world chains, source hashes, joint budgets and full-mesh floor measurements. Static hand and foot sources retain12.453mm and10.497mm floor depth respectively; target success is not collision success.

Actual Studio generation job `20260927-022531-b3c48262` used the accepted hand target at outputframe60, wave prompt, seed401 and the existing high-mobility text direction. Unchanged checkpoint,100diffusionsteps, no postprocessing. Total pipeline189.39seconds; generation10.59seconds; peak process-tree RSS2.808GB. This is one integration case, not a controlled style experiment.

The generated native right hand missed by23.166mm and11.541degrees. This passes the older provisional3cm/15degree conditioning screen but does not inherit the static editor's5mm target accuracy. Full eight-weight mesh floor depth12.381mm; half-frame depth12.370mm;114/120 integer frames exceed proposed10mm release screen. No action correctness or animator approval was assigned.

Seven GLBs validated with zero errors and warnings. Actual Godot imported132samples over sevenfiles; maximum world-joint position difference3.485e-7m. Generated GLB/raw poses agree within4.939e-7m. All12ZIP members and five served files were byte-verified. These establish data preservation and import behavior, not visual naturalness.

## Validation and provenance

Canonical full suite:401passed,4existingTorchwarnings,126.16seconds. Initial default collection included archived copies and vendor tests; `pytest.ini` now scopes discovery to `tests`, preserving the archives and original failed log. Focused pose/API/guidance suite32passed. Zero-offset inversion drift was fixed against the native local-FK reference without loosening the assertion. FinalJSmodules syntax-checked. Real browser capture/solve/accept/reject/generate/inspect flow checked; no console errors. Final generated character visible atframe60.

Evidence: `reports/pose-target-authoring-v1/{verification,generation-verification,http-verification,test-results,ui-verification,decision,implementation}.json`; immutable implementation copy in `implementation/`; Godot evidence in `reports/godot-pose-target-authoring-v1/verification.json`. Actual poses remain in `reports/pose-targets/6afe9014bc444df8b79d1b09b3206fa7`, `7f2eb2327d194485a4fdc4052bc6786c`, `df5659e28e754a6dbe86a2b875f6f600`.

The prior profile-response comparison viewer now renders all eight mesh weights through the shared helper. This fixes preview deformation only: model outputs, numerical metrics and failed cross-action mobility conclusion remain unchanged. Amendment saved with that study.

## Next under the full goal

Measure explicit pose controls across held-out actions and multiple seeds with side identity and action preservation. Do not infer reliability from one successful static solve or the existing approximate model-guidance screen. Joint/mesh support fitting, scene and partner contacts, target-rig transfer, offline packaging and independent animation review remain required by the release matrix. No new training is justified by this integration test alone.
