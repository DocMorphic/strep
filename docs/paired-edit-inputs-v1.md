# Paired editing on saved animation clocks

The paired rotation model now uses each GLB's actual key times rather than the fixed high-five frame schedule. `scripts/timed_rotation_edit.py` supports explicit joints, edit windows, control knots, protected contact times and cumulative rotation limits measured from an original reference. Export preserves the key clocks and clones shared sampler descriptors so selecting one joint cannot change an unselected joint.

Only keys whose complete interpolation support lies inside the edit window can change. Protected times, including points between keys, freeze every influencing key. Quaternion sampling matches the existing decoder's native float32 clock arithmetic. Stored protected keys remain exact; decoded world matrices use a 1e-12 numerical comparison tolerance.

`scripts/paired_edit_request.py` compiles and snapshots requests for existing native two-actor scenes. Requests explicitly select both actors' joints, contact IDs, seconds, knots and rotation budgets. Scene and implementation revisions reject stale inputs. Each prepared folder retains the original actor exports and scene, authored placements, hashes, exact contact times and implementation copies. Continuations must retain these original references rather than reset their rotation budget.

## Validation

The local `timed-pair-model-v2` study uses both actors from the original, retimed and trimmed published development pair, alternating left and right arm controls. Small declared sinusoidal control probes test the editing model; they are not collision-fitting results.

| Check | Result |
| --- | --- |
| Actor-pose observations | 3,900 |
| Protected or outside-window pose observations | 3,252 |
| Unchanged quaternion keys | 57,334 |
| Changed quaternion keys | 416 |
| Largest original-relative rotation edit | 0.340712 degrees |
| Largest exported-versus-model matrix error | 8.691534e-8 |
| Largest directional derivative discrepancy | 1.246892e-12 |
| Largest protected-pose numerical difference | 3.330669e-16 |

The first real-asset probe, `timed-pair-model-v1`, stopped at a bitwise world-matrix assertion despite only floating-point roundoff. It is preserved. The completed version uses the established numerical tolerance and still checks frozen quaternion keys exactly.

`timed-pair-model-engine-v1` checks all 12 input/probe GLBs in Godot: 1,944 actor-frame observations, 77 bones and one skinned surface per clip. Duration and nonlooping checks pass. Maximum position error is 7.363631e-7 metres; maximum basis-element error is 1.066265e-6.

Three immutable requests were also prepared under local `reports/paired-edit-jobs/`: `curve-controls-original-v1`, `curve-controls-retimed-v1` and `curve-controls-trimmed-v1`. Each has 72 controls and retains its exact protected contact time: 2.5, 3.7583892617449663 and 2.0917225950783 seconds respectively. They explicitly report `solver_executed: false` and `quality_approved: false`.

Thirty-one focused Python tests pass, covering irregular clocks, antipodal interpolation, shared samplers, protected intervals, derivatives, original-reference continuation budgets and saved-scene request validation. The synthetic clock tests are included in model-free CI; saved-scene tests require ignored local assets.

## Scope and next work

This is an editing model and input preparation layer. It does not yet run reusable paired collision fitting, add a Studio fitting button or qualify a new action family. Requests currently require two native actors without scene objects, linear rotation channels, one skin per actor, one to eight selected joints per actor and edit windows of at most five seconds. The window limit bounds local computation, not the action vocabulary.

Next connect these scene-derived models to coupled surface and motion constraints, then independently audit the actual exports before exposing a fitting worker in Studio. Existing partner penetration and full-clip floor failures remain. No human review or rendered browser verification is claimed. All 14 release capabilities remain unapproved.
