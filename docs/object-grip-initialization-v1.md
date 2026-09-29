# Object-relative grip initialization

The previous full-motion fit failed all 490 exported hand-contact samples. Repeating a short grip's local rotation correction passed only one native grasp frame per hand. The new initializer transports the short guide's hand and finger joint frames with the prescribed object's position and orientation, then fits the full original correction spline to those targets.

`object_grip_seed.py` uses the existing bounded rotation mapping, original per-frame bone offsets and original root trajectory. Its targets include both wrists and finger joints. A position loss and rotation-matrix loss with a 10 cm orientation lever are balanced against small pose and second-difference penalties. The initializer does not optimize skin contact, collision or forces. Contact interval targets do not imply unchanged poses outside that interval. `run_object_grip_seed.py` checks the guide's independent audit, matching contact definitions, primitive geometry and reference object pose; it preserves input hashes and implementation snapshots.

This is a development test on the existing 180-frame box-transfer scene, not a new generated action, held-out sample or release approval. The guide is frame zero of the five-frame `region-box-export-rates-v1` study, corresponding to full-source frame 60. The grasp interval is 60–121. Body edits retain the original 40-degree bound and finger edits their existing individual bounds. The source reference is never reset to the guide or initialized clip.

## Measured result

The 100-iteration initializer and native measurement/export completed in 9.6 seconds. The first run and a second run adding standard independent-audit artifacts produced identical NPZ and GLB hashes. Both are retained under `reports/region-object-grip-seed-v1` and `reports/region-object-grip-seed-v2`.

| Independent exported measurement | Original source | Object-relative seed |
| --- | ---: | ---: |
| Hand-contact failures | 490 / 490 | 15 / 490 |
| Body geometry failures | 382 / 717 | 349 / 717 |
| Worst body-box penetration | 54.256846 mm | 38.993185 mm |
| Whole-clip peak joint speed | 1.364918 m/s | 1.283450 m/s |
| Whole-clip peak joint acceleration | 37.982124 m/s² | 33.619047 m/s² |
| Release-boundary speed, frames 119–123 | 0.337513 m/s | 0.374989 m/s |
| Release-boundary acceleration | 22.747577 m/s² | 23.899977 m/s² |

Native anchor positions pass all 62 grasp frames for each hand, with maximum errors 4.19 and 4.71 mm. Distributed contact passes 58 left-hand and 62 right-hand native frames. On the denser exported quarter-frame audit, all 15 remaining contact failures belong to the left hand, around frames 106.25–107 and 116.5–119. One measured patch clearance is 1.998367 mm, slightly below the unchanged 2 mm constraint. These failures remain failures; no tolerance was relaxed.

Maximum edit is 16.03 degrees, and maximum native FK discrepancy is 3.58e-7 (metres for positions, unitless for rotation-matrix elements). The original edit checks pass. Body-box penetration remains substantial and the minimum skin-floor gap is 1.995154 mm. Lower global motion peaks do not hide the local regressions: 24 joint speed maxima and 37 acceleration maxima increase by more than the report's 1e-5 allowance. Actual Godot import reproduces all 360 source/candidate actor-frames and 77 joints, with maximum position discrepancy below 0.333 micrometres. This confirms export fidelity, not animation quality.

Independent reports are `region-object-grip-seed-v2-audit/verification.json`, `region-object-grip-seed-v2-rates.json` and `region-object-grip-seed-v2-engine/verification.json` under local `reports/`. Studio's scene collection `object-grip-seed-review-v1` exposes the source and failed seed with these diagnostics. All 12 package file hashes and 12 offline route mappings were verified. No live browser check or human rating was performed.

## Remaining-failure diagnosis

Re-evaluating the worst exported sample reproduces the recorded signed distance exactly. At frame 121 the seed has 108 penetrating vertices, all dominated by the right forearm; the deepest vertex has 100% right-forearm weight. The source has 954 penetrating vertices across both forearms, hands and fingers at that same frame. The earlier full-body fit's worst sample at 121.75 also belongs to the right forearm. These are sample-specific skin-weight groupings, not a statement about every frame or anatomical collision volumes.

The seed's 15 left-hand failures comprise 14 clearance failures and 11 normal failures with overlap. Minimum patch clearance is 1.937686 mm against the unchanged 2 mm requirement (with the existing 1 micrometre numerical allowance); maximum normal error is 10.045554 degrees against 10 degrees. The right hand has no failed exported samples. No anchor or distributed-witness failures remain in this seed.

A separate one-frame diagnosis sweeps the right elbow around the shoulder-to-wrist axis from -80 to +80 degrees in 0.25-degree steps. Rotating the upper arm and compensating the local wrist keeps the wrist frame fixed; original bone offsets, roots and source-relative edit budgets are checked. Of 641 samples, 291 satisfy the bounds, wrist position error below 1 micrometre and wrist rotation-matrix error below 1e-6. None clears the box. The best valid sample, a -20-degree swivel, still penetrates 38.020208 mm. This rules out the sampled elbow-only orbit as a correction for this frame; it does not establish infeasibility of shoulder/torso movement, different grip placement, other elbow orbits or the full animation problem. No diagnostic pose was applied to the running full-body fit.

Evidence remains under `reports/region-object-grip-seed-v2-clearance-diagnosis.json`, `region-object-grip-seed-v2-contact-diagnosis.json`, and `region-object-grip-elbow-diagnosis-v1/{method.py,result.json}`. The latter preserves its exact diagnostic script and input hashes. The full-body trial continued unchanged during this diagnosis; its completed result is recorded below.

## Forearm-path diagnosis

A further native-pose check rules out an embedded wrist center as the explanation for the grip seed's worst collision. At frame 121, its right wrist center is 28.655 mm outside the box and its elbow center is 76.336 mm outside, while the worst skin vertex penetrates 38.993 mm. That vertex is approximately 127 mm back along the forearm from the wrist and 31.7 mm off the forearm axis. The problem is farther along the forearm, not at the wrist center.

Sampling 1,001 equally spaced points along the elbow-to-wrist segment at each of the 62 native grasp frames finds points inside the box in 12 seed frames and six regional-multiplier frames. At frame 121, the deepest sampled centerline point is 21.331 mm inside for the seed and 7.565 mm inside for the regional-multiplier candidate. The fixed-region full-body candidate has no sampled centerline crossings, yet its skin still penetrates; its frame-121 sampled centerline gap is 26.017 mm while skin penetrates 1.592 mm. Joint centers and bone segments are diagnostic references, not substitutes for skin clearance.

This identifies an arm-path problem despite outside endpoints. It does not prove the grip targets are infeasible, make centerline clearance a sufficient acceptance test, or justify relaxing original pose budgets. The recorded elbow-only orbit still found no passing correction. Broader arm/shoulder/torso corrections must preserve the grip and pass the full skin and timing checks. No pose, target or active fitting worker was modified. Exact diagnostic methods, inputs and measurements are retained under `reports/region-wrist-clearance-diagnosis-v1/{method.py,result.json,axis-method.py,axis-result.json}`.

## Review timing details

Studio now exposes **Motion timing diagnostics** beneath the scene assessment for packages with a bound joint-rate report. The expandable section identifies the number of joints with increased whole-clip peaks and names the affected contact phases with their frame ranges. For this seed, it reports 24 speed increases and 37 acceleration increases, including the release boundary at frames 119-123. The full per-joint report remains downloadable. Source-only and older packages without these diagnostics hide the section; changing scene placement or loading another scene clears the previous display.

The existing region-editor checks pass, and a Node check against the actual saved seed package verifies the counts and boundary ranges. The generated desktop bundle matches its sources, contains unique control IDs and passes module syntax checking. Evidence is in `reports/scene-rate-details-ui-v1/verification.json`. This was checked offline; live rendering was not verified. Numerical worker source, its inputs and acceptance limits are unchanged.

## Reproduction and follow-through

With the preceding development assets available locally:

```powershell
.venv\Scripts\python.exe scripts/run_object_grip_seed.py reports/region-full-transfer-v1/scene.json reports/region-box-export-rates-v1 reports/region-box-export-rates-v1-audit/verification.json reports/region-full-pose-seed-v1/motion.npz reports/fresh-object-grip-seed --iterations 100
.venv\Scripts\python.exe scripts/audit_scene_region_fit.py reports/fresh-object-grip-seed reports/fresh-object-grip-seed-audit
.venv\Scripts\python.exe scripts/audit_scene_joint_rates.py reports/fresh-object-grip-seed reports/fresh-object-grip-seed-rates.json
```

Fourteen focused initializer, transport and review-publisher tests pass. The new tests check transport invariance under object translation/rotation, an attainable moving IK target with fixed root and bone lengths, and an unattainable target that must not enlarge the edit budget or claim approval.

## Completed full-body comparison

The initialized full-body trial completed in 1,557.6 seconds and 648 objective evaluations. Its six stages, settings, solver implementation and original source match the previous full trial; only initialization differs. The exact-owner completion process finished the geometry, rate and Godot audits without retrying fitting.

| Exported measurement | Original full fit | Grip seed | Initialized full fit |
| --- | ---: | ---: | ---: |
| Failed contact samples / 490 | 490 | 15 | 482 |
| Failed body geometry samples / 717 | 267 | 349 | 219 |
| Worst box penetration | 5.272749 mm | 38.993185 mm | 2.786049 mm |
| Release-boundary speed | 0.788448 m/s | 0.374989 m/s | 0.643522 m/s |
| Release-boundary acceleration | 36.839410 m/s² | 23.899977 m/s² | 32.670875 m/s² |

The full solver improves body clearance but loses the seed's near-complete hand contact. All 245 left-hand samples fail the normal constraint; 197 right-hand samples fail it. Missing distributed witnesses occur in 77 left and 81 right samples. Anchor errors exceed tolerance in one left and eight right samples. Worst exported penetration occurs at frame 121.5, while native integer-key penetration is 1.592268 mm; native-only checks understate the problem.

Original edit bounds pass with maximum edit 32.480904 degrees. Root lift remains approximately 0.022 mm. Minimum exported floor gap is 2.017051 mm. Global peak speed/acceleration, 1.338512 m/s and 37.771181 m/s², remain below the source peaks, but 50 joint speed maxima and 34 acceleration maxima increase beyond the reporting allowance. All 360 Godot actor-frames pass, with maximum position discrepancy below 0.317 micrometres. Export fidelity does not approve the failed contacts.

Studio collection `scene-region-jobs/object-grip-full-review-v1` retains the failed source/candidate comparison. All previous outputs remain intact. `reports/region-object-grip-full-v1/comparison.json` binds the four-way comparison to result/audit hashes; `compare.py` preserves its method. Twelve package hashes and twelve offline route mappings are checked. No human evidence or live browser verification was added.

## Root-coordinate conditioning diagnosis

A separate process probes the completed fixed-region trial's exact initial objective closure without taking an optimizer step. It uses the same source, grip seed, constraints, witness initialization, sparse skin implementation and zero initial multipliers. It preserves the diagnostic script and bound protocol/result hashes in `reports/region-root-conditioning-v1` and rechecks all solver-input and implementation hashes afterward. No running worker or animation was modified.

The root lift starts at 22 micrometres because the zero-lift seed is mapped through a clamped sigmoid. At that point, one unit of the encoded root variable changes lift by only 0.0000219978 metres. The gradient norm in encoded root coordinates is 0.002315, versus 105.248 per metre in physical coordinates: a factor of about 45,459. The rotation-control gradient norm is 855.184 in its own mixed parameter units. These norms illustrate coordinate scaling; they are not a Hessian condition number or directly comparable physical forces.

Both a uniform root translation and a normalized physical-gradient direction pass central finite-difference checks at a 1-micrometre step, with relative discrepancies below 3.3e-11. A uniform upward step lowers the initial loss from 18.908899 to 18.908332; its derivative is -567.833592 objective units per metre. Individual physical gradients favor upward movement in 85 frames and downward movement in 95 frames. This rules out an identically zero root gradient at initialization; it does not establish final stationarity, the cause of the completed fit's failure, a feasible root trajectory, foot support or a successful reparameterization.

The regional-multiplier comparison completed without changes during this diagnosis. Root-coordinate scaling is a separate candidate experiment after that matched run, retaining the original 0-0.22 m bounds and exact starting motion. An optimizer change must demonstrate its own contact, geometry and temporal results; gradient rescaling alone is not an animation improvement.

### Prepared coordinate helper

`bounded_root_coordinates.py` implements a fixed diagonal rescaling around the legacy initial sigmoid state. Its zero-valued coordinates reproduce the old decoded starting pose exactly. Its scale is the initial lift derivative, giving unit derivative with respect to the new coordinate at initialization. Scaling stays frozen during a solve; later derivatives are not guaranteed to remain one. Finite coordinates still decode into the same 0-0.22 m lift interval, including floating-point saturation at the endpoints. The helper was initially isolated from production; the optional integration below now uses it. The default remains legacy.

Five focused tests cover float32/float64 starting-pose identity and gradients, finite differences, extreme finite coordinate bounds, and invalid input layouts. A separate copy of the real fitting function changes only root initialization/decoding for a no-step probe. The initial loss is exactly 18.908899475238105 in both versions; the new coordinate gradient matches every previously measured physical root-gradient component exactly. Its central finite-difference discrepancy is 3.54e-8 relative at a 1e-9 coordinate step. The probe takes zero optimizer steps and writes no candidate motion.

The isolated function copy, driver, input hashes and result remain in `reports/region-root-coordinate-probe-v1`. The isolated probe did not change production numerical source or the then-active regional-multiplier worker. That worker and its audits subsequently completed before the optional integration below; the helper alone has no motion-quality approval.

## Completed regional-multiplier comparison

The six-stage regional-multiplier trial completed in 1,644.0 seconds and 674 objective evaluations. Its protocol matches the fixed-region initialized control except timestamp and regional constraint mode, including implementation, inputs, seed, margins and budgets. All raw failures are retained.

| Exported measurement | Fixed regional penalty | Regional multipliers |
| --- | ---: | ---: |
| Failed contact samples / 490 | 482 | 327 |
| Failed body geometry samples / 717 | 219 | 284 |
| Worst box penetration | 2.786049 mm | 27.872394 mm |
| Global peak acceleration | 37.771181 m/s² | 39.515958 m/s² |
| Release-boundary speed | 0.643522 m/s | 0.434537 m/s |
| Release-boundary acceleration | 32.670875 m/s² | 20.745412 m/s² |

Contact improves but clearance becomes much worse. Global acceleration also exceeds the source's 37.982124 m/s² despite the optional optimization guard. Neither hand passes overall contact. Root lift remains approximately 22 micrometres. Original edit bounds pass; maximum rotation edit is 22.693982 degrees. Actual Godot import passes all 360 actor-frames and 77 joints with candidate position discrepancy below 0.316 micrometres. None of this approves motion quality.

`reports/region-object-grip-augmented-v1/comparison.json` binds the comparison to its result and audit hashes; `compare.py` preserves the method. The failed candidate is available in Studio collection `object-grip-augmented-review-v1`. Twelve package hashes and eleven permitted offline file routes were verified; the Python provenance snapshot is intentionally not served by the route allowlist. No live browser or human review was performed.

## Optional root-coordinate integration

`fit_scene_regions.py --root-coordinate-mode scaled_initial` now selects the frozen initial-derivative scaling. Omitting the option preserves legacy behavior. The protocol, recipe and implementation snapshots record the selected mode and helper. Root range, original source-relative rotation bounds, contact limits and default behavior remain unchanged.

Forty-one focused coordinate, initialization, regional constraint, witness, objective and job tests pass. An actual five-frame integration check runs two stages of two iterations for the frozen old solver, the current default and the scaled option. Every motion array in the old/current default comparison is bit-identical. All three runs satisfy original edit bounds and native FK discrepancy below 0.3 micrometres. The preserved method and bound inputs are in `reports/root-coordinate-integration-v1`. This short check verifies wiring and compatibility, not quality or convergence.

A full 180-frame comparison is running in `reports/region-root-scaled-full-v1/guard`, initialized from the same object-relative grip seed. It uses six stages, 100 iterations, the 3,600-second budget, regional multipliers, full skin, per-vertex object inequalities, sparse skinning, stage witness refresh and the same margins/rate guard. All original protocol settings and input hashes match the completed regional-multiplier trial. Implementation intentionally differs in `support_contact_v8.py` and `fit_scene_regions.py`, with `bounded_root_coordinates.py` added; the exact differences are recorded in `comparison-protocol.json`. This is an optional parameterization experiment, not an identical-code repetition.

An exact-process completion watcher will run independent geometry, temporal-rate and Godot checks after fitting exits. The outcome is pending. No imported numerical source will change during the trial. All 14 release capabilities remain unapproved; arbitrary actions, rig transfer, editing, partner interaction and human validation remain part of the same project goal.
