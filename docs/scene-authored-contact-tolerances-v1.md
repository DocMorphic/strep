# Authored contact tolerances through scene correction

The scene contact compiler now carries each contact's metre tolerance into its native target segment and provenance. The independent actor evaluator uses that interval tolerance rather than silently substituting its 3 cm fallback. The V8 fitter and its descendants tighten their existing 5 mm point constraint when an authored interval asks for less; a looser authored tolerance never relaxes that existing solver limit. Release-boundary solver keys inherit the original segment tolerance. The recipe records the complete frame/region limit matrix. This changes numerical conditioning and failure reporting, not model weights or release approval.

Specifications without interval tolerances remain compatible: evaluation retains its explicit fallback, and fitting retains its original point limit. Invalid, nonfinite, boolean, zero and negative tolerances reject. Distributed region fitting keeps its separate anchor limits. These optimization inequalities do not guarantee convergence or verified motion quality.

## Actual checkpoint experiment

On 2026-10-08, the existing model-representable moving-box reference was prepared with the current intrinsic consistency, sparse planning and native/model projection checks. Both reference representations pass. The exact prompt is **“A person holds their left hand steady.”**, one second at 30 fps. Seeds 7103 and 7104 each have a text-only baseline and a guided take; guides retain contact frames 10–12. The unchanged Kimodo-SOMA-RP-v1.1 checkpoint uses 100 denoising steps, separated CFG [2, 2] and no postprocessing. Its actual text was encoded offline with the existing original-precision disk-offload implementation; full-resident encoder equivalence remains untested.

This is a constructive engineering fixture with one surface vertex on a moving box. It is not a realistic lift, grasp, held-out action/rig, anatomical calibration or human quality study. Its authored point tolerance is **1 mm**, distinct from the 3 cm provisional model-conditioning screen. All four raw samples, generation records, exports and failures are retained. Both guided takes were then corrected with the original V13 formulation and, separately, with the tolerance-preserving change. Original inputs, edit bounds and contact intent were retained.

| Seed | Text-only contact error | Guided contact error | Original correction | Tolerance-preserving correction |
| --- | ---: | ---: | ---: | ---: |
| 7103 | 979.983 mm | 44.859 mm | 4.821 mm | 1.987 mm |
| 7104 | 851.803 mm | 30.901 mm | 3.928 mm | 1.976 mm |

These are maximum actual skinned-point errors over all three requested frames. **Every condition still fails the authored 1 mm requirement.** The original corrections incorrectly had empty actor-level flags because their compiled specifications omitted that requirement, although the outer scene audit correctly retained the miss. Recompiling and reevaluating those unchanged outputs now rejects all three contact frames in both cases. The stricter rerun also correctly records `authored_contact_target_missed` for both actors.

The first guided take has 27.299 mm maximum analytic box penetration over its complete 30-frame clock. Both correction versions remove that measured penetration and full-skin floor penetration; orientation and actor edit limits remain separate observations. The new candidates' contact-frame normal errors are 7.525° and 6.150°, below the existing 15° measurement screen. No force, balance, self collision, triangle collision, continuous-time clearance or naturalness conclusion follows.

## Why the stricter solve still misses

The current fitter includes the selected contact vertex in a box inflated by its **2 mm clearance margin**, while the authored grip lies on the physical box face and allows only **1 mm point error**. Those particular inequalities conflict. A separate exact rational calculation shows that every point inside this grip's tolerance ball remains at least 1 mm inside the inflated box. This diagnoses the fitter's chosen conditions; it does not prove that contact with the physical box or joint generation is impossible. The approximately 1.98 mm results are retained, not accepted or hidden by a looser threshold.

Next work must make intended object contact and noncontact clearance compatible, preserving actual penetration checks and the authored contact tolerance. Repeating this same contradictory setup or increasing its iteration budget is not a justified next experiment.

## Verification and retained evidence

All 59 focused Python tests pass. They cover invalid values, different tolerances within one region, overriding a looser evaluator fallback, compiler/provenance preservation, unchanged inputs, release guards and solver controls. One initial test invocation named nonexistent modules and collected no tests; it is not counted as validation.

A separate NumPy reader implements all eight skin influences, explicit area-weighted normals, moving-box target sampling and analytic box penetration without importing the producer geometry/skinning helpers. It reproduces all complete point, object and normal tracks across twelve saved scenes and 360 actor-frames, using all 18,056 vertices per frame. It also reproduces the raw scenes' full-floor tracks. The first reader attempt chose a candidate orientation report for a saved source scene; that failed harness is retained. The corrected reader preserves all twelve scenes. This shares saved pose arrays and assets; it does not independently verify forward kinematics, anatomy or physics.

All twelve GLBs validate with zero errors and warnings. Actual headless Godot checks all 77 placed bone transforms across 360 actor-frames, including repeated source comparisons; maximum position-element error is below 0.8 micrometres. Raw scene packages retain authored events, measured failures and matching engine/source hashes. These are development/import checks, not successful interactions or held-out release evidence.

Local evidence is retained under `reports/scene-reference-generation-v1`, `reports/action-jobs/scene-reference-generation-v1`, `reports/scene-reference-correction-v1`, `reports/scene-reference-correction-v2`, `reports/scene-authored-tolerance-re-audit-v1`, `reports/scene-reference-clearance-conflict-v1`, `reports/scene-reference-separate-replay-v3` and the three corresponding `reports/godot-scene-reference-*` folders. Raw payloads and machine reports stay outside the public source repository.

## Reproduce

Use separately acquired pinned vendor/model assets, a compatible fitted scene and a complete actor plan; preserve earlier outputs by choosing fresh directories.

```powershell
.venv\Scripts\python.exe scripts/scene_generation.py prepare <scene.json> <actor-plan.json> reports/action-jobs/<new-job>
.venv\Scripts\python.exe scripts/run_actions.py reports/action-jobs/<new-job>/request.json --output reports/action-jobs/<new-job>
.venv\Scripts\python.exe scripts/scene_generation.py build reports/action-jobs/<new-job>
.venv\Scripts\python.exe scripts/audit_generated_scenes.py reports/action-jobs/<new-job>
.venv\Scripts\python.exe scripts/run_scene_fit.py <guided-scene-1.json> <guided-scene-2.json> --output reports/<new-correction> --solver-version 13 --preview-base reports/action-jobs/<new-job>
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/<new-correction> reports/<new-engine-audit>
```

Action families remain evaluation categories, not prompt restrictions. No training, dependency installation, new data acquisition, browser inspection, live API dispatch or animator rating occurred. All fourteen release evidence lists remain empty; the one whole-project goal stays active.
